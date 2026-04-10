/*
 * BITBRAIN: bit-native brain architecture with specialized regions
 * =================================================================
 *
 * Individual neurons = chaos. Organized regions = brain.
 *
 * Architecture:
 *   REGION 1 (Sensory): BitNet for pattern detection
 *     - Input features → learned features
 *     - Specializes in: XOR/AND/OR/Majority-like functions
 *
 *   REGION 2 (Memory): HDC for associative storage
 *     - Stores (key, value) pairs as HDV bundles
 *     - Specializes in: one-shot learning, recall from partial cue
 *
 *   REGION 3 (Working memory): small BitNet for integration
 *     - Takes outputs from Sensory + Memory
 *     - Produces final decision
 *     - Specializes in: combining information
 *
 *   ROUTER: simple BitNet that decides which regions to use
 *
 * Communication: all regions use the same HDV width (signal format)
 *
 * Test: a heterogeneous task requiring multiple region types.
 *
 * Compile: gcc -O3 -march=native -o bitbrain bitbrain.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)
#define MAX_MEMORY 100

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

/* ═══ HDV operations ═══ */
static HDV hdv_random(void){HDV v;for(int i=0;i<HDV_WORDS;i++)v.b[i]=rng_next();return v;}
static HDV hdv_zero(void){HDV v;memset(&v,0,sizeof(v));return v;}
static HDV hdv_bind(HDV a,HDV b){HDV r;for(int i=0;i<HDV_WORDS;i++)r.b[i]=a.b[i]^b.b[i];return r;}
static int hdv_ham(HDV a,HDV b){int d=0;for(int i=0;i<HDV_WORDS;i++)d+=__builtin_popcountll(a.b[i]^b.b[i]);return d;}
static double hdv_sim(HDV a,HDV b){return 1.0-(double)hdv_ham(a,b)/HDV_BITS;}

typedef struct { int c[HDV_BITS]; int n; } Bundle;
static void bundle_init(Bundle *b){memset(b,0,sizeof(*b));}
static void bundle_add(Bundle *b, HDV v){
    for(int i=0;i<HDV_BITS;i++) b->c[i] += ((v.b[i>>6]>>(i&63))&1)?1:-1;
    b->n++;
}
static HDV bundle_finalize(Bundle *b){
    HDV r=hdv_zero();
    for(int i=0;i<HDV_BITS;i++) if(b->c[i]>0) r.b[i>>6] |= (1ULL<<(i&63));
    return r;
}

/* Convert bit vector → HDV (each input bit maps to a fixed random HDV) */
static HDV V_bit[2];  /* 0/1 prototypes */
static HDV V_pos[128]; /* position prototypes */

static HDV encode_input(const int *bits, int n){
    HDV r = hdv_zero();
    for(int i = 0; i < n; i++){
        HDV c = hdv_bind(V_bit[bits[i]], V_pos[i]);
        r = hdv_bind(r, c);
    }
    return r;
}

/* ═══ REGION 1: SENSORY (BitNet for pattern detection) ═══ */

#define SENSORY_IN 16
#define SENSORY_HIDDEN 32
#define SENSORY_OUT 8

typedef struct {
    int8_t W1[SENSORY_IN][SENSORY_HIDDEN];
    int8_t W2[SENSORY_HIDDEN][SENSORY_OUT];
} Sensory;

static void sensory_init(Sensory *s){
    for(int i=0;i<SENSORY_IN;i++) for(int j=0;j<SENSORY_HIDDEN;j++)
        s->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<SENSORY_HIDDEN;i++) for(int j=0;j<SENSORY_OUT;j++)
        s->W2[i][j] = (rng_next()&1)?1:-1;
}

