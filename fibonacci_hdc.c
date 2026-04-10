/*
 * FIBONACCI / ZECKENDORF HDC
 * ===========================
 *
 * Combines:
 *   - HDC (Kanerva 1988)
 *   - Zeckendorf's theorem (1972): every positive integer has a unique
 *     representation as a sum of non-consecutive Fibonacci numbers
 *   - Fibonacci coding (universal prefix-free code)
 *   - Sturmian / Fibonacci words (combinatorics on words)
 *
 * Novel idea: encode HDVs in a sparse Zeckendorf basis where bit positions
 * correspond to Fibonacci numbers F_2, F_3, F_4, ... and where no two
 * adjacent 1-bits may appear. This gives:
 *
 *   - Natural SPARSITY: avg density ~ 1/φ² ≈ 0.382
 *   - Golden-ratio entropy: log2(φ) ≈ 0.694 bits/position
 *   - Unique representation → canonical form
 *   - Distance-preserving for integer encoding
 *
 * Comparison to binary HDC:
 *   binary:   bit_i independent, p=0.5, ~D/2 density
 *   Fibonacci: bit_i depends on bit_{i-1}, p=1/φ², ~D/φ² density
 *
 * The question: does the "no-adjacent-1s" constraint destroy or
 * ENHANCE the pseudo-orthogonality property of HDC?
 *
 * Experiments:
 *   1. Fibonacci HDV generation + statistics
 *   2. Pseudo-orthogonality: random Fibonacci HDVs
 *   3. Integer encoding via Zeckendorf: does distance preserve order?
 *   4. Addition in Zeckendorf space ≡ HDC bundling?
 *
 * Compile: gcc -O3 -march=native -o fhdc fibonacci_hdc.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define D 2048
#define D_WORDS (D/64)

typedef struct { uint64_t b[D_WORDS]; } HDV;

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

static HDV hdv_zero(void){HDV v;memset(&v,0,sizeof(v));return v;}
static int hdv_ham(HDV a,HDV b){int d=0;for(int i=0;i<D_WORDS;i++)d+=__builtin_popcountll(a.b[i]^b.b[i]);return d;}
static int hdv_weight(HDV v){int w=0;for(int i=0;i<D_WORDS;i++)w+=__builtin_popcountll(v.b[i]);return w;}
static double hdv_sim(HDV a,HDV b){return 1.0-(double)hdv_ham(a,b)/D;}

static inline int get_bit(HDV v, int i){return (v.b[i>>6] >> (i&63)) & 1;}
static inline void set_bit(HDV *v, int i){v->b[i>>6] |= (1ULL << (i&63));}

/* ═══ FIBONACCI HDV GENERATION ═══
 *
 * Generate a random vector in the "Fibonacci-admissible" language:
 * binary strings over {0,1} with no two adjacent 1s.
 *
 * Counting: f(n) = f(n-1) + f(n-2) with f(1)=2, f(2)=3 (Fibonacci)
 * Number of admissible D-strings ≈ φ^D / √5 ≈ 1.618^D
 * Entropy per position = log2(φ) ≈ 0.694 bits
 *
 * Sampling method: walk left-to-right, bit_i = 1 with prob 1/φ²
 * ONLY if bit_{i-1} = 0. Otherwise force 0.
 */
static HDV hdv_fibonacci(void){
    HDV v = hdv_zero();
    int prev = 0;
    /* 1/φ² = (3 - √5)/2 ≈ 0.38197 */
    /* Use 2^32 * 0.38197 ≈ 1640531527 as threshold */
    unsigned int threshold = 1640531527u;
    for(int i = 0; i < D; i++){
        if(prev == 1){
            prev = 0;
            continue;
        }
        unsigned int r = (unsigned int)(rng_next() & 0xFFFFFFFFu);
        if(r < threshold){
            set_bit(&v, i);
            prev = 1;
        } else {
            prev = 0;
        }
    }
    return v;
}

/* Verify a HDV satisfies the no-adjacent-1s constraint */
static int is_fibonacci_admissible(HDV v){
    int prev = 0;
    for(int i = 0; i < D; i++){
        int b = get_bit(v, i);
        if(b && prev) return 0;
        prev = b;
    }
    return 1;
}

/* ═══ ZECKENDORF ENCODING ═══
 *
 * Represent positive integer n as sum of non-consecutive Fibonacci numbers.
 * Fibonacci: F_2=1, F_3=2, F_4=3, F_5=5, F_6=8, F_7=13, ...
 * Example: 100 = 89 + 8 + 3 = F_11 + F_6 + F_4
 *          bits at positions 11, 6, 4 (all non-adjacent ✓)
 *
 * Greedy algorithm: subtract largest Fibonacci ≤ remainder.
 */
#define MAX_FIB 90
static unsigned long long fibs[MAX_FIB];
static int n_fibs;

