/*
 * SP diagnostic: understand where the algorithm fails
 * Runs single instances with verbose output
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       5000
#define MAX_CLAUSES 25000
#define MAX_K       3
#define MAX_DEGREE  200

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];
static double eta[MAX_CLAUSES][MAX_K];
static double W_plus[MAX_N], W_minus[MAX_N], W_zero[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void) {
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

/* Compute eta_{a->i} using 3-state SP */
static double sp_compute_edge_3state(int ci, int pos_i) {
    int var_i = cl_var[ci][pos_i];
    if(var_fixed[var_i] >= 0) return 0;
    double product = 1.0;
    for(int pj = 0; pj < 3; pj++) {
        if(pj == pos_i) continue;
        int j = cl_var[ci][pj];
        if(var_fixed[j] >= 0) {
            int sj = cl_sign[ci][pj];
            if((sj==1 && var_fixed[j]==1) || (sj==-1 && var_fixed[j]==0))
                return 0;
            continue;
        }
        int sign_j_in_a = cl_sign[ci][pj];
        double prod_s = 1.0, prod_u = 1.0;
        for(int d = 0; d < vdeg[j]; d++) {
            int bi = vlist[j][d], bp = vpos[j][d];
            if(bi == ci || !cl_active[bi]) continue;
            int b_sat = 0;
            for(int k=0; k<3; k++) {
                int vk = cl_var[bi][k];
                if(var_fixed[vk] >= 0) {
                    int sk = cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))
                        { b_sat=1; break; }
                }
            }
            if(b_sat) continue;
            int sign_j_in_b = cl_sign[bi][bp];
            double eta_b = eta[bi][bp];
            if(sign_j_in_b == sign_j_in_a)
                prod_s *= (1.0 - eta_b);
            else
                prod_u *= (1.0 - eta_b);
        }
        double P_u = (1.0 - prod_u) * prod_s;
        double P_s = (1.0 - prod_s) * prod_u;
        double P_0 = prod_u * prod_s;
        double denom = P_u + P_s + P_0; /* 3-state: no P_c */
        double p_j = (denom > 1e-15) ? (P_u / denom) : 0.0;
        product *= p_j;
    }
    return product;
}

/* Same but 4-state */
static double sp_compute_edge_4state(int ci, int pos_i) {
    int var_i = cl_var[ci][pos_i];
    if(var_fixed[var_i] >= 0) return 0;
    double product = 1.0;
    for(int pj = 0; pj < 3; pj++) {
        if(pj == pos_i) continue;
        int j = cl_var[ci][pj];
        if(var_fixed[j] >= 0) {
            int sj = cl_sign[ci][pj];
            if((sj==1 && var_fixed[j]==1) || (sj==-1 && var_fixed[j]==0))
                return 0;
            continue;
        }
        int sign_j_in_a = cl_sign[ci][pj];
        double prod_s = 1.0, prod_u = 1.0;
        for(int d = 0; d < vdeg[j]; d++) {
            int bi = vlist[j][d], bp = vpos[j][d];
            if(bi == ci || !cl_active[bi]) continue;
            int b_sat = 0;
            for(int k=0; k<3; k++) {
                int vk = cl_var[bi][k];
                if(var_fixed[vk] >= 0) {
                    int sk = cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))
                        { b_sat=1; break; }
                }
            }
            if(b_sat) continue;
            int sign_j_in_b = cl_sign[bi][bp];
            double eta_b = eta[bi][bp];
            if(sign_j_in_b == sign_j_in_a)
                prod_s *= (1.0 - eta_b);
            else
                prod_u *= (1.0 - eta_b);
        }
        double P_u = (1.0 - prod_u) * prod_s;
        double P_s = (1.0 - prod_s) * prod_u;
        double P_0 = prod_u * prod_s;
        double P_c = (1.0 - prod_u) * (1.0 - prod_s);
        double denom = P_u + P_s + P_0 + P_c; /* 4-state */
        double p_j = (denom > 1e-15) ? (P_u / denom) : 0.0;
        product *= p_j;
    }
    return product;
}

/* Run SP iteration (choose mode: 3 or 4 state) */
static double sp_iterate_mode(int mode, double rho) {
    double max_change = 0;
    for(int ci = 0; ci < n_clauses; ci++) {
        if(!cl_active[ci]) continue;
        for(int p = 0; p < 3; p++) {
            if(var_fixed[cl_var[ci][p]] >= 0) continue;
            double new_val;
            if(mode == 3)
                new_val = sp_compute_edge_3state(ci, p);
            else
                new_val = sp_compute_edge_4state(ci, p);
            double old_val = eta[ci][p];
            double updated = rho * old_val + (1.0 - rho) * new_val;
            double change = fabs(updated - old_val);
            if(change > max_change) max_change = change;
            eta[ci][p] = updated;
        }
    }
    return max_change;
}

