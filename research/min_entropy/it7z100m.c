/*
 * IT-7Z100M: SHA-256 microscopic bias at N=100M Wang pairs.
 *
 * Pure C for speed. For each pair:
 *   1. Generate random M (64 bytes), flip one bit in W[0] → M'
 *   2. Compute 16-round reduced SHA-256 block1 for both
 *   3. XOR state diff D = state(M) ^ state(M')
 *   4. Extract HW of e-register diff (word 4 of D)
 *   5. Compute Walsh-2 score from D bits using pre-trained M_in matrix
 *   6. Accumulate correlation(score, HW_e)
 *
 * Two passes: pass 1 trains M_in on first half, pass 2 tests on second.
 * Uses inline SHA-256 round function (16 rounds only).
 *
 * Output: correlation, z-score, block sign counts.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define ROUNDS 16
#define NBITS 64        /* use first 64 bits of 256-bit state for Walsh-2 */
#define N_TOTAL 100000000
#define N_HALF  50000000
#define BLOCK_SIZE 1000000

/* SHA-256 constants */
static const uint32_t K[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};
static const uint32_t IV[8] = {
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
    0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
};

#define ROTR(x,n) (((x)>>(n))|((x)<<(32-(n))))
#define CH(e,f,g) (((e)&(f))^((~(e))&(g)))
#define MAJ(a,b,c) (((a)&(b))^((a)&(c))^((b)&(c)))
#define EP0(a) (ROTR(a,2)^ROTR(a,13)^ROTR(a,22))
#define EP1(e) (ROTR(e,6)^ROTR(e,11)^ROTR(e,25))

static void compress_r(const uint32_t block[16], int nrounds, uint32_t out[8]) {
    uint32_t a=IV[0],b=IV[1],c=IV[2],d=IV[3],e=IV[4],f=IV[5],g=IV[6],h=IV[7];
    uint32_t W[64];
    for (int i = 0; i < 16; i++) W[i] = block[i];
    for (int i = 16; i < nrounds; i++) {
        uint32_t s0 = ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);
        uint32_t s1 = ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);
        W[i] = W[i-16] + s0 + W[i-7] + s1;
    }
    for (int i = 0; i < nrounds; i++) {
        uint32_t T1 = h + EP1(e) + CH(e,f,g) + K[i] + W[i];
        uint32_t T2 = EP0(a) + MAJ(a,b,c);
        h=g; g=f; f=e; e=d+T1; d=c; c=b; b=a; a=T1+T2;
    }
    out[0]=a+IV[0]; out[1]=b+IV[1]; out[2]=c+IV[2]; out[3]=d+IV[3];
    out[4]=e+IV[4]; out[5]=f+IV[5]; out[6]=g+IV[6]; out[7]=h+IV[7];
}

static inline int popcount32(uint32_t x) { return __builtin_popcount(x); }

/* Simple xorshift128+ PRNG */
static uint64_t s[2] = {0x1234567890abcdef, 0xfedcba0987654321};
static inline uint64_t xorshift128p(void) {
    uint64_t s1 = s[0], s0 = s[1];
    s[0] = s0;
    s1 ^= s1 << 23;
    s[1] = s1 ^ s0 ^ (s1 >> 17) ^ (s0 >> 26);
    return s[1] + s0;
}

static void fill_random(uint8_t *buf, int len) {
    for (int i = 0; i < len; i += 8) {
        uint64_t r = xorshift128p();
        int n = (len - i < 8) ? len - i : 8;
        memcpy(buf + i, &r, n);
    }
}

