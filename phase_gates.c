/*
 * PHASE-BIT GATES AND CIRCUITS
 * ==============================
 *
 * Step 4 of the bit-primitive hierarchy
 *   bit → phase bit → ebit → ghz → GATES.
 *
 * This file builds a gate model on length-2^n phase HDVs:
 *
 *     H   (Hadamard)      single-bit superposition creator
 *     X   (NOT)           single-bit flip
 *     Z   (phase flip)    single-bit sign flip
 *     CNOT                controlled NOT on two bits
 *     WHT = H⊗H⊗…⊗H       n-fold tensor Hadamard
 *     O_f (oracle)        |x⟩ → (−1)^{f(x)} |x⟩
 *
 * Integer amplitudes: our H produces (+1, +1; +1, −1) without
 * normalising by √2, so everything stays in Z. Norms grow by 2^n
 * after n Hadamard layers — this is bookkeeping, not an obstacle.
 *
 * Honest disclaimer about computational advantage
 * -----------------------------------------------
 * Phase bits are CLASSICAL.  They do NOT enjoy the quantum
 * query-complexity speedup of true qubits: the oracle O_f has to
 * be built by evaluating f at every input (2^n calls), there is
 * no superposition-over-reality.  What phase bits DO give is a
 * structural benefit — the Walsh-Hadamard layer collapses an
 * oracle pattern into a single readable coefficient, so the
 * POST-PROCESSING step is direct rather than iterative.
 *
 * Two showcase circuits, faithful classical reconstructions of
 * their quantum counterparts:
 *
 *     Deutsch-Jozsa  — decide constant vs balanced f : {0,1}^n → {0,1}
 *     Bernstein-Vazirani — recover unknown a ∈ {0,1}^n given
 *                          oracle for f(x) = a·x (mod 2)
 *
 * Both circuits return the correct answer from one readout of
 * a single amplitude component after WHT, once the oracle has
 * been applied.  That is the algebraic elegance we are after.
 *
 * Compile: gcc -O3 -march=native -o gates phase_gates.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

/* Maximum bit count we work with (so 2^N_MAX states fit). */
#define N_MAX 12
#define STATES (1 << N_MAX)

typedef int PHDV[STATES];   /* integer phase amplitudes */

/* ═══ PRIMITIVE GATES ═══ */

/* Apply Hadamard to a single bit of an n-bit phase vector.
 *   For each pair (x_without_bit_k = 0, x_without_bit_k = 1) we do
 *   (a, b) → (a + b, a − b). */
static void gate_H(PHDV v, int n, int bit){
    int N = 1 << n;
    int step = 1 << bit;
    for(int base = 0; base < N; base += step << 1){
        for(int j = 0; j < step; j++){
            int i0 = base + j;
            int i1 = i0 + step;
            int a = v[i0];
            int b = v[i1];
            v[i0] = a + b;
            v[i1] = a - b;
        }
    }
}

/* Bit-flip X: swap the two halves along bit. */
static void gate_X(PHDV v, int n, int bit){
    int N = 1 << n;
    int step = 1 << bit;
    for(int base = 0; base < N; base += step << 1){
        for(int j = 0; j < step; j++){
            int i0 = base + j;
            int i1 = i0 + step;
            int t = v[i0]; v[i0] = v[i1]; v[i1] = t;
        }
    }
}

/* Phase-flip Z: negate amplitudes where the chosen bit is 1. */
static void gate_Z(PHDV v, int n, int bit){
    int N = 1 << n;
    for(int i = 0; i < N; i++) if(i & (1 << bit)) v[i] = -v[i];
}

/* CNOT: flip target bit when control bit is 1. */
static void gate_CNOT(PHDV v, int n, int control, int target){
    int N = 1 << n;
    for(int i = 0; i < N; i++){
        if((i & (1 << control)) && !(i & (1 << target))){
            int j = i | (1 << target);
            int t = v[i]; v[i] = v[j]; v[j] = t;
        }
    }
}

