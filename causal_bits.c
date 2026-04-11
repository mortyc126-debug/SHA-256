/*
 * CAUSAL BITS: directed acyclic causal relations as primitive
 * ==============================================================
 *
 * Thirteenth axis in the bit taxonomy. Each causal bit is a
 * directed edge i → j meaning "i precedes / causes j".  A system
 * of causal bits is a DIRECTED ACYCLIC GRAPH, with acyclicity
 * enforced BY THE TYPE, not merely checked.
 *
 * Inspired by:
 *   - Directed acyclic graphs and partial orders
 *   - Lamport happens-before relation (1978)
 *   - Pearl causal calculus and the do-operator (2000)
 *   - Event structures (Winskel 1989)
 *   - Topological sort as a fundamental algorithm
 *
 * Distinction from the eleven earlier axes:
 *
 *   - RELATIONAL bits permit any relation. Causal bits require
 *     strict partial order (no cycles). Topological sort, do-
 *     calculus, and ancestor relations are not available for
 *     general relations.
 *   - MODAL bits have an accessibility relation, which can be
 *     reflexive, symmetric, or cyclic. Causal is strictly
 *     anti-symmetric and acyclic.
 *   - STREAM bits have a GLOBAL time axis; every bit has a
 *     definite moment. Causal bits have a PARTIAL order;
 *     two events can be incomparable.
 *   - None of binary, phase, probability, reversible, linear,
 *     self-ref, higher-order, cost has a primitive notion of
 *     directed precedence.
 *
 * Experiments:
 *
 *   1. Build a DAG incrementally; acyclicity check rejects
 *      edges that would close a loop.
 *   2. Transitive closure gives the ancestor relation.
 *   3. Topological sort produces a consistent linearisation.
 *   4. Pearl's do-calculus: intervene on a node, descendants
 *      respond but ancestors do not.
 *   5. Witness of non-reducibility: a cyclic relation has no
 *      topological sort; causal bits structurally forbid it.
 *
 * Compile: gcc -O3 -march=native -o causal causal_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define MAX_N 16

/* ═══ DAG representation ═══ */
typedef struct {
    int n;
    int e[MAX_N][MAX_N];   /* e[i][j] = 1 iff i → j directly */
} Dag;

static void dag_init(Dag *g, int n){
    g->n = n;
    memset(g->e, 0, sizeof(g->e));
}

/* Check reachability i →* j via BFS */
static int reachable(const Dag *g, int i, int j){
    int visited[MAX_N] = {0};
    int queue[MAX_N];
    int head = 0, tail = 0;
    queue[tail++] = i;
    visited[i] = 1;
    while(head < tail){
        int u = queue[head++];
        if(u == j) return 1;
        for(int v = 0; v < g->n; v++){
            if(g->e[u][v] && !visited[v]){
                visited[v] = 1;
                queue[tail++] = v;
            }
        }
    }
    return visited[j];
}

/* Add edge i → j. Returns 1 on success, 0 if creating cycle.
 * The acyclicity check asks: is j already able to reach i?
 * If so, adding i → j closes a cycle. */
static int dag_add_edge(Dag *g, int i, int j){
    if(i == j) return 0;          /* self-loop */
    if(g->e[i][j]) return 1;      /* already present */
    if(reachable(g, j, i)) return 0;  /* would cycle */
    g->e[i][j] = 1;
    return 1;
}

/* Transitive closure → ancestor relation. */
static void transitive_closure(Dag *out, const Dag *g){
    dag_init(out, g->n);
    /* Start with direct edges */
    for(int i = 0; i < g->n; i++)
        for(int j = 0; j < g->n; j++)
            out->e[i][j] = g->e[i][j];
    /* Warshall */
    for(int k = 0; k < g->n; k++)
        for(int i = 0; i < g->n; i++)
            for(int j = 0; j < g->n; j++)
                if(out->e[i][k] && out->e[k][j]) out->e[i][j] = 1;
}

/* Topological sort via Kahn's algorithm. Returns order length. */
static int topo_sort(const Dag *g, int *order){
    int indeg[MAX_N] = {0};
    for(int i = 0; i < g->n; i++)
        for(int j = 0; j < g->n; j++)
            if(g->e[i][j]) indeg[j]++;

    int queue[MAX_N];
    int head = 0, tail = 0;
    for(int i = 0; i < g->n; i++) if(indeg[i] == 0) queue[tail++] = i;

    int nout = 0;
    while(head < tail){
        int u = queue[head++];
        order[nout++] = u;
        for(int v = 0; v < g->n; v++){
            if(g->e[u][v]){
                indeg[v]--;
                if(indeg[v] == 0) queue[tail++] = v;
            }
        }
    }
    return nout;   /* should equal g->n for a valid DAG */
}

/* Pearl intervention do(x): delete all incoming edges to x. */
static void intervene(Dag *out, const Dag *g, int x){
    *out = *g;
    for(int i = 0; i < g->n; i++) out->e[i][x] = 0;
}