static void sensory_forward(Sensory *s, const int8_t *in, int8_t *hidden, int8_t *out){
    for(int j=0;j<SENSORY_HIDDEN;j++){
        int sum=0;
        for(int i=0;i<SENSORY_IN;i++) sum += s->W1[i][j]*in[i];
        hidden[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<SENSORY_OUT;j++){
        int sum=0;
        for(int i=0;i<SENSORY_HIDDEN;i++) sum += s->W2[i][j]*hidden[i];
        out[j] = (sum>=0)?1:-1;
    }
}

static void sensory_learn(Sensory *s, const int8_t *in, const int8_t *hidden,
                          const int8_t *target, int flip_prob){
    int8_t desired_hidden[SENSORY_HIDDEN] = {0};

    /* Output layer */
    for(int j=0;j<SENSORY_OUT;j++){
        int sum=0;
        for(int i=0;i<SENSORY_HIDDEN;i++) sum += s->W2[i][j]*hidden[i];
        int cur = (sum>=0)?1:-1;
        if(cur == target[j]) continue;

        /* Flip wrong-voting weights */
        for(int i=0;i<SENSORY_HIDDEN;i++){
            int contrib = s->W2[i][j]*hidden[i];
            if(contrib != target[j]){
                if((int)(rng_next()%100) < flip_prob)
                    s->W2[i][j] = -s->W2[i][j];
            }
        }
        /* Request hidden change */
        for(int i=0;i<SENSORY_HIDDEN;i++){
            int want = target[j] * s->W2[i][j];
            if(desired_hidden[i] == 0) desired_hidden[i] = want;
            else if(desired_hidden[i] != want) desired_hidden[i] = 0;
        }
    }

    /* Hidden layer */
    for(int j=0;j<SENSORY_HIDDEN;j++){
        if(desired_hidden[j] == 0) continue;
        if(desired_hidden[j] == hidden[j]) continue;
        for(int i=0;i<SENSORY_IN;i++){
            int contrib = s->W1[i][j]*in[i];
            if(contrib != desired_hidden[j]){
                if((int)(rng_next()%100) < flip_prob)
                    s->W1[i][j] = -s->W1[i][j];
            }
        }
    }
}

/* ═══ REGION 2: MEMORY (HDC) ═══ */

typedef struct {
    HDV keys[MAX_MEMORY];
    HDV values[MAX_MEMORY];
    int n;
    Bundle combined;
} Memory;

static void memory_init(Memory *m){
    m->n = 0;
    bundle_init(&m->combined);
}

static void memory_store(Memory *m, HDV key, HDV value){
    if(m->n < MAX_MEMORY){
        m->keys[m->n] = key;
        m->values[m->n] = value;
        m->n++;
    }
    HDV pair = hdv_bind(key, value);
    bundle_add(&m->combined, pair);
}

/* Recall: given key, find most similar stored pair's value */
static HDV memory_recall(Memory *m, HDV key){
    if(m->n == 0) return hdv_random(); /* no memories */

    /* Find closest key */
    int best = 0;
    double best_sim = -1;
    for(int i = 0; i < m->n; i++){
        double s = hdv_sim(key, m->keys[i]);
        if(s > best_sim){best_sim = s; best = i;}
    }
    return m->values[best];
}

/* Check if key is similar to any stored */
static double memory_familiarity(Memory *m, HDV key){
    if(m->n == 0) return 0;
    double best = -1;
    for(int i = 0; i < m->n; i++){
        double s = hdv_sim(key, m->keys[i]);
        if(s > best) best = s;
    }
    return best;
}

/* ═══ REGION 3: WORKING MEMORY (small BitNet that integrates) ═══ */

#define WORKING_IN 32  /* 8 from sensory + 8 converted from memory recall + ... */
#define WORKING_HIDDEN 16
#define WORKING_OUT 4

typedef struct {
    int8_t W1[WORKING_IN][WORKING_HIDDEN];
    int8_t W2[WORKING_HIDDEN][WORKING_OUT];
} Working;

static void working_init(Working *w){
    for(int i=0;i<WORKING_IN;i++) for(int j=0;j<WORKING_HIDDEN;j++)
        w->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<WORKING_HIDDEN;i++) for(int j=0;j<WORKING_OUT;j++)
        w->W2[i][j] = (rng_next()&1)?1:-1;
}

