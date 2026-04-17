/*
 * omega3_full.c — Full-amplification Ω_3 computation.
 *
 * Computes chain_3(b) for ALL 256 output bits in one pass over the
 * C(256,3) = 2,763,520 state1 triples. Returns direct_z[256],
 * chain_z[256], and Ω_3 = corr(direct_z, chain_z).
 *
 * Amortization: chi_S = s1[a] ^ s1[b] ^ s1[c] computed once per triple,
 * then XOR-popcount'd against 257 targets (fa + 256 state2 bits).
 * ≈ 100× speedup vs calling chain3 256 times.
 *
 * Input binary format:
 *   uint64_t N
 *   uint64_t state1[256][WORDS]   // bit-packed state1
 *   uint64_t fa[WORDS]            // bit-packed input feature
 *   uint64_t state2[256][WORDS]   // bit-packed state2 target bits
 *
 * Output: JSON with direct_z[256], chain_z[256], omega3, same_sign.
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
    int stride = (argc > 2) ? atoi(argv[2]) : 1;
    if (stride < 1) stride = 1;
    FILE *fp = infile ? fopen(infile, "rb") : stdin;
    if (!fp) { fprintf(stderr, "open fail\n"); return 2; }
    fprintf(stderr, "stride = %d (1 = full enum, >1 = subsample)\n", stride);

    uint64_t N;
    if (fread(&N, sizeof(N), 1, fp) != 1) return 3;

    uint64_t *state1 = malloc((size_t)NBITS * WORDS * sizeof(uint64_t));
    uint64_t *fa     = malloc(WORDS * sizeof(uint64_t));
    uint64_t *state2 = malloc((size_t)NBITS * WORDS * sizeof(uint64_t));
    if (!state1 || !fa || !state2) { fprintf(stderr, "alloc\n"); return 5; }

    if (fread(state1, sizeof(uint64_t), (size_t)NBITS * WORDS, fp) != (size_t)NBITS * WORDS) return 6;
    if (fread(fa,     sizeof(uint64_t), WORDS,                    fp) != WORDS)               return 7;
    if (fread(state2, sizeof(uint64_t), (size_t)NBITS * WORDS, fp) != (size_t)NBITS * WORDS) return 8;
    if (fp != stdin) fclose(fp);

    const double sqrt_N = sqrt((double)N);
    const double inv_sqrt_N = 1.0 / sqrt_N;

    /* Precompute z-score of each state2 bit vs fa: direct_z(b) */
    double direct_z[NBITS];
    for (int b = 0; b < NBITS; b++) {
        const uint64_t *S2b = state2 + (size_t)b * WORDS;
        long eq = 0;
        for (int w = 0; w < WORDS; w++) {
            /* bits where fa XOR state2[b] = 0 → equal */
            eq += __builtin_popcountll(~(fa[w] ^ S2b[w]));
        }
        /* Adjust for WORDS*64 total bits vs N */
        /* Since we pad with zeros: 0 XOR 0 = 0, so ~(0^0)=~0 gives 64 equal bits per pad word. */
        /* Total padded bits = WORDS*64. The trailing (WORDS*64 - N) bits must be excluded. */
        long padding = WORDS * 64 - (long)N;
        eq -= padding;  /* trailing zeros all counted as equal, subtract them */
        /* direct_z = sqrt(N) * (2*eq/N - 1) */
        direct_z[b] = sqrt_N * (2.0 * (double)eq / (double)N - 1.0);
    }

    /* chain_z accumulator */
    double chain_z[NBITS];
    for (int b = 0; b < NBITS; b++) chain_z[b] = 0.0;

    /* Chi buffer */
    uint64_t *chi = malloc(WORDS * sizeof(uint64_t));

    long n_triples = 0;
    long n_triples_visited = 0;
    long padding = WORDS * 64 - (long)N;

    fprintf(stderr, "Starting triple enumeration (stride=%d)...\n", stride);

    /* Allocate chi_abc reuse buffer */
    uint64_t *chi_abc = malloc(WORDS * sizeof(uint64_t));

    for (int a = 0; a < NBITS - 2; a++) {
        const uint64_t *Sa = state1 + (size_t)a * WORDS;
        if (a % 8 == 0) {
            fprintf(stderr, "  a=%d/%d, triples=%ld\r", a, NBITS - 2, n_triples);
            fflush(stderr);
        }
        for (int b = a + 1; b < NBITS - 1; b++) {
            const uint64_t *Sb = state1 + (size_t)b * WORDS;
            /* pairwise XOR */
            uint64_t *chi_ab = chi;
            for (int w = 0; w < WORDS; w++) chi_ab[w] = Sa[w] ^ Sb[w];

            for (int c = b + 1; c < NBITS; c++) {
                /* Subsample via stride */
                if (stride > 1 && (n_triples_visited++ % stride) != 0) continue;

                const uint64_t *Sc = state1 + (size_t)c * WORDS;
                /* Compute chi_abc once */
                for (int w = 0; w < WORDS; w++) chi_abc[w] = chi_ab[w] ^ Sc[w];

                /* z_in = sqrt(N) * (1 - 2*<chi, fa>/N) */
                long ne = 0;
                for (int w = 0; w < WORDS; w++) {
                    ne += __builtin_popcountll(chi_abc[w] ^ fa[w]);
                }
                double z_in = sqrt_N * (1.0 - 2.0 * (double)ne / (double)N);

                /* For each target: z_out */
                for (int bt = 0; bt < NBITS; bt++) {
                    const uint64_t *S2 = state2 + (size_t)bt * WORDS;
                    long ne2 = 0;
                    for (int w = 0; w < WORDS; w++) {
                        ne2 += __builtin_popcountll(chi_abc[w] ^ S2[w]);
                    }
                    double z_out = sqrt_N * (1.0 - 2.0 * (double)ne2 / (double)N);
                    chain_z[bt] += z_in * z_out * inv_sqrt_N;
                }
                n_triples++;
            }
        }
    }
    fprintf(stderr, "\nDone. %ld triples processed (of %ld visited).\n",
            n_triples, n_triples_visited);

    /* Scale chain_z if we sampled: compensate for missing triples */
    if (stride > 1) {
        double scale = (double)stride;
        for (int b = 0; b < NBITS; b++) chain_z[b] *= scale;
    }
    free(chi_abc);

    /* Compute Omega_3 = Pearson(direct_z, chain_z) */
    double sum_d = 0, sum_c = 0;
    for (int b = 0; b < NBITS; b++) { sum_d += direct_z[b]; sum_c += chain_z[b]; }
    double mean_d = sum_d / NBITS, mean_c = sum_c / NBITS;
    double var_d = 0, var_c = 0, cov = 0;
    int same_sign = 0;
    for (int b = 0; b < NBITS; b++) {
        double dd = direct_z[b] - mean_d;
        double dc = chain_z[b] - mean_c;
        var_d += dd * dd; var_c += dc * dc; cov += dd * dc;
        if ((direct_z[b] >= 0) == (chain_z[b] >= 0)) same_sign++;
    }
    double omega3 = (var_d > 0 && var_c > 0) ? cov / sqrt(var_d * var_c) : 0.0;

    /* JSON output */
    printf("{\"N\":%ld,\"n_triples\":%ld,\"omega3\":%.6f,\"same_sign\":%d,\"total_bits\":%d,\n",
           (long)N, n_triples, omega3, same_sign, NBITS);
    printf("\"direct_z\":[");
    for (int b = 0; b < NBITS; b++) printf("%s%.4f", b ? "," : "", direct_z[b]);
    printf("],\n\"chain_z\":[");
    for (int b = 0; b < NBITS; b++) printf("%s%.4f", b ? "," : "", chain_z[b]);
    printf("]}\n");

    free(state1); free(fa); free(state2); free(chi);
    return 0;
}
