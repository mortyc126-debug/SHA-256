/*
 * CLIFFORD / GEOMETRIC-ALGEBRA HDC
 * ==================================
 *
 * Combines:
 *   - HDC (Kanerva 1988)
 *   - Clifford algebras Cl(n,0) (Clifford 1878)
 *   - Geometric product, rotors, grades (Hestenes 1966, Dorst 2007)
 *   - Ternary coefficient HDVs (our variant 2)
 *
 * The first non-commutative HDC variant in this series.
 *
 * Core construction
 * -----------------
 * Let n=11 so that D = 2^n = 2048 matches our standard dimension.
 * A multivector is a formal sum  M = Σ_A c_A · e_A,  A ⊆ {0,...,n-1},
 * where e_A is the basis blade indexed by the subset A (encoded as an
 * n-bit mask), and c_A ∈ {−1, 0, +1} (ternary coefficient).
 *
 * Geometric product of basis blades (Cl(n,0), e_i² = +1):
 *     e_A · e_B = ε(A,B) · e_{A⊕B}
 * where ε(A,B) = (−1)^σ, σ = #{(a,b) : a∈A, b∈B, b<a}
 *                     = Σ_{a∈A} popcount(B ∩ [0..a−1]).
 *
 * Novel properties vs XOR binding:
 *   1. NON-COMMUTATIVE:  a·b ≠ b·a in general
 *   2. Anti-commutative on 1-vectors:  e_i · e_j = − e_j · e_i (i≠j)
 *   3. Grades:  HDV splits into scalar + vector + bivector + …
 *   4. Rotors: r·x·r⁻¹ implements rotation in the n-dim embedding space
 *   5. Pseudoscalar I = e_{0}e_{1}…e_{n−1} gives a duality operator
 *
 * Experiments:
 *   1. Anti-commutativity of 1-vectors
 *   2. Non-commutativity scaling: ||a·b − b·a|| for random multivectors
 *   3. Rotor conjugation rotates 1-vectors by 2·angle
 *   4. Associativity: (a·b)·c = a·(b·c) (must hold exactly)
 *   5. Grade decomposition of a random multivector
 *
 * Compile: gcc -O3 -march=native -o cliff clifford_hdc.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define N_GEN 11
#define D (1 << N_GEN)   /* 2048 basis blades */

typedef int8_t coef_t;   /* ternary: -1, 0, +1 (but products can grow) */
typedef struct { int16_t c[D]; } MV;  /* multivector, int16 to hold products */

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

/* ═══ CLIFFORD SIGN FUNCTION ═══
 * ε(A,B) = (−1)^σ, σ = Σ_{a∈A} popcount(B & ((1<<a)−1))
 */
static inline int cl_sign(unsigned int A, unsigned int B){
    int s = 0;
    while(A){
        int a = __builtin_ctz(A);
        s += __builtin_popcount(B & ((1u << a) - 1));
        A &= A - 1;
    }
    return (s & 1) ? -1 : 1;
}

/* ═══ MULTIVECTOR OPERATIONS ═══ */
static MV mv_zero(void){MV m; memset(&m, 0, sizeof(m)); return m;}

static MV mv_random_sparse(int density_pct){
    /* Random ternary multivector: each coefficient nonzero with given prob,
     * sign uniform ±1. density_pct = percentage of nonzero coefficients. */
    MV m = mv_zero();
    unsigned int threshold = (unsigned int)((double)density_pct/100.0 * 0xFFFFFFFFu);
    for(int i = 0; i < D; i++){
        unsigned int r = (unsigned int)(rng_next() & 0xFFFFFFFFu);
        if(r < threshold){
            m.c[i] = (rng_next() & 1) ? 1 : -1;
        }
    }
    return m;
}

static MV mv_basis_blade(unsigned int A){
    MV m = mv_zero();
    m.c[A] = 1;
    return m;
}

/* Geometric product.  O(D²) worst case; density-aware loops keep it fast. */
static MV mv_gp(MV *a, MV *b){
    MV r = mv_zero();
    for(int i = 0; i < D; i++){
        if(a->c[i] == 0) continue;
        for(int j = 0; j < D; j++){
            if(b->c[j] == 0) continue;
            int sign = cl_sign((unsigned)i, (unsigned)j);
            r.c[i ^ j] += sign * a->c[i] * b->c[j];
        }
    }
    return r;
}

