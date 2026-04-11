/*
 * REVERSIBLE BITS
 * =================
 *
 * First alternative direction after phase bits: information-
 * conserving classical computation.  Based on Bennett (1973),
 * Fredkin-Toffoli (1982), and Landauer (1961).  Every circuit is
 * invertible — no bits are erased, no information is destroyed,
 * so (in a thermodynamic sense) no heat is dissipated.
 *
 * Primitive gates:
 *
 *   NOT                     x     → ¬x
 *   CNOT(c, t)              t     → t ⊕ c
 *   TOFFOLI(c1, c2, t)      t     → t ⊕ (c1 ∧ c2)
 *   FREDKIN(c, a, b)        swap  a, b if c = 1
 *
 * Known facts:
 *   - {TOFFOLI, NOT} is universal for classical reversible
 *     computation (every permutation of {0,1}^n can be built).
 *   - FREDKIN is CONSERVATIVE: it preserves the Hamming weight
 *     of its input, so it's a classical analogue of a
 *     conservation law — useful for "ball-bearing" mechanical
 *     computing models.
 *   - Every Boolean function f : {0,1}^n → {0,1}^m can be made
 *     reversible as Uf : (x, y) → (x, y ⊕ f(x)), at the cost of
 *     carrying x along as an extra output (Bennett's trick).
 *
 * Experiments:
 *   1. Gate self-invertibility: every gate G satisfies G·G = id
 *      on its wires (for NOT, CNOT, TOFFOLI, FREDKIN).
 *   2. Fredkin conservation: popcount is preserved exactly.
 *   3. Build AND and OR from TOFFOLI + ancilla; measure cost.
 *   4. Full reversible adder: (a, b, cin, 0, 0) → (a, b, cin, sum, cout)
 *      verified on all 8 inputs, and run backwards recovers
 *      the original input.
 *   5. Bennett uncomputation: compute, copy, uncompute → clean
 *      ancillas restored to 0.
 *
 * Compile: gcc -O3 -march=native -o rev reversible_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* Integer "register" of n bits, packed into a uint32_t.  Wire k is
 * bit k of the register.  All gates act in place. */

static int BIT(uint32_t s, int k){return (s >> k) & 1;}
static uint32_t SET(uint32_t s, int k, int v){
    s &= ~(1u << k);
    s |= ((uint32_t)(v & 1)) << k;
    return s;
}

/* ═══ GATES ═══ */
static uint32_t gate_NOT(uint32_t s, int k){return s ^ (1u << k);}
static uint32_t gate_CNOT(uint32_t s, int c, int t){
    if(BIT(s, c)) s ^= (1u << t);
    return s;
}
static uint32_t gate_TOFFOLI(uint32_t s, int c1, int c2, int t){
    if(BIT(s, c1) && BIT(s, c2)) s ^= (1u << t);
    return s;
}
static uint32_t gate_FREDKIN(uint32_t s, int c, int a, int b){
    if(BIT(s, c)){
        int va = BIT(s, a);
        int vb = BIT(s, b);
        s = SET(s, a, vb);
        s = SET(s, b, va);
    }
    return s;
}

/* ═══ EXPERIMENT 1: Self-invertibility ═══ */
static void experiment_selfinverse(void){
    printf("\n═══ EXPERIMENT 1: Every primitive gate is its own inverse ═══\n\n");

    int n_states = 16;    /* exhaust all 4-bit states */
    int fail_NOT = 0, fail_CNOT = 0, fail_TOF = 0, fail_FRED = 0;

    for(int s = 0; s < n_states; s++){
        if(gate_NOT(gate_NOT((uint32_t)s, 0), 0) != (uint32_t)s) fail_NOT++;
        if(gate_CNOT(gate_CNOT((uint32_t)s, 0, 1), 0, 1) != (uint32_t)s) fail_CNOT++;
        if(gate_TOFFOLI(gate_TOFFOLI((uint32_t)s, 0, 1, 2), 0, 1, 2) != (uint32_t)s) fail_TOF++;
        if(gate_FREDKIN(gate_FREDKIN((uint32_t)s, 0, 1, 2), 0, 1, 2) != (uint32_t)s) fail_FRED++;
    }

    printf("  Applied each gate twice over all %d input states:\n", n_states);
    printf("    NOT     : %s   (%d failures)\n",
           fail_NOT == 0 ? "INVOLUTIVE ✓" : "not involutive", fail_NOT);
    printf("    CNOT    : %s   (%d failures)\n",
           fail_CNOT == 0 ? "INVOLUTIVE ✓" : "not involutive", fail_CNOT);
    printf("    TOFFOLI : %s   (%d failures)\n",
           fail_TOF == 0 ? "INVOLUTIVE ✓" : "not involutive", fail_TOF);
    printf("    FREDKIN : %s   (%d failures)\n",
           fail_FRED == 0 ? "INVOLUTIVE ✓" : "not involutive", fail_FRED);
    printf("\n  Every gate is its own inverse — a reversible circuit runs\n");
    printf("  backwards by executing the same sequence in reverse order.\n");
}

