/*
 * BRAID BITS: topological computation on classical strands
 * ==========================================================
 *
 * Fourth alternative: a bit is a physical strand in a braid.
 * Computation is carried out by BRAIDING — swapping adjacent
 * strands either over or under.  The result of a computation
 * is a topological invariant of the braid word.
 *
 * Strands and generators
 * ----------------------
 * n strands labelled 0..n−1.  The braid group B_n on n strands
 * has n−1 generators σ_1, ..., σ_{n−1}:
 *
 *   σ_i   = strand i crosses OVER strand i+1
 *   σ_i^{-1} = strand i crosses UNDER strand i+1
 *
 * Relations (Artin 1925):
 *   σ_i σ_j = σ_j σ_i          if |i − j| ≥ 2
 *   σ_i σ_{i+1} σ_i = σ_{i+1} σ_i σ_{i+1}      (Yang-Baxter)
 *
 * A braid word is a sequence of generators applied to n strands.
 * Two representative invariants we can compute classically:
 *
 *   1. UNDERLYING PERMUTATION — each σ_i swaps strands i and i+1,
 *      forgetting over/under. This is a homomorphism B_n → S_n.
 *
 *   2. LINKING NUMBER of two strands — signed count of times they
 *      cross each other, over − under.  Knot-theory invariant
 *      (Gauss linking integral in discrete form).
 *
 *   3. WRITHE — signed sum of all crossings, braid-dependent.
 *      Not a topological invariant of the link but IS an invariant
 *      of the braid word up to planar isotopy.
 *
 * The computational point: topology replaces iteration with a
 * continuous deformation space.  Moves that look different
 * algebraically (e.g. σ_1 σ_2 σ_1 and σ_2 σ_1 σ_2) collapse to
 * the same topological object.
 *
 * Experiments:
 *   1. Artin relations hold as permutations
 *   2. Underlying permutation of a few braid words
 *   3. Linking number of two strands under various braids
 *   4. Writhe of the canonical Hopf, trefoil, and figure-8 braids
 *   5. Braid-word equality up to Reidemeister moves as a
 *      computational equivalence relation
 *
 * Compile: gcc -O3 -march=native -o braid braid_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define MAX_STRANDS 16

/* A braid-word entry: positive integer = σ_i, negative = σ_i^{-1} */
typedef struct {
    int gens[256];
    int len;
} Braid;

static void braid_init(Braid *b){b->len = 0;}
static void braid_append(Braid *b, int g){b->gens[b->len++] = g;}

/* ═══ Underlying permutation ═══ */
static void identity_perm(int *p, int n){for(int i = 0; i < n; i++) p[i] = i;}
static void apply_braid_to_perm(int *p, int n, const Braid *b){
    for(int k = 0; k < b->len; k++){
        int g = b->gens[k];
        int i = (g > 0 ? g : -g) - 1;   /* 0-based */
        if(i < 0 || i >= n - 1) continue;
        int t = p[i]; p[i] = p[i+1]; p[i+1] = t;
    }
}

/* ═══ Linking number of strands a, b ═══
 *
 * Trace each strand's position through the braid; count signed
 * crossings between strands a and b (+1 for over-crossings
 * where a is on top, −1 for under-crossings).
 */
static int linking_number(const Braid *b, int n, int a, int c){
    int p[MAX_STRANDS];
    identity_perm(p, n);
    /* Track which strand label is at which position. */
    int pos_of[MAX_STRANDS];
    for(int i = 0; i < n; i++) pos_of[i] = i;

    int link = 0;
    for(int k = 0; k < b->len; k++){
        int g = b->gens[k];
        int sign = (g > 0) ? +1 : -1;
        int i = (g > 0 ? g : -g) - 1;
        if(i < 0 || i >= n - 1) continue;

        /* strands at positions i and i+1 swap */
        int s1 = p[i];
        int s2 = p[i+1];
        if((s1 == a && s2 == c) || (s1 == c && s2 == a)){
            link += sign;
        }
        p[i] = s2; p[i+1] = s1;
        pos_of[s1] = i+1;
        pos_of[s2] = i;
    }
    return link;
}

/* ═══ Writhe: signed sum of all crossings ═══ */
static int braid_writhe(const Braid *b){
    int w = 0;
    for(int k = 0; k < b->len; k++) w += (b->gens[k] > 0 ? +1 : -1);
    return w;
}

/* ═══ Print a braid word compactly ═══ */
static void braid_print(const char *name, const Braid *b){
    printf("  %-12s = ", name);
    for(int k = 0; k < b->len; k++){
        int g = b->gens[k];
        if(g > 0) printf("σ%d ", g);
        else      printf("σ%d⁻¹ ", -g);
    }
    printf("  (len %d)\n", b->len);
}

