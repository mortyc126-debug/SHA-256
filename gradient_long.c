/*
 * LONG GRADIENT: Give it ENOUGH steps. Does it converge?
 * ═══════════════════════════════════════════════════════
 *
 * Bug was: 50K steps not enough. |grad| still nonzero.
 * Fix: 500K, 1M, 5M steps. Track convergence curve.
 *
 * Also: ADAM optimizer (adaptive per-var lr) — much faster convergence.
 *
 * Compile: gcc -O3 -march=native -o grad_long gradient_long.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      1000
#define MAX_CLAUSES 5000
#define MAX_K      3

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);rng_seed(seed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;}}}

static int eval_disc(const int *a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static double x[MAX_N];

static void compute_grad(double *grad){
    int n=n_vars;memset(grad,0,sizeof(double)*n);
    for(int ci=0;ci<n_clauses;ci++){
        double lit[3],prod=1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            lit[j]=(s==1)?x[v]:(1-x[v]);double t=1-lit[j];if(t<1e-15)t=1e-15;prod*=t;}
        if(prod<1e-15)continue;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            double t=1-lit[j];if(t<1e-15)t=1e-15;grad[v]+=s*(prod/t);}}}

int main(void){
    printf("════════════════════════════════════════\n");
    printf("LONG GRADIENT + ADAM: Convergence test\n");
    printf("════════════════════════════════════════\n\n");

    int test_n[]={50, 100, 200, 300};

    for(int ti=0;ti<4;ti++){
        int nn=test_n[ti]; int m;
        int s_plain=0, s_adam=0, total=0;

        for(int seed=0;seed<5;seed++){
            generate(nn,4.267,63000000ULL+seed);
            m=n_clauses; int n=nn;

            printf("n=%d seed=%d:\n",nn,seed);

            /* ═══ METHOD 1: Plain gradient, MANY steps ═══ */
            rng_seed(seed*111);
            for(int v=0;v<n;v++) x[v]=0.3+0.4*((rng_next()%10000)/10000.0);

            double lr=0.01;
            int checkpoints[]={1000,5000,10000,50000,100000,500000,1000000};
            int nc=7;
            int ci_done=0;

            printf("  Plain gradient (lr=0.01):\n");
            printf("  %8s | %5s | %6s | %8s\n","steps","unsat","middle","|grad|");
            printf("  ---------+-------+--------+---------\n");

            for(int step=0;step<1000001;step++){
                double grad[MAX_N]; compute_grad(grad);
                for(int v=0;v<n;v++){x[v]+=lr*grad[v];
                    if(x[v]<0)x[v]=0;if(x[v]>1)x[v]=1;}

                if(ci_done<nc && step+1==checkpoints[ci_done]){
                    int a[MAX_N];for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
                    int disc=eval_disc(a);
                    int mid=0;for(int v=0;v<n;v++)if(x[v]>0.1&&x[v]<0.9)mid++;
                    double gnorm=0;for(int v=0;v<n;v++)gnorm+=grad[v]*grad[v];gnorm=sqrt(gnorm);
                    printf("  %8d | %5d | %6d | %8.2f%s\n",
                           step+1,m-disc,mid,gnorm,disc==m?" ★ SOLVED":"");
                    if(disc==m){s_plain++;break;}
                    ci_done++;
                }
            }

            /* ═══ METHOD 2: ADAM optimizer ═══ */
            rng_seed(seed*111);
            for(int v=0;v<n;v++) x[v]=0.3+0.4*((rng_next()%10000)/10000.0);

            double m_adam[MAX_N],v_adam[MAX_N]; /* ADAM state */
            memset(m_adam,0,sizeof(double)*n);
            memset(v_adam,0,sizeof(double)*n);
            double beta1=0.9,beta2=0.999,eps_adam=1e-8;
            double adam_lr=0.001;

            ci_done=0;
            printf("  ADAM optimizer (lr=0.001):\n");
            printf("  %8s | %5s | %6s | %8s\n","steps","unsat","middle","|grad|");
            printf("  ---------+-------+--------+---------\n");

            for(int step=0;step<1000001;step++){
                double grad[MAX_N]; compute_grad(grad);

                /* ADAM update */
                double gnorm=0;
                for(int v=0;v<n;v++){
                    m_adam[v]=beta1*m_adam[v]+(1-beta1)*grad[v];
                    v_adam[v]=beta2*v_adam[v]+(1-beta2)*grad[v]*grad[v];
                    double m_hat=m_adam[v]/(1-pow(beta1,step+1));
                    double v_hat=v_adam[v]/(1-pow(beta2,step+1));
                    double update=adam_lr*m_hat/(sqrt(v_hat)+eps_adam);
                    x[v]+=update;
                    if(x[v]<0)x[v]=0;if(x[v]>1)x[v]=1;
                    gnorm+=grad[v]*grad[v];}
                gnorm=sqrt(gnorm);

                if(ci_done<nc && step+1==checkpoints[ci_done]){
                    int a[MAX_N];for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
                    int disc=eval_disc(a);
                    int mid=0;for(int v=0;v<n;v++)if(x[v]>0.1&&x[v]<0.9)mid++;
                    printf("  %8d | %5d | %6d | %8.2f%s\n",
                           step+1,m-disc,mid,gnorm,disc==m?" ★ SOLVED":"");
                    if(disc==m){s_adam++;break;}
                    ci_done++;
                }
            }

            printf("\n");
            total++;
        }

        printf("n=%d: plain=%d/%d, ADAM=%d/%d\n\n",nn,s_plain,total,s_adam,total);
    }
    return 0;
}