int main(void) {
    /* M_in matrix for Walsh-2 (NBITS x NBITS), trained in pass 1 */
    double *M_in = calloc(NBITS * NBITS, sizeof(double));

    /* Accumulators for training */
    double *YtYf = calloc(NBITS * NBITS, sizeof(double));
    double sum_hw_tr = 0;
    long count_tr = 0;

    /* Test accumulators */
    double sum_score = 0, sum_hw = 0, sum_score2 = 0, sum_hw2 = 0, sum_score_hw = 0;
    long count_te = 0;
    int block_signs[200]; int n_blocks = 0;
    double block_sum_s = 0, block_sum_h = 0, block_sum_sh = 0;
    double block_sum_s2 = 0, block_sum_h2 = 0;
    long block_count = 0;

    uint8_t msg[64];
    uint32_t block1[16], block2[16], state1[8], state2[8];
    int8_t Y[NBITS];     /* ±1 coded bits of D */
    double tr_M = 0;

    clock_t t0 = clock();

    /* === PASS 1: Train on first N_HALF pairs === */
    fprintf(stderr, "Pass 1: training on %d pairs...\n", N_HALF);
    for (long i = 0; i < N_HALF; i++) {
        fill_random(msg, 64);
        /* Parse msg as big-endian uint32 words */
        for (int w = 0; w < 16; w++)
            block1[w] = ((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|
                        ((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        /* Flip random bit in W[0] */
        int j = xorshift128p() & 31;
        memcpy(block2, block1, 64);
        block2[0] ^= (1u << (31 - j));

        compress_r(block1, ROUNDS, state1);
        compress_r(block2, ROUNDS, state2);

        uint32_t D[8];
        for (int w = 0; w < 8; w++) D[w] = state1[w] ^ state2[w];
        int hw_e = popcount32(D[4]);
        double target = hw_e - 16.0;  /* centered */

        /* Extract first NBITS bits of D as ±1 */
        for (int b = 0; b < NBITS; b++) {
            int w = b / 32, bit = 31 - (b % 32);
            Y[b] = ((D[w] >> bit) & 1) ? 1 : -1;
        }

        /* Accumulate Y^T (Y * target) */
        for (int a = 0; a < NBITS; a++)
            for (int b = 0; b < NBITS; b++)
                YtYf[a * NBITS + b] += (double)Y[a] * Y[b] * target;

        sum_hw_tr += hw_e;
        count_tr++;
        if ((i+1) % 10000000 == 0) fprintf(stderr, "  train %ldM\n", (i+1)/1000000);
    }
    double sqrt_ntr = sqrt((double)count_tr);
    for (int i = 0; i < NBITS * NBITS; i++) M_in[i] = YtYf[i] / sqrt_ntr;
    tr_M = 0;
    for (int i = 0; i < NBITS; i++) tr_M += M_in[i * NBITS + i];
    free(YtYf);
    fprintf(stderr, "  trained. mean_hw=%.4f tr(M)=%.2f\n", sum_hw_tr/count_tr, tr_M);

    /* === PASS 2: Test on second N_HALF pairs === */
    fprintf(stderr, "Pass 2: testing on %d pairs...\n", N_HALF);
    for (long i = 0; i < N_HALF; i++) {
        fill_random(msg, 64);
        for (int w = 0; w < 16; w++)
            block1[w] = ((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|
                        ((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j = xorshift128p() & 31;
        memcpy(block2, block1, 64);
        block2[0] ^= (1u << (31 - j));

        compress_r(block1, ROUNDS, state1);
        compress_r(block2, ROUNDS, state2);

        uint32_t D[8];
        for (int w = 0; w < 8; w++) D[w] = state1[w] ^ state2[w];
        int hw_e = popcount32(D[4]);

        for (int b = 0; b < NBITS; b++) {
            int w = b / 32, bit = 31 - (b % 32);
            Y[b] = ((D[w] >> bit) & 1) ? 1 : -1;
        }

        /* score = Y^T M_in Y - tr(M) all /2  (upper triangle sum) */
        double Q = 0;
        for (int a = 0; a < NBITS; a++) {
            double row_sum = 0;
            for (int b = 0; b < NBITS; b++)
                row_sum += M_in[a * NBITS + b] * Y[b];
            Q += Y[a] * row_sum;
        }
        double score = (Q - tr_M) / 2.0;

        sum_score += score;
        sum_hw += hw_e;
        sum_score2 += score * score;
        sum_hw2 += (double)hw_e * hw_e;
        sum_score_hw += score * hw_e;
        count_te++;

        /* Block tracking */
        block_sum_s += score;
        block_sum_h += hw_e;
        block_sum_sh += score * hw_e;
        block_sum_s2 += score * score;
        block_sum_h2 += (double)hw_e * hw_e;
        block_count++;
        if (block_count >= BLOCK_SIZE) {
            double bm_s = block_sum_s / block_count;
            double bm_h = block_sum_h / block_count;
            double cov = block_sum_sh / block_count - bm_s * bm_h;
            double vs = block_sum_s2 / block_count - bm_s * bm_s;
            double vh = block_sum_h2 / block_count - bm_h * bm_h;
            double bc = (vs > 0 && vh > 0) ? cov / sqrt(vs * vh) : 0;
            block_signs[n_blocks++] = (bc > 0) ? 1 : 0;
            block_sum_s = block_sum_h = block_sum_sh = block_sum_s2 = block_sum_h2 = 0;
            block_count = 0;
        }
        if ((i+1) % 10000000 == 0) fprintf(stderr, "  test %ldM\n", (i+1)/1000000);
    }

    /* Global correlation */
    double m_s = sum_score / count_te;
    double m_h = sum_hw / count_te;
    double cov = sum_score_hw / count_te - m_s * m_h;
    double v_s = sum_score2 / count_te - m_s * m_s;
    double v_h = sum_hw2 / count_te - m_h * m_h;
    double corr = (v_s > 0 && v_h > 0) ? cov / sqrt(v_s * v_h) : 0;
    double z = corr * sqrt((double)count_te - 2);

    int n_pos = 0;
    for (int i = 0; i < n_blocks; i++) n_pos += block_signs[i];

    double elapsed = (double)(clock() - t0) / CLOCKS_PER_SEC;

    printf("{\n");
    printf("  \"N_total\": %d,\n", N_TOTAL);
    printf("  \"N_train\": %d,\n", N_HALF);
    printf("  \"N_test\": %ld,\n", count_te);
    printf("  \"rounds\": %d,\n", ROUNDS);
    printf("  \"nbits\": %d,\n", NBITS);
    printf("  \"correlation\": %.10f,\n", corr);
    printf("  \"z_score\": %.4f,\n", z);
    printf("  \"mean_hw_test\": %.6f,\n", m_h);
    printf("  \"n_blocks\": %d,\n", n_blocks);
    printf("  \"n_positive_blocks\": %d,\n", n_pos);
    printf("  \"sign_fraction\": %.4f,\n", (double)n_pos / n_blocks);
    printf("  \"elapsed_sec\": %.1f\n", elapsed);
    printf("}\n");

    free(M_in);
    return 0;
}
