/*
 * CAUSAL × COST: weighted causal DAGs
 * ======================================
 *
 * Third combination primitive in the programme, after
 * thermo_reversible (reversible × cost) and modal_quotient
 * (modal × quotient).
 *
 * The intersection of the CAUSAL axis (directed acyclic
 * structure with Pearl's do-operator) and the COST axis
 * (numerical weights on operations) gives a new primitive:
 * a weighted causal DAG, where every directed edge i → j
 * carries a numerical strength / cost.
 *
 * This corresponds directly to established practice in
 * probabilistic graphical models and path analysis (Wright
 * 1921, Pearl 2000): edges have regression coefficients,
 * causal influence decomposes additively along paths.
 *
 * Distinction from either axis alone:
 *
 *   - PURE CAUSAL has structure (acyclicity, topological
 *     sort, do-calculus) but no quantitative metric. You
 *     can say 'X is an ancestor of Y' but not 'by how much'.
 *   - PURE COST has weights and Ising-style energy but no
 *     directed acyclic structure. Frustration and ground
 *     states do not distinguish causes from effects.
 *   - COMBINED gives both: Pearl-style causal reasoning
 *     plus Wright-style path decomposition. Neither axis
 *     alone supports the characteristic operation here —
 *     computing the TOTAL CAUSAL INFLUENCE as a weighted
 *     sum along directed paths.
 *
 * Experiments:
 *
 *   1. Build a weighted DAG, compute shortest (lowest-cost)
 *      directed path between two nodes.
 *   2. Total causal influence = sum over all directed paths
 *      of the product of edge weights along each path.
 *   3. Intervention cost: how much total weight is "removed"
 *      by the do-operator (all incoming edges to node x).
 *   4. Path decomposition: distinguish direct vs indirect
 *      causal effect of X on Y.
 *   5. Witness of irreducibility: pure causal has no metric,
 *      pure cost has no direction.
 *
 * Compile: gcc -O3 -march=native -o ccost causal_cost.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define MAX_N 16
#define INF 1e18

/* ═══ WEIGHTED DAG ═══ */
typedef struct {
    int n;
    double w[MAX_N][MAX_N];   /* w[i][j] = edge weight, 0 if no edge */
} Wdag;

static void wdag_init(Wdag *g, int n){
    g->n = n;
    for(int i = 0; i < n; i++) for(int j = 0; j < n; j++) g->w[i][j] = 0;
}

/* Check reachability via BFS */
static int reachable(const Wdag *g, int i, int j){
    int visited[MAX_N] = {0};
    int queue[MAX_N];
    int head = 0, tail = 0;
    queue[tail++] = i;
    visited[i] = 1;
    while(head < tail){
        int u = queue[head++];
        if(u == j) return 1;
        for(int v = 0; v < g->n; v++){
            if(g->w[u][v] > 0 && !visited[v]){
                visited[v] = 1;
                queue[tail++] = v;
            }
        }
    }
    return visited[j];
}

/* Add edge with weight; fail if it would create a cycle. */
static int wdag_add(Wdag *g, int i, int j, double weight){
    if(i == j || weight <= 0) return 0;
    if(reachable(g, j, i)) return 0;
    g->w[i][j] = weight;
    return 1;
}

static void wdag_print(const char *name, const Wdag *g){
    printf("  %s edges:\n", name);
    for(int i = 0; i < g->n; i++)
        for(int j = 0; j < g->n; j++)
            if(g->w[i][j] > 0) printf("    %d → %d  (w = %.2f)\n", i, j, g->w[i][j]);
}

/* ═══ SHORTEST PATH via relaxation (topological order) ═══ */
static double shortest_path_cost(const Wdag *g, int source, int target){
    double dist[MAX_N];
    for(int i = 0; i < g->n; i++) dist[i] = INF;
    dist[source] = 0;

    /* Compute topological order via Kahn */
    int indeg[MAX_N] = {0};
    for(int i = 0; i < g->n; i++)
        for(int j = 0; j < g->n; j++)
            if(g->w[i][j] > 0) indeg[j]++;
    int queue[MAX_N], head = 0, tail = 0;
    for(int i = 0; i < g->n; i++) if(indeg[i] == 0) queue[tail++] = i;
    int order[MAX_N], nout = 0;
    while(head < tail){
        int u = queue[head++];
        order[nout++] = u;
        for(int v = 0; v < g->n; v++){
            if(g->w[u][v] > 0){
                indeg[v]--;
                if(indeg[v] == 0) queue[tail++] = v;
            }
        }
    }

    /* Relax in topological order */
    for(int k = 0; k < nout; k++){
        int u = order[k];
        if(dist[u] == INF) continue;
        for(int v = 0; v < g->n; v++){
            if(g->w[u][v] > 0){
                double d = dist[u] + g->w[u][v];
                if(d < dist[v]) dist[v] = d;
            }
        }
    }
    return dist[target];
}

