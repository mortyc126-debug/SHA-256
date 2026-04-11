/*
 * COST BITS: thermodynamic / energy accounting as primitive
 * ============================================================
 *
 * Twelfth axis in the bit taxonomy (first of three new axes
 * spotted after the methodology consolidation).  Each bit
 * carries a WEIGHT indicating the energy cost to be in each
 * state.  Pairs of bits carry COUPLINGS indicating the cost of
 * their joint configurations.
 *
 * Inspired by:
 *   - Ising model (Lenz 1920, Ising 1924)
 *   - Landauer's principle (1961) — erasure costs kT·ln 2
 *   - Spin glasses (Edwards-Anderson 1975)
 *   - Weighted MAX-SAT
 *   - Lucas (2014): nearly every NP-hard problem maps to an
 *     Ising ground state with polynomial overhead
 *
 * The primitive is a configuration x ∈ {0,1}^n with an energy
 * function
 *
 *     E(x) = Σ_i h_i(x_i) + Σ_{i<j} J_ij · f_ij(x_i, x_j)
 *
 * where h_i are local fields (per-bit biases) and J_ij are
 * pairwise couplings. Computation = finding arg min E(x).
 *
 * Why this is a new axis
 * ----------------------
 * None of the eleven previous axes carries energy as part of
 * the primitive:
 *   - binary / phase / prob / selfref / church / modal / relat
 *     have no notion of "cost to flip"
 *   - linear counts DISCRETE uses, not continuous energy
 *   - reversible GUARANTEES no information loss but does not
 *     account for thermodynamic cost (Landauer is a theorem
 *     applied externally, not a primitive)
 *   - stream tracks time but not energy dissipation
 *   - braid has topological invariants but no energy metric
 *
 * Cost bits add the missing axis: a numerical scalar per
 * operation that reflects thermodynamic / economic reality.
 *
 * Experiments:
 *   1. Single-bit ground state and flip cost
 *   2. Ising chain with uniform ferromagnetic coupling
 *   3. Frustrated triangle (antiferromagnetic) — residual energy
 *   4. Weighted MAX-SAT encoded as ground-state problem
 *   5. Landauer accounting: reversible vs irreversible circuit
 *      costs for the same Boolean computation
 *
 * Compile: gcc -O3 -march=native -o cost cost_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define MAX_N 16

/* ═══ COST SYSTEM ═══
 *
 * Stored as local fields h[i][v] (v = 0 or 1) and pairwise
 * couplings J[i][j][a][b] (a, b ∈ {0,1}). Energy is integer for
 * clarity of bookkeeping.
 */

typedef struct {
    int n;
    long long h[MAX_N][2];
    long long J[MAX_N][MAX_N][2][2];
} CostSystem;

static void cs_init(CostSystem *cs, int n){
    cs->n = n;
    memset(cs->h, 0, sizeof(cs->h));
    memset(cs->J, 0, sizeof(cs->J));
}
static void cs_local(CostSystem *cs, int i, long long h0, long long h1){
    cs->h[i][0] = h0;
    cs->h[i][1] = h1;
}
static void cs_couple(CostSystem *cs, int i, int j,
                       long long c00, long long c01, long long c10, long long c11){
    if(i > j){int t = i; i = j; j = t;
        long long t1 = c01; c01 = c10; c10 = t1;}
    cs->J[i][j][0][0] = c00;
    cs->J[i][j][0][1] = c01;
    cs->J[i][j][1][0] = c10;
    cs->J[i][j][1][1] = c11;
}

static long long cs_energy(const CostSystem *cs, int x){
    long long e = 0;
    for(int i = 0; i < cs->n; i++){
        int xi = (x >> i) & 1;
        e += cs->h[i][xi];
    }
    for(int i = 0; i < cs->n; i++){
        for(int j = i + 1; j < cs->n; j++){
            int xi = (x >> i) & 1;
            int xj = (x >> j) & 1;
            e += cs->J[i][j][xi][xj];
        }
    }
    return e;
}

