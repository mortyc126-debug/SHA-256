/*
 * COMPOSITE SOLVER: Stiffness × Double × Thermal → locate frozen core
 * ═══════════════════════════════════════════════════════════════════
 *
 * Combine all 3 signals into one score per variable.
 * Flip top-k by score. Test at n=50-1000.
 *
 * This is the ULTIMATE test: can physics-based probing crack the
 * exponential barrier?
 *
 * Compile: gcc -O3 -march=native -o composite_solver composite_solver.c -lm
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

/* RNG */
static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void) {
    unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];
    unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;
    unsigned long long t=s1<<17;
    s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);
    rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;
    return r;
}
static void rng_seed(unsigned long long s) {
    rng_s[0]=s; rng_s[1]=s*6364136223846793005ULL+1;
    rng_s[2]=s*1103515245ULL+12345; rng_s[3]=s^0xdeadbeefcafebabeULL;
    for(int i=0;i<20;i++) rng_next();
}
static double rng_double(void) {
    return (rng_next()>>11)*(1.0/9007199254740992.0);
}
static double rng_normal(double m, double s) {
    double u1=rng_double(), u2=rng_double();
    if(u1<1e-15) u1=1e-15;
    return m + s*sqrt(-2*log(u1))*cos(2*M_PI*u2);
}

static void generate(int n, double ratio, unsigned long long seed) {
    n_vars=n; n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES) n_clauses=MAX_CLAUSES;
    rng_seed(seed);
    memset(var_degree,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++) {
        int vs[3];
        vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++) {
            clause_var[ci][j]=vs[j];
            clause_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(var_degree[v]<MAX_DEGREE){
                var_clause_list[v][var_degree[v]]=ci;
                var_clause_pos[v][var_degree[v]]=j;
                var_degree[v]++;
            }
        }
    }
}

static int evaluate(const int *a) {
    int sat=0;
    for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<3;j++) {
            int v=clause_var[ci][j], s=clause_sign[ci][j];
            if((s==1&&a[v]==1)||(s==-1&&a[v]==0)){sat++;break;}
        }
    return sat;
}

/* Physics engine */
static double x[MAX_N], vel[MAX_N];

static void physics_run(int steps, unsigned long long seed) {
    int n=n_vars, m=n_clauses;
    rng_seed(seed);
    /* Tension init */
    for(int v=0;v<n;v++) {
        double p1=0,p0=0;
        for(int d=0;d<var_degree[v];d++) {
            int ci=var_clause_list[v][d], pos=var_clause_pos[v][d];
            if(clause_sign[ci][pos]==1) p1+=1.0/3; else p0+=1.0/3;
        }
        x[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;
        vel[v]=0;
    }
    double force[MAX_N];
    for(int step=0;step<steps;step++) {
        double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double crystal=(prog<0.3)?0.5*prog/0.3:
                       (prog<0.7)?0.5+2.5*(prog-0.3)/0.4:
                                  3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++) {
            double lit[3],prod=1.0;
            for(int j=0;j<3;j++){
                int v=clause_var[ci][j],s=clause_sign[ci][j];
                lit[j]=(s==1)?x[v]:(1.0-x[v]);
                double t=1.0-lit[j]; if(t<1e-12)t=1e-12; prod*=t;
            }
            if(prod<0.0001)continue;
            double w=sqrt(prod);
            for(int j=0;j<3;j++){
                int v=clause_var[ci][j],s=clause_sign[ci][j];
                double t=1.0-lit[j]; if(t<1e-12)t=1e-12;
                force[v]+=s*w*(prod/t);
            }
        }
        for(int v=0;v<n;v++){
            if(x[v]>0.5)force[v]+=crystal*(1.0-x[v]);
            else force[v]-=crystal*x[v];
            double noise=rng_normal(0,T);
            vel[v]=0.93*vel[v]+(force[v]+noise)*0.05;
            x[v]+=vel[v]*0.05;
            if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}
        }
    }
}

/* WalkSAT (from physicsat.c) */
static int assignment[MAX_N];
static int clause_sat_count[MAX_CLAUSES];

static void init_assignment(void) {
    for(int v=0;v<n_vars;v++) assignment[v]=(x[v]>0.5)?1:0;
    for(int ci=0;ci<n_clauses;ci++){
        int cnt=0;
        for(int j=0;j<3;j++){
            int v=clause_var[ci][j],s=clause_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))cnt++;
        }
        clause_sat_count[ci]=cnt;
    }
}

