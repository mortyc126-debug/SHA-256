/*
 * IT-12: Extended N-scaling on hash + per-bit z scan + Parseval-like invariant.
 *
 * Three tests:
 *  1. Extend N_TEST to 10M candidate pairs (~1.4M c-world) for hash.
 *     If c_∞ ≈ -0.005 is real, |z| should grow as √N from 4 (at 720K)
 *     toward 15 (at 10M). If it stays flat near 4 → accidental fluctuation.
 *
 *  2. Per-bit z-vector at b1_r64 and at hash:
 *     z_bit(b) = √N × corr(score, state_diff_bit_b)
 *     Find top |z| bits; compare spectrum b1 vs hash.
 *
 *  3. Parseval-like invariant: sum_bits z_bit². Under H0 (no signal),
 *     E[Σ z²] = 256 (chi-square). Signal → super-256. Architecture
 *     dilution → sub-256 at block-2.
 *     N-scaling: E[Σ z² | N] = 256 + N × c_persistent² × ...
 *     If persistent signal lives in higher order, Σ z_bit² (first order)
 *     stays ≈ 256 regardless of N, while individual corr → 0.
 *
 * Same trained M_in as IT-11 (seeded reproducibly).
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define NBITS 256
#define N_TRAIN 3000000
#define N_TEST  10000000

static const uint32_t KK[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))

static void compress_full(const uint32_t bl[16], const uint32_t iv[8], uint32_t out[8]) {
    uint32_t a=iv[0],b=iv[1],c=iv[2],d=iv[3],e=iv[4],f=iv[5],g=iv[6],h=iv[7],W[64];
    for(int i=0;i<16;i++) W[i]=bl[i];
    for(int i=16;i<64;i++){
        uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);
        uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);
        W[i]=W[i-16]+s0+W[i-7]+s1;
    }
    for(int i=0;i<64;i++){
        uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];
        uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;
    }
    out[0]=a+iv[0];out[1]=b+iv[1];out[2]=c+iv[2];out[3]=d+iv[3];
    out[4]=e+iv[4];out[5]=f+iv[5];out[6]=g+iv[6];out[7]=h+iv[7];
}

/* Reproducible: reuse IT-11 seed */
static uint64_t xs[2]={0x111ABB00CAFE01ULL, 0xDEAD111ABEEF02ULL};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int popc32(uint32_t x){return __builtin_popcount(x);}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=popc32(s[w]);return c;}

static double *M_in;
static double tr_M;

static void extract_bits(const uint32_t D[8], int8_t Y[NBITS]) {
    for(int w=0;w<8;w++) for(int b=0;b<32;b++)
        Y[w*32+b] = ((D[w]>>(31-b))&1) ? 1 : -1;
}
static double score_pair(const int8_t Y[NBITS]) {
    double Q = 0;
    for(int a=0;a<NBITS;a++){
        double r=0;
        for(int b=0;b<NBITS;b++) r += M_in[a*NBITS+b] * Y[b];
        Q += Y[a] * r;
    }
    return (Q - tr_M) / 2.0;
}

typedef struct {
    double ss, sh, ssh, ss2, sh2;
    long n;
} Acc;
static inline void acc_add(Acc*a, double s, double h){
    a->ss+=s; a->sh+=h; a->ssh+=s*h; a->ss2+=s*s; a->sh2+=h*h; a->n++;
}
static double acc_corr(const Acc*a){
    if(a->n<2) return 0;
    double ms=a->ss/a->n, mh=a->sh/a->n;
    double cv=a->ssh/a->n - ms*mh;
    double vs=a->ss2/a->n - ms*ms;
    double vh=a->sh2/a->n - mh*mh;
    return (vs>0 && vh>0) ? cv/sqrt(vs*vh) : 0;
}

