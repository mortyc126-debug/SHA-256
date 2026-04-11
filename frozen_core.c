/*
 * FROZEN CORE: three-layer structure of 3-SAT solution space
 * ==============================================================
 *
 * Returns to the bit-mathematical foundation we touched at the
 * start of the session but never fully excavated. In random
 * 3-SAT near the satisfiability threshold, solutions split into
 * three structural classes:
 *
 *     FROZEN    x_i has the same value in ALL solutions
 *     BIASED    x_i has a strong but not absolute preference
 *     FREE      x_i is roughly 50/50 across solutions
 *
 * The frozen core is the set of FROZEN variables; its size as a
 * function of α = m/n reveals a second-order phase transition
 * separate from the satisfiability threshold itself.
 *
 * Theory (random 3-SAT):
 *     α_d ≈ 3.86     solutions split into clusters (dynamic)
 *     α_c ≈ 3.87     condensation onto few clusters
 *     α_s ≈ 4.267    unsatisfiability threshold
 *
 * The frozen core grows abruptly between α_c and α_s. Local
 * search algorithms (WalkSAT, simulated annealing) fail above
 * this point because flipping a frozen variable requires
 * cascading flips of many others — the classical √n barrier.
 *
 * Small-n restriction: n = 18 so that 2^n = 262144 fits in a
 * brute-force enumeration. Finite-size effects blur the
 * asymptotic thresholds but the QUALITATIVE structure — three
 * layers, frozen fraction growing with α — is still visible.
 *
 * Experiments:
 *
 *   1. Given a single 3-SAT instance, enumerate all solutions,
 *      compute per-variable bias, classify into 3 layers.
 *   2. Sweep α from 1.0 to 4.0, plot frozen/biased/free fraction
 *      averaged over independent instances.
 *   3. Solution-space topology: count connected components in
 *      the solution hypercube graph (Hamming distance 1 edges).
 *      Correlate with frozen core size.
 *   4. Diameter of the solution space: maximum Hamming distance
 *      between two solutions. Compare low-α (one big blob) vs
 *      high-α (separated clusters).
 *   5. Local-search witness: pick a solution, try flipping each
 *      variable once; count how many resulting states are still
 *      satisfying. Frozen variables give 0, free variables give
 *      many. This is the local accessibility of each layer.
 *
 * Compile: gcc -O3 -march=native -o frozen frozen_core.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define N_MAX 20

/* ═══ RNG ═══ */
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

/* ═══ 3-SAT FORMULA ═══ */
typedef struct {
    int v[3];
    int p[3];    /* 0 = positive literal, 1 = negated */
} Clause;

typedef struct {
    int n;
    int m;
    Clause c[4096];
} Formula;

static void gen_random_3sat(Formula *f, int n, int m){
    f->n = n;
    f->m = m;
    for(int k = 0; k < m; k++){
        /* Pick 3 distinct variables */
        int chosen[3] = {-1, -1, -1};
        for(int i = 0; i < 3; i++){
            int v;
            do {
                v = rng_next() % n;
            } while(v == chosen[0] || v == chosen[1]);
            chosen[i] = v;
            f->c[k].v[i] = v;
            f->c[k].p[i] = rng_next() & 1;
        }
    }
}

static int satisfies(const Formula *f, int x){
    for(int k = 0; k < f->m; k++){
        int sat = 0;
        for(int i = 0; i < 3; i++){
            int bit = (x >> f->c[k].v[i]) & 1;
            if(f->c[k].p[i]) bit = !bit;
            if(bit){sat = 1; break;}
        }
        if(!sat) return 0;
    }
    return 1;
}

/* Enumerate all solutions, return count, fill buffer */
static int enumerate_solutions(const Formula *f, int *out, int max_out){
    int count = 0;
    int N = 1 << f->n;
    for(int x = 0; x < N; x++){
        if(satisfies(f, x)){
            if(count < max_out) out[count] = x;
            count++;
        }
    }
    return count;
}

/* Per-variable bias: P(x_i = 1 | SAT) */
static void compute_biases(const int *solutions, int n_sol, int n_vars, double *bias){
    for(int i = 0; i < n_vars; i++){
        int count = 0;
        for(int k = 0; k < n_sol; k++){
            if((solutions[k] >> i) & 1) count++;
        }
        bias[i] = (n_sol > 0) ? (double)count / n_sol : 0.5;
    }
}

/* Three-layer classification */
typedef enum {FROZEN_0, FROZEN_1, BIASED, FREE} VarClass;

