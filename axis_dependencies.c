/*
 * AXIS DEPENDENCIES: 12 × 12 simulation matrix
 * ===============================================
 *
 * For every ordered pair (X, Y) of the twelve bit-primitive axes
 * we assess whether X can SIMULATE Y and at what level:
 *
 *     2  native   — Y's distinguishing operations are directly
 *                   available in X without further construction
 *     1  encoded  — Y can be expressed inside X via a non-trivial
 *                   construction (an interpreter, an encoding, etc.)
 *     0  none     — no known simulation, or structural obstruction
 *
 * All entries are hand-assigned from the mathematical literature
 * plus the experiments in this repo.  They are deliberately
 * conservative: if I am not certain of a simulation at level 2,
 * I mark 1; if not certain of any simulation, I mark 0.
 *
 * From the matrix we compute:
 *
 *   - transitive closure (which axes reach which)
 *   - minimal elements (axes that nothing else simulates except
 *     the trivial binary baseline)
 *   - maximal elements (axes that simulate many others)
 *   - proposed MINIMAL BASIS: a set of axes whose closure is all 12
 *
 * Compile: gcc -O3 -march=native -o deps axis_dependencies.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define N_AXES 12

static const char *names[N_AXES] = {
    "binary",   /*  0 */
    "phase",    /*  1 */
    "ebit",     /*  2 */
    "prob",     /*  3 */
    "rev",      /*  4 */
    "stream",   /*  5 */
    "braid",    /*  6 */
    "linear",   /*  7 */
    "selfref",  /*  8 */
    "church",   /*  9 */
    "modal",    /* 10 */
    "relat"     /* 11 */
};

enum {BIN=0, PHA, EBI, PRO, REV, STR, BRA, LIN, SEL, CHU, MOD, REL};

/* M[i][j] = level at which axis i simulates axis j.
 * Row = simulator, Column = target. */
static int M[N_AXES][N_AXES];

static void set_matrix(void){
    memset(M, 0, sizeof(M));
    /* Diagonal: self-simulation is trivially native */
    for(int i = 0; i < N_AXES; i++) M[i][i] = 2;

    /* Everyone simulates binary natively (binary is embedded as
     * a subset of every primitive's state space). */
    for(int i = 0; i < N_AXES; i++) M[i][BIN] = 2;

    /* Tight natively-contained inclusions from the experiments: */
    /* phase contains prob (non-negative amplitudes = distributions) */
    M[PHA][PRO] = 2;
    /* ebit contains phase (single-bit ebit ≡ 2-d phase HDV) */
    M[EBI][PHA] = 2;
    /* ebit contains prob (transitively, non-negative 4-d amplitudes) */
    M[EBI][PRO] = 2;
    /* braid contains phase (Burau evaluated at integer t gives phases) */
    M[BRA][PHA] = 2;

    /* Encoded (level 1) simulations that require a non-trivial
     * construction but are mathematically standard: */

    /* Church / higher-order: lambda calculus is Turing-complete.
     * Every computable primitive can be encoded as a closure.
     * We mark native where the target IS a function and encoded
     * where an interpreter is needed. */
    M[CHU][SEL] = 1;   /* Y-combinator gives fixed points */
    M[CHU][REL] = 2;   /* a relation is a 2-arg predicate; native */
    M[CHU][MOD] = 1;   /* Kripke model as nested functions */
    M[CHU][LIN] = 1;   /* linear types as restricted Church terms */
    M[CHU][REV] = 1;   /* reversible circuits as terms */
    M[CHU][STR] = 1;   /* streams as lazy λ-terms */
    M[CHU][BRA] = 1;   /* braid groups as Church-encoded group terms */
    M[CHU][PHA] = 1;   /* phase as signed lambda terms */
    M[CHU][EBI] = 1;   /* ebits via pair encoding */
    M[CHU][PRO] = 1;   /* prob as weight-carrying closures */

    /* Linear logic ↔ reversible via budget interpretation
     * (Girard, Abramsky — loosely). */
    M[LIN][REV] = 1;

    /* Reversible is itself linear: every wire is used once by default
     * in a reversible circuit if we don't fanout. */
    M[REV][LIN] = 1;

    /* Modal S4 via !A in linear logic (known result). */
    M[LIN][MOD] = 1;
    M[MOD][LIN] = 1;

    /* Stream bits (rule 110) are Turing-complete, so in principle
     * they encode everything. This is an INTERPRETATION, not a
     * primitive containment. */
    M[STR][CHU] = 1;
    M[STR][REL] = 1;
    M[STR][MOD] = 1;
    M[STR][SEL] = 1;
    M[STR][LIN] = 1;
    M[STR][REV] = 1;
    M[STR][BRA] = 1;
    M[STR][PHA] = 1;
    M[STR][EBI] = 1;
    M[STR][PRO] = 1;

    /* Relational bits can encode graphs on which all previous
     * structures are built; this is closer to encoding than native,
     * so level 1 for most but not all. */
    M[REL][MOD] = 1;   /* Kripke frames ARE relations — almost native */

    /* Modal bits: the accessibility relation IS a relation, giving
     * natural access to relational primitives at least in one
     * direction. */
    M[MOD][REL] = 1;

    /* Self-ref contains pure functions implicitly (a fixed point
     * of f = f is a function of arity 0). But in general self-ref
     * doesn't subsume Church unless we already have lambdas. */

    /* ebit → ghz is upward in the amplitude hierarchy; already
     * covered by ebit's self entry since we conflate them here. */
}

