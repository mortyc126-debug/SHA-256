/*
 * NEURAL-GUIDED SHA-256 ROUND INVERSION
 * ======================================
 *
 * Hypothesis (user's):
 *   Data is destroyed by hashing, but a bit-based neural network
 *   could ENUMERATE LIKELY preimages instead of all 2^32 per round,
 *   potentially reducing the search space by orders of magnitude.
 *
 * What we measure:
 *   1. Structural correlation: does Hamming(state_R(W), state_R(W'))
 *      correlate with Hamming(W, W')? For pure random oracles, 0.
 *      Any non-zero correlation is exploitable.
 *
 *   2. Bit-level mutual information: for each output bit of state_R,
 *      how many input W bits does it statistically depend on?
 *      Full avalanche = each output bit depends on ~50% of inputs.
 *
 *   3. HDV memory retrieval: store 100k (state_R → W) training pairs.
 *      Query with unseen state_R; does top-K nearest-neighbor contain
 *      the true W? If yes, search space shrinks from 2^32 to K.
 *
 *   4. Phase transition: at what round R does all exploitable
 *      structure vanish? R=1 easy, R=4+ cryptographic.
 *
 * Caveat: for R rounds with fixed IV, the map W_vec → state_R is
 * invertible analytically when bijective. We frame this as an HDV
 * learning problem to test whether the network can RECOVER the
 * structure, not whether the structure exists.
 *
 * Compile: gcc -O3 -march=native -o sha_inv sha256_invert.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

/* ═══ SHA-256 CORE ═══ */
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

/* Run R rounds from IV with given message words */
static void sha256_Rrounds(uint32_t out[8], const uint32_t *W, int R){
    uint32_t S[8];
    memcpy(S, IV, sizeof(S));
    for(int t = 0; t < R; t++) sha256_round(S, W[t], t);
    memcpy(out, S, sizeof(S));
}

/* ═══ PACKING STATE into bit vector ═══ */
/* State = 8×32 = 256 bits, fits in 4×uint64. */
typedef struct { uint64_t b[4]; } State256;

static State256 state_pack(const uint32_t S[8]){
    State256 r;
    for(int i = 0; i < 4; i++){
        r.b[i] = ((uint64_t)S[2*i]) | ((uint64_t)S[2*i+1] << 32);
    }
    return r;
}
static inline int state_ham(State256 a, State256 b){
    int d = 0;
    for(int i = 0; i < 4; i++) d += __builtin_popcountll(a.b[i] ^ b.b[i]);
    return d;
}

/* Pack message word vector W[R] into 32*R-bit vector */
static int w_ham(const uint32_t *a, const uint32_t *b, int R){
    int d = 0;
    for(int i = 0; i < R; i++) d += __builtin_popcount(a[i] ^ b[i]);
    return d;
}

/* ═══ RNG ═══ */
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

/* ═══ EXPERIMENT 1: Structural correlation ═══
 *
 * For random (W_a, W_b) pairs, measure correlation between
 * Hamming(W_a, W_b) and Hamming(state_R(W_a), state_R(W_b)).
 *
 * True random oracle → correlation = 0 (avalanche).
 * Any non-zero value = exploitable structure.
 */