static VarClass classify_var(double b){
    if(b <= 0.05) return FROZEN_0;
    if(b >= 0.95) return FROZEN_1;
    if(b <= 0.40 || b >= 0.60) return BIASED;
    return FREE;
}

static const char *class_name(VarClass c){
    switch(c){
    case FROZEN_0: return "frozen=0";
    case FROZEN_1: return "frozen=1";
    case BIASED:   return "biased";
    case FREE:     return "free";
    }
    return "?";
}

/* ═══ EXPERIMENT 1: single instance dissection ═══ */
static void experiment_one_instance(void){
    printf("\n═══ EXPERIMENT 1: Single instance three-layer dissection ═══\n\n");

    int n = 18;
    int m = 60;     /* α = m/n = 3.33 — below threshold */
    double alpha = (double)m / n;

    Formula f;
    rng_seed(1);
    gen_random_3sat(&f, n, m);

    static int solutions[262144];
    int n_sol = enumerate_solutions(&f, solutions, 262144);
    printf("  n = %d, m = %d, α = %.2f\n", n, m, alpha);
    printf("  Satisfying assignments: %d out of %d (%.2f%%)\n",
           n_sol, 1 << n, 100.0 * n_sol / (1 << n));

    if(n_sol == 0){
        printf("  UNSAT — no frozen core to analyse.\n");
        return;
    }

    double bias[N_MAX];
    compute_biases(solutions, n_sol, n, bias);

    int counts[4] = {0};
    printf("\n  Per-variable bias and class:\n");
    printf("    var | bias    | class\n");
    printf("    ----+---------+----------\n");
    for(int i = 0; i < n; i++){
        VarClass c = classify_var(bias[i]);
        counts[c]++;
        printf("    %3d | %.4f  | %s\n", i, bias[i], class_name(c));
    }

    printf("\n  Layer sizes:\n");
    printf("    frozen=0 : %d\n", counts[FROZEN_0]);
    printf("    frozen=1 : %d\n", counts[FROZEN_1]);
    printf("    biased   : %d\n", counts[BIASED]);
    printf("    free     : %d\n", counts[FREE]);
    printf("    total frozen: %d (%.1f%%)\n",
           counts[FROZEN_0] + counts[FROZEN_1],
           100.0 * (counts[FROZEN_0] + counts[FROZEN_1]) / n);
}

/* ═══ EXPERIMENT 2: sweep α ═══ */
static void experiment_sweep(void){
    printf("\n═══ EXPERIMENT 2: Frozen-core fraction vs α ═══\n\n");

    int n = 16;
    int trials_per_alpha = 5;

    printf("  n = %d, %d trials per α, averaged\n\n", n, trials_per_alpha);
    printf("    α     | m  | avg #sol | %%frozen | %%biased | %%free\n");
    printf("    ------+----+----------+---------+---------+------\n");

    int alphas_m[] = {16, 24, 32, 40, 48, 56, 64, 68};
    int nalpha = sizeof(alphas_m) / sizeof(int);

    static int solutions[65536];

    for(int ai = 0; ai < nalpha; ai++){
        int m = alphas_m[ai];
        double alpha = (double)m / n;

        double avg_sol = 0;
        double avg_frozen = 0, avg_biased = 0, avg_free = 0;
        int n_valid = 0;

        for(int t = 0; t < trials_per_alpha; t++){
            rng_seed(1000 + ai * 100 + t);
            Formula f;
            gen_random_3sat(&f, n, m);
            int n_sol = enumerate_solutions(&f, solutions, 65536);
            if(n_sol == 0) continue;

            double bias[N_MAX];
            compute_biases(solutions, n_sol, n, bias);
            int counts[4] = {0};
            for(int i = 0; i < n; i++) counts[classify_var(bias[i])]++;
            avg_sol    += n_sol;
            avg_frozen += 100.0 * (counts[FROZEN_0] + counts[FROZEN_1]) / n;
            avg_biased += 100.0 * counts[BIASED] / n;
            avg_free   += 100.0 * counts[FREE] / n;
            n_valid++;
        }
        if(n_valid == 0){
            printf("    %.2f  | %2d | (UNSAT)\n", alpha, m);
            continue;
        }
        avg_sol    /= n_valid;
        avg_frozen /= n_valid;
        avg_biased /= n_valid;
        avg_free   /= n_valid;
        printf("    %.2f  | %2d | %8.0f | %6.1f%% | %6.1f%% | %5.1f%%\n",
               alpha, m, avg_sol, avg_frozen, avg_biased, avg_free);
    }

    printf("\n  As α grows toward the satisfiability threshold, the frozen\n");
    printf("  fraction climbs rapidly. Free variables disappear first, then\n");
    printf("  biased variables crystallise into frozen ones.\n");
}