static void dag_print(const char *name, const Dag *g, const char **labels){
    printf("  %s edges:\n", name);
    int any = 0;
    for(int i = 0; i < g->n; i++){
        for(int j = 0; j < g->n; j++){
            if(g->e[i][j]){
                if(labels) printf("    %s → %s\n", labels[i], labels[j]);
                else       printf("    %d → %d\n", i, j);
                any = 1;
            }
        }
    }
    if(!any) printf("    (empty)\n");
}

/* ═══ EXPERIMENT 1: Incremental DAG construction ═══ */
static void experiment_build_dag(void){
    printf("\n═══ EXPERIMENT 1: Acyclicity enforcement ═══\n\n");

    Dag g; dag_init(&g, 5);

    printf("  Adding edges incrementally:\n");
    printf("    add 0→1: %s\n", dag_add_edge(&g, 0, 1) ? "OK" : "REJECTED");
    printf("    add 1→2: %s\n", dag_add_edge(&g, 1, 2) ? "OK" : "REJECTED");
    printf("    add 2→3: %s\n", dag_add_edge(&g, 2, 3) ? "OK" : "REJECTED");
    printf("    add 0→3: %s\n", dag_add_edge(&g, 0, 3) ? "OK" : "REJECTED");
    printf("    add 3→0: %s  ← would close cycle 0→1→2→3→0\n",
           dag_add_edge(&g, 3, 0) ? "OK" : "REJECTED");
    printf("    add 3→1: %s  ← would close cycle 1→2→3→1\n",
           dag_add_edge(&g, 3, 1) ? "OK" : "REJECTED");
    printf("    add 3→4: %s\n", dag_add_edge(&g, 3, 4) ? "OK" : "REJECTED");

    printf("\n  Final DAG:\n");
    dag_print("", &g, NULL);

    printf("\n  The primitive does not merely allow acyclic graphs;\n");
    printf("  it REFUSES to construct cycles. Acyclicity is part of\n");
    printf("  the type system, not an afterthought.\n");
}

/* ═══ EXPERIMENT 2: Transitive closure as ancestor relation ═══ */
static void experiment_closure(void){
    printf("\n═══ EXPERIMENT 2: Ancestor relation via transitive closure ═══\n\n");

    Dag g; dag_init(&g, 6);
    dag_add_edge(&g, 0, 1);
    dag_add_edge(&g, 0, 2);
    dag_add_edge(&g, 1, 3);
    dag_add_edge(&g, 2, 3);
    dag_add_edge(&g, 3, 4);
    dag_add_edge(&g, 4, 5);

    dag_print("Direct edges", &g, NULL);

    Dag tc;
    transitive_closure(&tc, &g);
    printf("\n");
    dag_print("Transitive closure (ancestor relation)", &tc, NULL);

    printf("\n  5 is reachable from 0 via 0→1→3→4→5 or 0→2→3→4→5.\n");
    printf("  The closure says: 0 is an ancestor of everything.\n");
}

/* ═══ EXPERIMENT 3: Topological sort ═══ */
static void experiment_toposort(void){
    printf("\n═══ EXPERIMENT 3: Topological sort ═══\n\n");

    Dag g; dag_init(&g, 6);
    dag_add_edge(&g, 0, 1);
    dag_add_edge(&g, 0, 2);
    dag_add_edge(&g, 1, 3);
    dag_add_edge(&g, 2, 3);
    dag_add_edge(&g, 3, 4);
    dag_add_edge(&g, 4, 5);

    int order[MAX_N];
    int nout = topo_sort(&g, order);

    printf("  DAG with 6 nodes, edges above.\n");
    printf("  Topological order: ");
    for(int i = 0; i < nout; i++){
        printf("%d", order[i]);
        if(i < nout - 1) printf(" → ");
    }
    printf("\n");
    printf("  Length: %d (equals n = %d, meaning DAG is valid)\n", nout, g.n);

    /* Verify all edges respect the order */
    int pos[MAX_N];
    for(int i = 0; i < nout; i++) pos[order[i]] = i;
    int violations = 0;
    for(int i = 0; i < g.n; i++)
        for(int j = 0; j < g.n; j++)
            if(g.e[i][j] && pos[i] >= pos[j]) violations++;
    printf("  Edge-order violations: %d (expected 0)\n", violations);

    printf("\n  Every edge i→j has pos(i) < pos(j): the linear order\n");
    printf("  is consistent with the partial order. A cyclic relation\n");
    printf("  cannot produce such a linearisation.\n");
}

