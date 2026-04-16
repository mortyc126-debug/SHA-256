/*
 * IT-9E: Two separate scores for two blocks + combined.
 *
 * Score_1: trained on block-1 state_diff → hash_diff (end-to-end, like IT-9D)
 * Score_2: trained on block-2 INTERMEDIATE diff at round 32 → hash_diff
 * Combined: Score_1 + Score_2 → hash_diff
 *
 * Block 2 intermediate: run padding block with IV=state1_A and IV=state1_B
 * separately, extract state_diff at round 32 of block 2.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#define NBITS 256
#define N_HALF 25000000
static const uint32_t KK[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))
/* Compress with custom IV, return state at round mid AND at round 64 */
static void compress_full_iv(const uint32_t bl[16],const uint32_t iv[8],int mid,uint32_t o_mid[8],uint32_t o_final[8]){
    uint32_t a=iv[0],b=iv[1],c=iv[2],d=iv[3],e=iv[4],f=iv[5],g=iv[6],h=iv[7],W[64];
    for(int i=0;i<16;i++)W[i]=bl[i];for(int i=16;i<64;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<64;i++){uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;
        if(i+1==mid){o_mid[0]=a+iv[0];o_mid[1]=b+iv[1];o_mid[2]=c+iv[2];o_mid[3]=d+iv[3];o_mid[4]=e+iv[4];o_mid[5]=f+iv[5];o_mid[6]=g+iv[6];o_mid[7]=h+iv[7];}}
    o_final[0]=a+iv[0];o_final[1]=b+iv[1];o_final[2]=c+iv[2];o_final[3]=d+iv[3];o_final[4]=e+iv[4];o_final[5]=f+iv[5];o_final[6]=g+iv[6];o_final[7]=h+iv[7];}
static uint64_t xs[2]={0x2B10CC00CAFE01ULL,0xDEAD2B00BEEF02ULL};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=__builtin_popcount(s[w]);return c;}
typedef struct{double ss,sh,ssh,ss2,sh2;long n;}Acc;
static void aa(Acc*a,double s,double h){a->ss+=s;a->sh+=h;a->ssh+=s*h;a->ss2+=s*s;a->sh2+=h*h;a->n++;}
static double ac(Acc*a){if(a->n<2)return 0;double ms=a->ss/a->n,mh=a->sh/a->n,cv=a->ssh/a->n-ms*mh,vs=a->ss2/a->n-ms*ms,vh=a->sh2/a->n-mh*mh;return(vs>0&&vh>0)?cv/sqrt(vs*vh):0;}

static double *M1, *M2; /* 256×256 each */
static double tr1, tr2;
static uint32_t PAD[16];

static double score(const double*M,double tr,const uint32_t D[8]){
    int8_t Y[NBITS];
    for(int w=0;w<8;w++)for(int b=0;b<32;b++)Y[w*32+b]=((D[w]>>(31-b))&1)?1:-1;
    double Q=0;for(int a=0;a<NBITS;a++){double r=0;for(int b=0;b<NBITS;b++)r+=M[a*NBITS+b]*Y[b];Q+=Y[a]*r;}
    return(Q-tr)/2.0;
}

