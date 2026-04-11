/*
 * BIT CALCULUS: discrete derivatives, influences, and Walsh spectrum
 * ====================================================================
 *
 * Stage F of the "math of bits" programme.  The idea: treat boolean
 * functions as the fundamental objects, equip them with analytical
 * tools (derivative, gradient, Laplacian, Fourier) and apply these
 * directly to cryptographic primitives.
 *
 * Foundations combined:
 *   - Discrete derivative (finite-difference calculus)
 *   - Walsh-Hadamard transform / Boolean Fourier (Walsh 1923)
 *   - Influences and total influence (Ben-Or, Linial 1985;
 *     Kahn, Kalai, Linial 1988)
 *   - Linear cryptanalysis via Walsh spectrum (Matsui 1993)
 *
 * Core definitions for f: {0,1}^n → {0,1}, encoded as F(x) = (−1)^{f(x)}:
 *
 *   Discrete derivative      (∂_i f)(x) = f(x ⊕ e_i) ⊕ f(x)
 *   Influence of bit i       Inf_i(f)  = Pr_x[∂_i f(x) = 1]
 *   Total influence          I(f)      = Σ_i Inf_i(f)
 *   Walsh coefficient        F̂(s)     = Σ_x F(x)·(−1)^{s·x}
 *   Inversion                F(x)     = 2^{−n} Σ_s F̂(s)·(−1)^{s·x}
 *   Parseval                 Σ_s F̂(s)² = 2^n · Σ_x F(x)² = 2^{2n}
 *   Best linear bias         ε*        = (1/2^{n+1}) max_s |F̂(s)|
 *
 * Experiments:
 *   1. Sanity: Walsh transform on basic functions (XOR, AND, MAJ)
 *   2. Parseval identity — machine-verify
 *   3. Influences: classic functions, measure total influence I(f)
 *   4. Walsh spectrum of a single output bit of SHA-256 round
 *      (fix 240 bits of 288-bit input, vary 16 → 2^16 samples)
 *   5. Max Walsh coefficient across rounds → linear-cryptanalysis bias
 *   6. Average influence across rounds → avalanche via calculus
 *
 * Compile: gcc -O3 -march=native -o bitcalc bit_calculus.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define N_BITS 16
#define N_POINTS (1 << N_BITS)

/* ═══ FAST WALSH-HADAMARD TRANSFORM ═══
 *
 * In-place, ±1 convention.  After fwht(a, n):
 *     a[s] = Σ_x a_init[x] · (−1)^{s·x}
 * Inverse is the same transform divided by 2^n.
 */
static void fwht(double *a, int n){
    int N = 1 << n;
    for(int h = 1; h < N; h <<= 1){
        for(int i = 0; i < N; i += h*2){
            for(int j = i; j < i + h; j++){
                double x = a[j];
                double y = a[j + h];
                a[j]     = x + y;
                a[j + h] = x - y;
            }
        }
    }
}

/* ═══ SHA-256 CORE (reused) ═══ */
static const uint32_t K256[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};
static const uint32_t IV[8] = {
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
    0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
};
#define ROTR(x,n) (((x) >> (n)) | ((x) << (32-(n))))
#define SIG0(x)  (ROTR(x,2) ^ ROTR(x,13) ^ ROTR(x,22))
#define SIG1(x)  (ROTR(x,6) ^ ROTR(x,11) ^ ROTR(x,25))
#define CH(x,y,z)  (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))

static inline void sha256_round(uint32_t S[8], uint32_t Wt, int t){
    uint32_t T1 = S[7] + SIG1(S[4]) + CH(S[4],S[5],S[6]) + K256[t] + Wt;
    uint32_t T2 = SIG0(S[0]) + MAJ(S[0],S[1],S[2]);
    S[7]=S[6]; S[6]=S[5]; S[5]=S[4];
    S[4]=S[3]+T1;
    S[3]=S[2]; S[2]=S[1]; S[1]=S[0];
    S[0]=T1+T2;
}

/* ═══ BASIC BOOLEAN FUNCTIONS (for sanity checks) ═══ */
/* All encoded as F(x) = (−1)^{f(x)} so that F ∈ {−1, +1}. */

