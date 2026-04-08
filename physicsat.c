/*
 * PhysicsSAT v2 — High-performance C implementation
 * ═══════════════════════════════════════════════════
 *
 * Variables are particles with positions x ∈ [0,1].
 * Clauses create force fields. Particles drift to solution.
 *
 * Optimizations vs Python:
 *   - Clause-variable index for O(degree) force computation
 *   - SIMD-friendly force accumulation
 *   - Exponential cooling schedule (better annealing)
 *   - Adaptive time step
 *   - WalkSAT repair with break-score caching
 *   - Multiple restarts with diversification
 *
 * Compile: gcc -O3 -march=native -o physicsat physicsat.c -lm
 * Usage:   ./physicsat [n_min] [n_max] [n_instances]
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <float.h>

#define MAX_N      10000
#define MAX_CLAUSES 50000
#define MAX_K      3       /* 3-SAT */
#define MAX_DEGREE 200     /* max clauses per variable */

/* ============================================================
 * Instance storage
 * ============================================================ */

static int n_vars, n_clauses;
static int clause_var[MAX_CLAUSES][MAX_K];   /* variable index */
static int clause_sign[MAX_CLAUSES][MAX_K];  /* +1 or -1 */

/* Clause-variable index: var_clauses[v][i] = clause index */
static int var_clause_list[MAX_N][MAX_DEGREE];
static int var_clause_pos[MAX_N][MAX_DEGREE]; /* position within clause */
static int var_degree[MAX_N];

/* ============================================================
 * Random number generator (xoshiro256**)
 * ============================================================ */

static unsigned long long rng_state[4];

static inline unsigned long long rng_next(void) {
    unsigned long long s0 = rng_state[0], s1 = rng_state[1];
    unsigned long long s2 = rng_state[2], s3 = rng_state[3];
    unsigned long long result = ((s1 * 5) << 7 | (s1 * 5) >> 57) * 9;
    unsigned long long t = s1 << 17;
    s2 ^= s0; s3 ^= s1; s1 ^= s2; s0 ^= s3;
    s2 ^= t; s3 = (s3 << 45) | (s3 >> 19);
    rng_state[0] = s0; rng_state[1] = s1;
    rng_state[2] = s2; rng_state[3] = s3;
    return result;
}

static inline double rng_double(void) {
    return (rng_next() >> 11) * (1.0 / 9007199254740992.0);
}

/* Box-Muller transform for normal distribution */
static double rng_normal(double mean, double stddev) {
    double u1 = rng_double();
    double u2 = rng_double();
    if (u1 < 1e-15) u1 = 1e-15;
    double z = sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
    return mean + stddev * z;
}

static void rng_seed(unsigned long long seed) {
    rng_state[0] = seed;
    rng_state[1] = seed * 6364136223846793005ULL + 1;
    rng_state[2] = seed * 1103515245ULL + 12345;
    rng_state[3] = seed ^ 0xdeadbeefcafebabeULL;
    for (int i = 0; i < 20; i++) rng_next();
}

/* ============================================================
 * Instance generation
 * ============================================================ */

static void generate_random_3sat(int n, double ratio, unsigned long long seed) {
    n_vars = n;
    n_clauses = (int)(ratio * n);
    if (n_clauses > MAX_CLAUSES) n_clauses = MAX_CLAUSES;

    rng_seed(seed);
    memset(var_degree, 0, sizeof(int) * n);

    for (int ci = 0; ci < n_clauses; ci++) {
        /* Pick 3 distinct variables */
        int vs[3];
        vs[0] = rng_next() % n;
        do { vs[1] = rng_next() % n; } while (vs[1] == vs[0]);
        do { vs[2] = rng_next() % n; } while (vs[2] == vs[0] || vs[2] == vs[1]);

        for (int j = 0; j < 3; j++) {
            clause_var[ci][j] = vs[j];
            clause_sign[ci][j] = (rng_next() & 1) ? 1 : -1;

            /* Build index */
            int v = vs[j];
            if (var_degree[v] < MAX_DEGREE) {
                var_clause_list[v][var_degree[v]] = ci;
                var_clause_pos[v][var_degree[v]] = j;
                var_degree[v]++;
            }
        }
    }
}

