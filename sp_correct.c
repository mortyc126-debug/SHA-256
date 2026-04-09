/*
 * CORRECT Survey Propagation (Braunstein, Mézard, Zecchina 2005)
 * ═══════════════════════════════════════════════════════════════
 *
 * FIXED all 5 bugs from previous implementation:
 *   1. Messages: η_{a→i} = clause-to-variable (not var-to-clause)
 *   2. Cavity: uses ALL clauses of each variable (not just within-clause)
 *   3. Update: product of normalized P_u over other vars in clause
 *   4. Classification: relative to each var j's sign in clause a
 *   5. Bias: uses η directly, not derived cavity values
 *
 * Compile: gcc -O3 -march=native -o sp_correct sp_correct.c -lm
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
#define SP_MAX_ITER 300
#define SP_EPS     1e-3

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K]; /* +1 or -1 */
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N]; /* -1=free, 0 or 1 */

/* Adjacency: for each variable, list of (clause_index, position_in_clause) */
static int vlist[MAX_N][MAX_DEGREE]; /* clause index */
static int vpos[MAX_N][MAX_DEGREE];  /* position in clause */
static int vdeg[MAX_N];

/* SP messages: η[clause][position] = survey from CLAUSE to VARIABLE */
static double eta[MAX_CLAUSES][MAX_K];

/* RNG */
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

static void generate(int n, double ratio, unsigned long long seed){
    n_vars=n; n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES) n_clauses=MAX_CLAUSES;
    rng_seed(seed); memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3]; vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            cl_var[ci][j]=vs[j]; cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}
        }
    }
    for(int ci=0;ci<n_clauses;ci++) cl_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
}

static int evaluate(void){
    int sat=0;
    for(int ci=0;ci<n_clauses;ci++){
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j],s=cl_sign[ci][j];
            int val=(var_fixed[v]>=0)?var_fixed[v]:0;
            if((s==1&&val==1)||(s==-1&&val==0)){sat++;break;}}}
    return sat;}

/* ════════════════════════════════════════════════
 * CORRECT SP UPDATE
 *
 * For edge (clause a, variable i at position pos_i):
 *
 *   η_{a→i} = Π_{j in a, j≠i} [ P_u(j→a) / (P_u+P_s+P_0+P_c)(j→a) ]
 *
 * where for variable j with sign J_{j,a} in clause a:
 *   prod_s = Π_{b∈same(j,a)} (1 - η_{b→j})
 *   prod_u = Π_{b∈oppo(j,a)} (1 - η_{b→j})
 *   P_u = (1-prod_u) * prod_s
 *   P_s = (1-prod_s) * prod_u
 *   P_0 = prod_u * prod_s
 *   P_c = (1-prod_u) * (1-prod_s)
 *
 * same(j,a) = {b≠a : j∈b, J_{j,b}=J_{j,a}}  (same sign)
 * oppo(j,a) = {b≠a : j∈b, J_{j,b}≠J_{j,a}}  (opposite sign)
 * ════════════════════════════════════════════════ */

static double sp_update_one_edge(int ci, int pos_i) {
    /* Compute new η_{a→i} for clause ci, variable at position pos_i */
    int var_i = cl_var[ci][pos_i];
    if(var_fixed[var_i] >= 0) return 0; /* fixed → no survey */

    double product = 1.0;

    /* For each OTHER variable j in clause ci */
    for(int pj = 0; pj < MAX_K; pj++) {
        if(pj == pos_i) continue;
        int j = cl_var[ci][pj];
        if(var_fixed[j] >= 0) {
            /* Fixed var: check if it satisfies its literal in clause ci */
            int sj = cl_sign[ci][pj];
            if((sj==1 && var_fixed[j]==1) || (sj==-1 && var_fixed[j]==0)) {
                /* j satisfies clause a → η_{a→i} = 0 */
                return 0;
            }
            /* j is fixed but doesn't satisfy → acts like P_u=1 */
            /* product *= 1.0 (no change) */
            continue;
        }

        int sign_j_in_a = cl_sign[ci][pj]; /* J_{j,a} */

        /* Compute prod_s and prod_u for variable j relative to clause a */
        double prod_s = 1.0; /* Π over same-sign clauses */
        double prod_u = 1.0; /* Π over opposite-sign clauses */

        for(int d = 0; d < vdeg[j]; d++) {
            int bi = vlist[j][d]; /* clause b */
            int bp = vpos[j][d];  /* position of j in b */
            if(bi == ci) continue; /* skip clause a itself */
            if(!cl_active[bi]) continue; /* skip inactive */

            /* Check if clause b is already satisfied by some fixed var */
            int b_sat = 0;
            for(int k=0; k<MAX_K; k++) {
                int vk = cl_var[bi][k];
                if(var_fixed[vk] >= 0) {
                    int sk = cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))
                        { b_sat=1; break; }
                }
            }
            if(b_sat) continue; /* satisfied clause → no warning */

            int sign_j_in_b = cl_sign[bi][bp]; /* J_{j,b} */
            double eta_b_to_j = eta[bi][bp]; /* η_{b→j} */

            if(sign_j_in_b == sign_j_in_a) {
                /* Same sign: clause b is "supporting" for j wrt clause a */
                prod_s *= (1.0 - eta_b_to_j);
            } else {
                /* Opposite sign: clause b "contradicts" clause a's need */
                prod_u *= (1.0 - eta_b_to_j);
            }
        }

        /* Compute cavity probabilities for j→a */
        double P_u = (1.0 - prod_u) * prod_s;
        double P_s = (1.0 - prod_s) * prod_u;
        double P_0 = prod_u * prod_s;
        double P_c = (1.0 - prod_u) * (1.0 - prod_s);
        double total = P_u + P_s + P_0 + P_c;

        double p_j;
        if(total > 1e-15) {
            p_j = P_u / total;
        } else {
            p_j = 0;
        }

        product *= p_j;
    }

    return product;
}

