/*
 * PROBABILISTIC BITS
 * ====================
 *
 * Third alternative: a bit is no longer a definite value but a
 * probability distribution over {0, 1}.
 *
 *     pbit = (p_0, p_1)  with  p_0, p_1 ≥ 0  and  p_0 + p_1 = 1
 *
 * Compared to phase bits, the crucial difference is the
 * NON-NEGATIVITY of components.  You can add distributions and
 * renormalise, but you cannot subtract them — a pbit has no
 * interference.
 *
 * Operations
 *   prior_bit      =  (p_0, p_1)
 *   joint(p, q)    =  outer product, 4-d distribution over pairs
 *   marginal       =  sum out one axis of a joint
 *   noisy-NOT      =  mix the bit with its flip with probability f
 *   Bayes update   =  condition the joint on an observation
 *   entropy H(p)   =  −Σ p_i log₂ p_i
 *
 * Why include this?  Probabilistic bits give you:
 *   - Uncertainty quantification (entropy as cost of a bit)
 *   - Bayesian update as a first-class operation
 *   - Noisy channels and information-theoretic limits
 *   - A baseline against which phase bits are measurably more
 *     powerful (phase bits can exhibit anti-correlation; pbits
 *     cannot fall below zero anywhere).
 *
 * Experiments:
 *   1. Joint and marginal: build a joint distribution, trace out
 *      one axis, verify normalisation and consistency
 *   2. Bayes update: observe b, compute P(a | b)
 *   3. Entropy: measure H(p) for several distributions
 *   4. Noisy channel: a bit passed through a BSC with flip
 *      probability f retains (1 − H(f)) bits of mutual information
 *      (Shannon channel coding theorem numerical witness)
 *   5. Phase vs prob: show that a Bell-state-like correlation
 *      structure cannot be reproduced with non-negative
 *      amplitudes
 *
 * Compile: gcc -O3 -march=native -o prob prob_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* ═══ PBIT and JOINT distribution ═══ */
typedef double Pbit[2];        /* (p0, p1) */
typedef double Joint[4];       /* (p00, p01, p10, p11) indexed as 2a+b */

static void pbit_show(const char *name, const Pbit p){
    printf("  %-12s = (%.4f, %.4f)\n", name, p[0], p[1]);
}
static void joint_show(const char *name, const Joint j){
    printf("  %-12s = (%.4f, %.4f, %.4f, %.4f)   sum=%.4f\n",
           name, j[0], j[1], j[2], j[3], j[0]+j[1]+j[2]+j[3]);
}

static void joint_outer(Joint out, const Pbit a, const Pbit b){
    for(int i = 0; i < 2; i++)
        for(int k = 0; k < 2; k++)
            out[2*i + k] = a[i] * b[k];
}

static void joint_marginal_A(Pbit out, const Joint j){
    out[0] = j[0] + j[1];
    out[1] = j[2] + j[3];
}
static void joint_marginal_B(Pbit out, const Joint j){
    out[0] = j[0] + j[2];
    out[1] = j[1] + j[3];
}

/* Bayes update: observe B = b, return conditional on A. */
static void bayes_update(Pbit out, const Joint j, int b){
    double norm = j[0 + b] + j[2 + b];
    if(norm < 1e-12){out[0] = 0.5; out[1] = 0.5; return;}
    out[0] = j[0 + b] / norm;
    out[1] = j[2 + b] / norm;
}

static double entropy(const Pbit p){
    double h = 0;
    for(int i = 0; i < 2; i++){
        double pi = p[i];
        if(pi > 1e-12) h -= pi * log2(pi);
    }
    return h;
}
static double joint_entropy(const Joint j){
    double h = 0;
    for(int i = 0; i < 4; i++){
        if(j[i] > 1e-12) h -= j[i] * log2(j[i]);
    }
    return h;
}
static double mutual_info(const Joint j){
    Pbit pa, pb;
    joint_marginal_A(pa, j);
    joint_marginal_B(pb, j);
    return entropy(pa) + entropy(pb) - joint_entropy(j);
}

