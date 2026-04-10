/*
 * SP-Gradient Hybrid: Survey Propagation biases as soft compass for gradient ascent
 * ==================================================================================
 *
 * NOVEL IDEA: Instead of SP's destructive decimation, use SP bias information
 * as a Bayesian prior injected into a continuous optimization landscape.
 *
 * Algorithm:
 *   1. Run SP to convergence (no decimation) -> get W_plus[i], W_minus[i]
 *   2. Define augmented objective:
 *      F(x) = soft_sat(x) + lambda * sum_i [W_plus[i]*log(x[i]) + W_minus[i]*log(1-x[i])]
 *      The SP prior pushes x[i] toward cluster-predicted values
 *   3. ADAM optimizer on F(x)
 *   4. lambda ramps up as confidence grows
 *   5. Periodically re-run SP to refresh biases
 *   6. Round to {0,1} when converged near corners, then WalkSAT polish
 *
 * Why this might work:
 *   - SP sees cluster structure that gradient cannot
 *   - Gradient keeps everything smooth (no catastrophic decimation)
 *   - The two approaches complement each other's weaknesses
 *
 * Compile: gcc -O3 -march=native -o sp_hybrid sp_gradient_hybrid.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       10000
#define MAX_CLAUSES 50000
#define MAX_K       3
#define MAX_DEGREE  300

/* ======== Instance data ======== */
static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

/* ======== SP state ======== */
static double eta[MAX_CLAUSES][MAX_K];
static double W_plus[MAX_N], W_minus[MAX_N];

/* ======== Gradient state ======== */
static double x[MAX_N];          /* continuous assignment in [0,1] */
static double grad[MAX_N];       /* gradient buffer */
static double adam_m[MAX_N];     /* ADAM first moment */
static double adam_v[MAX_N];     /* ADAM second moment */

/* ======== RNG ======== */
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

/* ======== Instance generation ======== */
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
}

/* ======== Discrete evaluation ======== */
static int eval_disc(const int *a) {
    int s = 0;
    for(int ci=0; ci<n_clauses; ci++)
        for(int j=0; j<3; j++) {
            int v = cl_var[ci][j], ss = cl_sign[ci][j];
            if((ss==1 && a[v]==1) || (ss==-1 && a[v]==0)) { s++; break; }
        }
    return s;
}

/* ======== SP message passing (no decimation) ========
 * Runs SP on the full factor graph using the CURRENT continuous assignment
 * to softly weight things. No variables are fixed/decimated.
 */

static int *clause_perm;
static int perm_size;

static void init_perm(void) {
    if(!clause_perm) clause_perm = (int*)malloc(MAX_CLAUSES * sizeof(int));
    perm_size = 0;
    for(int ci=0; ci<n_clauses; ci++)
        clause_perm[perm_size++] = ci;
}

static void shuffle_perm(void) {
    for(int i=perm_size-1; i>0; i--) {
        int j = rng_next() % (i+1);
        int t = clause_perm[i]; clause_perm[i] = clause_perm[j]; clause_perm[j] = t;
    }
}

/* Standard 3-state SP edge computation (no fixed variables) */
static inline double sp_edge(int ci, int pos_i) {
    double product = 1.0;
    for(int pj = 0; pj < 3; pj++) {
        if(pj == pos_i) continue;
        int j = cl_var[ci][pj];
        int sign_j_a = cl_sign[ci][pj];
        double ps = 1.0, pu = 1.0;
        for(int d = 0; d < vdeg[j]; d++) {
            int bi = vlist[j][d], bp = vpos[j][d];
            if(bi == ci) continue;
            double eb = eta[bi][bp];
            if(cl_sign[bi][bp] == sign_j_a) ps *= (1.0 - eb);
            else pu *= (1.0 - eb);
        }
        double Pu = (1.0 - pu) * ps;
        double Ps = (1.0 - ps) * pu;
        double P0 = pu * ps;
        double den = Pu + Ps + P0;
        product *= (den > 1e-15) ? (Pu / den) : 0.0;
    }
    return product;
}

