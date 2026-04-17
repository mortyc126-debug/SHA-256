/*
 * IT-11: N-scaling law for Walsh-2 score correlation.
 *
 * User hypothesis (worth testing): SHA-256 architecturally dilutes signal with N.
 * - Small N: signal visible.
 * - Large N: signal disappears.
 * Standard null: |corr(N)| ~ 1/sqrt(N) (iid signal, √N noise).
 * User-hypothesized: |corr(N)| ~ N^{-α}, α > 0.5 — active cancellation.
 *
 * Protocol:
 *   1. Train M_in (256x256) on N_TRAIN c-world pairs at block-1 end.
 *      Target = HW(block-1 state_diff) - 128.
 *   2. Test: one big stream of N_TEST pairs. For each pair compute
 *        score_b1   = Y_b1 ^T M Y_b1     (at block-1 state_diff)
 *        score_b2_16= Y_b2@r16 ^T M Y_b2@r16
 *        score_b2_32= Y_b2@r32 ^T M Y_b2@r32
 *        score_hash = Y_hash  ^T M Y_hash
 *      and the 4 HW targets.
 *   3. After full stream: report |corr| on first K pairs for K in K_LIST.
 *      Plot log|corr| vs log N, fit slope.
 *
 * Key: same trained M. Only the evaluation point changes.
 * If IT-9 gave corr=+0.977 at block-1 end, THIS experiment reproduces that
 * at the same measurement, then extends to block 2. N-scan shows dilution rate.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define NBITS 256
#define N_TRAIN 3000000
#define N_TEST  5000000

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

/* partial block-2 compression stopping at round nr, returning INNER state (no feed-forward) */
static void compress_partial(const uint32_t bl[16], const uint32_t iv[8], int nr, uint32_t out[8]) {
    uint32_t a=iv[0],b=iv[1],c=iv[2],d=iv[3],e=iv[4],f=iv[5],g=iv[6],h=iv[7],W[64];
    for(int i=0;i<16;i++) W[i]=bl[i];
    for(int i=16;i<64;i++){
        uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);
        uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);
        W[i]=W[i-16]+s0+W[i-7]+s1;
    }
    for(int i=0;i<nr;i++){
        uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];
        uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;
    }
    out[0]=a;out[1]=b;out[2]=c;out[3]=d;
    out[4]=e;out[5]=f;out[6]=g;out[7]=h;
}

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

/* Streaming correlation accumulator */
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

/* Snapshot points for N-scaling */
#define N_SNAPS 12
static const long K_LIST[N_SNAPS] = {
    1000, 3000, 10000, 30000, 100000, 300000,
    1000000, 1500000, 2000000, 3000000, 4000000, 5000000
};

/* Four evaluation points: b1 (block1 state_diff), b2r16, b2r32, b2r48, hash */
#define N_POINTS 5
static const char* POINT_NAMES[N_POINTS] = {"b1_r64", "b2_r16", "b2_r32", "b2_r48", "hash"};