/* Exhaustive ground-state search (ok up to n = 20 or so). */
static int cs_ground_state(const CostSystem *cs, long long *e_out){
    int best_x = 0;
    long long best_e = cs_energy(cs, 0);
    int N = 1 << cs->n;
    for(int x = 1; x < N; x++){
        long long e = cs_energy(cs, x);
        if(e < best_e){best_e = e; best_x = x;}
    }
    if(e_out) *e_out = best_e;
    return best_x;
}

static void print_bits(const char *prefix, int x, int n){
    printf("%s", prefix);
    for(int i = 0; i < n; i++) printf("%d", (x >> i) & 1);
}

/* ═══ EXPERIMENT 1: Single-bit weights ═══ */
static void experiment_single_bit(void){
    printf("\n═══ EXPERIMENT 1: Single-bit cost and ground state ═══\n\n");

    CostSystem cs;
    cs_init(&cs, 1);
    cs_local(&cs, 0, /*h_0 =*/ 0, /*h_1 =*/ 5);

    printf("  Local field: h_0 = %lld, h_1 = %lld\n",
           cs.h[0][0], cs.h[0][1]);
    printf("  E(0) = %lld\n", cs_energy(&cs, 0));
    printf("  E(1) = %lld\n", cs_energy(&cs, 1));

    long long ge;
    int g = cs_ground_state(&cs, &ge);
    printf("  Ground state: value = %d, energy = %lld\n", g, ge);
    printf("  Cost to flip from ground: %lld\n",
           cs_energy(&cs, !g) - ge);

    printf("\n  A cost bit's 'value' is no longer arbitrary — the\n");
    printf("  primitive has a preferred configuration (the ground\n");
    printf("  state) and a positive energy cost to leave it.\n");
}

/* ═══ EXPERIMENT 2: Ferromagnetic Ising chain ═══ */
static void experiment_ising_chain(void){
    printf("\n═══ EXPERIMENT 2: Ferromagnetic Ising chain ═══\n\n");

    int n = 10;
    CostSystem cs;
    cs_init(&cs, n);

    /* Ferromagnetic coupling: agreement costs 0, disagreement costs 1 */
    for(int i = 0; i < n - 1; i++){
        cs_couple(&cs, i, i + 1, /*00*/0, /*01*/1, /*10*/1, /*11*/0);
    }

    long long ge;
    int g = cs_ground_state(&cs, &ge);
    printf("  n = %d bits, ferromagnetic chain (disagreement cost 1)\n", n);
    print_bits("  Ground state: ", g, n);
    printf("  Energy: %lld\n", ge);

    /* Show some higher-energy states */
    printf("\n  Compare alternating state 0101010101:\n");
    int alt = 0;
    for(int i = 0; i < n; i++) if(i & 1) alt |= (1 << i);
    print_bits("    x = ", alt, n);
    printf("  Energy: %lld\n", cs_energy(&cs, alt));

    printf("\n  The ferromagnetic ground state is all-aligned; the\n");
    printf("  anti-ferromagnetic 'mistake' costs one unit per edge.\n");
}

/* ═══ EXPERIMENT 3: Frustrated triangle ═══ */
static void experiment_frustration(void){
    printf("\n═══ EXPERIMENT 3: Frustrated triangle (antiferromagnetic) ═══\n\n");

    CostSystem cs;
    cs_init(&cs, 3);

    /* Antiferromagnetic: agreement costs 1, disagreement costs 0 */
    for(int i = 0; i < 3; i++){
        for(int j = i + 1; j < 3; j++){
            cs_couple(&cs, i, j, /*00*/1, /*01*/0, /*10*/0, /*11*/1);
        }
    }

    printf("  3 bits, all pairs antiferromagnetic (agreement cost 1)\n");
    printf("  Enumerating all 8 configurations:\n\n");
    printf("  config | energy\n");
    printf("  -------+-------\n");
    for(int x = 0; x < 8; x++){
        print_bits("  ", x, 3);
        printf("    | %lld\n", cs_energy(&cs, x));
    }

    long long ge;
    int g = cs_ground_state(&cs, &ge);
    printf("\n  Minimum energy = %lld (NOT 0)\n", ge);
    printf("  Any 3-bit assignment has at least one agreeing pair,\n");
    printf("  so the minimum cost is 1 — this is FRUSTRATION:\n");
    printf("  no configuration can satisfy all constraints at once.\n");
    (void)g;
}

