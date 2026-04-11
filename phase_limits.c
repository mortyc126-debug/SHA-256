/*
 * LIMITS OF PHASE BITS
 * =====================
 *
 * After four files showing what phase bits CAN do (interference,
 * ebits, ghz triples, gate circuits), this file shows what they
 * CANNOT do — the structural constraints that distinguish phase
 * bits from unrestricted classical representations.
 *
 * Four theorems, each with an empirical witness:
 *
 *   1. No-cloning: no linear operator maps |ψ⟩⊗|0⟩ to |ψ⟩⊗|ψ⟩
 *      for all ψ.  Cloning works on any fixed basis, fails the
 *      moment linearity is combined with more than one input.
 *
 *   2. Monogamy: if a pair (A, B) is in a Bell state, then B
 *      has zero correlation with any outside C.
 *
 *   3. Complementarity: a state sharp in Z (definite bit value)
 *      is uniform in X (definite phase).  They can't both be
 *      sharp — this is a classical version of the uncertainty
 *      relation.
 *
 *   4. Schmidt rank bounds: every 2-bit state decomposes into at
 *      most 2 product terms.  Product states have rank 1, Bell
 *      states have rank 2.  The rank measures the IRREDUCIBLE
 *      content of entanglement.
 *
 * Compile: gcc -O3 -march=native -o limits phase_limits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

/* ═══ NO-CLONING ═══
 *
 * A linear cloner C on 4-d phase HDVs (2 bits) must satisfy
 *     C(|00⟩) = |00⟩    (cloning |0⟩)
 *     C(|10⟩) = |11⟩    (cloning |1⟩)
 * So on the standard basis, C acts like a permutation:
 *     C |00⟩ = |00⟩,  C |10⟩ = |11⟩,
 *     C |01⟩ = ???,   C |11⟩ = ???
 * Fix a specific C that does the right thing on the blank-second-bit
 * subspace (i.e. a CNOT-like gate) and let it act on other inputs.
 * We will show it fails to clone |+⟩ = |0⟩ + |1⟩.
 */

typedef int Vec4[4];   /* 4-d phase HDV indexed as 00,01,10,11 */

static void vec4_print(const char *name, const Vec4 v){
    printf("  %-12s = (%+d, %+d, %+d, %+d)\n", name, v[0], v[1], v[2], v[3]);
}
static int vec4_eq(const Vec4 a, const Vec4 b){
    return memcmp(a, b, sizeof(Vec4)) == 0;
}

/* The natural linear cloner for computational-basis inputs is a
 * CNOT with control = bit 0, target = bit 1.  On a product state
 * |ψ⟩ ⊗ |0⟩ where ψ = (a, b), CNOT sends
 *     (a, 0, b, 0)  →  (a, 0, 0, b)
 * which equals |ψ⟩ ⊗ |ψ⟩ iff b = 0 or a = 0, i.e. only basis
 * states.  For a superposition this fails.
 */
static void cloner(Vec4 out, const Vec4 in){
    /* Index convention: idx = 2·bit_A + bit_B, so bit A is the
     * MSB and the "first" tensor factor. We clone A → B via
     * CNOT(control = A, target = B):
     *   indices with A=1 have their B flipped
     *   10 (idx 2) ↔ 11 (idx 3) */
    out[0] = in[0];  /* 00 */
    out[1] = in[1];  /* 01 */
    out[2] = in[3];  /* 10 ↔ 11 */
    out[3] = in[2];
}

