/*
 * BITBRAIN v5.1: add ATTENTION to v5
 * ====================================
 *
 * New: attention mask that filters irrelevant input bits.
 *   - Mask A[i] ∈ {0,1}: 1 = attend to this bit
 *   - Learned via correlation between input bit and target
 *   - Filtered input = input × A (bitwise AND)
 *
 * Test: parity of first 4 bits, last 4 are noise.
 *   Without attention: sensory struggles with 8 bits
 *   With attention: learns mask, applies to 4 bits
 *
 * Preserves: all v5 functionality (consolidation, memory, routing)
 *
 * Compile: gcc -O3 -march=native -o bitbrain5_1 bitbrain_v5_1.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)
#define MAX_MEMORY 100

#define S_IN 8       /* now 8 inputs */
#define S_H1 32
#define S_H2 16

typedef struct { uint64_t b[HDV_WORDS]; } HDV;

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

static HDV hdv_random(void){HDV v;for(int i=0;i<HDV_WORDS;i++)v.b[i]=rng_next();return v;}
static HDV hdv_zero(void){HDV v;memset(&v,0,sizeof(v));return v;}
static HDV hdv_bind(HDV a,HDV b){HDV r;for(int i=0;i<HDV_WORDS;i++)r.b[i]=a.b[i]^b.b[i];return r;}
static int hdv_ham(HDV a,HDV b){int d=0;for(int i=0;i<HDV_WORDS;i++)d+=__builtin_popcountll(a.b[i]^b.b[i]);return d;}
static double hdv_sim(HDV a,HDV b){return 1.0-(double)hdv_ham(a,b)/HDV_BITS;}

static HDV V_bit[2];
static HDV V_pos[16];

static HDV encode_bits(const int8_t *bits, int n){
    int counters[HDV_BITS] = {0};
    for(int i = 0; i < n; i++){
        int v = bits[i]==1 ? 1 : 0;
        HDV c = hdv_bind(V_bit[v], V_pos[i]);
        for(int k = 0; k < HDV_BITS; k++){
            counters[k] += ((c.b[k>>6] >> (k&63)) & 1) ? 1 : -1;
        }
    }
    HDV r = hdv_zero();
    for(int k = 0; k < HDV_BITS; k++){
        if(counters[k] > 0) r.b[k>>6] |= (1ULL << (k&63));
    }
    return r;
}

/* ═══ ATTENTION region (NEW in v5.1, fixed) ═══
 *
 * Uses SENSITIVITY: for each bit, how often does flipping it change the target?
 *
 * For parity-4-with-noise:
 *   Bits 0-3 (relevant): flipping ALWAYS changes target → sensitivity = 1.0
 *   Bits 4-7 (noise):     flipping NEVER changes target → sensitivity = 0.0
 *
 * This works for arbitrary boolean functions, not just correlated ones.
 */
typedef struct {
    int sensitivity[S_IN];  /* number of times flipping this bit changed target */
    int n_samples;
    int8_t mask[S_IN];
} Attention;

static void attention_init(Attention *a){
    for(int i = 0; i < S_IN; i++){
        a->sensitivity[i] = 0;
        a->mask[i] = 1;
    }
    a->n_samples = 0;
}

/* During training, we also see the TARGET for flipped versions.
 * We use pairs of examples: if input A and B differ only in bit i,
 * and their targets differ, then bit i is relevant. */
static void attention_update_pairwise(Attention *a, const int8_t *in1, int t1,
                                       const int8_t *in2, int t2){
    /* Find differing bits */
    int diff_bits[S_IN];
    int n_diff = 0;
    for(int i = 0; i < S_IN; i++){
        if(in1[i] != in2[i]){
            diff_bits[n_diff++] = i;
        }
    }
    /* If exactly one bit differs, we know that bit's sensitivity */
    if(n_diff == 1){
        if(t1 != t2) a->sensitivity[diff_bits[0]]++;
        a->n_samples++;
    }
    /* For multi-bit differences: couldn't isolate, skip */
}

