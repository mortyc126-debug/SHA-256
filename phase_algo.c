/*
 * PHASE-BIT ALGORITHMS ON CONCRETE PROBLEMS
 * ============================================
 *
 * Final piece of the phase-bit programme: apply the gate model
 * from phase_gates.c to real search problems and measure what
 * the structural speedup actually buys.
 *
 * Honest framing: phase bits do NOT give the quantum query
 * advantage of Grover or Shor.  They DO let us express search
 * problems as linear-algebra manipulations on a 2^n vector, and
 * one Walsh-Hadamard step after the oracle collapses the answer
 * into a single amplitude component.  This is a constant-factor
 * structural speedup in post-processing, not a complexity-class
 * improvement.
 *
 * Three test problems:
 *
 *   1. OR (single variable is 1)  — simplest oracle structure
 *      Show that after WHT · O_f · WHT · |0⟩, the amplitude
 *      pattern tells us whether f is non-trivial.
 *
 *   2. 3-SAT on small instances  — real search problem
 *      Encode a CNF formula as an oracle; measure the number of
 *      satisfying assignments from the |0⟩ amplitude after WHT.
 *
 *   3. Majority / "parity vs balanced" split on a random boolean
 *      function — measure how the Walsh spectrum diagnoses the
 *      structure of f without enumerating assignments directly.
 *
 * Compile: gcc -O3 -march=native -o algo phase_algo.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define N_MAX 12
#define STATES (1 << N_MAX)

typedef int PHDV[STATES];

/* Fast Walsh-Hadamard, in place, 2^n entries */
static void fwht(int *a, int n){
    int N = 1 << n;
    for(int h = 1; h < N; h <<= 1){
        for(int i = 0; i < N; i += h << 1){
            for(int j = i; j < i + h; j++){
                int x = a[j];
                int y = a[j + h];
                a[j]     = x + y;
                a[j + h] = x - y;
            }
        }
    }
}

/* ═══ EXPERIMENT 1: Constant / OR / XOR spectral signatures ═══ */
static void experiment_signatures(void){
    printf("\n═══ EXPERIMENT 1: Spectral signatures of simple functions ═══\n\n");

    int n = 5;     /* N = 32 */
    int N = 1 << n;

    /* const-0 */
    PHDV v;
    for(int i = 0; i < N; i++) v[i] = 1;
    fwht(v, n);
    printf("  f = const 0:    amp[0]=%+d  nonzero elsewhere: ", v[0]);
    int count = 0;
    for(int i = 1; i < N; i++) if(v[i]) count++;
    printf("%d\n", count);

    /* const-1: phase-flip everything */
    for(int i = 0; i < N; i++) v[i] = -1;
    fwht(v, n);
    printf("  f = const 1:    amp[0]=%+d\n", v[0]);

    /* OR (f=0 only at |0⟩): phase-flip every index except 0 */
    for(int i = 0; i < N; i++) v[i] = (i == 0) ? 1 : -1;
    fwht(v, n);
    printf("  f = OR (1 at non-0):  amp[0]=%+d, amp distribution: ", v[0]);
    int top_pos = 0, top_val = 0;
    for(int i = 0; i < N; i++) if(abs(v[i]) > abs(top_val)){top_val=v[i]; top_pos=i;}
    printf("largest=%d at index %d\n", top_val, top_pos);

    /* Parity (x_0 ⊕ x_1 ⊕ … ⊕ x_{n-1}) */
    for(int i = 0; i < N; i++) v[i] = (__builtin_popcount(i) & 1) ? -1 : 1;
    fwht(v, n);
    printf("  f = parity:     spike at amp[%d] = %+d (others zero)\n", N - 1, v[N-1]);

    /* AND (1 only at |1…1⟩) */
    for(int i = 0; i < N; i++) v[i] = (i == N - 1) ? -1 : 1;
    fwht(v, n);
    printf("  f = AND (1 at 1..1): amp[0]=%+d\n", v[0]);

    printf("\n  The Walsh spectrum IS the signature: different Boolean\n");
    printf("  functions leave different 'fingerprints' in amp-space.\n");
}

/* ═══ EXPERIMENT 2: 3-SAT structure via phase spectrum ═══ */

typedef struct {
    int v1, v2, v3;   /* variable indices (0-based) */
    int p1, p2, p3;   /* polarity: 0 = positive, 1 = negated */
} Clause;

static int eval_clause(const Clause *c, int x){
    int b1 = (x >> c->v1) & 1; if(c->p1) b1 = !b1;
    int b2 = (x >> c->v2) & 1; if(c->p2) b2 = !b2;
    int b3 = (x >> c->v3) & 1; if(c->p3) b3 = !b3;
    return b1 | b2 | b3;
}
static int eval_formula(const Clause *clauses, int m, int x){
    for(int i = 0; i < m; i++) if(!eval_clause(&clauses[i], x)) return 0;
    return 1;
}

static void random_clauses(Clause *out, int m, int n, unsigned seed){
    srand(seed);
    for(int i = 0; i < m; i++){
        int vs[3];
        /* pick 3 distinct variables */
        for(int k = 0; k < 3; k++){
            int v;
            do { v = rand() % n; int dup = 0;
                 for(int j = 0; j < k; j++) if(vs[j] == v){dup = 1; break;}
                 if(!dup) break;
            } while(1);
            vs[k] = v;
        }
        out[i].v1 = vs[0]; out[i].v2 = vs[1]; out[i].v3 = vs[2];
        out[i].p1 = rand() & 1;
        out[i].p2 = rand() & 1;
        out[i].p3 = rand() & 1;
    }
}

