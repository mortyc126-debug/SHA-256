/*
 * COMBINATION CATALOGUE
 * =========================
 *
 * Meta-file listing every primitive cell constructed in the
 * programme: 17 single axes, 4 pair combinations, 1 triple,
 * plus an explicit list of open combination cells worth
 * investigating in future.
 *
 * The catalogue does three things:
 *
 *   1. Enumerates built cells with their characteristic
 *      operation and file reference.
 *   2. Prints a coverage matrix over pairs of meta-groups
 *      (VALUE, OPERATION, RELATION, TIME) showing which
 *      have representative combination cells.
 *   3. Lists 'honourable mentions' — pair cells that look
 *      mathematically natural but have not been built yet,
 *      giving future-work direction.
 *
 * No new math is invented here. This is a navigation
 * document for the 50+ files in the branch.
 *
 * Compile: gcc -O3 -march=native -o catalogue comb_catalogue.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ═══ META-GROUPS ═══ */
typedef enum {MG_VALUE, MG_OPERATION, MG_RELATION, MG_TIME, MG_NONE} Meta;
static const char *meta_names[5] = {"VALUE", "OPERATION", "RELATION", "TIME", "—"};
static const char *meta_short[5] = {"VAL", "OP",        "REL",      "TIME", "-"};

/* ═══ CELL RECORD ═══ */
typedef struct {
    const char *name;             /* short label */
    int        arity;             /* 1 = single, 2 = pair, 3 = triple */
    const char *axes[3];          /* up to 3 axis names */
    Meta       metas[3];          /* up to 3 meta-groups */
    const char *characteristic;   /* signature operation */
    const char *file;             /* source file */
} Cell;

/* ═══ SINGLE AXES (17) ═══ */
static Cell singles[] = {
    /* VALUE */
    {"binary",      1, {"binary",      NULL, NULL}, {MG_VALUE,     MG_NONE, MG_NONE}, "XOR, AND, OR",                             "(implicit)"},
    {"phase",       1, {"phase",       NULL, NULL}, {MG_VALUE,     MG_NONE, MG_NONE}, "interference, exact removal",              "phase_bits.c"},
    {"ebit/ghz",    1, {"ebit/ghz",    NULL, NULL}, {MG_VALUE,     MG_NONE, MG_NONE}, "non-factorisable correlation",             "ebit_pairs.c, ghz_triples.c"},
    {"probability", 1, {"probability", NULL, NULL}, {MG_VALUE,     MG_NONE, MG_NONE}, "Bayes update, entropy, BSC capacity",      "prob_bits.c"},
    {"quotient",    1, {"quotient",    NULL, NULL}, {MG_VALUE,     MG_NONE, MG_NONE}, "equivalence class canonicalisation",       "quotient_bits.c"},

    /* OPERATION */
    {"reversible",  1, {"reversible",  NULL, NULL}, {MG_OPERATION, MG_NONE, MG_NONE}, "Toffoli/Fredkin self-inverse",             "reversible_bits.c"},
    {"linear",      1, {"linear",      NULL, NULL}, {MG_OPERATION, MG_NONE, MG_NONE}, "single-use resource budget",               "linear_bits.c"},
    {"self-ref",    1, {"self-ref",    NULL, NULL}, {MG_OPERATION, MG_NONE, MG_NONE}, "fixed-point b = f(b)",                     "selfref_bits.c"},
    {"higher-order",1, {"higher-order",NULL, NULL}, {MG_OPERATION, MG_NONE, MG_NONE}, "function as primitive (Church)",           "church_bits.c"},
    {"cost",        1, {"cost",        NULL, NULL}, {MG_OPERATION, MG_NONE, MG_NONE}, "Ising ground state, Landauer accounting",  "cost_bits.c"},

    /* RELATION */
    {"braid",       1, {"braid",       NULL, NULL}, {MG_RELATION,  MG_NONE, MG_NONE}, "Yang-Baxter, Burau, Alexander poly",       "braid_bits.c, braid_jones.c"},
    {"modal",       1, {"modal",       NULL, NULL}, {MG_RELATION,  MG_NONE, MG_NONE}, "Kripke □/◇ on accessibility frames",      "modal_bits.c"},
    {"relational",  1, {"relational",  NULL, NULL}, {MG_RELATION,  MG_NONE, MG_NONE}, "composition, transitive closure",          "relational_bits.c"},
    {"causal",      1, {"causal",      NULL, NULL}, {MG_RELATION,  MG_NONE, MG_NONE}, "topo-sort, Pearl do-calculus",             "causal_bits.c"},

    /* TIME */
    {"stream",      1, {"stream",      NULL, NULL}, {MG_TIME,      MG_NONE, MG_NONE}, "shift+XOR F_2-module, cellular automata", "stream_bits.c"},
    {"interval",    1, {"interval",    NULL, NULL}, {MG_TIME,      MG_NONE, MG_NONE}, "Allen's 13 temporal relations",            "interval_bits.c"},
    {"cyclic",      1, {"cyclic",      NULL, NULL}, {MG_TIME,      MG_NONE, MG_NONE}, "Z/P rotation group action",                "cyclic_bits.c"},
    {"branching",   1, {"branching",   NULL, NULL}, {MG_TIME,      MG_NONE, MG_NONE}, "CTL path quantifiers EF/AF/EG/AG",         "branching_bits.c"},
};
static int n_singles = sizeof(singles) / sizeof(Cell);

