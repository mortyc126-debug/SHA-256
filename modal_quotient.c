/*
 * MODAL × QUOTIENT: bisimulation-quotiented Kripke frames
 * ==========================================================
 *
 * Second combination primitive after thermo_reversible.c.  The
 * intersection of the MODAL axis (Kripke frames, accessibility,
 * □/◇ operators) and the QUOTIENT axis (equivalence classes as
 * primitives) yields a genuinely new object: a Kripke frame
 * where worlds are IDENTIFIED via bisimulation.
 *
 * Historical background:
 *
 *   - Park (1981), Milner (1989): bisimulation as the natural
 *     equivalence on labelled transition systems
 *   - Hennessy-Milner theorem: two worlds are bisimilar iff
 *     they satisfy exactly the same modal formulas
 *   - Minimal bisimulation-quotient frame: the smallest Kripke
 *     frame that retains all modal information of the original
 *
 * Why this combination matters:
 *
 *   MODAL alone has a Kripke frame but no way to MERGE worlds.
 *   Two worlds with identical outgoing structure are still
 *   addressable as different primitives.
 *
 *   QUOTIENT alone has equivalence classes but no modal
 *   operators — there is no notion of 'accessible' and hence
 *   no structural reason to identify two elements.
 *
 *   Their combination says: compute the largest equivalence
 *   relation on worlds that is closed under modal evidence
 *   (the bisimulation), then project the frame to that
 *   quotient. The resulting primitive is smaller, simpler,
 *   and modally equivalent to the original.
 *
 * Experiments:
 *
 *   1. Build a Kripke frame with a proposition at each world
 *   2. Compute the maximal bisimulation via fixed-point
 *      iteration (start with label equivalence, refine until
 *      stable)
 *   3. Project the frame to bisimulation classes
 *   4. Verify modal formula preservation: every subformula
 *      has the same truth value at corresponding world
 *   5. Witness the benefit: quotient is strictly smaller
 *
 * Compile: gcc -O3 -march=native -o mq modal_quotient.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define MAX_W 16

/* ═══ KRIPKE FRAME ═══ */
typedef struct {
    int n;
    int R[MAX_W][MAX_W];   /* R[i][j] = 1 iff i → j */
    int p[MAX_W];          /* proposition value at each world */
} Frame;

static void frame_print(const char *name, const Frame *f){
    printf("  %s (n = %d)\n", name, f->n);
    printf("    worlds:  ");
    for(int i = 0; i < f->n; i++) printf("%d ", i);
    printf("\n    p(w):    ");
    for(int i = 0; i < f->n; i++) printf("%d ", f->p[i]);
    printf("\n    edges:\n");
    for(int i = 0; i < f->n; i++){
        for(int j = 0; j < f->n; j++){
            if(f->R[i][j]) printf("      %d → %d\n", i, j);
        }
    }
}

/* ═══ BISIMULATION ═══
 *
 * Start with label equivalence: i ~ j iff p(i) == p(j).
 * Refine: i ~ j iff
 *   p(i) == p(j)  AND
 *   for every successor i' of i, there exists j' ~ i' that is a successor of j
 *   and vice versa.
 *
 * Iterate to fixed point.
 */
static int bisim_equivalent(const Frame *f, int i, int j, int part[MAX_W]){
    /* At this iteration, part[·] gives the current class id.
     * Check the back-and-forth condition under part. */
    if(part[i] != part[j]) return 0;

    /* Forth: every successor i' of i must be matched by some successor j' of j */
    for(int ip = 0; ip < f->n; ip++){
        if(!f->R[i][ip]) continue;
        int ok = 0;
        for(int jp = 0; jp < f->n; jp++){
            if(f->R[j][jp] && part[jp] == part[ip]){ok = 1; break;}
        }
        if(!ok) return 0;
    }
    /* Back: symmetric condition */
    for(int jp = 0; jp < f->n; jp++){
        if(!f->R[j][jp]) continue;
        int ok = 0;
        for(int ip = 0; ip < f->n; ip++){
            if(f->R[i][ip] && part[ip] == part[jp]){ok = 1; break;}
        }
        if(!ok) return 0;
    }
    return 1;
}

