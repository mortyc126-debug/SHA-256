/*
 * probSAT: State-of-art stochastic local search for 3-SAT
 * =========================================================
 *
 * Balint & Schöning (2012): "Choosing probability distributions for
 * stochastic local search and the role of make vs. break"
 *
 * Key idea: instead of SKC (zero-break preference + random walk),
 * use a probability distribution based on make/break counts:
 *
 *   For each variable v in unsatisfied clause:
 *     break(v) = #currently-sat clauses that become unsat if v is flipped
 *     make(v)  = #currently-unsat clauses that become sat if v is flipped
 *
 *   Probability of flipping v ∝ f(break(v))
 *   where f(b) = pow(cb, -break) for "break-only" version
 *   or f(m,b) = pow(cb, -break) * pow(cm, make) for full version
 *
 * probSAT uses: P(v) ∝ (epsilon + break(v))^{-cb}
 * with cb ≈ 2.06 for 3-SAT (tuned on competition benchmarks)
 *
 * This is MUCH more effective than SKC WalkSAT for hard instances.
 *
 * Compile: gcc -O3 -march=native -o probsat probsat.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       20000
#define MAX_CLAUSES 100000
#define MAX_K       3
#define MAX_DEGREE  300

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

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

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
    rng_seed(seed);memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}
        }
    }
}

/* ============================================================
 * probSAT local search
 *
 * Parameters (from Balint & Schöning 2012 for k=3):
 *   cb = 2.06  (break exponent)
 *   eps = 1.0  (smoothing)
 * ============================================================ */

static int a[MAX_N];         /* current assignment */
static int sc[MAX_CLAUSES];  /* sat count per clause */

/* Unsat list with O(1) add/remove */
static int ulist[MAX_CLAUSES];
static int upos[MAX_CLAUSES];
static int nu;

static inline void init_assignment(int n, int m, const int *init) {
    if(init) {
        memcpy(a, init, sizeof(int)*n);
    } else {
        for(int v=0; v<n; v++) a[v] = rng_next() & 1;
    }
    memset(sc, 0, sizeof(int)*m);
    for(int ci=0; ci<m; ci++)
        for(int j=0; j<3; j++) {
            int v=cl_var[ci][j], s=cl_sign[ci][j];
            if((s==1 && a[v]==1) || (s==-1 && a[v]==0)) sc[ci]++;
        }
    nu = 0;
    memset(upos, -1, sizeof(int)*m);
    for(int ci=0; ci<m; ci++)
        if(sc[ci]==0) { upos[ci]=nu; ulist[nu++]=ci; }
}

static inline void flip_var(int fv, int m) {
    int old=a[fv], nw=1-old;
    a[fv] = nw;
    for(int d=0; d<vdeg[fv]; d++) {
        int oci=vlist[fv][d], opos=vpos[fv][d];
        int os=cl_sign[oci][opos];
        int was=((os==1 && old==1) || (os==-1 && old==0));
        int now=((os==1 && nw==1) || (os==-1 && nw==0));
        if(was && !now) {
            sc[oci]--;
            if(sc[oci]==0) { upos[oci]=nu; ulist[nu++]=oci; }
        } else if(!was && now) {
            sc[oci]++;
            if(sc[oci]==1) {
                int p=upos[oci];
                if(p>=0 && p<nu) {
                    int l=ulist[nu-1];
                    ulist[p]=l; upos[l]=p; upos[oci]=-1; nu--;
                }
            }
        }
    }
}

/* Compute break(v) = number of currently-sat clauses with sc==1 containing v in satisfying position */
static inline int compute_break(int v) {
    int br = 0;
    for(int d=0; d<vdeg[v]; d++) {
        int oci=vlist[v][d], opos=vpos[v][d];
        int os=cl_sign[oci][opos];
        /* v currently satisfies oci? */
        if(((os==1 && a[v]==1) || (os==-1 && a[v]==0)) && sc[oci]==1)
            br++;
    }
    return br;
}

