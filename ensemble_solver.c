/*
 * ENSEMBLE SOLVER: 50 physics runs → majority vote → WalkSAT
 * ═══════════════════════════════════════════════════════════
 *
 * Key idea: wrong bits are UNSTABLE across runs.
 * Majority vote across N independent runs should converge
 * to the correct assignment more often than any single run.
 *
 * Also test: CONFIDENCE-WEIGHTED vote using P(v=1) across runs.
 * Variables near P=0.5 are candidates for wrong → try both values.
 *
 * Compile: gcc -O3 -march=native -o ensemble_solver ensemble_solver.c -lm
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
#define MAX_ENSEMBLE 50

static int n_vars, n_clauses;
static int clause_var[MAX_CLAUSES][MAX_K];
static int clause_sign[MAX_CLAUSES][MAX_K];
static int var_clause_list[MAX_N][MAX_DEGREE];
static int var_clause_pos[MAX_N][MAX_DEGREE];
static int var_degree[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){
    unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];
    unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;
    unsigned long long t=s1<<17;
    s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);
    rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){
    rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;
    rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;
    for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){
    double u1=(rng_next()>>11)*(1.0/9007199254740992.0);
    double u2=(rng_next()>>11)*(1.0/9007199254740992.0);
    if(u1<1e-15)u1=1e-15;
    return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
    rng_seed(seed);memset(var_degree,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            clause_var[ci][j]=vs[j];
            clause_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(var_degree[v]<MAX_DEGREE){
                var_clause_list[v][var_degree[v]]=ci;
                var_clause_pos[v][var_degree[v]]=j;
                var_degree[v]++;}}}}

static int evaluate(const int*a){
    int sat=0;
    for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<3;j++){
            int v=clause_var[ci][j],s=clause_sign[ci][j];
            if((s==1&&a[v]==1)||(s==-1&&a[v]==0)){sat++;break;}}
    return sat;}

static double x[MAX_N],vel[MAX_N];

static void physics_run(int steps,unsigned long long seed){
    int n=n_vars,m=n_clauses;
    rng_seed(seed);
    for(int v=0;v<n;v++){
        double p1=0,p0=0;
        for(int d=0;d<var_degree[v];d++){
            int ci=var_clause_list[v][d],pos=var_clause_pos[v][d];
            if(clause_sign[ci][pos]==1)p1+=1.0/3;else p0+=1.0/3;}
        x[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}
    double force[MAX_N];
    for(int step=0;step<steps;step++){
        double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double crystal=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++){
            double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                lit[j]=(s==1)?x[v]:(1.0-x[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){
            if(x[v]>0.5)force[v]+=crystal*(1-x[v]);else force[v]-=crystal*x[v];
            double noise=rng_normal(0,T);
            vel[v]=0.93*vel[v]+(force[v]+noise)*0.05;
            x[v]+=vel[v]*0.05;
            if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}}

/* WalkSAT */
static int assignment[MAX_N];
static int clause_sat_count[MAX_CLAUSES];
static int walksat(int max_flips){
    int m=n_clauses,n=n_vars;
    int unsat[MAX_CLAUSES],upos[MAX_CLAUSES],nu=0;
    memset(upos,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++){
        clause_sat_count[ci]=0;
        for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sat_count[ci]++;}
        if(clause_sat_count[ci]==0){upos[ci]=nu;unsat[nu++]=ci;}}
    for(int flip=0;flip<max_flips&&nu>0;flip++){
        int ci=unsat[rng_next()%nu];
        int bv=clause_var[ci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=clause_var[ci][j],br=0;
            for(int d=0;d<var_degree[v];d++){
                int oci=var_clause_list[v][d],opos=var_clause_pos[v][d];
                int os=clause_sign[oci][opos];
                if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sat_count[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?clause_var[ci][rng_next()%3]:bv);
        int old=assignment[fv],nw=1-old;assignment[fv]=nw;
        for(int d=0;d<var_degree[fv];d++){
            int oci=var_clause_list[fv][d],opos=var_clause_pos[fv][d];
            int os=clause_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){clause_sat_count[oci]--;
                if(clause_sat_count[oci]==0){upos[oci]=nu;unsat[nu++]=oci;}}
            else if(!was&&now){clause_sat_count[oci]++;
                if(clause_sat_count[oci]==1){int p=upos[oci];
                    if(p>=0&&p<nu){int l=unsat[nu-1];unsat[p]=l;upos[l]=p;upos[oci]=-1;nu--;}}}}}
    return n_clauses-nu;}

/* ════════════════════════════════════════════════════════
 * ENSEMBLE SOLVER
 * ════════════════════════════════════════════════════════ */