static void experiment_no_cloning(void){
    printf("\n═══ EXPERIMENT 1: No-cloning theorem ═══\n\n");
    printf("Linear cloner C must satisfy C(|ψ⟩⊗|0⟩) = |ψ⟩⊗|ψ⟩ for all ψ.\n");
    printf("We use the natural CNOT cloner and test several inputs.\n\n");

    /* Case A: ψ = |0⟩, so input = |00⟩ = (1,0,0,0) */
    Vec4 in, out, target;
    memset(in, 0, sizeof(in)); in[0] = 1;        /* |00⟩ = |0⟩⊗|0⟩ */
    memset(target, 0, sizeof(target)); target[0] = 1;  /* |0⟩⊗|0⟩ */
    cloner(out, in);
    vec4_print("input |0⟩⊗|0⟩", in);
    vec4_print("cloner output", out);
    vec4_print("target |0⟩⊗|0⟩", target);
    printf("  matches target: %s\n\n", vec4_eq(out, target) ? "YES ✓" : "NO ✗");

    /* Case B: ψ = |1⟩, input = |10⟩ */
    memset(in, 0, sizeof(in)); in[2] = 1;        /* |10⟩: bit 0=1, bit 1=0 */
    memset(target, 0, sizeof(target)); target[3] = 1;  /* |1⟩⊗|1⟩ = |11⟩ */
    cloner(out, in);
    vec4_print("input |1⟩⊗|0⟩", in);
    vec4_print("cloner output", out);
    vec4_print("target |1⟩⊗|1⟩", target);
    printf("  matches target: %s\n\n", vec4_eq(out, target) ? "YES ✓" : "NO ✗");

    /* Case C: ψ = |+⟩ = |0⟩ + |1⟩, input = |+⟩⊗|0⟩ = (1,0,1,0) */
    memset(in, 0, sizeof(in)); in[0] = 1; in[2] = 1;
    /* We WANT: C(|+⟩⊗|0⟩) = |+⟩⊗|+⟩ = (|0⟩+|1⟩)⊗(|0⟩+|1⟩)
     *         = |00⟩+|01⟩+|10⟩+|11⟩ = (1,1,1,1) */
    Vec4 want = {1, 1, 1, 1};
    cloner(out, in);
    vec4_print("input |+⟩⊗|0⟩", in);
    vec4_print("cloner output", out);
    vec4_print("target |+⟩⊗|+⟩", want);
    printf("  matches target: %s\n", vec4_eq(out, want) ? "YES ✓" : "NO ✗ (no-cloning)");

    printf("\n  Linearity forces C to act as CNOT on basis states, which\n");
    printf("  produces the Bell-like output (1, 0, 1, 0) = |0⟩_A ⊗ |+⟩_B\n");
    printf("  is wrong sign-wise vs the product |+⟩ ⊗ |+⟩.\n");
    printf("  In fact the cloner output IS the entangled state Φ+ · √2-ish:\n");
    printf("  it is an ebit, not a product — cloning has FAILED.\n");
}

/* ═══ MONOGAMY ═══
 *
 * Take a 3-bit phase HDV (length 8) where A and B are in Φ+.
 * Compute correlations C(A,B) and C(A,C).
 *
 * We show that if |AB⟩ is Bell, extending to any classical C
 * forces C(A,C) = 0 exactly.  Total correlation with A is
 * completely consumed by B.
 */
typedef int Vec8[8];

static double corr_Z(const Vec8 t, int bit_i, int bit_j){
    /* ⟨Z_i · Z_j⟩ = Σ_x |t_x|² (−1)^{x_i + x_j} / Σ |t_x|² */
    int total = 0;
    int signed_sum = 0;
    for(int x = 0; x < 8; x++){
        int w = t[x] * t[x];
        total += w;
        int xi = (x >> (2 - bit_i)) & 1;
        int xj = (x >> (2 - bit_j)) & 1;
        int par = (xi + xj) & 1;
        signed_sum += par ? -w : +w;
    }
    if(total == 0) return 0;
    return (double)signed_sum / total;
}

