/*
 * IT-10: Round-by-round signal fade through block 2.
 *
 * Idea (from methodology_v20 §4 Zone C invertibility + IT-9 +830σ block-1 signal):
 *   If signal dies monotonically through block-2 rounds, find last round r* where
 *   corr(state_diff[r*], hash_diff) is still measurable. That r* tells us how many
 *   rounds of block 2 we need to skip via Zone C backward inversion (up to 15 free).
 *
 * Experiment:
 *   N random pairs (m, m⊕e_singlebit), where e_j random bit of W[0].
 *   Block 1: full 64 rounds → state1_A, state1_B (our IT-9 +830σ region)
 *   Block 2: r_max=64 rounds with padding W, starting IV = state1
 *     Sample state_diff at intermediate rounds R_LIST
 *   Also: HW(hash_diff) = target (= what MITM would match)
 *
 * Measurements per r:
 *   mean_hw_diff[r]       — mean HW(state_diff at round r)
 *   corr(HW_r, HW_hash)   — linear predictivity of hash from mid-state
 *   enrichment bottom-1%  — do low-HW@r pairs give low-HW hash?
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define N_PAIRS 2000000

static const uint32_t KK[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))

/* compress block bl with initial state iv; return state at every round in states[65][8] (states[0]=iv, states[r]=after r rounds, without feed-forward) */
static void compress_all(const uint32_t bl[16], const uint32_t iv[8], uint32_t states[65][8]) {
    uint32_t a=iv[0],b=iv[1],c=iv[2],d=iv[3],e=iv[4],f=iv[5],g=iv[6],h=iv[7],W[64];
    for(int i=0;i<16;i++) W[i]=bl[i];
    for(int i=16;i<64;i++){
        uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);
        uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);
        W[i]=W[i-16]+s0+W[i-7]+s1;
    }
    states[0][0]=a;states[0][1]=b;states[0][2]=c;states[0][3]=d;
    states[0][4]=e;states[0][5]=f;states[0][6]=g;states[0][7]=h;
    for(int i=0;i<64;i++){
        uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];
        uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;
        states[i+1][0]=a;states[i+1][1]=b;states[i+1][2]=c;states[i+1][3]=d;
        states[i+1][4]=e;states[i+1][5]=f;states[i+1][6]=g;states[i+1][7]=h;
    }
}

/* fast full block1 + block2, return all intermediate states of block2 at all rounds 0..64 (inner, before feed-forward) */
static void compress_block1(const uint32_t bl[16], const uint32_t iv[8], uint32_t out[8]) {
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

static uint64_t xs[2]={0x10A11EB00CAFE01DULL, 0xDEAD10A1BEEF1234ULL};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int popc32(uint32_t x){return __builtin_popcount(x);}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=popc32(s[w]);return c;}
static int hwXOR(const uint32_t A[8], const uint32_t B[8]){int c=0;for(int w=0;w<8;w++)c+=popc32(A[w]^B[w]);return c;}

#define N_ROUNDS_SAMPLE 17
static const int R_LIST[N_ROUNDS_SAMPLE] = {1,2,4,8,12,16,20,24,28,32,40,48,52,56,60,62,64};

typedef struct{double ss,sh,ssh,ss2,sh2;long n;} Acc;
static void aa(Acc*a,double s,double h){a->ss+=s;a->sh+=h;a->ssh+=s*h;a->ss2+=s*s;a->sh2+=h*h;a->n++;}
static double corr(Acc*a){if(a->n<2)return 0;double ms=a->ss/a->n,mh=a->sh/a->n;double cv=a->ssh/a->n-ms*mh;double vs=a->ss2/a->n-ms*ms,vh=a->sh2/a->n-mh*mh;return(vs>0&&vh>0)?cv/sqrt(vs*vh):0;}

