/*
 * BITBRAIN v9: EVERYTHING UNIFIED
 * =================================
 *
 * Combines v6 (classification), v7 (maze), v8 (stream) in single brain.
 *
 * Regions:
 *   ATTENTION      — input bit filtering (v5.1)
 *   SENSORY POOL   — BitNet experts, self-expansion (v5.5)
 *   MEMORY         — HDC exception storage (v5)
 *   META           — consolidation trigger (v5.3)
 *   REASONING      — bit matrix closure (v4)
 *   PLANNING       — BFS on incremental graph (v7)
 *   STREAM         — temporal event processing (v8)
 *
 * Single brain handles: classification, navigation, anomaly detection.
 *
 * Compile: gcc -O3 -march=native -o bitbrain9 bitbrain_v9.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

/* ═══ Constants ═══ */
#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)
#define MAX_MEMORY 100
#define MAX_EXPERTS 4
#define MAX_INPUT 16
#define N_GRAPH_NODES 64
#define GRAPH_WORDS ((N_GRAPH_NODES+63)/64)
#define WINDOW_SIZE 4
#define ALPHABET 16

#define E_IN 8
#define E_H1 24
#define E_H2 12

typedef struct { uint64_t b[HDV_WORDS]; } HDV;

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

/* ═══ HDV ═══ */
static HDV hdv_random(void){HDV v;for(int i=0;i<HDV_WORDS;i++)v.b[i]=rng_next();return v;}
static HDV hdv_zero(void){HDV v;memset(&v,0,sizeof(v));return v;}
static HDV hdv_bind(HDV a,HDV b){HDV r;for(int i=0;i<HDV_WORDS;i++)r.b[i]=a.b[i]^b.b[i];return r;}
static int hdv_ham(HDV a,HDV b){int d=0;for(int i=0;i<HDV_WORDS;i++)d+=__builtin_popcountll(a.b[i]^b.b[i]);return d;}
static double hdv_sim(HDV a,HDV b){return 1.0-(double)hdv_ham(a,b)/HDV_BITS;}

/* Shared HDV prototypes */
static HDV V_bit[2];
static HDV V_pos[MAX_INPUT];
static HDV V_sym[ALPHABET];

/* Encode bit array */
static HDV encode_bits(const int8_t *bits, int n){
    int counters[HDV_BITS] = {0};
    for(int i = 0; i < n; i++){
        int v = bits[i]==1 ? 1 : 0;
        HDV c = hdv_bind(V_bit[v], V_pos[i]);
        for(int k = 0; k < HDV_BITS; k++)
            counters[k] += ((c.b[k>>6] >> (k&63)) & 1) ? 1 : -1;
    }
    HDV r = hdv_zero();
    for(int k = 0; k < HDV_BITS; k++)
        if(counters[k] > 0) r.b[k>>6] |= (1ULL << (k&63));
    return r;
}

/* Encode temporal window */
static HDV encode_window(const int *symbols){
    int counters[HDV_BITS] = {0};
    for(int i = 0; i < WINDOW_SIZE; i++){
        HDV pv = hdv_bind(V_sym[symbols[i]], V_pos[i]);
        for(int k = 0; k < HDV_BITS; k++)
            counters[k] += ((pv.b[k>>6] >> (k&63)) & 1) ? 1 : -1;
    }
    HDV r = hdv_zero();
    for(int k = 0; k < HDV_BITS; k++)
        if(counters[k] > 0) r.b[k>>6] |= (1ULL << (k&63));
    /* XOR all for sensitivity */
    HDV xor_part = hdv_zero();
    for(int i = 0; i < WINDOW_SIZE; i++){
        HDV pv = hdv_bind(V_sym[symbols[i]], V_pos[i]);
        xor_part = hdv_bind(xor_part, pv);
    }
    return hdv_bind(r, xor_part);
}

/* ═══ ATTENTION ═══ */
typedef struct {
    int sensitivity[MAX_INPUT];
    int8_t mask[MAX_INPUT];
    int n_in;
} Attention;