/* ═══ PAIR COMBINATION CELLS (4) ═══ */
static Cell pairs[] = {
    {"reversible × cost",
     2, {"reversible", "cost",      NULL}, {MG_OPERATION, MG_OPERATION, MG_NONE},
     "Landauer bound as structural law (C_rev(τ) = 1/τ, C_irr(τ) = 1 + 1/τ)",
     "thermo_reversible.c"},

    {"modal × quotient",
     2, {"modal",      "quotient",  NULL}, {MG_RELATION,  MG_VALUE,     MG_NONE},
     "bisimulation-quotient preserves modal formulas (Hennessy-Milner)",
     "modal_quotient.c"},

    {"causal × cost",
     2, {"causal",     "cost",      NULL}, {MG_RELATION,  MG_OPERATION, MG_NONE},
     "total_influence = sum over directed paths of edge-weight product (Wright 1921)",
     "causal_cost.c"},

    {"stream × linear",
     2, {"stream",     "linear",    NULL}, {MG_TIME,      MG_OPERATION, MG_NONE},
     "temporal budget evolution: decay, deadline, replenish, rate limit",
     "stream_linear.c"},
};
static int n_pairs = sizeof(pairs) / sizeof(Cell);

/* ═══ TRIPLE COMBINATION CELL (1) ═══ */
static Cell triples[] = {
    {"reversible × linear × cost",
     3, {"reversible", "linear", "cost"}, {MG_OPERATION, MG_OPERATION, MG_OPERATION},
     "bounded adiabatic computation; speed vs energy vs budget trade-off",
     "triple_rlc.c"},
};
static int n_triples = sizeof(triples) / sizeof(Cell);

/* ═══ HONOURABLE MENTIONS — pair cells not yet built ═══ */
typedef struct {
    const char *name;
    const char *axes[2];
    Meta metas[2];
    const char *candidate_operation;
} OpenCell;

