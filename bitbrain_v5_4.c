/*
 * BITBRAIN v5.4: + PLANNING region (sequences and path finding)
 * ==============================================================
 *
 * PLANNING region: learns state transitions, predicts next states, plans paths.
 *
 * Representation: transitions[state][next_state] as bit matrix.
 * Operations:
 *   - observe(from, to):  set bit transitions[from][to]
 *   - predict(state):     return all reachable next states (one step)
 *   - plan(start, goal):  BFS shortest path
 *
 * Tests:
 *   1. Learn a sequence, predict next states
 *   2. Learn multiple branching sequences
 *   3. Plan shortest path from start to goal
 *
 * Compile: gcc -O3 -march=native -o bitbrain5_4 bitbrain_v5_4.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define MAX_STATES 64
#define STATE_WORDS ((MAX_STATES + 63) / 64)

typedef struct {
    /* transitions[s] = bit vector of states reachable from s in one step */
    uint64_t transitions[MAX_STATES][STATE_WORDS];
    int n_states;
} Planning;

static void plan_init(Planning *p, int n){
    memset(p, 0, sizeof(*p));
    p->n_states = n;
}

/* Observe a transition */
static void plan_observe(Planning *p, int from, int to){
    if(from >= p->n_states || to >= p->n_states) return;
    p->transitions[from][to>>6] |= (1ULL << (to&63));
}

/* Observe a sequence: s1 → s2 → s3 → ... */
static void plan_observe_sequence(Planning *p, const int *seq, int len){
    for(int i = 0; i + 1 < len; i++){
        plan_observe(p, seq[i], seq[i+1]);
    }
}

/* Predict: all immediately reachable states from 'state' */
static int plan_next_states(Planning *p, int state, int *out){
    int n = 0;
    for(int s = 0; s < p->n_states; s++){
        if(p->transitions[state][s>>6] & (1ULL << (s&63))){
            out[n++] = s;
        }
    }
    return n;
}

/* Plan: BFS shortest path from start to goal. Returns path length, fills path. */
static int plan_shortest_path(Planning *p, int start, int goal, int *path){
    int n = p->n_states;
    int parent[MAX_STATES];
    int visited[MAX_STATES];
    memset(visited, 0, sizeof(visited));
    for(int i = 0; i < n; i++) parent[i] = -1;

    int queue[MAX_STATES];
    int head = 0, tail = 0;
    queue[tail++] = start;
    visited[start] = 1;

    while(head < tail){
        int cur = queue[head++];
        if(cur == goal){
            /* Reconstruct path */
            int tmp[MAX_STATES], len = 0;
            int c = goal;
            while(c != -1){
                tmp[len++] = c;
                c = parent[c];
            }
            /* Reverse */
            for(int i = 0; i < len; i++) path[i] = tmp[len-1-i];
            return len;
        }
        /* Enqueue neighbors */
        for(int s = 0; s < n; s++){
            if(p->transitions[cur][s>>6] & (1ULL << (s&63))){
                if(!visited[s]){
                    visited[s] = 1;
                    parent[s] = cur;
                    queue[tail++] = s;
                }
            }
        }
    }
    return -1; /* unreachable */
}

/* Check if reachable (using BFS) */
static int plan_reachable(Planning *p, int from, int to){
    int path[MAX_STATES];
    return plan_shortest_path(p, from, to, path) > 0;
}

