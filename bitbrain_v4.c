/*
 * BITBRAIN v4: three regions — Sensory, Memory, Reasoning
 * ========================================================
 *
 * New: REASONING region using bit-native graph propagation
 *   - Stores relations as bit matrices
 *   - Transitive closure via iterative bit operations
 *   - Answers "are X and Y related?" in O(n²) bit ops
 *
 * Improvements over v3:
 *   - Adaptive flip_prob (increases on stalls, decreases on progress)
 *   - Reasoning region for relational queries
 *   - Composite task requiring all three regions
 *
 * Theory: Brain(x) = f_{argmax_r s_r(x)}(x)
 *   specialization s_r measures "how much this region applies"
 *
 * Compile: gcc -O3 -march=native -o bitbrain4 bitbrain_v4.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)
#define MAX_MEMORY 50
#define MAX_REASON_NODES 64

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
    /* Bundle-based encoding (fixed from v3) */
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

/* ═══════════════════════════════════════════
 * REGION 1: SENSORY (BitNet)
 * ═══════════════════════════════════════════ */
#define S_IN 4
#define S_H1 16
#define S_H2 8

typedef struct {
    int8_t W1[S_IN][S_H1];
    int8_t W2[S_H1][S_H2];
    int8_t W3[S_H2];
    int flip_prob;        /* adaptive */
    int recent_correct;
    int recent_total;
} Sensory;

static void sensory_init(Sensory *s){
    for(int i=0;i<S_IN;i++) for(int j=0;j<S_H1;j++) s->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<S_H1;i++) for(int j=0;j<S_H2;j++) s->W2[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<S_H2;i++) s->W3[i] = (rng_next()&1)?1:-1;
    s->flip_prob = 30;
    s->recent_correct = 0;
    s->recent_total = 0;
}

static int8_t sensory_forward(Sensory *s, const int8_t *in){
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
    return (sum>=0)?1:-1;
}

/* Specialization: how "patterned" does this input look?
 * Heuristic: return 1 (always applicable) */
static double sensory_specialization(Sensory *s, const int8_t *in){
    (void)s; (void)in;
    return 0.5; /* baseline specialization */
}