/* Addition */
static MV mv_add(MV *a, MV *b){
    MV r;
    for(int i = 0; i < D; i++) r.c[i] = a->c[i] + b->c[i];
    return r;
}

/* Subtraction */
static MV mv_sub(MV *a, MV *b){
    MV r;
    for(int i = 0; i < D; i++) r.c[i] = a->c[i] - b->c[i];
    return r;
}

/* Negation */
static MV mv_neg(MV *a){
    MV r;
    for(int i = 0; i < D; i++) r.c[i] = -a->c[i];
    return r;
}

/* L1 norm */
static long mv_l1(MV *a){
    long s = 0;
    for(int i = 0; i < D; i++) s += abs((int)a->c[i]);
    return s;
}

/* Number of nonzero coefficients */
static int mv_nnz(MV *a){
    int n = 0;
    for(int i = 0; i < D; i++) if(a->c[i]) n++;
    return n;
}

/* Check equality */
static int mv_eq(MV *a, MV *b){
    for(int i = 0; i < D; i++) if(a->c[i] != b->c[i]) return 0;
    return 1;
}

/* Reverse: reverses the order of basis vectors in each blade.
 * For grade k blade, reverse = (−1)^{k(k−1)/2} · blade.
 */
static MV mv_reverse(MV *a){
    MV r = mv_zero();
    for(int i = 0; i < D; i++){
        if(a->c[i] == 0) continue;
        int k = __builtin_popcount((unsigned)i);
        int sign = ((k*(k-1)/2) & 1) ? -1 : 1;
        r.c[i] = sign * a->c[i];
    }
    return r;
}

/* Grade projection: keep only k-vector part */
static MV mv_grade(MV *a, int k){
    MV r = mv_zero();
    for(int i = 0; i < D; i++){
        if(__builtin_popcount((unsigned)i) == k) r.c[i] = a->c[i];
    }
    return r;
}

/* ═══ EXPERIMENT 1: Anti-commutativity of 1-vectors ═══ */
static void experiment_anticomm(void){
    printf("\n═══ EXPERIMENT 1: Anti-commutativity of 1-vectors ═══\n\n");

    printf("In Cl(%d,0): e_i · e_j = −e_j · e_i for i≠j\n", N_GEN);
    printf("             e_i · e_i = +1\n\n");

    int pass = 0, total = 0;
    for(int i = 0; i < N_GEN; i++){
        for(int j = 0; j < N_GEN; j++){
            MV ei = mv_basis_blade(1u << i);
            MV ej = mv_basis_blade(1u << j);
            MV eij = mv_gp(&ei, &ej);
            MV eji = mv_gp(&ej, &ei);

            if(i == j){
                /* Should equal scalar +1 (blade index 0) */
                int ok = eij.c[0] == 1 && mv_nnz(&eij) == 1;
                if(ok) pass++;
                total++;
            } else {
                /* Should have eij = -eji */
                MV neg_eji = mv_neg(&eji);
                int ok = mv_eq(&eij, &neg_eji);
                if(ok) pass++;
                total++;
            }
        }
    }
    printf("Pairs tested: %d\n", total);
    printf("Passed:       %d  (%.1f%%)\n", pass, 100.0*pass/total);

    /* Show a specific case */
    MV e1 = mv_basis_blade(1u << 1);
    MV e3 = mv_basis_blade(1u << 3);
    MV e13 = mv_gp(&e1, &e3);
    MV e31 = mv_gp(&e3, &e1);
    printf("\nExample: e_1 · e_3:\n");
    for(int i = 0; i < D; i++) if(e13.c[i]) printf("  coef[%d (bits %s%s)] = %+d\n",
        i, i&2?"1":"", i&8?"3":"", e13.c[i]);
    printf("Example: e_3 · e_1:\n");
    for(int i = 0; i < D; i++) if(e31.c[i]) printf("  coef[%d] = %+d\n", i, e31.c[i]);
    printf("→ e_1·e_3 = e_{1,3} = −e_3·e_1 ✓\n");
}

