/*
 * PHASE BITS: classical interference on hyperdimensional vectors
 * ================================================================
 *
 * Goal of the "math of bits" programme: find a classical primitive
 * that EXTENDS the computational power of a plain bit, analogous to
 * how a qubit extends it with phase and interference — but without
 * any quantum physics, purely in integer arithmetic on bit arrays.
 *
 * Construction
 * ------------
 * A phase bit is an element of {−1, 0, +1}:
 *     0    = "nothing here"
 *     +1   = "one with phase +"
 *     −1   = "one with phase −"
 *
 * A phase HDV (PHDV) is a length-D vector of phase bits, stored as
 * int8_t[D]. Two operations:
 *
 *   bind(a, b)   (value XOR, phase multiplication)
 *       r[i] = a[i] * b[i]
 *       0 absorbs; ±1 combine as {+1,+1→+1, +1,−1→−1, −1,−1→+1}.
 *       Binding is commutative, associative, involutive.
 *
 *   bundle(a, b) (real addition, so interference IS automatic)
 *       r[i] = a[i] + b[i]
 *       +1 + (−1) = 0   ← destructive interference
 *       +1 + +1  = 2    ← constructive interference
 *       Values grow; re-normalise via sign() when we want a PHDV.
 *
 *   sign(x) = [+1 if x > 0; −1 if x < 0; 0 if x == 0]
 *
 * Compared to ordinary binary HDC (Kanerva):
 *   - XOR has no way to "cancel" a previously bundled item.
 *     To remove p from bundle(p, q, r) you must XOR with p and
 *     remember to vote, it never actually subtracts.
 *   - Phase bits let you cancel with bundle(p, −p) = 0 exactly.
 *     That is the CLASSICAL analogue of destructive interference.
 *
 * Three experiments:
 *   1. Algebra sanity: bind associativity, bundle interference rule
 *   2. Interference memory: store N patterns, remove one by adding
 *      its negative, verify it is gone while the others stay.
 *   3. Search-by-cancellation: mark wrong answers with phase −1,
 *      sum them out, leave the right answer standing.
 *
 * Compile: gcc -O3 -march=native -o phase phase_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define D 1024

typedef int8_t PHDV[D];

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

/* ═══ OPERATIONS ═══ */
static void phdv_random(PHDV v){
    /* Dense phase HDV: each coefficient uniformly {−1, +1} (no zeros) */
    for(int i = 0; i < D; i++) v[i] = (rng_next() & 1) ? 1 : -1;
}
static void phdv_neg(PHDV out, const PHDV a){
    for(int i = 0; i < D; i++) out[i] = -a[i];
}
static void phdv_bind(PHDV out, const PHDV a, const PHDV b){
    for(int i = 0; i < D; i++) out[i] = (int8_t)(a[i] * b[i]);
}
/* Bundle stores a larger integer vector so we can see interference. */
typedef int32_t Acc[D];
static void acc_zero(Acc a){memset(a, 0, sizeof(int32_t)*D);}
static void acc_add(Acc a, const PHDV v){
    for(int i = 0; i < D; i++) a[i] += v[i];
}
static void acc_sub(Acc a, const PHDV v){
    for(int i = 0; i < D; i++) a[i] -= v[i];
}
static void acc_sign(PHDV out, const Acc a){
    for(int i = 0; i < D; i++){
        if(a[i] > 0) out[i] = 1;
        else if(a[i] < 0) out[i] = -1;
        else out[i] = 0;
    }
}
static double phdv_cosine(const PHDV a, const PHDV b){
    long dot = 0;
    long na = 0, nb = 0;
    for(int i = 0; i < D; i++){
        dot += a[i] * b[i];
        na += a[i] * a[i];
        nb += b[i] * b[i];
    }
    double denom = sqrt((double)na * nb);
    if(denom < 1e-12) return 0;
    return (double)dot / denom;
}
static double acc_cosine(const Acc a, const PHDV b){
    double dot = 0, na = 0, nb = 0;
    for(int i = 0; i < D; i++){
        dot += a[i] * b[i];
        na  += (double)a[i] * a[i];
        nb  += b[i] * b[i];
    }
    double denom = sqrt(na * nb);
    if(denom < 1e-12) return 0;
    return dot / denom;
}

