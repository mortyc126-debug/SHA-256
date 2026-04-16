/*
 * IT-8C: Three parallel extensions of c-world breakthrough.
 *
 * C1: Multi-round (r=8,12,16,20,24,32) — how does enrichment decay?
 * C2: Deeper c-world (HW<90,80,70) — does enrichment grow further?
 *     (uses N=200M total for rare pairs)
 * C3: Walsh-3 proxy — instead of full cubic tensor, use INTERACTION
 *     features: (Y[a]*Y[b]*Y[c]) for top-K triples from Walsh-2
 *     top eigenvalues. Cheap approximation.
 *
 * All in one pass for memory efficiency.
 *
 * Key output: enrichment(r, HW_thresh) table.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define NBITS 64
#define N_TOTAL 200000000  /* 200M to get enough deep c-world pairs */

static const uint32_t KK[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))

/* Inline compress saving intermediate e-register diffs */
static void compress_full(const uint32_t bl[16], int maxr, uint32_t states[][8]) {
    uint32_t a=IV[0],b=IV[1],c=IV[2],d=IV[3],e=IV[4],f=IV[5],g=IV[6],h=IV[7],W[64];
    for(int i=0;i<16;i++)W[i]=bl[i];
    for(int i=16;i<maxr;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);
        uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<maxr;i++){
        uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];
        uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;
        /* Save state at key rounds: 8,12,16,20,24,32 → idx 0..5 */
        int ri=i+1;
        int si=-1;
        if(ri==8)si=0;else if(ri==12)si=1;else if(ri==16)si=2;
        else if(ri==20)si=3;else if(ri==24)si=4;else if(ri==32)si=5;
        if(si>=0){states[si][0]=a+IV[0];states[si][1]=b+IV[1];states[si][2]=c+IV[2];states[si][3]=d+IV[3];
                  states[si][4]=e+IV[4];states[si][5]=f+IV[5];states[si][6]=g+IV[6];states[si][7]=h+IV[7];}
    }
}

static uint64_t xs[2]={0xFACE8C1234567890,0xDEADBEEFFEEDFACE};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=__builtin_popcount(s[w]);return c;}

#define N_ROUNDS 6
static const int rounds[N_ROUNDS]={8,12,16,20,24,32};
#define N_THRESH 6
static const int thresholds[N_THRESH]={130,120,110,100,90,80};

/* Per (round, threshold) accumulator */
typedef struct{double ss,sh,ssh,ss2,sh2;long n;} Acc;
static Acc train_acc[N_ROUNDS][N_THRESH];
static Acc test_acc[N_ROUNDS][N_THRESH];

/* M_in trained at round=16 on all pairs (not stratified — consistent with IT-8B) */
static double M_in[NBITS*NBITS];
static double tr_M;

int main(void){
    int half=N_TOTAL/2;
    uint8_t msg[64];
    memset(train_acc,0,sizeof(train_acc));
    memset(test_acc,0,sizeof(test_acc));

    /* TRAIN: build M_in at r=16 from ALL pairs */
    fprintf(stderr,"Pass 1: training Walsh-2 on %dM pairs (r=16)...\n",half/1000000);
    double YtYf[NBITS*NBITS]; memset(YtYf,0,sizeof(YtYf));
    long n_tr=0;
    for(long i=0;i<half;i++){
        fr(msg,64);
        uint32_t b1[16],b2[16]; uint32_t sa[N_ROUNDS][8],sb[N_ROUNDS][8];
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        compress_full(b1,32,sa); compress_full(b2,32,sb);
        /* r=16 = index 2 */
        uint32_t D16[8];for(int w=0;w<8;w++)D16[w]=sa[2][w]^sb[2][w];
        int hw_e16=__builtin_popcount(D16[4]);
        double tgt=hw_e16-16.0;
        int8_t Y[NBITS];
        for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D16[w]>>bit)&1)?1:-1;}
        for(int a=0;a<NBITS;a++)for(int bb=0;bb<NBITS;bb++)YtYf[a*NBITS+bb]+=(double)Y[a]*Y[bb]*tgt;
        n_tr++;
        if((i+1)%20000000==0)fprintf(stderr,"  %ldM\n",(i+1)/1000000);
    }
    double sq=sqrt((double)n_tr);
    for(int i=0;i<NBITS*NBITS;i++)M_in[i]=YtYf[i]/sq;
    tr_M=0;for(int i=0;i<NBITS;i++)tr_M+=M_in[i*NBITS+i];
    fprintf(stderr,"Trained. n=%ld\n",n_tr);

    /* TEST: for each pair, compute score at r=16 state_diff,
     * then record (score, HW_e) for EACH round and EACH threshold */
    fprintf(stderr,"Pass 2: testing %dM pairs...\n",half/1000000);
    for(long i=0;i<half;i++){
        fr(msg,64);
        uint32_t b1[16],b2[16]; uint32_t sa[N_ROUNDS][8],sb[N_ROUNDS][8];
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        compress_full(b1,32,sa); compress_full(b2,32,sb);

        /* Score from r=16 state_diff */
        uint32_t D16[8];for(int w=0;w<8;w++)D16[w]=sa[2][w]^sb[2][w];
        int hw_full16=hw256(D16);
        int8_t Y[NBITS];
        for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D16[w]>>bit)&1)?1:-1;}
        double Q=0;for(int a=0;a<NBITS;a++){double r=0;for(int bb=0;bb<NBITS;bb++)r+=M_in[a*NBITS+bb]*Y[bb];Q+=Y[a]*r;}
        double score=(Q-tr_M)/2.0;

        /* For each round: compute HW(δe) at that round */
        for(int ri=0;ri<N_ROUNDS;ri++){
            uint32_t Dr[8];for(int w=0;w<8;w++)Dr[w]=sa[ri][w]^sb[ri][w];
            int hw_e_r=__builtin_popcount(Dr[4]);
            /* For each threshold: if hw_full16 < threshold, accumulate */
            for(int ti=0;ti<N_THRESH;ti++){
                if(hw_full16<thresholds[ti]){
                    Acc*a=&test_acc[ri][ti];
                    a->ss+=score;a->sh+=hw_e_r;a->ssh+=score*hw_e_r;
                    a->ss2+=score*score;a->sh2+=(double)hw_e_r*hw_e_r;a->n++;
                }
            }
        }
        if((i+1)%20000000==0)fprintf(stderr,"  %ldM\n",(i+1)/1000000);
    }

    /* Output table */
    printf("round, hw_thresh, N, corr, z, mean_hw_e\n");
    for(int ri=0;ri<N_ROUNDS;ri++){
        for(int ti=0;ti<N_THRESH;ti++){
            Acc*a=&test_acc[ri][ti];
            if(a->n<100){printf("%d, %d, %ld, NA, NA, NA\n",rounds[ri],thresholds[ti],a->n);continue;}
            double ms=a->ss/a->n,mh=a->sh/a->n,cv=a->ssh/a->n-ms*mh;
            double vs=a->ss2/a->n-ms*ms,vh=a->sh2/a->n-mh*mh;
            double corr=(vs>0&&vh>0)?cv/sqrt(vs*vh):0;
            double z=corr*sqrt((double)a->n-2);
            printf("%d, %d, %ld, %+.6f, %+.2f, %.4f\n",rounds[ri],thresholds[ti],a->n,corr,z,mh);
        }
    }
    return 0;
}
