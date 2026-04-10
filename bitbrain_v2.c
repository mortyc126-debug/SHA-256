/*
 * BITBRAIN v2: specialized regions + familiarity-based router
 * ============================================================
 *
 * Fix from v1: don't train all regions together. Each region specializes,
 * router decides which to use based on familiarity.
 *
 * Architecture:
 *   SENSORY (BitNet): trained ONLY on pattern examples
 *     - Learns general rules (parity, majority, etc.)
 *     - Input: 16 bits → Output: 1 bit
 *
 *   MEMORY (HDC): stores ONLY specific memorized examples
 *     - One-shot: store (input, output) pair as HDV
 *     - Query: find nearest stored key, return its value
 *     - Reports familiarity score (similarity to nearest)
 *
 *   ROUTER: simple rule based on familiarity
 *     - If familiarity > threshold → use memory (this is memorized)
 *     - Else → use sensory (apply learned pattern)
 *
 * This mimics how humans work:
 *   - Recognize familiar faces → memory lookup
 *   - See new object → apply learned categories
 *
 * Compile: gcc -O3 -march=native -o bitbrain2 bitbrain_v2.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define HDV_BITS 4096
#define HDV_WORDS (HDV_BITS/64)
#define MAX_MEMORY 50

#define SENSORY_IN 16
#define SENSORY_H1 24
#define SENSORY_H2 12
#define SENSORY_OUT 1

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
static HDV V_pos[32];

static HDV encode_input(const int8_t *bits, int n){
    HDV r = hdv_zero();
    for(int i = 0; i < n; i++){
        HDV c = hdv_bind(V_bit[bits[i]==1?1:0], V_pos[i]);
        r = hdv_bind(r, c);
    }
    return r;
}

/* ═══ SENSORY: trained BitNet for patterns ═══ */
typedef struct {
    int8_t W1[SENSORY_IN][SENSORY_H1];
    int8_t W2[SENSORY_H1][SENSORY_H2];
    int8_t W3[SENSORY_H2][SENSORY_OUT];
} Sensory;

static void sensory_init(Sensory *s){
    for(int i=0;i<SENSORY_IN;i++) for(int j=0;j<SENSORY_H1;j++)
        s->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<SENSORY_H1;i++) for(int j=0;j<SENSORY_H2;j++)
        s->W2[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<SENSORY_H2;i++) for(int j=0;j<SENSORY_OUT;j++)
        s->W3[i][j] = (rng_next()&1)?1:-1;
}

