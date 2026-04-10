/*
 * EXPERIMENT 2: HDC + SP hybrid
 * ==============================
 *
 * Idea: multiple SP runs give different marginals due to initialization.
 * Encode each run as HDV, bundle them, extract stable consensus.
 *
 * Specifically: "uncertainty-aware" aggregation — variables where all runs
 * agree get sharp HDV representation; variables where runs disagree get
 * blurred (close to center of HDV space).
 *
 * Compile: gcc -O3 -march=native -o hdc_sp hdc_sp.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define MAX_N 200
#define MAX_CLAUSES 1000
#define MAX_K 3
#define MAX_DEGREE 100
#define D 8192
#define D_WORDS (D/64)
#define N_SP_RUNS 20

typedef struct { uint64_t b[D_WORDS]; } HDV;

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];
static double eta[MAX_CLAUSES][MAX_K];
static double W_plus[MAX_N], W_minus[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){
    unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];
    unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;
    s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);
    rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){
    rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;
    rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;
    for(int i=0;i<20;i++)rng_next();}
static inline double rng_double(void){return(rng_next()>>11)*(1.0/9007199254740992.0);}

static HDV hdv_random(void){HDV v;for(int i=0;i<D_WORDS;i++)v.b[i]=rng_next();return v;}
static HDV hdv_zero(void){HDV v;memset(&v,0,sizeof(v));return v;}
static HDV hdv_bind(HDV a,HDV b){HDV r;for(int i=0;i<D_WORDS;i++)r.b[i]=a.b[i]^b.b[i];return r;}
static int hdv_ham(HDV a,HDV b){int d=0;for(int i=0;i<D_WORDS;i++)d+=__builtin_popcountll(a.b[i]^b.b[i]);return d;}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    rng_seed(seed);memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
    for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
}

static inline double sp_edge(int ci,int pi){
    double product=1.0;
    for(int pj=0;pj<3;pj++){
        if(pj==pi)continue;
        int j=cl_var[ci][pj];
        if(var_fixed[j]>=0){int sj=cl_sign[ci][pj];
            if((sj==1&&var_fixed[j]==1)||(sj==-1&&var_fixed[j]==0))return 0.0;continue;}
        int sja=cl_sign[ci][pj];double ps=1.0,pu=1.0;
        for(int d=0;d<vdeg[j];d++){
            int bi=vlist[j][d],bp=vpos[j][d];
            if(bi==ci||!cl_active[bi])continue;
            double eb=eta[bi][bp];
            if(cl_sign[bi][bp]==sja)ps*=(1.0-eb);else pu*=(1.0-eb);}
        double Pu=(1.0-pu)*ps,Ps=(1.0-ps)*pu,P0=pu*ps;
        double den=Pu+Ps+P0;
        product*=(den>1e-15)?(Pu/den):0.0;}
    return product;
}

static double sp_sweep(double rho){
    double mc=0;
    for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;
        for(int p=0;p<3;p++){if(var_fixed[cl_var[ci][p]]>=0)continue;
            double nv=sp_edge(ci,p),ov=eta[ci][p];
            double up=rho*ov+(1.0-rho)*nv;
            double ch=fabs(up-ov);if(ch>mc)mc=ch;eta[ci][p]=up;}}
    return mc;
}

static int sp_run(unsigned long long init_seed){
    rng_seed(init_seed);
    for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<3;j++)
            eta[ci][j]=rng_double();

    for(int iter=0;iter<200;iter++){double ch=sp_sweep(0.1);if(ch<1e-4)return 1;}
    return 0;
}

static void compute_bias(void){
    for(int i=0;i<n_vars;i++){
        W_plus[i]=W_minus[i]=0;
        double pp=1.0,pm=1.0;
        for(int d=0;d<vdeg[i];d++){
            int ci=vlist[i][d],p=vpos[i][d];
            if(!cl_active[ci])continue;
            double e=eta[ci][p];
            if(cl_sign[ci][p]==1)pp*=(1.0-e);else pm*=(1.0-e);}
        double pip=(1.0-pp)*pm,pim=(1.0-pm)*pp,pi0=pp*pm,tot=pip+pim+pi0;
        if(tot>1e-15){W_plus[i]=pip/tot;W_minus[i]=pim/tot;}}
}

/* probSAT quick test */
static int probsat_test(int n, int m, int *assign){
    int sc[MAX_CLAUSES];
    memset(sc, 0, sizeof(int)*m);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&assign[v]==1)||(s==-1&&assign[v]==0))sc[ci]++;}
    int nu = 0;
    for(int ci = 0; ci < m; ci++) if(sc[ci] == 0) nu++;
    return m - nu;
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("EXPERIMENT 2: HDC + SP hybrid\n");
    printf("══════════════════════════════════════════\n\n");

    /* Test: multiple SP runs on same instance, aggregate marginals via HDC */
    int n = 100;
    generate(n, 4.0, 42);
    int m = n_clauses;

    printf("n=%d, α=4.0, m=%d\n\n", n, m);

    /* Create variable hypervectors */
    rng_seed(1);
    HDV V_var[200];
    for(int i = 0; i < n; i++) V_var[i] = hdv_random();
    HDV V_plus = hdv_random();
    HDV V_minus = hdv_random();

    /* Collect marginals from multiple SP runs */
    double marginal_sums[200] = {0};
    double marginal_sq_sums[200] = {0};
    int converged_runs = 0;

    /* Also: per-variable "vote" HDV (bundle) */
    int counters[200][D];
    memset(counters, 0, sizeof(counters));

    for(int run = 0; run < N_SP_RUNS; run++){
        for(int ci = 0; ci < m; ci++) cl_active[ci] = 1;
        memset(var_fixed, -1, sizeof(int)*n);

        if(!sp_run(run * 31337 + 1)){
            continue;
        }
        converged_runs++;

        compute_bias();

        for(int i = 0; i < n; i++){
            marginal_sums[i] += W_plus[i];
            marginal_sq_sums[i] += W_plus[i] * W_plus[i];

            /* Encode this run's decision in HDV bundle */
            int decision = (W_plus[i] > W_minus[i]) ? 1 : 0;
            HDV contribution = hdv_bind(V_var[i], decision ? V_plus : V_minus);
            for(int k = 0; k < D; k++){
                counters[i][k] += ((contribution.b[k>>6] >> (k&63)) & 1) ? 1 : -1;
            }
        }
    }

    printf("SP runs converged: %d/%d\n\n", converged_runs, N_SP_RUNS);
    if(converged_runs < 3){
        printf("Not enough runs — aborting\n");
        return 1;
    }

    /* Compute stability: variance of marginals across runs */
    printf("Stability analysis (first 20 variables):\n");
    printf("%4s | %7s | %7s | %8s | status\n", "var", "avg", "std", "consensus");
    printf("-----+---------+---------+----------+--------\n");

    int stable_count = 0, unstable_count = 0;
    for(int i = 0; i < 20; i++){
        double avg = marginal_sums[i] / converged_runs;
        double var = marginal_sq_sums[i]/converged_runs - avg*avg;
        double std = sqrt(var > 0 ? var : 0);

        const char *status;
        if(std < 0.05) {status = "stable  "; stable_count++;}
        else {status = "UNSTABLE"; unstable_count++;}

        printf("%4d | %7.4f | %7.4f | %8s\n", i, avg, std, status);
    }

    /* Count all variables */
    int n_stable = 0, n_unstable = 0;
    for(int i = 0; i < n; i++){
        double avg = marginal_sums[i] / converged_runs;
        double var = marginal_sq_sums[i]/converged_runs - avg*avg;
        double std = sqrt(var > 0 ? var : 0);
        if(std < 0.05) n_stable++; else n_unstable++;
    }

    printf("\nTotal stable: %d / %d (%.0f%%)\n", n_stable, n, 100.0*n_stable/n);

    /* Strategy: use stable variables first, unstable ones by HDC voting */
    int assign[200];
    for(int i = 0; i < n; i++){
        double avg = marginal_sums[i] / converged_runs;
        double var = marginal_sq_sums[i]/converged_runs - avg*avg;
        double std = sqrt(var > 0 ? var : 0);

        if(std < 0.05){
            /* Stable: use average marginal */
            assign[i] = (avg > 0.5) ? 1 : 0;
        } else {
            /* Unstable: use HDC voting (majority across runs) */
            /* Count: is V_plus or V_minus closer? */
            HDV finalized = hdv_zero();
            for(int k = 0; k < D; k++) if(counters[i][k] > 0) finalized.b[k>>6] |= (1ULL<<(k&63));

            HDV query_plus = hdv_bind(V_var[i], V_plus);
            HDV query_minus = hdv_bind(V_var[i], V_minus);
            int d_plus = hdv_ham(finalized, query_plus);
            int d_minus = hdv_ham(finalized, query_minus);
            assign[i] = (d_plus < d_minus) ? 1 : 0;
        }
    }

    /* Test the combined assignment */
    int sat = probsat_test(n, m, assign);
    printf("\nHybrid assignment: %d/%d clauses satisfied (%.1f%%)\n",
           sat, m, 100.0*sat/m);

    /* Compare with single-run SP + rounding */
    int single_assign[200];
    for(int ci = 0; ci < m; ci++) cl_active[ci] = 1;
    memset(var_fixed, -1, sizeof(int)*n);
    sp_run(42);
    compute_bias();
    for(int i = 0; i < n; i++){
        single_assign[i] = (W_plus[i] > W_minus[i]) ? 1 : 0;
    }
    int single_sat = probsat_test(n, m, single_assign);
    printf("Single-run SP:     %d/%d clauses satisfied (%.1f%%)\n",
           single_sat, m, 100.0*single_sat/m);

    printf("\nHybrid vs single: %+d clauses\n", sat - single_sat);

    if(sat > single_sat){
        printf("✓ HDC aggregation HELPS (multiple runs + voting > single run)\n");
    } else if(sat == single_sat){
        printf("= HDC aggregation neutral (same accuracy)\n");
    } else {
        printf("✗ HDC aggregation HURTS (single run better)\n");
    }

    return 0;
}
