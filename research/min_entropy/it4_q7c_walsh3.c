/*
 * IT-4.Q7c: 3rd-order Walsh scan for SHA-256 state1 vs bit5_max feature.
 *
 * For all C(256, 3) = 2,763,520 triples (a, b, c) with a < b < c < 256,
 * compute:
 *   z(a,b,c) = sqrt(N) * (1/N) * sum_x (-1)^(f(x) XOR s1_a(x) XOR s1_b(x) XOR s1_c(x))
 *
 * Equivalent: popcount of (mask_a XOR mask_b XOR mask_c XOR mask_f) counts
 * inputs where the XOR of all four bits is 1 (i.e., they disagree).
 *   walsh = 1 - 2*pop/N
 *   z = walsh * sqrt(N) = (N - 2*pop) / sqrt(N)
 *
 * Input binary format (stdin or file):
 *   uint64_t N                   -- number of inputs
 *   uint64_t state1[256][WORDS]  -- state1 bit-packed, bit i of mask[b] = state1[i][b]
 *   uint64_t f_mask[WORDS]       -- feature bit-packed, bit i = f[i]
 * WORDS = ceil(N_max / 64). We fix N_max = 131072 → WORDS = 2048.
 *
 * Output: JSON on stdout with max_abs_z, best triple, sum_z2, top-K triples.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <string.h>

#define NBITS 256
#define WORDS 2048          /* 2048 * 64 = 131072 bits, holds N up to that */
#define TOPK 50

static inline int popcount_buf(const uint64_t *restrict buf, int nwords) {
    int c = 0;
    for (int i = 0; i < nwords; i++) c += __builtin_popcountll(buf[i]);
    return c;
}