int main(void){
    uint32_t PAD[16]={0};
    PAD[0]=0x80000000;
    PAD[15]=512;

    /* Per-round accumulators: corr(HW_mid[r], HW_hash), mean HW_mid, mean HW_hash */
    Acc acc_corr[N_ROUNDS_SAMPLE];
    memset(acc_corr,0,sizeof(acc_corr));
    double sum_hw_mid[N_ROUNDS_SAMPLE]={0};

    /* Also: track HW histograms of state_diff at r=16 (IT-7v2 control) vs r=32 vs r=48 */
    long hw_mid_hist[N_ROUNDS_SAMPLE][257]; /* HW can be 0..256 */
    memset(hw_mid_hist,0,sizeof(hw_mid_hist));
    long hw_hash_hist[257]={0};

    /* For bottom-1% by mid_HW[r], measure hash HW mean */
    /* Use streaming rank: approximate via threshold: count pairs with HW_mid[r] <= T_r */
    /* Simpler: after run, for each r, sort by HW_mid[r] — but that's O(N log N). Use hist. */

    uint8_t msg[64]; uint32_t b1_A[16],b1_B[16];
    uint32_t s1_A[8],s1_B[8];
    uint32_t states_A[65][8], states_B[65][8];
    uint32_t hash_A[8],hash_B[8];

    fprintf(stderr,"IT-10: fade scan through block 2, N=%d pairs\n",N_PAIRS);

    for(long p=0;p<N_PAIRS;p++){
        fr(msg,64);
        for(int w=0;w<16;w++)
            b1_A[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        memcpy(b1_B,b1_A,64);
        int j=xr()&511; /* random bit flip across 512 input bits */
        b1_B[j>>5] ^= (1u<<(31-(j&31)));

        /* Block 1 */
        compress_block1(b1_A,IV,s1_A);
        compress_block1(b1_B,IV,s1_B);

        /* Block 2 with padding, all-round trace */
        compress_all(PAD, s1_A, states_A);
        compress_all(PAD, s1_B, states_B);

        /* Final hash = states[64] + s1 (feed-forward) */
        for(int w=0;w<8;w++){hash_A[w]=states_A[64][w]+s1_A[w];hash_B[w]=states_B[64][w]+s1_B[w];}
        int hw_hash = hwXOR(hash_A,hash_B);
        hw_hash_hist[hw_hash]++;

        /* For each sampled round r of block 2, measure mid-state diff */
        for(int ri=0;ri<N_ROUNDS_SAMPLE;ri++){
            int r = R_LIST[ri];
            int hw_mid = hwXOR(states_A[r], states_B[r]);
            hw_mid_hist[ri][hw_mid]++;
            sum_hw_mid[ri] += hw_mid;
            aa(&acc_corr[ri], (double)hw_mid, (double)hw_hash);
        }

        if((p+1)%500000==0) fprintf(stderr,"  %ld/%d\n",p+1,N_PAIRS);
    }

    /* Results */
    printf("=== IT-10: Block-2 round-by-round fade ===\n");
    printf("N pairs: %d (random bit flip in 512-bit block 1 msg)\n\n", N_PAIRS);

    double mean_hash=0; long n=0;
    for(int h=0;h<=256;h++){mean_hash+=h*hw_hash_hist[h];n+=hw_hash_hist[h];}
    mean_hash/=n;
    printf("Hash diff: mean HW = %.3f (expected ~128 for random)\n\n", mean_hash);

    printf("%3s %12s %10s %10s %7s %10s\n","r","mean_hw_mid","std","corr_hash","z","enrich_b1%");
    for(int ri=0;ri<N_ROUNDS_SAMPLE;ri++){
        int r=R_LIST[ri];
        double mean_m = sum_hw_mid[ri]/N_PAIRS;
        /* std from hist */
        double var=0;
        for(int h=0;h<=256;h++){double d=h-mean_m;var += d*d*hw_mid_hist[ri][h];}
        var/=N_PAIRS;
        double std=sqrt(var);
        double c = corr(&acc_corr[ri]);
        double z = c*sqrt((double)acc_corr[ri].n-2);

        /* Enrichment: find threshold T at bottom 1% by cumulative hist, then compute mean hash HW in that bucket */
        long cumul=0; long target=N_PAIRS/100;
        int T=0;
        for(int h=0;h<=256;h++){cumul+=hw_mid_hist[ri][h]; if(cumul>=target){T=h;break;}}
        /* Need pair-level data to know hash HW for those pairs; skipped: just report T (bottom-1% threshold). */
        /* We'll approximate enrichment via corr magnitude (strong corr ⇒ low-HW-mid pairs concentrate at low-HW-hash). */
        /* For now report threshold. */
        printf("%3d %12.3f %10.3f %+10.6f %+7.2f %10d\n", r, mean_m, std, c, z, T);
    }

    /* Explicit signature: we want to see corr magnitude decay vs round */
    printf("\n--- Fade curve (|corr| vs r) ---\n");
    for(int ri=0;ri<N_ROUNDS_SAMPLE;ri++){
        int r=R_LIST[ri];
        double c=corr(&acc_corr[ri]);
        int bar=(int)(fabs(c)*100.0);
        if(bar>60)bar=60;
        printf("r=%3d  %+.6f  ", r, c);
        for(int i=0;i<bar;i++)putchar('#');
        putchar('\n');
    }

    /* Last-surviving-round estimate: max r where |z|>5 */
    int r_last = -1;
    for(int ri=0;ri<N_ROUNDS_SAMPLE;ri++){
        double c=corr(&acc_corr[ri]);
        double z=c*sqrt((double)acc_corr[ri].n-2);
        if(fabs(z)>5.0) r_last = R_LIST[ri];
    }
    printf("\nLast round with |z|>5 for HW-HW corr: r = %d\n", r_last);
    printf("Implication: MITM meet-point should be at r ≈ %d (or earlier)\n", r_last>0?r_last:0);
    printf("Zone C (§4 v20) gives free O(1) inversion for r=49..63 (15 rounds)\n");
    printf("Required barrier zone: rounds [%d, 48] via algebraic/MITM\n", r_last>0?r_last+1:1);

    return 0;
}