/* ═══ EXPERIMENT 4: Weighted MAX-SAT as ground state ═══ */
static void experiment_maxsat(void){
    printf("\n═══ EXPERIMENT 4: Weighted MAX-SAT encoded in a cost system ═══\n\n");

    /* Small 3-SAT formula with 4 variables and 6 weighted clauses.
     * Each violated clause contributes its weight to the energy.
     * Ground state = optimal MAX-SAT assignment.  */

    /* Clauses (v1, v2, v3 with polarity, weight):
     *   (x0 ∨ x1 ∨ x2), w=3
     *   (¬x0 ∨ x1 ∨ x3), w=2
     *   (x0 ∨ ¬x1 ∨ ¬x3), w=4
     *   (¬x0 ∨ ¬x2 ∨ x3), w=1
     *   (x1 ∨ x2 ∨ ¬x3), w=5
     *   (¬x1 ∨ ¬x2 ∨ x3), w=3
     */

    struct Clause {
        int v[3];
        int p[3];   /* 0 = positive, 1 = negated */
        int w;
    } clauses[] = {
        {{0,1,2}, {0,0,0}, 3},
        {{0,1,3}, {1,0,0}, 2},
        {{0,1,3}, {0,1,1}, 4},
        {{0,2,3}, {1,1,0}, 1},
        {{1,2,3}, {0,0,1}, 5},
        {{1,2,3}, {1,1,0}, 3},
    };
    int M = 6;

    int total_weight = 0;
    for(int k = 0; k < M; k++) total_weight += clauses[k].w;

    /* Brute-force ground state search */
    int n = 4;
    int best_x = 0;
    int best_cost = total_weight + 1;
    for(int x = 0; x < (1 << n); x++){
        int cost = 0;
        for(int k = 0; k < M; k++){
            int sat = 0;
            for(int v = 0; v < 3; v++){
                int bit = (x >> clauses[k].v[v]) & 1;
                if(clauses[k].p[v]) bit = !bit;
                if(bit){sat = 1; break;}
            }
            if(!sat) cost += clauses[k].w;
        }
        if(cost < best_cost){best_cost = cost; best_x = x;}
    }

    printf("  4 variables, 6 clauses, total weight = %d\n", total_weight);
    print_bits("  Optimal assignment: ", best_x, n);
    printf("\n  Violated weight: %d / %d\n", best_cost, total_weight);
    printf("  Satisfied weight: %d\n", total_weight - best_cost);

    /* Verify which clauses are satisfied */
    printf("\n  Per-clause status:\n");
    for(int k = 0; k < M; k++){
        int sat = 0;
        for(int v = 0; v < 3; v++){
            int bit = (best_x >> clauses[k].v[v]) & 1;
            if(clauses[k].p[v]) bit = !bit;
            if(bit){sat = 1; break;}
        }
        printf("    clause %d (w=%d): %s\n", k, clauses[k].w,
               sat ? "SAT" : "UNSAT");
    }

    printf("\n  Weighted MAX-SAT becomes pure ground-state minimisation\n");
    printf("  of a cost system. No SAT solver needed — just enumerate\n");
    printf("  the energy landscape and pick the minimum.\n");
}