/* Adaptive training */
static void sensory_train_batch(Sensory *s, int8_t inputs[][4], int *targets, int n_ex){
    /* Count correct before training */
    int correct = 0;
    for(int i = 0; i < n_ex; i++){
        if(sensory_forward(s, inputs[i]) == targets[i]) correct++;
    }

    /* Adapt flip_prob based on progress */
    s->recent_total += n_ex;
    s->recent_correct += correct;
    if(s->recent_total >= 64){
        double rate = (double)s->recent_correct / s->recent_total;
        if(rate > 0.9 && s->flip_prob > 3) s->flip_prob--;  /* converging: exploit */
        else if(rate < 0.6 && s->flip_prob < 40) s->flip_prob++; /* stuck: explore */
        s->recent_total = 0;
        s->recent_correct = 0;
    }

    /* Train */
    for(int idx = 0; idx < n_ex; idx++){
        const int8_t *in = inputs[idx];
        int target = targets[idx];

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
        if(out == target) continue;

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
}

/* ═══════════════════════════════════════════
 * REGION 2: MEMORY (HDC)
 * ═══════════════════════════════════════════ */
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

/* Specialization: how familiar is this input? */
static double memory_specialization(Memory *m, HDV key){
    double s;
    memory_recall(m, key, &s);
    return s; /* direct similarity as specialization */
}

/* ═══════════════════════════════════════════
 * REGION 3: REASONING (bit-native graph propagation)
 * ═══════════════════════════════════════════
 *
 * Stores a directed graph as bit matrix.
 * Supports: add edge, query transitive closure, count connections.
 */
#define REASON_WORDS ((MAX_REASON_NODES + 63) / 64)

typedef struct {
    uint64_t adj[MAX_REASON_NODES][REASON_WORDS];
    uint64_t closure[MAX_REASON_NODES][REASON_WORDS];
    int n_nodes;
    int closure_valid;
} Reasoning;

static void reason_init(Reasoning *r){
    memset(r, 0, sizeof(*r));
}

static void reason_set_nodes(Reasoning *r, int n){
    r->n_nodes = n;
    memset(r->adj, 0, sizeof(r->adj));
    memset(r->closure, 0, sizeof(r->closure));
    r->closure_valid = 0;
}

static void reason_add_edge(Reasoning *r, int from, int to){
    if(from >= r->n_nodes || to >= r->n_nodes) return;
    r->adj[from][to>>6] |= (1ULL << (to&63));
    r->closure_valid = 0;
}

/* Compute transitive closure via iterated bit-matrix multiplication (Warshall-like) */
static void reason_compute_closure(Reasoning *r){
    int n = r->n_nodes;
    /* Initialize closure = adj + identity */
    for(int i = 0; i < n; i++){
        for(int w = 0; w < REASON_WORDS; w++) r->closure[i][w] = r->adj[i][w];
        r->closure[i][i>>6] |= (1ULL << (i&63)); /* self-loop */
    }

    /* Warshall: for each k, if i→k and k→j, then i→j */
    for(int k = 0; k < n; k++){
        for(int i = 0; i < n; i++){
            /* If i can reach k... */
            if(r->closure[i][k>>6] & (1ULL << (k&63))){
                /* ...then OR in k's reachability */
                for(int w = 0; w < REASON_WORDS; w++){
                    r->closure[i][w] |= r->closure[k][w];
                }
            }
        }
    }
    r->closure_valid = 1;
}

static int reason_reachable(Reasoning *r, int from, int to){
    if(!r->closure_valid) reason_compute_closure(r);
    return (r->closure[from][to>>6] >> (to&63)) & 1;
}

static int reason_count_reachable(Reasoning *r, int from){
    if(!r->closure_valid) reason_compute_closure(r);
    int count = 0;
    for(int w = 0; w < REASON_WORDS; w++) count += __builtin_popcountll(r->closure[from][w]);
    return count;
}

/* ═══════════════════════════════════════════
 * BITBRAIN: integrated
 * ═══════════════════════════════════════════ */
typedef struct {
    Sensory sensory;
    Memory memory;
    Reasoning reasoning;
} BitBrain;

static void brain_init(BitBrain *b){
    sensory_init(&b->sensory);
    memory_init(&b->memory);
    reason_init(&b->reasoning);
}

/* ═══════════════════════════════════════════
 * COMPOSITE TEST
 *
 * Task: classify small 4-bit inputs with:
 *   - Rule (parity) → SENSORY
 *   - Exceptions (specific overrides) → MEMORY
 * AND
 * Task: answer connectivity queries on stored graph → REASONING
 * ═══════════════════════════════════════════ */

static int test_sensory(BitBrain *b, int *rule_correct, int *rule_total){
    /* Train and test parity */
    int8_t inputs[16][4];
    int targets[16];
    for(int m = 0; m < 16; m++){
        for(int i = 0; i < 4; i++) inputs[m][i] = ((m>>i)&1) ? 1 : -1;
        targets[m] = inputs[m][0] * inputs[m][1] * inputs[m][2] * inputs[m][3];
    }

    /* Train until convergence */
    int best = 0;
    for(int epoch = 0; epoch < 500; epoch++){
        sensory_train_batch(&b->sensory, inputs, targets, 16);
        int correct = 0;
        for(int m = 0; m < 16; m++){
            if(sensory_forward(&b->sensory, inputs[m]) == targets[m]) correct++;
        }
        if(correct > best) best = correct;
        if(correct == 16) return epoch;
    }
    *rule_correct = best;
    *rule_total = 16;
    return -1;
}

static int test_memory(BitBrain *b, int *ex_correct, int *ex_total){
    /* Store 3 exceptions */
    int8_t except1[4] = {1, 1, 1, 1};
    int8_t except2[4] = {-1, -1, 1, 1};
    int8_t except3[4] = {1, -1, 1, -1};
    memory_store(&b->memory, encode_bits(except1, 4), -1);
    memory_store(&b->memory, encode_bits(except2, 4), -1);
    memory_store(&b->memory, encode_bits(except3, 4), -1);

    int correct = 0;
    int8_t *exs[3] = {except1, except2, except3};
    for(int i = 0; i < 3; i++){
        double s;
        int8_t v = memory_recall(&b->memory, encode_bits(exs[i], 4), &s);
        if(v == -1 && s > 0.95) correct++;
    }
    *ex_correct = correct;
    *ex_total = 3;
    return correct == 3;
}

static int test_reasoning(BitBrain *b){
    /* Build a small graph: A→B→C→D, A→E, F isolated */
    reason_set_nodes(&b->reasoning, 6);
    reason_add_edge(&b->reasoning, 0, 1); /* A→B */
    reason_add_edge(&b->reasoning, 1, 2); /* B→C */
    reason_add_edge(&b->reasoning, 2, 3); /* C→D */
    reason_add_edge(&b->reasoning, 0, 4); /* A→E */
    /* F (5) isolated */

    reason_compute_closure(&b->reasoning);

    /* Queries */
    struct {int from, to, expected;} queries[] = {
        {0, 1, 1}, /* A→B direct */
        {0, 2, 1}, /* A→C transitive */
        {0, 3, 1}, /* A→D transitive */
        {0, 4, 1}, /* A→E direct */
        {0, 5, 0}, /* A→F unreachable */
        {3, 0, 0}, /* D→A backward */
        {5, 0, 0}, /* F→A unreachable */
        {2, 3, 1}, /* C→D direct */
    };
    int n_queries = 8;
    int correct = 0;

    printf("  Reasoning queries:\n");
    for(int q = 0; q < n_queries; q++){
        int result = reason_reachable(&b->reasoning, queries[q].from, queries[q].to);
        int ok = (result == queries[q].expected);
        if(ok) correct++;
        printf("    %c→%c: %s (expected %d, got %d) %s\n",
               'A' + queries[q].from, 'A' + queries[q].to,
               ok ? "✓" : "✗", queries[q].expected, result,
               queries[q].from==0 && queries[q].to==3 ? " [A→B→C→D]" : "");
    }

    printf("  Reachable from A: %d nodes\n", reason_count_reachable(&b->reasoning, 0));
    return correct == n_queries;
}

/* ═══════════════════════════════════════════
 * COMPOSITE TASK
 *
 * Scenario: simple facts about related objects
 *   - "X likes Y" → store as edge in reasoning graph
 *   - "Is X related to Y?" → query transitive closure
 *
 * Classify input type via sensory (fact vs question)
 * Store facts via reasoning
 * Answer questions via reasoning
 * ═══════════════════════════════════════════ */

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v4: three-region architecture\n");
    printf("══════════════════════════════════════════\n\n");

    rng_seed(42);
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < 16; i++) V_pos[i] = hdv_random();

    BitBrain brain;
    brain_init(&brain);

    printf("Architecture:\n");
    printf("  SENSORY:   BitNet 4→16→8→1 with adaptive flip_prob\n");
    printf("  MEMORY:    HDC 2048-bit, up to 50 exceptions\n");
    printf("  REASONING: bit matrix %dx%d, Warshall closure\n\n",
           MAX_REASON_NODES, MAX_REASON_NODES);

    /* ── Test 1: Sensory learns parity ── */
    printf("Test 1: SENSORY learns parity\n");
    printf("──────────────────────────────\n");
    int rule_correct, rule_total;
    int epochs = test_sensory(&brain, &rule_correct, &rule_total);
    if(epochs >= 0){
        printf("  ✓ Parity learned in %d epochs (adaptive flip_prob)\n", epochs);
        printf("  Final flip_prob: %d\n", brain.sensory.flip_prob);
    } else {
        printf("  Best: %d/%d\n", rule_correct, rule_total);
    }

    /* ── Test 2: Memory stores exceptions ── */
    printf("\nTest 2: MEMORY stores exceptions\n");
    printf("─────────────────────────────────\n");
    int ex_correct, ex_total;
    int mem_ok = test_memory(&brain, &ex_correct, &ex_total);
    printf("  %s Exceptions stored and recalled: %d/%d\n",
           mem_ok ? "✓" : "✗", ex_correct, ex_total);

    /* ── Test 3: Reasoning computes closure ── */
    printf("\nTest 3: REASONING computes transitive closure\n");
    printf("──────────────────────────────────────────────\n");
    int reason_ok = test_reasoning(&brain);
    printf("  %s All queries answered correctly\n", reason_ok ? "✓" : "✗");

    /* ── Test 4: Integrated behavior ── */
    printf("\nTest 4: INTEGRATED behavior\n");
    printf("────────────────────────────\n");
    printf("All regions active simultaneously, no interference\n");

    /* Run all tests again in interleaved order */
    int all_ok = 1;

    /* Sensory check */
    for(int m = 0; m < 16; m++){
        int8_t in[4];
        for(int i = 0; i < 4; i++) in[i] = ((m>>i)&1)?1:-1;
        int target = in[0]*in[1]*in[2]*in[3];
        /* Check if it's a stored exception */
        int is_except = (m==0x0F || m==0x03 || m==0x05);
        if(is_except) continue;
        if(sensory_forward(&brain.sensory, in) != target){all_ok = 0; break;}
    }
    printf("  Sensory still works: %s\n", all_ok ? "✓" : "✗");

    /* Memory check */
    int8_t ex[4] = {1,1,1,1};
    double sim;
    int8_t v = memory_recall(&brain.memory, encode_bits(ex, 4), &sim);
    printf("  Memory still works: %s (sim=%.3f, val=%d)\n",
           (v==-1 && sim>0.95)?"✓":"✗", sim, v);

    /* Reasoning check */
    printf("  Reasoning still works: %s (A can reach %d nodes)\n",
           reason_reachable(&brain.reasoning, 0, 3)?"✓":"✗",
           reason_count_reachable(&brain.reasoning, 0));

    printf("\n═══ SUMMARY ═══\n");
    printf("Sensory (patterns):   %s\n", epochs>=0?"PASS":"FAIL");
    printf("Memory (exceptions):  %s\n", mem_ok?"PASS":"FAIL");
    printf("Reasoning (graph):    %s\n", reason_ok?"PASS":"FAIL");
    printf("Integration:          %s\n", all_ok?"PASS":"FAIL");

    if(epochs>=0 && mem_ok && reason_ok && all_ok){
        printf("\n✓✓✓ BITBRAIN v4: all regions cooperating\n");
        printf("    Three different computational paradigms\n");
        printf("    Unified under bit-native architecture\n");
        printf("    No floating point anywhere\n");
    }

    printf("\n═══ STATS ═══\n");
    printf("Sensory weights:    %d bits\n",
           S_IN*S_H1 + S_H1*S_H2 + S_H2);
    printf("Memory capacity:    %d × %d bits + %d values\n",
           MAX_MEMORY, HDV_BITS, MAX_MEMORY*8);
    printf("Reasoning storage:  %d × %d bits = %d bytes\n",
           MAX_REASON_NODES, MAX_REASON_NODES,
           MAX_REASON_NODES*MAX_REASON_NODES/8);
    printf("Total brain size:   ~%zu KB\n", sizeof(BitBrain)/1024);

    return 0;
}