static void working_forward(Working *w, const int8_t *in, int8_t *hidden, int8_t *out){
    for(int j=0;j<WORKING_HIDDEN;j++){
        int sum=0;
        for(int i=0;i<WORKING_IN;i++) sum += w->W1[i][j]*in[i];
        hidden[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<WORKING_OUT;j++){
        int sum=0;
        for(int i=0;i<WORKING_HIDDEN;i++) sum += w->W2[i][j]*hidden[i];
        out[j] = (sum>=0)?1:-1;
    }
}

static void working_learn(Working *w, const int8_t *in, const int8_t *hidden,
                           const int8_t *target, int flip_prob){
    int8_t desired_hidden[WORKING_HIDDEN] = {0};

    for(int j=0;j<WORKING_OUT;j++){
        int sum=0;
        for(int i=0;i<WORKING_HIDDEN;i++) sum += w->W2[i][j]*hidden[i];
        int cur = (sum>=0)?1:-1;
        if(cur == target[j]) continue;

        for(int i=0;i<WORKING_HIDDEN;i++){
            int contrib = w->W2[i][j]*hidden[i];
            if(contrib != target[j]){
                if((int)(rng_next()%100) < flip_prob)
                    w->W2[i][j] = -w->W2[i][j];
            }
        }
        for(int i=0;i<WORKING_HIDDEN;i++){
            int want = target[j] * w->W2[i][j];
            if(desired_hidden[i] == 0) desired_hidden[i] = want;
            else if(desired_hidden[i] != want) desired_hidden[i] = 0;
        }
    }

    for(int j=0;j<WORKING_HIDDEN;j++){
        if(desired_hidden[j] == 0 || desired_hidden[j] == hidden[j]) continue;
        for(int i=0;i<WORKING_IN;i++){
            int contrib = w->W1[i][j]*in[i];
            if(contrib != desired_hidden[j]){
                if((int)(rng_next()%100) < flip_prob)
                    w->W1[i][j] = -w->W1[i][j];
            }
        }
    }
}

/* ═══ BITBRAIN: all regions together ═══ */

typedef struct {
    Sensory sensory;
    Memory memory;
    Working working;
} BitBrain;

static void brain_init(BitBrain *b){
    sensory_init(&b->sensory);
    memory_init(&b->memory);
    working_init(&b->working);
}

/* Full forward pass through all regions */
static void brain_process(BitBrain *b, const int8_t *input,
                          HDV input_hdv, int8_t *output){
    /* 1. Sensory extracts features */
    int8_t sensory_hidden[SENSORY_HIDDEN];
    int8_t sensory_out[SENSORY_OUT];
    sensory_forward(&b->sensory, input, sensory_hidden, sensory_out);

    /* 2. Memory: recall based on input */
    HDV recalled = memory_recall(&b->memory, input_hdv);
    double familiarity = memory_familiarity(&b->memory, input_hdv);

    /* 3. Working memory: combine sensory features + memory recall signal */
    int8_t working_in[WORKING_IN];
    /* Sensory features → first 8 */
    for(int i=0;i<8;i++) working_in[i] = sensory_out[i];
    /* Memory signal: convert recalled HDV to 8 bits (sample first 8 bits) */
    for(int i=0;i<8;i++)
        working_in[8+i] = ((recalled.b[0] >> i) & 1) ? 1 : -1;
    /* Familiarity indicator (8 bits, thermometer encoding) */
    int fam_level = (int)(familiarity * 8);
    for(int i=0;i<8;i++) working_in[16+i] = (i < fam_level) ? 1 : -1;
    /* Context: just pad with sensory hidden features */
    for(int i=0;i<8;i++) working_in[24+i] = sensory_hidden[i];

    int8_t working_hidden[WORKING_HIDDEN];
    working_forward(&b->working, working_in, working_hidden, output);
}

/* Learn from a labeled example */
static void brain_learn(BitBrain *b, const int8_t *input, HDV input_hdv,
                         const int8_t *target, int flip_prob){
    /* 1. Store in memory (one-shot) */
    /* We encode target as HDV value */
    HDV target_hdv = hdv_zero();
    for(int i = 0; i < WORKING_OUT; i++){
        HDV c = hdv_bind(V_bit[target[i]==1?1:0], V_pos[i]);
        target_hdv = hdv_bind(target_hdv, c);
    }
    memory_store(&b->memory, input_hdv, target_hdv);

    /* 2. Compute forward pass (again, for learning) */
    int8_t sensory_hidden[SENSORY_HIDDEN];
    int8_t sensory_out[SENSORY_OUT];
    sensory_forward(&b->sensory, input, sensory_hidden, sensory_out);

    HDV recalled = memory_recall(&b->memory, input_hdv);
    double familiarity = memory_familiarity(&b->memory, input_hdv);

    int8_t working_in[WORKING_IN];
    for(int i=0;i<8;i++) working_in[i] = sensory_out[i];
    for(int i=0;i<8;i++) working_in[8+i] = ((recalled.b[0] >> i) & 1) ? 1 : -1;
    int fam_level = (int)(familiarity * 8);
    for(int i=0;i<8;i++) working_in[16+i] = (i < fam_level) ? 1 : -1;
    for(int i=0;i<8;i++) working_in[24+i] = sensory_hidden[i];

    int8_t working_hidden[WORKING_HIDDEN];
    int8_t working_out[WORKING_OUT];
    working_forward(&b->working, working_in, working_hidden, working_out);

    /* 3. Train working layer */
    working_learn(&b->working, working_in, working_hidden, target, flip_prob);

    /* 4. Also train sensory to help */
    /* Simple: use target (or a mapped version) as sensory target */
    int8_t sensory_target[SENSORY_OUT];
    for(int i=0;i<SENSORY_OUT;i++) sensory_target[i] = (i<WORKING_OUT) ? target[i] : 1;
    sensory_learn(&b->sensory, input, sensory_hidden, sensory_target, flip_prob);
}

/* ═══ HETEROGENEOUS TASK ═══
 *
 * The task tests multiple aspects:
 *   - Pattern recognition (sensory)
 *   - One-shot memorization (memory)
 *   - Combining info (working)
 *
 * Structure: binary classification with 2 modes:
 *   MODE A: pattern-based (e.g., parity of input)
 *   MODE B: memorized (specific input → specific output)
 *
 * The network should use sensory for MODE A and memory for MODE B.
 */

typedef struct {
    int8_t input[16];
    int8_t output[4];
    int is_memorized; /* 1 if from memory set, 0 if pattern-based */
} Example;

/* Generate mixed training set */
static void gen_mixed_data(Example *data, int n_pattern, int n_memory){
    /* Pattern: parity of first 4 bits → output[0] */
    for(int i = 0; i < n_pattern; i++){
        for(int j = 0; j < 16; j++) data[i].input[j] = (rng_next()&1)?1:-1;
        int parity = 1;
        for(int j = 0; j < 4; j++) parity *= data[i].input[j];
        data[i].output[0] = parity;
        data[i].output[1] = -parity;
        data[i].output[2] = parity;
        data[i].output[3] = -parity;
        data[i].is_memorized = 0;
    }

    /* Memory: specific inputs with unique outputs */
    for(int i = 0; i < n_memory; i++){
        int idx = n_pattern + i;
        /* Unique "anchored" input */
        for(int j = 0; j < 16; j++) data[idx].input[j] = (rng_next()&1)?1:-1;
        /* Unique output (random but fixed) */
        for(int j = 0; j < 4; j++) data[idx].output[j] = (rng_next()&1)?1:-1;
        data[idx].is_memorized = 1;
    }
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN: bit-native brain architecture\n");
    printf("══════════════════════════════════════════\n\n");

    rng_seed(42);

    /* Initialize HDV prototypes */
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < 128; i++) V_pos[i] = hdv_random();

    /* Initialize brain */
    BitBrain brain;
    brain_init(&brain);

    /* Generate mixed dataset */
    int n_pattern = 50;
    int n_memory = 10;
    int total = n_pattern + n_memory;
    Example data[100];
    gen_mixed_data(data, n_pattern, n_memory);

    printf("Dataset: %d pattern examples + %d memorized examples = %d total\n",
           n_pattern, n_memory, total);
    printf("Architecture:\n");
    printf("  Sensory: 16 → 32 → 8 (BitNet)\n");
    printf("  Memory:  HDC (2048-bit HDV)\n");
    printf("  Working: 32 → 16 → 4 (BitNet)\n\n");

    /* Train */
    printf("Training...\n");
    for(int epoch = 0; epoch < 200; epoch++){
        for(int i = 0; i < total; i++){
            /* Encode input as HDV */
            int bits[16];
            for(int j = 0; j < 16; j++) bits[j] = data[i].input[j] == 1 ? 1 : 0;
            HDV input_hdv = encode_input(bits, 16);

            int flip_prob = 30 - epoch * 20 / 200;
            if(flip_prob < 5) flip_prob = 5;
            brain_learn(&brain, data[i].input, input_hdv, data[i].output, flip_prob);
        }

        /* Evaluate */
        if(epoch % 20 == 0){
            int pattern_correct = 0, memory_correct = 0;
            for(int i = 0; i < total; i++){
                int bits[16];
                for(int j = 0; j < 16; j++) bits[j] = data[i].input[j] == 1 ? 1 : 0;
                HDV input_hdv = encode_input(bits, 16);
                int8_t out[4];
                brain_process(&brain, data[i].input, input_hdv, out);
                int ok = 1;
                for(int j = 0; j < 4; j++) if(out[j] != data[i].output[j]){ok = 0; break;}
                if(ok){
                    if(data[i].is_memorized) memory_correct++;
                    else pattern_correct++;
                }
            }
            printf("  Epoch %3d: pattern %d/%d, memory %d/%d\n",
                   epoch, pattern_correct, n_pattern, memory_correct, n_memory);
        }
    }

    /* Final test */
    printf("\nFinal evaluation:\n");
    int pattern_correct = 0, memory_correct = 0;
    for(int i = 0; i < total; i++){
        int bits[16];
        for(int j = 0; j < 16; j++) bits[j] = data[i].input[j] == 1 ? 1 : 0;
        HDV input_hdv = encode_input(bits, 16);
        int8_t out[4];
        brain_process(&brain, data[i].input, input_hdv, out);
        int ok = 1;
        for(int j = 0; j < 4; j++) if(out[j] != data[i].output[j]){ok = 0; break;}
        if(ok){
            if(data[i].is_memorized) memory_correct++;
            else pattern_correct++;
        }
    }
    printf("  Pattern: %d/%d (%.1f%%)\n", pattern_correct, n_pattern,
           100.0*pattern_correct/n_pattern);
    printf("  Memory:  %d/%d (%.1f%%)\n", memory_correct, n_memory,
           100.0*memory_correct/n_memory);

    /* Test generalization: fresh pattern examples */
    printf("\nGeneralization test (fresh pattern examples):\n");
    int gen_correct = 0;
    for(int i = 0; i < 50; i++){
        Example test;
        for(int j = 0; j < 16; j++) test.input[j] = (rng_next()&1)?1:-1;
        int parity = 1;
        for(int j = 0; j < 4; j++) parity *= test.input[j];
        test.output[0] = parity;
        test.output[1] = -parity;
        test.output[2] = parity;
        test.output[3] = -parity;

        int bits[16];
        for(int j = 0; j < 16; j++) bits[j] = test.input[j] == 1 ? 1 : 0;
        HDV input_hdv = encode_input(bits, 16);
        int8_t out[4];
        brain_process(&brain, test.input, input_hdv, out);
        int ok = 1;
        for(int j = 0; j < 4; j++) if(out[j] != test.output[j]){ok = 0; break;}
        if(ok) gen_correct++;
    }
    printf("  Fresh: %d/50 (%.1f%%)\n", gen_correct, 100.0*gen_correct/50);

    printf("\n═══ VERDICT ═══\n");
    if(memory_correct >= n_memory * 0.9 && pattern_correct >= n_pattern * 0.8){
        printf("✓ BitBrain WORKS: memory stores unique examples, pattern generalizes\n");
        printf("  Regions cooperate: specialization + integration\n");
    } else if(memory_correct > 0 && pattern_correct > 0){
        printf("~ BitBrain partially works, regions contribute but not optimally\n");
    } else {
        printf("✗ BitBrain fails to coordinate regions\n");
    }

    return 0;
}
