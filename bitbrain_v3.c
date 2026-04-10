/*
 * BITBRAIN v3: minimal but working
 * =================================
 *
 * Task: classify 4-bit inputs. Default rule = parity.
 * BUT: a few specific inputs have OVERRIDE rule (opposite of parity).
 *
 * The brain must:
 *   - Learn parity (sensory region)
 *   - Memorize exceptions (memory region)
 *   - Route correctly (router based on familiarity)
 *
 * Compile: gcc -O3 -march=native -o bitbrain3 bitbrain_v3.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)
#define MAX_MEMORY 20

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
static HDV V_pos[8];

static HDV encode4(const int8_t *bits){
    /* Use BUNDLE (majority) instead of XOR to avoid pairwise cancellation */
    int counters[HDV_BITS] = {0};
    for(int i = 0; i < 4; i++){
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

/* ═══ SENSORY ═══ */
#define S_IN 4
#define S_H1 16
#define S_H2 8

typedef struct {
    int8_t W1[S_IN][S_H1];
    int8_t W2[S_H1][S_H2];
    int8_t W3[S_H2];
} Sensory;

static void sensory_init(Sensory *s){
    for(int i=0;i<S_IN;i++) for(int j=0;j<S_H1;j++) s->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<S_H1;i++) for(int j=0;j<S_H2;j++) s->W2[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<S_H2;i++) s->W3[i] = (rng_next()&1)?1:-1;
}

