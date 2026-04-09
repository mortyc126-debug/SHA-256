/*
 * LOCAL CONVEXITY: Is the landscape convex near the solution?
 * ═══════════════════════════════════════════════════════════
 *
 * We know: greedy path A→B has max 8 unsat.
 * This suggests: near B (solution), sat increases monotonically
 * as we approach from ANY direction.
 *
 * Is this CONVEXITY? Test:
 * 1. From solution B: step in random directions.
 *    Does sat ALWAYS decrease? (= B is a local max)
 * 2. From various points NEAR B: does gradient point toward B?
 * 3. From physics output A: does CONTINUOUS gradient point toward B?
 * 4. BASIN OF ATTRACTION: from how far can gradient descent reach B?
 *
 * If the basin is large enough → gradient descent from physics → SOLVED.
 *
 * Compile: gcc -O3 -march=native -o convex local_convexity.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      20
#define MAX_CLAUSES 100
#define MAX_SOLUTIONS 10000

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][3];
static int cl_sign[MAX_CLAUSES][3];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);rng_seed(seed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;}}}

/* Soft satisfaction: continuous, differentiable */
static double soft_sat(const double *x){
    double total=0;
    for(int ci=0;ci<n_clauses;ci++){
        double prod=1;
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j],s=cl_sign[ci][j];
            double lit=(s==1)?x[v]:(1-x[v]);
            prod*=(1-lit);}
        total+=(1-prod);}
    return total;}

/* Gradient of soft_sat */
static void soft_gradient(const double *x, double *grad){
    int n=n_vars;
    memset(grad,0,sizeof(double)*n);
    for(int ci=0;ci<n_clauses;ci++){
        double lit[3],prod=1;
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j],s=cl_sign[ci][j];
            lit[j]=(s==1)?x[v]:(1-x[v]);
            prod*=(1-lit[j]);}
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j],s=cl_sign[ci][j];
            double t=1-lit[j];if(t<1e-12)t=1e-12;
            grad[v]+=s*(prod/t);}}}