/* Alternative: use the full labeled dataset to compute sensitivity exactly */
static void attention_compute_from_data(Attention *a, int8_t inputs[][S_IN],
                                          int *targets, int n){
    memset(a->sensitivity, 0, sizeof(a->sensitivity));
    /* For each pair that differs in exactly one bit */
    for(int i = 0; i < n; i++){
        for(int j = i+1; j < n; j++){
            int n_diff = 0, diff_bit = -1;
            for(int k = 0; k < S_IN; k++){
                if(inputs[i][k] != inputs[j][k]){
                    n_diff++;
                    diff_bit = k;
                }
            }
            if(n_diff == 1){
                if(targets[i] != targets[j]) a->sensitivity[diff_bit]++;
                a->n_samples++;
            }
        }
    }

    /* Mask: bits with high sensitivity are relevant */
    int max_sens = 0;
    for(int i = 0; i < S_IN; i++) if(a->sensitivity[i] > max_sens) max_sens = a->sensitivity[i];
    for(int i = 0; i < S_IN; i++){
        a->mask[i] = (a->sensitivity[i] * 3 >= max_sens * 2) ? 1 : 0;
    }
}

/* Keep legacy name for compatibility */
static void attention_update(Attention *a, const int8_t *in, int target){
    (void)a; (void)in; (void)target;
    /* No-op; use attention_compute_from_data instead */
}

/* Apply attention: multiply input by mask (irrelevant bits → 0) */
static void attention_apply(Attention *a, const int8_t *in, int8_t *out){
    for(int i = 0; i < S_IN; i++){
        out[i] = a->mask[i] ? in[i] : 0;
    }
}

static int attention_count(Attention *a){
    int c = 0;
    for(int i = 0; i < S_IN; i++) if(a->mask[i]) c++;
    return c;
}

/* ═══ SENSORY ═══ */
typedef struct {
    int8_t W1[S_IN][S_H1];
    int8_t W2[S_H1][S_H2];
    int8_t W3[S_H2];
    int flip_prob;
} Sensory;

static void sensory_init(Sensory *s){
    for(int i=0;i<S_IN;i++) for(int j=0;j<S_H1;j++) s->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<S_H1;i++) for(int j=0;j<S_H2;j++) s->W2[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<S_H2;i++) s->W3[i] = (rng_next()&1)?1:-1;
    s->flip_prob = 30;
}