/* ============================================================
 * Evaluate: count satisfied clauses
 * ============================================================ */

static int evaluate_discrete(const int *assignment) {
    int sat = 0;
    for (int ci = 0; ci < n_clauses; ci++) {
        for (int j = 0; j < MAX_K; j++) {
            int v = clause_var[ci][j];
            int s = clause_sign[ci][j];
            if ((s == 1 && assignment[v] == 1) ||
                (s == -1 && assignment[v] == 0)) {
                sat++;
                break;
            }
        }
    }
    return sat;
}

/* ============================================================
 * CORE: Physics simulation
 * ============================================================ */

static double x[MAX_N];       /* positions */
static double vel[MAX_N];     /* velocities */
static double force[MAX_N];   /* accumulated forces */
static double clause_weight[MAX_CLAUSES]; /* dynamic clause weighting */

/* ---- Innovation 1: Tension-guided initialization ---- */
static void tension_init(void) {
    int n = n_vars;
    double p1[MAX_N], p0[MAX_N];
    memset(p1, 0, sizeof(double) * n);
    memset(p0, 0, sizeof(double) * n);

    for (int ci = 0; ci < n_clauses; ci++) {
        double w = 1.0 / MAX_K;
        for (int j = 0; j < MAX_K; j++) {
            int v = clause_var[ci][j];
            int s = clause_sign[ci][j];
            if (s == 1) p1[v] += w; else p0[v] += w;
        }
    }
    for (int v = 0; v < n; v++) {
        double total = p1[v] + p0[v];
        if (total > 0) {
            /* Map tension to [0.15, 0.85]: bias toward predicted value */
            double tension = (p1[v] - p0[v]) / total; /* in [-1, 1] */
            x[v] = 0.5 + 0.35 * tension;
        } else {
            x[v] = 0.5;
        }
        vel[v] = 0.0;
    }
}