/* ═══ EXPERIMENT 4: Pearl's do-calculus ═══ */
static void experiment_pearl(void){
    printf("\n═══ EXPERIMENT 4: Pearl intervention do(X) ═══\n\n");

    /* Classic Pearl example:
     *   rain → wet_grass → slippery
     *   sprinkler → wet_grass
     * Indices: 0=rain, 1=sprinkler, 2=wet_grass, 3=slippery */

    const char *labels[] = {"rain", "sprinkler", "wet_grass", "slippery"};
    Dag g; dag_init(&g, 4);
    dag_add_edge(&g, 0, 2);
    dag_add_edge(&g, 1, 2);
    dag_add_edge(&g, 2, 3);

    dag_print("Original causal model", &g, labels);

    /* Intervene: do(wet_grass) — force wet_grass, cut its incoming edges */
    Dag intervened;
    intervene(&intervened, &g, 2);
    printf("\n");
    dag_print("After do(wet_grass): incoming edges to wet_grass removed", &intervened, labels);

    printf("\n  Observational reasoning (seeing wet grass):\n");
    printf("    wet grass is evidence → rain or sprinkler was likely\n");
    printf("    slippery → wet grass → rain\n");
    printf("\n  Interventional reasoning (setting wet grass = true):\n");
    printf("    does NOT tell us about rain or sprinkler\n");
    printf("    DOES tell us slippery is now likely\n");
    printf("\n  do-operator structurally distinguishes OBSERVATION\n");
    printf("  from INTERVENTION. This is the core of Pearl's causal\n");
    printf("  hierarchy and is absent from any non-causal primitive.\n");

    /* Verify: after intervention, rain is no longer an ancestor of wet_grass */
    Dag tc;
    transitive_closure(&tc, &intervened);
    printf("\n  After do(wet_grass):\n");
    printf("    rain is ancestor of wet_grass?   %s\n",
           tc.e[0][2] ? "yes" : "NO (correct)");
    printf("    wet_grass is ancestor of slippery? %s\n",
           tc.e[2][3] ? "YES (correct)" : "no");
}

/* ═══ EXPERIMENT 5: Non-reducibility to relational bits ═══ */
static void experiment_independence(void){
    printf("\n═══ EXPERIMENT 5: Causal bits not reducible to relational ═══\n\n");

    /* Try to build a "relation" with a cycle and topologically sort it. */
    printf("  Relational bits allow any graph including cycles.\n");
    printf("  Attempt to topologically sort a cyclic relation:\n\n");

    /* Manually build edges into a Dag structure, bypassing the
     * acyclic guard, to simulate what a pure relational bit would
     * offer. */
    Dag cyclic;
    dag_init(&cyclic, 3);
    cyclic.e[0][1] = 1;
    cyclic.e[1][2] = 1;
    cyclic.e[2][0] = 1;    /* cycle! */

    printf("  Bypass-added edges: 0→1, 1→2, 2→0 (cycle)\n");
    int order[MAX_N];
    int nout = topo_sort(&cyclic, order);
    printf("  Topo-sort result length: %d (expected 3, got partial)\n", nout);
    printf("  %s\n\n", nout == 3 ? "complete" : "INCOMPLETE — sort failed on cyclic input");

    /* Now show that the causal-bit API refuses to create the cycle
     * in the first place */
    printf("  Causal bit API:\n");
    Dag caus;
    dag_init(&caus, 3);
    printf("    add 0→1: %s\n", dag_add_edge(&caus, 0, 1) ? "OK" : "rejected");
    printf("    add 1→2: %s\n", dag_add_edge(&caus, 1, 2) ? "OK" : "rejected");
    printf("    add 2→0: %s  ← acyclicity refuses\n",
           dag_add_edge(&caus, 2, 0) ? "OK" : "REJECTED");

    printf("\n  Relational bits can HOLD a cycle but cannot DO anything\n");
    printf("  useful with it (topological sort, causal intervention,\n");
    printf("  ancestor queries all break). Causal bits never admit the\n");
    printf("  cycle in the first place, so those operations are\n");
    printf("  always well-defined. The primitive is strictly stronger\n");
    printf("  in terms of guaranteed invariants.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("CAUSAL BITS: DAG-constrained directed relations\n");
    printf("══════════════════════════════════════════\n");
    printf("Each causal bit is a directed edge i → j with\n");
    printf("acyclicity enforced by the primitive.\n");

    experiment_build_dag();
    experiment_closure();
    experiment_toposort();
    experiment_pearl();
    experiment_independence();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. DAG constraint is part of the TYPE, not a post-check\n");
    printf("  2. Transitive closure gives ancestor relation\n");
    printf("  3. Topological sort linearises the partial order\n");
    printf("  4. Pearl's do-operator is a primitive operation that\n");
    printf("     structurally distinguishes intervention from\n");
    printf("     observation\n");
    printf("  5. Not reducible to relational: relational can hold\n");
    printf("     cycles but cannot support do-calculus or topo-sort\n");
    printf("\n  THIRTEENTH axis: CAUSALITY / DIRECTED ACYCLIC ORDER.\n");
    printf("  Sits in the RELATION meta-group alongside modal and\n");
    printf("  braid, but strictly stronger than relational because\n");
    printf("  the acyclicity constraint enables a new class of\n");
    printf("  operations (topological sort, Pearl intervention).\n");
    return 0;
}