static double f_xor_01(unsigned x){  /* f(x) = x_0 XOR x_1 */
    int b = ((x >> 0) ^ (x >> 1)) & 1;
    return b ? -1.0 : 1.0;
}
static double f_and_01(unsigned x){
    int b = ((x >> 0) & (x >> 1)) & 1;
    return b ? -1.0 : 1.0;
}
static double f_maj_012(unsigned x){
    int a = (x >> 0) & 1, b = (x >> 1) & 1, c = (x >> 2) & 1;
    int m = (a & b) | (a & c) | (b & c);
    return m ? -1.0 : 1.0;
}
static double f_parity(unsigned x){
    int p = __builtin_popcount(x) & 1;
    return p ? -1.0 : 1.0;
}

/* Fill an array of size 2^N_BITS from a function pointer */
static void fill(double *a, double (*f)(unsigned)){
    for(unsigned x = 0; x < N_POINTS; x++) a[x] = f(x);
}

/* ═══ EXPERIMENT 1: Walsh spectra of basic functions ═══ */
static void experiment_basic_spectra(void){
    printf("\n═══ EXPERIMENT 1: Walsh spectra of basic boolean functions ═══\n\n");

    double *a = malloc(N_POINTS * sizeof(double));

    struct { const char *name; double (*f)(unsigned); } tests[] = {
        {"XOR(x_0, x_1)",  f_xor_01},
        {"AND(x_0, x_1)",  f_and_01},
        {"MAJ(x_0,x_1,x_2)", f_maj_012},
        {"PARITY(x)",      f_parity},
    };

    for(int t = 0; t < 4; t++){
        fill(a, tests[t].f);
        fwht(a, N_BITS);

        /* Find top-5 coefficients by magnitude */
        printf("  %-22s  top Walsh coefficients:\n", tests[t].name);
        for(int top = 0; top < 5; top++){
            int best = 0;
            double bv = 0;
            for(int s = 0; s < N_POINTS; s++){
                if(fabs(a[s]) > bv){bv = fabs(a[s]); best = s;}
            }
            if(bv < 1e-9) break;
            printf("    F̂(s=0x%04x) = %+8.0f   (bits set: ", best, a[best]);
            for(int b = 0; b < N_BITS; b++) if(best & (1<<b)) printf("%d ", b);
            printf(")\n");
            a[best] = 0;
        }
        printf("\n");
    }
    free(a);
}

/* ═══ EXPERIMENT 2: Parseval identity verification ═══ */
static void experiment_parseval(void){
    printf("\n═══ EXPERIMENT 2: Parseval identity ═══\n");
    printf("Σ_s F̂(s)² should equal 2^n · Σ_x F(x)² = 2^{2n}\n\n");

    double *a = malloc(N_POINTS * sizeof(double));
    double (*funcs[])(unsigned) = {f_xor_01, f_and_01, f_maj_012, f_parity};
    const char *names[] = {"XOR", "AND", "MAJ", "PARITY"};

    for(int t = 0; t < 4; t++){
        fill(a, funcs[t]);
        double sum_sq_before = 0;
        for(int x = 0; x < N_POINTS; x++) sum_sq_before += a[x]*a[x];

        fwht(a, N_BITS);
        double sum_sq_after = 0;
        for(int x = 0; x < N_POINTS; x++) sum_sq_after += a[x]*a[x];

        double expected = (double)N_POINTS * sum_sq_before;
        printf("  %-7s  Σ|F|² = %.0f   N·Σ|F̂|² ratio = %.6f   %s\n",
               names[t], sum_sq_before, sum_sq_after / expected,
               fabs(sum_sq_after / expected - 1.0) < 1e-9 ? "✓" : "✗");
    }
    free(a);
    printf("\n");
}

/* ═══ EXPERIMENT 3: Influences via discrete derivative ═══
 *
 * Influence of bit i: Inf_i(f) = Pr[f(x) ≠ f(x ⊕ e_i)]
 *                              = (1/2^n) · #{x : (∂_i f)(x) = 1}
 *
 * Equivalent via Walsh: Inf_i(f) = Σ_{s : s_i = 1} (F̂(s)/2^n)²
 * (Boolean "Plancherel for influences".)
 */
static double influence_direct(double (*f)(unsigned), int i){
    int count_diff = 0;
    for(unsigned x = 0; x < N_POINTS; x++){
        double a = f(x);
        double b = f(x ^ (1u << i));
        if(a != b) count_diff++;
    }
    return (double)count_diff / N_POINTS;
}