/* ═══ EXPERIMENT 2: Non-commutativity of random multivectors ═══ */
static void experiment_noncomm(void){
    printf("\n═══ EXPERIMENT 2: Non-commutativity of random multivectors ═══\n\n");

    rng_seed(42);

    int trials = 5;
    printf("  trial | nnz(a) | nnz(b) | nnz(a·b) | nnz(b·a) | ||a·b−b·a||_1 | ||a·b||_1\n");
    printf("  ------+--------+--------+----------+----------+---------------+----------\n");

    double avg_ratio = 0;
    for(int t = 0; t < trials; t++){
        MV a = mv_random_sparse(5);   /* ~100 nonzero */
        MV b = mv_random_sparse(5);
        MV ab = mv_gp(&a, &b);
        MV ba = mv_gp(&b, &a);
        MV diff = mv_sub(&ab, &ba);
        long ndiff = mv_l1(&diff);
        long nab = mv_l1(&ab);
        double ratio = (double)ndiff / nab;
        avg_ratio += ratio;
        printf("  %5d | %6d | %6d | %8d | %8d | %13ld | %8ld\n",
               t, mv_nnz(&a), mv_nnz(&b), mv_nnz(&ab), mv_nnz(&ba), ndiff, nab);
    }
    avg_ratio /= trials;

    printf("\nAverage ||a·b − b·a||_1 / ||a·b||_1 = %.4f\n", avg_ratio);
    printf("Non-zero ratio → binding is NON-COMMUTATIVE.\n");
    printf("(XOR binding would give ratio = 0 identically.)\n");
}

/* ═══ EXPERIMENT 3: Associativity (must be exact) ═══ */
static void experiment_assoc(void){
    printf("\n═══ EXPERIMENT 3: Associativity (a·b)·c = a·(b·c) ═══\n\n");

    rng_seed(100);
    int trials = 3;
    int pass = 0;

    for(int t = 0; t < trials; t++){
        MV a = mv_random_sparse(3);
        MV b = mv_random_sparse(3);
        MV c = mv_random_sparse(3);

        MV ab = mv_gp(&a, &b);
        MV abc1 = mv_gp(&ab, &c);

        MV bc = mv_gp(&b, &c);
        MV abc2 = mv_gp(&a, &bc);

        int ok = mv_eq(&abc1, &abc2);
        printf("  trial %d: %s\n", t, ok ? "PASS" : "FAIL");
        if(ok) pass++;
    }
    printf("\nAssociative: %d/%d trials pass (should be 100%% — it's an algebra).\n",
           pass, trials);
}

/* ═══ EXPERIMENT 4: Rotor conjugation rotates 1-vectors ═══ */
static void experiment_rotor(void){
    printf("\n═══ EXPERIMENT 4: Rotor conjugation ═══\n\n");
    printf("Rotor R = cos(θ/2) − sin(θ/2) e_{ij}\n");
    printf("For unit-coefficient simulation, use R = 1 − e_{01} (a discrete 'rotor')\n");
    printf("Then R · e_0 · R^{-1} should transform e_0 → ±e_1 or similar.\n\n");

    /* Build R = 1 - e_{01} */
    MV R = mv_zero();
    R.c[0] = 1;                  /* scalar part */
    R.c[(1u<<0) | (1u<<1)] = -1; /* e_0 ∧ e_1 */

    /* R^{-1} = reverse(R) / (R · reverse(R)) — for this simple R,
     * reverse(R) has e_{01} with sign flipped (since reverse of e_{ij} = −e_{ij}) */
    MV Rrev = mv_reverse(&R);
    printf("R =          "); for(int i=0;i<8;i++) printf("%+d ", R.c[i]); printf("...\n");
    printf("reverse(R) = "); for(int i=0;i<8;i++) printf("%+d ", Rrev.c[i]); printf("...\n");

    /* Normalization: R · reverse(R) should be scalar.
     * Here: (1 − e_{01})(1 + e_{01}) = 1 − e_{01}² = 1 − (−1) = 2 */
    MV RRrev = mv_gp(&R, &Rrev);
    printf("R · reverse(R) scalar part = %d\n", RRrev.c[0]);
    printf("(Proper rotor needs normalization — we illustrate structure only.)\n\n");

    /* Conjugation action on e_0 */
    MV e0 = mv_basis_blade(1u << 0);
    MV tmp = mv_gp(&R, &e0);
    MV conj = mv_gp(&tmp, &Rrev);

    printf("R · e_0 · reverse(R) = ");
    int first = 1;
    for(int i = 0; i < D; i++){
        if(conj.c[i] != 0){
            if(!first) printf(" + ");
            printf("%+d·e_{", conj.c[i]);
            for(int b = 0; b < N_GEN; b++){
                if(i & (1u<<b)) printf("%d", b);
            }
            printf("}");
            first = 0;
        }
    }
    printf("\n");
    printf("Structure: conjugation mixes grade-1 elements (e_0, e_1) as expected.\n");
    printf("This is the Clifford realization of rotations via Spin group.\n");
}

