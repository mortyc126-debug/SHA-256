/*
 * P-ADIC HDC: ultrametric topology on bit vectors
 * ==================================================
 *
 * Stage D of the "math of bits" programme.  A fundamentally
 * different metric on the same bit space.
 *
 * Hamming distance sees WHERE bits differ only as a count.
 * The p-adic metric cares about THE POSITION of the first
 * difference, exponentially weighted:
 *
 *     ‖x − y‖_p  =  p^{ − v_p(x − y) }
 *
 * where v_p(z) is the index of the lowest (or highest, depending
 * on convention) bit at which z is nonzero.
 *
 * For p = 2 and z = a bit vector read as an integer:
 *     v_2(z)  =  position of the lowest set bit (binary valuation)
 *     ‖z‖_2  =  2^{−v_2(z)}
 *
 * This satisfies the ULTRAMETRIC inequality, stronger than the
 * triangle inequality:
 *
 *     ‖x + y‖_p  ≤  max(‖x‖_p, ‖y‖_p)
 *
 * Consequences (weird but true):
 *   - Every triangle is isoceles with the two longest sides equal.
 *   - Every point inside a ball is its centre.
 *   - The topology is totally disconnected (Cantor-set-like).
 *
 * Why this is interesting for SHA-256:
 *   Hamming distance saturates by round 3 (avalanche).  But the
 *   p-adic metric is sensitive to WHERE differences land, not how
 *   many there are.  A function that flips bit 200 but leaves bits
 *   0..199 untouched has ‖·‖_2 = 2^{-200} — almost zero in p-adic!
 *   Does any such "low-valuation" structure survive through
 *   SHA-256 rounds?
 *
 * Experiments:
 *   1. Ultrametric inequality: verify it on random vectors
 *   2. Isoceles triangles: all triples of random vectors
 *   3. Ball structure: "every point is a centre"
 *   4. SHA-256 round: distribution of p-adic distances
 *      across rounds — does low-valuation structure survive?
 *   5. Walsh of the p-adic indicator function
 *
 * Compile: gcc -O3 -march=native -o padic padic_hdc.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

/* ═══ 2-ADIC VALUATION on a 256-bit "state" ═══
 *
 * We treat a State256 = (uint64_t b[4]) as a big unsigned integer
 * with b[0] the low 64 bits.  v_2(z) = position of the lowest set bit.
 * If z = 0, we define v_2(0) = +∞ (we use 256 as sentinel).
 *
 * p-adic NORM: 2^{−v_2}.  We store log-norm as an int = −v_2 so
 * that larger log-norm means larger norm (0 is max, −256 is zero).
 */
typedef struct { uint64_t b[4]; } State256;

static State256 state_xor(State256 a, State256 b){
    State256 r;
    for(int i = 0; i < 4; i++) r.b[i] = a.b[i] ^ b.b[i];
    return r;
}
static int state_is_zero(State256 a){
    return (a.b[0] | a.b[1] | a.b[2] | a.b[3]) == 0;
}

/* Binary valuation: position of lowest set bit, or 256 for zero */
static int v2(State256 a){
    for(int i = 0; i < 4; i++){
        if(a.b[i]) return 64*i + __builtin_ctzll(a.b[i]);
    }
    return 256;
}

/* 2-adic distance between a and b, represented as log₂ of distance,
 * i.e. −v_2(a − b) ∈ [−256, 0].  Zero-distance encoded as −256. */