static int8_t sensory_forward(Sensory *s, const int8_t *in, int *confidence){
    int8_t h1[S_H1], h2[S_H2];
    for(int j=0;j<S_H1;j++){
        int sum=0;for(int i=0;i<S_IN;i++) sum += s->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<S_H2;j++){
        int sum=0;for(int i=0;i<S_H1;i++) sum += s->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int sum = 0;
    for(int i=0;i<S_H2;i++) sum += s->W3[i]*h2[i];
    if(confidence) *confidence = abs(sum);
    return (sum>=0)?1:-1;
}

static void sensory_train_one(Sensory *s, const int8_t *in, int target){
    int8_t h1[S_H1], h2[S_H2];
    for(int j=0;j<S_H1;j++){
        int sum=0;for(int i=0;i<S_IN;i++) sum += s->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<S_H2;j++){
        int sum=0;for(int i=0;i<S_H1;i++) sum += s->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int out_sum = 0;
    for(int i=0;i<S_H2;i++) out_sum += s->W3[i]*h2[i];
    int out = (out_sum>=0)?1:-1;
    if(out == target) return;

    int8_t want_h2[S_H2] = {0};
    for(int i=0;i<S_H2;i++){
        int contrib = s->W3[i]*h2[i];
        if(contrib != target){
            if((int)(rng_next()%100) < s->flip_prob) s->W3[i] = -s->W3[i];
        }
        want_h2[i] = target * s->W3[i];
    }

    int8_t want_h1[S_H1] = {0};
    for(int j=0;j<S_H2;j++){
        if(want_h2[j] == h2[j]) continue;
        for(int i=0;i<S_H1;i++){
            int contrib = s->W2[i][j]*h1[i];
            if(contrib != want_h2[j]){
                if((int)(rng_next()%100) < s->flip_prob) s->W2[i][j] = -s->W2[i][j];
            }
        }
        for(int i=0;i<S_H1;i++){
            int w = s->W2[i][j];
            int wnt = want_h2[j]*w;
            if(want_h1[i] == 0) want_h1[i] = wnt;
            else if(want_h1[i] != wnt) want_h1[i] = 0;
        }
    }

    for(int j=0;j<S_H1;j++){
        if(want_h1[j] == 0 || want_h1[j] == h1[j]) continue;
        for(int i=0;i<S_IN;i++){
            int contrib = s->W1[i][j]*in[i];
            if(contrib != want_h1[j]){
                if((int)(rng_next()%100) < s->flip_prob) s->W1[i][j] = -s->W1[i][j];
            }
        }
    }
}

/* ═══ MEMORY ═══ */
typedef struct {
    HDV keys[MAX_MEMORY];
    int8_t values[MAX_MEMORY];
    int hit_count[MAX_MEMORY];
    int n;
} Memory;

static void memory_init(Memory *m){ m->n = 0; }

static int memory_find_closest(Memory *m, HDV key, double *sim_out){
    if(m->n == 0){if(sim_out)*sim_out=0; return -1;}
    int best = 0;
    double best_sim = -1;
    for(int i = 0; i < m->n; i++){
        double s = hdv_sim(key, m->keys[i]);
        if(s > best_sim){best_sim = s; best = i;}
    }
    if(sim_out) *sim_out = best_sim;
    return best;
}

static void memory_store(Memory *m, HDV key, int8_t val){
    double sim;
    int closest = memory_find_closest(m, key, &sim);
    if(closest >= 0 && sim > 0.95){
        m->values[closest] = val;
        m->hit_count[closest]++;
        return;
    }
    if(m->n >= MAX_MEMORY){
        int min_idx = 0;
        for(int i = 1; i < m->n; i++){
            if(m->hit_count[i] < m->hit_count[min_idx]) min_idx = i;
        }
        m->keys[min_idx] = key;
        m->values[min_idx] = val;
        m->hit_count[min_idx] = 1;
        return;
    }
    m->keys[m->n] = key;
    m->values[m->n] = val;
    m->hit_count[m->n] = 1;
    m->n++;
}

static int8_t memory_recall(Memory *m, HDV key, double *sim_out){
    int idx = memory_find_closest(m, key, sim_out);
    if(idx < 0) return 1;
    m->hit_count[idx]++;
    return m->values[idx];
}

/* ═══ BITBRAIN v5.1 ═══ */
typedef struct {
    Attention attention; /* NEW */
    Sensory sensory;
    Memory memory;
    int n_consolidations;
} BitBrain;

static void brain_init(BitBrain *b){
    attention_init(&b->attention);
    sensory_init(&b->sensory);
    memory_init(&b->memory);
    b->n_consolidations = 0;
}

/* Process: apply attention → sensory/memory routing */
static int8_t brain_process(BitBrain *b, const int8_t *input, HDV key,
                             const char **route, int *out_conf){
    /* Apply attention to input */
    int8_t filtered[S_IN];
    attention_apply(&b->attention, input, filtered);

    double mem_sim;
    int8_t mem_val = memory_recall(&b->memory, key, &mem_sim);
    int sen_conf;
    int8_t sen_val = sensory_forward(&b->sensory, filtered, &sen_conf);

    if(mem_sim >= 0.97){
        if(route) *route = "MEM";
        if(out_conf) *out_conf = (int)(mem_sim * 100);
        return mem_val;
    }
    if(route) *route = "SEN";
    if(out_conf) *out_conf = sen_conf;
    return sen_val;
}

/* Learn: update attention AND sensory */
static void brain_learn(BitBrain *b, const int8_t *input, HDV key, int target){
    /* Update attention based on raw input */
    attention_update(&b->attention, input, target);

    /* Apply attention then train sensory */
    int8_t filtered[S_IN];
    attention_apply(&b->attention, input, filtered);
    sensory_train_one(&b->sensory, filtered, target);
    (void)key;
}

static int brain_consolidate(BitBrain *b, int8_t inputs[][S_IN], int *targets,
                              int n_ex, HDV *keys){
    int new_cons = 0;
    for(int i = 0; i < n_ex; i++){
        int8_t filtered[S_IN];
        attention_apply(&b->attention, inputs[i], filtered);
        int conf;
        int8_t pred = sensory_forward(&b->sensory, filtered, &conf);
        if(pred != targets[i]){
            double sim;
            int idx = memory_find_closest(&b->memory, keys[i], &sim);
            if(idx < 0 || sim < 0.97){
                memory_store(&b->memory, keys[i], targets[i]);
                b->n_consolidations++;
                new_cons++;
            }
        }
    }
    return new_cons;
}

/* ═══ TEST: parity with noise bits ═══ */
int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v5.1: + ATTENTION mechanism\n");
    printf("══════════════════════════════════════════\n\n");

    rng_seed(42);
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < 16; i++) V_pos[i] = hdv_random();

    BitBrain brain;
    brain_init(&brain);

    /* Task: 8-bit input, target = parity of first 4 bits, last 4 are noise */
    printf("Task: Parity-4-with-noise (8 input bits, only first 4 matter)\n");
    printf("256 possible inputs (but target depends only on first 4)\n\n");

    /* Generate all 256 examples */
    int8_t inputs[256][8];
    int targets[256];
    for(int m = 0; m < 256; m++){
        for(int i = 0; i < 8; i++) inputs[m][i] = ((m>>i)&1)?1:-1;
        targets[m] = inputs[m][0] * inputs[m][1] * inputs[m][2] * inputs[m][3];
    }

    HDV keys[256];
    for(int m = 0; m < 256; m++) keys[m] = encode_bits(inputs[m], 8);

    /* FIRST: compute attention mask from pairwise data */
    printf("Step 1: Compute attention from data (sensitivity analysis)...\n");
    attention_compute_from_data(&brain.attention, inputs, targets, 256);
    printf("  Sensitivity per bit: ");
    for(int i = 0; i < 8; i++) printf("%d ", brain.attention.sensitivity[i]);
    printf("\n");
    printf("  Learned mask:        ");
    for(int i = 0; i < 8; i++) printf("%d", brain.attention.mask[i]);
    printf(" (%d/8 bits attended)\n\n", attention_count(&brain.attention));

    printf("Step 2: Training (sensory + attention + consolidation):\n");
    int best = 0;
    for(int epoch = 0; epoch < 500; epoch++){
        int order[256];
        for(int i = 0; i < 256; i++) order[i] = i;
        for(int i = 255; i > 0; i--){
            int j = rng_next() % (i+1);
            int t = order[i]; order[i] = order[j]; order[j] = t;
        }
        for(int e = 0; e < 256; e++){
            int idx = order[e];
            brain_learn(&brain, inputs[idx], keys[idx], targets[idx]);
        }

        if(epoch > 30 && brain.sensory.flip_prob > 5) brain.sensory.flip_prob--;

        if(epoch >= 50 && epoch % 30 == 0){
            brain_consolidate(&brain, inputs, targets, 256, keys);
        }

        int correct = 0;
        for(int m = 0; m < 256; m++){
            const char *r; int c;
            int8_t pred = brain_process(&brain, inputs[m], keys[m], &r, &c);
            if(pred == targets[m]) correct++;
        }
        if(correct > best){
            best = correct;
            if(correct >= 200 || epoch % 20 == 0 || correct == 256){
                printf("  Epoch %3d: %d/256 (%.0f%%) attn=%d/8 mem=%d cons=%d\n",
                       epoch, correct, 100.0*correct/256,
                       attention_count(&brain.attention),
                       brain.memory.n, brain.n_consolidations);
                if(correct == 256) break;
            }
        }
    }

    printf("\n═══ FINAL ═══\n");
    printf("Accuracy:        %d/256 (%.0f%%)\n", best, 100.0*best/256);
    printf("Attention mask:  ");
    for(int i = 0; i < 8; i++) printf("%d", brain.attention.mask[i]);
    printf(" (should be 11110000)\n");
    printf("Memory items:    %d\n", brain.memory.n);
    printf("Consolidations:  %d\n", brain.n_consolidations);

    /* Compare: same task WITHOUT attention (baseline) */
    printf("\nBaseline (no attention):\n");
    Sensory plain;
    rng_seed(42);
    sensory_init(&plain);
    int plain_best = 0;
    for(int epoch = 0; epoch < 500; epoch++){
        for(int m = 0; m < 256; m++){
            sensory_train_one(&plain, inputs[m], targets[m]);
        }
        if(epoch > 30 && plain.flip_prob > 5) plain.flip_prob--;
        int correct = 0;
        for(int m = 0; m < 256; m++){
            int c;
            if(sensory_forward(&plain, inputs[m], &c) == targets[m]) correct++;
        }
        if(correct > plain_best) plain_best = correct;
        if(plain_best == 256) break;
    }
    printf("  Without attention: %d/256 (%.0f%%)\n",
           plain_best, 100.0*plain_best/256);

    int attn_correct_mask = (brain.attention.mask[0] && brain.attention.mask[1] &&
                              brain.attention.mask[2] && brain.attention.mask[3]);
    int attn_noise_mask_off = (!brain.attention.mask[4] && !brain.attention.mask[5] &&
                                !brain.attention.mask[6] && !brain.attention.mask[7]);

    printf("\n═══ VERDICT ═══\n");
    if(attn_correct_mask && attn_noise_mask_off){
        printf("✓ ATTENTION learned correct mask (signal=1111, noise=0000)\n");
    } else {
        printf("~ Attention mask: ");
        for(int i=0;i<8;i++) printf("%d", brain.attention.mask[i]);
        printf("\n");
    }
    if(best > plain_best){
        printf("✓ Brain+Attention > Plain sensory: %d vs %d\n", best, plain_best);
    } else {
        printf("~ No improvement: %d vs %d\n", best, plain_best);
    }

    return 0;
}