static int8_t sensory_forward(Sensory *s, const int8_t *in){
    int8_t h1[S_H1], h2[S_H2];
    for(int j=0;j<S_H1;j++){
        int sum=0;
        for(int i=0;i<S_IN;i++) sum += s->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<S_H2;j++){
        int sum=0;
        for(int i=0;i<S_H1;i++) sum += s->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int sum = 0;
    for(int i=0;i<S_H2;i++) sum += s->W3[i]*h2[i];
    return (sum>=0)?1:-1;
}

static void sensory_train(Sensory *s, const int8_t *in, int target, int flip_prob){
    int8_t h1[S_H1], h2[S_H2];
    for(int j=0;j<S_H1;j++){
        int sum=0;
        for(int i=0;i<S_IN;i++) sum += s->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<S_H2;j++){
        int sum=0;
        for(int i=0;i<S_H1;i++) sum += s->W2[i][j]*h1[i];
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
            if((int)(rng_next()%100) < flip_prob) s->W3[i] = -s->W3[i];
        }
        want_h2[i] = target * s->W3[i];
    }

    int8_t want_h1[S_H1] = {0};
    for(int j=0;j<S_H2;j++){
        if(want_h2[j] == h2[j]) continue;
        for(int i=0;i<S_H1;i++){
            int contrib = s->W2[i][j]*h1[i];
            if(contrib != want_h2[j]){
                if((int)(rng_next()%100) < flip_prob) s->W2[i][j] = -s->W2[i][j];
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
                if((int)(rng_next()%100) < flip_prob) s->W1[i][j] = -s->W1[i][j];
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
    if(m->n < MAX_MEMORY){
        m->keys[m->n] = key;
        m->values[m->n] = val;
        m->n++;
    }
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

/* ═══ BITBRAIN ═══ */
typedef struct {
    Sensory sensory;
    Memory memory;
    double thresh;
} BitBrain;

static void brain_init(BitBrain *b, double thresh){
    sensory_init(&b->sensory);
    memory_init(&b->memory);
    b->thresh = thresh;
}

static int8_t brain_process(BitBrain *b, const int8_t *input, HDV key, const char **route){
    double sim;
    int8_t mem_val = memory_recall(&b->memory, key, &sim);
    if(sim >= b->thresh){
        if(route) *route = "MEM";
        return mem_val;
    }
    if(route) *route = "SEN";
    return sensory_forward(&b->sensory, input);
}

/* Compute parity of 4 bits */
static int parity4(const int8_t *bits){
    return bits[0] * bits[1] * bits[2] * bits[3];
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v3: minimal working version\n");
    printf("══════════════════════════════════════════\n\n");

    rng_seed(42);

    /* HDV prototypes */
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < 8; i++) V_pos[i] = hdv_random();

    /* Verify encoding gives quasi-orthogonal HDVs */
    printf("Encoding sanity check:\n");
    int8_t t1[4] = {1,1,1,1};
    int8_t t2[4] = {-1,1,1,1};
    int8_t t3[4] = {-1,-1,-1,-1};
    HDV h1 = encode4(t1), h2 = encode4(t2), h3 = encode4(t3);
    printf("  sim(1111, 1111) = %.3f (should be 1.0)\n", hdv_sim(h1, h1));
    printf("  sim(1111, -111) = %.3f (should be ~0.5)\n", hdv_sim(h1, h2));
    printf("  sim(1111, ----) = %.3f (should be ~0.5)\n", hdv_sim(h1, h3));
    printf("\n");

    /* Threshold: if similarity > 0.95 → it's memorized */
    BitBrain brain;
    brain_init(&brain, 0.95);

    /* STEP 1: Train sensory on parity of 4 bits */
    printf("Step 1: Training sensory on parity (16 examples)...\n");
    int best = 0;
    for(int epoch = 0; epoch < 500; epoch++){
        for(int m = 0; m < 16; m++){
            int8_t in[4];
            for(int i = 0; i < 4; i++) in[i] = ((m >> i) & 1) ? 1 : -1;
            int target = parity4(in);
            int flip = 30 - epoch * 25 / 500;
            if(flip < 5) flip = 5;
            sensory_train(&brain.sensory, in, target, flip);
        }
        int correct = 0;
        for(int m = 0; m < 16; m++){
            int8_t in[4];
            for(int i = 0; i < 4; i++) in[i] = ((m >> i) & 1) ? 1 : -1;
            if(sensory_forward(&brain.sensory, in) == parity4(in)) correct++;
        }
        if(correct > best){
            best = correct;
            if(correct == 16){
                printf("  Epoch %3d: 16/16 ✓ parity learned\n", epoch);
                break;
            }
        }
    }
    printf("  Best: %d/16\n\n", best);

    /* STEP 2: Store 3 exceptions in memory */
    printf("Step 2: Storing 3 exceptions in memory (override parity)...\n");
    int8_t except1[4] = {1, 1, 1, 1};   /* parity = +1, override to -1 */
    int8_t except2[4] = {-1, -1, 1, 1}; /* parity = +1, override to -1 */
    int8_t except3[4] = {1, -1, 1, -1}; /* parity = +1, override to -1 */
    memory_store(&brain.memory, encode4(except1), -1);
    memory_store(&brain.memory, encode4(except2), -1);
    memory_store(&brain.memory, encode4(except3), -1);
    printf("  Stored 3 exceptions\n\n");

    /* STEP 3: Test all 16 inputs */
    printf("Step 3: Testing brain on all 16 inputs:\n");
    printf("  input | parity | actual | route | status\n");
    printf("  ------+--------+--------+-------+--------\n");

    int8_t expected_mode_a = 0; /* rule-following */
    int8_t expected_mode_b = 0; /* exception */
    int rule_correct = 0, exception_correct = 0;
    int n_exceptions = 0, n_rules = 0;

    for(int m = 0; m < 16; m++){
        int8_t in[4];
        for(int i = 0; i < 4; i++) in[i] = ((m >> i) & 1) ? 1 : -1;
        int par = parity4(in);

        /* Is this an exception? */
        int is_except = 0;
        if(memcmp(in, except1, 4) == 0) is_except = 1;
        if(memcmp(in, except2, 4) == 0) is_except = 1;
        if(memcmp(in, except3, 4) == 0) is_except = 1;

        int expected = is_except ? -1 : par;

        HDV h = encode4(in);
        const char *route;
        int8_t out = brain_process(&brain, in, h, &route);

        const char *status = (out == expected) ? "OK " : "BAD";
        printf("  %d%d%d%d |  %+d    |  %+d    | %s   | %s%s\n",
               in[0]==1?1:0, in[1]==1?1:0, in[2]==1?1:0, in[3]==1?1:0,
               par, out, route, status, is_except?" (exception)":"");

        if(is_except){
            n_exceptions++;
            if(out == -1) exception_correct++;
        } else {
            n_rules++;
            if(out == par) rule_correct++;
        }
    }

    printf("\nResults:\n");
    printf("  Rule-following: %d/%d (%.0f%%)\n",
           rule_correct, n_rules, 100.0*rule_correct/n_rules);
    printf("  Exceptions:     %d/%d (%.0f%%)\n",
           exception_correct, n_exceptions, 100.0*exception_correct/n_exceptions);

    if(rule_correct == n_rules && exception_correct == n_exceptions){
        printf("\n✓✓✓ BITBRAIN WORKS PERFECTLY!\n");
        printf("    Sensory learned parity rule\n");
        printf("    Memory stores exceptions\n");
        printf("    Router correctly dispatches\n");
        printf("    Regions cooperate like brain areas\n");
    } else {
        printf("\n~ Partial: r=%d/%d, e=%d/%d\n",
               rule_correct, n_rules, exception_correct, n_exceptions);
    }

    return 0;
}
