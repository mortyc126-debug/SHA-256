/*
 * BITBRAIN v8: STREAM processing (event-driven, temporal)
 * =========================================================
 *
 * New paradigm: no clock ticks, only events.
 * Brain processes stream of symbols, maintains temporal context,
 * detects anomalies (patterns that don't match learned normal).
 *
 * Architecture:
 *   TEMPORAL BUFFER: sliding window of last K events
 *   PATTERN MEMORY:  HDC store of "normal" window encodings
 *   ANOMALY DETECT:  compares current window to memory
 *
 * Task: repeating pattern with noise + inserted anomalies
 *   Normal:  A B C D A B C D A B C D ...
 *   Anomaly: A B C D A B *X* D A B ...  (X is unexpected)
 *   Noise:   A B C D A B *B* D  (duplicate but still in alphabet)
 *
 * Brain should detect true anomalies without false-alarming on noise.
 *
 * Compile: gcc -O3 -march=native -o bitbrain8 bitbrain_v8_stream.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)
#define WINDOW_SIZE 4
#define MAX_MEMORY 500
#define ALPHABET 16

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

/* Symbol vectors and position vectors */
static HDV V_symbol[ALPHABET];
static HDV V_position[WINDOW_SIZE];

/* Encode a window [s0, s1, ..., sK-1] as HDV.
 * XOR-binding: sensitive to ANY change in any position.
 * For two windows differing in 1 symbol: similarity ~0.5 (quasi-orthogonal).
 * For identical windows: similarity = 1.0.
 */
static HDV encode_window(const int *symbols){
    /* Sum of (position XOR symbol) HDVs via BUNDLE, then add TAG */
    int counters[HDV_BITS] = {0};
    for(int i = 0; i < WINDOW_SIZE; i++){
        HDV pv = hdv_bind(V_symbol[symbols[i]], V_position[i]);
        for(int k = 0; k < HDV_BITS; k++){
            counters[k] += ((pv.b[k>>6] >> (k&63)) & 1) ? 1 : -1;
        }
    }
    HDV r = hdv_zero();
    for(int k = 0; k < HDV_BITS; k++){
        if(counters[k] > 0) r.b[k>>6] |= (1ULL << (k&63));
    }
    /* ALSO XOR-bind all together for sensitivity */
    HDV xor_part = hdv_zero();
    for(int i = 0; i < WINDOW_SIZE; i++){
        HDV pv = hdv_bind(V_symbol[symbols[i]], V_position[i]);
        xor_part = hdv_bind(xor_part, pv);
    }
    /* Combine bundle and xor for balance */
    return hdv_bind(r, xor_part);
}

/* ═══ TEMPORAL BUFFER ═══
 * Sliding window. New event: shift old ones, append new.
 * Event-driven: only processed when new event arrives.
 */
typedef struct {
    int window[WINDOW_SIZE];
    int filled;       /* how many slots filled */
    int total_events; /* total events seen */
    int last_event_time;
} TemporalBuffer;

static void tb_init(TemporalBuffer *tb){
    memset(tb, 0, sizeof(*tb));
}

static int tb_push(TemporalBuffer *tb, int symbol, int time){
    /* Shift window */
    for(int i = 0; i < WINDOW_SIZE - 1; i++) tb->window[i] = tb->window[i+1];
    tb->window[WINDOW_SIZE - 1] = symbol;
    if(tb->filled < WINDOW_SIZE) tb->filled++;
    tb->total_events++;
    tb->last_event_time = time;
    return tb->filled == WINDOW_SIZE; /* ready to process */
}

/* ═══ PATTERN MEMORY ═══
 * Stores HDV encodings of observed "normal" windows.
 */
typedef struct {
    HDV windows[MAX_MEMORY];
    int hit_count[MAX_MEMORY];
    int n;
} PatternMemory;

static void pm_init(PatternMemory *pm){ pm->n = 0; }

/* Store window, dedupe by similarity */
static void pm_store(PatternMemory *pm, HDV w){
    /* Check for near-duplicate */
    for(int i = 0; i < pm->n; i++){
        if(hdv_sim(w, pm->windows[i]) > 0.99){
            pm->hit_count[i]++;
            return;
        }
    }
    if(pm->n >= MAX_MEMORY){
        /* Evict least-used */
        int min_idx = 0;
        for(int i = 1; i < pm->n; i++){
            if(pm->hit_count[i] < pm->hit_count[min_idx]) min_idx = i;
        }
        pm->windows[min_idx] = w;
        pm->hit_count[min_idx] = 1;
        return;
    }
    pm->windows[pm->n] = w;
    pm->hit_count[pm->n] = 1;
    pm->n++;
}

