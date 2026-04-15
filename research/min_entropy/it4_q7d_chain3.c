/*
 * IT-4.Q7d: Walsh-3 CHAIN test (surgical amplification).
 *
 * For each triple (a, b, c) of state1 bit indices, compute TWO z-scores:
 *   z_in(a,b,c)  = corr of (s1_a ^ s1_b ^ s1_c) with feature f (bit5_max)
 *   z_out(a,b,c) = corr of (s1_a ^ s1_b ^ s1_c) with output target t (state2[bit 10])
 *
 * Chain contribution to final signal:
 *   chain_sum = (1/sqrt(N)) * Σ z_in * z_out
 *
 * Under Parseval, if we sum over ALL Walsh coefficients (|S| from 0 to 256),
 * we recover <f, t> * sqrt(N) exactly. Our partial sum over |S|=3 measures
 * how much of the observed signal lies in 3rd-order Walsh structure.
 *
 * Also report:
 *   - top-K triples by |z_in * z_out|
 *   - count of triples where both |z_in| > 2 AND |z_out| > 2
 *
 * Input binary format:
 *   uint64_t N
 *   uint64_t state1[256][WORDS]
 *   uint64_t f_mask[WORDS]       -- input feature (bit5_max)
 *   uint64_t t_mask[WORDS]       -- output target (state2[bit 10])
 *
 * Output: JSON on stdout.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <string.h>

#define NBITS 256
#define WORDS 2048
#define TOPK 50

int main(int argc, char **argv) {
    const char *infile = (argc > 1) ? argv[1] : NULL;
    FILE *fp = infile ? fopen(infile, "rb") : stdin;
    if (!fp) { fprintf(stderr, "open\n"); return 2; }

    uint64_t N;
    if (fread(&N, sizeof(N), 1, fp) != 1) return 3;

    uint64_t *state1 = malloc((size_t)NBITS * WORDS * sizeof(uint64_t));
    uint64_t *f_mask = malloc(WORDS * sizeof(uint64_t));
    uint64_t *t_mask = malloc(WORDS * sizeof(uint64_t));
    if (!state1 || !f_mask || !t_mask) return 5;

    if (fread(state1, sizeof(uint64_t), (size_t)NBITS * WORDS, fp) != (size_t)NBITS * WORDS) return 6;
    if (fread(f_mask, sizeof(uint64_t), WORDS, fp) != WORDS) return 7;
    if (fread(t_mask, sizeof(uint64_t), WORDS, fp) != WORDS) return 7;
    if (fp != stdin) fclose(fp);

    const double sqrt_N = sqrt((double)N);
    const double inv_sqrt_N = 1.0 / sqrt_N;

    /* Global maxima */
    double max_abs_zin = 0, max_abs_zout = 0, max_abs_prod = 0;
    int   best_prod_a = 0, best_prod_b = 0, best_prod_c = 0;
    double best_prod_zin = 0, best_prod_zout = 0;

    double chain_sum = 0.0;
    long n_triples = 0;
    long n_both_gt_2 = 0, n_both_gt_3 = 0;

    /* Top-K by |z_in * z_out| */
    double top_prod[TOPK];
    double top_zin[TOPK], top_zout[TOPK];
    int top_a[TOPK], top_b[TOPK], top_c[TOPK];
    for (int i = 0; i < TOPK; i++) { top_prod[i] = 0; top_a[i] = -1; }
    int min_slot = 0; double min_slot_abs = 0;

    uint64_t *xor_ab = malloc(WORDS * sizeof(uint64_t));

    for (int a = 0; a < NBITS - 2; a++) {
        const uint64_t *Ma = state1 + (size_t)a * WORDS;
        if (a % 16 == 0) fprintf(stderr, "a=%d/%d\r", a, NBITS - 2);

        for (int b = a + 1; b < NBITS - 1; b++) {
            const uint64_t *Mb = state1 + (size_t)b * WORDS;
            for (int i = 0; i < WORDS; i++) xor_ab[i] = Ma[i] ^ Mb[i];

            for (int c = b + 1; c < NBITS; c++) {
                const uint64_t *Mc = state1 + (size_t)c * WORDS;

                int pop_in = 0, pop_out = 0;
                for (int i = 0; i < WORDS; i++) {
                    uint64_t triple = xor_ab[i] ^ Mc[i];
                    pop_in  += __builtin_popcountll(triple ^ f_mask[i]);
                    pop_out += __builtin_popcountll(triple ^ t_mask[i]);
                }
                double walsh_in  = 1.0 - 2.0 * (double)pop_in  / (double)N;
                double walsh_out = 1.0 - 2.0 * (double)pop_out / (double)N;
                double z_in  = walsh_in  * sqrt_N;
                double z_out = walsh_out * sqrt_N;
                double prod  = z_in * z_out;

                chain_sum += prod * inv_sqrt_N;
                n_triples++;

                double ai = fabs(z_in), ao = fabs(z_out);
                if (ai > max_abs_zin)   max_abs_zin  = ai;
                if (ao > max_abs_zout)  max_abs_zout = ao;
                if (ai > 2.0 && ao > 2.0) n_both_gt_2++;
                if (ai > 3.0 && ao > 3.0) n_both_gt_3++;

                double ap = fabs(prod);
                if (ap > max_abs_prod) {
                    max_abs_prod = ap;
                    best_prod_a = a; best_prod_b = b; best_prod_c = c;
                    best_prod_zin = z_in; best_prod_zout = z_out;
                }

                /* maintain top-K by |prod| */
                if (ap > min_slot_abs) {
                    top_prod[min_slot] = prod;
                    top_zin[min_slot] = z_in;
                    top_zout[min_slot] = z_out;
                    top_a[min_slot] = a; top_b[min_slot] = b; top_c[min_slot] = c;
                    min_slot_abs = fabs(top_prod[0]); min_slot = 0;
                    for (int k = 1; k < TOPK; k++) {
                        double ap2 = fabs(top_prod[k]);
                        if (ap2 < min_slot_abs) { min_slot_abs = ap2; min_slot = k; }
                    }
                }
            }
        }
    }
    fprintf(stderr, "\n");

    /* sort top-K descending by |prod| */
    for (int i = 0; i < TOPK; i++)
        for (int j = i + 1; j < TOPK; j++)
            if (fabs(top_prod[j]) > fabs(top_prod[i])) {
                double t;
                t = top_prod[i]; top_prod[i] = top_prod[j]; top_prod[j] = t;
                t = top_zin[i]; top_zin[i] = top_zin[j]; top_zin[j] = t;
                t = top_zout[i]; top_zout[i] = top_zout[j]; top_zout[j] = t;
                int ti;
                ti = top_a[i]; top_a[i] = top_a[j]; top_a[j] = ti;
                ti = top_b[i]; top_b[i] = top_b[j]; top_b[j] = ti;
                ti = top_c[i]; top_c[i] = top_c[j]; top_c[j] = ti;
            }

    /* Also measure direct <f, t> * sqrt(N) as reference */
    int pop_direct = 0;
    for (int i = 0; i < WORDS; i++) pop_direct += __builtin_popcountll(f_mask[i] ^ t_mask[i]);
    double direct_walsh = 1.0 - 2.0 * (double)pop_direct / (double)N;
    double direct_z = direct_walsh * sqrt_N;

    printf("{\n");
    printf("  \"N\": %lu,\n", N);
    printf("  \"n_triples\": %ld,\n", n_triples);
    printf("  \"max_abs_zin\": %.6f,\n", max_abs_zin);
    printf("  \"max_abs_zout\": %.6f,\n", max_abs_zout);
    printf("  \"max_abs_prod\": %.6f,\n", max_abs_prod);
    printf("  \"best_prod\": {\"a\": %d, \"b\": %d, \"c\": %d, \"zin\": %.6f, \"zout\": %.6f, \"prod\": %.6f},\n",
           best_prod_a, best_prod_b, best_prod_c, best_prod_zin, best_prod_zout, best_prod_zin*best_prod_zout);
    printf("  \"chain_sum\": %.6f,\n", chain_sum);
    printf("  \"direct_signal_z\": %.6f,\n", direct_z);
    printf("  \"chain_fraction\": %.6f,\n", (fabs(direct_z) > 1e-9) ? chain_sum / direct_z : 0.0);
    printf("  \"n_both_gt_2\": %ld,\n", n_both_gt_2);
    printf("  \"n_both_gt_3\": %ld,\n", n_both_gt_3);
    printf("  \"top_k\": [\n");
    for (int i = 0; i < TOPK; i++) {
        if (top_a[i] < 0) continue;
        printf("    {\"a\": %d, \"b\": %d, \"c\": %d, \"zin\": %.4f, \"zout\": %.4f, \"prod\": %.4f}%s\n",
               top_a[i], top_b[i], top_c[i], top_zin[i], top_zout[i], top_prod[i],
               (i + 1 < TOPK && top_a[i+1] >= 0) ? "," : "");
    }
    printf("  ]\n");
    printf("}\n");

    free(xor_ab); free(state1); free(f_mask); free(t_mask);
    return 0;
}
