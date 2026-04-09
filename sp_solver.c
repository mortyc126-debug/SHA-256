/*
 * SURVEY PROPAGATION + DECIMATION
 * ════════════════════════════════
 *
 * SP is fundamentally different from everything we've tried:
 * - Physics/tension: estimate VARIABLE VALUES (x_i ∈ {0,1})
 * - SP: estimate PROBABILITY OF BEING FROZEN (η_i→a ∈ [0,1])
 *
 * SP messages are "surveys" — not about values but about
 * the STRUCTURE of the solution space (clusters).
 *
 * SP-guided decimation: converge SP → fix most biased var → repeat
 *
 * Algorithm:
 *   1. Initialize surveys η_{i→a} = random in [0,1]
 *   2. Iterate: update surveys until convergence
 *   3. Compute per-variable bias W_i
 *   4. Fix the variable with largest |W_i|
 *   5. Simplify instance, go to 1
 *   6. When SP trivializes (all η≈0), switch to UP or WalkSAT
 *
 * Compile: gcc -O3 -march=native -o sp_solver sp_solver.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      10000
#define MAX_CLAUSES 50000
#define MAX_K      3
#define MAX_DEGREE 200
#define MAX_SP_ITER 1000
#define SP_EPS     1e-4

static int n_vars, n_clauses;
static int clause_var[MAX_CLAUSES][MAX_K];
static int clause_sign[MAX_CLAUSES][MAX_K];  /* +1 or -1 */
static int clause_active[MAX_CLAUSES];
static int var_fixed[MAX_N];  /* -1=free, 0 or 1 */
static int var_clause_list[MAX_N][MAX_DEGREE];
static int var_clause_pos[MAX_N][MAX_DEGREE];
static int var_degree[MAX_N];

/* SP messages: η[clause][literal_position] = survey from var to clause */
static double eta[MAX_CLAUSES][MAX_K];

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
static double rng_double(void){return(rng_next()>>11)*(1.0/9007199254740992.0);}

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

static int evaluate(void){
    int sat=0;
    for(int ci=0;ci<n_clauses;ci++){
        for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
            int val=(var_fixed[v]>=0)?var_fixed[v]:0;
            if((s==1&&val==1)||(s==-1&&val==0)){sat++;break;}}}
    return sat;}

/* ════════════════════════════════════════════════
 * SURVEY PROPAGATION CORE
 *
 * For 3-SAT clause a = (l1 ∨ l2 ∨ l3):
 *   η_{i→a} = product over OTHER clauses b containing ¬i:
 *             Π_{b∈V⁻(i)\a} [1 - Π_{j∈b\i} (1 - η_{j→b})]
 *           / normalization
 *
 * Simplified SP update (Braunstein, Mézard, Zecchina 2005):
 *
 *   For clause a, literal position j (variable i = clause_var[a][j]):
 *     Let S = sign of i in a (clause_sign[a][j])
 *
 *     Compute for variable i:
 *       Π⁺ = Π over clauses b where i appears POSITIVE and b≠a:
 *            [1 - Π_{k∈b, k≠i} (1 - η_{k→b})]
 *       Π⁻ = same for NEGATIVE appearance
 *       Π⁰ = Π over ALL other clauses b≠a containing i:
 *            [1 - Π_{k∈b, k≠i} (1 - η_{k→b})]... actually the complement
 *
 * Let me use the simpler "warning propagation" version:
 *   u_{a→i} = Π_{j∈a, j≠i} (1 - η_{j→a})
 *   This is the "cavity field": prob that clause a is NOT satisfied
 *   by other literals, so it NEEDS variable i.
 *
 *   η_{i→a} = [Π_{b∈V⁻(i)\a} (1 - u_{b→i})]
 *           / [Π_{b∈V⁻(i)\a} (1 - u_{b→i}) + Π_{b∈V⁺(i)\a} (1 - u_{b→i})]
 *   ... simplified:
 *
 * Actually, let me implement the standard SP from the paper directly.
 * ════════════════════════════════════════════════ */

/* Cavity field: u_{a→i} = probability clause a is a "warning" to variable i */
static double cavity[MAX_CLAUSES][MAX_K]; /* u_{a→i} */