/* One SP sweep */
static double sp_sweep(double rho) {
    shuffle_perm();
    double max_ch = 0;
    for(int e = 0; e < perm_size; e++) {
        int ci = clause_perm[e];
        for(int p = 0; p < 3; p++) {
            double nv = sp_edge(ci, p);
            double ov = eta[ci][p];
            double up = rho * ov + (1.0 - rho) * nv;
            double ch = fabs(up - ov);
            if(ch > max_ch) max_ch = ch;
            eta[ci][p] = up;
        }
    }
    return max_ch;
}

/* Compute SP biases W_plus[i], W_minus[i] for each variable */
static void compute_bias(void) {
    for(int i = 0; i < n_vars; i++) {
        W_plus[i] = W_minus[i] = 0;
        double pp = 1.0, pm = 1.0;
        for(int d = 0; d < vdeg[i]; d++) {
            int ci = vlist[i][d], p = vpos[i][d];
            double e = eta[ci][p];
            if(cl_sign[ci][p] == 1) pp *= (1.0 - e);
            else pm *= (1.0 - e);
        }
        double pi_p = (1.0 - pp) * pm;
        double pi_m = (1.0 - pm) * pp;
        double pi_0 = pp * pm;
        double tot = pi_p + pi_m + pi_0;
        if(tot > 1e-15) {
            W_plus[i] = pi_p / tot;
            W_minus[i] = pi_m / tot;
        }
    }
}

/* Run SP to convergence. Returns 1 if converged, 0 otherwise. */
static int run_sp(unsigned long long sp_seed) {
    rng_seed(sp_seed);
    /* Initialize eta randomly */
    for(int ci=0; ci<n_clauses; ci++)
        for(int j=0; j<3; j++)
            eta[ci][j] = rng_double();

    init_perm();

    /* Try rho=0.1 first */
    int conv = 0;
    for(int iter=0; iter < 100; iter++) {
        double ch = sp_sweep(0.1);
        if(ch < 1e-4) { conv=1; break; }
    }
    /* If not converged, try heavier damping */
    if(!conv) {
        for(int iter=0; iter < 80; iter++) {
            double ch = sp_sweep(0.3);
            if(ch < 1e-4) { conv=1; break; }
        }
    }
    if(!conv) {
        for(int iter=0; iter < 50; iter++) {
            double ch = sp_sweep(0.5);
            if(ch < 1e-4) { conv=1; break; }
        }
    }

    if(conv) compute_bias();
    return conv;
}

/* Check if SP is non-trivial (surveys not all zero) */
static int sp_is_nontrivial(void) {
    double max_bias = 0;
    for(int i=0; i<n_vars; i++) {
        double b = fabs(W_plus[i] - W_minus[i]);
        if(b > max_bias) max_bias = b;
    }
    return (max_bias > 0.01);
}

/* ======== soft_sat + SP prior objective ========
 *
 * F(x) = soft_sat(x) + lambda * sum_i [W_plus[i]*log(x[i]) + W_minus[i]*log(1-x[i])]
 *
 * soft_sat(x) = sum_clauses [1 - prod_j (1 - lit_j)]
 *   where lit_j = x[v] if sign=+1, (1-x[v]) if sign=-1
 *
 * Gradient of SP prior term w.r.t. x[i]:
 *   d/dx[i] = lambda * [W_plus[i]/x[i] - W_minus[i]/(1-x[i])]
 */

static double compute_objective_and_grad(double lambda, int use_sp_prior) {
    int n = n_vars, m = n_clauses;
    memset(grad, 0, sizeof(double)*n);

    /* Part 1: soft_sat */
    double total = 0;
    for(int ci=0; ci<m; ci++) {
        double lit[3], prod = 1.0;
        for(int j=0; j<3; j++) {
            int v = cl_var[ci][j], s = cl_sign[ci][j];
            lit[j] = (s==1) ? x[v] : (1.0 - x[v]);
            double t = 1.0 - lit[j];
            if(t < 1e-15) t = 1e-15;
            prod *= t;
        }
        total += (1.0 - prod);
        if(prod > 1e-15) {
            for(int j=0; j<3; j++) {
                int v = cl_var[ci][j], s = cl_sign[ci][j];
                double t = 1.0 - lit[j];
                if(t < 1e-15) t = 1e-15;
                grad[v] += s * (prod / t);
            }
        }
    }

    /* Part 2: SP prior */
    if(use_sp_prior && lambda > 1e-12) {
        for(int i=0; i<n; i++) {
            double xi = x[i];
            /* Clamp to avoid log(0) */
            if(xi < 1e-8) xi = 1e-8;
            if(xi > 1.0 - 1e-8) xi = 1.0 - 1e-8;

            double wp = W_plus[i], wm = W_minus[i];
            total += lambda * (wp * log(xi) + wm * log(1.0 - xi));
            grad[i] += lambda * (wp / xi - wm / (1.0 - xi));
        }
    }

    return total;
}

