/*
 * HYPERDIMENSIONAL COMPUTING: bits as symbols
 * =============================================
 *
 * The RIGHT framework for "bits as neurons on standard hardware":
 * Kanerva (1988), developed since 2000.
 *
 * Each concept = random binary vector of dimension D (e.g., 10000)
 *   - 10000 bits = 1250 bytes per concept
 *   - Operations are BITWISE (fast on any CPU)
 *   - Binding: XOR
 *   - Bundling: majority
 *   - Similarity: Hamming distance
 *
 * Properties:
 *   - Nearly orthogonal random vectors (distance ~ D/2)
 *   - Bundle retains similarity to components
 *   - Bind creates approximately orthogonal new symbol
 *   - Distributed representation: no single bit is critical
 *
 * Tests:
 *   1. XOR learning (classic test)
 *   2. Parity learning
 *   3. Associative memory
 *   4. Multi-class classification
 *
 * Compile: gcc -O3 -march=native -o hdc hdc.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>

#define D 10000  /* hyperdimension */
#define D_WORDS ((D + 63) / 64)

typedef struct {
    uint64_t bits[D_WORDS];
} HDV;  /* Hyperdimensional Vector */

/* RNG */
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

/* Create random binary hypervector */
static HDV hdv_random(void){
    HDV v;
    for(int i = 0; i < D_WORDS; i++) v.bits[i] = rng_next();
    return v;
}

static HDV hdv_zero(void){
    HDV v;
    memset(&v, 0, sizeof(v));
    return v;
}

/* Binding: XOR (creates approximately orthogonal new symbol) */
static HDV hdv_bind(HDV a, HDV b){
    HDV r;
    for(int i = 0; i < D_WORDS; i++) r.bits[i] = a.bits[i] ^ b.bits[i];
    return r;
}

/* Hamming distance */
static int hdv_hamming(HDV a, HDV b){
    int d = 0;
    for(int i = 0; i < D_WORDS; i++)
        d += __builtin_popcountll(a.bits[i] ^ b.bits[i]);
    return d;
}

/* Similarity: 0 (opposite) to 1 (identical) */
static double hdv_similarity(HDV a, HDV b){
    return 1.0 - (double)hdv_hamming(a, b) / D;
}

/* Bundling: majority vote of multiple vectors
 * Uses counters since majority is not associative */
typedef struct {
    int counters[D];
    int n;
} HDVBundle;

static void hdvb_init(HDVBundle *b){
    memset(b, 0, sizeof(*b));
}

static void hdvb_add(HDVBundle *b, HDV v){
    for(int i = 0; i < D; i++){
        int bit = (v.bits[i >> 6] >> (i & 63)) & 1;
        b->counters[i] += bit ? 1 : -1;
    }
    b->n++;
}

static HDV hdvb_finalize(HDVBundle *b){
    HDV r = hdv_zero();
    for(int i = 0; i < D; i++){
        if(b->counters[i] > 0){
            r.bits[i >> 6] |= (1ULL << (i & 63));
        }
    }
    return r;
}

/* ═══ TEST 1: XOR ═══ */

static int test_xor(void){
    printf("\nTEST 1: XOR via HDC\n");
    printf("───────────────────\n");

    rng_seed(42);

    /* Create random hypervectors for 0 and 1 */
    HDV V[2];
    V[0] = hdv_random();
    V[1] = hdv_random();

    /* Train: store each XOR example as bound representation */
    int xor_table[4][3] = {{0,0,0}, {0,1,1}, {1,0,1}, {1,1,0}};

    /* Bundle for "XOR=0" and "XOR=1" */
    HDVBundle b0, b1;
    hdvb_init(&b0);
    hdvb_init(&b1);

    for(int t = 0; t < 4; t++){
        int x1 = xor_table[t][0];
        int x2 = xor_table[t][1];
        int y = xor_table[t][2];
        /* Bind the inputs together */
        HDV input = hdv_bind(V[x1], V[x2]);
        if(y == 0) hdvb_add(&b0, input);
        else hdvb_add(&b1, input);
    }

    HDV proto0 = hdvb_finalize(&b0);
    HDV proto1 = hdvb_finalize(&b1);

    /* Test */
    int correct = 0;
    for(int t = 0; t < 4; t++){
        int x1 = xor_table[t][0];
        int x2 = xor_table[t][1];
        int y = xor_table[t][2];

        HDV input = hdv_bind(V[x1], V[x2]);
        double s0 = hdv_similarity(input, proto0);
        double s1 = hdv_similarity(input, proto1);
        int pred = (s1 > s0) ? 1 : 0;

        printf("  (%d,%d)->%d: pred=%d sim0=%.3f sim1=%.3f %s\n",
               x1, x2, y, pred, s0, s1, pred==y?"OK":"WRONG");
        if(pred == y) correct++;
    }

    printf("  Result: %d/4 correct\n", correct);
    return correct == 4;
}