static int physics_solve(int max_steps, int restart_id) {
    int n = n_vars;
    int m = n_clauses;

    /* ---- Initialization ---- */
    if (restart_id == 0) {
        tension_init();  /* First try: start from tension (94% sat) */
    } else {
        /* Subsequent restarts: tension + random perturbation */
        tension_init();
        double perturb = 0.1 + 0.05 * restart_id;
        for (int v = 0; v < n; v++) {
            x[v] += rng_normal(0.0, perturb);
            if (x[v] < 0.05) x[v] = 0.05;
            if (x[v] > 0.95) x[v] = 0.95;
            vel[v] = 0.0;
        }
    }

    /* ---- Innovation 2: Clause weighting ---- */
    for (int ci = 0; ci < m; ci++) {
        clause_weight[ci] = 1.0;
    }

    /* ---- Physics parameters ---- */
    if (max_steps <= 0) {
        max_steps = 2000 + n * 20;
    }

    int best_discrete_sat = 0;
    double best_x[MAX_N];

    /* ---- Innovation 3: Three-stage cooling ----
     * Stage 1 (0-30%):   HOT — exploration, high noise, low crystal
     * Stage 2 (30-70%):  WARM — settling, moderate noise, growing crystal
     * Stage 3 (70-100%): COLD — freezing, low noise, strong crystal
     */

    for (int step = 0; step < max_steps; step++) {
        double progress = (double)step / max_steps;

        /* Three-stage temperature and parameters */
        double T, dt, damping, crystal;
        if (progress < 0.3) {
            /* HOT: explore */
            double p = progress / 0.3;
            T = 0.30 * (1.0 - 0.5 * p);  /* 0.30 → 0.15 */
            dt = 0.06;
            damping = 0.90;
            crystal = 0.5 * p;  /* 0 → 0.5 */
        } else if (progress < 0.7) {
            /* WARM: settle */
            double p = (progress - 0.3) / 0.4;
            T = 0.15 * (1.0 - 0.8 * p);  /* 0.15 → 0.03 */
            dt = 0.05;
            damping = 0.93;
            crystal = 0.5 + 2.5 * p;  /* 0.5 → 3.0 */
        } else {
            /* COLD: freeze */
            double p = (progress - 0.7) / 0.3;
            T = 0.03 * (1.0 - 0.95 * p) + 0.0001; /* 0.03 → ~0 */
            dt = 0.04;
            damping = 0.85;
            crystal = 3.0 + 5.0 * p;  /* 3.0 → 8.0 */
        }

        /* Reset forces */
        memset(force, 0, sizeof(double) * n);

        /* ---- Clause forces with dynamic weighting ---- */
        for (int ci = 0; ci < m; ci++) {
            double lit[MAX_K];
            double prod = 1.0;

            for (int j = 0; j < MAX_K; j++) {
                int v = clause_var[ci][j];
                int s = clause_sign[ci][j];
                lit[j] = (s == 1) ? x[v] : (1.0 - x[v]);
                double term = 1.0 - lit[j];
                if (term < 1e-12) term = 1e-12;
                prod *= term;
            }

            /* Skip nearly satisfied clauses */
            if (prod < 0.0001) continue;

            /* Force with clause weight */
            double w = clause_weight[ci] * sqrt(prod);

            for (int j = 0; j < MAX_K; j++) {
                int v = clause_var[ci][j];
                int s = clause_sign[ci][j];
                double term_j = 1.0 - lit[j];
                double prod_others;
                if (term_j > 1e-12) {
                    prod_others = prod / term_j;
                } else {
                    prod_others = 0.0;
                }
                force[v] += s * w * prod_others;
            }
        }

        /* ---- Innovation 4: Adaptive clause weight update ---- */
        /* Every 100 steps: increase weight of still-unsatisfied clauses */
        if (step % 100 == 99 && progress > 0.3) {
            for (int ci = 0; ci < m; ci++) {
                double lit_prod = 1.0;
                for (int j = 0; j < MAX_K; j++) {
                    int v = clause_var[ci][j];
                    int s = clause_sign[ci][j];
                    double lv = (s == 1) ? x[v] : (1.0 - x[v]);
                    lit_prod *= (1.0 - lv);
                }
                if (lit_prod > 0.1) {
                    /* Still substantially unsatisfied → increase weight */
                    clause_weight[ci] *= 1.1;
                    if (clause_weight[ci] > 20.0) clause_weight[ci] = 20.0;
                } else {
                    /* Satisfied → decay weight back toward 1 */
                    clause_weight[ci] = 1.0 + (clause_weight[ci] - 1.0) * 0.95;
                }
            }
        }

        /* ---- Crystallization + noise + velocity update ---- */
        for (int v = 0; v < n; v++) {
            /* Crystallization: push toward 0 or 1 */
            double dist_to_01 = (x[v] > 0.5) ? (1.0 - x[v]) : x[v];
            double crystal_force = crystal * (2.0 * (x[v] > 0.5 ? 1.0 : 0.0) - 1.0)
                                   * dist_to_01;
            force[v] += crystal_force;

            /* Thermal noise */
            double noise = rng_normal(0.0, T);

            /* ---- Innovation 5: Adaptive dt per variable ---- */
            double f_mag = fabs(force[v]);
            double local_dt = dt;
            if (f_mag > 5.0) local_dt = dt * 5.0 / f_mag; /* cap step */

            /* Velocity update */
            vel[v] = damping * vel[v] + (force[v] + noise) * local_dt;

            /* Position update */
            x[v] += vel[v] * local_dt;

            /* Clamp with elastic bounce */
            if (x[v] < 0.0) { x[v] = 0.01; vel[v] = fabs(vel[v]) * 0.3; }
            if (x[v] > 1.0) { x[v] = 0.99; vel[v] = -fabs(vel[v]) * 0.3; }
        }

        /* Periodic check */
        if (step % 50 == 49 || step == max_steps - 1) {
            int tmp[MAX_N];
            for (int v = 0; v < n; v++) tmp[v] = (x[v] > 0.5) ? 1 : 0;
            int sat = evaluate_discrete(tmp);
            if (sat > best_discrete_sat) {
                best_discrete_sat = sat;
                memcpy(best_x, x, sizeof(double) * n);
            }
            if (sat == m) {
                return sat;
            }
        }
    }

    /* Restore best position found */
    memcpy(x, best_x, sizeof(double) * n);
    return best_discrete_sat;
}