static void experiment_correlation(void){
    printf("\n═══ EXPERIMENT 1: Input-output Hamming correlation ═══\n");
    printf("Does Hamming(W, W') predict Hamming(state_R(W), state_R(W'))?\n");
    printf("Random oracle: correlation = 0. Any signal = exploitable.\n\n");

    rng_seed(1);
    const int N = 10000;
    const int R_MAX = 8;

    printf("  R  | mean H_out | std H_out | corr(H_in, H_out)\n");
    printf("  ---+-----------+-----------+------------------\n");

    for(int R = 1; R <= R_MAX; R++){
        double sum_x = 0, sum_y = 0, sum_xy = 0, sum_xx = 0, sum_yy = 0;
        double mean_y = 0, var_y = 0;

        for(int i = 0; i < N; i++){
            uint32_t Wa[R_MAX], Wb[R_MAX];
            for(int j = 0; j < R; j++){
                Wa[j] = (uint32_t)rng_next();
                Wb[j] = (uint32_t)rng_next();
            }
            int hin = w_ham(Wa, Wb, R);
            uint32_t Sa[8], Sb[8];
            sha256_Rrounds(Sa, Wa, R);
            sha256_Rrounds(Sb, Wb, R);
            int hout = state_ham(state_pack(Sa), state_pack(Sb));

            sum_x += hin; sum_y += hout;
            sum_xy += (double)hin * hout;
            sum_xx += (double)hin * hin;
            sum_yy += (double)hout * hout;
            mean_y += hout;
            var_y += (double)hout * hout;
        }
        double mx = sum_x/N, my = sum_y/N;
        double cov = sum_xy/N - mx*my;
        double var_x = sum_xx/N - mx*mx;
        double vy = sum_yy/N - my*my;
        double corr = cov / (sqrt(var_x * vy) + 1e-12);
        mean_y /= N;
        var_y = var_y/N - mean_y*mean_y;

        printf("  %2d | %9.2f | %9.2f | %+.6f\n",
               R, mean_y, sqrt(var_y), corr);
    }

    printf("\nExpected: R=1 has measurable corr, R≥4 ≈ 0 (avalanche).\n");
}

/* ═══ EXPERIMENT 2: Per-bit avalanche ═══
 *
 * Flip one bit of W; count bit flips in state_R.
 * Random oracle → ~50% (128 of 256).
 * Partial = round function not fully diffused.
 */
static void experiment_avalanche(void){
    printf("\n═══ EXPERIMENT 2: Avalanche effect per round ═══\n");
    printf("Flip 1 random bit of W; measure output bit flips.\n\n");

    rng_seed(2);
    const int N = 2000;

    printf("  R  | mean flips (of 256) | fraction | avalanche?\n");
    printf("  ---+---------------------+----------+-----------\n");

    for(int R = 1; R <= 8; R++){
        long total_flips = 0;
        for(int i = 0; i < N; i++){
            uint32_t Wa[8];
            for(int j = 0; j < R; j++) Wa[j] = (uint32_t)rng_next();
            uint32_t Wb[8];
            memcpy(Wb, Wa, sizeof(Wb));
            int bit = rng_next() % (32*R);
            Wb[bit/32] ^= 1u << (bit%32);

            uint32_t Sa[8], Sb[8];
            sha256_Rrounds(Sa, Wa, R);
            sha256_Rrounds(Sb, Wb, R);
            total_flips += state_ham(state_pack(Sa), state_pack(Sb));
        }
        double mean = (double)total_flips / N;
        double frac = mean / 256.0;
        const char *label = frac < 0.30 ? "partial" : frac > 0.48 ? "complete" : "forming";
        printf("  %2d | %19.2f | %8.4f | %s\n", R, mean, frac, label);
    }

    printf("\nPhase transition: partial → complete avalanche marks the\n");
    printf("round at which structural inversion becomes infeasible.\n");
}

/* ═══ EXPERIMENT 3: HDV memory retrieval ═══
 *
 * Store N (state_R → W_vec) training pairs. Query with unseen state_R;
 * find K nearest by Hamming distance; report the retrieved W_vecs.
 *
 * If the true W_vec is in top-K (or Hamming-close to a retrieved one),
 * the search space shrinks from 2^(32*R) to K.
 */
#define TRAIN_N 100000

typedef struct {
    State256 state;
    uint32_t W[4];  /* up to 4 rounds */
} Entry;

static Entry *mem;

static int entry_cmp_dist_key = 0;
static State256 entry_cmp_query;
static int entry_cmp(const void *a, const void *b){
    const Entry *ea = (const Entry*)a;
    const Entry *eb = (const Entry*)b;
    int da = state_ham(ea->state, entry_cmp_query);
    int db = state_ham(eb->state, entry_cmp_query);
    (void)entry_cmp_dist_key;
    return da - db;
}

