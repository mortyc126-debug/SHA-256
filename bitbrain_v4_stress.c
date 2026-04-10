/*
 * BITBRAIN v4 STRESS TEST: find where it breaks
 * ==============================================
 *
 * Tests each region under harder conditions:
 *   SENSORY:   learn various functions (XOR, Parity-N, Majority, AND/OR)
 *   MEMORY:    store many exceptions with noisy queries
 *   REASONING: larger graphs with various structures
 *
 * Goal: identify exact breaking points before building v5.
 *
 * Compile: gcc -O3 -march=native -o bb4_stress bitbrain_v4_stress.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)
#define MAX_MEMORY 200
#define MAX_REASON_NODES 128

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

/* ═══ SENSORY with variable size ═══ */
#define S_MAX_IN 8
#define S_MAX_H1 32
#define S_MAX_H2 16

typedef struct {
    int n_in, n_h1, n_h2;
    int8_t W1[S_MAX_IN][S_MAX_H1];
    int8_t W2[S_MAX_H1][S_MAX_H2];
    int8_t W3[S_MAX_H2];
    int flip_prob;
} Sensory;

static void sensory_init(Sensory *s, int n_in, int n_h1, int n_h2){
    s->n_in = n_in; s->n_h1 = n_h1; s->n_h2 = n_h2;
    for(int i=0;i<n_in;i++) for(int j=0;j<n_h1;j++) s->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<n_h1;i++) for(int j=0;j<n_h2;j++) s->W2[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<n_h2;i++) s->W3[i] = (rng_next()&1)?1:-1;
    s->flip_prob = 30;
}