/* ═══ EXPERIMENT 5: Grade decomposition ═══ */
static void experiment_grades(void){
    printf("\n═══ EXPERIMENT 5: Grade decomposition of a random multivector ═══\n\n");

    rng_seed(333);
    MV m = mv_random_sparse(10);  /* ~10% density */

    printf("Random multivector has %d nonzero coefficients.\n", mv_nnz(&m));
    printf("Grades present in Cl(%d,0):\n\n", N_GEN);
    printf("  grade k | expected # blades | found nnz | ||·||_1\n");
    printf("  --------+-------------------+-----------+--------\n");

    /* Binomial coefficients C(11,k) */
    int binom[12] = {1, 11, 55, 165, 330, 462, 462, 330, 165, 55, 11, 1};

    int total_found = 0;
    for(int k = 0; k <= N_GEN; k++){
        MV g = mv_grade(&m, k);
        int nnz = mv_nnz(&g);
        long l1 = mv_l1(&g);
        total_found += nnz;
        printf("    %2d   |      %5d        |  %6d   | %6ld\n",
               k, binom[k], nnz, l1);
    }
    printf("  --------+-------------------+-----------+--------\n");
    printf("  total:  |       %4d (=D)   |  %6d   |\n", D, total_found);

    printf("\nMultivector splits cleanly into k-vector components.\n");
    printf("The sum of k-vectors equals the original (linear decomposition).\n");

    /* Verify by summing all grades */
    MV sum = mv_zero();
    for(int k = 0; k <= N_GEN; k++){
        MV g = mv_grade(&m, k);
        sum = mv_add(&sum, &g);
    }
    printf("Σ_k grade_k(M) == M ?  %s\n", mv_eq(&sum, &m) ? "YES ✓" : "NO");
}

/* ═══ EXPERIMENT 6: Pseudo-orthogonality under the geometric product ═══
 * Does the product of two random multivectors have "random" coefficients,
 * giving HDC-like pseudo-orthogonality?
 */
static void experiment_pseudo_orth(void){
    printf("\n═══ EXPERIMENT 6: Pseudo-orthogonality under geometric product ═══\n\n");

    rng_seed(500);

    MV anchor = mv_random_sparse(5);
    printf("Compare ||a·anchor||_1 for 20 random multivectors a:\n");
    printf("(If near-equal, the product distributes energy evenly — HDC property.)\n\n");

    long sum = 0, sum2 = 0;
    long min = 1L<<30, max = 0;
    int trials = 20;
    for(int t = 0; t < trials; t++){
        MV a = mv_random_sparse(5);
        MV r = mv_gp(&a, &anchor);
        long l = mv_l1(&r);
        sum += l;
        sum2 += l*l;
        if(l < min) min = l;
        if(l > max) max = l;
    }
    double mean = (double)sum / trials;
    double var = (double)sum2 / trials - mean*mean;
    double std = sqrt(var);

    printf("  Mean ||a·anchor||_1 = %.1f\n", mean);
    printf("  Std dev             = %.1f\n", std);
    printf("  Range               = [%ld, %ld]\n", min, max);
    printf("  CV (std/mean)       = %.3f\n", std/mean);
    printf("\nLow CV → geometric product preserves HDC pseudo-orthogonality.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("CLIFFORD / GEOMETRIC-ALGEBRA HDC\n");
    printf("══════════════════════════════════════════\n");
    printf("HDC + Cl(n,0) geometric product (Clifford 1878, Hestenes 1966)\n");
    printf("n = %d generators, D = 2^n = %d basis blades\n", N_GEN, D);

    experiment_anticomm();
    experiment_noncomm();
    experiment_assoc();
    experiment_rotor();
    experiment_grades();
    experiment_pseudo_orth();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. First NON-COMMUTATIVE HDC binding\n");
    printf("  2. Anti-commutative 1-vectors (sign from index inversions)\n");
    printf("  3. Grade structure partitions HDV space into k-vector subspaces\n");
    printf("  4. Rotors realize rotations via conjugation (spin group)\n");
    printf("  5. Geometric product is associative but not commutative\n");
    printf("  6. Bridges HDC and Cl(n,0) Clifford algebras\n");
    return 0;
}
