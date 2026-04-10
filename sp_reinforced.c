/*
 * Reinforced Survey Propagation (rSP) for random 3-SAT
 * =====================================================
 *
 * Based on: Chavas, Braunstein, Zecchina (2005)
 *
 * Key idea: instead of hard decimation, add a soft reinforcement field
 * r_i that grows over time, nudging each variable toward its preferred
 * assignment. This avoids catastrophic wrong-decimation errors.
 *
 * Performance optimizations:
 *   - Precompute per-variable partial products (cache pp/pm)
 *     and update incrementally during sweeps
 *   - Interleave SP sweeps with reinforcement updates
 *   - Early extraction when polarized enough
 *   - Minimal restarts (1-2 rho values)
 *
 * Compile: gcc -O3 -march=native -o sp_reinforced sp_reinforced.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */
#define MAX_N       20000
#define MAX_CLAUSES 100000
#define MAX_K       3
#define MAX_DEGREE  300

/* ------------------------------------------------------------------ */
/* Global state                                                       */
/* ------------------------------------------------------------------ */
static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K]; /* +1 or -1 */

/* Variable-to-clause adjacency */
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

/* SP surveys on edges: eta[ci][j] = survey from clause ci to var cl_var[ci][j] */
static double eta[MAX_CLAUSES][MAX_K];

/* Per-variable cached products:
 *   vp_plus[v] = prod_{a: sign(v,a)=+1} (1 - eta[a][pos(v,a)])
 *   vp_minus[v] = prod_{a: sign(v,a)=-1} (1 - eta[a][pos(v,a)])
 * These allow O(1) computation of cavity fields for each edge.
 */
static double vp_plus[MAX_N];
static double vp_minus[MAX_N];

/* Biases */
static double W_plus[MAX_N], W_minus[MAX_N];

/* Reinforcement field per variable */
static double reinf[MAX_N];

/* Assignment */
static int assignment[MAX_N];

/* ------------------------------------------------------------------ */
/* PRNG: xoshiro256**                                                 */
/* ------------------------------------------------------------------ */
static unsigned long long rng_s[4];

static inline unsigned long long rng_next(void) {
    unsigned long long s0 = rng_s[0], s1 = rng_s[1];
    unsigned long long s2 = rng_s[2], s3 = rng_s[3];
    unsigned long long r = ((s1 * 5) << 7 | (s1 * 5) >> 57) * 9;
    unsigned long long t = s1 << 17;
    s2 ^= s0; s3 ^= s1; s1 ^= s2; s0 ^= s3; s2 ^= t;
    s3 = (s3 << 45) | (s3 >> 19);
    rng_s[0] = s0; rng_s[1] = s1; rng_s[2] = s2; rng_s[3] = s3;
    return r;
}

static void rng_seed(unsigned long long s) {
    rng_s[0] = s;
    rng_s[1] = s * 6364136223846793005ULL + 1;
    rng_s[2] = s * 1103515245ULL + 12345;
    rng_s[3] = s ^ 0xdeadbeefcafebabeULL;
    for (int i = 0; i < 20; i++) rng_next();
}

static inline double rng_double(void) {
    return (rng_next() >> 11) * (1.0 / 9007199254740992.0);
}