static double sp_iterate(void) {
    double max_change = 0;
    int m = n_clauses;

    for(int ci = 0; ci < m; ci++) {
        if(!cl_active[ci]) continue;
        for(int p = 0; p < MAX_K; p++) {
            double new_eta = sp_update_one_edge(ci, p);
            double change = fabs(new_eta - eta[ci][p]);
            if(change > max_change) max_change = change;
            /* Damping for stability */
            eta[ci][p] = 0.5 * new_eta + 0.5 * eta[ci][p];
        }
    }
    return max_change;
}

/* ════════════════════════════════════════════════
 * CORRECT BIAS COMPUTATION
 *
 * For variable i:
 *   prod_plus  = Π_{a: J_{i,a}=+1} (1 - η_{a→i})
 *   prod_minus = Π_{a: J_{i,a}=-1} (1 - η_{a→i})
 *   π+ = (1-prod_plus) × prod_minus
 *   π- = (1-prod_minus) × prod_plus
 *   π0 = prod_plus × prod_minus
 * ════════════════════════════════════════════════ */

static double W_plus[MAX_N], W_minus[MAX_N], W_zero[MAX_N];

static void sp_compute_bias(void) {
    int n = n_vars;
    for(int i = 0; i < n; i++) {
        W_plus[i] = W_minus[i] = 0; W_zero[i] = 1;
        if(var_fixed[i] >= 0) continue;

        double prod_plus = 1.0;  /* Π over clauses where sign=+1 */
        double prod_minus = 1.0; /* Π over clauses where sign=-1 */

        for(int d = 0; d < vdeg[i]; d++) {
            int ci = vlist[i][d];
            int p = vpos[i][d];
            if(!cl_active[ci]) continue;

            /* Check if clause satisfied by other fixed vars */
            int sat = 0;
            for(int k=0; k<MAX_K; k++) {
                int vk = cl_var[ci][k];
                if(vk != i && var_fixed[vk] >= 0) {
                    int sk = cl_sign[ci][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))
                        { sat=1; break; }
                }
            }
            if(sat) continue;

            int s = cl_sign[ci][p]; /* J_{i,a} */
            double e = eta[ci][p];  /* η_{a→i} */

            if(s == 1) {
                prod_plus *= (1.0 - e);
            } else {
                prod_minus *= (1.0 - e);
            }
        }

        double pi_plus  = (1.0 - prod_plus) * prod_minus;
        double pi_minus = (1.0 - prod_minus) * prod_plus;
        double pi_zero  = prod_plus * prod_minus;
        double total = pi_plus + pi_minus + pi_zero;

        if(total > 1e-15) {
            W_plus[i]  = pi_plus / total;
            W_minus[i] = pi_minus / total;
            W_zero[i]  = pi_zero / total;
        } else {
            W_zero[i] = 1.0;
        }
    }
}

/* Unit propagation */
static int unit_propagate(void){
    int changed=1;
    while(changed){changed=0;
        for(int ci=0;ci<n_clauses;ci++){
            if(!cl_active[ci])continue;
            int sat=0,fc=0,fv=-1,fs=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}
                else{fc++;fv=v;fs=s;}}
            if(sat){cl_active[ci]=0;continue;}
            if(fc==0)return 1;
            if(fc==1){var_fixed[fv]=(fs==1)?1:0;changed=1;}}}
    return 0;}

/* WalkSAT fallback */
static int walksat(int max_flips){
    int a[MAX_N],m=n_clauses,n=n_vars;
    for(int v=0;v<n;v++) a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    int sc[MAX_CLAUSES];
    for(int ci=0;ci<m;ci++){sc[ci]=0;for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&a[v]==1)||(s==-1&&a[v]==0))sc[ci]++;}}
    int unsat[MAX_CLAUSES],up[MAX_CLAUSES],nu=0;
    memset(up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(sc[ci]==0){up[ci]=nu;unsat[nu++]=ci;}
    for(int f=0;f<max_flips&&nu>0;f++){
        int ci=unsat[rng_next()%nu];
        int bv=cl_var[ci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){
                int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&a[v]==1)||(os==-1&&a[v]==0))&&sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[ci][rng_next()%3]:bv);
        int old=a[fv],nw=1-old;a[fv]=nw;
        for(int d=0;d<vdeg[fv];d++){
            int oci=vlist[fv][d],opos=vpos[fv][d];
            int os=cl_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){sc[oci]--;if(sc[oci]==0){up[oci]=nu;unsat[nu++]=oci;}}
            else if(!was&&now){sc[oci]++;if(sc[oci]==1){int p=up[oci];
                if(p>=0&&p<nu){int l=unsat[nu-1];unsat[p]=l;up[l]=p;up[oci]=-1;nu--;}}}}}
    for(int v=0;v<n;v++) var_fixed[v]=a[v];
    return m-nu;}