/* Transitive closure via repeated matrix 'max-composition'. */
static void transitive_closure(int T[N_AXES][N_AXES]){
    for(int i = 0; i < N_AXES; i++) for(int j = 0; j < N_AXES; j++) T[i][j] = M[i][j];
    int changed = 1;
    while(changed){
        changed = 0;
        for(int i = 0; i < N_AXES; i++)
            for(int j = 0; j < N_AXES; j++){
                int best = T[i][j];
                for(int k = 0; k < N_AXES; k++){
                    int via = (T[i][k] && T[k][j]) ?
                              (T[i][k] < T[k][j] ? T[i][k] : T[k][j]) : 0;
                    if(via > best){best = via; changed = 1;}
                }
                T[i][j] = best;
            }
    }
}

static void print_matrix(const char *title, int A[N_AXES][N_AXES]){
    printf("\n%s\n", title);
    printf("   ");
    for(int j = 0; j < N_AXES; j++) printf(" %-7s", names[j]);
    printf("\n");
    for(int i = 0; i < N_AXES; i++){
        printf("%-8s", names[i]);
        for(int j = 0; j < N_AXES; j++){
            const char *sym;
            if(A[i][j] == 2) sym = "  N ";      /* native */
            else if(A[i][j] == 1) sym = "  e ";  /* encoded */
            else if(i == j)   sym = "  . ";      /* self diag if 0 somehow */
            else              sym = "  - ";      /* none */
            printf(" %-7s", sym);
        }
        printf("\n");
    }
    printf("  Legend:  N native   e encoded   − none\n");
}

static void report_minimality(int T[N_AXES][N_AXES]){
    printf("\n══════════════════════════════════════════\n");
    printf("COVERAGE REPORT (from transitive closure)\n");
    printf("══════════════════════════════════════════\n\n");

    printf("  For each axis, list of axes it can reach (native ∪ encoded):\n\n");
    for(int i = 0; i < N_AXES; i++){
        int n_native = 0, n_enc = 0;
        printf("  %-8s native: {", names[i]);
        int first = 1;
        for(int j = 0; j < N_AXES; j++){
            if(T[i][j] == 2){
                if(!first) printf(", ");
                printf("%s", names[j]);
                first = 0;
                n_native++;
            }
        }
        printf("}\n");
        printf("           encoded additionally: {");
        first = 1;
        for(int j = 0; j < N_AXES; j++){
            if(T[i][j] == 1){
                if(!first) printf(", ");
                printf("%s", names[j]);
                first = 0;
                n_enc++;
            }
        }
        printf("}   total coverage %d/%d\n", n_native + n_enc, N_AXES);
    }
}