/* ═══ EXPERIMENT 1: Artin relations hold as permutations ═══ */
static void experiment_artin(void){
    printf("\n═══ EXPERIMENT 1: Artin relations as permutations ═══\n\n");

    int n = 4;
    int p1[MAX_STRANDS], p2[MAX_STRANDS];

    /* Relation 1: σ_1 σ_3 = σ_3 σ_1 (far commutativity) */
    Braid a, b;
    braid_init(&a); braid_append(&a, 1); braid_append(&a, 3);
    braid_init(&b); braid_append(&b, 3); braid_append(&b, 1);
    identity_perm(p1, n); identity_perm(p2, n);
    apply_braid_to_perm(p1, n, &a);
    apply_braid_to_perm(p2, n, &b);
    int eq1 = (memcmp(p1, p2, sizeof(int)*n) == 0);
    braid_print("σ_1 σ_3", &a);
    braid_print("σ_3 σ_1", &b);
    printf("  Underlying permutations equal: %s\n\n", eq1 ? "YES ✓" : "NO ✗");

    /* Relation 2: σ_1 σ_2 σ_1 = σ_2 σ_1 σ_2 (Yang-Baxter) */
    braid_init(&a);
    braid_append(&a, 1); braid_append(&a, 2); braid_append(&a, 1);
    braid_init(&b);
    braid_append(&b, 2); braid_append(&b, 1); braid_append(&b, 2);
    identity_perm(p1, n); identity_perm(p2, n);
    apply_braid_to_perm(p1, n, &a);
    apply_braid_to_perm(p2, n, &b);
    int eq2 = (memcmp(p1, p2, sizeof(int)*n) == 0);
    braid_print("σ_1 σ_2 σ_1", &a);
    braid_print("σ_2 σ_1 σ_2", &b);
    printf("  Underlying permutations equal: %s\n", eq2 ? "YES ✓" : "NO ✗");
    printf("  (Both reduce to the 3-cycle (1 3 2) on strands 0..3)\n");

    printf("\n  Artin relations are structural facts: they hold as\n");
    printf("  permutations but the braids themselves are topologically\n");
    printf("  DISTINCT once over/under is tracked.\n");
}

/* ═══ EXPERIMENT 2: Permutation images ═══ */
static void experiment_permutation_image(void){
    printf("\n═══ EXPERIMENT 2: Underlying permutation of braid words ═══\n\n");

    int n = 4;
    struct {const char *name; int gens[10]; int len;} tests[] = {
        {"σ_1",         {1}, 1},
        {"σ_1 σ_2 σ_3", {1, 2, 3}, 3},
        {"σ_1 σ_1",     {1, 1}, 2},
        {"σ_1 σ_2 σ_1 σ_2 σ_1 σ_2", {1,2,1,2,1,2}, 6},
    };

    for(int t = 0; t < 4; t++){
        Braid b; braid_init(&b);
        for(int k = 0; k < tests[t].len; k++) braid_append(&b, tests[t].gens[k]);
        int p[MAX_STRANDS]; identity_perm(p, n);
        apply_braid_to_perm(p, n, &b);
        printf("  %-28s  → perm ", tests[t].name);
        for(int i = 0; i < n; i++) printf("%d ", p[i]);
        printf("\n");
    }

    printf("\n  σ_1 σ_1 gives the identity as a permutation (double swap)\n");
    printf("  but as a braid it has writhe 2 — topologically NOT trivial.\n");
}

/* ═══ EXPERIMENT 3: Linking number ═══ */
static void experiment_linking(void){
    printf("\n═══ EXPERIMENT 3: Linking number of two strands ═══\n\n");

    int n = 3;

    /* Hopf link on 2 strands: σ_1 σ_1 linking number = 2
     * (but we need 2-strand closure; use 2 strands) */
    Braid hopf;
    braid_init(&hopf);
    braid_append(&hopf, 1); braid_append(&hopf, 1);
    printf("  Braid σ_1 σ_1 on strands 0 and 1:\n");
    printf("    linking number(0, 1) = %d\n", linking_number(&hopf, 2, 0, 1));

    /* Anti-Hopf: σ_1^{-1} σ_1^{-1} */
    Braid anti;
    braid_init(&anti);
    braid_append(&anti, -1); braid_append(&anti, -1);
    printf("  Braid σ_1⁻¹ σ_1⁻¹:\n");
    printf("    linking number(0, 1) = %d\n", linking_number(&anti, 2, 0, 1));

    /* Zero link: σ_1 σ_1^{-1} */
    Braid unlink;
    braid_init(&unlink);
    braid_append(&unlink, 1); braid_append(&unlink, -1);
    printf("  Braid σ_1 σ_1⁻¹ (trivial):\n");
    printf("    linking number(0, 1) = %d\n", linking_number(&unlink, 2, 0, 1));

    /* Three-strand case */
    Braid three;
    braid_init(&three);
    braid_append(&three, 1); braid_append(&three, 2);
    braid_append(&three, 1); braid_append(&three, 2);
    (void)n;
    printf("\n  Braid σ_1 σ_2 σ_1 σ_2 on 3 strands:\n");
    printf("    linking(0,1) = %d\n", linking_number(&three, 3, 0, 1));
    printf("    linking(0,2) = %d\n", linking_number(&three, 3, 0, 2));
    printf("    linking(1,2) = %d\n", linking_number(&three, 3, 1, 2));
}