static void sp_init(void) {
    /* Initialize surveys randomly */
    for(int ci=0; ci<n_clauses; ci++)
        for(int j=0; j<MAX_K; j++)
            eta[ci][j] = rng_double() * 0.5;
}

static double sp_iterate(void) {
    /* One iteration of SP. Returns max change. */
    int n=n_vars, m=n_clauses;
    double max_change = 0;

    /* Step 1: Compute cavity fields u_{a→i} from current surveys */
    for(int ci=0; ci<m; ci++) {
        if(!clause_active[ci]) continue;
        for(int j=0; j<MAX_K; j++) {
            if(var_fixed[clause_var[ci][j]] >= 0) { cavity[ci][j]=0; continue; }
            /* u_{a→i} = Π_{k∈a, k≠i} (1 - η_{k→a}) */
            double prod = 1.0;
            for(int k=0; k<MAX_K; k++) {
                if(k==j) continue;
                if(var_fixed[clause_var[ci][k]] >= 0) {
                    /* Fixed var: check if it satisfies this literal */
                    int v=clause_var[ci][k], s=clause_sign[ci][k];
                    if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))
                        prod = 0; /* clause satisfied by fixed var */
                    /* else: fixed var doesn't help → contributes (1-0)=1 */
                } else {
                    prod *= (1.0 - eta[ci][k]);
                }
            }
            cavity[ci][j] = prod;
        }
    }

    /* Step 2: Update surveys η_{i→a} from cavity fields */
    for(int ci=0; ci<m; ci++) {
        if(!clause_active[ci]) continue;
        for(int j=0; j<MAX_K; j++) {
            int i = clause_var[ci][j];
            if(var_fixed[i] >= 0) { eta[ci][j]=0; continue; }
            int s_ia = clause_sign[ci][j]; /* sign of i in clause a */

            /*
             * For variable i in clause a with sign s_ia:
             *   V⁺(i) = clauses where i appears with sign MATCHING s_ia (supporting)
             *   V⁻(i) = clauses where i appears with OPPOSITE sign (contradicting)
             *
             * η_{i→a} ∝ Π_{b∈V⁻\a} u_{b→i}
             *
             * Simplified: η = prob that i is "frozen" by contradicting clauses
             */

            double prod_contra = 1.0; /* product over contradicting clauses */
            double prod_support = 1.0; /* product over supporting clauses */

            for(int d=0; d<var_degree[i]; d++) {
                int bi = var_clause_list[i][d];
                int bpos = var_clause_pos[i][d];
                if(bi == ci) continue; /* skip clause a itself */
                if(!clause_active[bi]) continue;

                int s_ib = clause_sign[bi][bpos]; /* sign of i in clause b */
                double u_bi = cavity[bi][bpos];

                if(s_ib == s_ia) {
                    /* Supporting: clause b wants i the same way as a */
                    prod_support *= (1.0 - u_bi);
                } else {
                    /* Contradicting: clause b wants i the opposite way */
                    prod_contra *= (1.0 - u_bi);
                }
            }

            /* SP update: η = (1-prod_contra) / (1-prod_contra + 1-prod_support + prod_contra*prod_support) */
            /* Simplification for numerical stability */
            double p_contra = 1.0 - prod_contra;  /* prob at least one contradiction is warning */
            double p_support = 1.0 - prod_support;
            double p_both_free = prod_contra * prod_support;

            double denom = p_contra + p_support + p_both_free;
            double new_eta;
            if(denom > 1e-15) {
                new_eta = p_contra / denom;
            } else {
                new_eta = 0;
            }

            /* Damping for stability */
            new_eta = 0.5 * new_eta + 0.5 * eta[ci][j];

            double change = fabs(new_eta - eta[ci][j]);
            if(change > max_change) max_change = change;
            eta[ci][j] = new_eta;
        }
    }

    return max_change;
}