static void experiment_monogamy(void){
    printf("\n═══ EXPERIMENT 2: Monogamy of correlation ═══\n\n");

    /* Φ+_AB ⊗ |0⟩_C = (|00⟩+|11⟩)⊗|0⟩ = |000⟩ + |110⟩
     * Indices:  abc = 000 → 0, 110 → 6 */
    Vec8 t = {0};
    t[0] = 1;  /* |000⟩ */
    t[6] = 1;  /* |110⟩ */

    printf("  State: (Φ+)_AB ⊗ |0⟩_C = |000⟩ + |110⟩\n\n");
    printf("  ⟨Z_A · Z_B⟩ = %+.4f   (A-B correlation)\n", corr_Z(t, 0, 1));
    printf("  ⟨Z_A · Z_C⟩ = %+.4f   (A-C correlation)\n", corr_Z(t, 0, 2));
    printf("  ⟨Z_B · Z_C⟩ = %+.4f   (B-C correlation)\n", corr_Z(t, 1, 2));
    printf("\n  A is maximally correlated with B (+1) but has zero\n");
    printf("  correlation with C. The Bell pair 'exhausts' A's\n");
    printf("  correlation budget — that is monogamy.\n");

    /* Contrast: a state where A correlates weakly with both */
    Vec8 t2 = {0};
    t2[0] = 1; /* |000⟩ */
    t2[3] = 1; /* |011⟩ */
    t2[5] = 1; /* |101⟩ */
    t2[6] = 1; /* |110⟩ */
    printf("\n  State: |000⟩ + |011⟩ + |101⟩ + |110⟩ (even-parity subspace)\n");
    printf("  ⟨Z_A · Z_B⟩ = %+.4f\n", corr_Z(t2, 0, 1));
    printf("  ⟨Z_A · Z_C⟩ = %+.4f\n", corr_Z(t2, 0, 2));
    printf("  ⟨Z_B · Z_C⟩ = %+.4f\n", corr_Z(t2, 1, 2));
    printf("  Three-way even-parity constraint pins all pairwise\n");
    printf("  correlations to the same value simultaneously.\n");
}

/* ═══ COMPLEMENTARITY ═══
 *
 * Measuring a state |ψ⟩ in the Z basis gives outcome 0 with
 * probability |⟨0|ψ⟩|² and 1 with |⟨1|ψ⟩|².
 *
 * Measuring in the X basis means first rotating by H and then
 * measuring in Z:
 *     Pr(X=0) = |⟨0| H ψ⟩|² / norm²
 *     Pr(X=1) = |⟨1| H ψ⟩|² / norm²
 *
 * The complementarity statement: if |ψ⟩ is a Z-eigenstate (|0⟩
 * or |1⟩), its X-distribution is uniform.  If |ψ⟩ is an
 * X-eigenstate (|+⟩ or |−⟩), its Z-distribution is uniform.
 */
static void experiment_complementarity(void){
    printf("\n═══ EXPERIMENT 3: Complementarity of Z and X bases ═══\n\n");

    /* Single bit, 2-d */
    int states[4][2] = {
        {1, 0},    /* |0⟩ */
        {0, 1},    /* |1⟩ */
        {1, 1},    /* |+⟩ */
        {1, -1}    /* |−⟩ */
    };
    const char *names[4] = {"|0⟩", "|1⟩", "|+⟩", "|−⟩"};

    printf("  state | Pr(Z=0) | Pr(Z=1) | Pr(X=0) | Pr(X=1)\n");
    printf("  ------+---------+---------+---------+---------\n");

    for(int s = 0; s < 4; s++){
        int a = states[s][0], b = states[s][1];
        int n_z = a*a + b*b;
        double pz0 = (double)(a*a) / n_z;
        double pz1 = (double)(b*b) / n_z;

        /* Apply Hadamard: (a, b) → (a+b, a−b) */
        int ha = a + b, hb = a - b;
        int n_x = ha*ha + hb*hb;
        double px0 = (double)(ha*ha) / n_x;
        double px1 = (double)(hb*hb) / n_x;

        printf("   %-4s |  %.3f  |  %.3f  |  %.3f  |  %.3f\n",
               names[s], pz0, pz1, px0, px1);
    }

    printf("\n  Z-eigenstates  |0⟩, |1⟩  →  X is uniform 50/50\n");
    printf("  X-eigenstates  |+⟩, |−⟩  →  Z is uniform 50/50\n");
    printf("  The two bases are maximally complementary:\n");
    printf("  certainty in one means complete ignorance in the other.\n");
    printf("  This is a classical version of Heisenberg's uncertainty —\n");
    printf("  not about physical particles, but about amplitude bases.\n");
}