/* ======== WalkSAT (polish phase) ======== */
static int walksat(int *a, int max_flips) {
    int n = n_vars, m = n_clauses;
    int *sc = (int*)calloc(m, sizeof(int));
    for(int ci=0; ci<m; ci++)
        for(int j=0; j<3; j++) {
            int v = cl_var[ci][j], s = cl_sign[ci][j];
            if((s==1 && a[v]==1) || (s==-1 && a[v]==0)) sc[ci]++;
        }

    int *ul = (int*)malloc(m * sizeof(int));
    int *up = (int*)malloc(m * sizeof(int));
    int nu = 0;
    memset(up, -1, sizeof(int)*m);
    for(int ci=0; ci<m; ci++)
        if(sc[ci]==0) { up[ci]=nu; ul[nu++]=ci; }

    for(int f=0; f<max_flips && nu>0; f++) {
        int ci = ul[rng_next() % nu];
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
        int fv = (zb>=0) ? zb : ((rng_next()%100<57) ? cl_var[ci][rng_next()%3] : bv);

        int old = a[fv], nw = 1-old;
        a[fv] = nw;
        for(int d=0; d<vdeg[fv]; d++) {
            int oci = vlist[fv][d], opos = vpos[fv][d];
            int os = cl_sign[oci][opos];
            int was = ((os==1 && old==1) || (os==-1 && old==0));
            int now = ((os==1 && nw==1)  || (os==-1 && nw==0));
            if(was && !now) {
                sc[oci]--;
                if(sc[oci]==0) { up[oci]=nu; ul[nu++]=oci; }
            } else if(!was && now) {
                sc[oci]++;
                if(sc[oci]==1) {
                    int p2=up[oci];
                    if(p2>=0 && p2<nu) {
                        int l=ul[nu-1]; ul[p2]=l; up[l]=p2; up[oci]=-1; nu--;
                    }
                }
            }
        }
    }

    int sat = m - nu;
    free(sc); free(ul); free(up);
    return sat;
}

/* ======== THE HYBRID SOLVER ========
 *
 * Phases:
 *   Phase 0: Run SP once, get biases
 *   Phase 1: ADAM gradient ascent on F(x) = soft_sat(x) + lambda*SP_prior
 *            lambda ramps from small to moderate
 *   Phase 2: Re-run SP periodically to refresh biases
 *   Phase 3: When converged, round + WalkSAT polish
 */