/* ═══ TEST 2: PARITY ═══ */

static int test_parity(int n){
    printf("\nTEST 2: Parity of %d bits via HDC\n", n);
    printf("──────────────────────────────────\n");

    rng_seed(123);

    /* Random vectors for 0 and 1 */
    HDV V[2];
    V[0] = hdv_random();
    V[1] = hdv_random();

    /* For each position, a "position" vector */
    HDV pos[32];
    for(int i = 0; i < 32; i++) pos[i] = hdv_random();

    /* Train: bundle all examples with even and odd parity */
    HDVBundle beven, bodd;
    hdvb_init(&beven);
    hdvb_init(&bodd);

    int n_ex = 1 << n;
    for(int ex = 0; ex < n_ex; ex++){
        /* Bind each bit to its position */
        HDV rep = hdv_zero();
        int parity = 0;
        for(int i = 0; i < n; i++){
            int bit = (ex >> i) & 1;
            parity ^= bit;
            HDV contrib = hdv_bind(V[bit], pos[i]);
            rep = hdv_bind(rep, contrib); /* bind all contributions */
        }

        if(parity == 0) hdvb_add(&beven, rep);
        else hdvb_add(&bodd, rep);
    }

    HDV proto_even = hdvb_finalize(&beven);
    HDV proto_odd = hdvb_finalize(&bodd);

    /* Test */
    int correct = 0;
    for(int ex = 0; ex < n_ex; ex++){
        HDV rep = hdv_zero();
        int parity = 0;
        for(int i = 0; i < n; i++){
            int bit = (ex >> i) & 1;
            parity ^= bit;
            HDV contrib = hdv_bind(V[bit], pos[i]);
            rep = hdv_bind(rep, contrib);
        }

        double se = hdv_similarity(rep, proto_even);
        double so = hdv_similarity(rep, proto_odd);
        int pred = (so > se) ? 1 : 0;
        if(pred == parity) correct++;
    }

    printf("  Result: %d/%d correct (%.0f%%)\n", correct, n_ex, 100.0*correct/n_ex);
    return correct >= n_ex * 0.75;
}

/* ═══ TEST 3: MULTI-CLASS CLASSIFICATION ═══ */

