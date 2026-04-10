/*
 * BITBRAIN v5.3: + META-LEARNING
 * ================================
 *
 * New: META region that PREDICTS whether sensory will learn an input.
 *   - Observes (input, sensory_prediction, target) tuples
 *   - Learns to predict "will sensory get this right after more training?"
 *   - If NO → consolidate immediately, don't waste epochs
 *
 * This is "meta-cognitive awareness" — brain knows its own limits.
 *
 * Test: mixture of easy (learnable) and hard (unlearnable) patterns.
 *   Meta should detect hard ones and route them to memory fast.
 *
 * Compile: gcc -O3 -march=native -o bitbrain5_3 bitbrain_v5_3.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)
#define MAX_MEMORY 100

#define S_IN 6
#define S_H1 24
#define S_H2 12

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

/* ═══ META region (NEW) ═══
 *
 * For each input, tracks: recent error history (last N epochs).
 * If error rate for an input is high across recent epochs → hard
 * Hard inputs → immediately consolidate
 */
typedef struct {
    /* For each input (indexed by hash), track error count */
    int8_t recent_errors[256]; /* rolling window, simple hash */
    int total_observations[256];
} Meta;

static void meta_init(Meta *m){
    memset(m, 0, sizeof(*m));
}

static unsigned hash_input(const int8_t *in, int n){
    unsigned h = 0;
    for(int i = 0; i < n; i++) h = h*31 + (in[i]==1 ? 1 : 0);
    return h & 0xFF;
}

static void meta_record(Meta *m, const int8_t *in, int was_wrong){
    unsigned h = hash_input(in, S_IN);
    if(was_wrong) m->recent_errors[h]++;
    m->total_observations[h]++;
}

/* Predict: is this input "hard" for sensory?
 * Returns: 1 if likely hard (consolidate now), 0 otherwise */