static int ensemble_solve(int nn, int n_runs, int physics_steps) {
    int n = nn, m = n_clauses;
    double vote[MAX_N]; /* P(v=1) across runs */
    memset(vote, 0, sizeof(double)*n);

    int best_single_sat = 0;
    int best_single[MAX_N];

    /* Run physics N times, accumulate votes */
    for(int run = 0; run < n_runs; run++) {
        physics_run(physics_steps, 42 + run * 7919);
        int a[MAX_N];
        for(int v=0;v<n;v++) a[v] = (x[v]>0.5)?1:0;
        int sat = evaluate(a);

        if(sat == m) { memcpy(assignment,a,sizeof(int)*n); return 1; }

        if(sat > best_single_sat) {
            best_single_sat = sat;
            memcpy(best_single, a, sizeof(int)*n);
        }

        for(int v=0;v<n;v++) vote[v] += a[v];
    }

    /* Normalize votes to [0,1] */
    for(int v=0;v<n;v++) vote[v] /= n_runs;

    /* Method 1: MAJORITY VOTE */
    for(int v=0;v<n;v++) assignment[v] = (vote[v] > 0.5) ? 1 : 0;
    int sat_majority = evaluate(assignment);
    if(sat_majority == m) return 2;

    /* Method 2: BEST SINGLE + WalkSAT */
    memcpy(assignment, best_single, sizeof(int)*n);
    rng_seed(77777);
    int sat_best_walk = walksat(n * 500);
    if(sat_best_walk == m) return 3;

    /* Method 3: MAJORITY + WalkSAT */
    for(int v=0;v<n;v++) assignment[v] = (vote[v] > 0.5) ? 1 : 0;
    rng_seed(88888);
    int sat_maj_walk = walksat(n * 500);
    if(sat_maj_walk == m) return 4;

    /* Method 4: CONFIDENCE-WEIGHTED — try uncertain bits both ways */
    /* Find vars closest to 0.5 (most uncertain), try flipping them */
    double uncertainty[MAX_N];
    int sorted[MAX_N];
    for(int v=0;v<n;v++) { uncertainty[v]=fabs(vote[v]-0.5); sorted[v]=v; }
    /* Sort by uncertainty ascending (most uncertain first) */
    for(int i=0;i<n-1;i++)
        for(int j=i+1;j<n;j++)
            if(uncertainty[sorted[j]]<uncertainty[sorted[i]])
                {int t=sorted[i];sorted[i]=sorted[j];sorted[j]=t;}

    /* Try flipping top-k most uncertain */
    for(int v2=0;v2<n;v2++) assignment[v2]=(vote[v2]>0.5)?1:0;
    for(int k=1; k<=20 && k<=n/4; k++) {
        int test[MAX_N];
        memcpy(test, assignment, sizeof(int)*n);
        for(int i=0;i<k;i++) test[sorted[i]] = 1 - test[sorted[i]];
        if(evaluate(test) == m) {
            memcpy(assignment, test, sizeof(int)*n);
            return 5;
        }
    }

    /* Method 5: Uncertain flip + WalkSAT */
    /* Start from majority, flip top-5 uncertain, then WalkSAT */
    for(int v2=0;v2<n;v2++) assignment[v2]=(vote[v2]>0.5)?1:0;
    int n_flip = (n < 20) ? 3 : 5;
    for(int i=0;i<n_flip&&i<n;i++) assignment[sorted[i]] = 1 - assignment[sorted[i]];
    rng_seed(99999);
    int sat_unc_walk = walksat(n * 500);
    if(sat_unc_walk == m) return 6;

    return 0;
}

int main(void) {
    printf("══════════════════════════════════════════════\n");
    printf("ENSEMBLE SOLVER: N physics runs → vote → solve\n");
    printf("══════════════════════════════════════════════\n\n");

    int test_n[] = {50, 100, 200, 300, 500, 750, 1000};
    int sizes = sizeof(test_n)/sizeof(test_n[0]);

    /* Test different ensemble sizes */
    int ensemble_sizes[] = {5, 20, 50};
    int n_ens = 3;

    for(int ei=0; ei<n_ens; ei++) {
        int N = ensemble_sizes[ei];
        printf("─── Ensemble size N=%d ───\n", N);
        printf("%6s | %5s | %6s | %6s | %6s | %8s\n",
               "n", "total", "solved", "method", "sat%%", "time_ms");
        printf("-------+-------+--------+--------+--------+----------\n");

        for(int ti=0; ti<sizes; ti++) {
            int nn = test_n[ti];
            int n_inst = (nn<=200)?20:(nn<=500?10:5);
            int steps = 1500 + nn*10;

            int solved=0, total=0;
            int method_counts[7] = {0};
            double total_ms=0;

            for(int seed=0; seed<n_inst*3 && total<n_inst; seed++) {
                generate(nn, 4.267, 7000000ULL+seed);
                clock_t t0=clock();
                int result = ensemble_solve(nn, N, steps);
                clock_t t1=clock();
                total_ms += (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
                total++;
                if(result>0) { solved++; method_counts[result]++; }
            }

            /* Most common winning method */
            int best_method=0, best_count=0;
            for(int i=1;i<=6;i++)
                if(method_counts[i]>best_count){best_count=method_counts[i];best_method=i;}
            char *method_names[]={"","phys","majvt","bst+w","maj+w","uncflp","unc+w"};

            printf("%6d | %2d/%2d | %4d   | %5s  |        | %7.0fms\n",
                   nn, solved, total, solved,
                   (best_method>0)?method_names[best_method]:"none",
                   total_ms/total);
            fflush(stdout);
        }
        printf("\n");
    }
    return 0;
}
