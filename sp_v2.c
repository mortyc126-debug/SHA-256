/*
 * SP v2: Correct Survey Propagation for random 3-SAT
 * ====================================================
 *
 * CRITICAL FIX: 3-state cavity normalization.
 * Uses P_u/(P_u+P_s+P_0) excluding contradiction state P_c.
 *
 * Algorithm (one-shot SP + WalkSAT):
 *   1. Run 3-state SP to convergence (one time, ~100 iters)
 *   2. Compute biases, fix all vars with |bias| > threshold
 *   3. Unit propagation
 *   4. WalkSAT to complete the assignment
 *   5. Try multiple thresholds and seeds
 *
 * This is fast (single SP convergence, O(n * m * degree)) and
 * the SP biases give WalkSAT a huge head start.
 *
 * Compile: gcc -O3 -march=native -o sp_v2 sp_v2.c -lm
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
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N];

static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

static double eta[MAX_CLAUSES][MAX_K];
static double W_plus[MAX_N], W_minus[MAX_N], W_zero[MAX_N];

/* RNG */
static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void) {
    unsigned long long s0=rng_s[0], s1=rng_s[1], s2=rng_s[2], s3=rng_s[3];
    unsigned long long r = ((s1*5)<<7|(s1*5)>>57)*9;
    unsigned long long t = s1<<17;
    s2^=s0; s3^=s1; s1^=s2; s0^=s3; s2^=t; s3=(s3<<45)|(s3>>19);
    rng_s[0]=s0; rng_s[1]=s1; rng_s[2]=s2; rng_s[3]=s3;
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

static void generate(int n, double ratio, unsigned long long seed) {
    n_vars = n;
    n_clauses = (int)(ratio * n);
    if(n_clauses > MAX_CLAUSES) n_clauses = MAX_CLAUSES;
    rng_seed(seed);
    memset(vdeg, 0, sizeof(int)*n);
    for(int ci=0; ci<n_clauses; ci++) {
        int vs[3];
        vs[0] = rng_next() % n;
        do { vs[1] = rng_next() % n; } while(vs[1]==vs[0]);
        do { vs[2] = rng_next() % n; } while(vs[2]==vs[0] || vs[2]==vs[1]);
        for(int j=0; j<3; j++) {
            cl_var[ci][j] = vs[j];
            cl_sign[ci][j] = (rng_next()&1) ? 1 : -1;
            int v = vs[j];
            if(vdeg[v] < MAX_DEGREE) {
                vlist[v][vdeg[v]] = ci;
                vpos[v][vdeg[v]] = j;
                vdeg[v]++;
            }
        }
    }
    for(int ci=0; ci<n_clauses; ci++) cl_active[ci] = 1;
    memset(var_fixed, -1, sizeof(int)*n);
}

static int evaluate(void) {
    int sat = 0;
    for(int ci=0; ci<n_clauses; ci++) {
        for(int j=0; j<3; j++) {
            int v = cl_var[ci][j], s = cl_sign[ci][j];
            int val = (var_fixed[v]>=0) ? var_fixed[v] : 0;
            if((s==1 && val==1) || (s==-1 && val==0)) { sat++; break; }
        }
    }
    return sat;
}

/* ============================================================
 * 3-STATE SP
 * ============================================================ */
static inline double sp_compute_edge(int ci, int pos_i) {
    if(var_fixed[cl_var[ci][pos_i]] >= 0) return 0;
    double product = 1.0;
    for(int pj = 0; pj < MAX_K; pj++) {
        if(pj == pos_i) continue;
        int j = cl_var[ci][pj];
        if(var_fixed[j] >= 0) {
            int sj = cl_sign[ci][pj];
            if((sj==1 && var_fixed[j]==1) || (sj==-1 && var_fixed[j]==0)) return 0;
            continue;
        }
        int sign_j_in_a = cl_sign[ci][pj];
        double prod_s = 1.0, prod_u = 1.0;
        for(int d = 0; d < vdeg[j]; d++) {
            int bi = vlist[j][d], bp = vpos[j][d];
            if(bi == ci || !cl_active[bi]) continue;
            int b_sat = 0;
            for(int k=0; k<MAX_K; k++) {
                int vk = cl_var[bi][k];
                if(var_fixed[vk] >= 0) {
                    int sk = cl_sign[bi][k];
                    if((sk==1 && var_fixed[vk]==1) || (sk==-1 && var_fixed[vk]==0))
                        { b_sat=1; break; }
                }
            }
            if(b_sat) continue;
            double eta_b = eta[bi][bp];
            if(cl_sign[bi][bp] == sign_j_in_a) prod_s *= (1.0 - eta_b);
            else prod_u *= (1.0 - eta_b);
        }
        double P_u = (1.0 - prod_u) * prod_s;
        double P_s = (1.0 - prod_s) * prod_u;
        double P_0 = prod_u * prod_s;
        double denom = P_u + P_s + P_0;
        product *= (denom > 1e-15) ? (P_u / denom) : 0.0;
    }
    return product;
}

static double sp_iterate(double rho) {
    double max_change = 0;
    for(int ci = 0; ci < n_clauses; ci++) {
        if(!cl_active[ci]) continue;
        for(int p = 0; p < MAX_K; p++) {
            if(var_fixed[cl_var[ci][p]] >= 0) continue;
            double nv = sp_compute_edge(ci, p);
            double ov = eta[ci][p];
            double up = rho * ov + (1.0 - rho) * nv;
            double ch = fabs(up - ov);
            if(ch > max_change) max_change = ch;
            eta[ci][p] = up;
        }
    }
    return max_change;
}

/* Converge SP once */
static int sp_converge(unsigned long long seed) {
    rng_seed(seed);
    for(int ci=0; ci<n_clauses; ci++)
        for(int j=0; j<MAX_K; j++)
            eta[ci][j] = rng_double();

    double rho = 0.2;
    int stall = 0;
    double prev = 1e10;
    for(int iter = 0; iter < 300; iter++) {
        double ch = sp_iterate(rho);
        if(ch < 1e-4) return 1;
        if(ch > 0.9 * prev) {
            stall++;
            if(stall >= 10) { rho = fmin(rho + 0.05, 0.9); stall = 0; }
        } else { stall = 0; }
        prev = ch;
    }
    return 0;
}

/* Compute biases */
static void sp_compute_bias(void) {
    for(int i = 0; i < n_vars; i++) {
        W_plus[i] = W_minus[i] = 0; W_zero[i] = 1;
        if(var_fixed[i] >= 0) continue;
        double prod_plus = 1.0, prod_minus = 1.0;
        for(int d = 0; d < vdeg[i]; d++) {
            int ci = vlist[i][d], p = vpos[i][d];
            if(!cl_active[ci]) continue;
            int sat = 0;
            for(int k=0; k<MAX_K; k++) {
                int vk = cl_var[ci][k];
                if(vk != i && var_fixed[vk] >= 0) {
                    int sk = cl_sign[ci][k];
                    if((sk==1 && var_fixed[vk]==1) || (sk==-1 && var_fixed[vk]==0))
                        { sat=1; break; }
                }
            }
            if(sat) continue;
            double e = eta[ci][p];
            if(cl_sign[ci][p] == 1) prod_plus *= (1.0 - e);
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
        } else { W_zero[i] = 1.0; }
    }
}

/* Unit propagation */
static int unit_propagate(void) {
    int changed = 1;
    while(changed) {
        changed = 0;
        for(int ci=0; ci<n_clauses; ci++) {
            if(!cl_active[ci]) continue;
            int sat=0, fc=0, fv=-1, fs=0;
            for(int j=0; j<3; j++) {
                int v = cl_var[ci][j], s = cl_sign[ci][j];
                if(var_fixed[v] >= 0) {
                    if((s==1 && var_fixed[v]==1) || (s==-1 && var_fixed[v]==0)) sat = 1;
                } else { fc++; fv=v; fs=s; }
            }
            if(sat) { cl_active[ci]=0; continue; }
            if(fc==0) return 1;
            if(fc==1) { var_fixed[fv] = (fs==1) ? 1 : 0; changed=1; }
        }
    }
    return 0;
}

/* WalkSAT */
static int walksat(int max_flips, int use_bias) {
    int a[MAX_N], n = n_vars, m = n_clauses;
    for(int v=0; v<n; v++) {
        if(var_fixed[v] >= 0) a[v] = var_fixed[v];
        else if(use_bias && W_zero[v] < 0.95) a[v] = (W_plus[v] > W_minus[v]) ? 1 : 0;
        else a[v] = (rng_next() & 1) ? 1 : 0;
    }

    int sc[MAX_CLAUSES];
    for(int ci=0; ci<m; ci++) {
        sc[ci] = 0;
        for(int j=0; j<3; j++) {
            int v = cl_var[ci][j], s = cl_sign[ci][j];
            if((s==1 && a[v]==1) || (s==-1 && a[v]==0)) sc[ci]++;
        }
    }
    int unsat[MAX_CLAUSES], up[MAX_CLAUSES], nu = 0;
    memset(up, -1, sizeof(int)*m);
    for(int ci=0; ci<m; ci++)
        if(sc[ci]==0) { up[ci]=nu; unsat[nu++]=ci; }

    for(int f=0; f<max_flips && nu>0; f++) {
        int ci = unsat[rng_next() % nu];
        int bv = cl_var[ci][0], bb = m+1, zb = -1;
        for(int j=0; j<3; j++) {
            int v = cl_var[ci][j], br = 0;
            for(int d=0; d<vdeg[v]; d++) {
                int oci = vlist[v][d], opos = vpos[v][d];
                int os = cl_sign[oci][opos];
                if(((os==1 && a[v]==1) || (os==-1 && a[v]==0)) && sc[oci]==1) br++;
            }
            if(br == 0) { zb = v; break; }
            if(br < bb) { bb = br; bv = v; }
        }
        int fv;
        if(zb >= 0) fv = zb;
        else if(rng_next() % 100 < 57) fv = cl_var[ci][rng_next() % 3];
        else fv = bv;

        int old = a[fv], nw = 1 - old; a[fv] = nw;
        for(int d=0; d<vdeg[fv]; d++) {
            int oci = vlist[fv][d], opos = vpos[fv][d];
            int os = cl_sign[oci][opos];
            int was = ((os==1 && old==1) || (os==-1 && old==0));
            int now = ((os==1 && nw==1) || (os==-1 && nw==0));
            if(was && !now) { sc[oci]--; if(sc[oci]==0) { up[oci]=nu; unsat[nu++]=oci; } }
            else if(!was && now) { sc[oci]++;
                if(sc[oci]==1) { int p=up[oci]; if(p>=0&&p<nu) { int l=unsat[nu-1]; unsat[p]=l; up[l]=p; up[oci]=-1; nu--; } } }
        }
    }
    for(int v=0; v<n; v++) var_fixed[v] = a[v];
    return m - nu;
}

/* ============================================================
 * SOLVER: multiple strategies
 * ============================================================ */
static int init_cl_active[MAX_CLAUSES];
static int init_var_fixed[MAX_N];

static void save_init(void) {
    memcpy(init_cl_active, cl_active, sizeof(int)*n_clauses);
    memcpy(init_var_fixed, var_fixed, sizeof(int)*n_vars);
}
static void restore_init(void) {
    memcpy(cl_active, init_cl_active, sizeof(int)*n_clauses);
    memcpy(var_fixed, init_var_fixed, sizeof(int)*n_vars);
}

static int sp_solve(int nn) {
    int n = nn, m = n_clauses;

    if(unit_propagate()) return 0;
    save_init();

    /* Strategy 1: One-shot SP + threshold fixing + WalkSAT
     * Try multiple bias thresholds */
    double thresholds[] = {0.9, 0.8, 0.7, 0.5, 0.3};
    int n_thresh = 5;

    for(int t = 0; t < n_thresh; t++) {
        for(int sp_seed = 0; sp_seed < 2; sp_seed++) {
            restore_init();

            int conv = sp_converge(42ULL + sp_seed * 9973ULL + (unsigned long long)n * 13);
            if(!conv) continue;

            sp_compute_bias();

            double thresh = thresholds[t];

            /* Fix all variables with |bias| > threshold */
            int fixed_this_round = 0;
            for(int v = 0; v < n; v++) {
                if(var_fixed[v] >= 0) continue;
                double bias = fabs(W_plus[v] - W_minus[v]);
                if(bias > thresh) {
                    int val = (W_plus[v] > W_minus[v]) ? 1 : 0;
                    var_fixed[v] = val;
                    fixed_this_round++;
                    for(int d=0; d<vdeg[v]; d++) {
                        int ci = vlist[v][d], p = vpos[v][d];
                        if(!cl_active[ci]) continue;
                        int s = cl_sign[ci][p];
                        if((s==1 && val==1) || (s==-1 && val==0))
                            cl_active[ci] = 0;
                    }
                }
            }

            /* Unit propagation (may cause contradiction) */
            int conflict = unit_propagate();

            /* WalkSAT (even after conflict, try to recover) */
            int flips = n * 2000;
            if(flips > 5000000) flips = 5000000;

            for(int ws = 0; ws < 3; ws++) {
                rng_seed(t * 10000ULL + sp_seed * 77777ULL + ws * 12345ULL);
                int sat = walksat(flips, ws == 0 && !conflict);
                if(sat == m) return sat;
            }
        }
    }

    /* Strategy 2: Iterative decimation with limited rounds */
    for(int restart = 0; restart < 2; restart++) {
        restore_init();

        rng_seed(100ULL + restart * 9973ULL + (unsigned long long)n * 7);
        for(int ci=0; ci<m; ci++)
            for(int j=0; j<MAX_K; j++)
                eta[ci][j] = rng_double();

        int n_fixed = 0;
        for(int v=0; v<n; v++) if(var_fixed[v]>=0) n_fixed++;

        for(int round = 0; round < 15; round++) {
            /* SP convergence */
            double rho = 0.2;
            int stall = 0;
            double prev = 1e10;
            int conv = 0;
            for(int iter = 0; iter < 200; iter++) {
                double ch = sp_iterate(rho);
                if(ch < 1e-4) { conv = 1; break; }
                if(ch > 0.9 * prev) {
                    stall++;
                    if(stall >= 10) { rho = fmin(rho + 0.1, 0.9); stall = 0; }
                } else { stall = 0; }
                prev = ch;
            }
            if(!conv) break;

            double max_eta = 0;
            for(int ci=0; ci<m; ci++) {
                if(!cl_active[ci]) continue;
                for(int j=0; j<MAX_K; j++) {
                    if(var_fixed[cl_var[ci][j]] >= 0) continue;
                    if(eta[ci][j] > max_eta) max_eta = eta[ci][j];
                }
            }
            if(max_eta < 0.01) break;

            sp_compute_bias();

            /* Fix top 5% */
            int nf = n - n_fixed;
            if(nf == 0) break;
            int to_fix = nf / 20;
            if(to_fix < 1) to_fix = 1;

            /* Simple selection: find best to_fix */
            for(int f = 0; f < to_fix; f++) {
                double bb = -1;
                int bv = -1, bval = 0;
                for(int v=0; v<n; v++) {
                    if(var_fixed[v] >= 0) continue;
                    double b = fabs(W_plus[v] - W_minus[v]);
                    if(b > bb) { bb = b; bv = v; bval = (W_plus[v] > W_minus[v]) ? 1 : 0; }
                }
                if(bv < 0 || bb < 0.01) break;
                var_fixed[bv] = bval;
                n_fixed++;
                for(int d=0; d<vdeg[bv]; d++) {
                    int ci = vlist[bv][d], p = vpos[bv][d];
                    if(!cl_active[ci]) continue;
                    int s = cl_sign[ci][p];
                    if((s==1 && bval==1) || (s==-1 && bval==0))
                        cl_active[ci] = 0;
                }
            }

            if(unit_propagate()) break;
            n_fixed = 0;
            for(int v=0; v<n; v++) if(var_fixed[v]>=0) n_fixed++;
        }

        sp_compute_bias();
        int flips = n * 2000;
        if(flips > 5000000) flips = 5000000;

        for(int ws = 0; ws < 3; ws++) {
            rng_seed(restart * 55555ULL + ws * 12345ULL + 500);
            int sat = walksat(flips, ws < 2);
            if(sat == m) return sat;
        }
    }

    /* Final fallback */
    rng_seed(999999);
    return walksat(n_vars * 5000, 0);
}

/* ============================================================
 * BENCHMARK
 * ============================================================ */
int main(void) {
    printf("====================================================\n");
    printf("SP v2: 3-state SP + multi-strategy + WalkSAT\n");
    printf("====================================================\n");
    printf("Key fix: 3-state normalization (P_c excluded)\n");
    printf("Strategy 1: one-shot SP + threshold fixing\n");
    printf("Strategy 2: iterative 5%% decimation (15 rounds max)\n\n");

    int test_n[] = {100, 200, 300, 500, 750, 1000, 2000};
    int sizes = 7;

    printf("%6s | %5s | %6s | %8s | %s\n",
           "n", "total", "solved", "time_ms", "rate");
    printf("-------+-------+--------+----------+------\n");

    for(int ti=0; ti<sizes; ti++) {
        int nn = test_n[ti];
        int n_inst;
        if(nn <= 200) n_inst = 20;
        else if(nn <= 500) n_inst = 10;
        else if(nn <= 1000) n_inst = 5;
        else n_inst = 3;

        int solved = 0, total = 0;
        double total_ms = 0;

        for(int seed=0; seed < n_inst * 3 && total < n_inst; seed++) {
            generate(nn, 4.267, 11000000ULL + seed);

            clock_t t0 = clock();
            rng_seed(seed * 31337ULL);
            int sat = sp_solve(nn);
            clock_t t1 = clock();
            double ms = (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            total_ms += ms;
            total++;
            if(sat == n_clauses) solved++;
        }

        printf("%6d | %2d/%2d | %4d   | %7.0fms | %3.0f%%\n",
               nn, solved, total, solved, total_ms/total,
               100.0*solved/total);
        fflush(stdout);
    }

    printf("\n=== COMPARISON ===\n");
    printf("sp_correct.c (4-state): n=750 2/5, n=1000 0/5\n");
    printf("sp_v2.c (3-state):      (results above)\n");

    return 0;
}
