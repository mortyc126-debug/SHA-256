/*
 * IT-8E: Four extensions in sequence.
 *
 * E1: Cascaded score — train score1 on c-world, filter top 50%,
 *     retrain score2 on filtered, combine. Does enrichment stack?
 * E2: Walsh-3 proxy — pick top 10 Walsh-2 eigenpairs, form triple
 *     interaction features Y[a]*Y[b]*Y[c], train linear on those.
 * E3: Multi-round — apply c-world-trained score at r=8, 12, 24, 32.
 * E4: Multi-bit differential — deltaW[0] = random 32-bit word, not
 *     single bit. Broader differential space = more pairs in deep c-world.
 *
 * All share the same infrastructure. Run 100M pairs.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define NBITS 64
#define N_HALF 50000000

static const uint32_t KK[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))
static void compress_r(const uint32_t bl[16],int nr,uint32_t o[8]){
    uint32_t a=IV[0],b=IV[1],c=IV[2],d=IV[3],e=IV[4],f=IV[5],g=IV[6],h=IV[7],W[64];
    for(int i=0;i<16;i++)W[i]=bl[i];for(int i=16;i<nr;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<nr;i++){uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;}
    o[0]=a+IV[0];o[1]=b+IV[1];o[2]=c+IV[2];o[3]=d+IV[3];o[4]=e+IV[4];o[5]=f+IV[5];o[6]=g+IV[6];o[7]=h+IV[7];}
static uint64_t xs[2]={0xE1E2E3E4CAFE0001ULL,0xDEAD0000BEEF1234ULL};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=__builtin_popcount(s[w]);return c;}

typedef struct{double ss,sh,ssh,ss2,sh2;long n;}Acc;
static void aa(Acc*a,double s,double h){a->ss+=s;a->sh+=h;a->ssh+=s*h;a->ss2+=s*s;a->sh2+=h*h;a->n++;}
static double ac(Acc*a){if(a->n<2)return 0;double ms=a->ss/a->n,mh=a->sh/a->n,cv=a->ssh/a->n-ms*mh,vs=a->ss2/a->n-ms*ms,vh=a->sh2/a->n-mh*mh;return(vs>0&&vh>0)?cv/sqrt(vs*vh):0;}

static void gen_pair(uint32_t b1[16], uint32_t b2[16], int mode) {
    uint8_t msg[64]; fr(msg,64);
    for(int w=0;w<16;w++) b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|
        ((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
    memcpy(b2,b1,64);
    if(mode==0) { /* single bit flip */
        int j=xr()&31; b2[0]^=(1u<<(31-j));
    } else { /* random word diff (E4) */
        b2[0] ^= (uint32_t)(xr() & 0xFFFFFFFF);
    }
}