static int hybrid_solve(int nn, unsigned long long instance_seed) {
    int n = nn, m = n_clauses;

    /* ADAM hyperparameters */
    double adam_lr = 0.005;
    double beta1 = 0.9, beta2 = 0.999, eps = 1e-8;

    int best_disc = 0;
    int *best_a = (int*)malloc(n * sizeof(int));

    int n_restarts = (n <= 300) ? 5 : (n <= 1000 ? 3 : 2);

    for(int restart = 0; restart < n_restarts; restart++) {
        rng_seed(instance_seed * 97ULL + restart * 31337ULL + 777);

        /* Initialize x near center */
        for(int v=0; v<n; v++) {
            x[v] = 0.3 + 0.4 * rng_double();
            adam_m[v] = 0;
            adam_v[v] = 0;
        }

        /* Phase 0: Run SP to get initial biases */
        int sp_ok = run_sp(instance_seed * 13ULL + restart * 7919ULL);
        int use_sp = sp_ok && sp_is_nontrivial();

        /* If SP converged, bias the initial x toward SP predictions */
        if(use_sp) {
            for(int v=0; v<n; v++) {
                double bias_dir = W_plus[v] - W_minus[v];
                /* Gentle nudge toward SP prediction */
                x[v] += 0.1 * bias_dir;
                if(x[v] < 0.05) x[v] = 0.05;
                if(x[v] > 0.95) x[v] = 0.95;
            }
        }

        /* Lambda schedule: start small, ramp up */
        double lambda_base = use_sp ? 0.01 : 0.0;
        double lambda_max = use_sp ? 0.5 : 0.0;

        /* Maximum gradient steps - scale reasonably with n */
        int max_steps;
        if(n <= 100) max_steps = 10000;
        else if(n <= 300) max_steps = 8000;
        else if(n <= 1000) max_steps = 6000;
        else max_steps = 5000;

        int sp_refresh_interval = 2000; /* re-run SP every N steps */
        int stagnant = 0;
        double prev_obj = -1e30;

        for(int step = 0; step < max_steps; step++) {
            /* Lambda ramps up over first half of optimization */
            double progress = (double)step / max_steps;
            double lambda = lambda_base + (lambda_max - lambda_base) * fmin(1.0, progress * 2.0);

            /* Periodically refresh SP biases based on current x */
            if(use_sp && step > 0 && (step % sp_refresh_interval == 0)) {
                int fresh = run_sp(instance_seed * 17ULL + step);
                if(fresh && sp_is_nontrivial()) {
                    /* Keep using SP */
                } else {
                    /* SP trivialized or failed - phase out */
                    use_sp = 0;
                    lambda = 0;
                }
            }

            /* Compute objective and gradient */
            double obj = compute_objective_and_grad(lambda, use_sp);

            /* ADAM update */
            double t_step = step + 1;
            double bc1 = 1.0 - pow(beta1, t_step);
            double bc2 = 1.0 - pow(beta2, t_step);

            for(int v=0; v<n; v++) {
                adam_m[v] = beta1 * adam_m[v] + (1.0 - beta1) * grad[v];
                adam_v[v] = beta2 * adam_v[v] + (1.0 - beta2) * grad[v] * grad[v];
                double m_hat = adam_m[v] / bc1;
                double v_hat = adam_v[v] / bc2;
                x[v] += adam_lr * m_hat / (sqrt(v_hat) + eps);
                /* Soft clamp with reflection */
                if(x[v] < 0.001) x[v] = 0.001;
                if(x[v] > 0.999) x[v] = 0.999;
            }

            /* As optimization progresses, push toward corners (annealing) */
            if(progress > 0.5) {
                double corner_strength = 0.0001 * (progress - 0.5) * 2.0;
                for(int v=0; v<n; v++) {
                    /* Push toward 0 or 1 */
                    if(x[v] > 0.5) x[v] += corner_strength * (1.0 - x[v]);
                    else x[v] -= corner_strength * x[v];
                    if(x[v] < 0.001) x[v] = 0.001;
                    if(x[v] > 0.999) x[v] = 0.999;
                }
            }

            /* Check stagnation */
            if(fabs(obj - prev_obj) < 1e-9) stagnant++;
            else stagnant = 0;
            prev_obj = obj;
            if(stagnant > 1000) break;

            /* Periodic discrete check */
            if(step % 500 == 499 || step == max_steps - 1) {
                int *a = (int*)malloc(n * sizeof(int));
                for(int v=0; v<n; v++) a[v] = (x[v] > 0.5) ? 1 : 0;
                int ds = eval_disc(a);
                if(ds > best_disc) {
                    best_disc = ds;
                    memcpy(best_a, a, sizeof(int)*n);
                }
                if(ds == m) { free(a); free(best_a); return m; }
                free(a);
            }
        }

        /* Final rounding */
        {
            int *a = (int*)malloc(n * sizeof(int));
            for(int v=0; v<n; v++) a[v] = (x[v] > 0.5) ? 1 : 0;
            int ds = eval_disc(a);
            if(ds > best_disc) { best_disc = ds; memcpy(best_a, a, sizeof(int)*n); }
            if(ds == m) { free(a); free(best_a); return m; }

            /* WalkSAT polish on gradient-rounded assignment */
            rng_seed(instance_seed + restart * 999ULL);
            int flips = n * 3000;
            if(flips > 5000000) flips = 5000000;
            int ws = walksat(a, flips);
            if(ws > best_disc) { best_disc = ws; memcpy(best_a, a, sizeof(int)*n); }
            if(ws == m) { free(a); free(best_a); return m; }
            free(a);
        }

        /* Also try WalkSAT starting from SP-biased assignment */
        if(sp_ok) {
            int *wa = (int*)malloc(n * sizeof(int));
            for(int v=0; v<n; v++) {
                if(W_plus[v] > W_minus[v] + 0.1) wa[v] = 1;
                else if(W_minus[v] > W_plus[v] + 0.1) wa[v] = 0;
                else wa[v] = (x[v] > 0.5) ? 1 : 0;
            }
            rng_seed(instance_seed + restart * 5555ULL);
            int flips = n * 3000;
            if(flips > 5000000) flips = 5000000;
            int ws = walksat(wa, flips);
            if(ws > best_disc) { best_disc = ws; memcpy(best_a, wa, sizeof(int)*n); }
            if(ws == m) { free(wa); free(best_a); return m; }
            free(wa);
        }
    }

    /* Final desperation: WalkSAT on best found so far */
    {
        rng_seed(instance_seed + 123456789ULL);
        int flips = n * 5000;
        if(flips > 10000000) flips = 10000000;
        int ws = walksat(best_a, flips);
        if(ws > best_disc) best_disc = ws;
        if(ws == m) { free(best_a); return m; }
    }

    free(best_a);
    return best_disc;
}