static OpenCell open_cells[] = {
    /* VAL × VAL */
    {"ebit × quotient", {"ebit/ghz", "quotient"}, {MG_VALUE, MG_VALUE},
     "quotient over Bell-state equivalence; Schmidt rank as canonical form"},
    {"phase × probability", {"phase", "probability"}, {MG_VALUE, MG_VALUE},
     "Wigner quasi-probability distributions (real, not complex)"},

    /* VAL × OP */
    {"probability × linear", {"probability", "linear"}, {MG_VALUE, MG_OPERATION},
     "Bayesian resource: distributions with consumption budget"},
    {"phase × linear", {"phase", "linear"}, {MG_VALUE, MG_OPERATION},
     "phase-bit memory with exact removal plus budget"},
    {"probability × cost", {"probability", "cost"}, {MG_VALUE, MG_OPERATION},
     "weighted expected energy, free energy minimisation"},

    /* VAL × TIME */
    {"probability × stream", {"probability", "stream"}, {MG_VALUE, MG_TIME},
     "Markov chain as primitive (distributions evolving over time)"},
    {"phase × stream", {"phase", "stream"}, {MG_VALUE, MG_TIME},
     "signed temporal sequences, discrete Fourier of streams"},

    /* REL × REL */
    {"causal × modal", {"causal", "modal"}, {MG_RELATION, MG_RELATION},
     "modal logic over causal DAGs: temporal modal logic (Pnueli 1977)"},
    {"braid × relational", {"braid", "relational"}, {MG_RELATION, MG_RELATION},
     "relational reasoning over braided morphisms (braided categories)"},

    /* REL × TIME */
    {"causal × stream", {"causal", "stream"}, {MG_RELATION, MG_TIME},
     "event-based causal streams (logical clocks, Lamport 1978)"},
    {"causal × interval", {"causal", "interval"}, {MG_RELATION, MG_TIME},
     "causal dependencies over Allen intervals"},

    /* OP × TIME */
    {"reversible × stream", {"reversible", "stream"}, {MG_OPERATION, MG_TIME},
     "reversible cellular automata (Toffoli 1977)"},
    {"cost × cyclic", {"cost", "cyclic"}, {MG_OPERATION, MG_TIME},
     "energy on periodic oscillators, phase transitions on ring"},

    /* TIME × TIME */
    {"stream × cyclic", {"stream", "cyclic"}, {MG_TIME, MG_TIME},
     "aperiodic base + periodic carrier = almost-periodic sequences"},
    {"interval × branching", {"interval", "branching"}, {MG_TIME, MG_TIME},
     "interval-based CTL, duration of branching futures"},

    /* OP × OP (beyond rev × cost) */
    {"linear × self-ref", {"linear", "self-ref"}, {MG_OPERATION, MG_OPERATION},
     "budget-bounded recursion, termination by resource exhaustion"},
    {"higher-order × cost", {"higher-order", "cost"}, {MG_OPERATION, MG_OPERATION},
     "call-by-value complexity of Church terms (β-reduction cost)"},

    /* VAL × REL (beyond modal × quotient) */
    {"ebit × causal", {"ebit/ghz", "causal"}, {MG_VALUE, MG_RELATION},
     "entangled state with causal ordering; quantum causal network analogue"},
};
static int n_open_cells = sizeof(open_cells) / sizeof(OpenCell);

/* ═══ PRINTING ═══ */
static void print_cell_row(const Cell *c){
    /* Build the arity field */
    const char *ar = c->arity == 1 ? "single" : c->arity == 2 ? "pair  " : "triple";
    /* Build the meta field */
    char meta_buf[64] = "";
    for(int i = 0; i < c->arity; i++){
        strcat(meta_buf, meta_short[c->metas[i]]);
        if(i < c->arity - 1) strcat(meta_buf, "×");
    }
    printf("  [%s] %-30s  [%-10s]\n", ar, c->name, meta_buf);
    printf("      op: %s\n", c->characteristic);
    printf("      file: %s\n", c->file);
}

static void print_section(const char *title, Cell *cells, int n){
    printf("\n──────────────────────────────────────────\n");
    printf("  %s (%d)\n", title, n);
    printf("──────────────────────────────────────────\n");
    for(int i = 0; i < n; i++){
        print_cell_row(&cells[i]);
    }
}