static void attention_init(Attention *a, int n_in){
    a->n_in = n_in;
    for(int i = 0; i < n_in; i++){a->sensitivity[i] = 0; a->mask[i] = 1;}
}
static void attention_learn(Attention *a, int8_t inputs[][MAX_INPUT],
                             int *targets, int n_ex){
    memset(a->sensitivity, 0, sizeof(a->sensitivity));
    for(int i = 0; i < n_ex; i++){
        for(int j = i+1; j < n_ex; j++){
            int n_diff = 0, diff_bit = -1;
            for(int k = 0; k < a->n_in; k++)
                if(inputs[i][k] != inputs[j][k]){n_diff++; diff_bit = k;}
            if(n_diff == 1 && targets[i] != targets[j])
                a->sensitivity[diff_bit]++;
        }
    }
    int max_s = 0;
    for(int i = 0; i < a->n_in; i++) if(a->sensitivity[i] > max_s) max_s = a->sensitivity[i];
    if(max_s > 0)
        for(int i = 0; i < a->n_in; i++)
            a->mask[i] = (a->sensitivity[i] * 3 >= max_s * 2) ? 1 : 0;
}
static void attention_apply(Attention *a, const int8_t *in, int8_t *out){
    for(int i = 0; i < a->n_in; i++) out[i] = a->mask[i] ? in[i] : 0;
}

/* ═══ EXPERT (BitNet with flip-with-regret) ═══ */
typedef struct {
    int8_t W1[E_IN][E_H1];
    int8_t W2[E_H1][E_H2];
    int8_t W3[E_H2];
    int flip_prob;
    int active;
} Expert;

static void expert_init(Expert *e){
    for(int i=0;i<E_IN;i++) for(int j=0;j<E_H1;j++) e->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<E_H1;i++) for(int j=0;j<E_H2;j++) e->W2[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<E_H2;i++) e->W3[i] = (rng_next()&1)?1:-1;
    e->flip_prob = 30;
    e->active = 0;
}