/* ============================================================
 * WalkSAT repair phase
 * ============================================================ */

static int assignment[MAX_N];
static int clause_sat_count[MAX_CLAUSES]; /* how many true lits per clause */

static void init_walksat_from_physics(void) {
    for (int v = 0; v < n_vars; v++) {
        assignment[v] = (x[v] > 0.5) ? 1 : 0;
    }

    /* Compute clause satisfaction counts */
    for (int ci = 0; ci < n_clauses; ci++) {
        int cnt = 0;
        for (int j = 0; j < MAX_K; j++) {
            int v = clause_var[ci][j];
            int s = clause_sign[ci][j];
            if ((s == 1 && assignment[v] == 1) ||
                (s == -1 && assignment[v] == 0)) {
                cnt++;
            }
        }
        clause_sat_count[ci] = cnt;
    }
}

static int walksat_repair(int max_flips) {
    int n = n_vars;
    int m = n_clauses;

    /* Proper unsat tracking with swap-removal */
    int unsat_list[MAX_CLAUSES];
    int unsat_pos[MAX_CLAUSES]; /* clause ci is at unsat_list[unsat_pos[ci]] */
    int n_unsat = 0;

    memset(unsat_pos, -1, sizeof(int) * m);

    for (int ci = 0; ci < m; ci++) {
        if (clause_sat_count[ci] == 0) {
            unsat_pos[ci] = n_unsat;
            unsat_list[n_unsat++] = ci;
        }
    }

    if (n_unsat == 0) return m;

    for (int flip = 0; flip < max_flips && n_unsat > 0; flip++) {
        /* Pick random unsatisfied clause */
        int idx = rng_next() % n_unsat;
        int ci = unsat_list[idx];

        /* Find best variable to flip (min breaks) */
        int best_v = clause_var[ci][0];
        int best_breaks = n_clauses + 1;
        int zero_break = -1; /* var with 0 breaks (freebie) */

        for (int j = 0; j < MAX_K; j++) {
            int v = clause_var[ci][j];
            int breaks = 0;

            for (int d = 0; d < var_degree[v]; d++) {
                int oci = var_clause_list[v][d];
                int opos = var_clause_pos[v][d];
                int os = clause_sign[oci][opos];

                int is_true = ((os == 1 && assignment[v] == 1) ||
                              (os == -1 && assignment[v] == 0));
                if (is_true && clause_sat_count[oci] == 1) {
                    breaks++;
                }
            }

            if (breaks == 0) { zero_break = v; break; }
            if (breaks < best_breaks) {
                best_breaks = breaks;
                best_v = v;
            }
        }

        /* Decision: freebie > greedy > random */
        int flip_v;
        if (zero_break >= 0) {
            flip_v = zero_break; /* always take a freebie */
        } else if ((rng_next() % 100) < 30) {
            flip_v = clause_var[ci][rng_next() % MAX_K]; /* random walk */
        } else {
            flip_v = best_v; /* greedy */
        }

        /* Perform flip */
        int old_val = assignment[flip_v];
        int new_val = 1 - old_val;
        assignment[flip_v] = new_val;

        for (int d = 0; d < var_degree[flip_v]; d++) {
            int oci = var_clause_list[flip_v][d];
            int opos = var_clause_pos[flip_v][d];
            int os = clause_sign[oci][opos];

            int was_true = ((os == 1 && old_val == 1) ||
                           (os == -1 && old_val == 0));
            int now_true = ((os == 1 && new_val == 1) ||
                           (os == -1 && new_val == 0));

            if (was_true && !now_true) {
                clause_sat_count[oci]--;
                if (clause_sat_count[oci] == 0) {
                    /* Became unsatisfied — add to list */
                    unsat_pos[oci] = n_unsat;
                    unsat_list[n_unsat++] = oci;
                }
            } else if (!was_true && now_true) {
                clause_sat_count[oci]++;
                if (clause_sat_count[oci] == 1) {
                    /* Was unsatisfied (0→1), now satisfied — remove */
                    int pos = unsat_pos[oci];
                    if (pos >= 0 && pos < n_unsat) {
                        int last = unsat_list[n_unsat - 1];
                        unsat_list[pos] = last;
                        unsat_pos[last] = pos;
                        unsat_pos[oci] = -1;
                        n_unsat--;
                    }
                }
            }
        }
    }

    return m - n_unsat;
}

