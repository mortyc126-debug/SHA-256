/*
 * RELATIONAL BITS: a bit as an edge, not a vertex
 * ====================================================
 *
 * Candidate ELEVENTH axis. In every previous primitive the bit
 * is a PROPERTY of a single entity — a value, a distribution,
 * a function, a strand, a world, a resource count. A relational
 * bit is different: it lives BETWEEN two entities. It says
 *
 *     is a related to b ?    (0 = no, 1 = yes)
 *
 * The primitive is a subset of a product set, i.e. a binary
 * relation R ⊆ A × B. Operations are relational algebra:
 * composition, converse, union, intersection, transitive
 * closure.
 *
 * Why this is not just a collection of bits
 * ------------------------------------------
 * A 'collection of bits' has no intrinsic topology — it is just
 * a bit array. A RELATION has edge structure: composition
 * R ; S sends (a, c) to TRUE iff there is an intermediate b
 * with (a, b) ∈ R and (b, c) ∈ S. This is fundamentally
 * different from any of the ten earlier axes.
 *
 * None of:
 *   binary, phase, prob, reversible, stream, braid, linear,
 *   self-ref, higher-order, modal
 * treats 'connectedness between two objects' as primitive.
 * Graphs, Kleene algebras, database joins, Prolog facts, and
 * all of relational algebra live here.
 *
 * Experiments:
 *
 *   1. Basic operations: union, intersection, converse
 *   2. Composition R ; S and associativity thereof
 *   3. Transitive closure R⁺ via iterated composition
 *   4. Kleene-star closure R* including identity
 *   5. A relation on 4 nodes interpreted three ways: as a set
 *      of edges, as a square matrix, as a Boolean function of
 *      two variables — three faces of the same primitive
 *
 * Compile: gcc -O3 -march=native -o rel relational_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define N 5     /* number of nodes */

typedef int Rel[N][N];   /* R[i][j] = 1 iff i R j */

static void rel_zero(Rel r){for(int i = 0; i < N; i++) for(int j = 0; j < N; j++) r[i][j] = 0;}
static void rel_id(Rel r){rel_zero(r); for(int i = 0; i < N; i++) r[i][i] = 1;}
static void rel_copy(Rel dst, const Rel src){memcpy(dst, src, sizeof(Rel));}

static void rel_union(Rel out, const Rel a, const Rel b){
    for(int i = 0; i < N; i++) for(int j = 0; j < N; j++)
        out[i][j] = a[i][j] | b[i][j];
}
static void rel_inter(Rel out, const Rel a, const Rel b){
    for(int i = 0; i < N; i++) for(int j = 0; j < N; j++)
        out[i][j] = a[i][j] & b[i][j];
}
static void rel_converse(Rel out, const Rel a){
    for(int i = 0; i < N; i++) for(int j = 0; j < N; j++)
        out[j][i] = a[i][j];
}
/* Relational composition: (a ; b)(i, k) = OR_j a(i, j) AND b(j, k) */
static void rel_compose(Rel out, const Rel a, const Rel b){
    Rel r; rel_zero(r);
    for(int i = 0; i < N; i++)
        for(int k = 0; k < N; k++){
            int v = 0;
            for(int j = 0; j < N; j++){
                if(a[i][j] && b[j][k]){v = 1; break;}
            }
            r[i][k] = v;
        }
    memcpy(out, r, sizeof(Rel));
}
static int rel_eq(const Rel a, const Rel b){
    return memcmp(a, b, sizeof(Rel)) == 0;
}
static void rel_print(const char *name, const Rel r){
    printf("  %s =\n", name);
    for(int i = 0; i < N; i++){
        printf("    [ ");
        for(int j = 0; j < N; j++) printf("%d ", r[i][j]);
        printf("]\n");
    }
}

/* Transitive closure: R⁺ = R ∪ R² ∪ R³ ∪ ... */
static void rel_plus(Rel out, const Rel a){
    Rel cur, prod;
    rel_copy(cur, a);
    while(1){
        rel_compose(prod, cur, a);
        rel_union(cur, cur, prod);
        /* check if we gained anything */
        int changed = 0;
        for(int i = 0; i < N && !changed; i++)
            for(int j = 0; j < N && !changed; j++)
                if(prod[i][j] && !cur[i][j]) changed = 1;
        /* Actually simpler: iterate to fixed point */
        Rel next;
        rel_compose(next, cur, a);
        rel_union(next, cur, next);
        if(rel_eq(next, cur)) break;
        rel_copy(cur, next);
    }
    rel_copy(out, cur);
}
static void rel_star(Rel out, const Rel a){
    Rel id, plus;
    rel_id(id);
    rel_plus(plus, a);
    rel_union(out, plus, id);
}