/* Compute bisimulation partition via iterative refinement.
 * Returns number of classes. part[i] = class id of world i. */
static int compute_bisim(const Frame *f, int part[MAX_W]){
    /* Initial: group by label */
    for(int i = 0; i < f->n; i++) part[i] = f->p[i];

    int changed = 1;
    int iter = 0;
    while(changed && iter < 100){
        changed = 0;
        iter++;

        int new_part[MAX_W];
        int n_new = 0;

        for(int i = 0; i < f->n; i++){
            /* Find an earlier world j with j < i that is still
             * bisim-equivalent to i under the current partition. */
            int found = -1;
            for(int j = 0; j < i; j++){
                if(bisim_equivalent(f, i, j, part)){found = j; break;}
            }
            if(found >= 0){
                new_part[i] = new_part[found];
            } else {
                new_part[i] = n_new++;
            }
        }

        /* Check if partition changed */
        int same = 1;
        for(int i = 0; i < f->n; i++)
            for(int j = i + 1; j < f->n; j++){
                int old_same = (part[i] == part[j]);
                int new_same = (new_part[i] == new_part[j]);
                if(old_same != new_same){same = 0; break;}
            }
        if(!same) changed = 1;
        for(int i = 0; i < f->n; i++) part[i] = new_part[i];
    }

    /* Count classes */
    int max_id = 0;
    for(int i = 0; i < f->n; i++) if(part[i] > max_id) max_id = part[i];
    return max_id + 1;
}

/* ═══ QUOTIENT FRAME ═══ */
static void quotient_frame(const Frame *f, int part[MAX_W], int n_classes, Frame *out){
    out->n = n_classes;
    memset(out->R, 0, sizeof(out->R));
    /* Pick a representative for each class and copy its p(·) */
    int seen[MAX_W] = {0};
    for(int i = 0; i < f->n; i++){
        int c = part[i];
        if(!seen[c]){
            out->p[c] = f->p[i];
            seen[c] = 1;
        }
    }
    /* Edges between classes: c → c' iff some i in c has an edge to some j in c' */
    for(int i = 0; i < f->n; i++){
        for(int j = 0; j < f->n; j++){
            if(f->R[i][j]) out->R[part[i]][part[j]] = 1;
        }
    }
}

/* ═══ MODAL EVALUATION ═══
 *
 * Simple formulas: atomic p, ¬φ, φ∧ψ, □φ, ◇φ.
 * We encode them as a small enum + recursive eval.
 */
typedef enum {F_P, F_NOT, F_AND, F_OR, F_BOX, F_DIAMOND} FOp;

typedef struct Formula {
    FOp op;
    struct Formula *a, *b;
} Formula;

static Formula f_p    = {F_P, NULL, NULL};
static Formula f_notp = {F_NOT, &f_p, NULL};
static Formula f_box_p = {F_BOX, &f_p, NULL};
static Formula f_dia_p = {F_DIAMOND, &f_p, NULL};
static Formula f_box_box_p; /* init in main */
static Formula f_dia_dia_p;
static Formula f_box_dia_p;

static int eval(const Frame *f, int w, const Formula *phi){
    switch(phi->op){
    case F_P:       return f->p[w];
    case F_NOT:     return !eval(f, w, phi->a);
    case F_AND:     return eval(f, w, phi->a) && eval(f, w, phi->b);
    case F_OR:      return eval(f, w, phi->a) || eval(f, w, phi->b);
    case F_BOX:
        for(int u = 0; u < f->n; u++){
            if(f->R[w][u] && !eval(f, u, phi->a)) return 0;
        }
        return 1;
    case F_DIAMOND:
        for(int u = 0; u < f->n; u++){
            if(f->R[w][u] && eval(f, u, phi->a)) return 1;
        }
        return 0;
    }
    return 0;
}

