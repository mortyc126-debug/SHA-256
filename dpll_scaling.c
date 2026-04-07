/*
 * DPLL+tension scaling test in C.
 * Measures effective k = log2(calls) for n = 10 to 200.
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <string.h>

#define MAX_N 300
#define MAX_M 1500
#define MAX_CALLS 2000000

typedef struct {
    int vars[3];
    int signs[3];
} Clause;

Clause clauses[MAX_M];
int n, m;
int fixed[MAX_N];       /* -1 = unfixed, 0 or 1 = fixed */
long long calls;

/* Simple LCG random */
unsigned long rng_state = 42;
unsigned long rng_next(void) {
    rng_state = rng_state * 6364136223846793005ULL + 1442695040888963407ULL;
    return rng_state >> 33;
}

void generate_random_3sat(int nn, double ratio, unsigned long seed) {
    n = nn;
    m = (int)(ratio * n);
    rng_state = seed;

    for (int i = 0; i < m; i++) {
        /* Pick 3 distinct variables */
        int v0 = rng_next() % n;
        int v1 = rng_next() % n;
        while (v1 == v0) v1 = rng_next() % n;
        int v2 = rng_next() % n;
        while (v2 == v0 || v2 == v1) v2 = rng_next() % n;

        clauses[i].vars[0] = v0;
        clauses[i].vars[1] = v1;
        clauses[i].vars[2] = v2;
        clauses[i].signs[0] = (rng_next() % 2) ? 1 : -1;
        clauses[i].signs[1] = (rng_next() % 2) ? 1 : -1;
        clauses[i].signs[2] = (rng_next() % 2) ? 1 : -1;
    }
}

int evaluate(int *assignment) {
    int sat = 0;
    for (int i = 0; i < m; i++) {
        int ok = 0;
        for (int j = 0; j < 3; j++) {
            int v = clauses[i].vars[j];
            int s = clauses[i].signs[j];
            if ((s == 1 && assignment[v] == 1) || (s == -1 && assignment[v] == 0)) {
                ok = 1; break;
            }
        }
        if (ok) sat++;
    }
    return sat;
}

double bit_tension(int var, int *fix) {
    double p1 = 0, p0 = 0;
    for (int i = 0; i < m; i++) {
        int has_var = 0, var_sign = 0;
        int satisfied = 0;
        int remaining = 0;

        for (int j = 0; j < 3; j++) {
            int v = clauses[i].vars[j];
            int s = clauses[i].signs[j];
            if (v == var) { has_var = 1; var_sign = s; }
            else if (fix[v] >= 0) {
                if ((s == 1 && fix[v] == 1) || (s == -1 && fix[v] == 0))
                    satisfied = 1;
            } else {
                remaining++;
            }
        }

        if (!has_var || satisfied) continue;

        double w = 1.0 / (1 + remaining);
        if (var_sign == 1) p1 += w;
        else p0 += w;
    }

    double total = p1 + p0;
    if (total < 1e-10) return 0.0;
    return (p1 - p0) / total;
}

/* Unit propagation. Returns 1 if conflict. */
int unit_propagate(int *fix) {
    int changed = 1;
    while (changed) {
        changed = 0;
        for (int i = 0; i < m; i++) {
            int satisfied = 0;
            int free_count = 0;
            int free_var = -1, free_sign = 0;

            for (int j = 0; j < 3; j++) {
                int v = clauses[i].vars[j];
                int s = clauses[i].signs[j];
                if (fix[v] >= 0) {
                    if ((s == 1 && fix[v] == 1) || (s == -1 && fix[v] == 0))
                        satisfied = 1;
                } else {
                    free_count++;
                    free_var = v;
                    free_sign = s;
                }
            }

            if (satisfied) continue;
            if (free_count == 0) return 1; /* conflict */
            if (free_count == 1) {
                fix[free_var] = (free_sign == 1) ? 1 : 0;
                changed = 1;
            }
        }
    }
    return 0;
}

int dpll_result[MAX_N];

int dpll_solve(int *fix) {
    calls++;
    if (calls > MAX_CALLS) return 0;

    /* Copy and propagate */
    int local_fix[MAX_N];
    memcpy(local_fix, fix, n * sizeof(int));

    if (unit_propagate(local_fix)) return 0; /* conflict */

    /* Find unfixed */
    int unfixed = -1;
    double best_abs = -1;
    for (int v = 0; v < n; v++) {
        if (local_fix[v] >= 0) continue;
        double t = bit_tension(v, local_fix);
        double at = fabs(t);
        if (at > best_abs) {
            best_abs = at;
            unfixed = v;
        }
    }

    if (unfixed < 0) {
        /* All fixed — check */
        if (evaluate(local_fix) == m) {
            memcpy(dpll_result, local_fix, n * sizeof(int));
            return 1;
        }
        return 0;
    }

    double sigma = bit_tension(unfixed, local_fix);
    int first_val = (sigma >= 0) ? 1 : 0;

    /* Try first value */
    int fix1[MAX_N];
    memcpy(fix1, local_fix, n * sizeof(int));
    fix1[unfixed] = first_val;
    if (dpll_solve(fix1)) return 1;

    /* Try second value */
    int fix2[MAX_N];
    memcpy(fix2, local_fix, n * sizeof(int));
    fix2[unfixed] = 1 - first_val;
    if (dpll_solve(fix2)) return 1;

    return 0;
}

int main() {
    printf("DPLL+TENSION SCALING (C implementation)\n");
    printf("%5s | %7s | %10s | %6s | %7s | %8s | %8s\n",
           "n", "solved", "avg_calls", "eff_k", "k/logn", "k/sqrtn", "time_ms");
    printf("--------------------------------------------------------------\n");

    int test_n[] = {10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200};
    int n_tests = 13;

    for (int ti = 0; ti < n_tests; ti++) {
        int nn = test_n[ti];
        int n_inst = (nn <= 30) ? 30 : ((nn <= 75) ? 15 : ((nn <= 100) ? 10 : 5));
        int solved = 0, total = 0;
        long long total_calls = 0;
        clock_t t_start = clock();

        for (int seed = 0; seed < n_inst; seed++) {
            generate_random_3sat(nn, 4.27, seed + 30000000UL);
            total++;

            int init_fix[MAX_N];
            for (int v = 0; v < nn; v++) init_fix[v] = -1;

            calls = 0;
            int success = dpll_solve(init_fix);

            if (success) {
                solved++;
                total_calls += calls;
            }
        }

        clock_t t_end = clock();
        double total_ms = (double)(t_end - t_start) * 1000.0 / CLOCKS_PER_SEC;
        double avg_ms = total_ms / total;

        if (solved > 0) {
            double avg_calls = (double)total_calls / solved;
            double eff_k = log2(avg_calls > 0 ? avg_calls : 1);
            double logn = log2(nn);
            double sqrtn = sqrt(nn);

            printf("%5d | %3d/%2d | %10.1f | %6.1f | %7.2f | %8.2f | %8.1f\n",
                   nn, solved, total, avg_calls, eff_k,
                   eff_k / logn, eff_k / sqrtn, avg_ms);
        } else {
            printf("%5d | %3d/%2d |        N/A |    N/A |     N/A |      N/A | %8.1f\n",
                   nn, solved, total, avg_ms);
        }

        fflush(stdout);
    }

    /* Predictions */
    printf("\nBased on data, fitting k = a * f(n):\n");

    return 0;
}
