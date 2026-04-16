/* IT-7S: stratified by flip-bit j. Same as IT-7Z100M but 32 separate accumulators. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define ROUNDS 16
#define NBITS 64
#define N_TOTAL 50000000

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
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
};
#define ROTR(x,n) (((x)>>(n))|((x)<<(32-(n))))
#define CH(e,f,g) (((e)&(f))^((~(e))&(g)))
#define MAJ(a,b,c) (((a)&(b))^((a)&(c))^((b)&(c)))
#define EP0(a) (ROTR(a,2)^ROTR(a,13)^ROTR(a,22))
#define EP1(e) (ROTR(e,6)^ROTR(e,11)^ROTR(e,25))

static void compress_r(const uint32_t block[16], int nr, uint32_t out[8]) {
    uint32_t a=IV[0],b=IV[1],c=IV[2],d=IV[3],e=IV[4],f=IV[5],g=IV[6],h=IV[7];
    uint32_t W[64]; for(int i=0;i<16;i++) W[i]=block[i];
    for(int i=16;i<nr;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);
        uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<nr;i++){uint32_t T1=h+EP1(e)+CH(e,f,g)+K[i]+W[i];
        uint32_t T2=EP0(a)+MAJ(a,b,c);h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;}
    out[0]=a+IV[0];out[1]=b+IV[1];out[2]=c+IV[2];out[3]=d+IV[3];
    out[4]=e+IV[4];out[5]=f+IV[5];out[6]=g+IV[6];out[7]=h+IV[7];
}
static uint64_t s[2]={0x1234567890abcdef,0xfedcba0987654321};
static inline uint64_t xr128p(void){uint64_t s1=s[0],s0=s[1];s[0]=s0;
    s1^=s1<<23;s[1]=s1^s0^(s1>>17)^(s0>>26);return s[1]+s0;}
static void fillr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr128p();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}

/* Per-j accumulators */
typedef struct { double sum_s, sum_h, sum_sh, sum_s2, sum_h2; long count; } Acc;

int main(void) {
    /* Train M_in on first half with ALL j mixed */
    double *YtYf = calloc(NBITS*NBITS, sizeof(double));
    long n_tr = 0;
    int half = N_TOTAL/2;
    uint8_t msg[64]; uint32_t b1[16],b2[16],st1[8],st2[8];

    fprintf(stderr,"Training on %dM...\n", half/1000000);
    for(int i=0;i<half;i++){
        fillr(msg,64);
        for(int w=0;w<16;w++) b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|
            ((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr128p()&31; memcpy(b2,b1,64); b2[0]^=(1u<<(31-j));
        compress_r(b1,ROUNDS,st1); compress_r(b2,ROUNDS,st2);
        uint32_t D[8]; for(int w=0;w<8;w++) D[w]=st1[w]^st2[w];
        int hw=__builtin_popcount(D[4]); double tgt=hw-16.0;
        int8_t Y[NBITS];
        for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
        for(int a=0;a<NBITS;a++) for(int bb=0;bb<NBITS;bb++) YtYf[a*NBITS+bb]+=(double)Y[a]*Y[bb]*tgt;
        n_tr++;
        if((i+1)%10000000==0) fprintf(stderr,"  %dM\n",(i+1)/1000000);
    }
    double *M_in=calloc(NBITS*NBITS,sizeof(double));
    double sq=sqrt((double)n_tr);
    for(int i=0;i<NBITS*NBITS;i++) M_in[i]=YtYf[i]/sq;
    double tr_M=0; for(int i=0;i<NBITS;i++) tr_M+=M_in[i*NBITS+i];
    free(YtYf);
    fprintf(stderr,"Trained. tr(M)=%.1f\n",tr_M);

    /* Test: stratified by j */
    Acc acc[32]; memset(acc,0,sizeof(acc));
    fprintf(stderr,"Testing %dM stratified by j...\n",half/1000000);
    for(int i=0;i<half;i++){
        fillr(msg,64);
        for(int w=0;w<16;w++) b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|
            ((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr128p()&31; memcpy(b2,b1,64); b2[0]^=(1u<<(31-j));
        compress_r(b1,ROUNDS,st1); compress_r(b2,ROUNDS,st2);
        uint32_t D[8]; for(int w=0;w<8;w++) D[w]=st1[w]^st2[w];
        int hw=__builtin_popcount(D[4]);
        int8_t Y[NBITS];
        for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
        double Q=0;
        for(int a=0;a<NBITS;a++){double rs=0;for(int bb=0;bb<NBITS;bb++)rs+=M_in[a*NBITS+bb]*Y[bb];Q+=Y[a]*rs;}
        double score=(Q-tr_M)/2.0;
        acc[j].sum_s+=score; acc[j].sum_h+=hw; acc[j].sum_sh+=score*hw;
        acc[j].sum_s2+=score*score; acc[j].sum_h2+=(double)hw*hw; acc[j].count++;
        if((i+1)%10000000==0) fprintf(stderr,"  %dM\n",(i+1)/1000000);
    }
    free(M_in);

    printf("j,count,corr,z,mean_hw\n");
    int n_pos=0,n_neg=0; double max_z=0; int max_j=-1;
    for(int j=0;j<32;j++){
        Acc*a=&acc[j]; double n=a->count;
        double ms=a->sum_s/n, mh=a->sum_h/n;
        double cov=a->sum_sh/n-ms*mh;
        double vs=a->sum_s2/n-ms*ms, vh=a->sum_h2/n-mh*mh;
        double corr=(vs>0&&vh>0)?cov/sqrt(vs*vh):0;
        double z=corr*sqrt(n-2);
        printf("%d,%ld,%.10f,%.4f,%.6f\n",j,a->count,corr,z,mh);
        if(corr>0)n_pos++;else n_neg++;
        if(fabs(z)>fabs(max_z)){max_z=z;max_j=j;}
    }
    fprintf(stderr,"\nSign: %d pos, %d neg. Max |z|=%.2f at j=%d\n",n_pos,n_neg,fabs(max_z),max_j);
    return 0;
}