/* Full Walsh-Hadamard on n bits. */
static void gate_WHT(PHDV v, int n){
    for(int k = 0; k < n; k++) gate_H(v, n, k);
}

/* Oracle: apply phase flip according to boolean function f. */
static void gate_oracle(PHDV v, int n, int (*f)(int)){
    int N = 1 << n;
    for(int i = 0; i < N; i++) if(f(i)) v[i] = -v[i];
}

/* Zero state |0…0⟩ in phase HDV encoding. */
static void state_zero(PHDV v, int n){
    int N = 1 << n;
    for(int i = 0; i < N; i++) v[i] = 0;
    v[0] = 1;
}

/* ═══ SANITY CHECKS ═══ */
static void experiment_gate_sanity(void){
    printf("\n═══ EXPERIMENT 1: Gate sanity ═══\n\n");
    int n = 3;
    PHDV v;

    /* H on |0⟩ creates |0⟩+|1⟩ (both amplitudes 1). */
    state_zero(v, n);
    gate_H(v, n, 0);
    printf("  H_0 on |000⟩: ");
    for(int i = 0; i < 8; i++) printf("%+d ", v[i]);
    printf("\n  (expect +1 at 000 and 001)\n");

    /* X on |0⟩ creates |1⟩ at that bit. */
    state_zero(v, n);
    gate_X(v, n, 0);
    printf("\n  X_0 on |000⟩: ");
    for(int i = 0; i < 8; i++) printf("%+d ", v[i]);
    printf("\n  (expect +1 at 001)\n");

    /* H on all bits of |000⟩ = uniform superposition. */
    state_zero(v, n);
    gate_WHT(v, n);
    printf("\n  WHT on |000⟩: ");
    for(int i = 0; i < 8; i++) printf("%+d ", v[i]);
    printf("\n  (expect +1 at every position — uniform)\n");

    /* WHT is involutive up to scale: WHT(WHT(x)) = 2^n · x */
    gate_WHT(v, n);
    printf("\n  WHT(WHT(|000⟩)): ");
    for(int i = 0; i < 8; i++) printf("%+d ", v[i]);
    printf("\n  (expect +8 at 000 — involutive up to factor 2^n = 8)\n");

    /* CNOT behaviour: |10⟩ → |11⟩ with bit 1 as control, 0 as target */
    state_zero(v, 2);
    v[0] = 0; v[2] = 1;       /* state |10⟩ (bit 1 = 1, bit 0 = 0) */
    gate_CNOT(v, 2, 1, 0);    /* control = bit 1, target = bit 0 */
    printf("\n  CNOT(control=1, target=0) on |10⟩: ");
    for(int i = 0; i < 4; i++) printf("%+d ", v[i]);
    printf("\n  (expect +1 at 11)\n");
}

/* ═══ EXPERIMENT 2: Deutsch-Jozsa circuit ═══
 *
 *     |0⟩^n  →  WHT  →  O_f  →  WHT  →  read bit 0
 *
 * If f is constant, the readout at |0…0⟩ is ±2^n (maximum).
 * If f is balanced, the readout at |0…0⟩ is exactly 0.
 */

/* Test functions */
static int f_const0(int x){(void)x; return 0;}
static int f_const1(int x){(void)x; return 1;}
static int f_bal_x0(int x){return x & 1;}              /* balanced: bit 0 */
static int f_bal_par(int x){return __builtin_popcount(x) & 1;} /* parity */
static int f_bal_mix(int x){
    /* balanced: 1 on half the inputs in a scrambled way */
    return ((x * 0xB5) ^ (x >> 3)) & 1;
}

