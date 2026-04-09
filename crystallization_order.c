/*
 * CRYSTALLIZATION ORDER: The trajectory AS information
 * ════════════════════════════════════════════════════
 *
 * ADAM fixes vars gradually: 17 unsat → 2 unsat over 1M steps.
 * In WHAT ORDER do vars commit to 0/1?
 * Does the order contain information about the REMAINING unsolved vars?
 *
 * Track: for each var, WHEN does |x-0.5| > 0.4 for the LAST time?
 * Early commit = confident. Late commit = uncertain.
 *
 * Compare commit order with NEAREST SOLUTION:
 * Do vars that commit EARLIEST tend to be correct?
 * Do vars that commit LATEST tend to be wrong?
 *
 * Compile: gcc -O3 -march=native -o crystal_order crystallization_order.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      500
#define MAX_CLAUSES 2500
#define MAX_K      3
#define MAX_SOLUTIONS 10000

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);rng_seed(seed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;}}}

static int eval_disc(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static int all_sol[MAX_SOLUTIONS][MAX_N],n_sol;
static void find_all(int n){n_sol=0;for(long long m=0;m<(1LL<<n)&&n_sol<MAX_SOLUTIONS;m++){int a[MAX_N];for(int v=0;v<n;v++)a[v]=(m>>v)&1;if(eval_disc(a)==n_clauses){memcpy(all_sol[n_sol],a,sizeof(int)*n);n_sol++;}}}

static double x[MAX_N];

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("CRYSTALLIZATION ORDER: Trajectory as info\n");
    printf("═══════════════════════════════════════════\n\n");

    int n=16;

    for(int seed=0;seed<10;seed++){
        generate(n,4.267,66000000ULL+seed);
        find_all(n);
        if(n_sol<1)continue;

        /* ADAM with trajectory tracking */
        rng_seed(seed*111);
        for(int v=0;v<n;v++)x[v]=0.3+0.4*((rng_next()%10000)/10000.0);

        double ma[MAX_N],va[MAX_N];
        memset(ma,0,sizeof(double)*n);memset(va,0,sizeof(double)*n);

        int commit_step[MAX_N]; /* when var LAST crosses |x-0.5|>0.4 */
        int commit_val[MAX_N];  /* which side */
        int flip_count[MAX_N];  /* how many times var crosses 0.5 */
        memset(commit_step,0,sizeof(int)*n);
        memset(commit_val,0,sizeof(int)*n);
        memset(flip_count,0,sizeof(int)*n);

        int prev_side[MAX_N];
        for(int v=0;v<n;v++) prev_side[v]=(x[v]>0.5)?1:0;

        int total_steps=100000;
        for(int step=0;step<total_steps;step++){
            double grad[MAX_N];memset(grad,0,sizeof(double)*n);
            for(int ci=0;ci<n_clauses;ci++){
                double lit[3],prod=1;
                for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                    lit[j]=(s==1)?x[v]:(1-x[v]);double t=1-lit[j];if(t<1e-15)t=1e-15;prod*=t;}
                if(prod<1e-15)continue;
                for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                    double t=1-lit[j];if(t<1e-15)t=1e-15;grad[v]+=s*(prod/t);}}

            for(int v=0;v<n;v++){
                ma[v]=0.9*ma[v]+0.1*grad[v];
                va[v]=0.999*va[v]+0.001*grad[v]*grad[v];
                double mh=ma[v]/(1-pow(0.9,step+1));
                double vh=va[v]/(1-pow(0.999,step+1));
                x[v]+=0.001*mh/(sqrt(vh)+1e-8);
                if(x[v]<1e-6)x[v]=1e-6;if(x[v]>1-1e-6)x[v]=1-1e-6;

                /* Track crystallization */
                int side=(x[v]>0.5)?1:0;
                if(side!=prev_side[v]){flip_count[v]++;prev_side[v]=side;}
                if(fabs(x[v]-0.5)>0.4){
                    commit_step[v]=step;
                    commit_val[v]=(x[v]>0.5)?1:0;}
            }
        }

        /* Find nearest solution */
        int a[MAX_N];for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
        int min_h=n,ni=0;
        for(int si=0;si<n_sol;si++){int h=0;for(int v=0;v<n;v++)if(a[v]!=all_sol[si][v])h++;if(h<min_h){min_h=h;ni=si;}}
        int *near=all_sol[ni];

        printf("n=%d seed=%d: %d sol, %d unsat, hamming=%d to nearest\n",
               n,seed,n_sol,n_clauses-eval_disc(a),min_h);

        /* Analyze: commit order vs correctness */
        printf("  %4s | %7s | %5s | %5s | %7s | %s\n",
               "var","commit","value","near","flips","status");
        printf("  -----+---------+-------+-------+---------+-------\n");

        /* Sort by commit step */
        int order[MAX_N];for(int v=0;v<n;v++)order[v]=v;
        for(int i=0;i<n-1;i++)for(int j=i+1;j<n;j++)
            if(commit_step[order[j]]<commit_step[order[i]])
                {int t=order[i];order[i]=order[j];order[j]=t;}

        int early_correct=0,early_total=0;
        int late_correct=0,late_total=0;

        for(int i=0;i<n;i++){
            int v=order[i];
            int correct=(a[v]==near[v]);
            char *status=correct?"  ok":"WRONG";

            if(i<n/2){early_total++;if(correct)early_correct++;}
            else{late_total++;if(correct)late_correct++;}

            printf("  x%3d | %7d | %5d | %5d | %7d | %s\n",
                   v,commit_step[v],a[v],near[v],flip_count[v],status);
        }

        printf("\n  Early half (committed first): %d/%d correct (%.0f%%)\n",
               early_correct,early_total,100.0*early_correct/early_total);
        printf("  Late half (committed last):   %d/%d correct (%.0f%%)\n",
               late_correct,late_total,100.0*late_correct/late_total);
        printf("  → %s\n\n",
               early_correct>late_correct?"EARLY = MORE CORRECT":"no clear pattern");

        break; /* one detailed instance */
    }
    return 0;
}