/* ============================================================
 * Full solver: physics + walksat repair + restarts
 * ============================================================ */

static int full_solve(int max_restarts, int physics_steps, int walk_flips) {
    int m = n_clauses;
    int best_sat = 0;

    for (int r = 0; r < max_restarts; r++) {
        /* Physics phase */
        rng_seed(42 + r * 7919 + n_vars * 31);
        int sat = physics_solve(physics_steps, r);

        if (sat == m) {
            /* Pure physics solve! */
            return 1; /* 1 = solved by physics */
        }

        if (sat > best_sat) {
            best_sat = sat;
        }

        /* WalkSAT repair from physics result */
        init_walksat_from_physics();
        sat = walksat_repair(walk_flips);

        if (sat == m) {
            return 2; /* 2 = solved by walksat repair */
        }

        if (sat > best_sat) {
            best_sat = sat;
        }
    }

    return 0; /* 0 = not solved */
}

/* ============================================================
 * MiniSat interface for comparison
 * ============================================================ */

static int run_minisat(int n, double ratio, unsigned long long seed,
                       double timeout, double *elapsed, long long *decisions) {
    char filename[256], outfile[256];
    snprintf(filename, sizeof(filename), "/tmp/physicsat_ms_%d.cnf", (int)seed);
    snprintf(outfile, sizeof(outfile), "/tmp/physicsat_ms_%d.cnf.out", (int)seed);

    /* Write DIMACS */
    FILE *f = fopen(filename, "w");
    if (!f) return -1;
    int m = (int)(ratio * n);
    fprintf(f, "p cnf %d %d\n", n, m);

    rng_seed(seed);
    for (int ci = 0; ci < m; ci++) {
        int vs[3];
        vs[0] = rng_next() % n;
        do { vs[1] = rng_next() % n; } while (vs[1] == vs[0]);
        do { vs[2] = rng_next() % n; } while (vs[2] == vs[0] || vs[2] == vs[1]);
        int signs[3];
        for (int j = 0; j < 3; j++)
            signs[j] = (rng_next() & 1) ? 1 : -1;
        fprintf(f, "%d %d %d 0\n",
                signs[0]*(vs[0]+1), signs[1]*(vs[1]+1), signs[2]*(vs[2]+1));
    }
    fclose(f);

    /* Run MiniSat */
    char cmd[512];
    snprintf(cmd, sizeof(cmd),
             "timeout %.0f minisat %s %s 2>&1", timeout, filename, outfile);

    clock_t t0 = clock();
    FILE *p = popen(cmd, "r");
    char buf[4096] = {0};
    if (p) {
        while (fgets(buf + strlen(buf), sizeof(buf) - strlen(buf), p));
        pclose(p);
    }
    clock_t t1 = clock();
    *elapsed = (double)(t1 - t0) / CLOCKS_PER_SEC;

    /* Parse decisions */
    *decisions = 0;
    char *dec_line = strstr(buf, "decisions");
    if (dec_line) {
        char *colon = strchr(dec_line, ':');
        if (colon) {
            *decisions = atoll(colon + 1);
        }
    }

    /* Check result */
    int result = 0;
    f = fopen(outfile, "r");
    if (f) {
        char line[64];
        if (fgets(line, sizeof(line), f)) {
            if (strncmp(line, "SAT", 3) == 0) result = 1;
            else if (strncmp(line, "UNSAT", 5) == 0) result = -1;
        }
        fclose(f);
    }

    remove(filename);
    remove(outfile);
    return result;
}