/* ═══ EXPERIMENT 1: Basic operations ═══ */
static void experiment_basic(void){
    printf("\n═══ EXPERIMENT 1: Union, intersection, converse ═══\n\n");

    Rel a = {{0, 1, 0, 0, 0},
             {0, 0, 1, 0, 0},
             {0, 0, 0, 1, 0},
             {0, 0, 0, 0, 1},
             {1, 0, 0, 0, 0}};
    Rel b = {{0, 0, 1, 0, 0},
             {0, 0, 0, 0, 1},
             {1, 0, 0, 0, 0},
             {0, 1, 0, 0, 0},
             {0, 0, 0, 1, 0}};

    rel_print("a (cycle 0→1→2→3→4→0)", a);
    rel_print("b (skipping cycle)", b);

    Rel u; rel_union(u, a, b);
    rel_print("a ∪ b", u);

    Rel i; rel_inter(i, a, b);
    rel_print("a ∩ b (empty — disjoint)", i);

    Rel c; rel_converse(c, a);
    rel_print("a⁻¹ (reverse of cycle)", c);
}

/* ═══ EXPERIMENT 2: Composition and associativity ═══ */
static void experiment_compose(void){
    printf("\n═══ EXPERIMENT 2: Composition and associativity ═══\n\n");

    Rel a = {{0, 1, 0, 0, 0},
             {0, 0, 1, 0, 0},
             {0, 0, 0, 1, 0},
             {0, 0, 0, 0, 1},
             {1, 0, 0, 0, 0}};

    Rel aa; rel_compose(aa, a, a);
    rel_print("a ; a  (two-step successor)", aa);

    Rel aaa; rel_compose(aaa, aa, a);
    Rel aaa2; rel_compose(aaa2, a, aa);
    printf("  (a;a);a  equal to  a;(a;a) ?  %s\n",
           rel_eq(aaa, aaa2) ? "YES ✓ associative" : "NO ✗");
}

/* ═══ EXPERIMENT 3: Transitive closure ═══ */
static void experiment_plus(void){
    printf("\n═══ EXPERIMENT 3: Transitive closure R⁺ ═══\n\n");

    /* Path graph 0 → 1 → 2 → 3 → 4 (acyclic) */
    Rel a; rel_zero(a);
    a[0][1] = 1; a[1][2] = 1; a[2][3] = 1; a[3][4] = 1;

    Rel plus; rel_plus(plus, a);
    rel_print("a (path 0→1→2→3→4)", a);
    rel_print("a⁺ (reachability)", plus);

    printf("  a⁺ is the full upper triangle: every pair with i < j.\n");
}

/* ═══ EXPERIMENT 4: Kleene closure R* ═══ */
static void experiment_star(void){
    printf("\n═══ EXPERIMENT 4: Kleene star R* = R⁺ ∪ identity ═══\n\n");

    Rel a; rel_zero(a);
    a[0][1] = 1; a[1][2] = 1;
    a[2][0] = 1;   /* cycle */
    a[3][4] = 1;   /* separate component */

    Rel star; rel_star(star, a);
    rel_print("a  (cycle 0→1→2→0 plus 3→4)", a);
    rel_print("a* (includes identity)", star);

    printf("  In a*, the cycle yields a full 3×3 block on {0,1,2}\n");
    printf("  because every node can reach every other, plus the\n");
    printf("  identity on {3,4}.\n");
}

/* ═══ EXPERIMENT 5: Three faces of the same primitive ═══ */
static void experiment_three_faces(void){
    printf("\n═══ EXPERIMENT 5: Relation as edge set / matrix / Boolean function ═══\n\n");

    Rel r = {{0, 1, 1, 0, 0},
             {0, 0, 0, 1, 0},
             {0, 0, 0, 0, 1},
             {1, 0, 0, 0, 0},
             {0, 0, 0, 0, 0}};

    /* Face 1: edge list */
    printf("  As edge list:\n    ");
    for(int i = 0; i < N; i++)
        for(int j = 0; j < N; j++)
            if(r[i][j]) printf("(%d, %d) ", i, j);
    printf("\n\n");

    /* Face 2: Boolean matrix */
    rel_print("As adjacency matrix", r);

    /* Face 3: Boolean function of two vars */
    printf("  As function R : {0..%d}² → {0,1}:\n", N - 1);
    printf("    R(0,1)=%d, R(0,2)=%d, R(1,3)=%d, R(2,4)=%d, R(3,0)=%d\n",
           r[0][1], r[0][2], r[1][3], r[2][4], r[3][0]);

    printf("\n  The three presentations carry the same information,\n");
    printf("  but enable different operations naturally:\n");
    printf("    edge list    — enumeration, insertion\n");
    printf("    matrix       — composition, powers, rank\n");
    printf("    Boolean fn   — logical quantification, ∀∃\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("RELATIONAL BITS: bit as edge, not vertex\n");
    printf("══════════════════════════════════════════\n");
    printf("A bit encodes whether two things are related.\n");
    printf("N = %d nodes.\n", N);

    experiment_basic();
    experiment_compose();
    experiment_plus();
    experiment_star();
    experiment_three_faces();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. A relational bit is a subset of a product set\n");
    printf("  2. Relational algebra: union, intersection, converse,\n");
    printf("     composition — each a new fundamental operation\n");
    printf("  3. Composition is associative → monoid of relations\n");
    printf("  4. Transitive closure R⁺ and Kleene star R*\n");
    printf("  5. Triple presentation: edge list / matrix / Boolean fn\n");
    printf("\n  Proposed ELEVENTH axis: RELATIONALITY.\n");
    printf("  Every previous primitive was a property of ONE entity;\n");
    printf("  a relational bit is a connection between TWO.\n");
    return 0;
}
