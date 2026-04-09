/*
 * NEAREST SOLUTION: Is MiniSat giving us the WRONG target?
 * ═══════════════════════════════════════════════════════
 *
 * MiniSat returns ONE solution. But there may be MANY.
 * Physics might be closer to a DIFFERENT solution.
 *
 * At n=12-16: we can enumerate ALL solutions.
 * Compare physics assignment to EACH solution.
 * Which is NEAREST?
 *
 * Questions:
 * 1. How many solutions exist?
 * 2. Hamming to NEAREST vs to MiniSat's solution
 * 3. If we compare to nearest → what % wrong?
 * 4. Does "36% wrong" shrink to "10% wrong" with right target?
 *
 * Compile: gcc -O3 -march=native -o nearest nearest_solution.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      20
#define MAX_CLAUSES 100
#define MAX_K      3
#define MAX_SOLUTIONS 10000

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){double u1=(rng_next()>>11)*(1.0/9007199254740992.0),u2=(rng_next()>>11)*(1.0/9007199254740992.0);if(u1<1e-15)u1=1e-15;return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);rng_seed(seed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;}}}

static int eval_a(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

/* Find ALL solutions by brute force */
static int all_solutions[MAX_SOLUTIONS][MAX_N];
static int n_solutions;

static void find_all_solutions(int n){
    n_solutions=0;
    for(long long mask=0;mask<(1LL<<n)&&n_solutions<MAX_SOLUTIONS;mask++){
        int a[MAX_N];
        for(int v=0;v<n;v++)a[v]=(mask>>v)&1;
        if(eval_a(a)==n_clauses){
            memcpy(all_solutions[n_solutions],a,sizeof(int)*n);
            n_solutions++;}}}

static double x_cont[MAX_N];
static int assignment[MAX_N];
static void physics(int n,int steps,unsigned long long seed){rng_seed(seed);double vel[MAX_N];int vdeg2[MAX_N];memset(vdeg2,0,sizeof(int)*n);for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)vdeg2[cl_var[ci][j]]++;
    for(int v=0;v<n;v++){double p1=0,p0=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}
    double force[MAX_N];
    for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.25*exp(-4*prog)+0.0001;double cr=3*prog;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0)x_cont[v]=0.01;if(x_cont[v]>1)x_cont[v]=0.99;}}
    for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

int main(void){
    printf("══════════════════════════════════════════════════════\n");
    printf("NEAREST SOLUTION: Are we comparing to the wrong one?\n");
    printf("══════════════════════════════════════════════════════\n\n");

    for(int n=12;n<=18;n+=2){
        double sum_nearest_h=0, sum_farthest_h=0, sum_first_h=0;
        double sum_nsol=0;
        int n_inst=0;

        for(int seed=0;seed<200&&n_inst<20;seed++){
            generate(n,4.267,49000000ULL+seed);
            find_all_solutions(n);
            if(n_solutions<2)continue;

            /* Run physics */
            for(int run=0;run<5;run++){
                physics(n,500,42+run*7919+seed*31);
                int sat=eval_a(assignment);
                if(sat<n_clauses-n/3)continue;

                /* Find NEAREST and FARTHEST solution */
                int min_h=n,max_h=0,first_h=0;
                int nearest_idx=0,farthest_idx=0;
                for(int si=0;si<n_solutions;si++){
                    int h=0;
                    for(int v=0;v<n;v++)if(assignment[v]!=all_solutions[si][v])h++;
                    if(h<min_h){min_h=h;nearest_idx=si;}
                    if(h>max_h){max_h=h;farthest_idx=si;}
                    if(si==0)first_h=h;}

                sum_nearest_h+=min_h;
                sum_farthest_h+=max_h;
                sum_first_h+=first_h;
                sum_nsol+=n_solutions;
                n_inst++;

                if(n_inst<=3||n_inst%5==0)
                    printf("  n=%d: %d solutions, unsat=%d, "
                           "nearest=%d (%.0f%%), farthest=%d (%.0f%%), "
                           "first=%d (%.0f%%)\n",
                           n, n_solutions, n_clauses-sat,
                           min_h, 100.0*min_h/n,
                           max_h, 100.0*max_h/n,
                           first_h, 100.0*first_h/n);
                break; /* one run per instance */
            }
        }

        if(n_inst>0){
            printf("\n  n=%d AVERAGES (%d instances):\n",n,n_inst);
            printf("    Solutions: %.1f\n",sum_nsol/n_inst);
            printf("    Nearest:   %.1f (%.0f%% of n)\n",
                   sum_nearest_h/n_inst,100*sum_nearest_h/(n_inst*n));
            printf("    Farthest:  %.1f (%.0f%% of n)\n",
                   sum_farthest_h/n_inst,100*sum_farthest_h/(n_inst*n));
            printf("    First:     %.1f (%.0f%% of n)\n",
                   sum_first_h/n_inst,100*sum_first_h/(n_inst*n));
            printf("    NEAREST/FIRST ratio: %.2f\n\n",
                   sum_nearest_h/sum_first_h);
        }
    }
    return 0;
}