/* Return similarity to closest stored pattern */
static double pm_familiarity(PatternMemory *pm, HDV w){
    double best = 0;
    for(int i = 0; i < pm->n; i++){
        double s = hdv_sim(w, pm->windows[i]);
        if(s > best) best = s;
    }
    return best;
}

/* ═══ ANOMALY DETECTOR ═══
 * Threshold-based: if familiarity < threshold → anomaly
 */
typedef struct {
    double threshold;
    int n_flagged;
    int n_normal;
    double total_fam_normal;
    double total_fam_flagged;
} AnomalyDetector;

static void ad_init(AnomalyDetector *a, double threshold){
    memset(a, 0, sizeof(*a));
    a->threshold = threshold;
}

static int ad_check(AnomalyDetector *a, double familiarity){
    if(familiarity < a->threshold){
        a->n_flagged++;
        a->total_fam_flagged += familiarity;
        return 1;
    }
    a->n_normal++;
    a->total_fam_normal += familiarity;
    return 0;
}

/* ═══ STREAM BRAIN v8 ═══ */
typedef struct {
    TemporalBuffer buffer;
    PatternMemory memory;
    AnomalyDetector detector;
    int learning_mode; /* 1 = train, 0 = test */
} StreamBrain;

static void sb_init(StreamBrain *sb){
    tb_init(&sb->buffer);
    pm_init(&sb->memory);
    ad_init(&sb->detector, 0.95);  /* high threshold for sensitivity */
    sb->learning_mode = 1;
}

/* Process one event. Returns 1 if anomaly detected. */
static int sb_event(StreamBrain *sb, int symbol, int time){
    int ready = tb_push(&sb->buffer, symbol, time);
    if(!ready) return 0; /* window not full yet */

    HDV w = encode_window(sb->buffer.window);

    if(sb->learning_mode){
        /* Training: store as normal */
        pm_store(&sb->memory, w);
        return 0;
    }

    /* Testing: check familiarity */
    double fam = pm_familiarity(&sb->memory, w);
    return ad_check(&sb->detector, fam);
}

/* ═══ TESTS ═══ */

/* Generate normal stream: repeating pattern with occasional noise */
static void gen_normal_stream(int *stream, int n, int *pattern, int p_len){
    for(int i = 0; i < n; i++){
        stream[i] = pattern[i % p_len];
    }
}

