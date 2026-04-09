/*
 * PHYSICS-GUIDED DECIMATION: Fix one variable at a time
 * ═══════════════════════════════════════════════════════
 *
 * Instead of: physics → round ALL → WalkSAT (fails at n=750)
 * Do:         physics → fix ONE → simplify → physics → fix ONE → ...
 *
 * Each re-run of physics sees a SIMPLER instance.
 * Frozen vars become visible after their neighbors are fixed.
 *
 * This is the SP-decimation paradigm with physics instead of SP.
 *
 * Compile: gcc -O3 -march=native -o decimation_solver decimation_solver.c -lm
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
static int clause_active[MAX_CLAUSES]; /* 1=active, 0=satisfied and removed */
static int var_fixed[MAX_N]; /* -1=free, 0 or 1=fixed value */
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
                var_clause_pos[v][var_degree[v]]=j;var_degree[v]++;}}}
    for(int ci=0;ci<n_clauses;ci++) clause_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
}

static int evaluate_full(void){
    int sat=0;
    for(int ci=0;ci<n_clauses;ci++){
        for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
            int val=var_fixed[v]; if(val<0) val=0; /* unfixed → default 0 */
            if((s==1&&val==1)||(s==-1&&val==0)){sat++;break;}}}
    return sat;}

/* Unit propagation on active clauses with fixed vars */
static int unit_propagate(void) {
    int changed=1, conflict=0;
    while(changed && !conflict) {
        changed=0;
        for(int ci=0;ci<n_clauses;ci++){
            if(!clause_active[ci]) continue;
            int sat=0, free_count=0, free_var=-1, free_sign=0;
            for(int j=0;j<3;j++){
                int v=clause_var[ci][j], s=clause_sign[ci][j];
                if(var_fixed[v]>=0){
                    if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0)) sat=1;
                } else {
                    free_count++; free_var=v; free_sign=s;
                }
            }
            if(sat){ clause_active[ci]=0; continue; }
            if(free_count==0){ conflict=1; break; }
            if(free_count==1){
                var_fixed[free_var]=(free_sign==1)?1:0;
                changed=1;
            }
        }
    }
    return conflict;
}

/* Physics on ACTIVE clauses only, only FREE variables move */
static double x[MAX_N], vel[MAX_N];