/* ═══ EXPERIMENT 1: Build frame and compute bisimulation ═══ */
static void experiment_bisim(void){
    printf("\n═══ EXPERIMENT 1: Compute bisimulation of a Kripke frame ═══\n\n");

    /* 6 worlds: 0 and 3 have p=1 with the same outgoing pattern.
     * 1 and 4 have p=0 with the same outgoing. 2 and 5 are
     * 'dead ends' with p=1 and p=0 respectively. */
    Frame f;
    f.n = 6;
    memset(f.R, 0, sizeof(f.R));
    f.p[0] = 1; f.p[1] = 0; f.p[2] = 1;
    f.p[3] = 1; f.p[4] = 0; f.p[5] = 0;
    f.R[0][1] = 1; f.R[0][2] = 1;
    f.R[3][4] = 1; f.R[3][2] = 1;
    f.R[1][2] = 1;
    f.R[4][2] = 1;
    /* 2 and 5 have no successors */

    frame_print("Original frame", &f);

    int part[MAX_W];
    int n = compute_bisim(&f, part);
    printf("\n  Bisimulation partition: ");
    for(int i = 0; i < f.n; i++) printf("%d ", part[i]);
    printf("\n  Number of classes: %d (original had %d worlds)\n", n, f.n);

    printf("\n  Worlds that merged (bisimilar pairs):\n");
    for(int i = 0; i < f.n; i++)
        for(int j = i + 1; j < f.n; j++){
            if(part[i] == part[j]){
                printf("    %d ~ %d  (both have p=%d and same successor profile)\n",
                       i, j, f.p[i]);
            }
        }
}

/* ═══ EXPERIMENT 2: Quotient frame and modal preservation ═══ */
static void experiment_preservation(void){
    printf("\n═══ EXPERIMENT 2: Modal formula preservation under quotient ═══\n\n");

    Frame f;
    f.n = 6;
    memset(f.R, 0, sizeof(f.R));
    f.p[0] = 1; f.p[1] = 0; f.p[2] = 1;
    f.p[3] = 1; f.p[4] = 0; f.p[5] = 0;
    f.R[0][1] = 1; f.R[0][2] = 1;
    f.R[3][4] = 1; f.R[3][2] = 1;
    f.R[1][2] = 1;
    f.R[4][2] = 1;

    int part[MAX_W];
    int n_classes = compute_bisim(&f, part);

    Frame q;
    quotient_frame(&f, part, n_classes, &q);
    frame_print("Quotient frame", &q);

    /* Formulas */
    f_box_box_p.op = F_BOX; f_box_box_p.a = &f_box_p; f_box_box_p.b = NULL;
    f_dia_dia_p.op = F_DIAMOND; f_dia_dia_p.a = &f_dia_p; f_dia_dia_p.b = NULL;
    f_box_dia_p.op = F_BOX; f_box_dia_p.a = &f_dia_p; f_box_dia_p.b = NULL;

    struct { const char *name; Formula *phi; } fs[] = {
        {"p       ", &f_p},
        {"¬p      ", &f_notp},
        {"□p      ", &f_box_p},
        {"◇p      ", &f_dia_p},
        {"□□p     ", &f_box_box_p},
        {"◇◇p     ", &f_dia_dia_p},
        {"□◇p     ", &f_box_dia_p},
    };

    printf("\n  Formula truth values — original (by world) vs quotient (by class):\n");
    printf("  formula | original: w=0 1 2 3 4 5 | quotient: class 0 1 …\n");
    printf("  --------+------------------------+----------------------\n");
    int mismatches = 0;
    for(int k = 0; k < 7; k++){
        printf("  %s |           ", fs[k].name);
        for(int w = 0; w < f.n; w++) printf("%d ", eval(&f, w, fs[k].phi));
        printf("   |           ");
        for(int c = 0; c < q.n; c++) printf("%d ", eval(&q, c, fs[k].phi));
        printf("\n");

        /* Check preservation: each world must agree with its class representative */
        for(int w = 0; w < f.n; w++){
            int ov = eval(&f, w, fs[k].phi);
            int qv = eval(&q, part[w], fs[k].phi);
            if(ov != qv) mismatches++;
        }
    }
    printf("\n  Total mismatches world-vs-class: %d (expected 0)\n", mismatches);
    printf("  %s\n", mismatches == 0 ? "✓ modal formulas preserved by quotient"
                                      : "✗ FORMULAS NOT PRESERVED");
}

