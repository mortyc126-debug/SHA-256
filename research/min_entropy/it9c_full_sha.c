/*
 * IT-9C: Does c-world Walsh-2 score work on FULL SHA-256 (2 blocks)?
 *
 * Block 1: message. Block 2: padding (0x80 || zeros || length).
 * Score trained on block-1 state_diff, tested against FULL SHA-256
 * hash diff = final output after both blocks.
 *
 * If score predicts HW(hash_diff) → structure survives block 2.
 * If not → block 2 destroys c-world advantage.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#define NBITS 256
#define N_HALF 50000000
static const uint32_t KK[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))

static void compress_block(const uint32_t bl[16], const uint32_t iv[8], uint32_t o[8]){
    uint32_t a=iv[0],b=iv[1],c=iv[2],d=iv[3],e=iv[4],f=iv[5],g=iv[6],h=iv[7],W[64];
    for(int i=0;i<16;i++)W[i]=bl[i];
    for(int i=16;i<64;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);
        uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<64;i++){uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];
        uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;}
    o[0]=a+iv[0];o[1]=b+iv[1];o[2]=c+iv[2];o[3]=d+iv[3];
    o[4]=e+iv[4];o[5]=f+iv[5];o[6]=g+iv[6];o[7]=h+iv[7];
}

/* Full SHA-256 on 64-byte message: block1(msg) then block2(padding) */
static void sha256_full(const uint32_t msg[16], uint32_t hash[8]){
    uint32_t state1[8];
    compress_block(msg, IV, state1);
    /* Padding block for 64-byte (512-bit) message */
    uint32_t pad[16]={0};
    pad[0]=0x80000000; /* 0x80 in first byte, rest zeros */
    pad[15]=512;       /* length in bits, big-endian in last word */
    compress_block(pad, state1, hash);
}

static uint64_t xs[2]={0xF011A256CAFE01ULL, 0xDEAD2B10CCBEE0ULL};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=__builtin_popcount(s[w]);return c;}

typedef struct{double ss,sh,ssh,ss2,sh2;long n;}Acc;
static void aa(Acc*a,double s,double h){a->ss+=s;a->sh+=h;a->ssh+=s*h;a->ss2+=s*s;a->sh2+=h*h;a->n++;}
static double ac(Acc*a){if(a->n<2)return 0;double ms=a->ss/a->n,mh=a->sh/a->n,cv=a->ssh/a->n-ms*mh,vs=a->ss2/a->n-ms*ms,vh=a->sh2/a->n-mh*mh;return(vs>0&&vh>0)?cv/sqrt(vs*vh):0;}

static double *M_in;
static double tr_M;

int main(void){
    M_in=calloc(NBITS*NBITS,sizeof(double));
    uint8_t msg[64];uint32_t b1[16],b2[16],s1[8],s2[8];
    int8_t Y[NBITS];

    /* TRAIN on block-1 state_diff (same as IT-9) */
    fprintf(stderr,"Training on block-1 c-world state_diff...\n");
    long n_cw=0;
    for(long i=0;i<N_HALF;i++){
        fr(msg,64);
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        compress_block(b1,IV,s1);compress_block(b2,IV,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        int hwf=hw256(D);double tgt=hwf-115.0;
        for(int w=0;w<8;w++)for(int b=0;b<32;b++)Y[w*32+b]=((D[w]>>(31-b))&1)?1:-1;
        for(int a=0;a<NBITS;a++)for(int b=0;b<NBITS;b++)M_in[a*NBITS+b]+=(double)Y[a]*Y[b]*tgt;
        n_cw++;
        if((i+1)%10000000==0)fprintf(stderr,"  %ldM (cw=%ld)\n",(i+1)/1000000,n_cw);
    }
    double sq=sqrt((double)n_cw);
    for(int i=0;i<NBITS*NBITS;i++)M_in[i]/=sq;
    tr_M=0;for(int i=0;i<NBITS;i++)tr_M+=M_in[i*NBITS+i];
    fprintf(stderr,"Trained. n_cw=%ld\n",n_cw);

    /* TEST: score from block-1 state_diff, but target = FULL SHA-256 hash diff */
    fprintf(stderr,"Testing: score(block1_diff) vs HW(hash_diff)...\n");
    Acc a_b1={}, a_hash={};

    for(long i=0;i<N_HALF;i++){
        fr(msg,64);
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));

        /* Block 1 state diff (for score computation) */
        compress_block(b1,IV,s1);compress_block(b2,IV,s2);
        uint32_t D1[8];for(int w=0;w<8;w++)D1[w]=s1[w]^s2[w];
        if(hw256(D1)>=120)continue;

        /* Score from block-1 diff */
        for(int w=0;w<8;w++)for(int b=0;b<32;b++)Y[w*32+b]=((D1[w]>>(31-b))&1)?1:-1;
        double Q=0;for(int a=0;a<NBITS;a++){double r=0;for(int b=0;b<NBITS;b++)r+=M_in[a*NBITS+b]*Y[b];Q+=Y[a]*r;}
        double sc=(Q-tr_M)/2.0;

        /* Block-1 diff HW */
        int hw_b1=hw256(D1);
        aa(&a_b1,sc,(double)hw_b1);

        /* Full SHA-256 hash diff */
        uint32_t h1[8],h2[8];
        sha256_full(b1,h1);sha256_full(b2,h2);
        uint32_t Dh[8];for(int w=0;w<8;w++)Dh[w]=h1[w]^h2[w];
        int hw_hash=hw256(Dh);
        aa(&a_hash,sc,(double)hw_hash);

        if((i+1)%10000000==0)fprintf(stderr,"  %ldM\n",(i+1)/1000000);
    }

    printf("=== IT-9C: Full SHA-256 (2 blocks) ===\n");
    printf("c-world test pairs: %ld\n\n",a_hash.n);

    double c_b1=ac(&a_b1),z_b1=c_b1*sqrt((double)a_b1.n-2);
    double c_h=ac(&a_hash),z_h=c_h*sqrt((double)a_hash.n-2);

    printf("Score vs block-1 diff HW:   corr=%+.6f z=%+.2f mean=%.2f\n",c_b1,z_b1,a_b1.sh/a_b1.n);
    printf("Score vs FULL HASH diff HW: corr=%+.6f z=%+.2f mean=%.2f\n",c_h,z_h,a_hash.sh/a_hash.n);
    printf("\nIf hash corr ≈ block1 corr → block 2 preserves structure.\n");
    printf("If hash corr ≈ 0 → block 2 destroys c-world advantage.\n");

    free(M_in);
    return 0;
}