/* Compute per-variable bias from converged SP */
static void sp_bias(double *W_plus, double *W_minus, double *W_zero) {
    int n=n_vars, m=n_clauses;

    for(int i=0; i<n; i++) {
        W_plus[i] = W_minus[i] = W_zero[i] = 0;
        if(var_fixed[i] >= 0) continue;

        double prod_pos = 1.0; /* Π over clauses wanting i=1: (1 - u) */
        double prod_neg = 1.0; /* Π over clauses wanting i=0: (1 - u) */

        for(int d=0; d<var_degree[i]; d++) {
            int ci = var_clause_list[i][d];
            int pos = var_clause_pos[i][d];
            if(!clause_active[ci]) continue;

            int s = clause_sign[ci][pos];
            double u = cavity[ci][pos];

            if(s == 1) {
                prod_neg *= (1.0 - u); /* clause wants i=1, so it's a "negative" warning if i=0 */
            } else {
                prod_pos *= (1.0 - u); /* clause wants i=0, warning if i=1 */
            }
        }

        /* W⁺ = prob i should be 1 */
        double pi_plus = 1.0 - prod_pos;   /* prob forced to 1 */
        double pi_minus = 1.0 - prod_neg;  /* prob forced to 0 */
        double pi_zero = prod_pos * prod_neg; /* prob free */

        double total = pi_plus + pi_minus + pi_zero;
        if(total > 1e-15) {
            W_plus[i] = pi_plus / total;
            W_minus[i] = pi_minus / total;
            W_zero[i] = pi_zero / total;
        } else {
            W_zero[i] = 1.0;
        }
    }
}

/* Unit propagation */
static int unit_propagate(void) {
    int changed=1;
    while(changed){changed=0;
        for(int ci=0;ci<n_clauses;ci++){
            if(!clause_active[ci])continue;
            int sat=0,fc=0,fv=-1,fs=0;
            for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}
                else{fc++;fv=v;fs=s;}}
            if(sat){clause_active[ci]=0;continue;}
            if(fc==0)return 1;
            if(fc==1){var_fixed[fv]=(fs==1)?1:0;changed=1;}}}
    return 0;}

