/*
 * IT-9: Full 256-bit Walsh-2 in c-world at r=64.
 *
 * IT-8D/F used NBITS=64 (first 2 words of state_diff). Now use ALL 256
 * bits = 8 words. M_in becomes 256×256 = 65536 entries.
 *
 * Also: predict EACH of the 8 registers separately and combined,
 * to measure per-register contribution.
 *
 * Train on c-world (HW<120) pairs at r=64.
 * N=50M train + 50M test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define NBITS 256
#define R_COMPUTE 64
#define N_HALF 50000000

static const uint32_t KK[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))
static void compress64(const uint32_t bl[16],uint32_t o[8]){
    uint32_t a=IV[0],b=IV[1],c=IV[2],d=IV[3],e=IV[4],f=IV[5],g=IV[6],h=IV[7],W[64];
    for(int i=0;i<16;i++)W[i]=bl[i];for(int i=16;i<64;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<64;i++){uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;}
    o[0]=a+IV[0];o[1]=b+IV[1];o[2]=c+IV[2];o[3]=d+IV[3];o[4]=e+IV[4];o[5]=f+IV[5];o[6]=g+IV[6];o[7]=h+IV[7];}
static uint64_t xs[2]={0x9F9F256B10000AULL,0xDEAD256BEEF1234ULL};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=__builtin_popcount(s[w]);return c;}

typedef struct{double ss,sh,ssh,ss2,sh2;long n;}Acc;
static void aa(Acc*a,double s,double h){a->ss+=s;a->sh+=h;a->ssh+=s*h;a->ss2+=s*s;a->sh2+=h*h;a->n++;}
static double ac(Acc*a){if(a->n<2)return 0;double ms=a->ss/a->n,mh=a->sh/a->n,cv=a->ssh/a->n-ms*mh,vs=a->ss2/a->n-ms*ms,vh=a->sh2/a->n-mh*mh;return(vs>0&&vh>0)?cv/sqrt(vs*vh):0;}

/* 256×256 M_in matrix — heap allocated */
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

int main(void){
    M_in = calloc(NBITS*NBITS, sizeof(double));
    if(!M_in){fprintf(stderr,"malloc M_in failed\n");return 1;}

    uint8_t msg[64]; uint32_t b1[16],b2[16],s1[8],s2[8];
    int8_t Y[NBITS];

    /* TRAIN: c-world at r=64 using FULL 256-bit state_diff */
    fprintf(stderr,"Training 256-bit Walsh-2 on %dM c-world pairs (r=64)...\n",N_HALF/1000000);
    long n_cw=0;
    for(long i=0;i<N_HALF;i++){
        fr(msg,64);
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        compress64(b1,s1);compress64(b2,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        /* Target: HW of FULL 256-bit diff (not just e-register) */
        int hw_full=hw256(D);
        double tgt=hw_full-128.0; /* centered around full-diff mean in c-world (~115) */
        extract_bits(D, Y);
        for(int a=0;a<NBITS;a++)for(int b=0;b<NBITS;b++)
            M_in[a*NBITS+b]+=(double)Y[a]*Y[b]*tgt;
        n_cw++;
        if((i+1)%10000000==0)fprintf(stderr,"  %ldM (cw=%ld)\n",(i+1)/1000000,n_cw);
    }
    double sq=sqrt((double)n_cw);
    for(int i=0;i<NBITS*NBITS;i++)M_in[i]/=sq;
    tr_M=0;for(int i=0;i<NBITS;i++)tr_M+=M_in[i*NBITS+i];
    fprintf(stderr,"Trained. n_cw=%ld tr(M)=%.1f\n",n_cw,tr_M);

    /* TEST: score c-world pairs, measure correlation with each register + full */
    fprintf(stderr,"Testing %dM pairs...\n",N_HALF/1000000);
    Acc a_full={}, a_regs[8];
    memset(a_regs,0,sizeof(a_regs));

    for(long i=0;i<N_HALF;i++){
        fr(msg,64);
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        compress64(b1,s1);compress64(b2,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        extract_bits(D, Y);
        double sc=score_pair(Y);
        int hw_full=hw256(D);
        aa(&a_full,sc,(double)hw_full);
        for(int r=0;r<8;r++){
            int hw_r=__builtin_popcount(D[r]);
            aa(&a_regs[r],sc,(double)hw_r);
        }
        if((i+1)%10000000==0)fprintf(stderr,"  %ldM\n",(i+1)/1000000);
    }

    printf("=== IT-9: 256-bit Walsh-2, c-world, r=64 ===\n");
    printf("c-world test pairs: %ld\n\n",a_full.n);
    double c_f=ac(&a_full), z_f=c_f*sqrt((double)a_full.n-2);
    printf("Full 256-bit diff: corr=%+.6f z=%+.2f mean_hw=%.2f\n\n",c_f,z_f,a_full.sh/a_full.n);

    printf("Per-register (a,b,c,d,e,f,g,h):\n");
    const char*rnames[]={"a","b","c","d","e","f","g","h"};
    for(int r=0;r<8;r++){
        double c=ac(&a_regs[r]),z=c*sqrt((double)a_regs[r].n-2);
        printf("  %s: corr=%+.6f z=%+.2f mean_hw=%.2f\n",rnames[r],c,z,a_regs[r].sh/a_regs[r].n);
    }

    /* Compare to IT-8F (64-bit, same r=64) */
    printf("\nComparison: IT-8F (64-bit) full256 corr=+0.119 z=+227\n");
    printf("            IT-9  (256-bit) full256 corr=%+.3f z=%+.0f\n",c_f,z_f);
    printf("            Improvement: %.1fx in |corr|\n",fabs(c_f)/0.119);

    free(M_in);
    return 0;
}