static void experiment_retrieval(int R){
    printf("\n═══ EXPERIMENT 3 (R=%d): HDV memory retrieval ═══\n", R);
    printf("Train on %d random (state_R → W) samples.\n", TRAIN_N);
    printf("Query with unseen state_R; test top-K retrieval.\n\n");

    rng_seed(100 + R);
    mem = malloc(TRAIN_N * sizeof(Entry));

    /* Build training memory */
    for(int i = 0; i < TRAIN_N; i++){
        for(int j = 0; j < R; j++) mem[i].W[j] = (uint32_t)rng_next();
        uint32_t S[8];
        sha256_Rrounds(S, mem[i].W, R);
        mem[i].state = state_pack(S);
    }

    /* Run 200 test queries with fresh W_vec */
    const int Q = 200;
    int top1_bit_close = 0, top10_bit_close = 0, top100_bit_close = 0;
    int top1_any_match = 0, top10_any_match = 0, top100_any_match = 0;
    double sum_best_w_ham = 0;
    double sum_state_gap = 0;

    for(int q = 0; q < Q; q++){
        uint32_t W_true[4];
        for(int j = 0; j < R; j++) W_true[j] = (uint32_t)rng_next();
        uint32_t S_true[8];
        sha256_Rrounds(S_true, W_true, R);
        State256 qs = state_pack(S_true);

        /* Scan memory, find top-100 by Hamming distance.
         * Simple partial selection to keep it fast. */
        int topK = 100;
        int dists[100];
        int idxs[100];
        for(int i = 0; i < topK; i++){dists[i] = 1<<20; idxs[i] = -1;}

        for(int i = 0; i < TRAIN_N; i++){
            int d = state_ham(mem[i].state, qs);
            /* Insert into top-K if smaller than current max */
            int max_pos = 0;
            for(int k = 1; k < topK; k++) if(dists[k] > dists[max_pos]) max_pos = k;
            if(d < dists[max_pos]){
                dists[max_pos] = d;
                idxs[max_pos] = i;
            }
        }

        /* Sort top-K by distance ascending (bubble, K small) */
        for(int a = 0; a < topK-1; a++){
            for(int b = 0; b < topK-1-a; b++){
                if(dists[b] > dists[b+1]){
                    int t = dists[b]; dists[b]=dists[b+1]; dists[b+1]=t;
                    t = idxs[b]; idxs[b]=idxs[b+1]; idxs[b+1]=t;
                }
            }
        }

        /* Metrics:
         * - Closest state-Hamming from top-1, top-10, top-100
         * - W-hamming between true and closest retrieved
         * - "bit close": retrieved W within Hamming-8 of true
         * - "any match": retrieved W exactly equals true (very rare)
         */
        int best_wh = 1000;
        int best_wh_top10 = 1000;
        int best_wh_top100 = 1000;
        int state_gap = dists[0];
        for(int k = 0; k < topK; k++){
            int wh = w_ham(mem[idxs[k]].W, W_true, R);
            if(k == 0 && wh < best_wh) best_wh = wh;
            if(k < 10 && wh < best_wh_top10) best_wh_top10 = wh;
            if(wh < best_wh_top100) best_wh_top100 = wh;

            if(k == 0 && wh == 0) top1_any_match++;
            if(k < 10 && wh == 0) top10_any_match++;
            if(wh == 0) top100_any_match++;
        }
        if(best_wh <= 8) top1_bit_close++;
        if(best_wh_top10 <= 8) top10_bit_close++;
        if(best_wh_top100 <= 8) top100_bit_close++;
        sum_best_w_ham += best_wh_top100;
        sum_state_gap += state_gap;
    }

    double expected_random_wh = 16.0 * R; /* half of 32R bits */
    printf("Results over %d test queries (R=%d, W has %d bits):\n", Q, R, 32*R);
    printf("  Closest state_R in training: Hamming %.2f / 256\n", sum_state_gap/Q);
    printf("  Best W Hamming (top-100):    %.2f\n", sum_best_w_ham/Q);
    printf("  Expected for random memory:  %.2f\n", expected_random_wh);
    printf("\n");
    printf("  Hit rate (exact W recovery):\n");
    printf("    top-1:   %d/%d = %.1f%%\n", top1_any_match, Q, 100.0*top1_any_match/Q);
    printf("    top-10:  %d/%d = %.1f%%\n", top10_any_match, Q, 100.0*top10_any_match/Q);
    printf("    top-100: %d/%d = %.1f%%\n", top100_any_match, Q, 100.0*top100_any_match/Q);
    printf("\n");
    printf("  Near-hit rate (W within Hamming-8):\n");
    printf("    top-1:   %d/%d = %.1f%%\n", top1_bit_close, Q, 100.0*top1_bit_close/Q);
    printf("    top-10:  %d/%d = %.1f%%\n", top10_bit_close, Q, 100.0*top10_bit_close/Q);
    printf("    top-100: %d/%d = %.1f%%\n", top100_bit_close, Q, 100.0*top100_bit_close/Q);

    /* Interpretation */
    double improvement = expected_random_wh / (sum_best_w_ham/Q + 0.01);
    printf("\n  W-Hamming improvement factor: %.2fx vs random\n", improvement);

    free(mem);
}

