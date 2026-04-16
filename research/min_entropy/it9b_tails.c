/* IT-9B: tail analysis — does 98.4% corr translate to extreme HW reduction? */
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
static void compress64(const uint32_t bl[16],uint32_t o[8]){
    uint32_t a=IV[0],b=IV[1],c=IV[2],d=IV[3],e=IV[4],f=IV[5],g=IV[6],h=IV[7],W[64];
    for(int i=0;i<16;i++)W[i]=bl[i];for(int i=16;i<64;i++){uint32_t s0=ROTR(W[i-15],7)^ROTR(W[i-15],18)^(W[i-15]>>3);uint32_t s1=ROTR(W[i-2],17)^ROTR(W[i-2],19)^(W[i-2]>>10);W[i]=W[i-16]+s0+W[i-7]+s1;}
    for(int i=0;i<64;i++){uint32_t T1=h+(ROTR(e,6)^ROTR(e,11)^ROTR(e,25))+((e&f)^((~e)&g))+KK[i]+W[i];uint32_t T2=(ROTR(a,2)^ROTR(a,13)^ROTR(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+T1;d=c;c=b;b=a;a=T1+T2;}
    o[0]=a+IV[0];o[1]=b+IV[1];o[2]=c+IV[2];o[3]=d+IV[3];o[4]=e+IV[4];o[5]=f+IV[5];o[6]=g+IV[6];o[7]=h+IV[7];}
static uint64_t xs[2]={0x7A11256BCAFE001AULL,0xDEAD256BEEF5678ULL};
static inline uint64_t xr(void){uint64_t s1=xs[0],s0=xs[1];xs[0]=s0;s1^=s1<<23;xs[1]=s1^s0^(s1>>17)^(s0>>26);return xs[1]+s0;}
static void fr(uint8_t*b,int n){for(int i=0;i<n;i+=8){uint64_t r=xr();int m=n-i<8?n-i:8;memcpy(b+i,&r,m);}}
static int hw256(const uint32_t s[8]){int c=0;for(int w=0;w<8;w++)c+=__builtin_popcount(s[w]);return c;}

static double *M_in;
static double tr_M;
static float*g_scores;
static int cmp_asc(const void*a,const void*b){int ia=*(const int*)a,ib=*(const int*)b;return(g_scores[ia]>g_scores[ib])-(g_scores[ia]<g_scores[ib]);}


int main(void){
    M_in=calloc(NBITS*NBITS,sizeof(double));
    uint8_t msg[64];uint32_t b1[16],b2[16],s1[8],s2[8];
    int8_t Y[NBITS];

    /* TRAIN on c-world (HW<120) */
    fprintf(stderr,"Training...\n");
    long n_cw=0;
    for(long i=0;i<N_HALF;i++){
        fr(msg,64);
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        compress64(b1,s1);compress64(b2,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        int hw_full=hw256(D);double tgt=hw_full-115.0;
        for(int w=0;w<8;w++)for(int b=0;b<32;b++)Y[w*32+b]=((D[w]>>(31-b))&1)?1:-1;
        for(int a=0;a<NBITS;a++)for(int b=0;b<NBITS;b++)M_in[a*NBITS+b]+=(double)Y[a]*Y[b]*tgt;
        n_cw++;
        if((i+1)%10000000==0)fprintf(stderr,"  %ldM (cw=%ld)\n",(i+1)/1000000,n_cw);
    }
    double sq=sqrt((double)n_cw);
    for(int i=0;i<NBITS*NBITS;i++)M_in[i]/=sq;
    tr_M=0;for(int i=0;i<NBITS;i++)tr_M+=M_in[i*NBITS+i];
    fprintf(stderr,"Trained. n_cw=%ld\n",n_cw);

    /* TEST: collect (score, hw) pairs for sorting */
    #define MAX_TEST 8000000
    float*scores=malloc(MAX_TEST*sizeof(float));
    int16_t*hws=malloc(MAX_TEST*sizeof(int16_t));
    long nt=0;

    fprintf(stderr,"Testing...\n");
    for(long i=0;i<N_HALF;i++){
        fr(msg,64);
        for(int w=0;w<16;w++)b1[w]=((uint32_t)msg[w*4]<<24)|((uint32_t)msg[w*4+1]<<16)|((uint32_t)msg[w*4+2]<<8)|msg[w*4+3];
        int j=xr()&31;memcpy(b2,b1,64);b2[0]^=(1u<<(31-j));
        compress64(b1,s1);compress64(b2,s2);
        uint32_t D[8];for(int w=0;w<8;w++)D[w]=s1[w]^s2[w];
        if(hw256(D)>=120)continue;
        for(int w=0;w<8;w++)for(int b=0;b<32;b++)Y[w*32+b]=((D[w]>>(31-b))&1)?1:-1;
        double Q=0;for(int a=0;a<NBITS;a++){double r=0;for(int b=0;b<NBITS;b++)r+=M_in[a*NBITS+b]*Y[b];Q+=Y[a]*r;}
        double sc=(Q-tr_M)/2.0;
        int hw_full=hw256(D);
        if(nt<MAX_TEST){scores[nt]=(float)sc;hws[nt]=(int16_t)hw_full;nt++;}
        if((i+1)%10000000==0)fprintf(stderr,"  %ldM\n",(i+1)/1000000);
    }
    fprintf(stderr,"Test c-world: %ld pairs\n",nt);

    /* Sort by score ASCENDING (negative corr in some bins → lowest score = lowest HW?) */
    /* Actually IT-9 showed corr=+0.984: HIGH score → HIGH HW. So LOWEST score → LOWEST HW. */
    int*idx=malloc(nt*sizeof(int));
    for(long i=0;i<nt;i++)idx[i]=(int)i;
    /* Sort ascending by score */

    g_scores=scores;qsort(idx,nt,sizeof(int),cmp_asc);

    /* Percentile analysis — LOWEST score = closest to collision */
    double mean_all=0;for(long i=0;i<nt;i++)mean_all+=hws[i];mean_all/=nt;
    printf("=== IT-9B: Tail Analysis ===\n");
    printf("N_test=%ld  mean_hw=%.2f\n\n",nt,mean_all);

    printf("Lowest-score percentiles (best pairs for collision):\n");
    int pcts[]={1,5,10,25,50};
    for(int pi=0;pi<5;pi++){
        long np=nt*pcts[pi]/1000; if(np<1)np=1; /* per-mille for finer resolution */
        double hw_sum=0,hw_min=999,hw_max=0;
        for(long i=0;i<np;i++){
            double h=hws[idx[i]];
            hw_sum+=h; if(h<hw_min)hw_min=h; if(h>hw_max)hw_max=h;
        }
        double hw_mean=hw_sum/np;
        printf("  Bottom %.1f%%: N=%ld mean_hw=%.2f min_hw=%.0f max_hw=%.0f (delta=%.2f bits)\n",
               pcts[pi]/10.0,np,hw_mean,hw_min,hw_max,mean_all-hw_mean);
    }

    /* Count extreme low-HW pairs in bottom percentiles */
    printf("\nExtreme HW counts in bottom 1%% vs random:\n");
    long np1=nt/100;
    int threshs[]={100,90,80,70,60,50,40};
    for(int ti=0;ti<7;ti++){
        int th=threshs[ti];
        long cnt_top=0,cnt_all=0;
        for(long i=0;i<np1;i++) if(hws[idx[i]]<=th)cnt_top++;
        for(long i=0;i<nt;i++) if(hws[i]<=th)cnt_all++;
        double rate_top=(double)cnt_top/np1, rate_all=(double)cnt_all/nt;
        double enrichment=rate_all>0?rate_top/rate_all:0;
        printf("  HW<=%d: bottom1%%=%ld/%ld (%.4f%%) random=%ld/%ld (%.4f%%) enrichment=%.1fx\n",
               th,cnt_top,np1,100.0*rate_top,cnt_all,nt,100.0*rate_all,enrichment);
    }

    /* Absolute minimum HW found */
    printf("\nAbsolute minimum HW in test set: %d (pair index %d)\n",hws[idx[0]],idx[0]);
    printf("Top 10 lowest-HW pairs by score rank:\n");
    for(int i=0;i<10&&i<nt;i++){
        printf("  rank %d: score=%.1f hw=%d\n",i,scores[idx[i]],hws[idx[i]]);
    }

    free(scores);free(hws);free(idx);free(M_in);
    return 0;
}