int main(int argc, char **argv) {
    const char *infile = (argc > 1) ? argv[1] : NULL;
    FILE *fp = infile ? fopen(infile, "rb") : stdin;
    if (!fp) { fprintf(stderr, "cannot open %s\n", infile); return 2; }

    uint64_t N;
    if (fread(&N, sizeof(N), 1, fp) != 1) { fprintf(stderr, "read N\n"); return 3; }

    if (N > (uint64_t)WORDS * 64) {
        fprintf(stderr, "N=%lu exceeds WORDS*64=%d\n", N, WORDS * 64);
        return 4;
    }

    uint64_t *state1 = malloc((size_t)NBITS * WORDS * sizeof(uint64_t));
    uint64_t *f_mask = malloc(WORDS * sizeof(uint64_t));
    if (!state1 || !f_mask) { fprintf(stderr, "malloc\n"); return 5; }

    if (fread(state1, sizeof(uint64_t), (size_t)NBITS * WORDS, fp) != (size_t)NBITS * WORDS) {
        fprintf(stderr, "read state1\n"); return 6;
    }
    if (fread(f_mask, sizeof(uint64_t), WORDS, fp) != WORDS) {
        fprintf(stderr, "read f_mask\n"); return 7;
    }
    if (fp != stdin) fclose(fp);

    const double sqrt_N = sqrt((double)N);

    double max_abs_z = 0.0, best_z = 0.0;
    int best_a = 0, best_b = 0, best_c = 0;
    double sum_z2 = 0.0;
    long n_triples = 0;
    long n_above_5 = 0, n_above_4 = 0, n_above_3 = 0;

    /* top-K tracker (unsorted, maintains min slot) */
    double top_z[TOPK];
    int top_a[TOPK], top_b[TOPK], top_c[TOPK];
    for (int i = 0; i < TOPK; i++) {
        top_z[i] = 0.0; top_a[i] = top_b[i] = top_c[i] = -1;
    }
    int min_slot = 0;
    double min_slot_abs = 0.0;

    uint64_t *xor_ab = malloc(WORDS * sizeof(uint64_t));
    if (!xor_ab) { fprintf(stderr, "malloc xor_ab\n"); return 8; }

    for (int a = 0; a < NBITS - 2; a++) {
        const uint64_t *Ma = state1 + (size_t)a * WORDS;
        if (a % 16 == 0) fprintf(stderr, "a=%d/%d\r", a, NBITS - 2);

        for (int b = a + 1; b < NBITS - 1; b++) {
            const uint64_t *Mb = state1 + (size_t)b * WORDS;
            for (int i = 0; i < WORDS; i++) xor_ab[i] = Ma[i] ^ Mb[i];

            for (int c = b + 1; c < NBITS; c++) {
                const uint64_t *Mc = state1 + (size_t)c * WORDS;
                int pop = 0;
                for (int i = 0; i < WORDS; i++) {
                    uint64_t v = xor_ab[i] ^ Mc[i] ^ f_mask[i];
                    pop += __builtin_popcountll(v);
                }
                /* walsh = 1 - 2*pop/N ; z = walsh * sqrt(N) */
                double walsh = 1.0 - 2.0 * (double)pop / (double)N;
                double z = walsh * sqrt_N;
                double absz = z < 0 ? -z : z;

                sum_z2 += z * z;
                n_triples++;
                if (absz > 3.0) n_above_3++;
                if (absz > 4.0) n_above_4++;
                if (absz > 5.0) n_above_5++;

                if (absz > max_abs_z) {
                    max_abs_z = absz; best_z = z;
                    best_a = a; best_b = b; best_c = c;
                }

                /* maintain top-K: insert if |z| > current min_slot */
                if (absz > min_slot_abs) {
                    top_z[min_slot] = z;
                    top_a[min_slot] = a; top_b[min_slot] = b; top_c[min_slot] = c;
                    /* find new min */
                    min_slot_abs = fabs(top_z[0]); min_slot = 0;
                    for (int k = 1; k < TOPK; k++) {
                        double az = fabs(top_z[k]);
                        if (az < min_slot_abs) { min_slot_abs = az; min_slot = k; }
                    }
                }
            }
        }
    }
    fprintf(stderr, "\n");

    /* sort top-K descending by |z| */
    for (int i = 0; i < TOPK; i++)
        for (int j = i + 1; j < TOPK; j++)
            if (fabs(top_z[j]) > fabs(top_z[i])) {
                double tz = top_z[i]; top_z[i] = top_z[j]; top_z[j] = tz;
                int ta = top_a[i]; top_a[i] = top_a[j]; top_a[j] = ta;
                int tb = top_b[i]; top_b[i] = top_b[j]; top_b[j] = tb;
                int tc = top_c[i]; top_c[i] = top_c[j]; top_c[j] = tc;
            }

    /* JSON output */
    printf("{\n");
    printf("  \"N\": %lu,\n", N);
    printf("  \"n_triples\": %ld,\n", n_triples);
    printf("  \"max_abs_z\": %.6f,\n", max_abs_z);
    printf("  \"best_z\": %.6f,\n", best_z);
    printf("  \"best_triple\": [%d, %d, %d],\n", best_a, best_b, best_c);
    printf("  \"sum_z2\": %.6f,\n", sum_z2);
    printf("  \"n_above_3\": %ld,\n", n_above_3);
    printf("  \"n_above_4\": %ld,\n", n_above_4);
    printf("  \"n_above_5\": %ld,\n", n_above_5);
    printf("  \"top_k\": [\n");
    for (int i = 0; i < TOPK; i++) {
        if (top_a[i] < 0) continue;
        printf("    {\"a\": %d, \"b\": %d, \"c\": %d, \"z\": %.6f}%s\n",
               top_a[i], top_b[i], top_c[i], top_z[i],
               (i + 1 < TOPK && top_a[i+1] >= 0) ? "," : "");
    }
    printf("  ]\n");
    printf("}\n");

    free(xor_ab);
    free(state1);
    free(f_mask);
    return 0;
}