static int probsat(int n, int m, int max_flips, const int *init) {
    double cb = 2.06;  /* break exponent for 3-SAT */
    double eps = 1.0;

    /* Precompute power table for break values 0..max_degree */
    double pow_table[MAX_DEGREE+1];
    for(int b=0; b<=MAX_DEGREE && b<=50; b++)
        pow_table[b] = pow(eps + b, -cb);
    for(int b=51; b<=MAX_DEGREE; b++)
        pow_table[b] = 0.0; /* negligible */

    init_assignment(n, m, init);

    for(int f=0; f<max_flips && nu>0; f++) {
        /* Pick random unsatisfied clause */
        int ci = ulist[rng_next() % nu];

        /* For each variable in clause, compute flip probability */
        double probs[3];
        int vars[3];
        double sum = 0;

        for(int j=0; j<3; j++) {
            vars[j] = cl_var[ci][j];
            int br = compute_break(vars[j]);
            probs[j] = (br <= 50) ? pow_table[br] : pow(eps + br, -cb);
            sum += probs[j];
        }

        /* Sample proportionally */
        double r = rng_double() * sum;
        int fv;
        if(r < probs[0]) fv = vars[0];
        else if(r < probs[0] + probs[1]) fv = vars[1];
        else fv = vars[2];

        flip_var(fv, m);
    }

    return nu;
}

/* ============================================================
 * Classic WalkSAT (SKC) for comparison
 * ============================================================ */
static int walksat_skc(int n, int m, int max_flips, const int *init) {
    init_assignment(n, m, init);

    for(int f=0; f<max_flips && nu>0; f++) {
        int ci = ulist[rng_next() % nu];
        int bv=cl_var[ci][0], bb=m+1, zb=-1;
        for(int j=0; j<3; j++) {
            int v=cl_var[ci][j];
            int br = compute_break(v);
            if(br==0) { zb=v; break; }
            if(br<bb) { bb=br; bv=v; }
        }
        int fv = (zb>=0) ? zb : ((rng_next()%100<57) ? cl_var[ci][rng_next()%3] : bv);
        flip_var(fv, m);
    }

    return nu;
}

/* ============================================================
 * BENCHMARK: probSAT vs WalkSAT head-to-head
 * ============================================================ */
int main(void) {
    printf("════════════════════════════════════════════════\n");
    printf("probSAT vs WalkSAT: head-to-head comparison\n");
    printf("════════════════════════════════════════════════\n");
    printf("probSAT: P(flip v) ∝ (ε + break(v))^{-cb}\n");
    printf("WalkSAT: SKC heuristic, noise=57%%\n\n");

    int test_n[] = {200, 500, 1000, 2000, 3000, 5000};
    double ratios[] = {4.0, 4.267};

    for(int ri=0; ri<2; ri++) {
        printf("α=%.3f:\n", ratios[ri]);
        printf("  %6s | %8s %6s | %8s %6s | flips\n",
               "n", "probSAT","rate", "WalkSAT","rate");
        printf("  -------+------------------+------------------+------\n");

        for(int ti=0; ti<6; ti++) {
            int nn=test_n[ti];
            int ni = (nn<=200)?20 : (nn<=500?10 : (nn<=2000?5:3));
            int max_flips = nn * 5000;
            if(max_flips > 50000000) max_flips = 50000000;

            int ps_solved=0, ws_solved=0, total=0;
            double ps_ms=0, ws_ms=0;

            for(int seed=0; seed<ni*3 && total<ni; seed++) {
                generate(nn, ratios[ri], 11000000ULL+seed);
                int n=nn, m=n_clauses;

                /* probSAT */
                clock_t t0=clock();
                int best_ps = m;
                for(int restart=0; restart<5; restart++) {
                    rng_seed(seed*31337ULL + restart*99991ULL);
                    int unsat = probsat(n, m, max_flips, NULL);
                    if(unsat < best_ps) best_ps = unsat;
                    if(unsat == 0) break;
                }
                clock_t t1=clock();
                ps_ms += (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
                if(best_ps == 0) ps_solved++;

                /* WalkSAT */
                clock_t t2=clock();
                int best_ws = m;
                for(int restart=0; restart<5; restart++) {
                    rng_seed(seed*31337ULL + restart*99991ULL + 77777ULL);
                    int unsat = walksat_skc(n, m, max_flips, NULL);
                    if(unsat < best_ws) best_ws = unsat;
                    if(unsat == 0) break;
                }
                clock_t t3=clock();
                ws_ms += (double)(t3-t2)*1000.0/CLOCKS_PER_SEC;
                if(best_ws == 0) ws_solved++;

                total++;
            }

            printf("  %6d | %3d/%2d %3.0f%%  %4.0fms | %3d/%2d %3.0f%%  %4.0fms | %dK\n",
                   nn,
                   ps_solved, total, 100.0*ps_solved/total, ps_ms/total,
                   ws_solved, total, 100.0*ws_solved/total, ws_ms/total,
                   max_flips/1000);
            fflush(stdout);
        }
        printf("\n");
    }

    printf("If probSAT >> WalkSAT: replace WalkSAT in SP pipeline.\n");
    return 0;
}
