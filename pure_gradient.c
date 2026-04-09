/*
 * PURE GRADIENT: No physics, no WalkSAT. Just gradient ascent on soft_sat.
 * ═══════════════════════════════════════════════════════════════════════
 *
 * At n=16: 100% solve rate. Does it SCALE?
 *
 * Algorithm:
 * 1. Start from random x ∈ [0.3, 0.7]^n (center of hypercube)
 * 2. Gradient ascent: x += lr × ∇soft_sat(x)
 * 3. Clamp to [0, 1]
 * 4. NO rounding until the end
 * 5. After convergence: round x → {0,1}, check discrete sat
 *
 * Key difference from PhysicsSAT:
 *   PhysicsSAT adds noise + crystallization → forces to corners early
 *   Pure gradient: smooth ascent, corners emerge NATURALLY
 *
 * Compile: gcc -O3 -march=native -o pure_grad pure_gradient.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      5000
#define MAX_CLAUSES 25000
#define MAX_K      3
#define MAX_DEGREE 200

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;rng_seed(seed);memset(vdeg,0,sizeof(int)*n);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}}

static int eval_disc(const int *a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static double x[MAX_N];

static double soft_sat_and_grad(double *grad){
    int n=n_vars, m=n_clauses;
    if(grad) memset(grad,0,sizeof(double)*n);
    double total=0;
    for(int ci=0;ci<m;ci++){
        double lit[3],prod=1;
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j],s=cl_sign[ci][j];
            lit[j]=(s==1)?x[v]:(1-x[v]);
            double t=1-lit[j]; if(t<1e-15)t=1e-15;
            prod*=t;}
        total+=(1-prod);
        if(grad && prod>1e-15){
            for(int j=0;j<3;j++){
                int v=cl_var[ci][j],s=cl_sign[ci][j];
                double t=1-lit[j]; if(t<1e-15)t=1e-15;
                grad[v]+=s*(prod/t);}}}
    return total;}

static int pure_gradient_solve(int nn, int max_steps, double lr, int restarts){
    int n=nn, m=n_clauses;
    int best_disc_sat=0;
    int best_a[MAX_N];

    for(int restart=0;restart<restarts;restart++){
        /* Random start near center */
        for(int v=0;v<n;v++)
            x[v]=0.3+0.4*((rng_next()%10000)/10000.0);

        double prev_soft=0;
        int stagnant=0;

        for(int step=0;step<max_steps;step++){
            double grad[MAX_N];
            double soft=soft_sat_and_grad(grad);

            /* Adaptive learning rate */
            double gnorm=0;
            for(int v=0;v<n;v++) gnorm+=grad[v]*grad[v];
            gnorm=sqrt(gnorm);
            double actual_lr = (gnorm>1e-10) ? lr*n/gnorm : lr;
            if(actual_lr>0.1) actual_lr=0.1;

            /* Update */
            for(int v=0;v<n;v++){
                x[v]+=actual_lr*grad[v];
                if(x[v]<0)x[v]=0; if(x[v]>1)x[v]=1;}

            /* Check stagnation */
            if(fabs(soft-prev_soft)<1e-8) stagnant++;
            else stagnant=0;
            prev_soft=soft;
            if(stagnant>500) break;

            /* Periodic discrete check */
            if(step%1000==999||step==max_steps-1){
                int a[MAX_N];
                for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;
                int disc_sat=eval_disc(a);
                if(disc_sat>best_disc_sat){
                    best_disc_sat=disc_sat;
                    memcpy(best_a,a,sizeof(int)*n);}
                if(disc_sat==m) return m; /* SOLVED */
            }
        }

        /* Final round */
        int a[MAX_N];
        for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;
        int disc_sat=eval_disc(a);
        if(disc_sat>best_disc_sat){
            best_disc_sat=disc_sat;memcpy(best_a,a,sizeof(int)*n);}
        if(disc_sat==m) return m;
    }

    return best_disc_sat;
}

/* Also: gradient + MOMENTUM (like physics but without noise/crystal) */
static int gradient_momentum_solve(int nn, int max_steps, double lr, int restarts){
    int n=nn, m=n_clauses;
    int best_disc_sat=0;

    for(int restart=0;restart<restarts;restart++){
        double vel[MAX_N];
        for(int v=0;v<n;v++){
            x[v]=0.3+0.4*((rng_next()%10000)/10000.0);
            vel[v]=0;}

        for(int step=0;step<max_steps;step++){
            double grad[MAX_N];
            soft_sat_and_grad(grad);

            double damping=0.95;
            for(int v=0;v<n;v++){
                vel[v]=damping*vel[v]+lr*grad[v];
                x[v]+=vel[v];
                if(x[v]<0){x[v]=0;vel[v]=0;}
                if(x[v]>1){x[v]=1;vel[v]=0;}}

            if(step%1000==999){
                int a[MAX_N];for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
                int ds=eval_disc(a);if(ds>best_disc_sat)best_disc_sat=ds;
                if(ds==m)return m;}}

        int a[MAX_N];for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
        int ds=eval_disc(a);if(ds>best_disc_sat)best_disc_sat=ds;
        if(ds==m)return m;
    }
    return best_disc_sat;
}

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("PURE GRADIENT: Does it scale?\n");
    printf("═══════════════════════════════════════════\n\n");

    int test_n[]={16,20,30,50,75,100,150,200,300,500,750,1000};
    int sizes=12;

    printf("%6s | %5s | %6s | %6s | %6s | %8s\n",
           "n","total","grad","g+mom","unsat","time_ms");
    printf("-------+-------+--------+--------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=50)?20:(nn<=200?10:(nn<=500?5:3));
        int max_steps=(nn<=100)?20000:(nn<=500?10000:5000);
        int restarts=(nn<=100)?5:3;
        double lr=0.01;

        int s_grad=0,s_mom=0,total=0;
        double sum_unsat=0,tms=0;

        for(int seed=0;seed<ni*3&&total<ni;seed++){
            generate(nn,4.267,61000000ULL+seed);
            clock_t t0=clock();

            /* Pure gradient */
            rng_seed(seed*111);
            int sat_g=pure_gradient_solve(nn,max_steps,lr,restarts);
            if(sat_g==n_clauses) s_grad++;
            sum_unsat+=(n_clauses-sat_g);

            /* Gradient + momentum */
            rng_seed(seed*222);
            int sat_m=gradient_momentum_solve(nn,max_steps,lr*0.5,restarts);
            if(sat_m==n_clauses) s_mom++;

            total++;
            tms+=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;
        }

        printf("%6d | %2d/%2d | %4d   | %4d   | %5.1f  | %7.0fms\n",
               nn,total,total,s_grad,s_mom,sum_unsat/total,tms/total);
        fflush(stdout);
    }

    printf("\nIf gradient solves at n=500+: CONTINUOUS SAT IS EASIER THAN DISCRETE.\n");
    return 0;
}