static void init_fibs(void){
    fibs[0] = 1; fibs[1] = 2;
    int i = 2;
    while(i < MAX_FIB && fibs[i-1] < (1ULL<<62)){
        fibs[i] = fibs[i-1] + fibs[i-2];
        i++;
    }
    n_fibs = i;
}

static HDV hdv_zeckendorf(unsigned long long n){
    HDV v = hdv_zero();
    while(n > 0){
        /* Find largest Fibonacci ≤ n */
        int k = n_fibs - 1;
        while(k >= 0 && fibs[k] > n) k--;
        if(k < 0) break;
        /* Place at bit position k (scaled into D) */
        /* Use position = k directly (if k < D) for integer encoding */
        if(k < D) set_bit(&v, k);
        n -= fibs[k];
    }
    return v;
}

/* ═══ EXPERIMENT 1: Fibonacci HDV statistics ═══ */
static void experiment_fib_stats(void){
    printf("\n═══ EXPERIMENT 1: Fibonacci HDV statistics ═══\n\n");

    rng_seed(42);

    const int N = 1000;
    double sum_density = 0;
    int admissible_count = 0;
    int min_w = D, max_w = 0;

    for(int i = 0; i < N; i++){
        HDV v = hdv_fibonacci();
        int w = hdv_weight(v);
        sum_density += (double)w / D;
        if(w < min_w) min_w = w;
        if(w > max_w) max_w = w;
        if(is_fibonacci_admissible(v)) admissible_count++;
    }

    double avg_density = sum_density / N;
    double expected = 1.0 / (1.618033988749 * 1.618033988749);

    printf("Sampled %d Fibonacci HDVs (D=%d):\n", N, D);
    printf("  Admissibility rate:  %d/%d (should be 100%%)\n", admissible_count, N);
    printf("  Average density:     %.4f (expected 1/φ² ≈ %.4f)\n", avg_density, expected);
    printf("  Weight range:        [%d, %d] (~ D/φ² = %.0f)\n",
           min_w, max_w, D / (1.618 * 1.618));
    printf("  Entropy per position: ~ log2(φ) ≈ 0.694 bits\n");
    printf("  Total entropy:        ~ %.0f bits (vs %d for binary)\n",
           D * 0.694, D);
}

/* ═══ EXPERIMENT 2: Pseudo-orthogonality ═══ */
static void experiment_pseudo_orth(void){
    printf("\n═══ EXPERIMENT 2: Pseudo-orthogonality of Fibonacci HDVs ═══\n\n");

    rng_seed(100);

    const int N = 200;
    HDV vecs[200];
    for(int i = 0; i < N; i++) vecs[i] = hdv_fibonacci();

    double sum_sim = 0, sum_sq = 0;
    double min_sim = 1.0, max_sim = 0;
    int pairs = 0;
    for(int i = 0; i < N; i++){
        for(int j = i+1; j < N; j++){
            double s = hdv_sim(vecs[i], vecs[j]);
            sum_sim += s;
            sum_sq += s*s;
            if(s < min_sim) min_sim = s;
            if(s > max_sim) max_sim = s;
            pairs++;
        }
    }

    double mean = sum_sim / pairs;
    double var = sum_sq / pairs - mean*mean;
    double std = sqrt(var);

    /* Expected similarity between two independent Fibonacci HDVs:
     * P(bit_i^A = bit_i^B) = p² + (1-p)² where p = 1/φ²
     * = (1/φ²)² + (1 - 1/φ²)² ≈ 0.146 + 0.382 ≈ 0.528
     * (Ignoring the sequential constraint — upper estimate)
     */
    double p = 1.0 / (1.618033988749 * 1.618033988749);
    double expected_sim = p*p + (1-p)*(1-p);

    printf("Pairwise similarity over %d pairs:\n", pairs);
    printf("  Mean:     %.4f (binary HDC: 0.500)\n", mean);
    printf("  Std dev:  %.4f\n", std);
    printf("  Range:    [%.4f, %.4f]\n", min_sim, max_sim);
    printf("  Expected: %.4f (matches mean?)\n", expected_sim);
    printf("\nInterpretation:\n");
    printf("  Fibonacci HDVs are ~%.3f similar on average (not 0.5)\n", mean);
    printf("  because shared 0-bits inflate similarity.\n");
    printf("  The *variance* — not the mean — measures orthogonality.\n");
    printf("  Smaller std → more uniform distances → weaker discrimination.\n");
}

