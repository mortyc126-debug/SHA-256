/*
 * IT-8A: Does the carry-out collision signal MIGRATE into high Walsh
 * orders instead of dying?
 *
 * v20 §217-218 found: at 8 rounds, carry-out collision pairs have
 * δH 3.3 bits closer to collision. By round 20, this advantage = 0.
 * v20 concluded: "carry-out approach not better than birthday."
 *
 * But v20 only measured DIRECT δH (Walsh-1 metric). Our IT-6 showed
 * that input→output signal migrates Walsh-1→Walsh-3 (Ω_3=0.98 when
 * Ω_1≈0). Same migration might happen here.
 *
 * Method:
 *   1. Generate N random Wang pairs (single-bit flip in W[0])
 *   2. At round 8: compute carry-out of e-register addition
 *   3. Split into "carry-matched" (same carry pattern in low bits)
 *      and "carry-unmatched" pairs
 *   4. For each group, compute state_diff at rounds 8, 12, 16, 20
 *   5. Measure: does carry-matching predict lower δH_e at later rounds?
 *      - Direct metric: mean HW(δe) for matched vs unmatched
 *      - Chain-2 Ω: does Walsh-2 of state_diff correlate with δH_e
 *        MORE for carry-matched pairs?
 *
 * Key insight: we don't need full carry-out match (28 bits = rare).
 * Partial match on a few carry bits creates a gradient.
 * Feature = number of matching carry-out bits (continuous).
 *
 * Actually simpler: compute carry-out overlap between pair members
 * at round 8, use as feature, test if it predicts δH at round 20.
 * v20 says: no (direct). We test: through Walsh-2?
 *
 * Even simpler approach that reuses our infrastructure:
 *   - At round 8: pair has state_diff D8 and known δe_8 (with HW info)
 *   - At round 20: same pair has state_diff D20 and δe_20
 *   - Feature: HW(δe_8) (how close to collision at round 8)
 *   - Target: HW(δe_20) (how close at round 20)
 *   - Question: does Walsh-2 of D8 predict HW(δe_20)?
 *
 * If YES at Walsh-2: the 8-round carry signal persists in Walsh-2
 * form through rounds 8→20, invisible to direct δH measurement.
 *
 * This is the simplest test that directly addresses v20 §218.
 * Run at N=50M in C for definitive answer.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define NBITS 64
#define N_TRAIN 25000000
#define N_TEST  25000000

static const uint32_t K[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))

static void compress_r(const uint32_t bl[16],int nr,uint32_t o[8]){
    uint32_t a=IV[0],b=IV[1],c=IV[2],d=IV[3],e=IV[4],f=IV[5],g=IV[6],h=IV[7],W[64];
    for(int i=0;i<16;i++)W[i]=bl[i];
    for(int i=16;i<nr;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);
        uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<nr;i++){uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+K[i]+W[i];
        uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;}
    o[0]=a+IV[0];o[1]=b+IV[1];o[2]=c+IV[2];o[3]=d+IV[3];
    o[4]=e+IV[4];o[5]=f+IV[5];o[6]=g+IV[6];o[7]=h+IV[7];}

static uint64_t xs[2]={0xDEAD8A1CAFE12345,0xABCD5678FEDCBA90};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}

typedef struct {
    double sum_s, sum_h, sum_sh, sum_s2, sum_h2;
    long count;
} Acc;

static void acc_add(Acc*a, double score, double hw) {
    a->sum_s += score; a->sum_h += hw; a->sum_sh += score*hw;
    a->sum_s2 += score*score; a->sum_h2 += hw*hw; a->count++;
}

static double acc_corr(Acc*a) {
    double ms = a->sum_s / a->count, mh = a->sum_h / a->count;
    double vs = a->sum_s2/a->count - ms*ms, vh = a->sum_h2/a->count - mh*mh;
    double cv = a->sum_sh/a->count - ms*mh;
    return (vs>0 && vh>0) ? cv/sqrt(vs*vh) : 0;
}

int main(void) {
    /* Test multiple (feature_round, target_round) combinations.
     * Feature: Walsh-2 score trained on state_diff at round R_feat
     *          to predict HW(δe) at round R_feat.
     * Target:  HW(δe) at round R_tgt (LATER round).
     *
     * If corr(score_from_R_feat, HW_at_R_tgt) > 0:
     *   → early-round structure predicts later-round proximity.
     *   → carry-signal MIGRATES through Walsh-2 of state_diff.
     */

    int R_feat_list[] = {8, 12};           /* train Walsh-2 score at these rounds */
    int R_tgt_list[]  = {12, 16, 20, 24};  /* predict HW(δe) at these rounds */
    int n_feat = 2, n_tgt = 4;

    uint8_t msg[64]; uint32_t b1[16],b2[16];

    for (int fi = 0; fi < n_feat; fi++) {
        int R_feat = R_feat_list[fi];

        /* TRAIN: build M_in from state_diff at R_feat vs HW(δe) at R_feat */
        fprintf(stderr, "=== Feature round %d ===\n", R_feat);
        fprintf(stderr, "Training on %dM pairs...\n", N_TRAIN/1000000);
        double *YtYf = calloc(NBITS*NBITS, sizeof(double));
        long n_tr = 0;

        for (long i = 0; i < N_TRAIN; i++) {
            fr(msg, 64);
            for(int w=0;w<16;w++) b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
            int j = xr() & 31; uint32_t b2c[16]; memcpy(b2c, b1, 64); b2c[0] ^= (1u<<(31-j));
            uint32_t s1[8], s2[8];
            compress_r(b1, R_feat, s1);
            compress_r(b2c, R_feat, s2);
            uint32_t D[8]; for(int w=0;w<8;w++) D[w]=s1[w]^s2[w];
            int hw_e = __builtin_popcount(D[4]);
            double tgt = hw_e - 16.0;
            int8_t Y[NBITS];
            for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
            for(int a=0;a<NBITS;a++) for(int bb=0;bb<NBITS;bb++) YtYf[a*NBITS+bb]+=(double)Y[a]*Y[bb]*tgt;
            n_tr++;
            if((i+1)%5000000==0) fprintf(stderr,"  %ldM\n",(i+1)/1000000);
        }
        double *M_in = calloc(NBITS*NBITS, sizeof(double));
        double sq = sqrt((double)n_tr);
        for(int i=0;i<NBITS*NBITS;i++) M_in[i] = YtYf[i]/sq;
        double tr_M = 0; for(int i=0;i<NBITS;i++) tr_M += M_in[i*NBITS+i];
        free(YtYf);
        fprintf(stderr, "Trained at r=%d. tr(M)=%.1f\n", R_feat, tr_M);

        /* TEST: for each target round, compute score from R_feat state_diff,
         * correlate with HW(δe) at R_tgt */
        fprintf(stderr, "Testing on %dM pairs...\n", N_TEST/1000000);

        Acc accs[4]; memset(accs, 0, sizeof(accs));
        /* Also track direct cross-round correlation (no Walsh) */
        Acc direct_accs[4]; memset(direct_accs, 0, sizeof(direct_accs));

        for (long i = 0; i < N_TEST; i++) {
            fr(msg, 64);
            for(int w=0;w<16;w++) b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
            int j = xr() & 31; uint32_t b2c[16]; memcpy(b2c, b1, 64); b2c[0] ^= (1u<<(31-j));

            /* Compute state at feature round */
            uint32_t sf1[8], sf2[8];
            compress_r(b1, R_feat, sf1);
            compress_r(b2c, R_feat, sf2);
            uint32_t Df[8]; for(int w=0;w<8;w++) Df[w]=sf1[w]^sf2[w];
            int hw_feat = __builtin_popcount(Df[4]);

            /* Walsh-2 score from feature-round state_diff */
            int8_t Y[NBITS];
            for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((Df[w]>>bit)&1)?1:-1;}
            double Q=0;
            for(int a=0;a<NBITS;a++){double r=0;for(int bb=0;bb<NBITS;bb++)r+=M_in[a*NBITS+bb]*Y[bb];Q+=Y[a]*r;}
            double score = (Q - tr_M) / 2.0;

            /* Compute δe at each target round */
            for (int ti = 0; ti < n_tgt; ti++) {
                int R_tgt = R_tgt_list[ti];
                if (R_tgt <= R_feat) continue;
                uint32_t st1[8], st2[8];
                compress_r(b1, R_tgt, st1);
                compress_r(b2c, R_tgt, st2);
                int hw_tgt = __builtin_popcount(st1[4] ^ st2[4]);
                acc_add(&accs[ti], score, (double)hw_tgt);
                acc_add(&direct_accs[ti], (double)hw_feat, (double)hw_tgt);
            }
            if((i+1)%5000000==0) fprintf(stderr,"  %ldM\n",(i+1)/1000000);
        }
        free(M_in);

        /* Results */
        printf("feature_round=%d\n", R_feat);
        printf("  target_round, walsh2_corr, walsh2_z, direct_corr, direct_z\n");
        for (int ti = 0; ti < n_tgt; ti++) {
            int R_tgt = R_tgt_list[ti];
            if (R_tgt <= R_feat) continue;
            double c_w = acc_corr(&accs[ti]);
            double z_w = c_w * sqrt((double)accs[ti].count - 2);
            double c_d = acc_corr(&direct_accs[ti]);
            double z_d = c_d * sqrt((double)direct_accs[ti].count - 2);
            printf("  r_tgt=%d: walsh2_corr=%+.8f z=%+.2f | direct_corr=%+.8f z=%+.2f | N=%ld\n",
                   R_tgt, c_w, z_w, c_d, z_d, accs[ti].count);
        }
        printf("\n");
    }
    return 0;
}