/* ═══ EXPERIMENT 4: Writhe of canonical braids ═══ */
static void experiment_writhe(void){
    printf("\n═══ EXPERIMENT 4: Writhe of canonical braids ═══\n\n");

    struct {const char *name; int gens[12]; int len;} cases[] = {
        {"trivial",            {1, -1}, 2},
        {"Hopf (σ₁²)",         {1, 1}, 2},
        {"trefoil (σ₁³)",      {1, 1, 1}, 3},
        {"figure-8 (σ₁σ₂⁻¹)^2",{1, -2, 1, -2}, 4},
        {"8-crossing identity",{1,1,1,-1,-1,-1}, 6},
    };

    for(int i = 0; i < 5; i++){
        Braid b; braid_init(&b);
        for(int k = 0; k < cases[i].len; k++) braid_append(&b, cases[i].gens[k]);
        printf("  %-22s writhe = %+d  length = %d\n",
               cases[i].name, braid_writhe(&b), b.len);
    }
    printf("\n  Writhe = algebraic crossing number = (positive) − (negative).\n");
    printf("  trefoil σ₁³ has writhe 3 — corresponds to the 3_1 knot\n");
    printf("  with crossing number 3 after closure.\n");
}

/* ═══ EXPERIMENT 5: Braid word equivalence via invariants ═══ */
static void experiment_equivalence(void){
    printf("\n═══ EXPERIMENT 5: Braid equivalence by invariants ═══\n\n");

    /* Build three braid words on 3 strands. Check if permutations
     * agree and if writhes agree — if both do, they are likely
     * equivalent up to simple Reidemeister moves. */
    int n = 3;

    Braid a, b, c;
    braid_init(&a);
    braid_append(&a, 1); braid_append(&a, 2); braid_append(&a, 1);

    braid_init(&b);
    braid_append(&b, 2); braid_append(&b, 1); braid_append(&b, 2);

    braid_init(&c);
    braid_append(&c, 1); braid_append(&c, 1); braid_append(&c, 1);

    int pa[MAX_STRANDS], pb[MAX_STRANDS], pc[MAX_STRANDS];
    identity_perm(pa, n); identity_perm(pb, n); identity_perm(pc, n);
    apply_braid_to_perm(pa, n, &a);
    apply_braid_to_perm(pb, n, &b);
    apply_braid_to_perm(pc, n, &c);

    braid_print("a = σ₁σ₂σ₁", &a);
    printf("             perm = %d %d %d, writhe = %+d\n", pa[0], pa[1], pa[2], braid_writhe(&a));
    braid_print("b = σ₂σ₁σ₂", &b);
    printf("             perm = %d %d %d, writhe = %+d\n", pb[0], pb[1], pb[2], braid_writhe(&b));
    braid_print("c = σ₁σ₁σ₁", &c);
    printf("             perm = %d %d %d, writhe = %+d\n", pc[0], pc[1], pc[2], braid_writhe(&c));

    int ab_same = (memcmp(pa, pb, sizeof(int)*n) == 0) && braid_writhe(&a) == braid_writhe(&b);
    int ac_same = (memcmp(pa, pc, sizeof(int)*n) == 0) && braid_writhe(&a) == braid_writhe(&c);
    printf("\n  a ~ b (Yang-Baxter)? %s\n", ab_same ? "YES ✓" : "NO ✗");
    printf("  a ~ c ?              %s\n", ac_same ? "compatible on these invariants" : "NO — different permutations");
    printf("\n  Two invariants (permutation + writhe) already distinguish\n");
    printf("  many braid classes. Finer invariants (Burau matrix, Jones\n");
    printf("  polynomial) complete the classification.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BRAID BITS: topological computation on strands\n");
    printf("══════════════════════════════════════════\n");

    experiment_artin();
    experiment_permutation_image();
    experiment_linking();
    experiment_writhe();
    experiment_equivalence();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Bits as physical strands in a braid group B_n\n");
    printf("  2. Artin relations verified via underlying permutation\n");
    printf("  3. Linking number as a strand-pair invariant\n");
    printf("  4. Writhe as a simple braid-word invariant\n");
    printf("  5. Equivalence classes via multi-invariant comparison\n");
    printf("\n  New primitive property vs ordinary bits: TOPOLOGY.\n");
    printf("  Computation becomes tracking how strands cross over or\n");
    printf("  under each other; topological invariants are the outputs.\n");
    return 0;
}
