/*
 * IT-4.Q7f: Walsh-4 CHAIN test.
 *
 * For each 4-tuple (a, b, c, d) in C(256, 4) = 174,792,640, compute
 *   z_in  = sqrt(N) * <(s1_a ^ s1_b ^ s1_c ^ s1_d), f_in>
 *   z_out = sqrt(N) * <(same), f_out>
 * chain_sum = (1/sqrt(N)) * Σ z_in * z_out
 *
 * If chain_4 shows significant z vs RO, 4th-order subspace also carries
 * signal. Compare to chain_3 (Q7d): z = -3.83 there. If z ~ 0 at 4th
 * order, 3rd is the dominant carrier. If z > 3 too, signal is spread
 * across multiple orders.
 *
 * Same input binary format as Q7d.
 * Expected runtime: 174M / 2.76M * 2.4s ≈ 150s per realization.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <string.h>

#define NBITS 256
#define WORDS 2048

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

    double max_abs_zin = 0, max_abs_zout = 0, max_abs_prod = 0;
    int best_a = 0, best_b = 0, best_c = 0, best_d = 0;
    double best_zin = 0, best_zout = 0;

    double chain_sum = 0.0;
    long n_quads = 0;
    long n_both_gt_2 = 0, n_both_gt_3 = 0;

    uint64_t *xor_ab = malloc(WORDS * sizeof(uint64_t));
    uint64_t *xor_abc = malloc(WORDS * sizeof(uint64_t));

    for (int a = 0; a < NBITS - 3; a++) {
        const uint64_t *Ma = state1 + (size_t)a * WORDS;
        fprintf(stderr, "a=%d/%d  chain=%.2f  n=%ld\n", a, NBITS - 3, chain_sum, n_quads);

        for (int b = a + 1; b < NBITS - 2; b++) {
            const uint64_t *Mb = state1 + (size_t)b * WORDS;
            for (int i = 0; i < WORDS; i++) xor_ab[i] = Ma[i] ^ Mb[i];

            for (int c = b + 1; c < NBITS - 1; c++) {
                const uint64_t *Mc = state1 + (size_t)c * WORDS;
                for (int i = 0; i < WORDS; i++) xor_abc[i] = xor_ab[i] ^ Mc[i];

                for (int d = c + 1; d < NBITS; d++) {
                    const uint64_t *Md = state1 + (size_t)d * WORDS;
                    int pop_in = 0, pop_out = 0;
                    for (int i = 0; i < WORDS; i++) {
                        uint64_t quad = xor_abc[i] ^ Md[i];
                        pop_in  += __builtin_popcountll(quad ^ f_mask[i]);
                        pop_out += __builtin_popcountll(quad ^ t_mask[i]);
                    }
                    double walsh_in  = 1.0 - 2.0 * (double)pop_in  / (double)N;
                    double walsh_out = 1.0 - 2.0 * (double)pop_out / (double)N;
                    double z_in  = walsh_in  * sqrt_N;
                    double z_out = walsh_out * sqrt_N;
                    double prod  = z_in * z_out;

                    chain_sum += prod * inv_sqrt_N;
                    n_quads++;

                    double ai = fabs(z_in), ao = fabs(z_out);
                    if (ai > max_abs_zin)   max_abs_zin  = ai;
                    if (ao > max_abs_zout)  max_abs_zout = ao;
                    if (ai > 2.0 && ao > 2.0) n_both_gt_2++;
                    if (ai > 3.0 && ao > 3.0) n_both_gt_3++;

                    double ap = fabs(prod);
                    if (ap > max_abs_prod) {
                        max_abs_prod = ap;
                        best_a = a; best_b = b; best_c = c; best_d = d;
                        best_zin = z_in; best_zout = z_out;
                    }
                }
            }
        }
    }
    fprintf(stderr, "\n");

    /* Direct <f,t> * sqrt(N) */
    int pop_direct = 0;
    for (int i = 0; i < WORDS; i++) pop_direct += __builtin_popcountll(f_mask[i] ^ t_mask[i]);
    double direct_walsh = 1.0 - 2.0 * (double)pop_direct / (double)N;
    double direct_z = direct_walsh * sqrt_N;

    printf("{\n");
    printf("  \"N\": %lu,\n", N);
    printf("  \"n_quads\": %ld,\n", n_quads);
    printf("  \"max_abs_zin\": %.6f,\n", max_abs_zin);
    printf("  \"max_abs_zout\": %.6f,\n", max_abs_zout);
    printf("  \"max_abs_prod\": %.6f,\n", max_abs_prod);
    printf("  \"best_prod\": {\"a\": %d, \"b\": %d, \"c\": %d, \"d\": %d, \"zin\": %.6f, \"zout\": %.6f, \"prod\": %.6f},\n",
           best_a, best_b, best_c, best_d, best_zin, best_zout, best_zin*best_zout);
    printf("  \"chain_sum\": %.6f,\n", chain_sum);
    printf("  \"direct_signal_z\": %.6f,\n", direct_z);
    printf("  \"chain_fraction\": %.6f,\n", (fabs(direct_z) > 1e-9) ? chain_sum / direct_z : 0.0);
    printf("  \"n_both_gt_2\": %ld,\n", n_both_gt_2);
    printf("  \"n_both_gt_3\": %ld\n", n_both_gt_3);
    printf("}\n");

    free(xor_ab); free(xor_abc); free(state1); free(f_mask); free(t_mask);
    return 0;
}