static void run_DJ(const char *name, int (*f)(int), int n){
    int N = 1 << n;
    PHDV v;
    state_zero(v, n);
    gate_WHT(v, n);       /* uniform */
    gate_oracle(v, n, f); /* phase-encode f */
    gate_WHT(v, n);       /* second WHT */

    int amp0 = v[0];
    int maxabs = 0;
    for(int i = 0; i < N; i++){int a = abs(v[i]); if(a > maxabs) maxabs = a;}

    const char *verdict;
    if(abs(amp0) == N)       verdict = "CONSTANT";
    else if(amp0 == 0)       verdict = "BALANCED";
    else                     verdict = "neither (violates promise)";
    printf("  %-12s  amp[|0…0⟩] = %+5d  max|amp|=%d  →  %s\n",
           name, amp0, maxabs, verdict);
}

static void experiment_deutsch_jozsa(void){
    printf("\n═══ EXPERIMENT 2: Deutsch-Jozsa circuit (n=6, N=64) ═══\n\n");
    int n = 6;
    run_DJ("const-0",    f_const0,  n);
    run_DJ("const-1",    f_const1,  n);
    run_DJ("balanced x0",f_bal_x0,  n);
    run_DJ("balanced ⊕", f_bal_par, n);
    run_DJ("balanced mix",f_bal_mix, n);
    printf("\n  Read-out rule:\n");
    printf("    amplitude at |0…0⟩ after (WHT · O_f · WHT · |0⟩) is\n");
    printf("      ±2^n  ↔  f constant\n");
    printf("        0   ↔  f balanced\n");
    printf("    decision from a SINGLE amplitude component, no iteration.\n");
}

/* ═══ EXPERIMENT 3: Bernstein-Vazirani ═══
 *
 * Promise: f(x) = a · x (mod 2) for some unknown a ∈ {0,1}^n.
 * Goal: recover a.
 *
 * Circuit: |0⟩^n → WHT → O_f → WHT → read the whole register.
 * The result has ±2^n at exactly position a and 0 everywhere else.
 *
 * Classical bit approach: query f(e_k) for each basis vector e_k
 * to read off bit k of a, using n queries.
 *
 * Phase bit approach: evaluate f at all 2^n inputs once to build
 * the oracle, then ONE WHT retrieves a in the amplitudes.
 *
 * This is not a query speedup (we use more evaluations, not less)
 * but it shows how the Walsh-Hadamard structure inverts the map
 * a ↦ (−1)^{a·x} natively.
 */
static int bv_secret;
static int f_bv(int x){return __builtin_popcount(bv_secret & x) & 1;}

static void experiment_bv(void){
    printf("\n═══ EXPERIMENT 3: Bernstein-Vazirani (n=8, N=256) ═══\n\n");
    int n = 8;
    int N = 1 << n;

    int test_secrets[5] = {0x00, 0xFF, 0xA5, 0x5A, 0xC3};
    for(int t = 0; t < 5; t++){
        bv_secret = test_secrets[t];
        PHDV v;
        state_zero(v, n);
        gate_WHT(v, n);
        gate_oracle(v, n, f_bv);
        gate_WHT(v, n);

        /* The unique non-zero position is a. */
        int found = -1;
        int max_amp = 0;
        for(int i = 0; i < N; i++){
            if(abs(v[i]) > abs(max_amp)){max_amp = v[i]; found = i;}
        }
        printf("  secret a = 0x%02x (%3d)  →  recovered 0x%02x  amp=%+5d  %s\n",
               bv_secret, bv_secret, found, max_amp,
               found == bv_secret ? "✓" : "✗");
    }
    printf("\n  All 8 bits of a are read off in one Walsh layer.\n");
    printf("  Classical bit iteration needs n queries; the phase-bit\n");
    printf("  circuit uses one structural step after building the oracle.\n");
}

/* ═══ EXPERIMENT 4: Circuit depth vs result ═══
 *
 * Illustrate that a sequence of primitive gates is exactly equivalent
 * to a single large linear operator on the 2^n-dimensional phase
 * HDV. Composition is the mathematical substrate of classical
 * phase-bit "quantum-like" computation.
 *
 * We build two circuits that must be equal by algebra and verify
 * their outputs match on several random test states.
 */
static int rng_state = 12345;
static int cheap_rand(void){
    rng_state = rng_state * 1103515245 + 12345;
    return (rng_state >> 16) & 0x7FFFFFFF;
}