/* Per-bit accumulator for z_bit = sqrt(N) * corr(score, state_diff_bit[b]) */
typedef struct {
    double s_sum;
    double s2_sum;
    double y_sum[NBITS];   /* sum of signed bit */
    double sy_sum[NBITS];  /* sum of score * signed bit */
    long n;
} PerBitAcc;
static void pba_init(PerBitAcc*p){memset(p,0,sizeof(*p));}
static void pba_add(PerBitAcc*p, double score, const int8_t Y[NBITS]){
    p->s_sum += score; p->s2_sum += score*score; p->n++;
    for(int b=0; b<NBITS; b++){ p->y_sum[b] += Y[b]; p->sy_sum[b] += score * Y[b]; }
}
/* Compute z_bit[b] = corr(score, Y_b) * sqrt(n) */
static void pba_compute(const PerBitAcc*p, double z_out[NBITS]){
    double ms = p->s_sum / p->n;
    double vs = p->s2_sum/p->n - ms*ms;
    double sd_s = sqrt(vs>0 ? vs : 1e-20);
    for(int b=0; b<NBITS; b++){
        double my = p->y_sum[b]/p->n;
        double cv = p->sy_sum[b]/p->n - ms*my;
        double vy = 1.0 - my*my; /* Y ∈ {±1} so E[Y^2]=1 */
        double corr = cv / (sd_s * sqrt(vy>0 ? vy : 1e-20));
        z_out[b] = corr * sqrt((double)p->n - 2);
    }
}

/* Snapshot points */
#define N_SNAPS 8
static const long K_LIST[N_SNAPS] = {10000, 30000, 100000, 300000, 500000, 800000, 1200000, 1500000};