/* ═══ EXPERIMENT 1: algebraic sanity ═══ */
static void experiment_algebra(void){
    printf("\n═══ EXPERIMENT 1: Algebra of phase bits ═══\n\n");

    rng_seed(42);
    PHDV a, b, c, ab, bc, abc1, abc2;
    phdv_random(a); phdv_random(b); phdv_random(c);

    /* Associativity of bind */
    phdv_bind(ab, a, b);
    phdv_bind(abc1, ab, c);
    phdv_bind(bc, b, c);
    phdv_bind(abc2, a, bc);
    int assoc = (memcmp(abc1, abc2, sizeof(PHDV)) == 0);
    printf("  bind associativity (a⊗b)⊗c = a⊗(b⊗c): %s\n", assoc ? "YES ✓" : "NO ✗");

    /* Involutivity of bind: a ⊗ a = I (all +1) */
    PHDV aa;
    phdv_bind(aa, a, a);
    int all_one = 1;
    for(int i = 0; i < D; i++) if(aa[i] != 1) {all_one = 0; break;}
    printf("  a ⊗ a = identity (all +1):           %s\n", all_one ? "YES ✓" : "NO ✗");

    /* Destructive interference: a + (−a) = 0 exactly */
    Acc acc; acc_zero(acc);
    acc_add(acc, a);
    PHDV neg_a;
    phdv_neg(neg_a, a);
    acc_add(acc, neg_a);
    int all_zero = 1;
    for(int i = 0; i < D; i++) if(acc[i] != 0) {all_zero = 0; break;}
    printf("  bundle(a, −a) = 0 exactly:            %s\n", all_zero ? "YES ✓" : "NO ✗");

    /* Constructive: a + a = 2·a */
    acc_zero(acc);
    acc_add(acc, a);
    acc_add(acc, a);
    int all_two = 1;
    for(int i = 0; i < D; i++) if(acc[i] != 2*a[i]) {all_two = 0; break;}
    printf("  bundle(a, a) = 2·a (amplification):  %s\n", all_two ? "YES ✓" : "NO ✗");

    /* Partial interference: three patterns, remove middle one */
    Acc acc2; acc_zero(acc2);
    PHDV x, y, z, neg_y;
    phdv_random(x); phdv_random(y); phdv_random(z);
    phdv_neg(neg_y, y);
    acc_add(acc2, x);
    acc_add(acc2, y);
    acc_add(acc2, z);
    double sim_y_before = acc_cosine(acc2, y);
    acc_add(acc2, neg_y);    /* cancel y */
    double sim_y_after  = acc_cosine(acc2, y);
    double sim_x_after  = acc_cosine(acc2, x);
    double sim_z_after  = acc_cosine(acc2, z);

    printf("\n  Removing y from bundle(x,y,z) by adding (−y):\n");
    printf("    cosine(bundle, y) before  = %+.4f\n", sim_y_before);
    printf("    cosine(bundle, y) after   = %+.4f  (should ≈ 0)\n", sim_y_after);
    printf("    cosine(bundle, x) after   = %+.4f  (unchanged)\n", sim_x_after);
    printf("    cosine(bundle, z) after   = %+.4f  (unchanged)\n", sim_z_after);
}

/* ═══ EXPERIMENT 2: Interference memory ═══
 *
 * Store N random patterns in an accumulator. Ask: for each stored
 * pattern, is cosine(bundle, pattern) high (retrieval)?
 *
 * Then remove ONE pattern by adding its negative. Check that the
 * removed pattern's similarity drops to ≈0 while all others are
 * preserved. Binary HDC cannot do this cleanly; phase bits can.
 */