static int8_t expert_forward(Expert *e, const int8_t *in, int *conf){
    int8_t h1[E_H1], h2[E_H2];
    for(int j=0;j<E_H1;j++){
        int sum=0;for(int i=0;i<E_IN;i++) sum += e->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<E_H2;j++){
        int sum=0;for(int i=0;i<E_H1;i++) sum += e->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int sum = 0;
    for(int i=0;i<E_H2;i++) sum += e->W3[i]*h2[i];
    if(conf) *conf = abs(sum);
    return (sum>=0)?1:-1;
}

static void expert_train(Expert *e, const int8_t *in, int target){
    int8_t h1[E_H1], h2[E_H2];
    for(int j=0;j<E_H1;j++){
        int sum=0;for(int i=0;i<E_IN;i++) sum += e->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<E_H2;j++){
        int sum=0;for(int i=0;i<E_H1;i++) sum += e->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int out_sum = 0;
    for(int i=0;i<E_H2;i++) out_sum += e->W3[i]*h2[i];
    int out = (out_sum>=0)?1:-1;
    if(out == target) return;

    int8_t want_h2[E_H2] = {0};
    for(int i=0;i<E_H2;i++){
        int contrib = e->W3[i]*h2[i];
        if(contrib != target){
            if((int)(rng_next()%100) < e->flip_prob) e->W3[i] = -e->W3[i];
        }
        want_h2[i] = target * e->W3[i];
    }
    int8_t want_h1[E_H1] = {0};
    for(int j=0;j<E_H2;j++){
        if(want_h2[j] == h2[j]) continue;
        for(int i=0;i<E_H1;i++){
            int contrib = e->W2[i][j]*h1[i];
            if(contrib != want_h2[j]){
                if((int)(rng_next()%100) < e->flip_prob) e->W2[i][j] = -e->W2[i][j];
            }
        }
        for(int i=0;i<E_H1;i++){
            int w = e->W2[i][j];
            int wnt = want_h2[j]*w;
            if(want_h1[i] == 0) want_h1[i] = wnt;
            else if(want_h1[i] != wnt) want_h1[i] = 0;
        }
    }
    for(int j=0;j<E_H1;j++){
        if(want_h1[j] == 0 || want_h1[j] == h1[j]) continue;
        for(int i=0;i<E_IN;i++){
            int contrib = e->W1[i][j]*in[i];
            if(contrib != want_h1[j]){
                if((int)(rng_next()%100) < e->flip_prob) e->W1[i][j] = -e->W1[i][j];
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
    for(int i = 0; i < m->n; i++)
        if(hdv_sim(key, m->keys[i]) > 0.97){m->values[i] = val; return;}
    if(m->n >= MAX_MEMORY) return;
    m->keys[m->n] = key; m->values[m->n] = val; m->n++;
}
static int8_t memory_recall(Memory *m, HDV key, double *sim_out){
    if(m->n == 0){if(sim_out)*sim_out=0; return 1;}
    int best = 0; double best_sim = -1;
    for(int i = 0; i < m->n; i++){
        double s = hdv_sim(key, m->keys[i]);
        if(s > best_sim){best_sim = s; best = i;}
    }
    if(sim_out) *sim_out = best_sim;
    return m->values[best];
}

/* ═══ META ═══ */
typedef struct {
    int8_t errors[256];
    int8_t total[256];
} Meta;
static void meta_init(Meta *m){memset(m, 0, sizeof(*m));}
static unsigned meta_hash(const int8_t *in, int n){
    unsigned h = 0;
    for(int i = 0; i < n; i++) h = h*31 + (in[i]==1?1:0);
    return h & 0xFF;
}
static void meta_record(Meta *m, const int8_t *in, int n, int wrong){
    unsigned h = meta_hash(in, n);
    if(m->total[h] < 100){
        if(wrong && m->errors[h] < 100) m->errors[h]++;
        m->total[h]++;
    }
}
static int meta_is_hard(Meta *m, const int8_t *in, int n){
    unsigned h = meta_hash(in, n);
    if(m->total[h] < 10) return 0;
    return m->errors[h] * 2 > m->total[h];
}

/* ═══ REASONING / PLANNING (shared bit-graph) ═══ */
typedef struct {
    uint64_t adj[N_GRAPH_NODES][GRAPH_WORDS];
    uint64_t closure[N_GRAPH_NODES][GRAPH_WORDS];
    int n;
    int valid;
} Graph;

static void graph_init(Graph *g, int n){
    memset(g, 0, sizeof(*g));
    g->n = n;
}
static void graph_edge(Graph *g, int from, int to){
    g->adj[from][to>>6] |= (1ULL << (to&63));
    g->valid = 0;
}
static void graph_compute_closure(Graph *g){
    int n = g->n;
    for(int i = 0; i < n; i++){
        for(int w = 0; w < GRAPH_WORDS; w++) g->closure[i][w] = g->adj[i][w];
        g->closure[i][i>>6] |= (1ULL << (i&63));
    }
    for(int k = 0; k < n; k++)
        for(int i = 0; i < n; i++)
            if(g->closure[i][k>>6] & (1ULL << (k&63)))
                for(int w = 0; w < GRAPH_WORDS; w++)
                    g->closure[i][w] |= g->closure[k][w];
    g->valid = 1;
}
static int graph_reachable(Graph *g, int from, int to){
    if(!g->valid) graph_compute_closure(g);
    return (g->closure[from][to>>6] >> (to&63)) & 1;
}

/* BFS shortest path */
static int graph_bfs(Graph *g, int start, int goal, int *path){
    int parent[N_GRAPH_NODES];
    int visited[N_GRAPH_NODES] = {0};
    for(int i = 0; i < g->n; i++) parent[i] = -1;
    int queue[N_GRAPH_NODES], head = 0, tail = 0;
    queue[tail++] = start; visited[start] = 1;
    while(head < tail){
        int cur = queue[head++];
        if(cur == goal){
            int tmp[N_GRAPH_NODES], len = 0;
            int c = goal;
            while(c != -1){tmp[len++] = c; c = parent[c];}
            for(int i = 0; i < len; i++) path[i] = tmp[len-1-i];
            return len;
        }
        for(int s = 0; s < g->n; s++){
            if((g->adj[cur][s>>6] >> (s&63)) & 1){
                if(!visited[s]){visited[s] = 1; parent[s] = cur; queue[tail++] = s;}
            }
        }
    }
    return -1;
}

/* ═══ STREAM ═══ */
typedef struct {
    int window[WINDOW_SIZE];
    int filled;
    int total_events;
    HDV stored_windows[200];
    int stored_hits[200];
    int n_stored;
    double threshold;
} Stream;

static void stream_init(Stream *s, double threshold){
    memset(s, 0, sizeof(*s));
    s->threshold = threshold;
}

static int stream_push(Stream *s, int symbol){
    for(int i = 0; i < WINDOW_SIZE - 1; i++) s->window[i] = s->window[i+1];
    s->window[WINDOW_SIZE - 1] = symbol;
    if(s->filled < WINDOW_SIZE) s->filled++;
    s->total_events++;
    return s->filled == WINDOW_SIZE;
}

static void stream_learn(Stream *s){
    if(s->filled < WINDOW_SIZE) return;
    HDV w = encode_window(s->window);
    for(int i = 0; i < s->n_stored; i++){
        if(hdv_sim(w, s->stored_windows[i]) > 0.99){s->stored_hits[i]++; return;}
    }
    if(s->n_stored >= 200) return;
    s->stored_windows[s->n_stored] = w;
    s->stored_hits[s->n_stored] = 1;
    s->n_stored++;
}

static int stream_is_anomaly(Stream *s, double *fam){
    if(s->filled < WINDOW_SIZE){if(fam)*fam=1.0; return 0;}
    HDV w = encode_window(s->window);
    double best = 0;
    for(int i = 0; i < s->n_stored; i++){
        double sim = hdv_sim(w, s->stored_windows[i]);
        if(sim > best) best = sim;
    }
    if(fam) *fam = best;
    return best < s->threshold;
}

/* ═══ BITBRAIN v9: ALL IN ONE ═══ */
typedef struct {
    Attention attention;
    Expert experts[MAX_EXPERTS];
    int n_experts;
    int current_expert;
    Memory memory;
    Meta meta;
    Graph graph; /* shared for reasoning + planning */
    Stream stream;
} BitBrain;

static void brain_init(BitBrain *b, int n_in){
    attention_init(&b->attention, n_in);
    for(int i = 0; i < MAX_EXPERTS; i++){
        rng_seed(3000 + i * 131);
        expert_init(&b->experts[i]);
    }
    b->n_experts = 1;
    b->experts[0].active = 1;
    b->current_expert = 0;
    memory_init(&b->memory);
    meta_init(&b->meta);
    graph_init(&b->graph, N_GRAPH_NODES);
    stream_init(&b->stream, 0.95);
}

/* Classification: attention → memory → expert */
static int8_t brain_classify(BitBrain *b, const int8_t *in, int n_in){
    int8_t filt[MAX_INPUT];
    attention_apply(&b->attention, in, filt);
    HDV key = encode_bits(in, n_in);
    double mem_sim;
    int8_t mem_val = memory_recall(&b->memory, key, &mem_sim);
    if(mem_sim >= 0.97) return mem_val;
    int conf;
    return expert_forward(&b->experts[b->current_expert], filt, &conf);
}

static void brain_classify_learn(BitBrain *b, const int8_t *in, int n_in, int target){
    int8_t filt[MAX_INPUT];
    attention_apply(&b->attention, in, filt);
    int conf;
    int8_t pred = expert_forward(&b->experts[b->current_expert], filt, &conf);
    meta_record(&b->meta, in, n_in, pred != target);
    expert_train(&b->experts[b->current_expert], filt, target);
    if(pred != target && meta_is_hard(&b->meta, in, n_in)){
        HDV key = encode_bits(in, n_in);
        memory_store(&b->memory, key, target);
    }
}

/* Navigation: graph-based planning */
static void brain_nav_add(BitBrain *b, int from, int to){
    graph_edge(&b->graph, from, to);
    graph_edge(&b->graph, to, from); /* undirected for maze */
}
static int brain_nav_path(BitBrain *b, int start, int goal, int *path){
    return graph_bfs(&b->graph, start, goal, path);
}

/* Stream: temporal pattern learning */
static int brain_stream_observe(BitBrain *b, int symbol, int learning){
    int ready = stream_push(&b->stream, symbol);
    if(!ready) return 0;
    if(learning){stream_learn(&b->stream); return 0;}
    return stream_is_anomaly(&b->stream, NULL);
}

/* ═══ TEST SUITE ═══ */

static int f_parity(const int8_t *in, int n){
    int p = 1;
    for(int i = 0; i < n; i++) p *= in[i];
    return p;
}

static int test_classification(BitBrain *b){
    /* Parity-4 with attention-worthy noise (4 signal + 4 noise = 8) */
    brain_init(b, 8);
    int8_t inputs[256][MAX_INPUT] = {0};
    int targets[256];
    int n_ex = 256;
    for(int m = 0; m < n_ex; m++){
        for(int i = 0; i < 8; i++) inputs[m][i] = ((m>>i)&1)?1:-1;
        /* Target = parity of first 4 only */
        targets[m] = inputs[m][0]*inputs[m][1]*inputs[m][2]*inputs[m][3];
    }
    attention_learn(&b->attention, inputs, targets, n_ex);

    for(int epoch = 0; epoch < 100; epoch++){
        for(int m = 0; m < n_ex; m++) brain_classify_learn(b, inputs[m], 8, targets[m]);
        if(epoch > 30 && (epoch%5)==0 && b->experts[0].flip_prob > 5)
            b->experts[0].flip_prob--;
        int correct = 0;
        for(int m = 0; m < n_ex; m++)
            if(brain_classify(b, inputs[m], 8) == targets[m]) correct++;
        if(correct == n_ex){
            printf("  Classification: %d/%d ✓ (epoch %d, attn=%d/8)\n",
                   correct, n_ex, epoch,
                   b->attention.mask[0]+b->attention.mask[1]+b->attention.mask[2]+b->attention.mask[3]+
                   b->attention.mask[4]+b->attention.mask[5]+b->attention.mask[6]+b->attention.mask[7]);
            return 1;
        }
    }
    int correct = 0;
    for(int m = 0; m < n_ex; m++)
        if(brain_classify(b, inputs[m], 8) == targets[m]) correct++;
    printf("  Classification: %d/%d\n", correct, n_ex);
    return correct == n_ex;
}

static int test_navigation(BitBrain *b){
    /* 6×6 maze, edges: create a path from 0 to 35 with branches */
    graph_init(&b->graph, 36);
    /* Simple graph: linear 0→1→2→3→...→35 with some shortcuts */
    for(int i = 0; i < 35; i++) brain_nav_add(b, i, i+1);
    /* Shortcut: 5→15 */
    brain_nav_add(b, 5, 15);
    /* Shortcut: 10→25 */
    brain_nav_add(b, 10, 25);

    int path[N_GRAPH_NODES];
    int len = brain_nav_path(b, 0, 35, path);
    /* With shortcuts: 0→1→2→3→4→5→15→16→17...→25→26...→35
       = 0→5 (6 nodes), 5→15 (shortcut), 15→25 (11 steps), 25→35 (11 steps)
       = 6 + 1 + 10 + 10 + 1 = actually need to compute */
    /* Without shortcuts: 36 nodes in path. With: fewer. */
    printf("  Navigation: path length %d (should be < 36)\n", len);
    return len > 0 && len < 36;
}

static int test_stream(BitBrain *b){
    stream_init(&b->stream, 0.95);
    /* Train on ABCD pattern */
    int pattern[] = {0, 1, 2, 3};
    for(int i = 0; i < 100; i++) brain_stream_observe(b, pattern[i%4], 1);

    /* Test: inject anomaly at position 15 */
    int detected = 0;
    for(int i = 0; i < 30; i++){
        int sym = (i == 15) ? 9 : pattern[i%4];
        if(brain_stream_observe(b, sym, 0)) detected = 1;
    }
    printf("  Stream anomaly detection: %s\n", detected ? "✓" : "✗");
    return detected;
}

static int test_reasoning(BitBrain *b){
    graph_init(&b->graph, 8);
    graph_edge(&b->graph, 0, 1);
    graph_edge(&b->graph, 1, 2);
    graph_edge(&b->graph, 2, 3);
    graph_edge(&b->graph, 0, 4);
    graph_compute_closure(&b->graph);

    int ok = graph_reachable(&b->graph, 0, 3) &&
             graph_reachable(&b->graph, 0, 4) &&
             !graph_reachable(&b->graph, 3, 0) &&
             !graph_reachable(&b->graph, 4, 3);
    printf("  Reasoning (closure): %s\n", ok ? "✓" : "✗");
    return ok;
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v9: EVERYTHING UNIFIED\n");
    printf("══════════════════════════════════════════\n\n");

    rng_seed(42);
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < MAX_INPUT; i++) V_pos[i] = hdv_random();
    for(int i = 0; i < ALPHABET; i++) V_sym[i] = hdv_random();

    printf("Regions: Attention, Experts, Memory, Meta, Graph, Stream\n");
    printf("Brain size: ~%zu KB\n\n", sizeof(BitBrain)/1024);

    BitBrain brain;
    brain_init(&brain, 8);

    printf("═══ TEST SUITE ═══\n\n");

    int passed = 0, total = 0;

    printf("[1] Classification (parity + noise):\n");
    if(test_classification(&brain)) passed++;
    total++;
    printf("\n[2] Navigation (graph shortest path):\n");
    if(test_navigation(&brain)) passed++;
    total++;
    printf("\n[3] Stream anomaly detection:\n");
    if(test_stream(&brain)) passed++;
    total++;
    printf("\n[4] Reasoning (transitive closure):\n");
    if(test_reasoning(&brain)) passed++;
    total++;

    printf("\n═══ SUMMARY ═══\n");
    printf("Passed: %d/%d\n", passed, total);
    if(passed == total){
        printf("\n✓✓✓ UNIFIED v9: all task types handled\n");
        printf("    Single BitBrain, 4 different task domains\n");
        printf("    Classification + Navigation + Streaming + Reasoning\n");
        printf("    Brain size: ~%zu KB\n", sizeof(BitBrain)/1024);
    }

    return 0;
}