static int walksat(int max_flips) {
    int n=n_vars, m=n_clauses;
    int unsat[MAX_CLAUSES], upos[MAX_CLAUSES], nu=0;
    memset(upos,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)
        if(clause_sat_count[ci]==0){upos[ci]=nu;unsat[nu++]=ci;}
    for(int flip=0;flip<max_flips&&nu>0;flip++){
        int ci=unsat[rng_next()%nu];
        int bv=clause_var[ci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){
            int v=clause_var[ci][j],br=0;
            for(int d=0;d<var_degree[v];d++){
                int oci=var_clause_list[v][d],opos=var_clause_pos[v][d];
                int os=clause_sign[oci][opos];
                if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))
                   &&clause_sat_count[oci]==1) br++;
            }
            if(br==0){zb=v;break;}
            if(br<bb){bb=br;bv=v;}
        }
        int fv=(zb>=0)?zb:((rng_next()%100<30)?clause_var[ci][rng_next()%3]:bv);
        int old=assignment[fv],nw=1-old; assignment[fv]=nw;
        for(int d=0;d<var_degree[fv];d++){
            int oci=var_clause_list[fv][d],opos=var_clause_pos[fv][d];
            int os=clause_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){clause_sat_count[oci]--;
                if(clause_sat_count[oci]==0){upos[oci]=nu;unsat[nu++]=oci;}}
            else if(!was&&now){clause_sat_count[oci]++;
                if(clause_sat_count[oci]==1){int p=upos[oci];
                    if(p>=0&&p<nu){int l=unsat[nu-1];unsat[p]=l;upos[l]=p;upos[oci]=-1;nu--;}}}
        }
    }
    return n_clauses-nu;
}

/* ════════════════════════════════════════════════════════════
 * THE COMPOSITE SOLVER
 * ════════════════════════════════════════════════════════════ */

static double x_run1[MAX_N], x_run2[MAX_N];
static double stiffness[MAX_N];
static double thermal[MAX_N];
static int differ[MAX_N];
static double composite[MAX_N];

static int composite_solve(int nn, int physics_steps) {
    int n = nn, m = n_clauses;

    /* ── Run 1: Physics ── */
    physics_run(physics_steps, 42);
    memcpy(x_run1, x, sizeof(double)*n);
    int a1[MAX_N];
    for(int v=0;v<n;v++) a1[v]=(x[v]>0.5)?1:0;
    int sat1 = evaluate(a1);
    if(sat1 == m) { memcpy(assignment,a1,sizeof(int)*n); return 1; }

    /* ── Run 2: Physics with different seed ── */
    physics_run(physics_steps, 12345);
    memcpy(x_run2, x, sizeof(double)*n);
    int a2[MAX_N];
    for(int v=0;v<n;v++) a2[v]=(x[v]>0.5)?1:0;
    int sat2 = evaluate(a2);
    if(sat2 == m) { memcpy(assignment,a2,sizeof(int)*n); return 2; }

    /* ── Signal 1: DIFFER between runs ── */
    for(int v=0;v<n;v++) differ[v] = (a1[v] != a2[v]) ? 1 : 0;

    /* ── Signal 2: STIFFNESS probe (from run1 state) ── */
    memcpy(x, x_run1, sizeof(double)*n);
    for(int v=0;v<n;v++) {
        double x_save[MAX_N], vel_probe[MAX_N];
        memcpy(x_save, x_run1, sizeof(double)*n);
        memset(vel_probe, 0, sizeof(double)*n);
        x_save[v] = 1.0 - x_run1[v]; /* flip */

        /* Short relaxation (20 steps, no noise) */
        for(int step=0; step<20; step++) {
            double f[MAX_N]; memset(f,0,sizeof(double)*n);
            for(int ci=0;ci<m;ci++){
                double lit[3],prod=1.0;
                for(int j=0;j<3;j++){
                    int vv=clause_var[ci][j],ss=clause_sign[ci][j];
                    lit[j]=(ss==1)?x_save[vv]:(1.0-x_save[vv]);
                    double t=1.0-lit[j]; if(t<1e-12)t=1e-12; prod*=t;
                }
                if(prod<0.001)continue;
                double w=sqrt(prod);
                for(int j=0;j<3;j++){
                    int vv=clause_var[ci][j],ss=clause_sign[ci][j];
                    double t=1.0-lit[j]; if(t<1e-12)t=1e-12;
                    f[vv]+=ss*w*(prod/t);
                }
            }
            for(int vv=0;vv<n;vv++){
                if(x_save[vv]>0.5)f[vv]+=2*(1-x_save[vv]);
                else f[vv]-=2*x_save[vv];
                vel_probe[vv]=0.9*vel_probe[vv]+f[vv]*0.03;
                x_save[vv]+=vel_probe[vv]*0.03;
                if(x_save[vv]<0)x_save[vv]=0;
                if(x_save[vv]>1)x_save[vv]=1;
            }
        }
        stiffness[v] = fabs(x_save[v] - (1.0 - x_run1[v]));
        /* Low stiffness = soft = likely wrong */
    }

    /* ── Signal 3: THERMAL response ── */
    for(int v=0;v<n;v++) {
        int a_test[MAX_N];
        memcpy(a_test, a1, sizeof(int)*n);
        a_test[v] = 1 - a_test[v];
        thermal[v] = (double)(evaluate(a_test) - sat1);
        /* Higher thermal = flipping HELPS = likely wrong */
    }

    /* ── COMPOSITE SCORE ── */
    /* Score = weighted combination:
     *   - Low stiffness (soft) → high score
     *   - Differs between runs → bonus
     *   - High thermal response → high score
     */
    for(int v=0;v<n;v++) {
        double s_soft = 1.0 - stiffness[v]; /* 0=stiff, 1=soft */
        double s_diff = differ[v] ? 1.0 : 0.0;
        double s_therm = (thermal[v] + 2.0) / 4.0; /* normalize ~[-2,2]→[0,1] */
        if(s_therm<0) s_therm=0; if(s_therm>1) s_therm=1;

        composite[v] = 0.4*s_soft + 0.3*s_diff + 0.3*s_therm;
    }

    /* ── TRY: flip top-k by composite score ── */
    /* Sort vars by composite (descending) */
    int sorted[MAX_N];
    for(int v=0;v<n;v++) sorted[v]=v;
    for(int i=0;i<n-1;i++)
        for(int j=i+1;j<n;j++)
            if(composite[sorted[j]]>composite[sorted[i]]) {
                int tmp=sorted[i];sorted[i]=sorted[j];sorted[j]=tmp;
            }

    /* Try flipping top-k for k=1..min(n/4, 20) */
    int best_sat = sat1;
    int best_k = 0;
    int best_a[MAX_N];
    memcpy(best_a, a1, sizeof(int)*n);

    for(int k=1; k<=n/4 && k<=20; k++) {
        int test[MAX_N];
        memcpy(test, a1, sizeof(int)*n);
        for(int i=0;i<k;i++) test[sorted[i]] = 1 - test[sorted[i]];
        int sat = evaluate(test);
        if(sat > best_sat) { best_sat=sat; best_k=k; memcpy(best_a,test,sizeof(int)*n); }
        if(sat == m) { memcpy(assignment,test,sizeof(int)*n); return 3; } /* composite solved! */
    }

    /* ── FALLBACK: WalkSAT from best composite result ── */
    memcpy(assignment, best_a, sizeof(int)*n);
    for(int ci=0;ci<m;ci++){
        int cnt=0;
        for(int j=0;j<3;j++){
            int v=clause_var[ci][j],s=clause_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))cnt++;
        }
        clause_sat_count[ci]=cnt;
    }
    rng_seed(99999);
    int walk_flips = n * 500;
    int final_sat = walksat(walk_flips);
    if(final_sat == m) return 4; /* walksat from composite */

    return 0; /* failed */
}