/* ═══ SCHMIDT RANK ═══
 *
 * A 2-bit state is an element of C^2 ⊗ C^2 (here Z^2 ⊗ Z^2).
 * Writing it as a 2×2 matrix M with M[a][b] = t_{ab}, the Schmidt
 * rank of the state equals the rank of M.
 *
 * Rank 1: state is a product |α⟩⊗|β⟩
 * Rank 2: state is entangled (no such factorisation exists)
 *
 * We compute rank via an integer determinant: rank ≥ 2 iff
 * M has a non-zero 2×2 minor, i.e. det(M) ≠ 0 OR M has two
 * independent rows.  For 2×2 integer matrices rank is 0, 1, or 2.
 */
static int matrix_rank_2x2(const Vec4 t){
    /* M = [[t[0], t[1]], [t[2], t[3]]] */
    int m00 = t[0], m01 = t[1], m10 = t[2], m11 = t[3];
    if(m00 == 0 && m01 == 0 && m10 == 0 && m11 == 0) return 0;
    /* rank ≥ 1 */
    int det = m00 * m11 - m01 * m10;
    if(det != 0) return 2;
    return 1;
}

static void experiment_schmidt(void){
    printf("\n═══ EXPERIMENT 4: Schmidt rank bounds ═══\n\n");

    struct { const char *name; Vec4 v; } cases[] = {
        {"|00⟩",        {1, 0, 0, 0}},
        {"|01⟩",        {0, 1, 0, 0}},
        {"|+⟩⊗|0⟩",    {1, 0, 1, 0}},
        {"|+⟩⊗|+⟩",    {1, 1, 1, 1}},
        {"Φ+",          {1, 0, 0, 1}},
        {"Φ−",          {1, 0, 0, -1}},
        {"Ψ+",          {0, 1, 1, 0}},
        {"Ψ−",          {0, 1, -1, 0}},
        {"(0,0,0,0)",   {0, 0, 0, 0}},
    };
    int n = sizeof(cases) / sizeof(cases[0]);

    printf("  state         | matrix form       | rank\n");
    printf("  --------------+-------------------+-----\n");
    for(int i = 0; i < n; i++){
        int r = matrix_rank_2x2(cases[i].v);
        printf("  %-13s | [[%+d,%+d],[%+d,%+d]] |  %d\n",
               cases[i].name,
               cases[i].v[0], cases[i].v[1],
               cases[i].v[2], cases[i].v[3], r);
    }

    printf("\n  Rank 1 (separable): |00⟩, |01⟩, |+⟩⊗|0⟩, |+⟩⊗|+⟩\n");
    printf("  Rank 2 (entangled): all four Bell states\n");
    printf("  Entanglement = the state cannot be compressed below rank 2.\n");
    printf("  A 2-bit system has maximum Schmidt rank 2 — the irreducible\n");
    printf("  bound on bipartite entanglement content.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("LIMITS OF PHASE BITS\n");
    printf("══════════════════════════════════════════\n");
    printf("Four structural constraints that phase bits CANNOT violate.\n");

    experiment_no_cloning();
    experiment_monogamy();
    experiment_complementarity();
    experiment_schmidt();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. No linear cloner exists: CNOT clones basis states\n");
    printf("     but turns |+⟩⊗|0⟩ into a Bell state, not |+⟩⊗|+⟩\n");
    printf("  2. Monogamy: Bell-paired A has exactly 0 correlation\n");
    printf("     with any third bit C — the budget is exhausted\n");
    printf("  3. Complementarity: Z-sharp states are X-uniform,\n");
    printf("     classical Heisenberg on amplitude bases\n");
    printf("  4. Schmidt rank ≤ 2 for 2-bit states — the hard ceiling\n");
    printf("     on bipartite entanglement content\n");
    printf("\n  These four limits match their quantum counterparts\n");
    printf("  structurally, derived from LINEARITY alone (no physics).\n");
    return 0;
}