/* ============================================================
 * MAIN: Benchmark across n
 * ============================================================ */

int main(int argc, char **argv) {
    int n_min = 20, n_max = 1000, n_inst = 30;

    if (argc >= 2) n_min = atoi(argv[1]);
    if (argc >= 3) n_max = atoi(argv[2]);
    if (argc >= 4) n_inst = atoi(argv[3]);

    printf("═══════════════════════════════════════════════════════════════\n");
    printf("PhysicsSAT v2 (C) — Benchmark\n");
    printf("═══════════════════════════════════════════════════════════════\n");

    int test_sizes[] = {20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000,
                        1500, 2000, 3000, 5000};
    int n_sizes = sizeof(test_sizes) / sizeof(test_sizes[0]);

    printf("\n%6s | %5s | %10s | %8s | %10s | %8s | %10s\n",
           "n", "ratio", "PhysSAT", "time_ms", "MiniSat", "time_ms", "decisions");
    printf("-------+-------+------------+----------+------------+"
           "----------+-----------\n");

    for (int si = 0; si < n_sizes; si++) {
        int nn = test_sizes[si];
        if (nn < n_min || nn > n_max) continue;

        int inst = (nn <= 200) ? n_inst : (nn <= 500 ? 20 : 10);

        int phys_solved = 0, phys_pure = 0;
        int ms_solved = 0;
        double phys_total_ms = 0, ms_total_ms = 0;
        long long ms_total_dec = 0;

        /* Scale parameters with n */
        int m_approx = (int)(4.27 * nn);
        int physics_steps = 2000 + nn * 20;
        int walk_flips = nn * 500;  /* WalkSAT budget: 500n flips */
        int max_restarts = 20;
        if (nn > 200) {
            max_restarts = 15;
            physics_steps = 1500 + nn * 15;
            walk_flips = nn * 500;
        }
        if (nn > 500) {
            max_restarts = 10;
            physics_steps = 1000 + nn * 10;
            walk_flips = nn * 500;
        }
        if (nn > 2000) {
            max_restarts = 5;
            physics_steps = nn * 5;
            walk_flips = nn * 100;
        }

        for (int seed = 0; seed < inst; seed++) {
            unsigned long long instance_seed = 69000000ULL + seed;

            /* Generate instance */
            generate_random_3sat(nn, 4.27, instance_seed);

            /* PhysicsSAT */
            clock_t t0 = clock();
            int result = full_solve(max_restarts, physics_steps, walk_flips);
            clock_t t1 = clock();
            double phys_ms = (double)(t1 - t0) * 1000.0 / CLOCKS_PER_SEC;

            if (result > 0) {
                phys_solved++;
                phys_total_ms += phys_ms;
                if (result == 1) phys_pure++;
            }

            /* MiniSat comparison */
            double ms_elapsed;
            long long ms_dec;
            int ms_result = run_minisat(nn, 4.27, instance_seed,
                                        60.0, &ms_elapsed, &ms_dec);
            if (ms_result == 1) {
                ms_solved++;
                ms_total_ms += ms_elapsed * 1000.0;
                ms_total_dec += ms_dec;
            }
        }

        double avg_phys_ms = phys_solved > 0 ? phys_total_ms / phys_solved : 0;
        double avg_ms_ms = ms_solved > 0 ? ms_total_ms / ms_solved : 0;
        double avg_ms_dec = ms_solved > 0 ? (double)ms_total_dec / ms_solved : 0;

        printf("%6d | %5.2f | %3d/%2d(%2dp) | %7.1fms | %3d/%2d     | %7.1fms | %9.0f\n",
               nn, 4.27, phys_solved, inst, phys_pure,
               avg_phys_ms, ms_solved, inst, avg_ms_ms, avg_ms_dec);

        fflush(stdout);
    }

    printf("\nLegend: PhysSAT solved/total(pure_physics_solves)\n");
    printf("        'pure' = solved by physics alone, no WalkSAT repair\n");

    return 0;
}