/* ═══ EXPERIMENT 2: Fredkin conservation ═══ */
static void experiment_conservation(void){
    printf("\n═══ EXPERIMENT 2: Fredkin preserves Hamming weight ═══\n\n");

    int n_states = 1 << 8;
    int fail = 0;
    for(int s = 0; s < n_states; s++){
        uint32_t t = gate_FREDKIN((uint32_t)s, 0, 3, 5);
        if(__builtin_popcount(t) != __builtin_popcount((unsigned)s)) fail++;
    }
    printf("  Tested Fredkin(c=0, a=3, b=5) on all 256 eight-bit states.\n");
    printf("  Weight preserved in %d/%d cases.  %s\n",
           n_states - fail, n_states, fail == 0 ? "✓" : "✗");

    /* Contrast: TOFFOLI is NOT conservative */
    int n_changed = 0;
    int n_decreased = 0, n_increased = 0;
    for(int s = 0; s < n_states; s++){
        uint32_t t = gate_TOFFOLI((uint32_t)s, 0, 1, 2);
        int dw = __builtin_popcount(t) - __builtin_popcount((unsigned)s);
        if(dw != 0) n_changed++;
        if(dw < 0) n_decreased++;
        if(dw > 0) n_increased++;
    }
    printf("\n  By comparison, TOFFOLI changed weight in %d/%d cases.\n",
           n_changed, n_states);
    printf("  TOFFOLI is reversible but NOT conservative:\n");
    printf("    %d cases flipped target 0→1 (+1 weight)\n", n_increased);
    printf("    %d cases flipped target 1→0 (−1 weight)\n", n_decreased);
    printf("\n  Fredkin is the 'conservation law' of reversible logic —\n");
    printf("  a classical analogue of charge or particle-number conservation.\n");
}

/* ═══ EXPERIMENT 3: Building AND and OR from Toffoli ═══ */
static void experiment_and_or(void){
    printf("\n═══ EXPERIMENT 3: AND and OR via Toffoli + NOT + ancilla ═══\n\n");

    printf("  AND(a, b) with ancilla wire 2 initialised to 0:\n");
    printf("    TOFFOLI(a=0, b=1, target=2):  wire 2 becomes a ∧ b\n\n");
    printf("  a | b | wire 2 after\n");
    printf("  --+---+--------------\n");
    for(int a = 0; a < 2; a++)
        for(int b = 0; b < 2; b++){
            uint32_t s = 0;
            s = SET(s, 0, a);
            s = SET(s, 1, b);
            /* wire 2 = 0 initially */
            s = gate_TOFFOLI(s, 0, 1, 2);
            printf("  %d | %d |   %d\n", a, b, BIT(s, 2));
        }

    printf("\n  OR(a, b) via De Morgan: a ∨ b = ¬(¬a ∧ ¬b)\n");
    printf("  Circuit: NOT(a); NOT(b); TOFFOLI(a, b, c←0); NOT(c);\n");
    printf("           NOT(a); NOT(b);   (uncompute the input flips)\n\n");
    printf("  a | b | OR result\n");
    printf("  --+---+----------\n");
    for(int a = 0; a < 2; a++)
        for(int b = 0; b < 2; b++){
            uint32_t s = 0;
            s = SET(s, 0, a);
            s = SET(s, 1, b);
            /* wire 2 = 0 initially */
            s = gate_NOT(s, 0);
            s = gate_NOT(s, 1);
            s = gate_TOFFOLI(s, 0, 1, 2);
            s = gate_NOT(s, 2);
            s = gate_NOT(s, 0);
            s = gate_NOT(s, 1);
            printf("  %d | %d |   %d\n", a, b, BIT(s, 2));
        }

    printf("\n  Cost of one non-reversible binary gate as a reversible circuit:\n");
    printf("    1 Toffoli + 1 ancilla  for AND\n");
    printf("    1 Toffoli + 1 ancilla + 5 NOTs  for OR\n");
    printf("  Every irreversible operation becomes reversible with ancillas.\n");
}