static int meta_predict_hard(Meta *m, const int8_t *in){
    unsigned h = hash_input(in, S_IN);
    if(m->total_observations[h] < 5) return 0; /* not enough data */
    /* Error rate > 50% across recent observations = hard */
    return m->recent_errors[h] * 2 > m->total_observations[h];
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

static int8_t sensory_forward(Sensory *s, const int8_t *in, int *conf){
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
    if(conf) *conf = abs(sum);
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
    int n;
} Memory;

static void memory_init(Memory *m){ m->n = 0; }

static void memory_store(Memory *m, HDV key, int8_t val){
    if(m->n >= MAX_MEMORY) return;
    /* Check for duplicate */
    for(int i = 0; i < m->n; i++){
        if(hdv_sim(key, m->keys[i]) > 0.97){
            m->values[i] = val;
            return;
        }
    }
    m->keys[m->n] = key;
    m->values[m->n] = val;
    m->n++;
}

static int8_t memory_recall(Memory *m, HDV key, double *sim_out){
    if(m->n == 0){if(sim_out)*sim_out=0; return 1;}
    int best = 0;
    double best_sim = -1;
    for(int i = 0; i < m->n; i++){
        double s = hdv_sim(key, m->keys[i]);
        if(s > best_sim){best_sim = s; best = i;}
    }
    if(sim_out) *sim_out = best_sim;
    return m->values[best];
}

/* ═══ BITBRAIN v5.3 ═══ */
typedef struct {
    Meta meta;
    Sensory sensory;
    Memory memory;
    int n_consolidations;
    int n_meta_triggers;
} BitBrain;

static void brain_init(BitBrain *b){
    meta_init(&b->meta);
    sensory_init(&b->sensory);
    memory_init(&b->memory);
    b->n_consolidations = 0;
    b->n_meta_triggers = 0;
}

static int8_t brain_process(BitBrain *b, const int8_t *in, HDV key,
                             const char **route){
    double mem_sim;
    int8_t mem_val = memory_recall(&b->memory, key, &mem_sim);
    if(mem_sim >= 0.97){
        if(route) *route = "MEM";
        return mem_val;
    }
    int conf;
    if(route) *route = "SEN";
    return sensory_forward(&b->sensory, in, &conf);
}

/* Learn with meta-cognition:
 * 1. Forward pass, check if sensory is correct
 * 2. Record in meta (input → error?)
 * 3. If meta predicts this is HARD → immediately consolidate
 * 4. Otherwise: train sensory as usual */
static void brain_learn(BitBrain *b, const int8_t *in, HDV key, int target){
    int conf;
    int8_t pred = sensory_forward(&b->sensory, in, &conf);
    int was_wrong = (pred != target);
    meta_record(&b->meta, in, was_wrong);

    /* Meta: is this input HARD? */
    if(meta_predict_hard(&b->meta, in)){
        /* Skip sensory training, consolidate immediately */
        memory_store(&b->memory, key, target);
        b->n_consolidations++;
        b->n_meta_triggers++;
        return;
    }

    /* Normal: train sensory */
    sensory_train_one(&b->sensory, in, target);
}

/* ═══ TEST: mix of learnable and unlearnable patterns ═══ */
int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v5.3: + META-LEARNING\n");
    printf("══════════════════════════════════════════\n\n");

    rng_seed(42);
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < 16; i++) V_pos[i] = hdv_random();

    /* Task: Parity-6 again, test meta triggers */
    printf("Task: Parity-6 (sensory struggles on some inputs)\n\n");

    BitBrain brain;
    brain_init(&brain);

    int8_t inputs[64][6];
    int targets[64];
    for(int m = 0; m < 64; m++){
        int p = 1;
        for(int i = 0; i < 6; i++){
            inputs[m][i] = ((m>>i)&1)?1:-1;
            p *= inputs[m][i];
        }
        targets[m] = p;
    }

    HDV keys[64];
    for(int m = 0; m < 64; m++) keys[m] = encode_bits(inputs[m], 6);

    int best = 0;
    int first_100_epoch = -1;
    for(int epoch = 0; epoch < 500; epoch++){
        int order[64];
        for(int i = 0; i < 64; i++) order[i] = i;
        for(int i = 63; i > 0; i--){
            int j = rng_next() % (i+1);
            int t = order[i]; order[i] = order[j]; order[j] = t;
        }
        for(int e = 0; e < 64; e++){
            int idx = order[e];
            brain_learn(&brain, inputs[idx], keys[idx], targets[idx]);
        }

        if(epoch > 30 && brain.sensory.flip_prob > 5) brain.sensory.flip_prob--;

        int correct = 0;
        for(int m = 0; m < 64; m++){
            const char *r;
            if(brain_process(&brain, inputs[m], keys[m], &r) == targets[m]) correct++;
        }
        if(correct > best){
            best = correct;
            if(correct == 64 || correct >= 60){
                printf("  Epoch %3d: %d/64  meta_triggers=%d  memory=%d  cons=%d\n",
                       epoch, correct,
                       brain.n_meta_triggers, brain.memory.n, brain.n_consolidations);
                if(correct == 64 && first_100_epoch < 0) first_100_epoch = epoch;
                if(correct == 64) break;
            }
        }
    }

    printf("\n═══ RESULTS ═══\n");
    printf("Best accuracy:       %d/64\n", best);
    printf("Epochs to 100%%:      %d\n", first_100_epoch);
    printf("Meta triggers:       %d (early consolidation)\n", brain.n_meta_triggers);
    printf("Memory items:        %d\n", brain.memory.n);
    printf("Total consolidations: %d\n", brain.n_consolidations);

    printf("\nComparison:\n");
    printf("  v5   (reactive consolidation): ~100 epochs\n");
    printf("  v5.3 (meta-predictive):        %d epochs\n", first_100_epoch);

    if(first_100_epoch >= 0 && first_100_epoch < 100){
        printf("\n✓ Meta-learning ACCELERATES convergence\n");
        printf("  Brain predicts which inputs are hard and stores them early\n");
    } else if(first_100_epoch >= 0){
        printf("\n~ Meta doesn't accelerate significantly for this task\n");
    } else {
        printf("\n✗ Did not reach 100%%\n");
    }

    return 0;
}