/* Coverage matrix: how many pair cells in each meta × meta cell */
static void print_coverage(void){
    printf("\n──────────────────────────────────────────\n");
    printf("  META-GROUP COVERAGE (pairs and triples)\n");
    printf("──────────────────────────────────────────\n\n");

    int coverage[4][4] = {{0}};
    for(int i = 0; i < n_pairs; i++){
        int a = pairs[i].metas[0];
        int b = pairs[i].metas[1];
        if(a > b){int t = a; a = b; b = t;}
        coverage[a][b]++;
    }
    for(int i = 0; i < n_triples; i++){
        /* Count each pair within the triple */
        int m[3] = {triples[i].metas[0], triples[i].metas[1], triples[i].metas[2]};
        for(int x = 0; x < 3; x++)
            for(int y = x+1; y < 3; y++){
                int a = m[x], b = m[y];
                if(a > b){int t = a; a = b; b = t;}
                coverage[a][b]++;
            }
    }

    printf("         ");
    for(int j = 0; j < 4; j++) printf(" %-6s", meta_short[j]);
    printf("\n");
    for(int i = 0; i < 4; i++){
        printf("  %-6s ", meta_short[i]);
        for(int j = 0; j < 4; j++){
            if(j < i) printf("   .   ");
            else      printf("   %d   ", coverage[i][j]);
        }
        printf("\n");
    }

    /* Count filled vs empty pair cells */
    int filled = 0, empty = 0;
    for(int i = 0; i < 4; i++) for(int j = i; j < 4; j++){
        if(coverage[i][j] > 0) filled++;
        else empty++;
    }
    printf("\n  Meta-group pair cells filled:  %d / 10\n", filled);
    printf("  Meta-group pair cells empty:   %d / 10\n", empty);
}

/* Open cells section */
static void print_open(void){
    printf("\n──────────────────────────────────────────\n");
    printf("  OPEN COMBINATION CELLS (%d candidates)\n", n_open_cells);
    printf("──────────────────────────────────────────\n");
    for(int i = 0; i < n_open_cells; i++){
        printf("  %-26s  [%s × %s]\n",
               open_cells[i].name,
               meta_short[open_cells[i].metas[0]],
               meta_short[open_cells[i].metas[1]]);
        printf("      candidate op: %s\n", open_cells[i].candidate_operation);
    }
}

/* Statistics */
static void print_stats(void){
    printf("\n──────────────────────────────────────────\n");
    printf("  STATISTICS\n");
    printf("──────────────────────────────────────────\n\n");

    /* Total pair cells and triple cells possible over 17 axes */
    int n_axes = 17;
    int n_pair_possible = n_axes * (n_axes - 1) / 2;
    int n_triple_possible = n_axes * (n_axes - 1) * (n_axes - 2) / 6;

    printf("  Single axes (native independent):  %d / ~17\n", n_singles);
    printf("  Pair cells built:                  %d\n", n_pairs);
    printf("  Pair cells candidates catalogued:  %d\n", n_open_cells);
    printf("  Pair cells possible (C(17,2)):     %d\n", n_pair_possible);
    printf("  Triple cells built:                %d\n", n_triples);
    printf("  Triple cells possible (C(17,3)):   %d\n", n_triple_possible);
    printf("\n  Coverage ratio (built / possible):\n");
    printf("    pairs:   %.2f%%\n", 100.0 * n_pairs / n_pair_possible);
    printf("    triples: %.2f%%\n", 100.0 * n_triples / n_triple_possible);

    printf("\n  The programme has explored a small fraction of the\n");
    printf("  combinatorial space. The catalogue is a navigation\n");
    printf("  snapshot, not a completeness claim.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("COMBINATION CATALOGUE: navigation snapshot\n");
    printf("══════════════════════════════════════════\n");
    printf("Index of all primitive cells built in the programme,\n");
    printf("plus candidates for future construction.\n");

    print_section("SINGLE AXES", singles, n_singles);
    print_section("PAIR COMBINATION CELLS", pairs, n_pairs);
    print_section("TRIPLE COMBINATION CELLS", triples, n_triples);
    print_coverage();
    print_open();
    print_stats();

    printf("\n──────────────────────────────────────────\n");
    printf("  HOW TO USE THIS CATALOGUE\n");
    printf("──────────────────────────────────────────\n\n");
    printf("  1. Pick a meta-group pair from the coverage matrix.\n");
    printf("  2. Look at the open-cells section for that pair.\n");
    printf("  3. Choose a combination with a specified candidate\n");
    printf("     operation.\n");
    printf("  4. Build it as a new file, following the pattern of\n");
    printf("     the existing combination files.\n");
    printf("  5. Update this catalogue with the new cell entry.\n");
    printf("\n  The 'defining operation' test: a combination is\n");
    printf("  non-trivial iff its characteristic operation cannot\n");
    printf("  be expressed in any of its component axes alone.\n");
    return 0;
}