/* ═══ TOTAL PATH PRODUCT = sum over all paths of product of edge weights ═══ */
static double total_influence(const Wdag *g, int source, int target){
    /* Dynamic programming: inf[v] = sum over all source→v paths
     * of the product of edge weights. Process in topological order. */
    double inf[MAX_N];
    for(int i = 0; i < g->n; i++) inf[i] = 0;
    inf[source] = 1;   /* empty path from source to itself has product 1 */

    int indeg[MAX_N] = {0};
    for(int i = 0; i < g->n; i++)
        for(int j = 0; j < g->n; j++)
            if(g->w[i][j] > 0) indeg[j]++;
    int queue[MAX_N], head = 0, tail = 0;
    for(int i = 0; i < g->n; i++) if(indeg[i] == 0) queue[tail++] = i;
    int order[MAX_N], nout = 0;
    while(head < tail){
        int u = queue[head++];
        order[nout++] = u;
        for(int v = 0; v < g->n; v++){
            if(g->w[u][v] > 0){
                indeg[v]--;
                if(indeg[v] == 0) queue[tail++] = v;
            }
        }
    }

    for(int k = 0; k < nout; k++){
        int u = order[k];
        for(int v = 0; v < g->n; v++){
            if(g->w[u][v] > 0){
                inf[v] += inf[u] * g->w[u][v];
            }
        }
    }
    return inf[target];
}

/* ═══ INTERVENTION: remove incoming edges to node x ═══ */
static double intervene_cost(const Wdag *g, int x){
    double total = 0;
    for(int i = 0; i < g->n; i++){
        if(g->w[i][x] > 0) total += g->w[i][x];
    }
    return total;
}

/* ═══ EXPERIMENT 1: Shortest path in a weighted DAG ═══ */
static void experiment_shortest(void){
    printf("\n═══ EXPERIMENT 1: Shortest causal path ═══\n\n");

    Wdag g; wdag_init(&g, 5);
    wdag_add(&g, 0, 1, 2.0);
    wdag_add(&g, 0, 2, 4.0);
    wdag_add(&g, 1, 2, 1.0);
    wdag_add(&g, 1, 3, 7.0);
    wdag_add(&g, 2, 3, 3.0);
    wdag_add(&g, 3, 4, 1.0);
    wdag_add(&g, 2, 4, 5.0);

    wdag_print("Weighted causal graph", &g);

    printf("\n  Shortest path costs from 0:\n");
    for(int j = 0; j < g.n; j++){
        double c = shortest_path_cost(&g, 0, j);
        printf("    0 → %d : %s\n", j, c == INF ? "unreachable" : "");
        if(c != INF) printf("       cost = %.2f\n", c);
    }

    printf("\n  For 0 → 4, the cheapest path is 0→1→2→3→4\n");
    printf("  with cost 2 + 1 + 3 + 1 = 7.\n");
    printf("\n  Pure causal bits know that 0 reaches 4; pure cost\n");
    printf("  bits know per-edge weights but no direction.\n");
    printf("  Their combination gives the minimum-cost causal path.\n");
}

/* ═══ EXPERIMENT 2: Total causal influence ═══ */
static void experiment_influence(void){
    printf("\n═══ EXPERIMENT 2: Total causal influence as path sum ═══\n\n");

    /* A diamond: 0 → 1 → 3 and 0 → 2 → 3. Two paths. */
    Wdag g; wdag_init(&g, 4);
    wdag_add(&g, 0, 1, 0.5);
    wdag_add(&g, 0, 2, 0.3);
    wdag_add(&g, 1, 3, 0.8);
    wdag_add(&g, 2, 3, 0.6);

    wdag_print("Diamond", &g);

    double direct_through_1 = 0.5 * 0.8;
    double direct_through_2 = 0.3 * 0.6;
    double total = total_influence(&g, 0, 3);

    printf("\n  Path 0→1→3 product: %.2f × %.2f = %.3f\n", 0.5, 0.8, direct_through_1);
    printf("  Path 0→2→3 product: %.2f × %.2f = %.3f\n", 0.3, 0.6, direct_through_2);
    printf("  Total influence 0 → 3 = %.3f\n", total);
    printf("  Expected sum = %.3f\n", direct_through_1 + direct_through_2);
    printf("  Match? %s\n",
           fabs(total - (direct_through_1 + direct_through_2)) < 1e-9 ? "YES ✓" : "NO");

    printf("\n  Wright-style path analysis (1921): decomposes causal\n");
    printf("  influence into a sum over independent directed paths.\n");
    printf("  This is the defining operation of the combined primitive.\n");
}