/* ═══ EXPERIMENT 3: Compression benefit ═══ */
static void experiment_compression(void){
    printf("\n═══ EXPERIMENT 3: Quotient can compress the frame significantly ═══\n\n");

    /* Build a frame with many bisimilar worlds */
    Frame f;
    f.n = 8;
    memset(f.R, 0, sizeof(f.R));

    /* Worlds 0..3: p=1, each has a single edge to a dead p=0 end
     * Worlds 4..7: p=0, each is a dead end
     * Pattern: 0→4, 1→5, 2→6, 3→7.
     * All 0..3 are bisimilar; all 4..7 are bisimilar. */
    f.p[0] = 1; f.p[1] = 1; f.p[2] = 1; f.p[3] = 1;
    f.p[4] = 0; f.p[5] = 0; f.p[6] = 0; f.p[7] = 0;
    f.R[0][4] = 1;
    f.R[1][5] = 1;
    f.R[2][6] = 1;
    f.R[3][7] = 1;

    int part[MAX_W];
    int n = compute_bisim(&f, part);
    printf("  Original: 8 worlds\n");
    printf("  Partition: ");
    for(int i = 0; i < 8; i++) printf("%d ", part[i]);
    printf("\n  Quotient classes: %d\n", n);
    printf("  Compression ratio: %d → %d (%.0f%%)\n",
           f.n, n, 100.0 * n / f.n);
    printf("\n  Every modal property that held in the original frame\n");
    printf("  holds in the quotient, and vice versa. The smaller frame\n");
    printf("  is a lossless compression for modal reasoning.\n");
}

/* ═══ EXPERIMENT 4: Witness of combined primitive ═══ */
static void experiment_witness(void){
    printf("\n═══ EXPERIMENT 4: Neither axis alone can express this ═══\n\n");

    printf("  Pure MODAL primitive:\n");
    printf("    has a Kripke frame and □/◇ operators\n");
    printf("    CANNOT merge worlds: every world is a distinct\n");
    printf("      addressable primitive\n");
    printf("    cannot compress bisimilar worlds\n\n");

    printf("  Pure QUOTIENT primitive:\n");
    printf("    has equivalence classes and canonicalisation\n");
    printf("    CANNOT define 'bisimilar' without an accessibility\n");
    printf("      relation and modal operators\n");
    printf("    has no notion of what equivalence to compute\n\n");

    printf("  Combined MODAL × QUOTIENT:\n");
    printf("    accessibility gives the structure\n");
    printf("    bisimulation is a specific equivalence DEFINED BY\n");
    printf("      the modal language\n");
    printf("    quotient projection gives a minimal frame\n");
    printf("    modal formulas are INVARIANT by construction\n\n");

    printf("  The combination is not the union of capabilities —\n");
    printf("  it is a new primitive whose characteristic operation\n");
    printf("  (bisimulation-quotient) does not exist in either axis\n");
    printf("  alone. This is the defining test for a combination\n");
    printf("  cell in the taxonomy.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("MODAL × QUOTIENT: bisimulation-quotient Kripke frames\n");
    printf("══════════════════════════════════════════\n");
    printf("Second combination primitive (after thermo_reversible).\n");

    experiment_bisim();
    experiment_preservation();
    experiment_compression();
    experiment_witness();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Bisimulation as fixed-point refinement of a\n");
    printf("     partition on worlds\n");
    printf("  2. Quotient frame: worlds → bisimulation classes\n");
    printf("  3. Modal formulas preserved exactly under quotient\n");
    printf("     (Hennessy-Milner theorem)\n");
    printf("  4. Compression: 8-world frame → 2 classes (4× reduction)\n");
    printf("     with no loss of modal information\n");
    printf("  5. Irreducibility to either axis alone: pure modal\n");
    printf("     cannot merge, pure quotient has no modal structure\n");
    printf("\n  Combination cell: MODAL × QUOTIENT\n");
    printf("  Meta-groups: RELATION × VALUE\n");
    return 0;
}