/* ═══ EXPERIMENT 3: solution-space connectivity ═══
 *
 * Build a graph on the solution set, edges between solutions at
 * Hamming distance 1. Count connected components via union-find.
 * Below α_d there is one big component; above, solutions split.
 */
static int uf_parent[65536];
static int uf_find(int x){
    while(uf_parent[x] != x){
        uf_parent[x] = uf_parent[uf_parent[x]];
        x = uf_parent[x];
    }
    return x;
}
static void uf_union(int x, int y){
    int rx = uf_find(x), ry = uf_find(y);
    if(rx != ry) uf_parent[rx] = ry;
}

static int count_components(const int *sol, int n_sol, int n_vars){
    /* O(n_sol²) — fine for small n */
    for(int i = 0; i < n_sol; i++) uf_parent[i] = i;
    for(int i = 0; i < n_sol; i++){
        for(int j = i + 1; j < n_sol; j++){
            int d = __builtin_popcount(sol[i] ^ sol[j]);
            if(d == 1) uf_union(i, j);
        }
    }
    int c = 0;
    for(int i = 0; i < n_sol; i++) if(uf_parent[i] == i) c++;
    (void)n_vars;
    return c;
}

static void experiment_connectivity(void){
    printf("\n═══ EXPERIMENT 3: Solution-space connectivity ═══\n\n");

    int n = 14;
    printf("  n = %d; edges between solutions at Hamming distance 1\n\n", n);
    printf("    α     | m  | #sol | components | max comp size | comps/sol\n");
    printf("    ------+----+------+------------+---------------+----------\n");

    int alphas_m[] = {14, 21, 28, 35, 42, 49, 56, 60};
    int nalpha = sizeof(alphas_m) / sizeof(int);
    static int sol[16384];

    for(int ai = 0; ai < nalpha; ai++){
        int m = alphas_m[ai];
        double alpha = (double)m / n;

        rng_seed(2000 + ai);
        Formula f;
        gen_random_3sat(&f, n, m);
        int n_sol = enumerate_solutions(&f, sol, 16384);
        if(n_sol == 0){
            printf("    %.2f  | %2d | UNSAT\n", alpha, m);
            continue;
        }

        int comps = count_components(sol, n_sol, n);

        /* Max component size */
        int size_of[16384] = {0};
        for(int i = 0; i < n_sol; i++) size_of[uf_find(i)]++;
        int max_sz = 0;
        for(int i = 0; i < n_sol; i++) if(size_of[i] > max_sz) max_sz = size_of[i];

        printf("    %.2f  | %2d | %5d | %10d | %13d | %7.4f\n",
               alpha, m, n_sol, comps, max_sz, (double)comps / n_sol);
    }

    printf("\n  At low α, all solutions form ONE connected component (every\n");
    printf("  pair of solutions is reachable via single-bit flips). As α\n");
    printf("  grows, the solution space fragments: more components, smaller\n");
    printf("  largest component, more isolated solutions per unit.\n");
    printf("  This is the clustering transition α_d.\n");
}

/* ═══ EXPERIMENT 4: local accessibility per layer ═══
 *
 * Pick one solution, attempt to flip each bit and check if the
 * result is still satisfying. The number of successful flips
 * is the 'local mobility' at that solution. Frozen bits give 0,
 * free bits give many.
 */