int main(void){
    M_in = calloc(NBITS*NBITS, sizeof(double));
    uint32_t PAD[16]={0}; PAD[0]=0x80000000; PAD[15]=512;

    uint8_t msg[64];
    uint32_t b1_A[16], b1_B[16], s1_A[8], s1_B[8];
    int8_t Y[NBITS];

    /* ---- TRAIN: M_in on block-1 c-world pairs ---- */
    fprintf(stderr, "Train: N=%d pairs, target = HW(block-1 state_diff) - 128\n", N_TRAIN);
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
        if((i+1)%500000==0) fprintf(stderr, "  %ldK (cw=%ld)\n", (i+1)/1000, n_cw);
    }
    double sq = sqrt((double)n_cw);
    for(int i=0; i<NBITS*NBITS; i++) M_in[i] /= sq;
    tr_M = 0; for(int i=0; i<NBITS; i++) tr_M += M_in[i*NBITS+i];
    fprintf(stderr, "Trained: cw=%ld  tr(M)=%.1f\n", n_cw, tr_M);

    /* ---- TEST: 5 eval points × 12 sample sizes ---- */
    fprintf(stderr, "Test: %d pairs, computing scores at 5 block-2 evaluation points\n", N_TEST);
    Acc acc[N_POINTS];
    memset(acc, 0, sizeof(acc));

    /* Results[point][snap] = |corr| and z at that N */
    double results_corr[N_POINTS][N_SNAPS];
    double results_z[N_POINTS][N_SNAPS];
    long   results_n[N_POINTS][N_SNAPS];

    int snap_idx[N_POINTS]={0};  /* next snapshot per point */

    uint32_t hash_A[8], hash_B[8];
    uint32_t mid_A[8], mid_B[8];

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

        /* Point 0: b1_r64 (block-1 state_diff itself) */
        extract_bits(D1, Y);
        double sc0 = score_pair(Y);
        acc_add(&acc[0], sc0, (double)hw_b1);

        /* Point 1: b2 at round 16 (inner state diff) */
        compress_partial(PAD, s1_A, 16, mid_A);
        compress_partial(PAD, s1_B, 16, mid_B);
        uint32_t D2_16[8]; for(int w=0;w<8;w++) D2_16[w]=mid_A[w]^mid_B[w];
        int hw_b2_16 = hw256(D2_16);
        extract_bits(D2_16, Y);
        double sc1 = score_pair(Y);
        acc_add(&acc[1], sc1, (double)hw_b2_16);

        /* Point 2: b2 at round 32 */
        compress_partial(PAD, s1_A, 32, mid_A);
        compress_partial(PAD, s1_B, 32, mid_B);
        uint32_t D2_32[8]; for(int w=0;w<8;w++) D2_32[w]=mid_A[w]^mid_B[w];
        int hw_b2_32 = hw256(D2_32);
        extract_bits(D2_32, Y);
        double sc2 = score_pair(Y);
        acc_add(&acc[2], sc2, (double)hw_b2_32);

        /* Point 3: b2 at round 48 */
        compress_partial(PAD, s1_A, 48, mid_A);
        compress_partial(PAD, s1_B, 48, mid_B);
        uint32_t D2_48[8]; for(int w=0;w<8;w++) D2_48[w]=mid_A[w]^mid_B[w];
        int hw_b2_48 = hw256(D2_48);
        extract_bits(D2_48, Y);
        double sc3 = score_pair(Y);
        acc_add(&acc[3], sc3, (double)hw_b2_48);

        /* Point 4: final hash */
        compress_full(PAD, s1_A, hash_A);
        compress_full(PAD, s1_B, hash_B);
        uint32_t Dh[8]; for(int w=0;w<8;w++) Dh[w]=hash_A[w]^hash_B[w];
        int hw_hash = hw256(Dh);
        extract_bits(Dh, Y);
        double sc4 = score_pair(Y);
        acc_add(&acc[4], sc4, (double)hw_hash);

        /* Snapshot check */
        for(int p=0; p<N_POINTS; p++){
            while(snap_idx[p]<N_SNAPS && acc[p].n >= K_LIST[snap_idx[p]]){
                double c = acc_corr(&acc[p]);
                results_corr[p][snap_idx[p]] = c;
                results_z[p][snap_idx[p]] = c*sqrt((double)acc[p].n-2);
                results_n[p][snap_idx[p]] = acc[p].n;
                snap_idx[p]++;
            }
        }

        if((i+1)%500000==0) fprintf(stderr, "  test %ldK  (cw_b1=%ld)\n", (i+1)/1000, acc[0].n);
    }

    /* Finalize any remaining snapshots with final n */
    for(int p=0; p<N_POINTS; p++){
        while(snap_idx[p]<N_SNAPS){
            double c = acc_corr(&acc[p]);
            results_corr[p][snap_idx[p]] = c;
            results_z[p][snap_idx[p]] = c*sqrt((double)acc[p].n-2);
            results_n[p][snap_idx[p]] = acc[p].n;
            snap_idx[p]++;
        }
    }

    printf("=== IT-11: Walsh-2 score N-scaling through block 2 ===\n");
    printf("Train: M_in on N=%d block-1 c-world pairs, target=HW(b1_diff)\n", N_TRAIN);
    printf("Test: %d candidate pairs (c-world filter applied)\n\n", N_TEST);

    printf("%-10s ", "N");
    for(int p=0; p<N_POINTS; p++) printf("%14s ", POINT_NAMES[p]);
    printf("\n");

    for(int s=0; s<N_SNAPS; s++){
        printf("%-10ld ", K_LIST[s]);
        for(int p=0; p<N_POINTS; p++){
            printf("%+8.4f/%+5.1f ", results_corr[p][s], results_z[p][s]);
        }
        printf("\n");
    }

    printf("\n--- Fit |corr| ~ N^{-alpha} per point (OLS on log|corr| vs log N, use last 8 snaps) ---\n");
    for(int p=0; p<N_POINTS; p++){
        double sx=0, sy=0, sxy=0, sx2=0; int k=0;
        for(int s=4; s<N_SNAPS; s++){
            double absC = fabs(results_corr[p][s]);
            if(absC < 1e-10) continue;
            double lx = log((double)K_LIST[s]);
            double ly = log(absC);
            sx+=lx; sy+=ly; sxy+=lx*ly; sx2+=lx*lx; k++;
        }
        if(k<3){ printf("  %s: too few points\n", POINT_NAMES[p]); continue; }
        double alpha = -(k*sxy - sx*sy) / (k*sx2 - sx*sx);
        double log_c0 = (sy + alpha*sx)/k;
        printf("  %-10s  alpha=%+6.3f  (null=0.5 means pure noise; <0.5 persistent signal; >0.5 ACTIVE DILUTION)\n",
               POINT_NAMES[p], alpha);
    }

    printf("\n--- INTERPRETATION ---\n");
    printf("alpha < 0.5: real signal persists (super-root-N)\n");
    printf("alpha ≈ 0.5: 1/sqrt(N) noise (no real signal)\n");
    printf("alpha > 0.5: ACTIVE DILUTION — signal cancels faster than noise\n");
    printf("This is the test of user hypothesis: is SHA-256 architecture actively\n");
    printf("scrubbing signal with sample size, beyond standard sqrt(N) behaviour?\n");

    free(M_in);
    return 0;
}