/* ═══ EXPERIMENT 4: HONEST end-to-end inversion at R=1 ═══
 *
 * Given target state_1, use HDV memory to propose candidate W,
 * then brute-force a Hamming ball around each candidate and
 * CHECK: does the candidate reproduce state_1 exactly?
 *
 * Report the actual number of sha256_round() evaluations needed
 * to find a valid preimage, vs 2^32 brute force.
 */
static uint64_t count_combinations(int n, int k){
    if(k < 0 || k > n) return 0;
    if(k > n - k) k = n - k;
    uint64_t r = 1;
    for(int i = 0; i < k; i++){
        r *= (uint64_t)(n - i);
        r /= (uint64_t)(i + 1);
    }
    return r;
}

/* Enumerate all W in Hamming ball of radius <= radius around center.
 * For each: apply round, compare to target. Return #evals and success. */
static int flip_up_to_radius(uint32_t center, uint32_t target_s[8],
                             int radius, uint64_t *evals_out, uint32_t *W_found){
    /* Enumerate by number of flips 0..radius, each with combinations */
    uint64_t evals = 0;
    int positions[32];
    for(int r = 0; r <= radius; r++){
        /* Gosper's hack: iterate all r-subsets of 32 bits */
        if(r == 0){
            uint32_t cand = center;
            uint32_t S[8]; memcpy(S, IV, sizeof(S));
            sha256_round(S, cand, 0);
            evals++;
            State256 a = state_pack(S);
            State256 b = state_pack(target_s);
            if(state_ham(a, b) == 0){
                *W_found = cand;
                *evals_out = evals;
                return 1;
            }
            continue;
        }
        /* Start with lowest r bits */
        for(int i = 0; i < r; i++) positions[i] = i;
        while(1){
            uint32_t mask = 0;
            for(int i = 0; i < r; i++) mask |= 1u << positions[i];
            uint32_t cand = center ^ mask;
            uint32_t S[8]; memcpy(S, IV, sizeof(S));
            sha256_round(S, cand, 0);
            evals++;
            State256 a = state_pack(S);
            State256 b = state_pack(target_s);
            if(state_ham(a, b) == 0){
                *W_found = cand;
                *evals_out = evals;
                return 1;
            }

            /* Advance to next r-subset */
            int i = r - 1;
            while(i >= 0 && positions[i] == 32 - r + i) i--;
            if(i < 0) break;
            positions[i]++;
            for(int j = i + 1; j < r; j++) positions[j] = positions[j-1] + 1;
        }
    }
    *evals_out = evals;
    return 0;
}