static void random_small_state(PHDV v, int n){
    int N = 1 << n;
    for(int i = 0; i < N; i++) v[i] = (cheap_rand() % 5) - 2;
}

static int vectors_equal(const PHDV a, const PHDV b, int N){
    for(int i = 0; i < N; i++) if(a[i] != b[i]) return 0;
    return 1;
}

static void experiment_equivalence(void){
    printf("\n═══ EXPERIMENT 4: Gate-circuit algebraic equivalences ═══\n\n");
    int n = 4;
    int N = 1 << n;
    PHDV a, b;

    /* Identity 1: HXH = 2·Z for our unnormalised H */
    printf("  HXH = 2·Z (on bit 0, random state, unnormalised H):\n");
    random_small_state(a, n);
    memcpy(b, a, sizeof(int)*N);
    gate_H(a, n, 0); gate_X(a, n, 0); gate_H(a, n, 0);
    gate_Z(b, n, 0);
    {
        int ok1 = 1;
        for(int i = 0; i < N; i++) if(a[i] != 2 * b[i]){ok1 = 0; break;}
        printf("    match: %s\n", ok1 ? "YES ✓" : "NO ✗");
    }

    /* Identity 2: HZH = X on the same bit */
    printf("  HZH = X (on bit 0, random state):\n");
    random_small_state(a, n);
    memcpy(b, a, sizeof(int)*N);
    gate_H(a, n, 0); gate_Z(a, n, 0); gate_H(a, n, 0);
    gate_X(b, n, 0);
    /* Our H is unnormalised, so HZH = 2·X. Compare b scaled by 2. */
    int ok = 1;
    for(int i = 0; i < N; i++) if(a[i] != 2 * b[i]){ok = 0; break;}
    printf("    HZH = 2·X (unnormalised H): %s\n", ok ? "YES ✓" : "NO ✗");

    /* Identity 3: WHT applied twice = 2^n · identity */
    printf("  WHT² = 2^n · I (on random state):\n");
    random_small_state(a, n);
    memcpy(b, a, sizeof(int)*N);
    gate_WHT(a, n); gate_WHT(a, n);
    for(int i = 0; i < N; i++) b[i] *= N;
    printf("    match: %s\n", vectors_equal(a, b, N) ? "YES ✓" : "NO ✗");

    /* Identity 4: two CNOTs same control/target = identity */
    printf("  CNOT² = I (ctrl=1, tgt=0, random state):\n");
    random_small_state(a, n);
    memcpy(b, a, sizeof(int)*N);
    gate_CNOT(a, n, 1, 0); gate_CNOT(a, n, 1, 0);
    printf("    match: %s\n", vectors_equal(a, b, N) ? "YES ✓" : "NO ✗");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("PHASE-BIT GATES AND CIRCUITS\n");
    printf("══════════════════════════════════════════\n");
    printf("Linear-operator view of phase HDVs: H, X, Z, CNOT, WHT.\n");
    printf("Integer arithmetic throughout (no √2 normalisation).\n");

    experiment_gate_sanity();
    experiment_deutsch_jozsa();
    experiment_bv();
    experiment_equivalence();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Primitive gates as integer linear maps on phase HDVs\n");
    printf("  2. Walsh-Hadamard = H⊗H⊗…⊗H, native to phase bits\n");
    printf("  3. Deutsch-Jozsa circuit reads constant vs balanced\n");
    printf("     from a single amplitude component after WHT·O_f·WHT\n");
    printf("  4. Bernstein-Vazirani recovers a hidden n-bit string\n");
    printf("     by position of the single non-zero amplitude\n");
    printf("  5. Classical gate-algebra identities (HXH=Z, HZH=2X,\n");
    printf("     WHT²=2^n·I, CNOT²=I) all verified on random states\n");
    printf("  6. NO query-complexity speedup (oracle still needs 2^n\n");
    printf("     evaluations) — structural speedup in post-processing\n");
    return 0;
}