static void report_minimal_basis(int T[N_AXES][N_AXES]){
    printf("\n══════════════════════════════════════════\n");
    printf("PROPOSED MINIMAL BASIS (greedy set cover)\n");
    printf("══════════════════════════════════════════\n\n");

    int covered[N_AXES] = {0};
    int basis[N_AXES], nb = 0;

    while(1){
        /* Find axis covering the most uncovered targets. */
        int best = -1, best_gain = 0;
        for(int i = 0; i < N_AXES; i++){
            int gain = 0;
            for(int j = 0; j < N_AXES; j++)
                if(!covered[j] && T[i][j] > 0) gain++;
            if(gain > best_gain){best_gain = gain; best = i;}
        }
        if(best < 0 || best_gain == 0) break;
        basis[nb++] = best;
        for(int j = 0; j < N_AXES; j++)
            if(T[best][j] > 0) covered[j] = 1;
        int n_cov = 0;
        for(int j = 0; j < N_AXES; j++) if(covered[j]) n_cov++;
        printf("  + %-8s  covers %2d new, total %2d/12\n",
               names[best], best_gain, n_cov);
        if(n_cov == N_AXES) break;
    }

    printf("\n  Minimal basis (greedy): {");
    for(int i = 0; i < nb; i++){
        printf("%s%s", names[basis[i]], (i < nb - 1) ? ", " : "");
    }
    printf("}\n");
    printf("  Size: %d axes suffice to reach all 12 under simulation.\n", nb);
}

static void report_independence(int T[N_AXES][N_AXES]){
    printf("\n══════════════════════════════════════════\n");
    printf("INDEPENDENCE REPORT\n");
    printf("══════════════════════════════════════════\n\n");

    printf("  An axis X is INDEPENDENT if no other axis simulates X\n");
    printf("  natively (except binary, which is universally embedded).\n\n");

    int indep[N_AXES] = {0};
    for(int j = 0; j < N_AXES; j++){
        if(j == BIN) continue;
        int someone_simulates = 0;
        for(int i = 0; i < N_AXES; i++){
            if(i == j) continue;
            if(T[i][j] == 2){someone_simulates = 1; break;}
        }
        indep[j] = !someone_simulates;
    }

    printf("  Natively independent axes (nothing else contains them):\n");
    int n = 0;
    for(int j = 0; j < N_AXES; j++) if(indep[j]){
        printf("    - %s\n", names[j]);
        n++;
    }
    printf("  Count: %d\n\n", n);

    printf("  Axes simulated natively by something else:\n");
    for(int j = 0; j < N_AXES; j++) if(!indep[j] && j != BIN){
        printf("    %s  ← ", names[j]);
        int first = 1;
        for(int i = 0; i < N_AXES; i++){
            if(i == j) continue;
            if(T[i][j] == 2){
                if(!first) printf(", ");
                printf("%s", names[i]);
                first = 0;
            }
        }
        printf("\n");
    }
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("AXIS DEPENDENCIES: 12 × 12 simulation matrix\n");
    printf("══════════════════════════════════════════\n");
    printf("Entries: N = native, e = encoded, − = none.\n");

    set_matrix();
    print_matrix("Direct simulation matrix (hand-assigned):", M);

    int T[N_AXES][N_AXES];
    transitive_closure(T);
    print_matrix("Transitive closure:", T);

    report_minimality(T);
    report_minimal_basis(T);
    report_independence(T);

    printf("\n══════════════════════════════════════════\n");
    printf("INTERPRETATION\n");
    printf("══════════════════════════════════════════\n\n");
    printf("  The simulation matrix is sparse. Most axes contain\n");
    printf("  nothing natively except themselves and binary. Two\n");
    printf("  axes stand out as broadly-containing:\n\n");
    printf("    - CHURCH / higher-order: universal by lambda\n");
    printf("      calculus. Contains everything at level ≥ 1.\n");
    printf("    - STREAM (rule 110): Turing-complete; also reaches\n");
    printf("      everything via encoding.\n\n");
    printf("  The two 'universal' axes reduce the minimal basis to\n");
    printf("  a very small set. But that does NOT mean the other\n");
    printf("  axes are redundant: they give NATIVE algebraic\n");
    printf("  structure that encoded versions lack.\n\n");
    printf("  A useful analogy: Turing machines can simulate\n");
    printf("  quantum circuits too (slowly), but we still study\n");
    printf("  the native quantum primitives because the structure\n");
    printf("  is different.\n");
    return 0;
}