static void experiment_sat(void){
    printf("\n═══ EXPERIMENT 2: 3-SAT via phase-bit oracle ═══\n\n");

    int n = 8;            /* 8 variables, 2^8 = 256 assignments */
    int N = 1 << n;
    int ratios[] = {2, 3, 4, 5};

    printf("  n=%d variables, 3-SAT formulas with m clauses.\n", n);
    printf("  Oracle: phase-flip UNSAT assignments (phase_bit = −1).\n");
    printf("  Apply WHT; amp[0] tells us 2·#SAT − N.\n\n");
    printf("  m | ratio | #SAT (brute) | amp[0] | (amp[0]+N)/2 | match\n");
    printf("  --+-------+--------------+--------+--------------+------\n");

    PHDV v;
    for(int ri = 0; ri < 4; ri++){
        int m = n * ratios[ri];
        Clause *cls = malloc(m * sizeof(Clause));
        random_clauses(cls, m, n, 42 + ri);

        /* Brute force count of SAT assignments */
        int sat = 0;
        for(int x = 0; x < N; x++) if(eval_formula(cls, m, x)) sat++;

        /* Phase oracle: v[x] = +1 if SAT, −1 otherwise */
        for(int x = 0; x < N; x++) v[x] = eval_formula(cls, m, x) ? +1 : -1;
        fwht(v, n);

        /* amp[0] = Σ_x v[x] = (#SAT) − (#UNSAT) = 2·SAT − N */
        int amp0 = v[0];
        int derived = (amp0 + N) / 2;
        printf("  %2d| %4.1f | %12d | %6d | %12d | %s\n",
               m, (double)m / n, sat, amp0, derived, derived == sat ? "✓" : "✗");

        free(cls);
    }

    printf("\n  Amp[0] after WHT = number of satisfying minus unsatisfying\n");
    printf("  assignments. One WHT scan gives the exact SAT count.\n");
    printf("  (Still O(2^n) to build the oracle — no query speedup.)\n");
}

/* ═══ EXPERIMENT 3: Linearity check via spectrum concentration ═══
 *
 * Is a given boolean function LINEAR (f(x) = a · x + c for some a)?
 *
 *   Classical test: evaluate f at O(n) carefully chosen inputs,
 *                   run linear regression over GF(2).
 *   Phase-bit test: apply WHT to the phase-encoded function and
 *                   check whether the spectrum is concentrated
 *                   at a single coefficient (|F̂(s)| = N for one s,
 *                   zero elsewhere).  Total spectral mass is fixed
 *                   by Parseval so we just check the peak-to-mean
 *                   ratio.
 */
static int f_linear(int x){return __builtin_popcount(x & 0xA5) & 1;}  /* a=0xA5 */
static int f_nonlinear(int x){return ((x & 1) & ((x >> 1) & 1)) ^ ((x >> 2) & 1);}
static int f_random_mask;
static int f_random(int x){return __builtin_popcount(x & f_random_mask) & 1;}

static void experiment_linearity(void){
    printf("\n═══ EXPERIMENT 3: Linearity test via Walsh concentration ═══\n\n");

    int n = 6;
    int N = 1 << n;
    PHDV v;

    struct {const char *name; int (*f)(int);} tests[] = {
        {"linear (a=0xA5)", f_linear},
        {"nonlinear (AB+C)", f_nonlinear},
        {"random mask 0x13", f_random},
    };

    f_random_mask = 0x13;

    for(int t = 0; t < 3; t++){
        int (*f)(int) = tests[t].f;
        for(int x = 0; x < N; x++) v[x] = f(x) ? -1 : 1;
        fwht(v, n);

        int peak = 0, peak_idx = 0;
        long long sum_sq = 0;
        for(int i = 0; i < N; i++){
            if(abs(v[i]) > peak){peak = abs(v[i]); peak_idx = i;}
            sum_sq += (long long)v[i] * v[i];
        }
        double peak_frac = (double)(peak * peak) / sum_sq;
        int is_linear = (peak_frac > 0.999);

        printf("  %-18s  peak=%d at s=0x%02x, peak²/total=%.4f  → %s\n",
               tests[t].name, peak, peak_idx, peak_frac,
               is_linear ? "LINEAR" : "nonlinear");
    }
    printf("\n  Linear function ⇔ Walsh spectrum is a single delta.\n");
    printf("  One WHT decides the question without probing f further.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("PHASE-BIT ALGORITHMS ON CONCRETE PROBLEMS\n");
    printf("══════════════════════════════════════════\n");
    printf("Constant, OR, SAT counting, linearity — all via WHT + oracle.\n");

    experiment_signatures();
    experiment_sat();
    experiment_linearity();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Walsh spectrum as a 'function signature' library\n");
    printf("  2. 3-SAT counting via a single WHT after phase oracle\n");
    printf("  3. Linearity test via peak concentration in spectrum\n");
    printf("  4. Oracle building remains O(2^n) (no quantum speedup)\n");
    printf("  5. Post-oracle work is O(n 2^n) via FWHT vs O(2^n · m)\n");
    printf("     of naive bit-by-bit analysis\n");
    return 0;
}