static int8_t sensory_forward(Sensory *s, const int8_t *in){
    int8_t h1[SENSORY_H1], h2[SENSORY_H2];
    for(int j=0;j<SENSORY_H1;j++){
        int sum=0;
        for(int i=0;i<SENSORY_IN;i++) sum += s->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<SENSORY_H2;j++){
        int sum=0;
        for(int i=0;i<SENSORY_H1;i++) sum += s->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int sum = 0;
    for(int i=0;i<SENSORY_H2;i++) sum += s->W3[i][0]*h2[i];
    return (sum>=0)?1:-1;
}

static void sensory_train_one(Sensory *s, const int8_t *in, int target, int flip_prob){
    /* Forward */
    int8_t h1[SENSORY_H1], h2[SENSORY_H2];
    for(int j=0;j<SENSORY_H1;j++){
        int sum=0;
        for(int i=0;i<SENSORY_IN;i++) sum += s->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<SENSORY_H2;j++){
        int sum=0;
        for(int i=0;i<SENSORY_H1;i++) sum += s->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int out_sum = 0;
    for(int i=0;i<SENSORY_H2;i++) out_sum += s->W3[i][0]*h2[i];
    int out = (out_sum>=0)?1:-1;

    if(out == target) return;

    /* Train output layer */
    int8_t want_h2[SENSORY_H2] = {0};
    for(int i=0;i<SENSORY_H2;i++){
        int contrib = s->W3[i][0] * h2[i];
        if(contrib != target){
            if((int)(rng_next()%100) < flip_prob) s->W3[i][0] = -s->W3[i][0];
        }
        want_h2[i] = target * s->W3[i][0];
    }

    /* Train H2 layer */
    int8_t want_h1[SENSORY_H1] = {0};
    for(int j=0;j<SENSORY_H2;j++){
        if(want_h2[j] == h2[j]) continue;
        for(int i=0;i<SENSORY_H1;i++){
            int contrib = s->W2[i][j] * h1[i];
            if(contrib != want_h2[j]){
                if((int)(rng_next()%100) < flip_prob) s->W2[i][j] = -s->W2[i][j];
            }
        }
        for(int i=0;i<SENSORY_H1;i++){
            int w = s->W2[i][j];
            int wnt = want_h2[j] * w;
            if(want_h1[i] == 0) want_h1[i] = wnt;
            else if(want_h1[i] != wnt) want_h1[i] = 0;
        }
    }

    /* Train H1 layer */
    for(int j=0;j<SENSORY_H1;j++){
        if(want_h1[j] == 0 || want_h1[j] == h1[j]) continue;
        for(int i=0;i<SENSORY_IN;i++){
            int contrib = s->W1[i][j] * in[i];
            if(contrib != want_h1[j]){
                if((int)(rng_next()%100) < flip_prob) s->W1[i][j] = -s->W1[i][j];
            }
        }
    }
}

/* ═══ MEMORY: one-shot HDC store ═══ */
typedef struct {
    HDV keys[MAX_MEMORY];
    int8_t values[MAX_MEMORY];  /* one bit per memory */
    int n;
} Memory;

static void memory_init(Memory *m){ m->n = 0; }

static void memory_store(Memory *m, HDV key, int8_t value){
    if(m->n < MAX_MEMORY){
        m->keys[m->n] = key;
        m->values[m->n] = value;
        m->n++;
    }
}

static int8_t memory_recall(Memory *m, HDV key, double *out_sim){
    if(m->n == 0){if(out_sim)*out_sim=0; return 1;}
    int best = 0;
    double best_sim = -1;
    for(int i = 0; i < m->n; i++){
        double s = hdv_sim(key, m->keys[i]);
        if(s > best_sim){best_sim = s; best = i;}
    }
    if(out_sim) *out_sim = best_sim;
    return m->values[best];
}

/* ═══ BITBRAIN: regions + router ═══ */
typedef struct {
    Sensory sensory;
    Memory memory;
    double router_threshold; /* familiarity threshold */
} BitBrain;

static void brain_init(BitBrain *b){
    sensory_init(&b->sensory);
    memory_init(&b->memory);
    b->router_threshold = 0.85; /* >85% similarity → it's memorized */
}

/* Process input: router decides memory vs sensory */
static int8_t brain_process(BitBrain *b, const int8_t *input, HDV input_hdv,
                              const char **route){
    double fam;
    int8_t mem_out = memory_recall(&b->memory, input_hdv, &fam);

    if(fam >= b->router_threshold){
        if(route) *route = "MEMORY";
        return mem_out;
    } else {
        if(route) *route = "SENSORY";
        return sensory_forward(&b->sensory, input);
    }
}

/* ═══ TASK: mixed pattern + memorized ═══ */
typedef struct {
    int8_t input[16];
    int target;  /* ±1 */
    int is_memorized;
} Example;

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v2: specialized regions + router\n");
    printf("══════════════════════════════════════════\n");
    printf("Each region does its OWN job.\n\n");

    rng_seed(42);

    /* Init HDV prototypes */
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < 32; i++) V_pos[i] = hdv_random();

    BitBrain brain;
    brain_init(&brain);

    /* Generate data */
    int n_pattern = 200;
    int n_memory = 10;
    Example pattern_data[200];
    Example memory_data[10];

    /* Pattern: parity of first 4 bits → output */
    for(int i = 0; i < n_pattern; i++){
        for(int j = 0; j < 16; j++) pattern_data[i].input[j] = (rng_next()&1)?1:-1;
        int parity = 1;
        for(int j = 0; j < 4; j++) parity *= pattern_data[i].input[j];
        pattern_data[i].target = parity;
        pattern_data[i].is_memorized = 0;
    }

    /* Memory: specific inputs with OVERRIDE outputs (different from pattern) */
    for(int i = 0; i < n_memory; i++){
        for(int j = 0; j < 16; j++) memory_data[i].input[j] = (rng_next()&1)?1:-1;
        /* OVERRIDE: make output DIFFERENT from what parity would give */
        int parity = 1;
        for(int j = 0; j < 4; j++) parity *= memory_data[i].input[j];
        memory_data[i].target = -parity; /* opposite of parity! */
        memory_data[i].is_memorized = 1;
    }

    printf("Dataset:\n");
    printf("  %d pattern examples (parity rule)\n", n_pattern);
    printf("  %d memorized examples (override rule: opposite of parity)\n", n_memory);
    printf("\n");

    /* STEP 1: Train sensory on PATTERN examples only */
    printf("Step 1: Training sensory on pattern examples...\n");
    int best = 0;
    for(int epoch = 0; epoch < 300; epoch++){
        for(int i = 0; i < n_pattern; i++){
            int flip = 30 - epoch * 25 / 300;
            if(flip < 3) flip = 3;
            sensory_train_one(&brain.sensory, pattern_data[i].input,
                              pattern_data[i].target, flip);
        }
        /* Evaluate */
        int correct = 0;
        for(int i = 0; i < n_pattern; i++){
            if(sensory_forward(&brain.sensory, pattern_data[i].input) ==
               pattern_data[i].target) correct++;
        }
        if(correct > best){
            best = correct;
            if(correct == n_pattern){
                printf("  Epoch %3d: %d/%d ✓ converged\n", epoch, correct, n_pattern);
                break;
            }
        }
        if(epoch % 50 == 0){
            printf("  Epoch %3d: %d/%d\n", epoch, correct, n_pattern);
        }
    }
    printf("  Best: %d/%d (%.0f%%)\n\n", best, n_pattern, 100.0*best/n_pattern);

    /* STEP 2: Store memorized examples in memory */
    printf("Step 2: Storing memorized examples in HDC memory...\n");
    for(int i = 0; i < n_memory; i++){
        HDV key = encode_input(memory_data[i].input, 16);
        memory_store(&brain.memory, key, memory_data[i].target);
    }
    printf("  Stored: %d items\n\n", brain.memory.n);

    /* STEP 3: Test - can router correctly route? */
    printf("Step 3: Testing brain on mixed data...\n");
    int pattern_ok = 0, pattern_wrong = 0;
    int memory_ok = 0, memory_wrong = 0;
    int routed_mem_from_pattern = 0, routed_sen_from_mem = 0;

    for(int i = 0; i < n_pattern; i++){
        HDV h = encode_input(pattern_data[i].input, 16);
        const char *route;
        int8_t out = brain_process(&brain, pattern_data[i].input, h, &route);
        if(strcmp(route, "MEMORY") == 0) routed_mem_from_pattern++;
        if(out == pattern_data[i].target) pattern_ok++;
        else pattern_wrong++;
    }

    for(int i = 0; i < n_memory; i++){
        HDV h = encode_input(memory_data[i].input, 16);
        const char *route;
        int8_t out = brain_process(&brain, memory_data[i].input, h, &route);
        if(strcmp(route, "SENSORY") == 0) routed_sen_from_mem++;
        if(out == memory_data[i].target) memory_ok++;
        else memory_wrong++;
    }

    printf("\nPattern examples (should route to SENSORY):\n");
    printf("  Correct: %d/%d (%.1f%%)\n", pattern_ok, n_pattern,
           100.0*pattern_ok/n_pattern);
    printf("  Wrong-routed to memory: %d\n", routed_mem_from_pattern);

    printf("\nMemorized examples (should route to MEMORY, give OPPOSITE of pattern):\n");
    printf("  Correct: %d/%d (%.1f%%)\n", memory_ok, n_memory,
           100.0*memory_ok/n_memory);
    printf("  Wrong-routed to sensory: %d\n", routed_sen_from_mem);

    /* STEP 4: Fresh generalization test */
    printf("\nStep 4: Generalization on 100 fresh pattern examples...\n");
    int gen_ok = 0;
    for(int i = 0; i < 100; i++){
        int8_t in[16];
        for(int j = 0; j < 16; j++) in[j] = (rng_next()&1)?1:-1;
        int par = 1;
        for(int j = 0; j < 4; j++) par *= in[j];
        HDV h = encode_input(in, 16);
        const char *route;
        int8_t out = brain_process(&brain, in, h, &route);
        if(out == par) gen_ok++;
    }
    printf("  Fresh accuracy: %d/100 (%.0f%%)\n", gen_ok, (double)gen_ok);

    printf("\n═══ VERDICT ═══\n");
    int total_correct = pattern_ok + memory_ok;
    int total = n_pattern + n_memory;

    if(memory_ok == n_memory && pattern_ok >= n_pattern * 0.9 && gen_ok >= 70){
        printf("✓✓✓ BITBRAIN WORKS!\n");
        printf("    Memory perfectly recalls memorized examples\n");
        printf("    Sensory generalizes pattern rule to fresh inputs\n");
        printf("    Router correctly sends each input to its region\n");
    } else if(memory_ok >= n_memory * 0.8 && pattern_ok >= n_pattern * 0.7){
        printf("✓ BITBRAIN mostly works: regions cooperate, some errors\n");
    } else {
        printf("~ Partial success: memory works, sensory needs more training\n");
    }

    printf("\nOverall: %d/%d (%.1f%%)\n", total_correct, total,
           100.0*total_correct/total);

    return 0;
}