static void experiment_honest_invert_r1(void){
    printf("\n═══ EXPERIMENT 4: Honest end-to-end inversion at R=1 ═══\n");
    printf("HDV memory proposes W candidates; local brute-force verifies.\n");
    printf("Metric: sha256_round evaluations to find true preimage.\n\n");

    rng_seed(777);
    mem = malloc(TRAIN_N * sizeof(Entry));
    for(int i = 0; i < TRAIN_N; i++){
        mem[i].W[0] = (uint32_t)rng_next();
        uint32_t S[8];
        sha256_Rrounds(S, mem[i].W, 1);
        mem[i].state = state_pack(S);
    }

    const int Q = 50;
    uint64_t total_evals = 0;
    int successes = 0;
    uint64_t max_evals = 0, min_evals = ~0ULL;

    for(int q = 0; q < Q; q++){
        uint32_t W_true = (uint32_t)rng_next();
        uint32_t S_true[8];
        sha256_Rrounds(S_true, &W_true, 1);
        State256 qs = state_pack(S_true);

        /* Find top-10 nearest in memory */
        const int TK = 10;
        int dists[10], idxs[10];
        for(int i = 0; i < TK; i++){dists[i] = 1<<20; idxs[i] = -1;}
        for(int i = 0; i < TRAIN_N; i++){
            int d = state_ham(mem[i].state, qs);
            int mp = 0;
            for(int k = 1; k < TK; k++) if(dists[k] > dists[mp]) mp = k;
            if(d < dists[mp]){dists[mp] = d; idxs[mp] = i;}
        }

        /* Try each candidate: expand Hamming ball of radius up to 6 */
        uint64_t q_evals = 0;
        uint32_t W_found = 0;
        int found = 0;
        for(int k = 0; k < TK && !found; k++){
            uint32_t center = mem[idxs[k]].W[0];
            uint64_t local_evals = 0;
            if(flip_up_to_radius(center, S_true, 6, &local_evals, &W_found)){
                q_evals += local_evals;
                found = 1;
                break;
            }
            q_evals += local_evals;
        }

        if(found){
            successes++;
            total_evals += q_evals;
            if(q_evals > max_evals) max_evals = q_evals;
            if(q_evals < min_evals) min_evals = q_evals;
        }
    }

    free(mem);

    double brute_force = 4.29e9; /* 2^32 */
    double avg = successes ? (double)total_evals / successes : 0;
    printf("Queries:        %d\n", Q);
    printf("Successes:      %d / %d (%.1f%%)\n", successes, Q, 100.0*successes/Q);
    printf("Avg evals:      %.2e\n", avg);
    printf("Min/Max evals:  %llu / %llu\n",
           (unsigned long long)min_evals, (unsigned long long)max_evals);
    printf("Brute force:    %.2e (2^32)\n", brute_force);
    if(successes)
        printf("Speedup:        %.1fx vs brute force\n", brute_force / avg);

    /* Ball sizes for reference */
    printf("\nHamming ball sizes around a W (32-bit):\n");
    for(int r = 0; r <= 8; r++){
        uint64_t sz = 0;
        for(int i = 0; i <= r; i++) sz += count_combinations(32, i);
        printf("  radius %d: %llu\n", r, (unsigned long long)sz);
    }
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("NEURAL-GUIDED SHA-256 ROUND INVERSION\n");
    printf("══════════════════════════════════════════\n");
    printf("Testing hypothesis: bit-based memory narrows preimage search\n");
    printf("across reduced-round SHA-256.\n");

    experiment_correlation();
    experiment_avalanche();
    experiment_retrieval(1);
    experiment_retrieval(2);
    experiment_retrieval(3);
    experiment_retrieval(4);
    experiment_honest_invert_r1();

    printf("\n══════════════════════════════════════════\n");
    printf("VERDICT:\n");
    printf("  - Correlation and avalanche curves show the phase\n");
    printf("    transition from structured to cryptographic rounds.\n");
    printf("  - Retrieval at R=1 should give measurable W-Hamming\n");
    printf("    improvement; R=2,3 reveals how fast it degrades.\n");
    printf("  - Any improvement >1x = HDV memory is learning SOMETHING.\n");
    return 0;
}