/* ═══ EXPERIMENT 3: Intervention cost ═══ */
static void experiment_intervention(void){
    printf("\n═══ EXPERIMENT 3: do(X) removes incoming edges; cost tallied ═══\n\n");

    /* rain → wet_grass ← sprinkler, wet_grass → slippery */
    Wdag g; wdag_init(&g, 4);
    /* 0 = rain, 1 = sprinkler, 2 = wet_grass, 3 = slippery */
    wdag_add(&g, 0, 2, 0.9);
    wdag_add(&g, 1, 2, 0.7);
    wdag_add(&g, 2, 3, 0.95);

    wdag_print("rain/sprinkler/wet/slippery", &g);

    double cost_before = intervene_cost(&g, 2);
    printf("\n  Cost to perform do(wet_grass): total weight of\n");
    printf("  removed incoming edges = %.2f + %.2f = %.2f\n",
           0.9, 0.7, cost_before);

    /* After intervention the causal influence from rain to slippery should drop to 0 */
    Wdag g2 = g;
    for(int i = 0; i < g.n; i++) g2.w[i][2] = 0;
    double inf_rain_slip_before = total_influence(&g, 0, 3);
    double inf_rain_slip_after = total_influence(&g2, 0, 3);
    printf("\n  Causal influence rain → slippery:\n");
    printf("    before intervention: %.4f\n", inf_rain_slip_before);
    printf("    after intervention:  %.4f\n", inf_rain_slip_after);
    printf("  %s\n", inf_rain_slip_after == 0 ? "✓ rain no longer reaches slippery" : "");

    printf("\n  Intervention cost combines Pearl's do-operator\n");
    printf("  (remove incoming edges) with cost accounting (weight\n");
    printf("  of removed edges). A new primitive operation.\n");
}

/* ═══ EXPERIMENT 4: Direct vs indirect effect ═══ */
static void experiment_decomposition(void){
    printf("\n═══ EXPERIMENT 4: Direct vs indirect effect ═══\n\n");

    /* X has a direct effect on Y (edge X → Y) AND an indirect
     * effect through mediator M: X → M → Y. */
    Wdag g; wdag_init(&g, 3);
    /* 0 = X, 1 = M, 2 = Y */
    wdag_add(&g, 0, 1, 0.6);   /* X → M */
    wdag_add(&g, 1, 2, 0.7);   /* M → Y */
    wdag_add(&g, 0, 2, 0.2);   /* X → Y direct */

    wdag_print("X - mediator - Y", &g);

    double direct = 0.2;                 /* X → Y path */
    double indirect = 0.6 * 0.7;         /* X → M → Y path */
    double total = total_influence(&g, 0, 2);

    printf("\n  Direct effect   (X → Y)       : %.3f\n", direct);
    printf("  Indirect effect (X → M → Y)   : %.3f\n", indirect);
    printf("  Total   (direct + indirect)   : %.3f\n", direct + indirect);
    printf("  Computed total_influence      : %.3f\n", total);

    printf("\n  The decomposition is NATIVE to the combined primitive.\n");
    printf("  Pure causal can only say 'X is an ancestor of Y' with\n");
    printf("  no separation. Pure cost has no notion of 'direct vs\n");
    printf("  mediated'. The combination makes both visible.\n");
}

/* ═══ EXPERIMENT 5: Irreducibility witness ═══ */
static void experiment_irreducibility(void){
    printf("\n═══ EXPERIMENT 5: Irreducibility to either axis alone ═══\n\n");

    printf("  Pure CAUSAL primitive:\n");
    printf("    knows 'X is an ancestor of Y' (yes/no)\n");
    printf("    supports topological sort and do-calculus\n");
    printf("    has NO metric — cannot distinguish 0.5 from 0.9\n");
    printf("    cannot compute path products or shortest paths\n\n");

    printf("  Pure COST primitive:\n");
    printf("    has weights and Ising-style energy\n");
    printf("    computes ground states of frustrated systems\n");
    printf("    has NO direction — edges are symmetric by default\n");
    printf("    cannot distinguish cause from effect\n\n");

    printf("  Combined CAUSAL × COST:\n");
    printf("    numerical weights ON directed acyclic edges\n");
    printf("    path products decompose causal influence (Wright 1921)\n");
    printf("    shortest path = minimum-cost causal chain\n");
    printf("    intervention cost = weight of removed incoming edges\n");
    printf("    direct effect vs mediated effect are DISTINCT\n\n");

    printf("  The defining new operation is TOTAL CAUSAL INFLUENCE\n");
    printf("  computed as a sum over directed paths of the product of\n");
    printf("  edge weights. Neither causal (no weights) nor cost (no\n");
    printf("  direction) can express it alone.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("CAUSAL × COST: weighted causal DAGs\n");
    printf("══════════════════════════════════════════\n");
    printf("Third combination primitive in the programme.\n");

    experiment_shortest();
    experiment_influence();
    experiment_intervention();
    experiment_decomposition();
    experiment_irreducibility();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Weighted DAG primitive inheriting acyclicity from\n");
    printf("     causal and numerical weights from cost\n");
    printf("  2. Shortest-path cost (Dijkstra / topological DP)\n");
    printf("  3. Total causal influence as sum-over-path-products\n");
    printf("     (Wright 1921 path analysis)\n");
    printf("  4. Intervention cost as weight-tallied do-operator\n");
    printf("  5. Direct vs mediated effect decomposition\n");
    printf("  6. Neither pure causal nor pure cost can express\n");
    printf("     total_influence — it is the combination's signature\n");
    printf("\n  Combination cell: CAUSAL × COST (RELATION × OPERATION)\n");
    printf("  Third entry in the combination catalogue after\n");
    printf("  reversible × cost and modal × quotient.\n");
    return 0;
}