/* ═══ EXPERIMENT 4: Reversible full adder ═══
 *
 * Inputs: a (wire 0), b (wire 1), cin (wire 2)
 * Ancilla: sum (wire 3), cout (wire 4)  — both start at 0
 *
 * Output: (a, b, cin, sum, cout) where sum = a⊕b⊕cin, cout = maj(a,b,cin)
 *
 * Circuit uses 2 Toffoli + 3 CNOT.  At the end we run the circuit
 * backwards and verify the state returns to (a, b, cin, 0, 0).
 */
static uint32_t reversible_full_adder(uint32_t s){
    /* sum = a XOR b XOR cin */
    s = gate_CNOT(s, 0, 3);  /* sum ^= a */
    s = gate_CNOT(s, 1, 3);  /* sum ^= b */
    s = gate_CNOT(s, 2, 3);  /* sum ^= cin */
    /* cout = (a AND b) XOR (cin AND (a XOR b)) */
    s = gate_TOFFOLI(s, 0, 1, 4);  /* cout ^= a AND b */
    /* Now we need (a XOR b) in some wire. We can temporarily compute it
     * by CNOTing a into b, using b as the scratch, then undoing. */
    s = gate_CNOT(s, 0, 1);        /* b ← a XOR b (destructive) */
    s = gate_TOFFOLI(s, 1, 2, 4);  /* cout ^= (a XOR b) AND cin */
    s = gate_CNOT(s, 0, 1);        /* restore b ← a XOR b XOR a = original b */
    return s;
}

static uint32_t reversible_full_adder_inverse(uint32_t s){
    /* Run all gates in reverse */
    s = gate_CNOT(s, 0, 1);
    s = gate_TOFFOLI(s, 1, 2, 4);
    s = gate_CNOT(s, 0, 1);
    s = gate_TOFFOLI(s, 0, 1, 4);
    s = gate_CNOT(s, 2, 3);
    s = gate_CNOT(s, 1, 3);
    s = gate_CNOT(s, 0, 3);
    return s;
}

static void experiment_adder(void){
    printf("\n═══ EXPERIMENT 4: Reversible full adder ═══\n\n");
    printf("  (a, b, cin, 0, 0) → (a, b, cin, sum, cout)\n\n");
    printf("  a b cin | sum cout | expected | match\n");
    printf("  --------+----------+----------+------\n");

    int all_ok = 1;
    int all_inv = 1;
    for(int a = 0; a < 2; a++)
      for(int b = 0; b < 2; b++)
        for(int cin = 0; cin < 2; cin++){
            uint32_t s0 = 0;
            s0 = SET(s0, 0, a);
            s0 = SET(s0, 1, b);
            s0 = SET(s0, 2, cin);
            /* wires 3, 4 = 0 */

            uint32_t s = reversible_full_adder(s0);
            int sum_bit = BIT(s, 3);
            int cout_bit = BIT(s, 4);
            int exp_sum = a ^ b ^ cin;
            int exp_cout = (a & b) | (cin & (a ^ b));
            int ok = (sum_bit == exp_sum && cout_bit == exp_cout);
            if(!ok) all_ok = 0;

            /* Also check wires 0,1,2 unchanged */
            int a_out = BIT(s, 0), b_out = BIT(s, 1), cin_out = BIT(s, 2);
            int inputs_preserved = (a_out == a && b_out == b && cin_out == cin);
            if(!inputs_preserved) all_ok = 0;

            printf("  %d %d  %d  |  %d   %d   |  %d   %d   |  %s\n",
                   a, b, cin, sum_bit, cout_bit, exp_sum, exp_cout, ok ? "✓" : "✗");

            /* Run backwards — should get s0 back */
            uint32_t s_back = reversible_full_adder_inverse(s);
            if(s_back != s0) all_inv = 0;
        }

    printf("\n  All outputs correct: %s\n", all_ok ? "YES ✓" : "NO ✗");
    printf("  Backward pass recovered inputs: %s\n", all_inv ? "YES ✓" : "NO ✗");
    printf("\n  Cost: 3 CNOT + 2 Toffoli + 2 ancilla wires.\n");
    printf("  The circuit is a genuine permutation of {0,1}^5 and can be\n");
    printf("  simulated by adiabatic hardware with zero heat dissipation.\n");
}