static int padic_log_dist(State256 a, State256 b){
    State256 d = state_xor(a, b);
    int v = v2(d);
    return (v == 256) ? -256 : -v;
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
static State256 state_pack(const uint32_t S[8]){
    State256 r;
    for(int i = 0; i < 4; i++)
        r.b[i] = ((uint64_t)S[2*i]) | ((uint64_t)S[2*i+1] << 32);
    return r;
}
static State256 sha256_Rrounds_state(const uint32_t *W, int R){
    uint32_t S[8]; memcpy(S, IV, sizeof(S));
    for(int t = 0; t < R; t++) sha256_round(S, W[t], t);
    return state_pack(S);
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

static State256 random_state(void){
    State256 r;
    for(int i = 0; i < 4; i++) r.b[i] = rng_next();
    return r;
}

/* ═══ EXPERIMENT 1: Ultrametric inequality ═══
 *
 * For all random pairs (x, y, z), verify
 *     ‖x − z‖_p  ≤  max(‖x − y‖_p, ‖y − z‖_p)
 *
 * In log-space this becomes
 *     log_dist(x, z)  ≤  max(log_dist(x, y), log_dist(y, z))
 *
 * (Larger log_dist = larger distance in our encoding.)
 */
static void experiment_ultrametric(void){
    printf("\n═══ EXPERIMENT 1: Ultrametric inequality ═══\n\n");
    printf("Verify ‖x−z‖ ≤ max(‖x−y‖, ‖y−z‖) on random triples.\n\n");

    rng_seed(1);
    int N = 100000;
    int ok = 0, bad = 0;
    int strict = 0;

    for(int i = 0; i < N; i++){
        State256 x = random_state();
        State256 y = random_state();
        State256 z = random_state();
        int dxz = padic_log_dist(x, z);
        int dxy = padic_log_dist(x, y);
        int dyz = padic_log_dist(y, z);
        int mx = dxy > dyz ? dxy : dyz;
        if(dxz <= mx){ ok++; if(dxz < mx) strict++; }
        else bad++;
    }
    printf("  Triples tested:     %d\n", N);
    printf("  Ultrametric holds:  %d\n", ok);
    printf("  Violations:         %d\n", bad);
    printf("  Strict inequality:  %d (%.1f%%)\n", strict, 100.0*strict/N);
    printf("  %s\n", bad == 0 ? "✓ Ultrametric confirmed" : "✗ VIOLATIONS FOUND");
}

/* ═══ EXPERIMENT 2: Every triangle is isoceles ═══
 *
 * In an ultrametric space, for any triangle (x, y, z), the two
 * largest sides are equal.  Equivalently: the distance set
 * {d(x,y), d(y,z), d(x,z)} has at most 2 distinct values.
 */
static void experiment_isoceles(void){
    printf("\n═══ EXPERIMENT 2: Every triangle is isoceles ═══\n\n");

    rng_seed(2);
    int N = 100000;
    int iso = 0, equi = 0, scalene = 0;

    for(int i = 0; i < N; i++){
        State256 x = random_state();
        State256 y = random_state();
        State256 z = random_state();
        int a = padic_log_dist(x, y);
        int b = padic_log_dist(y, z);
        int c = padic_log_dist(x, z);

        /* Unique values */
        int u[3] = {a, b, c};
        int n_uniq = 1;
        if(u[1] != u[0]) n_uniq++;
        if(u[2] != u[0] && u[2] != u[1]) n_uniq++;

        if(n_uniq == 1) equi++;
        else if(n_uniq == 2) iso++;
        else scalene++;
    }
    printf("  Triples tested:         %d\n", N);
    printf("  Equilateral (a=b=c):    %d (%.2f%%)\n", equi, 100.0*equi/N);
    printf("  Isoceles  (1 unique):   %d (%.2f%%)\n", iso, 100.0*iso/N);
    printf("  Scalene (a,b,c all ≠):  %d\n", scalene);
    printf("  %s\n", scalene == 0 ? "✓ All triangles isoceles (as ultrametrics require)"
                                  : "✗ Scalene triangles found — metric is not ultrametric");
}

/* ═══ EXPERIMENT 3: Every point is a centre of its ball ═══
 *
 * In an ultrametric, if y lies in the open ball B(x, r), then
 * B(y, r) = B(x, r) exactly.  We verify by sampling points in a
 * ball and confirming all pairwise distances are ≤ r.
 */
static void experiment_balls(void){
    printf("\n═══ EXPERIMENT 3: Every point is a ball centre ═══\n\n");

    rng_seed(3);
    /* Pick a reference point x and radius corresponding to log_dist ≤ -5
     * (i.e. the two points agree on bits 0..4). */
    State256 x = random_state();
    int radius_log = -5;   /* v_2 ≥ 5 */

    /* Sample candidates and collect those in B(x, r) */
    int max_coll = 64;
    State256 coll[64];
    int nc = 0;
    int tries = 0;
    while(nc < max_coll && tries < 500000){
        State256 y = x;
        /* Force agreement on low 5 bits by clearing low 5 bits of xor */
        /* Easier: y = x XOR (random & ~0x1F) across low 64 bits */
        y.b[0] = x.b[0] ^ (rng_next() & ~0x1FULL);
        y.b[1] = x.b[1] ^ rng_next();
        y.b[2] = x.b[2] ^ rng_next();
        y.b[3] = x.b[3] ^ rng_next();
        if(padic_log_dist(x, y) <= radius_log){
            coll[nc++] = y;
        }
        tries++;
    }

    /* Check: all pairwise distances in coll are ≤ radius_log */
    int ok = 1;
    int max_pair = -257;
    for(int i = 0; i < nc; i++){
        for(int j = i+1; j < nc; j++){
            int d = padic_log_dist(coll[i], coll[j]);
            if(d > max_pair) max_pair = d;
            if(d > radius_log){ok = 0;}
        }
    }
    printf("  Points in ball B(x, 2^%d):  %d\n", radius_log, nc);
    printf("  Max pairwise log-distance:  %d\n", max_pair);
    printf("  All pairs within radius?    %s\n", ok ? "YES ✓" : "NO ✗");
    printf("  Consequence: any of these %d points can serve as the centre.\n", nc);
}

/* ═══ EXPERIMENT 4: p-adic distance through SHA-256 ═══
 *
 * For a pair (W, W'), compute state_R(W), state_R(W'), and look at
 * v_2(state_R(W) − state_R(W')) — the index of the lowest differing
 * bit in the output.
 *
 * A random oracle gives uniform distribution of v_2 with
 * Pr[v_2 = k] = 2^{-k-1} (geometric in k).  The mean valuation is 1.
 *
 * The question: does v_2 follow this geometric pattern already at
 * R=1, or does the round function leave a "low-valuation hole"
 * where v_2 has a nontrivial dependence on the input difference?
 */
static void experiment_sha_padic(void){
    printf("\n═══ EXPERIMENT 4: p-adic distance through SHA-256 ═══\n\n");
    printf("Distribution of v_2(state_R(W) XOR state_R(W')) across rounds\n");
    printf("(lower v_2 = larger p-adic distance = bits differ in low places)\n\n");

    rng_seed(4);
    int N = 200000;

    printf("  R  | mean v_2 | max v_2 | %%(v_2=0) | %%(v_2<4) | %%(v_2<16)\n");
    printf("  ---+----------+---------+----------+----------+-----------\n");

    for(int R = 1; R <= 8; R++){
        long sum_v = 0;
        int max_v = 0;
        int at0 = 0, lt4 = 0, lt16 = 0;
        for(int i = 0; i < N; i++){
            uint32_t W1[8], W2[8];
            for(int j = 0; j < R; j++){
                W1[j] = (uint32_t)rng_next();
                W2[j] = (uint32_t)rng_next();
            }
            State256 s1 = sha256_Rrounds_state(W1, R);
            State256 s2 = sha256_Rrounds_state(W2, R);
            State256 d  = state_xor(s1, s2);
            int v = v2(d);
            if(v == 256) continue;   /* identical → skip */
            sum_v += v;
            if(v > max_v) max_v = v;
            if(v == 0) at0++;
            if(v < 4) lt4++;
            if(v < 16) lt16++;
        }
        double mean_v = (double)sum_v / N;
        printf("  %d  | %7.3f  |  %5d  |  %5.2f%%  |  %5.2f%%  |  %5.2f%%\n",
               R, mean_v, max_v,
               100.0 * at0 / N,
               100.0 * lt4 / N,
               100.0 * lt16 / N);
    }

    printf("\nRandom-oracle predictions (geometric distribution):\n");
    printf("  mean v_2 → 1.000   %%(v_2=0) → 50%%   %%(v_2<4) → 93.75%%  %%(v_2<16) → 99.998%%\n");
    printf("\nIf SHA-256 matches from R=1: p-adic sees no structure either.\n");
    printf("If low rounds DEVIATE from geometric: p-adic finds hidden bias\n");
    printf("that Hamming distance averaged out.\n");
}

/* ═══ EXPERIMENT 5: Low-valuation preimage search ═══
 *
 * A novel attack surface: fix an IV and look for W such that
 * v_2(state_R(W) XOR target) is LARGE (bits match in low positions).
 *
 * This is the p-adic version of "find a near-collision".  For a
 * random function, finding v_2 ≥ k requires about 2^k trials on
 * average.  If SHA-256 round function has bias, we may find larger
 * v_2 values cheaper.
 *
 * Measure: best v_2 achieved in 100k random W trials vs the
 * expected maximum under a geometric distribution.
 */
static void experiment_valuation_attack(void){
    printf("\n═══ EXPERIMENT 5: Low-valuation near-collision search ═══\n\n");
    printf("Sample 100k random W, find max v_2(state_R(W) XOR target).\n");
    printf("Random function: expected max v_2 ≈ log₂(N) ≈ 17.\n\n");

    rng_seed(5);

    /* Pick a fixed target */
    uint32_t W_target[8] = {0};
    for(int j = 0; j < 8; j++) W_target[j] = (uint32_t)rng_next();

    printf("  R  | best v_2 found | expected (rand) | ratio | W trials\n");
    printf("  ---+----------------+-----------------+-------+---------\n");

    int N = 100000;
    for(int R = 1; R <= 6; R++){
        State256 target = sha256_Rrounds_state(W_target, R);

        int best_v = 0;
        for(int i = 0; i < N; i++){
            uint32_t W[8];
            for(int j = 0; j < R; j++) W[j] = (uint32_t)rng_next();
            State256 s = sha256_Rrounds_state(W, R);
            int v = v2(state_xor(s, target));
            if(v == 256) v = 256;   /* should never collide fully */
            if(v > best_v) best_v = v;
        }
        double expected = log2((double)N);
        double ratio = (double)best_v / expected;
        printf("  %d  |       %3d      |      %5.2f      | %.2fx |   %d\n",
               R, best_v, expected, ratio, N);
    }

    printf("\nBest v_2 significantly larger than log₂(N) = evidence of bias.\n");
    printf("Ratio ≈ 1 = matches random-oracle baseline.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("P-ADIC HDC: ultrametric topology on bit vectors\n");
    printf("══════════════════════════════════════════\n");
    printf("Tools: p-adic valuation v_2, ultrametric distance, SHA-256 lens\n");

    experiment_ultrametric();
    experiment_isoceles();
    experiment_balls();
    experiment_sha_padic();
    experiment_valuation_attack();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. New metric on HDV space: p-adic valuation\n");
    printf("  2. Ultrametric holds (triangles are isoceles)\n");
    printf("  3. Every point is a ball centre — Cantor-set topology\n");
    printf("  4. SHA-256 lens: does p-adic distance see round structure?\n");
    printf("  5. Low-valuation near-collisions as novel attack surface\n");
    return 0;
}