/* Insert anomalies at specific positions */
static void insert_anomalies(int *stream, int n, int *anomaly_positions,
                              int n_anomalies, int *anomaly_values){
    for(int i = 0; i < n_anomalies; i++){
        int pos = anomaly_positions[i];
        if(pos < n) stream[pos] = anomaly_values[i];
    }
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v8: STREAM processing (temporal)\n");
    printf("══════════════════════════════════════════\n\n");

    rng_seed(42);

    /* Initialize HDV prototypes */
    for(int i = 0; i < ALPHABET; i++) V_symbol[i] = hdv_random();
    for(int i = 0; i < WINDOW_SIZE; i++) V_position[i] = hdv_random();

    StreamBrain brain;
    sb_init(&brain);

    /* ═══ TEST 1: Simple repeating pattern ═══ */
    printf("TEST 1: Simple pattern ABCDABCDABCD...\n");
    printf("────────────────────────────────────────\n");

    int pattern1[] = {0, 1, 2, 3}; /* A, B, C, D */
    int p_len = 4;

    /* Training: 100 clean pattern events */
    printf("Training on 100 clean events...\n");
    int stream[500];
    gen_normal_stream(stream, 100, pattern1, p_len);
    for(int i = 0; i < 100; i++){
        sb_event(&brain, stream[i], i);
    }
    printf("  Memory stored: %d unique windows\n", brain.memory.n);

    /* Switch to testing */
    brain.learning_mode = 0;

    /* Continue clean for 20 events (should be familiar) */
    printf("\nTesting on 20 clean events (should be 0 anomalies)...\n");
    gen_normal_stream(stream, 20, pattern1, p_len);
    int clean_anomalies = 0;
    for(int i = 0; i < 20; i++){
        if(sb_event(&brain, stream[i], 100+i)) clean_anomalies++;
    }
    printf("  Clean false positives: %d/20\n", clean_anomalies);

    /* Now inject true anomalies */
    printf("\nTesting with injected anomalies...\n");
    int test_stream[100];
    gen_normal_stream(test_stream, 100, pattern1, p_len);
    /* Insert unknown symbols at positions 15, 35, 60 */
    int anom_pos[] = {15, 35, 60};
    int anom_val[] = {9, 12, 15}; /* symbols not in normal pattern */
    insert_anomalies(test_stream, 100, anom_pos, 3, anom_val);

    brain.detector.n_flagged = 0;
    brain.detector.n_normal = 0;

    int detected_positions[100] = {0};
    for(int i = 0; i < 100; i++){
        int flagged = sb_event(&brain, test_stream[i], 200+i);
        if(flagged) detected_positions[i] = 1;
    }

    printf("  Total flagged: %d\n", brain.detector.n_flagged);
    printf("  Flagged positions: ");
    int tp = 0, fp = 0;
    for(int i = 0; i < 100; i++){
        if(detected_positions[i]){
            /* Is this near an injected anomaly? (within window size) */
            int near_anomaly = 0;
            for(int a = 0; a < 3; a++){
                if(i >= anom_pos[a] && i < anom_pos[a] + WINDOW_SIZE){
                    near_anomaly = 1; break;
                }
            }
            printf("%d ", i);
            if(near_anomaly) tp++;
            else fp++;
        }
    }
    printf("\n");
    printf("  True positives (near injected): %d\n", tp);
    printf("  False positives:                %d\n", fp);
    printf("  Expected: each anomaly flagged for ~%d positions (window)\n", WINDOW_SIZE);

    /* ═══ TEST 2: More complex pattern with subtle anomaly ═══ */
    printf("\n\nTEST 2: Complex pattern, subtle anomaly\n");
    printf("────────────────────────────────────────\n");

    sb_init(&brain);
    brain.learning_mode = 1;

    /* Longer pattern: 8 symbols */
    int pattern2[] = {0, 1, 2, 3, 4, 5, 6, 7};
    int p2_len = 8;

    /* Train on 200 events */
    gen_normal_stream(stream, 200, pattern2, p2_len);
    for(int i = 0; i < 200; i++) sb_event(&brain, stream[i], i);
    printf("Trained on 200 events. Memory: %d windows\n", brain.memory.n);

    brain.learning_mode = 0;
    brain.detector.n_flagged = 0;

    /* Test with REORDERED pattern (same symbols, different order) */
    printf("\nInjecting: reorder symbols at position 50 (same alphabet!)\n");
    int test2[100];
    gen_normal_stream(test2, 100, pattern2, p2_len);
    /* Reorder: swap positions 50 and 52 */
    int tmp = test2[50]; test2[50] = test2[52]; test2[52] = tmp;

    int detected2[100] = {0};
    for(int i = 0; i < 100; i++){
        if(sb_event(&brain, test2[i], i)) detected2[i] = 1;
    }

    printf("Flagged positions around 50: ");
    int found = 0;
    for(int i = 45; i <= 60; i++){
        if(detected2[i]){
            printf("%d ", i);
            found++;
        }
    }
    printf("\n");
    printf("Detected the reorder: %s\n", found > 0 ? "✓ YES" : "✗ NO");

    /* ═══ TEST 3: Multiple patterns ═══ */
    printf("\n\nTEST 3: Learn multiple normal patterns\n");
    printf("────────────────────────────────────────\n");

    sb_init(&brain);
    brain.learning_mode = 1;

    /* Two normal patterns */
    int pA[] = {0, 1, 2, 3};
    int pB[] = {5, 6, 7, 8};

    /* Train: alternate between the two */
    for(int i = 0; i < 200; i++){
        int *p = (i/16 % 2 == 0) ? pA : pB;
        sb_event(&brain, p[i % 4], i);
    }
    printf("Trained on 2 alternating patterns. Memory: %d\n", brain.memory.n);

    brain.learning_mode = 0;
    brain.detector.n_flagged = 0;
    brain.detector.n_normal = 0;

    /* Test: present both patterns (should be normal) + wrong (anomaly) */
    int test3[60];
    for(int i = 0; i < 20; i++) test3[i] = pA[i % 4];
    for(int i = 20; i < 40; i++) test3[i] = pB[i % 4];
    /* Anomaly: mix patterns */
    for(int i = 40; i < 60; i++){
        test3[i] = (i % 2 == 0) ? pA[i % 4] : pB[i % 4];
    }

    for(int i = 0; i < 60; i++) sb_event(&brain, test3[i], i);
    printf("Testing: 20 clean A + 20 clean B + 20 mixed (anomalous)\n");
    printf("  Normal detected (first 40): %d (of 36 ready events)\n",
           brain.detector.n_normal - brain.detector.n_flagged);
    printf("  Flagged: %d\n", brain.detector.n_flagged);

    /* ═══ SUMMARY ═══ */
    printf("\n═══ SUMMARY ═══\n");
    printf("v8 adds TEMPORAL dimension to BitBrain:\n");
    printf("  Event-driven processing (no clock)\n");
    printf("  Sliding window context\n");
    printf("  HDC-based pattern memory\n");
    printf("  Familiarity-based anomaly detection\n");
    printf("\nAll bit operations. ~%zu KB per brain.\n", sizeof(StreamBrain)/1024);

    return 0;
}