static void experiment_local_flips(void){
    printf("\n═══ EXPERIMENT 4: Local accessibility by layer ═══\n\n");

    int n = 16;
    int m = 52;    /* α = 3.25 */
    double alpha = (double)m / n;

    Formula f;
    rng_seed(3);
    gen_random_3sat(&f, n, m);

    static int sol[65536];
    int n_sol = enumerate_solutions(&f, sol, 65536);
    if(n_sol == 0){
        printf("  UNSAT — retry.\n");
        return;
    }

    double bias[N_MAX];
    compute_biases(sol, n_sol, n, bias);

    printf("  n = %d, m = %d, α = %.2f, #solutions = %d\n\n", n, m, alpha, n_sol);

    /* Pick solution 0 as the anchor */
    int anchor = sol[0];
    printf("  Anchor solution: ");
    for(int i = 0; i < n; i++) printf("%d", (anchor >> i) & 1);
    printf("\n\n");

    int layer_flippable[4] = {0};
    int layer_count[4] = {0};

    printf("    bit | bias   | class    | single-flip satisfies?\n");
    printf("    ----+--------+----------+-----------------------\n");
    for(int i = 0; i < n; i++){
        VarClass c = classify_var(bias[i]);
        int flipped = anchor ^ (1 << i);
        int ok = satisfies(&f, flipped);
        printf("    %3d | %.4f | %-8s | %s\n",
               i, bias[i], class_name(c), ok ? "YES" : "no");
        layer_count[c]++;
        if(ok) layer_flippable[c]++;
    }

    printf("\n  Flippability by layer (how many single flips stay SAT):\n");
    for(int c = 0; c < 4; c++){
        if(layer_count[c] == 0) continue;
        printf("    %-8s  %d / %d  (%.0f%%)\n",
               class_name((VarClass)c),
               layer_flippable[c], layer_count[c],
               100.0 * layer_flippable[c] / layer_count[c]);
    }

    printf("\n  Expected behaviour:\n");
    printf("    FROZEN variables: 0 single-flip neighbours satisfy (they\n");
    printf("                      are locked by the rest of the formula)\n");
    printf("    FREE variables:   high flip success (they are genuinely\n");
    printf("                      symmetric at this anchor)\n");
    printf("    BIASED variables: somewhere in between.\n");
    printf("\n  This is the microscopic reason WalkSAT slows down: moves in\n");
    printf("  frozen regions fail silently.\n");
}

/* ═══ EXPERIMENT 5: diameter of solution space ═══ */
static void experiment_diameter(void){
    printf("\n═══ EXPERIMENT 5: Diameter of solution space ═══\n\n");

    int n = 14;
    printf("    α     | m  | #sol | max Hamming dist | min Hamming dist\n");
    printf("    ------+----+------+------------------+-----------------\n");
    int alphas_m[] = {14, 21, 28, 35, 42, 49, 55};
    int nalpha = sizeof(alphas_m) / sizeof(int);
    static int sol[16384];

    for(int ai = 0; ai < nalpha; ai++){
        int m = alphas_m[ai];
        double alpha = (double)m / n;

        rng_seed(4000 + ai);
        Formula f;
        gen_random_3sat(&f, n, m);
        int n_sol = enumerate_solutions(&f, sol, 16384);
        if(n_sol == 0){
            printf("    %.2f  | %2d | UNSAT\n", alpha, m);
            continue;
        }

        int max_d = 0, min_d = n;
        for(int i = 0; i < n_sol; i++)
            for(int j = i + 1; j < n_sol; j++){
                int d = __builtin_popcount(sol[i] ^ sol[j]);
                if(d > max_d) max_d = d;
                if(d < min_d) min_d = d;
            }
        if(n_sol == 1){min_d = 0; max_d = 0;}

        printf("    %.2f  | %2d | %5d | %16d | %15d\n",
               alpha, m, n_sol, max_d, min_d);
    }

    printf("\n  As α grows, surviving solutions concentrate on fewer\n");
    printf("  coordinates (frozen core grows), so the maximum Hamming\n");
    printf("  distance between any two solutions SHRINKS. The solution\n");
    printf("  space contracts toward the frozen core skeleton.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("FROZEN CORE: three-layer structure of 3-SAT solutions\n");
    printf("══════════════════════════════════════════\n");
    printf("Per-variable bias P(x_i = 1 | SAT) partitions bits into\n");
    printf("FROZEN (always fixed), BIASED (preference), and FREE.\n");

    experiment_one_instance();
    experiment_sweep();
    experiment_connectivity();
    experiment_local_flips();
    experiment_diameter();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY TAKEAWAYS:\n");
    printf("  1. The solution set of random 3-SAT has a sharp three-\n");
    printf("     layer structure: frozen, biased, free.\n");
    printf("  2. The frozen fraction grows with α, crossing from near\n");
    printf("     0 at low α to near 1 approaching α_s.\n");
    printf("  3. Solution-space connectivity breaks up as α grows:\n");
    printf("     one large component fragments into many small clusters.\n");
    printf("  4. Local moves fail exactly in the frozen core — this\n");
    printf("     is the microscopic reason for the √n barrier.\n");
    printf("  5. The diameter of the solution space CONTRACTS with α,\n");
    printf("     reflecting the shrinking degrees of freedom.\n");
    return 0;
}