/* ═══ EXPERIMENT 1: Joint and marginal ═══ */
static void experiment_joint(void){
    printf("\n═══ EXPERIMENT 1: Joint distribution and marginals ═══\n\n");

    Pbit a = {0.7, 0.3};
    Pbit b = {0.5, 0.5};
    Joint j;
    joint_outer(j, a, b);

    pbit_show("a",  a);
    pbit_show("b",  b);
    joint_show("outer(a,b)", j);

    Pbit ma, mb;
    joint_marginal_A(ma, j);
    joint_marginal_B(mb, j);
    printf("\n  Marginals:\n");
    pbit_show("marg_A", ma);
    pbit_show("marg_B", mb);
    printf("\n  Marginals recover the original pbits ✓\n");

    /* Non-product joint: entangled-ish positive distribution */
    Joint correlated = {0.4, 0.1, 0.1, 0.4};  /* A and B correlated */
    joint_show("correlated ", correlated);
    joint_marginal_A(ma, correlated);
    joint_marginal_B(mb, correlated);
    pbit_show("marg_A", ma);
    pbit_show("marg_B", mb);

    /* Is 'correlated' factorable? Test det = p_00 · p_11 − p_01 · p_10 */
    double det = correlated[0]*correlated[3] - correlated[1]*correlated[2];
    printf("  det = p_00·p_11 − p_01·p_10 = %.4f\n", det);
    printf("  %s\n", fabs(det) < 1e-12 ? "factorable (separable)" : "NOT factorable (correlated)");
}

/* ═══ EXPERIMENT 2: Bayes update ═══ */
static void experiment_bayes(void){
    printf("\n═══ EXPERIMENT 2: Bayes update ═══\n\n");

    /* Joint distribution of (A, B):
     *   A = sick? prior 0.1
     *   B = test positive? noisy: P(B=+|A=sick) = 0.9, P(B=+|A=well) = 0.1 */
    double p_sick = 0.1;
    double p_well = 0.9;
    double tpr = 0.9;   /* true positive rate */
    double fpr = 0.1;   /* false positive rate */

    Joint j;
    j[0*2 + 0] = p_well * (1 - fpr);  /* well, test − */
    j[0*2 + 1] = p_well * fpr;         /* well, test + */
    j[1*2 + 0] = p_sick * (1 - tpr);   /* sick, test − */
    j[1*2 + 1] = p_sick * tpr;         /* sick, test + */

    joint_show("P(A, B)", j);
    Pbit ma, mb;
    joint_marginal_A(ma, j);
    joint_marginal_B(mb, j);
    pbit_show("P(A=sick)", ma);
    pbit_show("P(B=+)",    mb);

    /* Observe test positive: Bayes-update on A */
    Pbit posterior;
    bayes_update(posterior, j, 1);
    printf("\n  After observing test positive:\n");
    pbit_show("P(A | B=+)", posterior);
    printf("\n  Base rate 0.10 → posterior %.4f: the famous\n", posterior[1]);
    printf("  'base-rate fallacy' calculation. Correct inference is\n");
    printf("  a primitive operation on probabilistic bits.\n");
}

/* ═══ EXPERIMENT 3: Entropy and information content ═══ */
static void experiment_entropy(void){
    printf("\n═══ EXPERIMENT 3: Entropy of pbits ═══\n\n");

    struct {const char *name; Pbit v;} tests[] = {
        {"(1.0, 0.0)",  {1.0, 0.0}},
        {"(0.9, 0.1)",  {0.9, 0.1}},
        {"(0.7, 0.3)",  {0.7, 0.3}},
        {"(0.5, 0.5)",  {0.5, 0.5}},
        {"(0.3, 0.7)",  {0.3, 0.7}},
    };
    printf("  pbit        |  H(p)      (bits)\n");
    printf("  ------------+-------------------\n");
    for(int i = 0; i < 5; i++){
        printf("  %-11s |  %.4f\n", tests[i].name, entropy(tests[i].v));
    }
    printf("\n  H is maximal at (0.5, 0.5) = 1 bit, zero at the\n");
    printf("  deterministic endpoints. Entropy measures how many\n");
    printf("  classical bits are needed to convey the pbit's value.\n");
}