/* Classify random patterns into K classes */
static int test_classification(int K, int n_features){
    printf("\nTEST 3: %d-class classification, %d features\n", K, n_features);
    printf("────────────────────────────────────────────\n");

    rng_seed(456);

    /* Feature value vectors */
    HDV features[32][2]; /* features[i][0] and features[i][1] */
    for(int i = 0; i < n_features; i++){
        features[i][0] = hdv_random();
        features[i][1] = hdv_random();
    }

    /* Position vectors for each feature */
    HDV fpos[32];
    for(int i = 0; i < n_features; i++) fpos[i] = hdv_random();

    /* Generate K "prototype" patterns */
    int prototypes[16][32];
    for(int c = 0; c < K; c++){
        for(int i = 0; i < n_features; i++){
            prototypes[c][i] = rng_next() & 1;
        }
    }

    /* Training: for each class, bundle examples that are near its prototype */
    HDVBundle class_bundles[16];
    for(int c = 0; c < K; c++) hdvb_init(&class_bundles[c]);

    int n_train = 50 * K;
    for(int ex = 0; ex < n_train; ex++){
        int c = rng_next() % K;
        /* Create noisy version of prototype */
        int pattern[32];
        for(int i = 0; i < n_features; i++){
            pattern[i] = prototypes[c][i];
            if((rng_next() % 100) < 10) pattern[i] = 1 - pattern[i]; /* 10% noise */
        }

        /* Encode as HDV */
        HDV rep = hdv_zero();
        for(int i = 0; i < n_features; i++){
            HDV contrib = hdv_bind(features[i][pattern[i]], fpos[i]);
            rep = hdv_bind(rep, contrib);
        }

        hdvb_add(&class_bundles[c], rep);
    }

    HDV class_protos[16];
    for(int c = 0; c < K; c++) class_protos[c] = hdvb_finalize(&class_bundles[c]);

    /* Test: classify fresh noisy examples */
    int n_test = 200;
    int correct = 0;
    for(int ex = 0; ex < n_test; ex++){
        int true_c = rng_next() % K;
        int pattern[32];
        for(int i = 0; i < n_features; i++){
            pattern[i] = prototypes[true_c][i];
            if((rng_next() % 100) < 10) pattern[i] = 1 - pattern[i];
        }

        HDV rep = hdv_zero();
        for(int i = 0; i < n_features; i++){
            HDV contrib = hdv_bind(features[i][pattern[i]], fpos[i]);
            rep = hdv_bind(rep, contrib);
        }

        /* Find nearest class */
        int best_c = 0;
        double best_sim = -1;
        for(int c = 0; c < K; c++){
            double s = hdv_similarity(rep, class_protos[c]);
            if(s > best_sim){
                best_sim = s;
                best_c = c;
            }
        }
        if(best_c == true_c) correct++;
    }

    double acc = 100.0 * correct / n_test;
    printf("  Accuracy: %d/%d (%.1f%%)\n", correct, n_test, acc);
    return acc >= 80.0;
}

/* ═══ TEST 4: ASSOCIATIVE RECALL ═══ */

static int test_recall(void){
    printf("\nTEST 4: Associative recall (key→value pairs)\n");
    printf("─────────────────────────────────────────────\n");

    rng_seed(789);

    /* Store 20 key-value pairs */
    int n_pairs = 20;
    HDV keys[20], values[20];
    for(int i = 0; i < n_pairs; i++){
        keys[i] = hdv_random();
        values[i] = hdv_random();
    }

    /* Memory: bundle all (key ⊗ value) */
    HDVBundle memory;
    hdvb_init(&memory);
    for(int i = 0; i < n_pairs; i++){
        HDV pair = hdv_bind(keys[i], values[i]);
        hdvb_add(&memory, pair);
    }
    HDV mem = hdvb_finalize(&memory);

    /* Recall: for each key, extract value by binding with memory */
    int correct = 0;
    for(int i = 0; i < n_pairs; i++){
        HDV recalled = hdv_bind(keys[i], mem);

        /* Find which value is most similar */
        int best = 0;
        double best_sim = -1;
        for(int j = 0; j < n_pairs; j++){
            double s = hdv_similarity(recalled, values[j]);
            if(s > best_sim){
                best_sim = s;
                best = j;
            }
        }
        if(best == i) correct++;
    }

    printf("  Correctly recalled: %d/%d\n", correct, n_pairs);
    return correct >= n_pairs * 0.9;
}

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("HYPERDIMENSIONAL COMPUTING with bits\n");
    printf("═══════════════════════════════════════════\n");
    printf("Dimension: %d bits (%d bytes per vector)\n", D, D/8);

    int t1 = test_xor();
    int t2a = test_parity(3);
    int t2b = test_parity(4);
    int t2c = test_parity(5);
    int t3a = test_classification(3, 10);
    int t3b = test_classification(5, 15);
    int t4 = test_recall();

    printf("\n═══ SUMMARY ═══\n");
    printf("XOR:                %s\n", t1 ? "PASS" : "FAIL");
    printf("Parity-3:           %s\n", t2a ? "PASS" : "FAIL");
    printf("Parity-4:           %s\n", t2b ? "PASS" : "FAIL");
    printf("Parity-5:           %s\n", t2c ? "PASS" : "FAIL");
    printf("3-class classify:   %s\n", t3a ? "PASS" : "FAIL");
    printf("5-class classify:   %s\n", t3b ? "PASS" : "FAIL");
    printf("Associative recall: %s\n", t4 ? "PASS" : "FAIL");

    return 0;
}
