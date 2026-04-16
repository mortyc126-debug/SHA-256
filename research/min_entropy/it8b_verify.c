/* Quick verification: IT-8B exact setup (5-bin stratification) with 3 seeds */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#define NBITS 64
#define R_COMPUTE 16
#define N_HALF 25000000
static const uint32_t KK[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const uint32_t IV[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
#define ROTR(x,n)(((x)>>(n))|((x)<<(32-(n))))
static void compress_r(const uint32_t bl[16],int nr,uint32_t o[8]){
    uint32_t a=IV[0],b=IV[1],c=IV[2],d=IV[3],e=IV[4],f=IV[5],g=IV[6],h=IV[7],W[64];
    for(int i=0;i<16;i++)W[i]=bl[i];for(int i=16;i<nr;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<nr;i++){uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;}
    o[0]=a+IV[0];o[1]=b+IV[1];o[2]=c+IV[2];o[3]=d+IV[3];o[4]=e+IV[4];o[5]=f+IV[5];o[6]=g+IV[6];o[7]=h+IV[7];}
static uint64_t xs[2];
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=__builtin_popcount(s[w]);return c;}
typedef struct{double ss,sh,ssh,ss2,sh2;long n;}Acc;
static void aa(Acc*a,double s,double h){a->ss+=s;a->sh+=h;a->ssh+=s*h;a->ss2+=s*s;a->sh2+=h*h;a->n++;}
static double ac(Acc*a){double ms=a->ss/a->n,mh=a->sh/a->n,cv=a->ssh/a->n-ms*mh,vs=a->ss2/a->n-ms*ms,vh=a->sh2/a->n-mh*mh;return(vs>0&&vh>0)?cv/sqrt(vs*vh):0;}

int main(void){
    uint64_t seeds[][2]={{0x8BCDEF0123456789ULL,0xFEDCBA9876543210ULL},
                         {0x1111111122222222ULL,0x3333333344444444ULL},
                         {0xAAAABBBBCCCCDDDDULL,0xEEEEFFFF00001111ULL}};
    int bounds[]={0,120,125,131,136,257};
    uint8_t msg[64];

    for(int si=0;si<3;si++){
        xs[0]=seeds[si][0];xs[1]=seeds[si][1];
        printf("Seed %d:\n",si);
        /* Train */
        double YtYf[NBITS*NBITS];memset(YtYf,0,sizeof(YtYf));long ntr=0;
        for(long i=0;i<N_HALF;i++){
            fr(msg,64);uint32_t b1[16],b2[16],s1[8],s2[8];
            for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
            int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
            compress_r(b1,R_COMPUTE,s1);compress_r(b2,R_COMPUTE,s2);
            uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
            int hw_e=__builtin_popcount(D[4]);double tgt=hw_e-16.0;
            int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
            for(int a=0;a<NBITS;a++)for(int bb=0;bb<NBITS;bb++)YtYf[a*NBITS+bb]+=(double)Y[a]*Y[bb]*tgt;
            ntr++;
        }
        double M[NBITS*NBITS];double sq=sqrt((double)ntr);
        for(int i=0;i<NBITS*NBITS;i++)M[i]=YtYf[i]/sq;
        double trM=0;for(int i=0;i<NBITS;i++)trM+=M[i*NBITS+i];

        /* Test with 5-bin stratification */
        Acc acc[5];memset(acc,0,sizeof(acc));
        for(long i=0;i<N_HALF;i++){
            fr(msg,64);uint32_t b1[16],b2[16],s1[8],s2[8];
            for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
            int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
            compress_r(b1,R_COMPUTE,s1);compress_r(b2,R_COMPUTE,s2);
            uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
            int hw_e=__builtin_popcount(D[4]);int hwf=hw256(D);
            int8_t Y[NBITS];for(int bb=0;bb<NBITS;bb++){int w=bb/32,bit=31-(bb%32);Y[bb]=((D[w]>>bit)&1)?1:-1;}
            double Q=0;for(int a=0;a<NBITS;a++){double r=0;for(int bb=0;bb<NBITS;bb++)r+=M[a*NBITS+bb]*Y[bb];Q+=Y[a]*r;}
            double score=(Q-trM)/2.0;
            for(int bi=0;bi<5;bi++)if(hwf>=bounds[bi]&&hwf<bounds[bi+1]){aa(&acc[bi],score,(double)hw_e);break;}
        }
        for(int bi=0;bi<5;bi++){
            double c=ac(&acc[bi]);double z=c*sqrt((double)acc[bi].n-2);
            printf("  [%d,%d): N=%ld corr=%+.6f z=%+.2f hw=%.2f\n",
                   bounds[bi],bounds[bi+1],acc[bi].n,c,z,acc[bi].sh/acc[bi].n);
        }
    }
    return 0;
}