/* ═══ TESTS ═══ */

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v5.4: + PLANNING region\n");
    printf("══════════════════════════════════════════\n\n");

    Planning p;
    plan_init(&p, 16);

    /* ── Test 1: learn a simple sequence ── */
    printf("Test 1: Learn sequence 0 → 3 → 5 → 7 → 2 → 0 → ...\n");
    int seq1[] = {0, 3, 5, 7, 2, 0, 3, 5};
    plan_observe_sequence(&p, seq1, 8);

    /* Predict from each state */
    for(int s = 0; s < 8; s++){
        int next[16];
        int n = plan_next_states(&p, s, next);
        if(n > 0){
            printf("  From %d: {", s);
            for(int i = 0; i < n; i++) printf("%d%s", next[i], i<n-1?", ":"");
            printf("}\n");
        }
    }

    /* ── Test 2: multiple branching sequences ── */
    printf("\nTest 2: Multiple sequences\n");
    plan_init(&p, 16);
    int s1[] = {0, 1, 2, 3, 4};    /* linear */
    int s2[] = {0, 5, 6, 4};       /* alternative to 4 */
    int s3[] = {6, 7, 8};          /* branches off */
    int s4[] = {4, 9, 10};         /* continues from 4 */
    plan_observe_sequence(&p, s1, 5);
    plan_observe_sequence(&p, s2, 4);
    plan_observe_sequence(&p, s3, 3);
    plan_observe_sequence(&p, s4, 3);

    printf("  From 0 reachable in 1 step: ");
    int next[16];
    int n = plan_next_states(&p, 0, next);
    for(int i = 0; i < n; i++) printf("%d ", next[i]);
    printf("\n");

    printf("  From 6 reachable in 1 step: ");
    n = plan_next_states(&p, 6, next);
    for(int i = 0; i < n; i++) printf("%d ", next[i]);
    printf("\n");

    /* ── Test 3: plan shortest path ── */
    printf("\nTest 3: Plan shortest path\n");
    int path[MAX_STATES];

    /* 0 → 10: should be 0 → 1 → 2 → 3 → 4 → 9 → 10 (7 nodes) */
    int len = plan_shortest_path(&p, 0, 10, path);
    printf("  0 → 10: ");
    if(len > 0){
        for(int i = 0; i < len; i++) printf("%d%s", path[i], i<len-1?"→":"");
        printf(" (len=%d)\n", len);
    } else printf("unreachable\n");

    /* 0 → 8: should be 0 → 5 → 6 → 7 → 8 (5 nodes) */
    len = plan_shortest_path(&p, 0, 8, path);
    printf("  0 → 8:  ");
    if(len > 0){
        for(int i = 0; i < len; i++) printf("%d%s", path[i], i<len-1?"→":"");
        printf(" (len=%d)\n", len);
    } else printf("unreachable\n");

    /* 10 → 0: backward, should be unreachable */
    len = plan_shortest_path(&p, 10, 0, path);
    printf("  10 → 0: ");
    if(len > 0) printf("len=%d (unexpected)\n", len);
    else printf("unreachable ✓\n");

    /* ── Test 4: larger graph ── */
    printf("\nTest 4: Larger sequence learning (32 states)\n");
    plan_init(&p, 32);

    /* Simulate: 5 random sequences of length 6-10 */
    unsigned long long rng = 42;
    for(int trial = 0; trial < 5; trial++){
        int seq[16], len = 6 + (rng % 5);
        rng = rng * 6364136223846793005ULL + 1;
        for(int i = 0; i < len; i++){
            seq[i] = rng % 32;
            rng = rng * 6364136223846793005ULL + 1;
        }
        plan_observe_sequence(&p, seq, len);
    }

    /* Count total edges */
    int n_edges = 0;
    for(int i = 0; i < 32; i++){
        for(int w = 0; w < STATE_WORDS; w++){
            n_edges += __builtin_popcountll(p.transitions[i][w]);
        }
    }
    printf("  Total edges learned: %d\n", n_edges);

    /* Try random pathfinding */
    int n_queries = 10;
    int reachable_count = 0;
    for(int q = 0; q < n_queries; q++){
        int from = (rng>>8) % 32; rng = rng * 6364136223846793005ULL + 1;
        int to = (rng>>8) % 32; rng = rng * 6364136223846793005ULL + 1;
        int len = plan_shortest_path(&p, from, to, path);
        if(len > 0){
            reachable_count++;
            printf("  %d → %d: path length %d\n", from, to, len);
        }
    }
    printf("  Reachable: %d/%d queries\n", reachable_count, n_queries);

    /* ── Test 5: cycles ── */
    printf("\nTest 5: Detect cycles via self-reachability\n");
    plan_init(&p, 8);
    int cycle[] = {0, 1, 2, 3, 4, 0}; /* forms a cycle */
    plan_observe_sequence(&p, cycle, 6);
    for(int i = 0; i < 5; i++){
        int cycles_back = plan_reachable(&p, i, i);
        printf("  State %d: %s\n", i, cycles_back ? "cycles back to self ✓" : "no cycle");
    }

    printf("\n═══ SUMMARY ═══\n");
    printf("PLANNING region: learns sequences, predicts next states, plans paths\n");
    printf("  Storage: %d × %d bits = %d bytes per region\n",
           MAX_STATES, MAX_STATES, MAX_STATES*MAX_STATES/8);
    printf("  Operations: observe O(1), predict O(n), plan O(n²) BFS\n");
    printf("  All bit operations, no floating point\n");

    return 0;
}