static int8_t sensory_forward(Sensory *s, const int8_t *in){
    int8_t h1[S_MAX_H1], h2[S_MAX_H2];
    for(int j=0;j<s->n_h1;j++){
        int sum=0;for(int i=0;i<s->n_in;i++) sum += s->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<s->n_h2;j++){
        int sum=0;for(int i=0;i<s->n_h1;i++) sum += s->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int sum = 0;
    for(int i=0;i<s->n_h2;i++) sum += s->W3[i]*h2[i];
    return (sum>=0)?1:-1;
}

static void sensory_train_one(Sensory *s, const int8_t *in, int target){
    int8_t h1[S_MAX_H1], h2[S_MAX_H2];
    for(int j=0;j<s->n_h1;j++){
        int sum=0;for(int i=0;i<s->n_in;i++) sum += s->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<s->n_h2;j++){
        int sum=0;for(int i=0;i<s->n_h1;i++) sum += s->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int out_sum = 0;
    for(int i=0;i<s->n_h2;i++) out_sum += s->W3[i]*h2[i];
    int out = (out_sum>=0)?1:-1;
    if(out == target) return;

    int8_t want_h2[S_MAX_H2] = {0};
    for(int i=0;i<s->n_h2;i++){
        int contrib = s->W3[i]*h2[i];
        if(contrib != target){
            if((int)(rng_next()%100) < s->flip_prob) s->W3[i] = -s->W3[i];
        }
        want_h2[i] = target * s->W3[i];
    }

    int8_t want_h1[S_MAX_H1] = {0};
    for(int j=0;j<s->n_h2;j++){
        if(want_h2[j] == h2[j]) continue;
        for(int i=0;i<s->n_h1;i++){
            int contrib = s->W2[i][j]*h1[i];
            if(contrib != want_h2[j]){
                if((int)(rng_next()%100) < s->flip_prob) s->W2[i][j] = -s->W2[i][j];
            }
        }
        for(int i=0;i<s->n_h1;i++){
            int w = s->W2[i][j];
            int wnt = want_h2[j]*w;
            if(want_h1[i] == 0) want_h1[i] = wnt;
            else if(want_h1[i] != wnt) want_h1[i] = 0;
        }
    }

    for(int j=0;j<s->n_h1;j++){
        if(want_h1[j] == 0 || want_h1[j] == h1[j]) continue;
        for(int i=0;i<s->n_in;i++){
            int contrib = s->W1[i][j]*in[i];
            if(contrib != want_h1[j]){
                if((int)(rng_next()%100) < s->flip_prob) s->W1[i][j] = -s->W1[i][j];
            }
        }
    }
}

/* Target function type */
typedef int (*TargetFn)(const int8_t *in);

static int fn_parity(const int8_t *in){ /* arbitrary-n parity */
    int p = 1;
    return p; /* override per-test */
}

static int test_sensory_function(const char *name, int n_in, TargetFn fn, int max_epochs){
    Sensory s;
    /* Architecture scales with n_in */
    int h1 = 8 * n_in; if(h1 > S_MAX_H1) h1 = S_MAX_H1;
    int h2 = 4 * n_in; if(h2 > S_MAX_H2) h2 = S_MAX_H2;

    int best = 0;
    int best_epochs = -1;
    int n_ex = 1 << n_in;

    /* Multiple trials */
    for(int trial = 0; trial < 5; trial++){
        rng_seed(42 + trial*1000);
        sensory_init(&s, n_in, h1, h2);

        for(int epoch = 0; epoch < max_epochs; epoch++){
            for(int ex = 0; ex < n_ex; ex++){
                int8_t in[S_MAX_IN];
                for(int i = 0; i < n_in; i++) in[i] = ((ex>>i)&1)?1:-1;
                sensory_train_one(&s, in, fn(in));

                /* Adapt flip_prob */
                if(epoch > max_epochs/2 && s.flip_prob > 5) s.flip_prob--;
            }
            /* Eval */
            int correct = 0;
            for(int ex = 0; ex < n_ex; ex++){
                int8_t in[S_MAX_IN];
                for(int i = 0; i < n_in; i++) in[i] = ((ex>>i)&1)?1:-1;
                if(sensory_forward(&s, in) == fn(in)) correct++;
            }
            if(correct > best){
                best = correct;
                best_epochs = epoch;
            }
            if(correct == n_ex){
                printf("  %-15s (n=%d, %d/%d): ✓ trial %d, epoch %d\n",
                       name, n_in, correct, n_ex, trial, epoch);
                return epoch;
            }
        }
    }
    printf("  %-15s (n=%d, %d/%d): BEST %d/%d at epoch %d\n",
           name, n_in, best, n_ex, best, n_ex, best_epochs);
    return -1;
}

/* Target functions */
static int f_xor(const int8_t *in){ return in[0]*in[1]; }
static int f_parity3(const int8_t *in){ return in[0]*in[1]*in[2]; }
static int f_parity4(const int8_t *in){ return in[0]*in[1]*in[2]*in[3]; }
static int f_parity5(const int8_t *in){ return in[0]*in[1]*in[2]*in[3]*in[4]; }
static int f_parity6(const int8_t *in){ return in[0]*in[1]*in[2]*in[3]*in[4]*in[5]; }
static int f_and4(const int8_t *in){ return (in[0]==1&&in[1]==1&&in[2]==1&&in[3]==1)?1:-1; }
static int f_or4(const int8_t *in){ return (in[0]==1||in[1]==1||in[2]==1||in[3]==1)?1:-1; }
static int f_majority5(const int8_t *in){
    int s = in[0]+in[1]+in[2]+in[3]+in[4]; return s>0?1:-1;
}
static int f_custom(const int8_t *in){
    /* (x0 AND x1) XOR (x2 AND x3) */
    int a = (in[0]==1 && in[1]==1) ? 1 : -1;
    int b = (in[2]==1 && in[3]==1) ? 1 : -1;
    return a*b;
}

/* ═══ MEMORY stress test ═══ */
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

static void test_memory_stress(void){
    printf("\nMEMORY stress test\n");
    printf("──────────────────\n");

    int mem_sizes[] = {10, 30, 50, 100, 150, 200};
    for(int ni_idx = 0; ni_idx < 6; ni_idx++){
        int n_items = mem_sizes[ni_idx];
        Memory m;
        memory_init(&m);

        /* Store n_items random 8-bit patterns with random values */
        int8_t patterns[MAX_MEMORY][8];
        int8_t values[MAX_MEMORY];
        rng_seed(42 + n_items);
        for(int i = 0; i < n_items; i++){
            for(int j = 0; j < 8; j++) patterns[i][j] = (rng_next()&1)?1:-1;
            values[i] = (rng_next()&1)?1:-1;
            memory_store(&m, encode_bits(patterns[i], 8), values[i]);
        }

        /* Clean recall */
        int clean_correct = 0;
        for(int i = 0; i < n_items; i++){
            double s;
            int8_t v = memory_recall(&m, encode_bits(patterns[i], 8), &s);
            if(v == values[i]) clean_correct++;
        }

        /* Noisy recall (flip 1-2 bits) */
        int noisy_correct = 0;
        for(int i = 0; i < n_items; i++){
            int8_t noisy[8];
            memcpy(noisy, patterns[i], 8);
            int flip_idx = rng_next() % 8;
            noisy[flip_idx] = -noisy[flip_idx];
            double s;
            int8_t v = memory_recall(&m, encode_bits(noisy, 8), &s);
            if(v == values[i]) noisy_correct++;
        }

        printf("  n=%3d: clean %d/%d (%.0f%%), noisy %d/%d (%.0f%%)\n",
               n_items, clean_correct, n_items, 100.0*clean_correct/n_items,
               noisy_correct, n_items, 100.0*noisy_correct/n_items);
    }
}

/* ═══ REASONING stress test ═══ */
#define REASON_WORDS ((MAX_REASON_NODES + 63) / 64)

typedef struct {
    uint64_t adj[MAX_REASON_NODES][REASON_WORDS];
    uint64_t closure[MAX_REASON_NODES][REASON_WORDS];
    int n_nodes;
} Reasoning;

static void reason_init(Reasoning *r, int n){
    memset(r, 0, sizeof(*r));
    r->n_nodes = n;
}

static void reason_add_edge(Reasoning *r, int from, int to){
    r->adj[from][to>>6] |= (1ULL << (to&63));
}

static void reason_closure(Reasoning *r){
    int n = r->n_nodes;
    for(int i = 0; i < n; i++){
        for(int w = 0; w < REASON_WORDS; w++) r->closure[i][w] = r->adj[i][w];
        r->closure[i][i>>6] |= (1ULL << (i&63));
    }
    for(int k = 0; k < n; k++){
        for(int i = 0; i < n; i++){
            if(r->closure[i][k>>6] & (1ULL << (k&63))){
                for(int w = 0; w < REASON_WORDS; w++){
                    r->closure[i][w] |= r->closure[k][w];
                }
            }
        }
    }
}

static int reason_reachable(Reasoning *r, int from, int to){
    return (r->closure[from][to>>6] >> (to&63)) & 1;
}

/* Brute force reachability for verification */
static int brute_reachable(int n, int *edges_from, int *edges_to, int n_edges, int from, int to){
    int *visited = calloc(n, sizeof(int));
    int *queue = malloc(n * sizeof(int));
    int head = 0, tail = 0;
    visited[from] = 1;
    queue[tail++] = from;
    int result = 0;
    while(head < tail){
        int cur = queue[head++];
        if(cur == to){result = 1; break;}
        for(int i = 0; i < n_edges; i++){
            if(edges_from[i] == cur && !visited[edges_to[i]]){
                visited[edges_to[i]] = 1;
                queue[tail++] = edges_to[i];
            }
        }
    }
    free(visited); free(queue);
    return result;
}

static void test_reasoning_stress(void){
    printf("\nREASONING stress test\n");
    printf("─────────────────────\n");

    int node_sizes[] = {10, 20, 50, 100};
    for(int nn_idx = 0; nn_idx < 4; nn_idx++){
        int n_nodes = node_sizes[nn_idx];
        Reasoning r;
        reason_init(&r, n_nodes);

        /* Random graph with ~2n edges */
        int n_edges = 2 * n_nodes;
        int ef[500], et[500];
        rng_seed(100 + n_nodes);
        for(int i = 0; i < n_edges; i++){
            ef[i] = rng_next() % n_nodes;
            et[i] = rng_next() % n_nodes;
            reason_add_edge(&r, ef[i], et[i]);
        }

        reason_closure(&r);

        /* Verify with random queries */
        int n_queries = 100;
        int correct = 0;
        for(int q = 0; q < n_queries; q++){
            int from = rng_next() % n_nodes;
            int to = rng_next() % n_nodes;
            int bitbrain = reason_reachable(&r, from, to);
            int truth = (from == to) ? 1 : brute_reachable(n_nodes, ef, et, n_edges, from, to);
            if(bitbrain == truth) correct++;
        }

        printf("  n=%3d, edges=%d: %d/%d correct (%.0f%%)\n",
               n_nodes, n_edges, correct, n_queries, 100.0*correct/n_queries);
    }
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v4 STRESS TEST\n");
    printf("══════════════════════════════════════════\n");

    rng_seed(42);
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < 32; i++) V_pos[i] = hdv_random();

    /* ── SENSORY STRESS ── */
    printf("\nSENSORY stress test\n");
    printf("───────────────────\n");

    test_sensory_function("XOR",        2, f_xor,       200);
    test_sensory_function("Parity-3",   3, f_parity3,   200);
    test_sensory_function("Parity-4",   4, f_parity4,   500);
    test_sensory_function("Parity-5",   5, f_parity5,   1000);
    test_sensory_function("Parity-6",   6, f_parity6,   2000);
    test_sensory_function("AND-4",      4, f_and4,      500);
    test_sensory_function("OR-4",       4, f_or4,       500);
    test_sensory_function("Majority-5", 5, f_majority5, 1000);
    test_sensory_function("Custom",     4, f_custom,    500);

    /* ── MEMORY STRESS ── */
    test_memory_stress();

    /* ── REASONING STRESS ── */
    test_reasoning_stress();

    return 0;
}