/* WalkSAT fallback */
static int walksat(int max_flips){
    int a[MAX_N],m=n_clauses,n=n_vars;
    for(int v=0;v<n;v++)a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    int sc[MAX_CLAUSES];
    for(int ci=0;ci<m;ci++){sc[ci]=0;for(int j=0;j<3;j++){
        int v=clause_var[ci][j],s=clause_sign[ci][j];
        if((s==1&&a[v]==1)||(s==-1&&a[v]==0))sc[ci]++;}}
    int unsat[MAX_CLAUSES],upos[MAX_CLAUSES],nu=0;
    memset(upos,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(sc[ci]==0){upos[ci]=nu;unsat[nu++]=ci;}
    for(int f=0;f<max_flips&&nu>0;f++){
        int ci=unsat[rng_next()%nu];
        int bv=clause_var[ci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=clause_var[ci][j],br=0;
            for(int d=0;d<var_degree[v];d++){
                int oci=var_clause_list[v][d],opos=var_clause_pos[v][d];
                int os=clause_sign[oci][opos];
                if(((os==1&&a[v]==1)||(os==-1&&a[v]==0))&&sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?clause_var[ci][rng_next()%3]:bv);
        int old=a[fv],nw=1-old;a[fv]=nw;
        for(int d=0;d<var_degree[fv];d++){
            int oci=var_clause_list[fv][d],opos=var_clause_pos[fv][d];
            int os=clause_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){sc[oci]--;if(sc[oci]==0){upos[oci]=nu;unsat[nu++]=oci;}}
            else if(!was&&now){sc[oci]++;if(sc[oci]==1){int p=upos[oci];
                if(p>=0&&p<nu){int l=unsat[nu-1];unsat[p]=l;upos[l]=p;upos[oci]=-1;nu--;}}}}}
    /* Copy back */
    for(int v=0;v<n;v++) var_fixed[v]=a[v];
    return m-nu;}

/* ════════════════════════════════════════════════
 * SP-GUIDED DECIMATION SOLVER
 * ════════════════════════════════════════════════ */

static int sp_solve(int nn) {
    int n=nn, m=n_clauses;
    double W_plus[MAX_N], W_minus[MAX_N], W_zero[MAX_N];

    /* Initial UP */
    if(unit_propagate()) return 0;

    int n_fixed = 0;
    for(int v=0;v<n;v++) if(var_fixed[v]>=0) n_fixed++;

    int sp_rounds = 0;

    while(n_fixed < n) {
        int n_free = n - n_fixed;

        /* Run SP to convergence */
        sp_init();
        int converged = 0;
        for(int iter=0; iter<MAX_SP_ITER; iter++) {
            double change = sp_iterate();
            if(change < SP_EPS) { converged=1; break; }
        }

        /* Compute bias */
        sp_bias(W_plus, W_minus, W_zero);

        /* Check if SP has trivialized (all W_zero ≈ 1) */
        double max_bias = 0;
        int best_var = -1, best_val = 0;
        for(int v=0; v<n; v++) {
            if(var_fixed[v] >= 0) continue;
            double bias = fabs(W_plus[v] - W_minus[v]);
            if(bias > max_bias) {
                max_bias = bias;
                best_var = v;
                best_val = (W_plus[v] > W_minus[v]) ? 1 : 0;
            }
        }

        if(max_bias < 0.01 || best_var < 0) {
            /* SP trivialized — switch to WalkSAT */
            rng_seed(sp_rounds * 12345 + 777);
            int sat = walksat(n * 500);
            return sat;
        }

        /* Fix the most biased variable */
        var_fixed[best_var] = best_val;
        n_fixed++;

        /* Simplify: mark satisfied clauses inactive */
        for(int d=0; d<var_degree[best_var]; d++) {
            int ci = var_clause_list[best_var][d];
            if(!clause_active[ci]) continue;
            int pos = var_clause_pos[best_var][d];
            int s = clause_sign[ci][pos];
            if((s==1 && best_val==1) || (s==-1 && best_val==0))
                clause_active[ci] = 0;
        }

        /* UP cascade */
        if(unit_propagate()) {
            /* Conflict — try opposite */
            var_fixed[best_var] = 1 - best_val;
            /* Reset clause_active */
            for(int ci=0;ci<m;ci++){clause_active[ci]=1;
                for(int j=0;j<3;j++){int v=clause_var[ci][j],s=clause_sign[ci][j];
                    if(var_fixed[v]>=0&&((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0)))
                        {clause_active[ci]=0;break;}}}
            if(unit_propagate()) {
                /* Both fail — WalkSAT fallback */
                rng_seed(sp_rounds * 99999);
                return walksat(n * 500);
            }
        }

        n_fixed = 0;
        for(int v=0;v<n;v++) if(var_fixed[v]>=0) n_fixed++;
        sp_rounds++;
    }

    return evaluate();
}

/* ════════════════════════════════════════════════
 * BENCHMARK
 * ════════════════════════════════════════════════ */

int main(void) {
    printf("══════════════════════════════════════════════\n");
    printf("SURVEY PROPAGATION + DECIMATION\n");
    printf("══════════════════════════════════════════════\n\n");

    int test_n[] = {50, 100, 200, 300, 500, 750, 1000, 1500, 2000};
    int sizes = 9;

    printf("%6s | %5s | %6s | %8s\n", "n", "total", "solved", "time_ms");
    printf("-------+-------+--------+----------\n");

    for(int ti=0; ti<sizes; ti++) {
        int nn = test_n[ti];
        int n_inst = (nn<=200)?20:(nn<=500?10:(nn<=1000?5:3));

        int solved=0, total=0;
        double total_ms=0;

        for(int seed=0; seed<n_inst*3 && total<n_inst; seed++) {
            generate(nn, 4.267, 10000000ULL+seed);
            clock_t t0=clock();

            int sat = sp_solve(nn);

            clock_t t1=clock();
            total_ms += (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            total++;

            if(sat == n_clauses) solved++;
        }

        printf("%6d | %2d/%2d | %4d   | %7.0fms\n",
               nn, solved, total, solved, total_ms/total);
        fflush(stdout);
    }

    printf("\nComparison: PhysicsSAT best = 4/20 at n=500, 0 at n=750+\n");
    printf("If SP breaks n=1000+: fundamentally different paradigm works!\n");

    return 0;
}