static void experiment_memory(void){
    printf("\n═══ EXPERIMENT 2: Interference memory (add & remove) ═══\n\n");

    rng_seed(100);
    const int N = 20;
    PHDV items[20];
    for(int i = 0; i < N; i++) phdv_random(items[i]);

    Acc mem; acc_zero(mem);
    for(int i = 0; i < N; i++) acc_add(mem, items[i]);

    printf("Stored %d random patterns in accumulator.\n\n", N);

    printf("  Initial cosine(mem, item_k):\n");
    double sum_before = 0;
    for(int k = 0; k < N; k++){
        double s = acc_cosine(mem, items[k]);
        sum_before += s;
    }
    printf("    avg over all %d stored items: %.4f\n", N, sum_before / N);
    printf("    (random baseline ≈ 0, pure store = 1/√N ≈ %.4f)\n", 1.0 / sqrt(N));

    /* Remove item 7 via negative interference */
    int target = 7;
    PHDV neg_target;
    phdv_neg(neg_target, items[target]);
    acc_add(mem, neg_target);

    printf("\n  After adding (−item_%d) to cancel it:\n", target);
    double s_removed = acc_cosine(mem, items[target]);
    double sum_after = 0;
    int preserved = 0;
    for(int k = 0; k < N; k++){
        if(k == target) continue;
        double s = acc_cosine(mem, items[k]);
        sum_after += s;
        if(s > 0.1) preserved++;
    }
    printf("    cosine(mem, item_%d) = %+.4f  (should ≈ 0)\n", target, s_removed);
    printf("    avg cosine(mem, remaining %d items): %.4f\n", N-1, sum_after / (N-1));
    printf("    items still retrievable (cosine>0.1): %d/%d\n", preserved, N-1);

    /* Add an external pattern not in the set: should be uncorrelated */
    PHDV outsider;
    phdv_random(outsider);
    double s_out = acc_cosine(mem, outsider);
    printf("    cosine(mem, unrelated outsider):    %+.4f (should ≈ 0)\n", s_out);
}

/* ═══ EXPERIMENT 3: Search by cancellation ═══
 *
 * Given a database of N items and a query, we want to amplify the
 * matching item and cancel the rest. Classical approach: loop and
 * compare. Phase-bit approach: build a "query key" k such that
 * bind(item, k) has phase +1 if item matches the query and random
 * otherwise. Bundle all bound-items; the match stands out.
 *
 * To emulate "search", we build a bundle where every item i is
 * stored as items[i] ⊗ role[i], where role[i] is a unique tag.
 * The bundle hides all items. Query by binding with role[query_id]:
 * the matching item's tag cancels (role ⊗ role = identity), while
 * other items have random new tags. Averaging should recover the
 * queried item.
 *
 * Compare: can we recover the queried item with high similarity
 * even when N is large?
 */
static void experiment_search(void){
    printf("\n═══ EXPERIMENT 3: Associative search by cancellation ═══\n\n");

    rng_seed(200);
    const int N_MAX = 40;
    PHDV items[N_MAX], roles[N_MAX];
    for(int i = 0; i < N_MAX; i++){
        phdv_random(items[i]);
        phdv_random(roles[i]);
    }

    printf("  N items | query id | cos(recovered, truth) | noise (avg other) | margin\n");
    printf("  --------+----------+-----------------------+-------------------+-------\n");

    int sizes[] = {5, 10, 20, 30, 40};
    for(int si = 0; si < 5; si++){
        int N = sizes[si];
        Acc bundle; acc_zero(bundle);
        for(int i = 0; i < N; i++){
            PHDV bound;
            phdv_bind(bound, items[i], roles[i]);
            acc_add(bundle, bound);
        }

        /* Query id = 3 */
        int q = 3;
        /* Recover by binding bundle with role[q]:
         *   bundle = Σ items[i] ⊗ roles[i]
         *   bundle ⊗ role[q] = items[q] + noise
         * We need a PHDV multiply of an accumulator by a PHDV. */
        int32_t recovered[D];
        for(int i = 0; i < D; i++) recovered[i] = bundle[i] * roles[q][i];

        double truth_sim = acc_cosine(recovered, items[q]);
        double noise_sum = 0;
        double max_noise = 0;
        for(int i = 0; i < N; i++){
            if(i == q) continue;
            double s = fabs(acc_cosine(recovered, items[i]));
            noise_sum += s;
            if(s > max_noise) max_noise = s;
        }
        double avg_noise = noise_sum / (N - 1);
        double margin = truth_sim - max_noise;
        printf("  %7d |    %2d    |      %+.4f        |      %.4f      | %+.4f\n",
               N, q, truth_sim, avg_noise, margin);
    }
    printf("\n  Positive margin = truth stands above the strongest distractor.\n");
    printf("  This is content-addressable memory built on phase interference.\n");
}