static int eval_disc(const int *a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static int all_sol[MAX_SOLUTIONS][MAX_N],n_sol;
static void find_all(int n){n_sol=0;for(long long m=0;m<(1LL<<n)&&n_sol<MAX_SOLUTIONS;m++){int a[MAX_N];for(int v=0;v<n;v++)a[v]=(m>>v)&1;if(eval_disc(a)==n_clauses){memcpy(all_sol[n_sol],a,sizeof(int)*n);n_sol++;}}}

int main(void){
    printf("═══════════════════════════════════════\n");
    printf("LOCAL CONVEXITY around solution\n");
    printf("═══════════════════════════════════════\n\n");

    int n=16;
    for(int seed=0;seed<100;seed++){
        generate(n,4.267,60000000ULL+seed);
        find_all(n);
        if(n_sol<1)continue;

        int *sol=all_sol[0];
        double sol_x[MAX_N];
        for(int v=0;v<n;v++) sol_x[v]=(double)sol[v];
        double sol_soft=soft_sat(sol_x);

        printf("n=%d seed=%d: %d solutions, soft_sat(sol)=%.2f/%d\n",
               n,seed,n_sol,sol_soft,n_clauses);

        /* ═══ 1. Is solution a LOCAL MAX of soft_sat? ═══ */
        int is_local_max=1;
        double grad[MAX_N];
        soft_gradient(sol_x, grad);
        double grad_norm=0;
        for(int v=0;v<n;v++) grad_norm+=grad[v]*grad[v];
        grad_norm=sqrt(grad_norm);
        printf("  |gradient| at solution: %.6f %s\n",
               grad_norm, grad_norm<0.01?"(≈0 = critical point)":"(nonzero!)");

        /* Step in each axis direction, check if sat decreases */
        double eps_step=0.01;
        int n_decrease=0,n_increase=0;
        for(int v=0;v<n;v++){
            double x_p[MAX_N],x_m[MAX_N];
            memcpy(x_p,sol_x,sizeof(double)*n);
            memcpy(x_m,sol_x,sizeof(double)*n);
            x_p[v]+=eps_step; if(x_p[v]>1)x_p[v]=1;
            x_m[v]-=eps_step; if(x_m[v]<0)x_m[v]=0;
            double sp=soft_sat(x_p), sm=soft_sat(x_m);
            if(sp<sol_soft-1e-10 || sm<sol_soft-1e-10) n_decrease++;
            if(sp>sol_soft+1e-10 || sm>sol_soft+1e-10) n_increase++;
        }
        printf("  Step ±%.2f: %d decrease, %d increase, %d flat\n",
               eps_step,n_decrease,n_increase,n-n_decrease-n_increase);
        printf("  → %s\n", n_decrease==0?"LOCAL MAXIMUM!":"not local max");

        /* ═══ 2. CONTINUOUS gradient descent from RANDOM start ═══ */
        printf("\n  Gradient descent from random starts:\n");
        int gd_solved=0,gd_total=20;
        for(int trial=0;trial<gd_total;trial++){
            double x[MAX_N];
            for(int v=0;v<n;v++) x[v]=0.3+0.4*((rng_next()%1000)/1000.0);

            /* Gradient ascent on soft_sat */
            for(int step=0;step<5000;step++){
                double g[MAX_N];
                soft_gradient(x,g);
                double lr=0.01;
                for(int v=0;v<n;v++){
                    x[v]+=lr*g[v];
                    if(x[v]<0)x[v]=0;if(x[v]>1)x[v]=1;}}

            /* Round and check */
            int disc[MAX_N];
            for(int v=0;v<n;v++) disc[v]=(x[v]>0.5)?1:0;
            if(eval_disc(disc)==n_clauses) gd_solved++;
        }
        printf("  Pure gradient descent: %d/%d solved\n",gd_solved,gd_total);

        /* ═══ 3. Gradient descent from PHYSICS output ═══ */
        rng_seed(42+seed*31);
        double phys_x[MAX_N];
        /* Quick physics */
        double vel[MAX_N];
        for(int v=0;v<n;v++){double p1=0,p0=0;
            for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}
            phys_x[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}
        for(int step=0;step<500;step++){
            double prog=(double)step/500;double T=0.25*exp(-4*prog)+0.0001;double cr=3*prog;
            double force[MAX_N];memset(force,0,sizeof(double)*n);
            for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1;
                for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                    lit[j]=(s==1)?phys_x[v]:(1-phys_x[v]);double t=1-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
                if(prod<0.001)continue;double w=sqrt(prod);
                for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                    double t=1-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
            for(int v=0;v<n;v++){if(phys_x[v]>0.5)force[v]+=cr*(1-phys_x[v]);else force[v]-=cr*phys_x[v];
                vel[v]=0.93*vel[v]+(force[v]+((rng_next()%2000-1000)/10000.0)*T)*0.05;
                phys_x[v]+=vel[v]*0.05;if(phys_x[v]<0)phys_x[v]=0.01;if(phys_x[v]>1)phys_x[v]=0.99;}}

        /* Now: PURE gradient ascent from physics endpoint (no noise, no crystal) */
        for(int step=0;step<10000;step++){
            double g[MAX_N]; soft_gradient(phys_x,g);
            for(int v=0;v<n;v++){phys_x[v]+=0.005*g[v];
                if(phys_x[v]<0)phys_x[v]=0;if(phys_x[v]>1)phys_x[v]=1;}}

        int phys_disc[MAX_N];
        for(int v=0;v<n;v++)phys_disc[v]=(phys_x[v]>0.5)?1:0;
        int phys_sat=eval_disc(phys_disc);
        printf("  Physics → gradient: %d/%d sat (%d unsat)\n",
               phys_sat,n_clauses,n_clauses-phys_sat);

        /* ═══ 4. BASIN: from how far can gradient reach solution? ═══ */
        printf("\n  Basin test (start at hamming h from solution):\n");
        for(int h=1;h<=n;h+=2){
            int reached=0,trials=20;
            for(int t=0;t<trials;t++){
                /* Create point at hamming h from solution in continuous space */
                double x2[MAX_N]; memcpy(x2,sol_x,sizeof(double)*n);
                /* Flip h random vars partially */
                int perm[MAX_N];for(int v=0;v<n;v++)perm[v]=v;
                for(int i=n-1;i>0;i--){int j=rng_next()%(i+1);int tmp=perm[i];perm[i]=perm[j];perm[j]=tmp;}
                for(int i=0;i<h;i++){
                    int v=perm[i];
                    x2[v]=1.0-sol_x[v]; /* flip in continuous space */
                }
                /* Gradient ascent */
                for(int step=0;step<5000;step++){
                    double g2[MAX_N];soft_gradient(x2,g2);
                    for(int v=0;v<n;v++){x2[v]+=0.01*g2[v];
                        if(x2[v]<0)x2[v]=0;if(x2[v]>1)x2[v]=1;}}
                int d2[MAX_N];for(int v=0;v<n;v++)d2[v]=(x2[v]>0.5)?1:0;
                if(eval_disc(d2)==n_clauses)reached++;
            }
            printf("    h=%2d (%.0f%%): %d/%d reached solution\n",
                   h,100.0*h/n,reached,trials);
        }

        printf("\n");
        break;
    }
    return 0;
}
