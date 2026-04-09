/*
 * SELECTION EFFECT: |tension| is LOW for wrong because physics
 * PLACES wrong on low-tension vars. Not new information — SELECTION.
 *
 * Verify: compute E[|tension| | wrong] from Binomial model
 * INCLUDING the fact that P(wrong) depends on |tension|.
 *
 * P(wrong | tension=σ) = 1 - P(sign(σ) = sign(solution) | σ)
 *   = 1 - P(K > d/2 | σ > 0) [approximately]
 *   ≈ 1 - accuracy(σ)
 *
 * Then: E[|tension| | wrong] = Σ_σ |σ| × P(wrong|σ) × P(σ) / P(wrong)
 *
 * This should PREDICT the measured ratio without invoking "new info".
 *
 * Compile: gcc -O3 -o sel_eff selection_effect.c -lm
 */

#include <stdio.h>
#include <math.h>

int main(void){
    printf("═══════════════════════════════\n");
    printf("SELECTION EFFECT COMPUTATION\n");
    printf("═══════════════════════════════\n\n");

    int d = 13; /* average degree at threshold */
    double p = 4.0/7; /* P(vote correct) */
    double q = 3.0/7;

    /* For each possible K (number of positive votes):
       tension σ = (2K-d)/d
       P(K) = Binomial(d, 1/2) [unconditional on solution]
       P(correct | K) = P(solution=1 and K>d/2 | K) + P(solution=0 and K<d/2 | K)

       More precisely:
       P(K | solution=1) = Bin(K; d, p)
       P(K | solution=0) = Bin(K; d, q)
       P(solution=1) = 1/2

       P(K) = 1/2 × [Bin(K;d,p) + Bin(K;d,q)]

       Physics predicts: x̂ = sign(σ) = sign(2K-d)
       P(correct) = P(x̂ = solution)
         = P(K>d/2 | sol=1) × P(sol=1) + P(K<d/2 | sol=0) × P(sol=0)
         By symmetry = P(K>d/2 | sol=1) = Σ_{k>d/2} Bin(k;d,p)

       But P(correct | K) is different:
       If K > d/2: x̂=1. P(correct|K) = P(sol=1|K) = Bin(K;d,p) / [Bin(K;d,p)+Bin(K;d,q)]
       If K < d/2: x̂=0. P(correct|K) = P(sol=0|K) = Bin(K;d,q) / [Bin(K;d,p)+Bin(K;d,q)]
       If K = d/2: P(correct) = 0.5

       P(wrong|K) = 1 - P(correct|K)
    */

    double e_t_wrong = 0; /* E[|tension| | wrong] */
    double e_t_right = 0;
    double p_wrong_total = 0;
    double p_right_total = 0;

    printf("  K | |tension| | P(K)   | P(cor|K) | P(wrong|K)\n");
    printf("  --+----------+--------+----------+-----------\n");

    for(int k=0; k<=d; k++){
        double sigma = fabs(2.0*k/d - 1.0);

        /* P(K=k) = 1/2 [Bin(k;d,p) + Bin(k;d,q)] */
        double binom_p = 1, binom_q = 1;
        /* Compute binomial coefficients properly */
        double log_comb = 0;
        for(int i=1;i<=k;i++) log_comb += log(d-i+1) - log(i);

        binom_p = exp(log_comb + k*log(p) + (d-k)*log(1-p));
        binom_q = exp(log_comb + k*log(q) + (d-k)*log(1-q));

        double pk = 0.5 * (binom_p + binom_q);

        /* P(correct | K) */
        double p_correct;
        if(2*k > d){
            /* x̂ = 1. P(correct) = P(sol=1|K) = Bin(K;d,p) / [Bin(K;d,p)+Bin(K;d,q)] */
            p_correct = binom_p / (binom_p + binom_q);
        } else if(2*k < d){
            /* x̂ = 0. P(correct) = P(sol=0|K) = Bin(K;d,q) / [Bin(K;d,p)+Bin(K;d,q)] */
            p_correct = binom_q / (binom_p + binom_q);
        } else {
            p_correct = 0.5;
        }

        double p_wrong = 1 - p_correct;

        printf("  %2d |   %.3f   | %.4f | %.4f   | %.4f\n",
               k, sigma, pk, p_correct, p_wrong);

        e_t_wrong += sigma * p_wrong * pk;
        e_t_right += sigma * p_correct * pk;
        p_wrong_total += p_wrong * pk;
        p_right_total += p_correct * pk;
    }

    /* Normalize */
    e_t_wrong /= p_wrong_total;
    e_t_right /= p_right_total;

    printf("\n  ═══ PREDICTION FROM SELECTION EFFECT ═══\n\n");
    printf("  E[|tension| | wrong] = %.4f\n", e_t_wrong);
    printf("  E[|tension| | right] = %.4f\n", e_t_right);
    printf("  Predicted ratio = %.4f\n", e_t_wrong / e_t_right);
    printf("\n  MEASURED ratios:\n");
    printf("    n=12: 0.743\n");
    printf("    n=14: 0.742\n");
    printf("    n=16: 0.757\n");
    printf("    n=18: 0.660\n");
    printf("\n  Does selection effect EXPLAIN the anomaly?\n");
    double predicted_ratio = e_t_wrong / e_t_right;
    if(fabs(predicted_ratio - 0.74) < 0.10)
        printf("  → YES! Predicted %.3f ≈ measured 0.74. SELECTION EFFECT.\n",predicted_ratio);
    else
        printf("  → NO. Predicted %.3f ≠ measured 0.74. Something ELSE.\n",predicted_ratio);

    printf("\n  P(wrong overall) = %.4f\n", p_wrong_total);
    printf("  = 1 - accuracy = 1 - %.4f = %.4f\n",
           p_right_total, 1-p_right_total);

    return 0;
}