/* ═══ EXPERIMENT 5: Bennett uncomputation ═══
 *
 * Compute g = AND(a, b) into an ancilla wire and COPY it to an
 * output wire (via CNOT), then UNCOMPUTE the AND to restore the
 * ancilla to 0.  Only the copied output remains.
 *
 * Layout:
 *   wire 0 = a     (input)
 *   wire 1 = b     (input)
 *   wire 2 = AND ancilla
 *   wire 3 = output copy
 */
static void experiment_bennett(void){
    printf("\n═══ EXPERIMENT 5: Bennett uncomputation ═══\n\n");
    printf("  Compute AND(a,b) into wire 2, copy to wire 3, uncompute wire 2.\n");
    printf("  Final state: (a, b, 0, a∧b).  Ancilla wire is CLEAN.\n\n");
    printf("  a | b | wire 2 | wire 3\n");
    printf("  --+---+--------+--------\n");

    int all_clean = 1;
    for(int a = 0; a < 2; a++)
        for(int b = 0; b < 2; b++){
            uint32_t s = 0;
            s = SET(s, 0, a);
            s = SET(s, 1, b);
            /* Compute AND into wire 2 */
            s = gate_TOFFOLI(s, 0, 1, 2);
            /* Copy wire 2 to wire 3 via CNOT */
            s = gate_CNOT(s, 2, 3);
            /* Uncompute wire 2 */
            s = gate_TOFFOLI(s, 0, 1, 2);
            printf("  %d | %d |   %d    |   %d\n",
                   a, b, BIT(s, 2), BIT(s, 3));
            if(BIT(s, 2) != 0) all_clean = 0;
        }
    printf("\n  Ancilla cleanly restored to 0: %s\n", all_clean ? "YES ✓" : "NO ✗");
    printf("  This is how reversible computation 'erases' intermediate\n");
    printf("  values without actually losing information — the junk is\n");
    printf("  reversibly returned to its initial state.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("REVERSIBLE BITS: information-conserving classical computation\n");
    printf("══════════════════════════════════════════\n");
    printf("Toffoli, Fredkin, CNOT, NOT — all 100%% classical,\n");
    printf("all strictly invertible, all dissipation-free.\n");

    experiment_selfinverse();
    experiment_conservation();
    experiment_and_or();
    experiment_adder();
    experiment_bennett();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Every primitive gate is its own inverse → every\n");
    printf("     circuit runs backwards by reversing the sequence\n");
    printf("  2. Fredkin is a conservative gate — classical analogue\n");
    printf("     of a conservation law\n");
    printf("  3. Irreversible functions (AND, OR, f: n→m) become\n");
    printf("     reversible at the cost of ancilla wires\n");
    printf("  4. Full adder in 5 gates + 2 ancillas, verified\n");
    printf("     forward and backward on all 8 inputs\n");
    printf("  5. Bennett uncomputation cleans up ancillas so only\n");
    printf("     the intended output remains\n");
    printf("\n  New primitive property vs ordinary bits: INFORMATION\n");
    printf("  CONSERVATION as a hard constraint. No bit is ever erased.\n");
    return 0;
}