/* ======== Benchmark ======== */
static void run_benchmark(double alpha, const char *label) {
    printf("\n====================================================\n");
    printf("SP-Gradient Hybrid | alpha=%.3f (%s)\n", alpha, label);
    printf("====================================================\n");
    printf("%6s | %5s | %6s | %8s | %s\n",
           "n", "total", "solved", "time_ms", "rate");
    printf("-------+-------+--------+----------+------\n");

    int test_n[] = {100, 200, 300, 500, 750, 1000, 2000};
    int sizes = 7;

    for(int ti=0; ti<sizes; ti++) {
        int nn = test_n[ti];
        int ni;
        if(nn <= 200) ni = 20;
        else if(nn <= 500) ni = 10;
        else if(nn <= 2000) ni = 5;
        else ni = 3;

        int solved = 0, total = 0;
        double tms = 0;
        double sum_unsat = 0;

        for(int seed=0; seed < ni * 3 && total < ni; seed++) {
            generate(nn, alpha, 11000000ULL + seed);

            clock_t t0 = clock();
            int sat = hybrid_solve(nn, 11000000ULL + seed);
            clock_t t1 = clock();
            double ms = (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;

            tms += ms;
            total++;
            sum_unsat += (n_clauses - sat);
            if(sat == n_clauses) solved++;
        }

        printf("%6d | %2d/%2d | %4d   | %7.0fms | %3.0f%% (avg_unsat=%.1f)\n",
               nn, solved, total, solved, tms/total,
               100.0*solved/total, sum_unsat/total);
        fflush(stdout);

        /* Don't burn too long on impossible sizes */
        if(tms/total > 120000 && solved == 0) {
            printf("  (stopping: >120s/instance with 0%% rate)\n");
            break;
        }
    }
}

int main(void) {
    printf("================================================================\n");
    printf("SP-GRADIENT HYBRID SOLVER\n");
    printf("================================================================\n");
    printf("Novel approach: SP biases as soft compass for ADAM gradient ascent\n");
    printf("  F(x) = soft_sat(x) + lambda * SP_prior(x)\n");
    printf("  SP_prior = sum_i [W+[i]*log(x[i]) + W-[i]*log(1-x[i])]\n");
    printf("  + WalkSAT polish on rounded solutions\n");
    printf("================================================================\n");

    run_benchmark(4.0, "below threshold");
    run_benchmark(4.267, "AT threshold");

    printf("\n=== COMPARISON ===\n");
    printf("SP v4 (hard decimate):  Works but fragile at threshold\n");
    printf("Pure gradient:          Hits sqrt(n) barrier\n");
    printf("Hybrid (this):          SP compass + smooth gradient (results above)\n");

    return 0;
}