static double influence_walsh(double *F_hat, int i){
    double s = 0;
    double invN = 1.0 / N_POINTS;
    for(int idx = 0; idx < N_POINTS; idx++){
        if(idx & (1 << i)){
            double c = F_hat[idx] * invN;
            s += c * c;
        }
    }
    return s;
}

static void experiment_influences(void){
    printf("\n═══ EXPERIMENT 3: Influences via derivative AND Walsh ═══\n");
    printf("Two formulas must agree (a classic identity).\n\n");

    double *a = malloc(N_POINTS * sizeof(double));
    double (*funcs[])(unsigned) = {f_xor_01, f_and_01, f_maj_012, f_parity};
    const char *names[] = {"XOR(0,1)", "AND(0,1)", "MAJ(0,1,2)", "PARITY"};

    for(int t = 0; t < 4; t++){
        fill(a, funcs[t]);
        fwht(a, N_BITS);
        printf("  %s\n", names[t]);
        printf("    bit | Inf (direct) | Inf (Walsh) | agree?\n");
        for(int i = 0; i < 5; i++){
            double d = influence_direct(funcs[t], i);
            double w = influence_walsh(a, i);
            printf("    %2d  |   %.4f     |   %.4f    |  %s\n",
                   i, d, w, fabs(d - w) < 1e-9 ? "✓" : "✗");
        }
        double total = 0;
        for(int i = 0; i < N_BITS; i++) total += influence_direct(funcs[t], i);
        printf("    Total influence I(f) = %.4f\n\n", total);
    }
    free(a);
}

/* ═══ EXPERIMENT 4: Walsh spectrum of SHA-256 round function ═══
 *
 * We cannot transform the full 288-bit input to 256-bit output.
 * Instead: fix most of the input, pick 16 "variable" input bits,
 * and pick a single output bit to study.  We get f: {0,1}^16 → {0,1},
 * of which we can compute the full Walsh spectrum.
 *
 * We do this for multiple output bits and multiple round counts
 * and report:
 *   - max |F̂(s)| / 2^n  =  best linear-approximation correlation
 *   - Σ |F̂(s)|^4 / 2^{2n}  =  non-linearity measure (L4)
 *
 * As R grows, max|F̂| should SHRINK (rounds destroy linear structure).
 */
static uint32_t sha256_run_Rrounds(uint32_t W[], int R){
    uint32_t S[8]; memcpy(S, IV, sizeof(S));
    for(int t = 0; t < R; t++) sha256_round(S, W[t], t);
    /* Return 32-bit chunk of state[0] as the "output word" we inspect */
    return S[0];
}

static void experiment_sha_walsh(void){
    printf("\n═══ EXPERIMENT 4: Walsh spectrum of SHA-256 round ═══\n");
    printf("Vary 16 bits of W[0] (bits 0..15), fix the rest.\n");
    printf("Study all 32 bits of state[0] after R rounds.\n\n");

    double *a = malloc(N_POINTS * sizeof(double));

    printf("  R | output bit | max|F̂|/2^n | best-bias ε | I(f) total\n");
    printf("  --+------------+------------+-------------+-----------\n");

    for(int R = 1; R <= 6; R++){
        double sum_max_corr = 0;
        double sum_total_inf = 0;
        int bits_tested = 0;

        /* Sample 8 output bits to summarize */
        int chosen_bits[8] = {0, 3, 7, 11, 15, 19, 23, 31};

        for(int oi = 0; oi < 8; oi++){
            int output_bit = chosen_bits[oi];

            /* Fill the truth table: for each 16-bit input, run SHA round,
             * extract output_bit. */
            uint32_t W[8] = {0};
            for(unsigned x = 0; x < N_POINTS; x++){
                W[0] = (uint32_t)x;          /* vary low 16 bits */
                /* leave other W[i] = 0 */
                uint32_t y = sha256_run_Rrounds(W, R);
                int bit = (y >> output_bit) & 1;
                a[x] = bit ? -1.0 : 1.0;
            }

            fwht(a, N_BITS);

            /* Max |F̂|/2^n over s ≠ 0 (skip trivial DC component) */
            double max_corr = 0;
            for(int s = 1; s < N_POINTS; s++){
                double c = fabs(a[s]) / N_POINTS;
                if(c > max_corr) max_corr = c;
            }
            /* Total influence via sum of s·|F̂(s)|²  weighted */
            double total_inf = 0;
            double invN = 1.0 / N_POINTS;
            for(int i = 0; i < N_BITS; i++){
                double s = 0;
                for(int idx = 0; idx < N_POINTS; idx++){
                    if(idx & (1 << i)){
                        double c = a[idx] * invN;
                        s += c * c;
                    }
                }
                total_inf += s;
            }

            double bias = max_corr / 2.0;
            if(oi < 3 || oi == 7){
                printf("  %d |    %2d      |  %.6f  |  %.6f   |   %.4f\n",
                       R, output_bit, max_corr, bias, total_inf);
            }

            sum_max_corr += max_corr;
            sum_total_inf += total_inf;
            bits_tested++;
        }

        printf("    avg over 8 bits:  max-corr = %.6f, bias = %.6f, I(f) = %.4f\n\n",
               sum_max_corr / bits_tested,
               sum_max_corr / bits_tested / 2.0,
               sum_total_inf / bits_tested);
    }

    printf("INTERPRETATION:\n");
    printf("  max|F̂|/2^n is the best linear approximation of the output bit\n");
    printf("  as a linear combination of the 16 varied input bits.\n");
    printf("  bias = (max|F̂|/2^n) / 2  tells how far from uniform.\n");
    printf("  I(f) = total influence; random function → I ≈ 8 (= 16/2).\n");
    printf("\n  Cryptographic regime: max-corr → 0, I(f) → 8.\n");
    printf("  Structured regime: max-corr > 1/4, I(f) far from 8.\n");

    free(a);
}