int main(void){
    M1=calloc(NBITS*NBITS,sizeof(double));
    M2=calloc(NBITS*NBITS,sizeof(double));
    PAD[0]=0x80000000;PAD[15]=512;
    uint8_t msg[64];uint32_t b1[16],b2[16];

    /* TRAIN BOTH scores simultaneously */
    fprintf(stderr,"Training Score_1 (block1 diff→hash) and Score_2 (block2_mid diff→hash)...\n");
    long n_cw=0;
    for(long i=0;i<N_HALF;i++){
        fr(msg,64);
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        /* Block 1 */
        uint32_t s1a[8],s1b[8];
        compress_full_iv(b1,IV,32,NULL,s1a); /* don't need mid for block1 */
        /* Oops, NULL for mid crashes. Let me use dummy. */
        uint32_t dummy[8];
        compress_full_iv(b1,IV,32,dummy,s1a);
        compress_full_iv(b2,IV,32,dummy,s1b);
        uint32_t D1[8];for(int w=0;w<8;w++)D1[w]=s1a[w]^s1b[w];
        if(hw256(D1)>=120)continue;
        /* Block 2: padding with IV=state1 */
        uint32_t b2mid_a[8],b2fin_a[8],b2mid_b[8],b2fin_b[8];
        compress_full_iv(PAD,s1a,16,b2mid_a,b2fin_a);
        compress_full_iv(PAD,s1b,16,b2mid_b,b2fin_b);
        uint32_t D2mid[8],Dhash[8];
        for(int w=0;w<8;w++){D2mid[w]=b2mid_a[w]^b2mid_b[w];Dhash[w]=b2fin_a[w]^b2fin_b[w];}
        int hw_hash=hw256(Dhash);
        double tgt=hw_hash-128.0;
        /* Train M1 on block-1 diff features → hash target */
        int8_t Y1[NBITS];
        for(int w=0;w<8;w++)for(int b=0;b<32;b++)Y1[w*32+b]=((D1[w]>>(31-b))&1)?1:-1;
        for(int a=0;a<NBITS;a++)for(int b=0;b<NBITS;b++)M1[a*NBITS+b]+=(double)Y1[a]*Y1[b]*tgt;
        /* Train M2 on block-2 mid diff features → hash target */
        int8_t Y2[NBITS];
        for(int w=0;w<8;w++)for(int b=0;b<32;b++)Y2[w*32+b]=((D2mid[w]>>(31-b))&1)?1:-1;
        for(int a=0;a<NBITS;a++)for(int b=0;b<NBITS;b++)M2[a*NBITS+b]+=(double)Y2[a]*Y2[b]*tgt;
        n_cw++;
        if((i+1)%5000000==0)fprintf(stderr,"  %ldM (cw=%ld)\n",(i+1)/1000000,n_cw);
    }
    double sq=sqrt((double)n_cw);
    for(int i=0;i<NBITS*NBITS;i++){M1[i]/=sq;M2[i]/=sq;}
    tr1=0;tr2=0;for(int i=0;i<NBITS;i++){tr1+=M1[i*NBITS+i];tr2+=M2[i*NBITS+i];}
    fprintf(stderr,"Trained. n_cw=%ld\n",n_cw);

    /* TEST */
    fprintf(stderr,"Testing...\n");
    Acc as1={},as2={},acomb={};
    for(long i=0;i<N_HALF;i++){
        fr(msg,64);
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        uint32_t s1a[8],s1b[8],dummy[8];
        compress_full_iv(b1,IV,32,dummy,s1a);compress_full_iv(b2,IV,32,dummy,s1b);
        uint32_t D1[8];for(int w=0;w<8;w++)D1[w]=s1a[w]^s1b[w];
        if(hw256(D1)>=120)continue;
        uint32_t b2mid_a[8],b2fin_a[8],b2mid_b[8],b2fin_b[8];
        compress_full_iv(PAD,s1a,16,b2mid_a,b2fin_a);
        compress_full_iv(PAD,s1b,16,b2mid_b,b2fin_b);
        uint32_t D2mid[8],Dhash[8];
        for(int w=0;w<8;w++){D2mid[w]=b2mid_a[w]^b2mid_b[w];Dhash[w]=b2fin_a[w]^b2fin_b[w];}
        double sc1=score(M1,tr1,D1);
        double sc2=score(M2,tr2,D2mid);
        int hw_hash=hw256(Dhash);
        aa(&as1,sc1,(double)hw_hash);
        aa(&as2,sc2,(double)hw_hash);
        aa(&acomb,sc1+sc2,(double)hw_hash);
        if((i+1)%5000000==0)fprintf(stderr,"  %ldM\n",(i+1)/1000000);
    }
    printf("=== IT-9E: Two-block scores ===\n");
    printf("c-world test: %ld\n\n",as1.n);
    double c1=ac(&as1),z1=c1*sqrt((double)as1.n-2);
    double c2=ac(&as2),z2=c2*sqrt((double)as2.n-2);
    double cc=ac(&acomb),zc=cc*sqrt((double)acomb.n-2);
    printf("Score_1 (block1 diff) vs hash_diff: corr=%+.8f z=%+.2f\n",c1,z1);
    printf("Score_2 (block2@r16)  vs hash_diff: corr=%+.8f z=%+.2f\n",c2,z2);
    printf("Combined (s1+s2)      vs hash_diff: corr=%+.8f z=%+.2f\n",cc,zc);
    printf("\nmean HW(hash_diff) = %.2f\n",as1.sh/as1.n);
    free(M1);free(M2);
    return 0;
}
