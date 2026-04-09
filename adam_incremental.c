/*
 * ADAM + INCREMENTAL: Long ADAM to ≤5 unsat, then incremental finish
 * ═══════════════════════════════════════════════════════════════════
 *
 * ADAM at n=300: 17→2 in 1M steps. But exponentially slow near end.
 * Incremental (remove unsat, add back one at a time) works at ≤5 unsat.
 *
 * Pipeline:
 * 1. ADAM gradient for 2M steps → get to ~2-5 unsat
 * 2. Round to discrete
 * 3. Remove unsat clauses
 * 4. Add back one at a time, short ADAM after each
 * 5. If stuck: re-enter continuous and ADAM more
 *
 * Also: try LONGER ADAM (5M, 10M) to see convergence curve
 *
 * Compile: gcc -O3 -march=native -o adam_inc adam_incremental.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      2000
#define MAX_CLAUSES 10000
#define MAX_K      3

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;rng_seed(seed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;}}
    for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;}

static int eval_active(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}}return s;}
static int count_active(void){int c=0;for(int ci=0;ci<n_clauses;ci++)if(cl_active[ci])c++;return c;}
static int eval_full(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static double x[MAX_N];

static void compute_grad_active(double *grad){
    int n=n_vars;memset(grad,0,sizeof(double)*n);
    for(int ci=0;ci<n_clauses;ci++){
        if(!cl_active[ci])continue;
        double lit[3],prod=1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            lit[j]=(s==1)?x[v]:(1-x[v]);double t=1-lit[j];if(t<1e-15)t=1e-15;prod*=t;}
        if(prod<1e-15)continue;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            double t=1-lit[j];if(t<1e-15)t=1e-15;grad[v]+=s*(prod/t);}}}

static void adam_active(int steps){
    int n=n_vars;double m_a[MAX_N],v_a[MAX_N];
    memset(m_a,0,sizeof(double)*n);memset(v_a,0,sizeof(double)*n);
    for(int step=0;step<steps;step++){
        double grad[MAX_N];compute_grad_active(grad);
        for(int v=0;v<n;v++){
            m_a[v]=0.9*m_a[v]+0.1*grad[v];
            v_a[v]=0.999*v_a[v]+0.001*grad[v]*grad[v];
            double mh=m_a[v]/(1-pow(0.9,step+1));
            double vh=v_a[v]/(1-pow(0.999,step+1));
            x[v]+=0.001*mh/(sqrt(vh)+1e-8);
            if(x[v]<1e-6)x[v]=1e-6;if(x[v]>1-1e-6)x[v]=1-1e-6;}}}

int main(void){
    printf("══════════════════════════════════════════════\n");
    printf("ADAM + INCREMENTAL: Long ADAM → incremental\n");
    printf("══════════════════════════════════════════════\n\n");

    int test_n[]={100,200,300,500};
    int sizes=4;

    printf("%6s | %5s | %6s | %6s | %6s | %8s\n",
           "n","total","solved","adam_u","final_u","time_ms");
    printf("-------+-------+--------+--------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?8:(nn<=300?5:3);
        int adam_steps=(nn<=200)?2000000:1000000;
        int solved=0,total=0;double sum_adam_u=0,sum_final_u=0,tms=0;

        for(int seed=0;seed<ni*3&&total<ni;seed++){
            generate(nn,4.267,65000000ULL+seed);
            int n=nn,m=n_clauses;
            clock_t t0=clock();

            /* ═══ Phase 1: Long ADAM ═══ */
            rng_seed(seed*111);
            for(int v=0;v<n;v++)x[v]=0.3+0.4*((rng_next()%10000)/10000.0);
            for(int ci=0;ci<m;ci++)cl_active[ci]=1;

            adam_active(adam_steps);

            /* Round */
            int a[MAX_N];for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
            int adam_unsat=m-eval_full(a);
            sum_adam_u+=adam_unsat;

            if(adam_unsat==0){solved++;total++;
                tms+=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;continue;}

            /* ═══ Phase 2: Incremental ═══ */
            /* Find unsat clauses */
            int unsat_list[MAX_CLAUSES],nu=0;
            for(int ci=0;ci<m;ci++){
                int ok=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                    if((s==1&&a[v]==1)||(s==-1&&a[v]==0)){ok=1;break;}}
                if(!ok)unsat_list[nu++]=ci;}

            /* Deactivate unsat */
            for(int i=0;i<nu;i++)cl_active[unsat_list[i]]=0;

            /* Set x from discrete assignment */
            for(int v=0;v<n;v++)x[v]=a[v]?0.99:0.01;

            /* Add back one at a time */
            int final_unsat=0;
            for(int i=0;i<nu;i++){
                cl_active[unsat_list[i]]=1;

                /* Check: is it already satisfied? */
                int ok=0;for(int j=0;j<3;j++){int v=cl_var[unsat_list[i]][j],s=cl_sign[unsat_list[i]][j];
                    if((s==1&&a[v]==1)||(s==-1&&a[v]==0)){ok=1;break;}}
                if(ok)continue;

                /* Short ADAM to accommodate new clause */
                adam_active(50000);

                /* Re-round */
                for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;

                /* Check all active */
                int cur_unsat=count_active()-eval_active(a);
                if(cur_unsat>0){
                    /* More ADAM */
                    adam_active(100000);
                    for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
                }
            }

            /* Final check on FULL instance */
            for(int ci=0;ci<m;ci++)cl_active[ci]=1;
            for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
            final_unsat=m-eval_full(a);
            sum_final_u+=final_unsat;
            if(final_unsat==0)solved++;

            total++;
            tms+=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;
        }

        if(total>0)
            printf("%6d | %2d/%2d | %4d   | %5.1f  | %5.1f  | %7.0fms\n",
                   nn,total,total,solved,sum_adam_u/total,sum_final_u/total,tms/total);
        fflush(stdout);
    }
    return 0;
}
