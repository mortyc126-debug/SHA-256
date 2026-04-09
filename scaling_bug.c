/*
 * SCALING BUG: What EXACTLY breaks between n=16 and n=100?
 * ════════════════════════════════════════════════════════
 *
 * At n=16: gradient from random → 100% solved (in original test)
 * At n=100: 0% solved.
 *
 * Possible bugs:
 * A. Learning rate too large/small for larger n
 * B. Not enough steps (need more iterations)
 * C. Gradient becomes ZERO before reaching solution (stuck)
 * D. Local maxima appear at n>16
 * E. Soft_sat landscape CHANGES qualitatively with n
 *
 * Test each hypothesis systematically.
 *
 * Compile: gcc -O3 -march=native -o scbug scaling_bug.c -lm
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

static double compute_soft_and_grad(double *grad){
    int n=n_vars,m=n_clauses;
    if(grad) memset(grad,0,sizeof(double)*n);
    double total=0;
    for(int ci=0;ci<m;ci++){
        double lit[3],prod=1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            lit[j]=(s==1)?x[v]:(1-x[v]);
            double t=1-lit[j];if(t<1e-15)t=1e-15;prod*=t;}
        total+=(1-prod);
        if(grad){for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            double t=1-lit[j];if(t<1e-15)t=1e-15;
            grad[v]+=s*(prod/t);}}}
    return total;}

int main(void){
    printf("═══════════════════════════════\n");
    printf("SCALING BUG HUNT\n");
    printf("═══════════════════════════════\n\n");

    int test_n[]={16, 30, 50, 100, 200};

    for(int ti=0;ti<5;ti++){
        int nn=test_n[ti];

        for(int seed=0;seed<5;seed++){
            generate(nn,4.267,62000000ULL+seed);
            int n=nn,m=n_clauses;

            /* Start from center */
            rng_seed(seed*111);
            for(int v=0;v<n;v++) x[v]=0.3+0.4*((rng_next()%10000)/10000.0);

            printf("n=%d seed=%d (m=%d):\n",nn,seed,m);

            /* Track gradient descent CAREFULLY */
            double prev_soft=0;
            int last_improve_step=0;

            /* Try MANY different learning rates */
            double best_lr=0; int best_disc_sat=0;

            for(int lr_exp=-4;lr_exp<=0;lr_exp++){
                double lr=pow(10.0,lr_exp);

                /* Reset */
                rng_seed(seed*111);
                for(int v=0;v<n;v++) x[v]=0.3+0.4*((rng_next()%10000)/10000.0);

                int max_steps=50000;
                double final_soft=0;
                double final_grad_norm=0;
                int stagnant_at=-1;

                for(int step=0;step<max_steps;step++){
                    double grad[MAX_N];
                    double soft=compute_soft_and_grad(grad);

                    /* Gradient norm */
                    double gnorm=0;
                    for(int v=0;v<n;v++) gnorm+=grad[v]*grad[v];
                    gnorm=sqrt(gnorm);

                    /* Update */
                    for(int v=0;v<n;v++){
                        x[v]+=lr*grad[v];
                        if(x[v]<0)x[v]=0;if(x[v]>1)x[v]=1;}

                    if(step==max_steps-1||gnorm<1e-10){
                        final_soft=soft;final_grad_norm=gnorm;
                        if(gnorm<1e-10&&stagnant_at<0)stagnant_at=step;}
                }

                /* Round and check */
                int a[MAX_N];for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
                int disc_sat=eval_disc(a);

                /* How many vars are NOT near 0 or 1? */
                int n_middle=0;
                for(int v=0;v<n;v++)
                    if(x[v]>0.1&&x[v]<0.9) n_middle++;

                if(disc_sat>best_disc_sat){best_disc_sat=disc_sat;best_lr=lr;}

                printf("  lr=%.0e: soft=%.1f/%d disc=%d/%d middle=%d |∇|=%.2e %s\n",
                       lr,final_soft,m,disc_sat,m,n_middle,final_grad_norm,
                       disc_sat==m?"★ SOLVED":"");
            }

            printf("  Best: lr=%.0e → %d/%d\n\n",best_lr,best_disc_sat,m);
        }
    }
    return 0;
}
