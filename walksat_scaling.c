/*
 * THE OPEN QUESTION: WalkSAT from 99% — polynomial or exponential?
 *
 * Strategy:
 *   1. Generate random 3-SAT at threshold
 *   2. Run PhysicsSAT to get ~99% satisfaction
 *   3. Count EXACT flips WalkSAT needs to reach 100%
 *   4. Plot flips(n) — polynomial or exponential?
 *
 * If flips ~ n^c  →  P = NP (for random SAT)
 * If flips ~ 2^f(n)  →  last 1% concentrates all hardness
 *
 * Compile: gcc -O3 -march=native -o walksat_scaling walksat_scaling.c -lm
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
static double rng_normal(double m, double s) {
    double u1=(rng_next()>>11)*(1.0/9007199254740992.0);
    double u2=(rng_next()>>11)*(1.0/9007199254740992.0);
    if(u1<1e-15) u1=1e-15;
    return m + s*sqrt(-2*log(u1))*cos(2*M_PI*u2);
}

static void generate(int n, double ratio, unsigned long long seed) {
    n_vars = n;
    n_clauses = (int)(ratio * n);
    rng_seed(seed);
    memset(var_degree, 0, sizeof(int)*n);
    for(int ci=0; ci<n_clauses; ci++) {
        int vs[3];
        vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++) {
            clause_var[ci][j]=vs[j];
            clause_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(var_degree[v]<MAX_DEGREE) {
                var_clause_list[v][var_degree[v]]=ci;
                var_clause_pos[v][var_degree[v]]=j;
                var_degree[v]++;
            }
        }
    }
}

/* Physics simulation (simplified, fast) */
static double x[MAX_N], vel[MAX_N];

static void physics_run(int steps) {
    int n=n_vars, m=n_clauses;
    /* Tension init */
    for(int v=0;v<n;v++) {
        double p1=0,p0=0;
        for(int d=0;d<var_degree[v];d++) {
            int ci=var_clause_list[v][d], pos=var_clause_pos[v][d];
            if(clause_sign[ci][pos]==1) p1+=1.0/3; else p0+=1.0/3;
        }
        x[v] = (p1+p0>0) ? 0.5+0.35*(p1-p0)/(p1+p0) : 0.5;
        vel[v] = 0;
    }
    double force[MAX_N];
    for(int step=0; step<steps; step++) {
        double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double crystal = (prog<0.3) ? 0.5*prog/0.3 :
                         (prog<0.7) ? 0.5+2.5*(prog-0.3)/0.4 :
                                      3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++) {
            double lit[3], prod=1.0;
            for(int j=0;j<3;j++) {
                int v=clause_var[ci][j], s=clause_sign[ci][j];
                lit[j]=(s==1)?x[v]:(1.0-x[v]);
                double t=1.0-lit[j]; if(t<1e-12)t=1e-12;
                prod*=t;
            }
            if(prod<0.0001) continue;
            double w=sqrt(prod);
            for(int j=0;j<3;j++) {
                int v=clause_var[ci][j], s=clause_sign[ci][j];
                double t=1.0-lit[j]; if(t<1e-12)t=1e-12;
                force[v] += s*w*(prod/t);
            }
        }
        for(int v=0;v<n;v++) {
            if(x[v]>0.5) force[v]+=crystal*(1.0-x[v]);
            else force[v]-=crystal*x[v];
            double noise=rng_normal(0,T);
            vel[v]=0.93*vel[v]+(force[v]+noise)*0.05;
            x[v]+=vel[v]*0.05;
            if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}
        }
    }
}

/* WalkSAT with EXACT flip counting */
static int assignment[MAX_N];
static int clause_sat_count[MAX_CLAUSES];

static void init_from_physics(void) {
    for(int v=0;v<n_vars;v++)
        assignment[v]=(x[v]>0.5)?1:0;
    for(int ci=0;ci<n_clauses;ci++) {
        int cnt=0;
        for(int j=0;j<3;j++) {
            int v=clause_var[ci][j], s=clause_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0)) cnt++;
        }
        clause_sat_count[ci]=cnt;
    }
}