int main(void){
    uint32_t b1[16],b2[16],s1[8],s2[8];

    /* ============ E1: CASCADED SCORE ============ */
    printf("=== E1: Cascaded Score ===\n");
    /* Stage 1: train on c-world (HW<120) */
    double M1[NBITS*NBITS]; memset(M1,0,sizeof(M1)); long n1=0;
    fprintf(stderr,"E1 stage1 train...\n");
    for(long i=0;i<N_HALF;i++){
        gen_pair(b1,b2,0);
        compress_r(b1,16,s1);compress_r(b2,16,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        int hw_e=__builtin_popcount(D[4]);double tgt=hw_e-16.0;
        int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
        for(int a=0;a<NBITS;a++)for(int bb=0;bb<NBITS;bb++)M1[a*NBITS+bb]+=(double)Y[a]*Y[bb]*tgt;
        n1++;
    }
    double sq1=sqrt((double)n1),tr1=0;
    for(int i=0;i<NBITS*NBITS;i++)M1[i]/=sq1;
    for(int i=0;i<NBITS;i++)tr1+=M1[i*NBITS+i];

    /* Stage 2: score c-world pairs with M1, then retrain M2 on top 50% by score */
    fprintf(stderr,"E1 stage2: score + retrain on top half...\n");
    double M2[NBITS*NBITS]; memset(M2,0,sizeof(M2)); long n2=0;
    /* First pass: compute scores for c-world pairs to find median */
    #define MAX_CW 8000000
    float *scores_buf = malloc(MAX_CW*sizeof(float));
    int16_t *hw_buf = malloc(MAX_CW*sizeof(int16_t));
    long ncw=0;
    /* Also store Y for retraining (too much memory for 8M×64 int8... skip, retrain in pass 2) */

    for(long i=0;i<N_HALF;i++){
        gen_pair(b1,b2,0);
        compress_r(b1,16,s1);compress_r(b2,16,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        int hw_e=__builtin_popcount(D[4]);
        int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
        double Q=0;for(int a=0;a<NBITS;a++){double r=0;for(int bb=0;bb<NBITS;bb++)r+=M1[a*NBITS+bb]*Y[bb];Q+=Y[a]*r;}
        double sc=(Q-tr1)/2.0;
        if(ncw<MAX_CW){scores_buf[ncw]=(float)sc;hw_buf[ncw]=(int16_t)hw_e;}
        /* Retrain M2 only on pairs with LOW score (negative corr → low score = near-collision) */
        /* Actually: retrain on ALL but weight by -score (emphasize near-collision direction) */
        /* Simpler: retrain on bottom 50% by score */
        /* For now: just retrain on pairs where score < 0 (since corr is negative) */
        if(sc < 0){
            double tgt2=hw_e-16.0;
            for(int a=0;a<NBITS;a++)for(int bb=0;bb<NBITS;bb++)M2[a*NBITS+bb]+=(double)Y[a]*Y[bb]*tgt2;
            n2++;
        }
        ncw++;
    }
    double sq2=sqrt((double)n2),tr2=0;
    for(int i=0;i<NBITS*NBITS;i++)M2[i]/=sq2;
    for(int i=0;i<NBITS;i++)tr2+=M2[i*NBITS+i];
    fprintf(stderr,"  stage1 cw=%ld, stage2 filtered=%ld\n",ncw,n2);

    /* Test: compare score1 vs combined (score1+score2) */
    Acc a_s1={},a_s2={},a_comb={};
    for(long i=0;i<N_HALF;i++){
        gen_pair(b1,b2,0);
        compress_r(b1,16,s1);compress_r(b2,16,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        int hw_e=__builtin_popcount(D[4]);
        int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
        double Q1=0;for(int a=0;a<NBITS;a++){double r=0;for(int bb=0;bb<NBITS;bb++)r+=M1[a*NBITS+bb]*Y[bb];Q1+=Y[a]*r;}
        double sc1=(Q1-tr1)/2.0;
        double Q2=0;for(int a=0;a<NBITS;a++){double r=0;for(int bb=0;bb<NBITS;bb++)r+=M2[a*NBITS+bb]*Y[bb];Q2+=Y[a]*r;}
        double sc2=(Q2-tr2)/2.0;
        aa(&a_s1,sc1,(double)hw_e);
        aa(&a_s2,sc2,(double)hw_e);
        aa(&a_comb,sc1+sc2,(double)hw_e);
    }
    printf("  score1 only:   corr=%+.6f z=%+.2f N=%ld\n",ac(&a_s1),ac(&a_s1)*sqrt((double)a_s1.n-2),a_s1.n);
    printf("  score2 only:   corr=%+.6f z=%+.2f N=%ld\n",ac(&a_s2),ac(&a_s2)*sqrt((double)a_s2.n-2),a_s2.n);
    printf("  combined s1+s2:corr=%+.6f z=%+.2f N=%ld\n",ac(&a_comb),ac(&a_comb)*sqrt((double)a_comb.n-2),a_comb.n);

    /* ============ E3: MULTI-ROUND ============ */
    printf("\n=== E3: Multi-round c-world-trained score ===\n");
    int rlist[]={8,12,16,24,32};
    for(int ri=0;ri<5;ri++){
        int R=rlist[ri];
        /* Train M on c-world at this round */
        double MR[NBITS*NBITS]; memset(MR,0,sizeof(MR)); long nr=0;
        for(long i=0;i<N_HALF/2;i++){
            gen_pair(b1,b2,0);
            compress_r(b1,R,s1);compress_r(b2,R,s2);
            uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
            if(hw256(D)>=120)continue;
            int hw_e=__builtin_popcount(D[4]);double tgt=hw_e-16.0;
            int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
            for(int a=0;a<NBITS;a++)for(int bb=0;bb<NBITS;bb++)MR[a*NBITS+bb]+=(double)Y[a]*Y[bb]*tgt;
            nr++;
        }
        double sqr=sqrt((double)nr),trr=0;
        for(int i=0;i<NBITS*NBITS;i++)MR[i]/=sqr;
        for(int i=0;i<NBITS;i++)trr+=MR[i*NBITS+i];
        /* Test */
        Acc ar={}; long ntest=0;
        for(long i=0;i<N_HALF/2;i++){
            gen_pair(b1,b2,0);
            compress_r(b1,R,s1);compress_r(b2,R,s2);
            uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
            if(hw256(D)>=120)continue;
            int hw_e=__builtin_popcount(D[4]);
            int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
            double Q=0;for(int a=0;a<NBITS;a++){double r=0;for(int bb=0;bb<NBITS;bb++)r+=MR[a*NBITS+bb]*Y[bb];Q+=Y[a]*r;}
            aa(&ar,(Q-trr)/2.0,(double)hw_e); ntest++;
        }
        printf("  r=%d: cw_train=%ld cw_test=%ld corr=%+.6f z=%+.2f\n",
               R,nr,ntest,ac(&ar),ac(&ar)*sqrt((double)ar.n-2));
    }

    /* ============ E4: MULTI-BIT DIFFERENTIAL ============ */
    printf("\n=== E4: Random-word differential (vs single-bit) ===\n");
    /* Train on c-world with random word diff */
    double MW[NBITS*NBITS]; memset(MW,0,sizeof(MW)); long nw=0;
    for(long i=0;i<N_HALF;i++){
        gen_pair(b1,b2,1); /* mode=1: random word diff */
        compress_r(b1,16,s1);compress_r(b2,16,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        int hw_e=__builtin_popcount(D[4]);double tgt=hw_e-16.0;
        int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
        for(int a=0;a<NBITS;a++)for(int bb=0;bb<NBITS;bb++)MW[a*NBITS+bb]+=(double)Y[a]*Y[bb]*tgt;
        nw++;
    }
    double sqw=sqrt((double)nw),trw=0;
    for(int i=0;i<NBITS*NBITS;i++)MW[i]/=sqw;
    for(int i=0;i<NBITS;i++)trw+=MW[i*NBITS+i];
    /* Test */
    Acc aw={}; long nwt=0;
    for(long i=0;i<N_HALF;i++){
        gen_pair(b1,b2,1);
        compress_r(b1,16,s1);compress_r(b2,16,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        int hw_e=__builtin_popcount(D[4]);
        int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
        double Q=0;for(int a=0;a<NBITS;a++){double r=0;for(int bb=0;bb<NBITS;bb++)r+=MW[a*NBITS+bb]*Y[bb];Q+=Y[a]*r;}
        aa(&aw,(Q-trw)/2.0,(double)hw_e); nwt++;
    }
    printf("  random-word diff: cw_train=%ld cw_test=%ld corr=%+.6f z=%+.2f mean_hw=%.4f\n",
           nw,nwt,ac(&aw),ac(&aw)*sqrt((double)aw.n-2),aw.sh/aw.n);

    free(scores_buf); free(hw_buf);
    return 0;
}