/* ═══ EXPERIMENT 3: Zeckendorf integer encoding ═══ */
static void experiment_zeckendorf(void){
    printf("\n═══ EXPERIMENT 3: Zeckendorf encoding of integers ═══\n\n");

    init_fibs();
    printf("First Fibonacci numbers used: ");
    for(int i = 0; i < 12; i++) printf("%llu ", fibs[i]);
    printf("...\n\n");

    /* Encode integers 1..20 and show structure */
    printf("Integer encodings (positions set):\n");
    for(int n = 1; n <= 15; n++){
        HDV v = hdv_zeckendorf((unsigned long long)n);
        printf("  %3d → [", n);
        int first = 1;
        for(int i = 0; i < 20; i++){
            if(get_bit(v, i)){
                if(!first) printf(",");
                printf("%d", i);
                first = 0;
            }
        }
        printf("]  w=%d\n", hdv_weight(v));
    }

    /* Key question: does "semantic distance" (|a-b|) correlate with
     * Hamming distance in Zeckendorf space? */
    printf("\nDistance preservation test (|a-b| vs Hamming):\n");
    printf("  |a-b| | mean Hamming | stddev\n");
    printf("  ------+--------------+-------\n");

    int diffs[] = {1, 2, 5, 10, 50, 100, 500, 1000, 10000};
    for(int di = 0; di < 9; di++){
        int d = diffs[di];
        double sum = 0, sum2 = 0;
        int trials = 100;
        for(int t = 0; t < trials; t++){
            unsigned long long a = (rng_next() % 100000) + d + 1;
            unsigned long long b = a - d;
            HDV va = hdv_zeckendorf(a);
            HDV vb = hdv_zeckendorf(b);
            int h = hdv_ham(va, vb);
            sum += h;
            sum2 += h*h;
        }
        double mean = sum / trials;
        double std = sqrt(sum2/trials - mean*mean);
        printf("  %5d | %12.2f | %.2f\n", d, mean, std);
    }

    printf("\nIf close integers have SMALL Hamming distance, Zeckendorf\n");
    printf("HDC provides a metric-preserving integer embedding.\n");
}

/* ═══ EXPERIMENT 4: Zeckendorf addition vs bundle ═══ */
static void experiment_zeck_addition(void){
    printf("\n═══ EXPERIMENT 4: Integer arithmetic in Fibonacci HDV space ═══\n\n");

    /* Test: does Z(a+b) ≈ bundle(Z(a), Z(b))?
     * Or: Z(a+b) similar to Z(a) ⊕ Z(b)?
     */
    printf("Testing: how does Z(a+b) relate to Z(a) and Z(b)?\n\n");

    int trials = 10;
    double avg_sim_xor = 0, avg_sim_or = 0, avg_sim_sum = 0;

    printf("  a    b   a+b | sim(Z(a+b),Z(a)⊕Z(b)) | sim(Z(a+b),Z(a)|Z(b))\n");
    printf("  ---- ---- ----+----------------------+---------------------\n");

    for(int t = 0; t < trials; t++){
        unsigned long long a = (rng_next() % 500) + 1;
        unsigned long long b = (rng_next() % 500) + 1;
        HDV va = hdv_zeckendorf(a);
        HDV vb = hdv_zeckendorf(b);
        HDV vsum = hdv_zeckendorf(a+b);

        /* XOR combination */
        HDV vxor;
        for(int i = 0; i < D_WORDS; i++) vxor.b[i] = va.b[i] ^ vb.b[i];

        /* OR combination (union of Fibonacci numbers used) */
        HDV vor;
        for(int i = 0; i < D_WORDS; i++) vor.b[i] = va.b[i] | vb.b[i];

        double s_xor = hdv_sim(vsum, vxor);
        double s_or = hdv_sim(vsum, vor);
        avg_sim_xor += s_xor;
        avg_sim_or += s_or;

        if(t < 5){
            printf("  %4llu %4llu %4llu |       %.4f         |      %.4f\n",
                   a, b, a+b, s_xor, s_or);
        }
    }
    avg_sim_xor /= trials;
    avg_sim_or /= trials;
    (void)avg_sim_sum;

    printf("\nAverage similarities:\n");
    printf("  Z(a+b) vs Z(a)⊕Z(b): %.4f\n", avg_sim_xor);
    printf("  Z(a+b) vs Z(a)|Z(b): %.4f\n", avg_sim_or);
    printf("\nZeckendorf addition is NOT a simple bitwise op — it requires\n");
    printf("'carry' rules: F_k + F_k = F_{k+1} + F_{k-2}, and 011 → 100.\n");
    printf("This makes Fibonacci HDC non-linear, unlike binary HDC.\n");
    printf("Non-linearity = more expressive, harder to analyze.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("FIBONACCI / ZECKENDORF HDC\n");
    printf("══════════════════════════════════════════\n");
    printf("Combining HDC + Zeckendorf's theorem + Fibonacci coding\n");
    printf("D=%d, golden ratio φ≈1.618\n", D);

    experiment_fib_stats();
    experiment_pseudo_orth();
    experiment_zeckendorf();
    experiment_zeck_addition();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. HDV sparsity derived from number theory (1/φ²)\n");
    printf("  2. Unique canonical form via Zeckendorf's theorem\n");
    printf("  3. Natural integer embedding in high-dim bit space\n");
    printf("  4. Non-linear arithmetic from carry rules\n");
    printf("  5. Entropy = D·log₂(φ) ≈ 0.694·D bits (vs D for binary)\n");
    return 0;
}
