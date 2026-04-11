/*
 * CHAINED HDV-GUIDED INVERSION OF SHA-256 (R=2)
 * ===============================================
 *
 * User's idea: at each round the network proposes candidate outcomes;
 * we walk backwards one round at a time. For R=2:
 *
 *   state_2  ─[HDV memory: state_2 → state_1 candidates]─>  state_1*
 *   state_1  ─[analytical: state_1, IV → W_0 (unique)  ]─>  W_0*
 *                                                          +
 *   state_1, state_2 ─[analytical: W_1 unique          ]─>  W_1*
 *
 * Key idea: we don't brute-force W_0, W_1 in 2^64 space.  Instead
 * we enumerate candidate state_1 values — which lie on a much
 * smaller effective manifold after 1 forward round from IV — and
 * for each candidate analytically derive W_0, W_1, verify.
 *
 * HDV memory stores (state_2 → state_1) pairs. Top-K retrieval
 * gives K candidate state_1s; we also do a local Hamming-ball
 * search around each, testing candidate state_1s by applying round 2
 * and comparing to the query.
 *
 * Final verification: given state_1 candidate and target state_2,
 * compute W_1 = state_2.a - (state_1.d + SIG1(state_1.e)
 *                + CH(state_1.e,f,g) + K_1) - SIG0(state_1.a)
 *                - MAJ(state_1.a,b,c)... (derived from round equations).
 *
 * We use a simpler path: for each candidate W_1 (try a few around
 * HDV-suggested value), apply round to state_1 → compare to state_2.
 *
 * Compile: gcc -O3 -march=native -o sha_chain sha256_invert_chain.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

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

typedef struct { uint64_t b[4]; } State256;
static State256 state_pack(const uint32_t S[8]){
    State256 r;
    for(int i = 0; i < 4; i++)
        r.b[i] = ((uint64_t)S[2*i]) | ((uint64_t)S[2*i+1] << 32);
    return r;
}
static void state_unpack(State256 s, uint32_t S[8]){
    for(int i = 0; i < 4; i++){
        S[2*i] = (uint32_t)(s.b[i] & 0xFFFFFFFFu);
        S[2*i+1] = (uint32_t)(s.b[i] >> 32);
    }
}
static inline int state_ham(State256 a, State256 b){
    int d = 0;
    for(int i = 0; i < 4; i++) d += __builtin_popcountll(a.b[i] ^ b.b[i]);
    return d;
}

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

/* ═══ INVERSE ROUND ═══
 * Given state_after and W_t, compute state_before. Round is
 * fully invertible once W_t is known. */
static void sha256_round_inverse(uint32_t S[8], uint32_t Wt, int t){
    uint32_t old_a = S[1], old_b = S[2], old_c = S[3];
    uint32_t old_e = S[5], old_f = S[6], old_g = S[7];
    uint32_t T2 = SIG0(old_a) + MAJ(old_a, old_b, old_c);
    uint32_t T1 = S[0] - T2;
    uint32_t old_d = S[4] - T1;
    uint32_t old_h = T1 - SIG1(old_e) - CH(old_e, old_f, old_g) - K256[t] - Wt;
    S[0] = old_a;
    S[1] = old_b;
    S[2] = old_c;
    S[3] = old_d;
    S[4] = old_e;
    S[5] = old_f;
    S[6] = old_g;
    S[7] = old_h;
}

/* ═══ HDV MEMORY R=1 (state_1 → W_0) ═══ */
#define MEM1_N 200000
typedef struct { State256 state; uint32_t W; } MemR1;
static MemR1 *mem1;

static void build_mem1(void){
    mem1 = malloc(MEM1_N * sizeof(MemR1));
    rng_seed(111);
    for(int i = 0; i < MEM1_N; i++){
        uint32_t W = (uint32_t)rng_next();
        uint32_t S[8]; memcpy(S, IV, sizeof(S));
        sha256_round(S, W, 0);
        mem1[i].state = state_pack(S);
        mem1[i].W = W;
    }
}

/* R=1 inversion via HDV + local ball (reused from Experiment 4 of sha256_invert.c).
 * Returns 1 on success; sets W_out; increments *evals. */