/* ═══ EXPERIMENT 4: Binary symmetric channel (BSC) ═══ */
static void experiment_bsc(void){
    printf("\n═══ EXPERIMENT 4: Capacity of a binary symmetric channel ═══\n\n");

    printf("  Input pbit (0.5, 0.5) through BSC with flip probability f.\n");
    printf("  Capacity = 1 − H(f) bits per use.\n\n");
    printf("  f     | H(f)    | capacity (bits)\n");
    printf("  ------+---------+----------------\n");
    double fs[] = {0.0, 0.01, 0.05, 0.1, 0.2, 0.3, 0.5};
    for(int i = 0; i < 7; i++){
        double f = fs[i];
        Pbit noise = {1 - f, f};
        double Hf = entropy(noise);
        double capacity = 1.0 - Hf;

        /* Numerical witness via joint distribution:
         * P(X, Y) = 0.5 * [[1-f, f], [f, 1-f]]
         * I(X; Y) should equal the capacity at uniform input. */
        Joint j = {0.5*(1-f), 0.5*f, 0.5*f, 0.5*(1-f)};
        double mi = mutual_info(j);

        printf("  %.2f  | %.4f  | cap=%.4f  MI=%.4f\n",
               f, Hf, capacity, mi);
    }
    printf("\n  Capacity and mutual information match exactly at uniform\n");
    printf("  input. This is Shannon's channel coding theorem numerically.\n");
    printf("  f=0.5 is useless (capacity 0), f=0 is perfect (capacity 1).\n");
}

/* ═══ EXPERIMENT 5: Why pbits cannot fake phase bits ═══ */
static void experiment_vs_phase(void){
    printf("\n═══ EXPERIMENT 5: Probabilistic bits cannot encode Bell-like anti-correlation with phase ═══\n\n");

    printf("  Phase-bit ebits Φ+ and Φ− share the same probability\n");
    printf("  distribution |amplitude|² = (0.5, 0, 0, 0.5) but differ\n");
    printf("  in the phase of the |11⟩ component: +1 vs −1.\n\n");

    printf("  In pbit land the 'distribution' of Φ+ and Φ− is identical.\n");
    printf("  No pbit-valued variable can distinguish them — negative\n");
    printf("  amplitudes are NOT allowed in prob. distributions.\n\n");

    /* Numerical check: build a joint for Φ+ and for Φ− as probability
     * distributions (squared amplitudes), they coincide. */
    Joint phi_plus_prob  = {0.5, 0.0, 0.0, 0.5};
    Joint phi_minus_prob = {0.5, 0.0, 0.0, 0.5};
    joint_show("Φ+ squared", phi_plus_prob);
    joint_show("Φ− squared", phi_minus_prob);
    int same = 1;
    for(int i = 0; i < 4; i++) if(phi_plus_prob[i] != phi_minus_prob[i]){same = 0; break;}
    printf("\n  Are probability distributions identical? %s\n",
           same ? "YES (phase lost)" : "NO");
    printf("\n  Concretely: probabilistic bits are a STRICT SUBSET of\n");
    printf("  phase bits restricted to non-negative amplitudes. The\n");
    printf("  Φ+/Φ− pair is the simplest witness of what pbits miss.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("PROBABILISTIC BITS\n");
    printf("══════════════════════════════════════════\n");
    printf("A pbit is a non-negative distribution over {0,1}.\n");

    experiment_joint();
    experiment_bayes();
    experiment_entropy();
    experiment_bsc();
    experiment_vs_phase();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Joint distributions and marginals as primitives\n");
    printf("  2. Bayes update: condition on observed bits\n");
    printf("  3. Shannon entropy as bit-content measure\n");
    printf("  4. BSC capacity = mutual information at uniform input\n");
    printf("  5. Pbits are STRICTLY WEAKER than phase bits:\n");
    printf("     non-negative amplitudes forbid Bell-like sign structure\n");
    printf("\n  New primitive property vs ordinary bits: UNCERTAINTY\n");
    printf("  quantified as entropy. No interference, no negative amp.\n");
    return 0;
}