static void physics_on_active(int steps, unsigned long long seed) {
    int n=n_vars, m=n_clauses;
    rng_seed(seed);

    /* Init: tension from ACTIVE clauses only */
    for(int v=0;v<n;v++){
        if(var_fixed[v]>=0){ x[v]=(var_fixed[v]==1)?0.99:0.01; vel[v]=0; continue; }
        double p1=0,p0=0;
        for(int d=0;d<var_degree[v];d++){
            int ci=var_clause_list[v][d],pos=var_clause_pos[v][d];
            if(!clause_active[ci]) continue;
            /* Check if clause is already partially satisfied by fixed vars */
            int sat=0;
            for(int j=0;j<3;j++){
                int vv=clause_var[ci][j],ss=clause_sign[ci][j];
                if(var_fixed[vv]>=0&&((ss==1&&var_fixed[vv]==1)||(ss==-1&&var_fixed[vv]==0)))
                    sat=1;
            }
            if(sat) continue;
            int ss=clause_sign[ci][pos];
            /* Count free vars in this clause */
            int nfree=0;
            for(int j=0;j<3;j++) if(var_fixed[clause_var[ci][j]]<0) nfree++;
            double w=1.0/fmax(nfree,1);
            if(ss==1)p1+=w; else p0+=w;
        }
        x[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;
        vel[v]=0;
    }

    double force[MAX_N];
    for(int step=0;step<steps;step++){
        double prog=(double)step/steps;
        double T=0.20*exp(-4.0*prog)+0.0001;
        double crystal=(prog<0.3)?0.3*prog/0.3:(prog<0.7)?0.3+2.0*(prog-0.3)/0.4:2.3+4.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);

        for(int ci=0;ci<m;ci++){
            if(!clause_active[ci]) continue;
            /* Check if satisfied by fixed vars */
            int sat=0;
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                if(var_fixed[v]>=0&&((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0)))sat=1;}
            if(sat) continue;

            double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                lit[j]=(s==1)?x[v]:(1.0-x[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                if(var_fixed[v]>=0) continue; /* fixed vars don't move */
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}

        for(int v=0;v<n;v++){
            if(var_fixed[v]>=0) continue;
            if(x[v]>0.5)force[v]+=crystal*(1-x[v]);else force[v]-=crystal*x[v];
            vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.04;
            x[v]+=vel[v]*0.04;
            if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}
}

/* ════════════════════════════════════════════════════════
 * DECIMATION SOLVER
 * ════════════════════════════════════════════════════════ */

static int decimation_solve(int nn, int batch_size) {
    int n = nn, m = n_clauses;
    int n_fixed = 0;

    /* Initial UP */
    if(unit_propagate()) return 0; /* conflict */
    for(int v=0;v<n;v++) if(var_fixed[v]>=0) n_fixed++;

    int iteration = 0;
    while(n_fixed < n) {
        /* Count remaining free vars */
        int n_free = n - n_fixed;
        if(n_free == 0) break;

        /* Physics on current (simplified) instance */
        int steps = 200 + n_free * 5; /* fewer steps for smaller instance */
        physics_on_active(steps, 42 + iteration * 7919);

        /* Find the most confident FREE variable(s) */
        /* Fix a BATCH of the most confident */
        int to_fix = (batch_size > 0) ? batch_size : 1;
        if(to_fix > n_free) to_fix = n_free;

        /* Sort free vars by confidence */
        int candidates[MAX_N]; int nc=0;
        for(int v=0;v<n;v++) if(var_fixed[v]<0) candidates[nc++]=v;

        /* Simple selection sort for top `to_fix` */
        for(int i=0; i<to_fix && i<nc; i++){
            int best=i;
            for(int j=i+1;j<nc;j++)
                if(fabs(x[candidates[j]]-0.5) > fabs(x[candidates[best]]-0.5))
                    best=j;
            int tmp=candidates[i];candidates[i]=candidates[best];candidates[best]=tmp;
        }

        /* Fix top `to_fix` variables */
        int conflict = 0;
        for(int i=0; i<to_fix; i++){
            int v = candidates[i];
            var_fixed[v] = (x[v] > 0.5) ? 1 : 0;
            n_fixed++;
        }

        /* UP cascade */
        conflict = unit_propagate();
        if(conflict) {
            /* Backtrack: undo last batch and try opposite for first */
            /* Simple: just try flipping the first of the batch */
            int v0 = candidates[0];
            var_fixed[v0] = 1 - var_fixed[v0];
            /* Re-propagate — need to reset clause_active first */
            /* Simplified: just re-check all clauses */
            for(int ci=0;ci<m;ci++) clause_active[ci]=1;
            for(int ci=0;ci<m;ci++){
                for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                    if(var_fixed[v]>=0&&((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0)))
                        {clause_active[ci]=0;break;}}}
            if(unit_propagate()) return 0; /* both fail */
        }

        /* Recount */
        n_fixed=0;
        for(int v=0;v<n;v++) if(var_fixed[v]>=0) n_fixed++;
        iteration++;

        if(iteration > n) break; /* safety */
    }

    return evaluate_full();
}

/* WalkSAT as fallback */
static int assignment[MAX_N];
static int clause_sat_count[MAX_CLAUSES];
static int walksat(int max_flips){
    int m=n_clauses,n=n_vars;
    for(int v=0;v<n;v++) assignment[v]=(var_fixed[v]>=0)?var_fixed[v]:0;
    for(int ci=0;ci<m;ci++){clause_sat_count[ci]=0;
        for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sat_count[ci]++;}}
    int unsat[MAX_CLAUSES],upos[MAX_CLAUSES],nu=0;
    memset(upos,-1,sizeof(int)*m);
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
    return m-nu;}

/* ════════════════════════════════════════════════════════
 * BENCHMARK
 * ════════════════════════════════════════════════════════ */

int main(void) {
    printf("═══════════════════════════════════════════════════════\n");
    printf("DECIMATION: Physics → fix one → simplify → repeat\n");
    printf("═══════════════════════════════════════════════════════\n\n");

    int test_n[] = {50, 100, 200, 300, 500, 750, 1000};
    int sizes = 7;

    /* Test batch sizes: 1 (pure decimation) and 5 (faster) */
    int batches[] = {1, 3};
    int n_batches = 2;

    for(int bi=0; bi<n_batches; bi++) {
        int batch = batches[bi];
        printf("─── Batch size = %d ───\n", batch);
        printf("%6s | %5s | %6s | %6s | %8s\n",
               "n", "total", "decim", "+walk", "time_ms");
        printf("-------+-------+--------+--------+----------\n");

        for(int ti=0; ti<sizes; ti++) {
            int nn = test_n[ti];
            int n_inst = (nn<=200)?20:(nn<=500?10:5);

            int s_decim=0, s_walk=0, total=0;
            double total_ms=0;

            for(int seed=0; seed<n_inst*3 && total<n_inst; seed++) {
                generate(nn, 4.267, 9000000ULL+seed);
                clock_t t0=clock();

                int sat = decimation_solve(nn, batch);

                if(sat == n_clauses) {
                    s_decim++;
                } else {
                    /* WalkSAT fallback */
                    rng_seed(seed*55555);
                    int sat2 = walksat(nn*300);
                    if(sat2 == n_clauses) s_walk++;
                }

                total++;
                clock_t t1=clock();
                total_ms += (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;

                /* Reset for next instance */
            }

            int solved = s_decim + s_walk;
            printf("%6d | %2d/%2d | %4d   | %4d   | %7.0fms\n",
                   nn, solved, total, s_decim, s_walk, total_ms/total);
            fflush(stdout);
        }
        printf("\n");
    }
    return 0;
}