static int invert_r1(State256 target, uint32_t *W_out, uint64_t *evals){
    /* Convert target back to uint32[8] for verification */
    uint32_t target_S[8];
    state_unpack(target, target_S);

    /* Top-10 nearest in mem1 */
    const int TK = 10;
    int dists[10]; int idxs[10];
    for(int i = 0; i < TK; i++){dists[i] = 1<<20; idxs[i] = -1;}
    for(int i = 0; i < MEM1_N; i++){
        int d = state_ham(mem1[i].state, target);
        int mp = 0;
        for(int k = 1; k < TK; k++) if(dists[k] > dists[mp]) mp = k;
        if(d < dists[mp]){dists[mp] = d; idxs[mp] = i;}
    }

    /* For each candidate, local Hamming ball radius ≤ 6 */
    int positions[32];
    for(int k = 0; k < TK; k++){
        uint32_t center = mem1[idxs[k]].W;
        for(int r = 0; r <= 6; r++){
            if(r == 0){
                uint32_t S[8]; memcpy(S, IV, sizeof(S));
                sha256_round(S, center, 0);
                (*evals)++;
                if(state_ham(state_pack(S), target) == 0){
                    *W_out = center;
                    return 1;
                }
                continue;
            }
            for(int i = 0; i < r; i++) positions[i] = i;
            while(1){
                uint32_t mask = 0;
                for(int i = 0; i < r; i++) mask |= 1u << positions[i];
                uint32_t cand = center ^ mask;
                uint32_t S[8]; memcpy(S, IV, sizeof(S));
                sha256_round(S, cand, 0);
                (*evals)++;
                if(state_ham(state_pack(S), target) == 0){
                    *W_out = cand;
                    return 1;
                }
                int ii = r - 1;
                while(ii >= 0 && positions[ii] == 32 - r + ii) ii--;
                if(ii < 0) break;
                positions[ii]++;
                for(int jj = ii + 1; jj < r; jj++) positions[jj] = positions[jj-1] + 1;
            }
        }
    }
    return 0;
}

/* ═══ ANALYTICAL W_t recovery given state_before and state_after ═══
 *
 * Given state_t, state_{t+1}, recover W_t:
 *   T1 = state_{t+1}.a - T2       where T2 = SIG0(state_t.a) + MAJ(state_t.a, b, c)
 *   W_t = T1 - state_t.h - SIG1(state_t.e) - CH(state_t.e, f, g) - K_t
 *
 * Also sanity: state_{t+1}.e = state_t.d + T1  must hold.
 */
static int recover_W(uint32_t S_before[8], uint32_t S_after[8], int t, uint32_t *W_out){
    uint32_t T2 = SIG0(S_before[0]) + MAJ(S_before[0], S_before[1], S_before[2]);
    uint32_t T1 = S_after[0] - T2;
    /* Sanity: S_after[4] = S_before[3] + T1 */
    if((uint32_t)(S_before[3] + T1) != S_after[4]) return 0;
    /* Structural sanity: S_after[1..3,5..7] match S_before[0..2,4..6] */
    if(S_after[1] != S_before[0]) return 0;
    if(S_after[2] != S_before[1]) return 0;
    if(S_after[3] != S_before[2]) return 0;
    if(S_after[5] != S_before[4]) return 0;
    if(S_after[6] != S_before[5]) return 0;
    if(S_after[7] != S_before[6]) return 0;

    uint32_t W = T1 - S_before[7] - SIG1(S_before[4])
               - CH(S_before[4], S_before[5], S_before[6]) - K256[t];
    *W_out = W;
    return 1;
}

/* ═══ TWO-ROUND INVERSION ═══
 *
 * Given target state_2, find (W_0, W_1) such that
 *   state_2 = round_1(round_0(IV, W_0), W_1).
 *
 * Strategy:
 *   1. Enumerate candidate state_1 values via HDV memory for R=2.
 *      mem2[i] stores (state_2_i → state_1_i) for random (W_0, W_1).
 *   2. For each candidate state_1, recover W_0 analytically from
 *      (IV, state_1). Verify: does round_0(IV, W_0) = state_1?
 *   3. Recover W_1 analytically from (state_1, state_2). Verify.
 *   4. If both verify, return (W_0, W_1).
 *
 * If HDV retrieval is close but not exact, we do a local Hamming-ball
 * search around candidate state_1 in 256-bit state space. That's
 * expensive, but the ball we need is small (match is close).
 */
/* mem2w1: store (state_2 → W_1) for random (W_0, W_1).
 * Hypothesis: W_1 is the LAST action, so it correlates more strongly
 * with state_2 than W_0 does (W_0 is filtered through the second round).
 */
#define MEM2_N 500000
typedef struct { State256 state2; uint32_t W1; } MemR2W1;
static MemR2W1 *mem2w1;