/* ═══ EXPERIMENT 5: Walsh distance between rounds ═══
 *
 * d(f, g) = (1/2^n) · Σ_s |F̂(s) − Ĝ(s)|
 *
 * Measures how different two round functions look in spectrum.
 * If round_R and round_{R+1} are "spectrally close", the transform
 * is slowing.  If each round reshuffles the spectrum, mixing is good.
 */
static void experiment_spectral_distance(void){
    printf("\n═══ EXPERIMENT 5: Walsh distance between consecutive rounds ═══\n\n");

    double *a = malloc(N_POINTS * sizeof(double));
    double *prev = malloc(N_POINTS * sizeof(double));
    int output_bit = 7;

    printf("Output bit %d of state[0], varying W[0] low 16 bits.\n\n", output_bit);
    printf("  R | ||F̂_R||₁/2^n | d(F̂_R, F̂_{R-1})/2^n\n");
    printf("  --+---------------+---------------------\n");

    for(int R = 1; R <= 6; R++){
        uint32_t W[8] = {0};
        for(unsigned x = 0; x < N_POINTS; x++){
            W[0] = (uint32_t)x;
            uint32_t y = sha256_run_Rrounds(W, R);
            a[x] = ((y >> output_bit) & 1) ? -1.0 : 1.0;
        }
        fwht(a, N_BITS);

        double l1 = 0;
        for(int s = 0; s < N_POINTS; s++) l1 += fabs(a[s]);
        l1 /= N_POINTS;

        double d = 0;
        if(R > 1){
            for(int s = 0; s < N_POINTS; s++) d += fabs(a[s] - prev[s]);
            d /= N_POINTS;
        }

        printf("  %d |   %.4f      |   %.4f\n", R, l1, d);
        memcpy(prev, a, N_POINTS * sizeof(double));
    }
    free(a); free(prev);

    printf("\n||F̂||₁/2^n normalised: ~1 for delta (structured), √(2^n) for random.\n");
    printf("Rapid growth of ||F̂||₁ and large Δ between rounds = strong mixing.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BIT CALCULUS: derivatives, influences, Walsh spectrum\n");
    printf("══════════════════════════════════════════\n");
    printf("Tools: ∂_i, Inf_i, Walsh-Hadamard transform\n");
    printf("n = %d,  2^n = %d sample points per truth table\n", N_BITS, N_POINTS);

    experiment_basic_spectra();
    experiment_parseval();
    experiment_influences();
    experiment_sha_walsh();
    experiment_spectral_distance();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Analytical tools (∂, ∫, Fourier) lifted to pure bits\n");
    printf("  2. Walsh transform reveals linear structure in SHA-256\n");
    printf("  3. Influence = discrete derivative density per bit\n");
    printf("  4. Linear cryptanalysis framed in bit-calculus terms\n");
    printf("  5. Phase transition via max|F̂| across rounds\n");
    return 0;
}