static long long walksat_count_flips(int max_flips) {
    int n=n_vars, m=n_clauses;
    int unsat[MAX_CLAUSES], unsat_pos[MAX_CLAUSES];
    int n_unsat=0;
    memset(unsat_pos,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++) {
        if(clause_sat_count[ci]==0) {
            unsat_pos[ci]=n_unsat;
            unsat[n_unsat++]=ci;
        }
    }
    if(n_unsat==0) return 0;

    for(long long flip=0; flip<max_flips && n_unsat>0; flip++) {
        int idx=rng_next()%n_unsat;
        int ci=unsat[idx];
        /* Find best var (min breaks) or freebie */
        int best_v=clause_var[ci][0], best_b=m+1, zero=-1;
        for(int j=0;j<3;j++) {
            int v=clause_var[ci][j], breaks=0;
            for(int d=0;d<var_degree[v];d++) {
                int oci=var_clause_list[v][d], opos=var_clause_pos[v][d];
                int os=clause_sign[oci][opos];
                int is_true=((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0));
                if(is_true&&clause_sat_count[oci]==1) breaks++;
            }
            if(breaks==0){zero=v;break;}
            if(breaks<best_b){best_b=breaks;best_v=v;}
        }
        int fv;
        if(zero>=0) fv=zero;
        else if((rng_next()%100)<30) fv=clause_var[ci][rng_next()%3];
        else fv=best_v;

        int old=assignment[fv], nw=1-old;
        assignment[fv]=nw;
        for(int d=0;d<var_degree[fv];d++) {
            int oci=var_clause_list[fv][d], opos=var_clause_pos[fv][d];
            int os=clause_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now) {
                clause_sat_count[oci]--;
                if(clause_sat_count[oci]==0){unsat_pos[oci]=n_unsat;unsat[n_unsat++]=oci;}
            } else if(!was&&now) {
                clause_sat_count[oci]++;
                if(clause_sat_count[oci]==1) {
                    int pos=unsat_pos[oci];
                    if(pos>=0&&pos<n_unsat) {
                        int last=unsat[n_unsat-1];
                        unsat[pos]=last; unsat_pos[last]=pos;
                        unsat_pos[oci]=-1; n_unsat--;
                    }
                }
            }
        }
        if(n_unsat==0) return flip+1;
    }
    return -1; /* failed */
}

int main(int argc, char **argv) {
    printf("================================================================\n");
    printf("THE OPEN QUESTION: WalkSAT from physics — how does it scale?\n");
    printf("================================================================\n\n");

    int test_n[] = {50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000};
    int n_tests = sizeof(test_n)/sizeof(test_n[0]);

    printf("%6s | %4s | %8s | %10s | %8s | %10s | %8s\n",
           "n", "inst", "unsat", "flips", "flips/n", "flips/n^2", "status");
    printf("-------+------+----------+------------+----------+------------+---------\n");

    for(int ti=0; ti<n_tests; ti++) {
        int nn = test_n[ti];
        if(nn > MAX_N) break;

        int n_inst = (nn<=200) ? 20 : (nn<=500 ? 10 : 5);
        int physics_steps = 2000 + nn*20;
        long long max_flips = (long long)nn * nn * 10; /* n² × 10 budget */
        if(max_flips > 100000000LL) max_flips = 100000000LL;

        int solved=0, total=0;
        long long total_flips=0;
        int total_unsat_before=0;

        for(int seed=0; seed<n_inst*3 && total<n_inst; seed++) {
            generate(nn, 4.267, 2000000ULL+seed);

            /* Physics */
            rng_seed(42+seed*7919);
            physics_run(physics_steps);
            init_from_physics();

            /* Count unsat before WalkSAT */
            int unsat_before=0;
            for(int ci=0;ci<n_clauses;ci++)
                if(clause_sat_count[ci]==0) unsat_before++;

            if(unsat_before==0) {
                solved++; total++; continue;
            }

            /* WalkSAT */
            rng_seed(seed*12345+nn);
            long long flips = walksat_count_flips(max_flips);

            total++;
            total_unsat_before += unsat_before;

            if(flips >= 0) {
                solved++;
                total_flips += flips;
            }
        }

        double avg_flips = (solved>0) ? (double)total_flips/solved : -1;
        double avg_unsat = (total>0) ? (double)total_unsat_before/total : 0;

        if(solved > 0) {
            printf("%6d | %2d/%2d | %8.1f | %10.0f | %8.1f | %10.4f | SOLVED\n",
                   nn, solved, total, avg_unsat, avg_flips,
                   avg_flips/nn, avg_flips/((double)nn*nn));
        } else {
            printf("%6d | %2d/%2d | %8.1f | %10s | %8s | %10s | FAILED\n",
                   nn, solved, total, avg_unsat, "—", "—", "—");
        }
        fflush(stdout);
    }

    printf("\n");
    printf("INTERPRETATION:\n");
    printf("  If flips/n  ≈ const → WalkSAT is O(n)    → POLYNOMIAL\n");
    printf("  If flips/n² ≈ const → WalkSAT is O(n²)   → POLYNOMIAL\n");
    printf("  If flips/n² grows   → WalkSAT is > O(n²)  → check if exponential\n");
    printf("  If FAILED at large n → exponential barrier exists\n");

    return 0;
}