static void sp_compute_bias_3state(void) {
    for(int i = 0; i < n_vars; i++) {
        W_plus[i] = W_minus[i] = 0; W_zero[i] = 1;
        if(var_fixed[i] >= 0) continue;
        double prod_plus = 1.0, prod_minus = 1.0;
        for(int d = 0; d < vdeg[i]; d++) {
            int ci = vlist[i][d], p = vpos[i][d];
            if(!cl_active[ci]) continue;
            int sat = 0;
            for(int k=0; k<3; k++) {
                int vk = cl_var[ci][k];
                if(vk != i && var_fixed[vk] >= 0) {
                    int sk = cl_sign[ci][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))
                        { sat=1; break; }
                }
            }
            if(sat) continue;
            int s = cl_sign[ci][p];
            double e = eta[ci][p];
            if(s == 1) prod_plus *= (1.0 - e);
            else prod_minus *= (1.0 - e);
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

int main(void) {
    int nn = 500;
    int seed = 0;
    generate(nn, 4.267, 11000000ULL + seed);
    printf("Instance: n=%d, m=%d, ratio=%.3f\n", n_vars, n_clauses, (double)n_clauses/n_vars);

    /* Test 3-state vs 4-state convergence */
    for(int mode = 3; mode <= 4; mode++) {
        printf("\n=== %d-state SP ===\n", mode);

        /* Reset */
        for(int ci=0; ci<n_clauses; ci++) cl_active[ci] = 1;
        memset(var_fixed, -1, sizeof(int)*n_vars);

        /* Init surveys */
        rng_seed(42);
        for(int ci=0; ci<n_clauses; ci++)
            for(int j=0; j<3; j++)
                eta[ci][j] = rng_double();

        /* Converge */
        double rho = 0.5; /* same damping as sp_correct.c */
        int converged = 0;
        for(int iter = 0; iter < 500; iter++) {
            double ch = sp_iterate_mode(mode, rho);
            if(iter < 10 || iter % 50 == 0 || ch < 1e-3)
                printf("  iter %3d: max_change=%.6f\n", iter, ch);
            if(ch < 1e-3) { converged = 1; break; }
        }
        printf("  converged=%d\n", converged);

        if(converged) {
            /* Analyze surveys */
            int n_zero = 0, n_low = 0, n_mid = 0, n_high = 0, n_total = 0;
            double sum_eta = 0;
            for(int ci=0; ci<n_clauses; ci++) {
                if(!cl_active[ci]) continue;
                for(int j=0; j<3; j++) {
                    if(var_fixed[cl_var[ci][j]] >= 0) continue;
                    n_total++;
                    double e = eta[ci][j];
                    sum_eta += e;
                    if(e < 0.001) n_zero++;
                    else if(e < 0.1) n_low++;
                    else if(e < 0.5) n_mid++;
                    else n_high++;
                }
            }
            printf("  surveys: total=%d, zero=%d, low=%d, mid=%d, high=%d\n",
                   n_total, n_zero, n_low, n_mid, n_high);
            printf("  avg eta=%.6f\n", n_total > 0 ? sum_eta/n_total : 0);

            /* Analyze biases */
            sp_compute_bias_3state();
            int n_biased = 0;
            double max_bias = 0;
            for(int v=0; v<n_vars; v++) {
                if(var_fixed[v] >= 0) continue;
                double bias = fabs(W_plus[v] - W_minus[v]);
                if(bias > max_bias) max_bias = bias;
                if(bias > 0.1) n_biased++;
            }
            printf("  biases: max=%.6f, n_biased(>0.1)=%d/%d\n",
                   max_bias, n_biased, n_vars);
        }
    }

    /* Now test with different damping */
    printf("\n=== Damping study (3-state) ===\n");
    double rhos[] = {0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9};
    for(int ri = 0; ri < 7; ri++) {
        double rho = rhos[ri];
        for(int ci=0; ci<n_clauses; ci++) cl_active[ci] = 1;
        memset(var_fixed, -1, sizeof(int)*n_vars);
        rng_seed(42);
        for(int ci=0; ci<n_clauses; ci++)
            for(int j=0; j<3; j++)
                eta[ci][j] = rng_double();

        int converged = 0;
        int iters_needed = -1;
        for(int iter = 0; iter < 500; iter++) {
            double ch = sp_iterate_mode(3, rho);
            if(ch < 1e-3) { converged = 1; iters_needed = iter; break; }
        }
        printf("  rho=%.1f: converged=%d", rho, converged);
        if(converged) printf(" in %d iters", iters_needed);
        printf("\n");
    }

    return 0;
}