/* ------------------------------------------------------------------ */
/* Instance generation: random 3-SAT                                  */
/* ------------------------------------------------------------------ */
static void generate(int n, double ratio, unsigned long long seed) {
    n_vars = n;
    n_clauses = (int)(ratio * n);
    if (n_clauses > MAX_CLAUSES) n_clauses = MAX_CLAUSES;
    rng_seed(seed);
    memset(vdeg, 0, sizeof(int) * n);

    for (int ci = 0; ci < n_clauses; ci++) {
        int vs[3];
        vs[0] = rng_next() % n;
        do { vs[1] = rng_next() % n; } while (vs[1] == vs[0]);
        do { vs[2] = rng_next() % n; } while (vs[2] == vs[0] || vs[2] == vs[1]);
        for (int j = 0; j < 3; j++) {
            cl_var[ci][j] = vs[j];
            cl_sign[ci][j] = (rng_next() & 1) ? 1 : -1;
            int v = vs[j];
            if (vdeg[v] < MAX_DEGREE) {
                vlist[v][vdeg[v]] = ci;
                vpos[v][vdeg[v]] = j;
                vdeg[v]++;
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/* Build/rebuild cached variable products from current eta values.    */
/* ------------------------------------------------------------------ */
static void rebuild_vp(int n) {
    for (int v = 0; v < n; v++) {
        double pp = 1.0, pm = 1.0;
        for (int d = 0; d < vdeg[v]; d++) {
            int ci = vlist[v][d], p = vpos[v][d];
            double e = eta[ci][p];
            if (cl_sign[ci][p] == 1)
                pp *= (1.0 - e);
            else
                pm *= (1.0 - e);
        }
        vp_plus[v] = pp;
        vp_minus[v] = pm;
    }
}

/* ------------------------------------------------------------------ */
/* SP edge computation using cached products + reinforcement          */
/*                                                                    */
/* For edge (a, i), we need for each j != i in clause a:             */
/*   The cavity product "all clauses b != a pushing j".              */
/*   Using cached vp_plus/vp_minus, the cavity is obtained by        */
/*   dividing out the contribution of clause a from the full product.*/
/*                                                                    */
/* eta_{a->i} = prod_{j in a, j!=i} [Pu_j / (Pu_j + Ps_j + P0_j)]  */
/* ------------------------------------------------------------------ */
static inline double sp_edge_cached(int ci, int pos_i) {
    double product = 1.0;
    for (int pj = 0; pj < 3; pj++) {
        if (pj == pos_i) continue;
        int j = cl_var[ci][pj];
        int sign_j_a = cl_sign[ci][pj];

        /* Get full products for variable j */
        double full_ps, full_pu;
        if (sign_j_a == 1) {
            full_ps = vp_plus[j];  /* same-sign as a */
            full_pu = vp_minus[j]; /* opposite-sign */
        } else {
            full_ps = vp_minus[j];
            full_pu = vp_plus[j];
        }

        /* Divide out the contribution of clause a itself.
         * Clause a contributes (1 - eta[a][pj]) to the same-sign product. */
        double ea = eta[ci][pj];
        double one_minus_ea = 1.0 - ea;
        if (one_minus_ea > 1e-15)
            full_ps /= one_minus_ea;
        else {
            /* eta very close to 1; recompute cavity from scratch */
            double ps_cav = 1.0, pu_cav = 1.0;
            for (int d = 0; d < vdeg[j]; d++) {
                int bi = vlist[j][d], bp = vpos[j][d];
                if (bi == ci) continue;
                double eb = eta[bi][bp];
                if (cl_sign[bi][bp] == sign_j_a)
                    ps_cav *= (1.0 - eb);
                else
                    pu_cav *= (1.0 - eb);
            }
            double Pu = (1.0 - pu_cav) * ps_cav;
            double Ps = (1.0 - ps_cav) * pu_cav;
            double P0 = pu_cav * ps_cav;

            double rj = reinf[j];
            if (rj != 0.0) {
                double field = rj * sign_j_a;
                if (field > 15.0) field = 15.0;
                if (field < -15.0) field = -15.0;
                double expf = exp(field);
                Ps *= expf;
                Pu /= expf;
            }

            double den = Pu + Ps + P0;
            product *= (den > 1e-15) ? (Pu / den) : 0.0;
            continue;
        }

        /* ps = cavity same-sign product (without clause a) */
        double ps = full_ps;
        double pu = full_pu;

        double Pu = (1.0 - pu) * ps;
        double Ps = (1.0 - ps) * pu;
        double P0 = pu * ps;

        /* Apply reinforcement */
        double rj = reinf[j];
        if (rj != 0.0) {
            double field = rj * sign_j_a;
            if (field > 15.0) field = 15.0;
            if (field < -15.0) field = -15.0;
            double expf = exp(field);
            Ps *= expf;
            Pu /= expf;
        }

        double den = Pu + Ps + P0;
        if (den > 1e-15)
            product *= Pu / den;
        else
            return 0.0;
    }
    return product;
}

/* ------------------------------------------------------------------ */
/* SP sweep: update all edges, rebuild cache periodically             */
/* ------------------------------------------------------------------ */
static int *clause_perm = NULL;

static void init_perm(void) {
    if (!clause_perm)
        clause_perm = (int *)malloc(MAX_CLAUSES * sizeof(int));
}

static void shuffle_clauses(int m) {
    for (int i = m - 1; i > 0; i--) {
        int j = rng_next() % (i + 1);
        int t = clause_perm[i];
        clause_perm[i] = clause_perm[j];
        clause_perm[j] = t;
    }
}

static double sp_sweep(int n, double damp) {
    int m = n_clauses;

    /* Rebuild cached products before each sweep for correctness.
     * This is O(sum of degrees) = O(3*m) which is cheap. */
    rebuild_vp(n);

    shuffle_clauses(m);
    double max_ch = 0;
    for (int e = 0; e < m; e++) {
        int ci = clause_perm[e];
        for (int p = 0; p < 3; p++) {
            double nv = sp_edge_cached(ci, p);
            double ov = eta[ci][p];
            double up = damp * ov + (1.0 - damp) * nv;
            if (up < 0.0) up = 0.0;
            if (up > 1.0) up = 1.0;
            double ch = fabs(up - ov);
            if (ch > max_ch) max_ch = ch;

            /* Update the cached product for the affected variable.
             * We need to update vp_plus or vp_minus for cl_var[ci][p].
             * Remove old contribution, add new. */
            int v = cl_var[ci][p];
            int s = cl_sign[ci][p];
            double old_factor = 1.0 - ov;
            double new_factor = 1.0 - up;

            if (old_factor > 1e-15) {
                if (s == 1)
                    vp_plus[v] = vp_plus[v] / old_factor * new_factor;
                else
                    vp_minus[v] = vp_minus[v] / old_factor * new_factor;
            } else {
                /* Can't divide; defer to next full rebuild. This is rare. */
            }

            eta[ci][p] = up;
        }
    }
    return max_ch;
}

/* ------------------------------------------------------------------ */
/* Bias computation with reinforcement                                */
/* ------------------------------------------------------------------ */
static void compute_bias(int n) {
    rebuild_vp(n);
    for (int i = 0; i < n; i++) {
        double pp = vp_plus[i];
        double pm = vp_minus[i];
        double pi_p = (1.0 - pp) * pm;
        double pi_m = (1.0 - pm) * pp;
        double pi_0 = pp * pm;

        double ri = reinf[i];
        if (ri != 0.0) {
            double ef = ri;
            if (ef > 15.0) ef = 15.0;
            if (ef < -15.0) ef = -15.0;
            double expf = exp(ef);
            pi_p *= expf;
            pi_m /= expf;
        }

        double tot = pi_p + pi_m + pi_0;
        if (tot > 1e-15) {
            W_plus[i] = pi_p / tot;
            W_minus[i] = pi_m / tot;
        } else {
            W_plus[i] = W_minus[i] = 0.0;
        }
    }
}

/* ------------------------------------------------------------------ */
/* WalkSAT                                                            */
/* ------------------------------------------------------------------ */
static int walksat(int *a, int max_flips) {
    int n = n_vars, m = n_clauses;

    int *sc = (int *)calloc(m, sizeof(int));
    for (int ci = 0; ci < m; ci++)
        for (int j = 0; j < 3; j++) {
            int v = cl_var[ci][j], s = cl_sign[ci][j];
            if ((s == 1 && a[v] == 1) || (s == -1 && a[v] == 0))
                sc[ci]++;
        }

    int *ul = (int *)malloc(m * sizeof(int));
    int *up = (int *)malloc(m * sizeof(int));
    int nu = 0;
    memset(up, -1, sizeof(int) * m);
    for (int ci = 0; ci < m; ci++)
        if (sc[ci] == 0) {
            up[ci] = nu;
            ul[nu++] = ci;
        }

    for (int f = 0; f < max_flips && nu > 0; f++) {
        int ci = ul[rng_next() % nu];
        int bv = cl_var[ci][0], bb = m + 1, zb = -1;
        for (int j = 0; j < 3; j++) {
            int v = cl_var[ci][j];
            int br = 0;
            for (int d = 0; d < vdeg[v]; d++) {
                int oci = vlist[v][d], opos = vpos[v][d];
                int os = cl_sign[oci][opos];
                if (((os == 1 && a[v] == 1) || (os == -1 && a[v] == 0)) &&
                    sc[oci] == 1)
                    br++;
            }
            if (br == 0) { zb = v; break; }
            if (br < bb) { bb = br; bv = v; }
        }

        int fv;
        if (zb >= 0)
            fv = zb;
        else if (rng_next() % 100 < 57)
            fv = cl_var[ci][rng_next() % 3];
        else
            fv = bv;

        int old = a[fv], nw = 1 - old;
        a[fv] = nw;
        for (int d = 0; d < vdeg[fv]; d++) {
            int oci = vlist[fv][d], opos = vpos[fv][d];
            int os = cl_sign[oci][opos];
            int was = ((os == 1 && old == 1) || (os == -1 && old == 0));
            int now = ((os == 1 && nw == 1) || (os == -1 && nw == 0));
            if (was && !now) {
                sc[oci]--;
                if (sc[oci] == 0) {
                    up[oci] = nu;
                    ul[nu++] = oci;
                }
            } else if (!was && now) {
                sc[oci]++;
                if (sc[oci] == 1) {
                    int p2 = up[oci];
                    if (p2 >= 0 && p2 < nu) {
                        int l = ul[nu - 1];
                        ul[p2] = l;
                        up[l] = p2;
                        up[oci] = -1;
                        nu--;
                    }
                }
            }
        }
    }

    int unsat = nu;
    free(sc);
    free(ul);
    free(up);
    return m - unsat;
}

/* ------------------------------------------------------------------ */
/* Count satisfied clauses                                            */
/* ------------------------------------------------------------------ */
static int count_sat(int *a) {
    int sat = 0;
    for (int ci = 0; ci < n_clauses; ci++) {
        for (int j = 0; j < 3; j++) {
            int v = cl_var[ci][j], s = cl_sign[ci][j];
            if ((s == 1 && a[v] == 1) || (s == -1 && a[v] == 0)) {
                sat++;
                break;
            }
        }
    }
    return sat;
}

/* ------------------------------------------------------------------ */
/* Reinforced SP solver                                               */
/*                                                                    */
/* Phase 1: Pure SP convergence (no reinforcement)                    */
/* Phase 2: Interleave SP sweeps with reinforcement updates           */
/*   Each round: 5-15 SP sweeps + reinf update                       */
/* Phase 3: Extract assignment, WalkSAT to finish                    */
/* ------------------------------------------------------------------ */
static int rsp_solve(int n, double rho_val, unsigned long long seed) {
    int m = n_clauses;

    rng_seed(seed);

    /* Initialize surveys randomly */
    for (int ci = 0; ci < m; ci++)
        for (int j = 0; j < 3; j++)
            eta[ci][j] = rng_double();

    /* Initialize reinforcement to 0 */
    memset(reinf, 0, sizeof(double) * n);

    init_perm();
    for (int ci = 0; ci < m; ci++)
        clause_perm[ci] = ci;

    /* ---- Phase 1: pure SP convergence ---- */
    int conv = 0;
    for (int iter = 0; iter < 100; iter++) {
        double ch = sp_sweep(n, 0.10);
        if (ch < 1e-4) { conv = 1; break; }
    }
    if (!conv) {
        for (int iter = 0; iter < 60; iter++) {
            double ch = sp_sweep(n, 0.25);
            if (ch < 1e-4) { conv = 1; break; }
        }
    }
    if (!conv) return 0;

    /* ---- Phase 2: reinforcement loop ---- */
    double rho = rho_val;

    for (int rnd = 0; rnd < 300; rnd++) {
        /* Compute biases */
        compute_bias(n);

        /* Check polarization */
        int n_polar99 = 0;
        for (int i = 0; i < n; i++) {
            double mx = (W_plus[i] > W_minus[i]) ? W_plus[i] : W_minus[i];
            if (mx > 0.99) n_polar99++;
        }

        if (n_polar99 >= (int)(n * 0.98))
            break;

        /* Check if surveys have trivialized */
        double max_eta = 0;
        for (int ci = 0; ci < m; ci++)
            for (int j = 0; j < 3; j++)
                if (eta[ci][j] > max_eta) max_eta = eta[ci][j];
        if (max_eta < 0.01 && rnd > 10)
            break;

        /* Update reinforcement */
        for (int i = 0; i < n; i++) {
            double diff = W_plus[i] - W_minus[i];
            reinf[i] += rho * diff;
            if (reinf[i] > 30.0) reinf[i] = 30.0;
            if (reinf[i] < -30.0) reinf[i] = -30.0;
        }

        /* Reconverge SP (few sweeps since change is small) */
        int nsweeps = (rnd < 5) ? 20 : 8;
        for (int iter = 0; iter < nsweeps; iter++) {
            double ch = sp_sweep(n, 0.15);
            if (ch < 1e-4) break;
        }

        rho *= 1.01;
        if (rho > 1.0) rho = 1.0;
    }

    /* ---- Phase 3: extract ---- */
    compute_bias(n);
    for (int i = 0; i < n; i++) {
        if (W_plus[i] > W_minus[i])
            assignment[i] = 1;
        else if (W_minus[i] > W_plus[i])
            assignment[i] = 0;
        else
            assignment[i] = (reinf[i] >= 0) ? 1 : 0;
    }

    int sat = count_sat(assignment);
    if (sat == m) return m;

    /* WalkSAT polish */
    int flips = n * 5000;
    if (flips > 20000000) flips = 20000000;

    for (int ws = 0; ws < 5; ws++) {
        int *a = (int *)malloc(n * sizeof(int));
        memcpy(a, assignment, n * sizeof(int));
        rng_seed(seed + ws * 77777ULL + 12345ULL);
        sat = walksat(a, flips);
        if (sat == m) {
            memcpy(assignment, a, n * sizeof(int));
            free(a);
            return m;
        }
        free(a);
    }

    return sat;
}

/* ------------------------------------------------------------------ */
/* Full solve                                                         */
/* ------------------------------------------------------------------ */
static int full_solve(int n) {
    int m = n_clauses;

    double rhos[] = {0.05, 0.15, 0.3};
    int n_rhos = 3;

    for (int attempt = 0; attempt < n_rhos; attempt++) {
        unsigned long long seed = 42ULL + attempt * 9973ULL +
                                  (unsigned long long)n * 13;
        int sat = rsp_solve(n, rhos[attempt], seed);
        if (sat == m) return m;
    }

    /* Fallback: WalkSAT from random/biased start */
    for (int ws = 0; ws < 3; ws++) {
        int *a = (int *)malloc(n * sizeof(int));
        rng_seed(999999ULL + ws * 31337ULL);
        for (int i = 0; i < n; i++)
            a[i] = (rng_next() & 1) ? 1 : 0;

        int flips = n * 10000;
        if (flips > 20000000) flips = 20000000;
        int sat = walksat(a, flips);
        if (sat == m) {
            free(a);
            return m;
        }
        free(a);
    }

    return 0;
}

/* ------------------------------------------------------------------ */
/* Benchmark main                                                     */
/* ------------------------------------------------------------------ */
int main(void) {
    printf("============================================================\n");
    printf("Reinforced Survey Propagation (rSP) for random 3-SAT\n");
    printf("============================================================\n");
    printf("Based on Chavas, Braunstein, Zecchina (2005)\n");
    printf("Soft reinforcement + cached cavity products\n\n");

    struct {
        int n;
        double alpha;
    } tests[] = {
        {1000, 4.0},   {2000, 4.0},   {3000, 4.0},
        {5000, 4.0},   {7500, 4.0},   {10000, 4.0},
        {1000, 4.267}, {2000, 4.267}, {3000, 4.267},
        {5000, 4.267}, {7500, 4.267}, {10000, 4.267},
    };
    int n_tests = 12;

    printf("%6s | %6s | %5s | %6s | %9s | %s\n",
           "n", "alpha", "total", "solved", "avg_ms", "rate");
    printf("-------+--------+-------+--------+-----------+------\n");

    for (int ti = 0; ti < n_tests; ti++) {
        int nn = tests[ti].n;
        double alpha = tests[ti].alpha;

        int ni;
        if (nn <= 1000)
            ni = 10;
        else if (nn <= 3000)
            ni = 5;
        else if (nn <= 5000)
            ni = 3;
        else
            ni = 2;

        int solved = 0, total = 0;
        double tms = 0;

        for (int seed = 0; seed < ni; seed++) {
            generate(nn, alpha,
                     11000000ULL + seed * 1000ULL +
                         (unsigned long long)(alpha * 1000));

            clock_t t0 = clock();
            int sat = full_solve(nn);
            clock_t t1 = clock();
            double ms = (double)(t1 - t0) * 1000.0 / CLOCKS_PER_SEC;
            tms += ms;
            total++;
            if (sat == n_clauses) solved++;

            if (ms > 300000) {
                printf("  (instance %d took %.0fs, stopping)\n",
                       seed, ms / 1000.0);
                break;
            }
        }

        printf("%6d | %6.3f | %2d/%2d | %4d   | %8.0fms | %3.0f%%\n",
               nn, alpha, solved, total, solved, tms / total,
               100.0 * solved / total);
        fflush(stdout);

        if (tms / total > 180000 && solved == 0) {
            printf("  (stopping alpha=%.3f: too slow)\n", alpha);
            while (ti + 1 < n_tests && tests[ti + 1].alpha == alpha)
                ti++;
        }
    }

    printf("\n=== COMPARISON ===\n");
    printf("sp_v4 (hard decimation): n=3000 works, n=5000+ fails\n");
    printf("rSP (this, reinforced):  (results above)\n");
    printf("Literature rSP:          n=100000+ near threshold\n");

    return 0;
}