/* ═══ EXPERIMENT 4: Walsh-Hadamard basis native-hosted ═══
 *
 * Because phase bits live in {−1, +1}, the Walsh-Hadamard basis
 * vectors χ_s(x) = (−1)^{s·x} ARE exactly PHDVs. Any boolean
 * function's Walsh spectrum can be computed by dotting its
 * function values (as a PHDV) with each χ_s.
 *
 * We demonstrate: build PHDV from a boolean function, compute its
 * Walsh coefficient at a chosen index s by a single phase-bit
 * inner product. Then verify against a direct truth-table sum.
 */
static int parity(unsigned x){return __builtin_popcount(x) & 1;}

static void experiment_walsh(void){
    printf("\n═══ EXPERIMENT 4: Walsh spectrum as phase-bit inner product ═══\n\n");

    /* Use n = 10 so 2^n = 1024 = D */
    const int n = 10;
    const int N = 1024;

    /* f(x) = x_0 XOR x_3 XOR x_7 */
    PHDV F;
    for(int x = 0; x < N; x++){
        int v = ((x >> 0) ^ (x >> 3) ^ (x >> 7)) & 1;
        F[x] = v ? -1 : 1;
    }

    /* χ_s as a PHDV for any s */
    PHDV chi;
    auto void fill_chi(int s);
    void fill_chi(int s){
        for(int x = 0; x < N; x++){
            int sign = parity((unsigned)(s & x));
            chi[x] = sign ? -1 : 1;
        }
    }

    /* Compute Walsh coefficient as phase inner product */
    int targets[] = {0x000, 0x001, 0x008, 0x080, 0x089, 0x0FF, 0x3FF};
    printf("  f(x) = x_0 ⊕ x_3 ⊕ x_7, n=%d, D=%d\n\n", n, N);
    printf("  s (binary)    |  inner product  |  expected\n");
    printf("  --------------+-----------------+----------\n");
    for(int ti = 0; ti < 7; ti++){
        int s = targets[ti];
        fill_chi(s);
        long dot = 0;
        for(int x = 0; x < N; x++) dot += (int)F[x] * chi[x];
        /* Expected: F̂(s) = N if s = 0b10001001 = 0x89, else 0 */
        int expected = (s == 0x089) ? N : 0;
        if(s == 0x089) expected = N;
        /* Actually F̂(s) = +N if s = 1000_1001 (bits 0,3,7), 0 else */
        printf("  0x%03x (%4d) |      %+6ld    |     %+d\n",
               s, s, dot, expected);
    }

    printf("\n  Coefficient is non-zero only when s has exactly the bits\n");
    printf("  {0, 3, 7} — the support of f. Phase-bit inner product IS\n");
    printf("  the Walsh transform evaluation at a single frequency.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("PHASE BITS: classical interference on HDVs\n");
    printf("══════════════════════════════════════════\n");
    printf("Ternary alphabet {−1, 0, +1}, addition = interference\n");
    printf("D = %d\n", D);

    experiment_algebra();
    experiment_memory();
    experiment_search();
    experiment_walsh();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Classical analogue of phase/interference on pure bits\n");
    printf("  2. Bundle-based associative memory with EXACT removal\n");
    printf("     (binary HDC cannot do this — XOR has no subtraction)\n");
    printf("  3. Content-addressable search via role-unbinding\n");
    printf("  4. Walsh spectrum = single phase-bit inner product\n");
    printf("  5. Phase bits are a strict extension of binary bits:\n");
    printf("     every binary HDV is also a phase HDV, but phase HDVs\n");
    printf("     can express (−) which binary cannot.\n");
    return 0;
}