/* ════════════════════════════════════════════════════════════
 * BENCHMARK
 * ════════════════════════════════════════════════════════════ */

int main(void) {
    printf("══════════════════════════════════════════════════════════\n");
    printf("COMPOSITE SOLVER: Stiffness × Double × Thermal\n");
    printf("══════════════════════════════════════════════════════════\n\n");

    int test_n[] = {50, 75, 100, 150, 200, 300, 500, 750, 1000};
    int n_tests = sizeof(test_n)/sizeof(test_n[0]);

    printf("%6s | %5s | %6s | %6s | %6s | %6s | %8s\n",
           "n", "total", "phys1", "phys2", "compo", "+walk", "time_ms");
    printf("-------+-------+--------+--------+--------+--------+----------\n");

    for(int ti=0; ti<n_tests; ti++) {
        int nn = test_n[ti];
        if(nn > MAX_N) break;

        int n_inst = (nn<=200)?20:(nn<=500?10:5);
        int physics_steps = 2000 + nn*15;

        int s_phys1=0, s_phys2=0, s_composite=0, s_walk=0, total=0;
        double total_ms = 0;

        for(int seed=0; seed<n_inst*3 && total<n_inst; seed++) {
            generate(nn, 4.267, 6000000ULL+seed);

            clock_t t0 = clock();
            int result = composite_solve(nn, physics_steps);
            clock_t t1 = clock();
            double ms = (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;

            total++;
            total_ms += ms;

            if(result >= 1) s_phys1++;  /* any method solved */
            if(result >= 1) {
                if(result==1) s_phys1++;  /* double count: solved by run1 */
                if(result==2) s_phys2++;
                if(result==3) s_composite++;
                if(result==4) s_walk++;
            }
            /* Fix: count properly */
        }

        /* Recount properly */
        s_phys1=0; s_phys2=0; s_composite=0; s_walk=0; total=0;
        total_ms=0;

        for(int seed=0; seed<n_inst*3 && total<n_inst; seed++) {
            generate(nn, 4.267, 6000000ULL+seed);
            clock_t t0 = clock();
            int result = composite_solve(nn, physics_steps);
            clock_t t1 = clock();
            total_ms += (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            total++;
            switch(result) {
                case 1: s_phys1++; break;
                case 2: s_phys2++; break;
                case 3: s_composite++; break;
                case 4: s_walk++; break;
            }
        }

        int solved = s_phys1+s_phys2+s_composite+s_walk;
        double avg_ms = total_ms/total;

        printf("%6d | %2d/%2d | %4d   | %4d   | %4d   | %4d   | %7.0fms\n",
               nn, solved, total, s_phys1, s_phys2, s_composite, s_walk, avg_ms);
        fflush(stdout);
    }

    printf("\nLegend: phys1=run1 solved, phys2=run2 solved,\n");
    printf("        compo=composite flip solved, +walk=walksat from composite\n");

    return 0;
}