/* ════════════════════════════════════════════════
 * SP-GUIDED DECIMATION
 * ════════════════════════════════════════════════ */

static int sp_solve(int nn) {
    int n=nn, m=n_clauses;

    if(unit_propagate()) return 0;

    int n_fixed=0;
    for(int v=0;v<n;v++) if(var_fixed[v]>=0) n_fixed++;

    /* Initialize surveys */
    for(int ci=0;ci<m;ci++) for(int j=0;j<3;j++)
        eta[ci][j] = rng_double() * 0.5;

    while(n_fixed < n) {
        /* Converge SP */
        int converged=0;
        for(int iter=0; iter<SP_MAX_ITER; iter++){
            double change = sp_iterate();
            if(change < SP_EPS) { converged=1; break; }
        }

        /* Check if SP trivialized: max η < threshold */
        double max_eta = 0;
        for(int ci=0;ci<m;ci++){
            if(!cl_active[ci]) continue;
            for(int j=0;j<3;j++){
                if(var_fixed[cl_var[ci][j]]>=0) continue;
                if(eta[ci][j]>max_eta) max_eta=eta[ci][j];}}

        if(max_eta < 0.01) {
            /* SP trivialized → switch to WalkSAT */
            rng_seed(n_fixed*12345+777);
            return walksat(n*500);
        }

        /* Compute bias */
        sp_compute_bias();

        /* Decimate: fix fraction of most biased variables */
        int n_free = n - n_fixed;
        int to_fix = n_free / 100; /* 1% per round */
        if(to_fix < 1) to_fix = 1;
        if(to_fix > 20) to_fix = 20;

        /* Find most biased free variables */
        for(int f=0; f<to_fix; f++) {
            double best_bias = -1;
            int best_var = -1, best_val = 0;

            for(int v=0;v<n;v++){
                if(var_fixed[v]>=0) continue;
                double bias = fabs(W_plus[v] - W_minus[v]);
                if(bias > best_bias){
                    best_bias=bias; best_var=v;
                    best_val = (W_plus[v] > W_minus[v]) ? 1 : 0;
                }
            }

            if(best_var < 0) break;
            var_fixed[best_var] = best_val;
            n_fixed++;

            /* Deactivate satisfied clauses */
            for(int d=0;d<vdeg[best_var];d++){
                int ci=vlist[best_var][d], p=vpos[best_var][d];
                if(!cl_active[ci]) continue;
                int s=cl_sign[ci][p];
                if((s==1&&best_val==1)||(s==-1&&best_val==0))
                    cl_active[ci]=0;
            }
        }

        /* UP cascade */
        if(unit_propagate()){
            /* Conflict → WalkSAT fallback */
            rng_seed(n_fixed*99999);
            return walksat(n*500);
        }

        n_fixed=0;
        for(int v=0;v<n;v++) if(var_fixed[v]>=0) n_fixed++;
    }

    return evaluate();
}

/* ════════════════════════════════════════════════
 * BENCHMARK
 * ════════════════════════════════════════════════ */

int main(void){
    printf("══════════════════════════════════════════════════\n");
    printf("CORRECT SP + DECIMATION (Braunstein et al 2005)\n");
    printf("══════════════════════════════════════════════════\n\n");

    int test_n[]={50,100,200,300,500,750,1000,1500,2000,3000};
    int sizes=10;

    printf("%6s | %5s | %6s | %8s\n","n","total","solved","time_ms");
    printf("-------+-------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int n_inst=(nn<=200)?20:(nn<=500?10:(nn<=1000?5:3));
        int solved=0,total=0;
        double total_ms=0;

        for(int seed=0;seed<n_inst*3&&total<n_inst;seed++){
            generate(nn,4.267,11000000ULL+seed);
            clock_t t0=clock();
            rng_seed(seed*31337);
            int sat=sp_solve(nn);
            clock_t t1=clock();
            total_ms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            total++;
            if(sat==n_clauses) solved++;
        }

        printf("%6d | %2d/%2d | %4d   | %7.0fms\n",
               nn,solved,total,solved,total_ms/total);
        fflush(stdout);
    }

    printf("\n=== COMPARISON ===\n");
    printf("Previous (buggy) SP: n=500 1/10, n=750 0\n");
    printf("PhysicsSAT:          n=500 3/20, n=750 1/10\n");
    printf("If correct SP breaks n=1000+: SP paradigm works!\n");
    return 0;
}
