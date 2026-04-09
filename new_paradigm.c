/*
 * NEW PARADIGM: Three fundamentally different approaches to the last 1%
 * ════════════════════════════════════════════════════════════════════
 *
 * 1. SEQUENTIAL CRYSTALLIZATION — round one variable at a time + UP
 * 2. SUB-INSTANCE EXTRACTION — extract small sub-problem from unsat clauses
 * 3. TARGETED MELT — reheat locally, refreeze differently
 *
 * Compile: gcc -O3 -march=native -o new_paradigm new_paradigm.c -lm
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
static int clause_var[MAX_CLAUSES][MAX_K];
static int clause_sign[MAX_CLAUSES][MAX_K];
static int var_clause_list[MAX_N][MAX_DEGREE];
static int var_clause_pos[MAX_N][MAX_DEGREE];
static int var_degree[MAX_N];

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
        for(int j=0;j<3;j++){clause_var[ci][j]=vs[j];
            clause_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];if(var_degree[v]<MAX_DEGREE){
                var_clause_list[v][var_degree[v]]=ci;
                var_clause_pos[v][var_degree[v]]=j;var_degree[v]++;}}}}

static int evaluate(const int*a){
    int sat=0;for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
            if((s==1&&a[v]==1)||(s==-1&&a[v]==0)){sat++;break;}}
    return sat;}

/* Physics engine */
static double x[MAX_N],vel[MAX_N];
static void physics_run(int steps,unsigned long long seed){
    int n=n_vars,m=n_clauses;rng_seed(seed);
    for(int v=0;v<n;v++){double p1=0,p0=0;
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
        for(int ci=0;ci<m;ci++){double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                lit[j]=(s==1)?x[v]:(1.0-x[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){
            if(x[v]>0.5)force[v]+=crystal*(1-x[v]);else force[v]-=crystal*x[v];
            vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;
            x[v]+=vel[v]*0.05;
            if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}}

/* WalkSAT (standard, for comparison) */
static int assignment[MAX_N];
static int clause_sat_count[MAX_CLAUSES];

static void recompute_sat_counts(void) {
    for(int ci=0;ci<n_clauses;ci++){clause_sat_count[ci]=0;
        for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sat_count[ci]++;}}}

static int walksat(int max_flips){
    int m=n_clauses,n=n_vars;
    int unsat[MAX_CLAUSES],upos[MAX_CLAUSES],nu=0;
    memset(upos,-1,sizeof(int)*m);
    recompute_sat_counts();
    for(int ci=0;ci<m;ci++)if(clause_sat_count[ci]==0){upos[ci]=nu;unsat[nu++]=ci;}
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
 * METHOD 1: SEQUENTIAL CRYSTALLIZATION
 * Round one variable at a time (highest confidence first)
 * + unit propagation after each rounding
 * ════════════════════════════════════════════════════════ */

static int unit_propagate(int *fixed, int n) {
    /* Returns: 0=ok, 1=conflict */
    int changed = 1;
    while(changed) {
        changed = 0;
        for(int ci=0; ci<n_clauses; ci++) {
            int sat=0, free_count=0, free_var=-1, free_sign=0;
            for(int j=0; j<3; j++) {
                int v=clause_var[ci][j], s=clause_sign[ci][j];
                if(fixed[v] >= 0) {
                    if((s==1&&fixed[v]==1)||(s==-1&&fixed[v]==0)) sat=1;
                } else {
                    free_count++; free_var=v; free_sign=s;
                }
            }
            if(sat) continue;
            if(free_count==0) return 1; /* conflict */
            if(free_count==1) {
                fixed[free_var] = (free_sign==1) ? 1 : 0;
                changed = 1;
            }
        }
    }
    return 0;
}

static int sequential_crystallize(int n) {
    /* Sort variables by confidence (|x - 0.5|) descending */
    int order[MAX_N];
    double confidence[MAX_N];
    for(int v=0;v<n;v++) { order[v]=v; confidence[v]=fabs(x[v]-0.5); }
    for(int i=0;i<n-1;i++) for(int j=i+1;j<n;j++)
        if(confidence[order[j]]>confidence[order[i]])
            {int t=order[i];order[i]=order[j];order[j]=t;}

    int fixed[MAX_N];
    memset(fixed, -1, sizeof(int)*n); /* -1 = unfixed */

    for(int i=0; i<n; i++) {
        int v = order[i];
        if(fixed[v] >= 0) continue; /* already fixed by UP */

        /* Round this variable based on continuous state */
        fixed[v] = (x[v] > 0.5) ? 1 : 0;

        /* Unit propagation */
        if(unit_propagate(fixed, n)) {
            /* Conflict! Try opposite value */
            fixed[v] = 1 - fixed[v];
            if(unit_propagate(fixed, n)) {
                /* Both fail — backtrack not implemented, just continue */
                break;
            }
        }
    }

    /* Fill any remaining unfixed */
    for(int v=0;v<n;v++)
        assignment[v] = (fixed[v]>=0) ? fixed[v] : ((x[v]>0.5)?1:0);

    return evaluate(assignment);
}

/* ════════════════════════════════════════════════════════
 * METHOD 2: TARGETED MELT + REFREEZE
 * Identify frustrated region, reheat locally, refreeze
 * ════════════════════════════════════════════════════════ */

static int targeted_melt(int n, int steps) {
    int m = n_clauses;

    /* First: get 99% state */
    for(int v=0;v<n;v++) assignment[v]=(x[v]>0.5)?1:0;
    int base_sat = evaluate(assignment);

    /* Find unsatisfied clause variables */
    int hot[MAX_N]; memset(hot,0,sizeof(int)*n);
    for(int ci=0;ci<m;ci++) {
        int sat=0;
        for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))sat=1;}
        if(!sat) {
            for(int j=0;j<3;j++) hot[clause_var[ci][j]]=1;
            /* Also heat neighbors of hot vars */
            for(int j=0;j<3;j++){
                int v=clause_var[ci][j];
                for(int d=0;d<var_degree[v]&&d<10;d++){
                    int oci=var_clause_list[v][d];
                    for(int jj=0;jj<3;jj++) hot[clause_var[oci][jj]]=1;
                }
            }
        }
    }

    int n_hot=0; for(int v=0;v<n;v++) if(hot[v]) n_hot++;

    /* Melt hot region: push back toward 0.5 */
    for(int v=0;v<n;v++) {
        if(hot[v]) {
            x[v] = 0.5 + 0.1 * (x[v] - 0.5); /* shrink toward 0.5 */
            vel[v] = 0;
        }
    }

    /* Refreeze with physics (only hot vars move, cold are fixed) */
    double force[MAX_N];
    for(int step=0;step<steps;step++) {
        double prog=(double)step/steps;
        double T=0.15*exp(-3.0*prog)+0.0001;
        double crystal=2.0+4.0*prog;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++){double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                lit[j]=(s==1)?x[v]:(1.0-x[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){
            if(!hot[v]) continue; /* only move hot vars */
            if(x[v]>0.5)force[v]+=crystal*(1-x[v]);else force[v]-=crystal*x[v];
            vel[v]=0.9*vel[v]+(force[v]+rng_normal(0,T))*0.04;
            x[v]+=vel[v]*0.04;
            if(x[v]<0){x[v]=0.01;vel[v]=0;}if(x[v]>1){x[v]=0.99;vel[v]=0;}}
    }

    for(int v=0;v<n;v++) assignment[v]=(x[v]>0.5)?1:0;
    return evaluate(assignment);
}

/* ════════════════════════════════════════════════════════
 * BENCHMARK: Compare all methods
 * ════════════════════════════════════════════════════════ */

int main(void) {
    printf("═══════════════════════════════════════════════════\n");
    printf("NEW PARADIGM: Sequential Crystal / Targeted Melt\n");
    printf("═══════════════════════════════════════════════════\n\n");

    int test_n[] = {50, 100, 200, 300, 500, 750, 1000};
    int sizes = 7;

    printf("%6s | %5s | %6s | %6s | %6s | %6s | %8s\n",
           "n", "total", "bulk", "seqcry", "melt", "+walk", "time_ms");
    printf("-------+-------+--------+--------+--------+--------+----------\n");

    for(int ti=0; ti<sizes; ti++) {
        int nn = test_n[ti];
        int n_inst = (nn<=200)?20:(nn<=500?10:5);
        int steps = 2000+nn*15;

        int s_bulk=0, s_seq=0, s_melt=0, s_walk=0, total=0;
        double total_ms=0;

        for(int seed=0; seed<n_inst*3 && total<n_inst; seed++) {
            generate(nn, 4.267, 8000000ULL+seed);
            clock_t t0=clock();

            /* Physics run */
            physics_run(steps, 42+seed*31);
            double x_save[MAX_N]; memcpy(x_save,x,sizeof(double)*nn);

            /* Method 0: Bulk rounding (baseline) */
            for(int v=0;v<nn;v++) assignment[v]=(x[v]>0.5)?1:0;
            int sat_bulk = evaluate(assignment);
            if(sat_bulk == n_clauses) s_bulk++;

            /* Method 1: Sequential crystallization */
            memcpy(x,x_save,sizeof(double)*nn);
            int sat_seq = sequential_crystallize(nn);
            if(sat_seq == n_clauses) s_seq++;

            /* Method 2: Targeted melt + refreeze */
            memcpy(x,x_save,sizeof(double)*nn);
            for(int v=0;v<nn;v++) assignment[v]=(x[v]>0.5)?1:0; /* reset */
            rng_seed(seed*777);
            int sat_melt = targeted_melt(nn, 500+nn*5);
            if(sat_melt == n_clauses) s_melt++;

            /* Method 3: Best result + WalkSAT */
            int best_sat = sat_bulk;
            int best_a[MAX_N];
            for(int v=0;v<nn;v++) best_a[v]=(x_save[v]>0.5)?1:0;
            /* Try seq result */
            memcpy(x,x_save,sizeof(double)*nn);
            sequential_crystallize(nn);
            if(evaluate(assignment) > best_sat) {
                best_sat=evaluate(assignment); memcpy(best_a,assignment,sizeof(int)*nn);
            }
            /* Try melt result */
            memcpy(x,x_save,sizeof(double)*nn);
            for(int v=0;v<nn;v++) assignment[v]=(x[v]>0.5)?1:0;
            rng_seed(seed*777);
            targeted_melt(nn, 500+nn*5);
            if(evaluate(assignment) > best_sat) {
                best_sat=evaluate(assignment); memcpy(best_a,assignment,sizeof(int)*nn);
            }
            /* WalkSAT from best */
            memcpy(assignment,best_a,sizeof(int)*nn);
            rng_seed(seed*9999);
            int sat_final = walksat(nn*500);
            if(sat_final == n_clauses) s_walk++;

            total++;
            clock_t t1=clock();
            total_ms += (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
        }

        int best = s_bulk; if(s_seq>best)best=s_seq; if(s_melt>best)best=s_melt; if(s_walk>best)best=s_walk;
        printf("%6d | %2d/%2d | %4d   | %4d   | %4d   | %4d   | %7.0fms\n",
               nn, best, total, s_bulk, s_seq, s_melt, s_walk, total_ms/total);
        fflush(stdout);
    }

    printf("\nLegend: bulk=all-at-once rounding, seqcry=sequential crystallization,\n");
    printf("        melt=targeted melt+refreeze, +walk=best+WalkSAT\n");
    return 0;
}