static void build_mem2w1(void){
    mem2w1 = malloc(MEM2_N * sizeof(MemR2W1));
    rng_seed(222);
    for(int i = 0; i < MEM2_N; i++){
        uint32_t W0 = (uint32_t)rng_next();
        uint32_t W1 = (uint32_t)rng_next();
        uint32_t S[8]; memcpy(S, IV, sizeof(S));
        sha256_round(S, W0, 0);
        sha256_round(S, W1, 1);
        mem2w1[i].state2 = state_pack(S);
        mem2w1[i].W1 = W1;
    }
}

/* Try to invert 2 rounds using W_1-first HDV retrieval.
 *
 * 1. Retrieve top-TK W_1 candidates from mem2w1 based on state_2 proximity.
 * 2. For each W_1 candidate (and local Hamming ball around it):
 *      state_1 = inv_round(state_2, W_1)
 *      Verify state_1 is reachable from IV by calling invert_r1(state_1).
 *      If invert_r1 succeeds with W_0, we have the full preimage.
 *
 * This breaks 2-round inversion into two 1-round inversions, tied via
 * the fully invertible inverse round function.
 */
static int invert_r2(State256 target2, uint32_t W_out[2], uint64_t *evals){
    /* Retrieve top-TK W_1 candidates from mem2w1 */
    const int TK = 10;
    int dists[10]; int idxs[10];
    for(int i = 0; i < TK; i++){dists[i] = 1<<20; idxs[i] = -1;}
    for(int i = 0; i < MEM2_N; i++){
        int d = state_ham(mem2w1[i].state2, target2);
        int mp = 0;
        for(int k = 1; k < TK; k++) if(dists[k] > dists[mp]) mp = k;
        if(d < dists[mp]){dists[mp] = d; idxs[mp] = i;}
    }

    uint32_t target2_S[8]; state_unpack(target2, target2_S);

    /* For each W_1 candidate, local ball radius ≤ 4 in W_1 space */
    int positions[32];
    for(int k = 0; k < TK; k++){
        uint32_t center = mem2w1[idxs[k]].W1;
        for(int r = 0; r <= 4; r++){
            int inner_break = 0;
            if(r == 0){
                uint32_t W1_cand = center;
                /* Compute state_1 */
                uint32_t S[8]; memcpy(S, target2_S, sizeof(S));
                sha256_round_inverse(S, W1_cand, 1);
                (*evals)++;
                State256 s1_cand = state_pack(S);
                /* Try to invert round 0 → find W_0 */
                uint32_t W0;
                uint64_t sub_evals = 0;
                if(invert_r1(s1_cand, &W0, &sub_evals)){
                    *evals += sub_evals;
                    W_out[0] = W0;
                    W_out[1] = W1_cand;
                    return 1;
                }
                *evals += sub_evals;
                /* Cap sub_evals so we don't burn forever on bad candidates */
                if(*evals > 50000000ULL) return 0;
                continue;
            }
            for(int i = 0; i < r; i++) positions[i] = i;
            while(1){
                uint32_t mask = 0;
                for(int i = 0; i < r; i++) mask |= 1u << positions[i];
                uint32_t W1_cand = center ^ mask;

                uint32_t S[8]; memcpy(S, target2_S, sizeof(S));
                sha256_round_inverse(S, W1_cand, 1);
                (*evals)++;
                State256 s1_cand = state_pack(S);

                uint32_t W0;
                uint64_t sub_evals = 0;
                if(invert_r1(s1_cand, &W0, &sub_evals)){
                    *evals += sub_evals;
                    W_out[0] = W0;
                    W_out[1] = W1_cand;
                    return 1;
                }
                *evals += sub_evals;
                if(*evals > 50000000ULL){inner_break = 1; break;}

                int ii = r - 1;
                while(ii >= 0 && positions[ii] == 32 - r + ii) ii--;
                if(ii < 0) break;
                positions[ii]++;
                for(int jj = ii + 1; jj < r; jj++) positions[jj] = positions[jj-1] + 1;
            }
            if(inner_break) return 0;
        }
    }
    (void)recover_W;
    return 0;
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("CHAINED HDV-GUIDED SHA-256 INVERSION (R=2)\n");
    printf("══════════════════════════════════════════\n");
    printf("Walk backward round-by-round. HDV memory proposes\n");
    printf("state_1 candidates; analytical recovery fills in W_0, W_1.\n");

    printf("\nBuilding memories...\n");
    build_mem1();
    printf("  mem1 (state_1 → W_0): %d entries\n", MEM1_N);
    build_mem2w1();
    printf("  mem2w1 (state_2 → W_1):   %d entries\n", MEM2_N);

    /* SANITY: oracle test. If we hand the true W_1 in directly, does
     * the R=1 inverter find the true W_0? This isolates whether the
     * bottleneck is W_1 retrieval or the R=1 sub-solver. */
    printf("\n--- Sanity: oracle W_1 → R=1 inverter ---\n");
    rng_seed(888);
    {
        int oracle_success = 0;
        uint64_t oracle_total = 0;
        int Q = 30;
        for(int q = 0; q < Q; q++){
            uint32_t W0_true = (uint32_t)rng_next();
            uint32_t W1_true = (uint32_t)rng_next();
            uint32_t S[8]; memcpy(S, IV, sizeof(S));
            sha256_round(S, W0_true, 0);
            State256 s1_true = state_pack(S);
            sha256_round(S, W1_true, 1);
            State256 s2 = state_pack(S);
            (void)s2;
            (void)s1_true;

            /* Use true W_1 to compute s1, pass to invert_r1 */
            uint32_t SS[8]; state_unpack(s2, SS);
            sha256_round_inverse(SS, W1_true, 1);
            State256 s1_from_inv = state_pack(SS);
            /* Should equal s1_true */
            int ok_inv = (state_ham(s1_from_inv, s1_true) == 0);

            uint32_t W0_found;
            uint64_t sub = 0;
            int ok_r1 = invert_r1(s1_from_inv, &W0_found, &sub);
            oracle_total += sub;
            if(ok_inv && ok_r1 && W0_found == W0_true) oracle_success++;
        }
        printf("  Oracle successes: %d/%d\n", oracle_success, Q);
        if(oracle_success > 0)
            printf("  Avg sub-evals:    %.2e\n", (double)oracle_total/oracle_success);
    }

    /* Also: measure W_1 retrieval quality from mem2w1 */
    printf("\n--- Sanity: W_1 retrieval from state_2 ---\n");
    rng_seed(889);
    {
        int Q = 30;
        double sum_best_wh = 0;
        double sum_state_ham = 0;
        int exact = 0;
        for(int q = 0; q < Q; q++){
            uint32_t W0 = (uint32_t)rng_next();
            uint32_t W1 = (uint32_t)rng_next();
            uint32_t S[8]; memcpy(S, IV, sizeof(S));
            sha256_round(S, W0, 0);
            sha256_round(S, W1, 1);
            State256 tgt = state_pack(S);

            int best = 1<<20; int best_wh = 100;
            for(int i = 0; i < MEM2_N; i++){
                int d = state_ham(mem2w1[i].state2, tgt);
                if(d < best){
                    best = d;
                    best_wh = __builtin_popcount(mem2w1[i].W1 ^ W1);
                }
            }
            sum_state_ham += best;
            sum_best_wh += best_wh;
            if(best_wh == 0) exact++;
        }
        printf("  Avg closest state_2 Hamming: %.2f / 256\n", sum_state_ham/Q);
        printf("  Corresponding W_1 Hamming:   %.2f / 32 (random = 16)\n", sum_best_wh/Q);
        printf("  Exact W_1 matches:           %d/%d\n", exact, Q);
    }

    printf("\nRunning %d inversion trials on R=2...\n", 100);
    rng_seed(999);

    int success = 0;
    uint64_t total_evals = 0;
    uint64_t min_evals = ~0ULL, max_evals = 0;

    for(int q = 0; q < 100; q++){
        uint32_t W0_true = (uint32_t)rng_next();
        uint32_t W1_true = (uint32_t)rng_next();
        uint32_t S[8]; memcpy(S, IV, sizeof(S));
        sha256_round(S, W0_true, 0);
        sha256_round(S, W1_true, 1);
        State256 target = state_pack(S);

        uint32_t W_found[2];
        uint64_t evals = 0;
        int ok = invert_r2(target, W_found, &evals);
        if(ok){
            success++;
            total_evals += evals;
            if(evals < min_evals) min_evals = evals;
            if(evals > max_evals) max_evals = evals;
        }
    }

    double brute = 1.84e19; /* 2^64 */
    printf("\nResults:\n");
    printf("  Successes:       %d / 100\n", success);
    if(success){
        double avg = (double)total_evals / success;
        printf("  Avg evals:       %.2e\n", avg);
        printf("  Min/Max:         %llu / %llu\n",
               (unsigned long long)min_evals, (unsigned long long)max_evals);
        printf("  Brute force:     %.2e (2^64)\n", brute);
        printf("  Speedup:         %.2e x\n", brute / avg);
    } else {
        printf("  No successes — HDV retrieval insufficient for R=2.\n");
        printf("  (Would need larger memory or smarter ball search.)\n");
    }

    free(mem1);
    free(mem2w1);
    return 0;
}