/* ═══ EXPERIMENT 5: Landauer accounting ═══
 *
 * Compare the thermodynamic cost of computing f(a, b) = a AND b
 * in two ways:
 *
 *   irreversible:  output bit c, then the 2 inputs a, b are
 *                   discarded  →  2 bit erasures  →  2·kT·ln 2
 *
 *   reversible:    Toffoli(a, b, 0) → (a, b, a∧b), all inputs
 *                   preserved, ancilla clean at the end
 *                   →  0 bit erasures (Bennett 1973)
 *
 * We don't use real units; we count BIT ERASURES as the cost
 * proxy. The point is the ratio, not the absolute scale.
 */
static void experiment_landauer(void){
    printf("\n═══ EXPERIMENT 5: Landauer bit-erasure accounting ═══\n\n");

    printf("  Compute f(a, b) = a AND b on all 4 inputs.\n\n");

    /* Irreversible AND: keeps c = a AND b, discards a and b. */
    printf("  IRREVERSIBLE schema: inputs discarded after producing c.\n");
    printf("    a b | c | bits erased this step\n");
    printf("    ----+---+---------------------\n");
    int total_irrev = 0;
    for(int a = 0; a < 2; a++)
        for(int b = 0; b < 2; b++){
            int c = a & b;
            int erased = 2;  /* a and b thrown away */
            total_irrev += erased;
            printf("    %d %d | %d |       %d\n", a, b, c, erased);
        }
    printf("    TOTAL bit erasures: %d\n", total_irrev);
    printf("    Landauer cost: %d · kT·ln 2\n\n", total_irrev);

    /* Reversible Toffoli: keeps (a, b, a∧b) */
    printf("  REVERSIBLE schema (Toffoli): keep (a, b, a∧b).\n");
    printf("    a b | output triple\n");
    printf("    ----+--------------\n");
    int total_rev = 0;
    for(int a = 0; a < 2; a++)
        for(int b = 0; b < 2; b++){
            printf("    %d %d | (%d, %d, %d)\n", a, b, a, b, a & b);
        }
    printf("    TOTAL bit erasures: %d\n", total_rev);
    printf("    Landauer cost: 0 · kT·ln 2 (adiabatic limit)\n\n");

    printf("  The cost-bit primitive makes this accounting EXPLICIT.\n");
    printf("  Every operation declares how many bits it erases; the\n");
    printf("  total is a first-class invariant of the computation,\n");
    printf("  not an afterthought.\n");
    printf("\n  Ratio irreversible / reversible = %d / 0 (∞).\n",
           total_irrev);
    printf("  Reversible circuits are STRICTLY cheaper in the\n");
    printf("  thermodynamic sense, even though they compute the\n");
    printf("  same function. This is Bennett-Landauer reality.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("COST BITS: thermodynamic accounting as primitive\n");
    printf("══════════════════════════════════════════\n");
    printf("Each bit carries a weight. Pairs carry couplings.\n");
    printf("Computation = finding arg min E(x).\n");

    experiment_single_bit();
    experiment_ising_chain();
    experiment_frustration();
    experiment_maxsat();
    experiment_landauer();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Cost bit = value plus state-dependent weight\n");
    printf("  2. Coupled cost systems form an Ising-like energy\n");
    printf("     function whose ground state IS the computation\n");
    printf("  3. Ferromagnetic chains have unique aligned ground\n");
    printf("  4. Antiferromagnetic triangles exhibit FRUSTRATION:\n");
    printf("     no configuration has energy 0\n");
    printf("  5. Weighted MAX-SAT becomes direct ground-state search\n");
    printf("  6. Landauer accounting is first-class: every operation\n");
    printf("     declares how many bits it erases\n");
    printf("\n  TWELFTH axis: ENERGY / THERMODYNAMIC ACCOUNTING.\n");
    printf("  Distinct from linear (discrete budget) and reversible\n");
    printf("  (information conservation). Cost bits give a continuous\n");
    printf("  numerical weight to every state and operation.\n");
    return 0;
}