int main(void){
    M_in = calloc(NBITS*NBITS, sizeof(double));
    uint32_t PAD[16]={0}; PAD[0]=0x80000000; PAD[15]=512;

    uint8_t msg[64];
    uint32_t b1_A[16], b1_B[16], s1_A[8], s1_B[8];
    int8_t Y[NBITS];

    /* Train identical to IT-11 */
    fprintf(stderr, "IT-12 Train: %d pairs, block-1 c-world\n", N_TRAIN);
    long n_cw = 0;
    for(long i=0; i<N_TRAIN; i++){
        fr(msg, 64);
        for(int w=0; w<16; w++) b1_A[w] = ((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        memcpy(b1_B, b1_A, 64);
        int j = xr() & 511;
        b1_B[j>>5] ^= (1u << (31 - (j & 31)));
        compress_full(b1_A, IV, s1_A);
        compress_full(b1_B, IV, s1_B);
        uint32_t D1[8]; for(int w=0; w<8; w++) D1[w] = s1_A[w]^s1_B[w];
        if(hw256(D1) >= 120) continue;
        int hw_b1 = hw256(D1);
        double tgt = hw_b1 - 128.0;
        extract_bits(D1, Y);
        for(int a=0; a<NBITS; a++) for(int b=0; b<NBITS; b++)
            M_in[a*NBITS+b] += (double)Y[a]*Y[b]*tgt;
        n_cw++;
        if((i+1)%1000000==0) fprintf(stderr, "  train %ldM (cw=%ld)\n", (i+1)/1000000, n_cw);
    }
    double sq = sqrt((double)n_cw);
    for(int i=0; i<NBITS*NBITS; i++) M_in[i] /= sq;
    tr_M = 0; for(int i=0; i<NBITS; i++) tr_M += M_in[i*NBITS+i];
    fprintf(stderr, "Train done: cw=%ld tr(M)=%.1f\n", n_cw, tr_M);

    /* Test: 10M candidate pairs, track corr at b1_r64 and hash, per-bit z at end */
    Acc acc_b1, acc_hash;
    memset(&acc_b1, 0, sizeof(acc_b1));
    memset(&acc_hash, 0, sizeof(acc_hash));
    PerBitAcc pba_b1, pba_hash;
    pba_init(&pba_b1); pba_init(&pba_hash);

    /* Snapshot arrays */
    double snap_corr_b1[N_SNAPS]={0}, snap_z_b1[N_SNAPS]={0};
    double snap_corr_hash[N_SNAPS]={0}, snap_z_hash[N_SNAPS]={0};
    long snap_n[N_SNAPS]={0};
    int snap_i = 0;

    fprintf(stderr, "IT-12 Test: %d candidate pairs\n", N_TEST);
    uint32_t hash_A[8], hash_B[8];
    for(long i=0; i<N_TEST; i++){
        fr(msg, 64);
        for(int w=0; w<16; w++) b1_A[w] = ((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        memcpy(b1_B, b1_A, 64);
        int j = xr() & 511;
        b1_B[j>>5] ^= (1u << (31 - (j & 31)));
        compress_full(b1_A, IV, s1_A);
        compress_full(b1_B, IV, s1_B);
        uint32_t D1[8]; for(int w=0; w<8; w++) D1[w] = s1_A[w]^s1_B[w];
        if(hw256(D1) >= 120) continue;
        int hw_b1 = hw256(D1);

        /* b1_r64 score + per-bit */
        extract_bits(D1, Y);
        double sc_b1 = score_pair(Y);
        acc_add(&acc_b1, sc_b1, (double)hw_b1);
        pba_add(&pba_b1, sc_b1, Y);

        /* Hash */
        compress_full(PAD, s1_A, hash_A);
        compress_full(PAD, s1_B, hash_B);
        uint32_t Dh[8]; for(int w=0;w<8;w++) Dh[w]=hash_A[w]^hash_B[w];
        int hw_hash = hw256(Dh);
        extract_bits(Dh, Y);
        double sc_hash = score_pair(Y);
        acc_add(&acc_hash, sc_hash, (double)hw_hash);
        pba_add(&pba_hash, sc_hash, Y);

        /* Snapshot */
        while(snap_i < N_SNAPS && acc_b1.n >= K_LIST[snap_i]){
            double cb = acc_corr(&acc_b1);
            double ch = acc_corr(&acc_hash);
            snap_corr_b1[snap_i] = cb; snap_z_b1[snap_i] = cb*sqrt((double)acc_b1.n-2);
            snap_corr_hash[snap_i] = ch; snap_z_hash[snap_i] = ch*sqrt((double)acc_hash.n-2);
            snap_n[snap_i] = acc_b1.n;
            snap_i++;
        }
        if((i+1)%1000000==0) fprintf(stderr, "  test %ldM (cw=%ld)\n", (i+1)/1000000, acc_b1.n);
    }

    /* Fill remaining snapshots with final N */
    while(snap_i < N_SNAPS){
        double cb = acc_corr(&acc_b1);
        double ch = acc_corr(&acc_hash);
        snap_corr_b1[snap_i] = cb; snap_z_b1[snap_i] = cb*sqrt((double)acc_b1.n-2);
        snap_corr_hash[snap_i] = ch; snap_z_hash[snap_i] = ch*sqrt((double)acc_hash.n-2);
        snap_n[snap_i] = acc_b1.n;
        snap_i++;
    }

    /* Per-bit z vectors at final N */
    double z_b1_bits[NBITS], z_hash_bits[NBITS];
    pba_compute(&pba_b1, z_b1_bits);
    pba_compute(&pba_hash, z_hash_bits);

    /* Parseval-like: sum z^2 */
    double sumz2_b1=0, sumz2_hash=0;
    for(int b=0; b<NBITS; b++){ sumz2_b1 += z_b1_bits[b]*z_b1_bits[b]; sumz2_hash += z_hash_bits[b]*z_hash_bits[b]; }

    /* Report */
    printf("=== IT-12: Extended N-scaling + per-bit spectrum ===\n\n");
    printf("Train: %d pairs, %ld c-world (%.2f%%)\n", N_TRAIN, n_cw, 100.0*n_cw/N_TRAIN);
    printf("Test:  %d candidate pairs, %ld c-world (%.2f%%)\n\n", N_TEST, acc_b1.n, 100.0*acc_b1.n/N_TEST);

    printf("%-12s  %-18s  %-18s\n", "N(c-world)", "b1_r64 (corr/z)", "hash (corr/z)");
    for(int s=0; s<N_SNAPS; s++){
        if(snap_n[s]==0) continue;
        printf("%-12ld  %+8.5f/%+7.1f  %+8.5f/%+7.2f\n",
               snap_n[s], snap_corr_b1[s], snap_z_b1[s], snap_corr_hash[s], snap_z_hash[s]);
    }

    /* c_∞ test for hash: if z grows as sqrt(N), c_∞ real */
    printf("\n--- c_∞ test for hash ---\n");
    if(N_SNAPS >= 4){
        double z_early = fabs(snap_z_hash[3]);
        double z_late = fabs(snap_z_hash[N_SNAPS-1]);
        double n_ratio = (double)snap_n[N_SNAPS-1] / snap_n[3];
        double expected_z_late_if_persistent = z_early * sqrt(n_ratio);
        printf("  z[N=%ld] = %.2f\n", snap_n[3], z_early);
        printf("  z[N=%ld] = %.2f\n", snap_n[N_SNAPS-1], z_late);
        printf("  if c_∞ persistent: z should be %.2f (√N growth)\n", expected_z_late_if_persistent);
        printf("  Observed / expected = %.2f\n", z_late/expected_z_late_if_persistent);
        if(z_late/expected_z_late_if_persistent > 0.5)
            printf("  → SIGNAL LOOKS REAL (within factor 2 of √N prediction)\n");
        else
            printf("  → LOOKS LIKE FLUCTUATION (sub-√N growth, alpha > 0)\n");
    }

    /* Per-bit report */
    printf("\n--- Per-bit z at final N (b1_r64 vs hash) ---\n");
    /* Find top 10 |z| bits for each */
    int idx_b1[NBITS], idx_h[NBITS];
    for(int b=0; b<NBITS; b++){idx_b1[b]=b; idx_h[b]=b;}
    /* bubble sort by |z| desc; fine for 256 */
    for(int i=0;i<NBITS-1;i++) for(int j=0;j<NBITS-1-i;j++){
        if(fabs(z_b1_bits[idx_b1[j]]) < fabs(z_b1_bits[idx_b1[j+1]])){int t=idx_b1[j];idx_b1[j]=idx_b1[j+1];idx_b1[j+1]=t;}
        if(fabs(z_hash_bits[idx_h[j]]) < fabs(z_hash_bits[idx_h[j+1]])){int t=idx_h[j];idx_h[j]=idx_h[j+1];idx_h[j+1]=t;}
    }

    printf("Top 10 |z| bits at b1_r64:\n");
    for(int i=0;i<10;i++) printf("  bit %3d: z=%+8.2f\n", idx_b1[i], z_b1_bits[idx_b1[i]]);
    printf("Top 10 |z| bits at hash:\n");
    for(int i=0;i<10;i++) printf("  bit %3d: z=%+8.2f\n", idx_h[i], z_hash_bits[idx_h[i]]);

    /* Parseval invariant */
    printf("\n--- Parseval Σ z_bit² ---\n");
    printf("  b1_r64: Σz² = %.1f  (E[H0] = 256; strong signal ⇒ Σz² >> 256)\n", sumz2_b1);
    printf("  hash:   Σz² = %.1f  (dilution ⇒ Σz² ≈ 256; super-256 ⇒ residual signal)\n", sumz2_hash);
    double z_hash_excess = (sumz2_hash - 256.0) / sqrt(2.0*256.0); /* chi²_256 std = √(2×256) */
    printf("  hash excess: (Σz²-256)/√(2·256) = %+.2f σ\n", z_hash_excess);
    if(z_hash_excess > 3.0)
        printf("  → CHI² EXCESS AT HASH: residual signal in linear projection\n");
    else if(z_hash_excess < -3.0)
        printf("  → CHI² DEFICIT AT HASH: sub-random (like IT-1.3 finding)\n");
    else
        printf("  → No chi² excess: linear projection at hash is RO-consistent\n");

    free(M_in);
    return 0;
}
