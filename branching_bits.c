/*
 * BRANCHING BITS: CTL temporal logic with path quantifiers
 * ============================================================
 *
 * Candidate fourth TIME axis (after stream, interval, cyclic),
 * testing the hypothesis that TIME is rich enough to fill the
 * meta-group to the same size as VALUE and OPERATION (5 axes).
 *
 * Based on Computation Tree Logic (Clarke-Emerson 1981). A
 * branching bit lives on a state-transition graph where each
 * state has zero or more NEXT states. Time is not linear: at
 * every moment, multiple futures are possible.
 *
 * CTL operators combine path quantifiers with temporal
 * modalities:
 *
 *     EX p         exists next state where p holds
 *     AX p         all next states have p
 *     EF p         exists path along which p eventually holds
 *     AF p         all paths eventually reach p
 *     EG p         exists path along which p always holds
 *     AG p         all paths always have p
 *     E[p U q]     exists path where p holds until q
 *     A[p U q]     all paths have p holding until q
 *
 * Distinction from the previous three TIME axes:
 *
 *   - STREAM is LINEAR time with one future per moment.
 *     Cannot express 'all possible futures' or 'some future'.
 *   - INTERVAL has temporal extent but no branching.
 *   - CYCLIC is a closed loop; every moment has exactly one
 *     successor (the next point on the circle).
 *   - BRANCHING allows multiple futures per moment, and the
 *     characteristic operations are PATH QUANTIFIERS.
 *
 * Distinction from modal bits:
 *
 *   - Modal has □p (necessarily p) and ◇p (possibly p), but
 *     both are SINGLE-STEP operators equivalent to AX and EX.
 *   - Modal cannot express 'eventually' (AF, EF) or 'always'
 *     (AG, EG) — these require fixed-point reasoning over
 *     arbitrary path lengths.
 *
 * Experiments:
 *
 *   1. Simple state machine with branching. Evaluate EX, AX.
 *   2. Fixed-point computation of EF (reachability).
 *   3. AF requires the μ-calculus fixed point: AF p = p ∨ AX AF p.
 *      Verify on a small example.
 *   4. EG requires a different fixed point: EG p = p ∧ EX EG p.
 *   5. Witness: modal cannot express EF; only EX. Verify on a
 *      frame where the difference matters.
 *
 * Compile: gcc -O3 -march=native -o branch branching_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define MAX_S 16

/* ═══ TRANSITION SYSTEM ═══ */
typedef struct {
    int n;                 /* number of states */
    int next[MAX_S][MAX_S];/* next[i][j] = 1 iff i → j */
    int prop[MAX_S];       /* proposition p at each state */
} Kripke;

static void k_init(Kripke *k, int n){
    k->n = n;
    memset(k->next, 0, sizeof(k->next));
    memset(k->prop, 0, sizeof(k->prop));
}

static void k_add(Kripke *k, int i, int j){k->next[i][j] = 1;}

static void k_print(const char *name, const Kripke *k){
    printf("  %s (n = %d)\n", name, k->n);
    printf("    p:    ");
    for(int i = 0; i < k->n; i++) printf("%d ", k->prop[i]);
    printf("\n");
    printf("    edges: ");
    int any = 0;
    for(int i = 0; i < k->n; i++)
        for(int j = 0; j < k->n; j++)
            if(k->next[i][j]){
                printf("%s%d→%d", any ? ", " : "", i, j);
                any = 1;
            }
    printf("\n");
}

/* A CTL formula evaluates to a SET of states where it holds. */
typedef int StateSet[MAX_S];

static void set_clear(StateSet s){memset(s, 0, sizeof(StateSet));}
static void set_full(StateSet s, int n){for(int i = 0; i < n; i++) s[i] = 1;}
static void set_copy(StateSet d, const StateSet s){memcpy(d, s, sizeof(StateSet));}
static int set_eq(const StateSet a, const StateSet b, int n){
    for(int i = 0; i < n; i++) if(a[i] != b[i]) return 0;
    return 1;
}
static void set_and(StateSet out, const StateSet a, const StateSet b, int n){
    for(int i = 0; i < n; i++) out[i] = a[i] && b[i];
}
static void set_or(StateSet out, const StateSet a, const StateSet b, int n){
    for(int i = 0; i < n; i++) out[i] = a[i] || b[i];
}

static void set_from_prop(StateSet out, const Kripke *k){
    for(int i = 0; i < k->n; i++) out[i] = k->prop[i];
}

/* ═══ CTL OPERATORS ═══ */

/* EX φ: exists next state where φ */
static void ctl_EX(StateSet out, const StateSet phi, const Kripke *k){
    set_clear(out);
    for(int i = 0; i < k->n; i++){
        for(int j = 0; j < k->n; j++){
            if(k->next[i][j] && phi[j]){out[i] = 1; break;}
        }
    }
}

/* AX φ: all next states have φ.  Note: states with NO successors
 * vacuously satisfy AX φ. */
static void ctl_AX(StateSet out, const StateSet phi, const Kripke *k){
    set_clear(out);
    for(int i = 0; i < k->n; i++){
        int ok = 1;
        for(int j = 0; j < k->n; j++){
            if(k->next[i][j] && !phi[j]){ok = 0; break;}
        }
        out[i] = ok;
    }
}

/* EF φ = μZ. φ ∨ EX Z   (least fixed point) */
static void ctl_EF(StateSet out, const StateSet phi, const Kripke *k){
    set_clear(out);
    StateSet prev;
    set_copy(out, phi);
    int iter = 0;
    while(iter++ < 100){
        set_copy(prev, out);
        StateSet ex_z;
        ctl_EX(ex_z, out, k);
        set_or(out, phi, ex_z, k->n);
        if(set_eq(out, prev, k->n)) break;
    }
}

/* AF φ = μZ. φ ∨ AX Z   (least fixed point) */
static void ctl_AF(StateSet out, const StateSet phi, const Kripke *k){
    set_clear(out);
    StateSet prev;
    set_copy(out, phi);
    int iter = 0;
    while(iter++ < 100){
        set_copy(prev, out);
        StateSet ax_z;
        ctl_AX(ax_z, out, k);
        set_or(out, phi, ax_z, k->n);
        if(set_eq(out, prev, k->n)) break;
    }
}

/* EG φ = νZ. φ ∧ EX Z   (greatest fixed point) */
static void ctl_EG(StateSet out, const StateSet phi, const Kripke *k){
    StateSet prev;
    set_full(out, k->n);
    set_and(out, out, phi, k->n);
    int iter = 0;
    while(iter++ < 100){
        set_copy(prev, out);
        StateSet ex_z;
        ctl_EX(ex_z, out, k);
        set_and(out, phi, ex_z, k->n);
        if(set_eq(out, prev, k->n)) break;
    }
}

/* AG φ = νZ. φ ∧ AX Z   (greatest fixed point) */
static void ctl_AG(StateSet out, const StateSet phi, const Kripke *k){
    StateSet prev;
    set_full(out, k->n);
    set_and(out, out, phi, k->n);
    int iter = 0;
    while(iter++ < 100){
        set_copy(prev, out);
        StateSet ax_z;
        ctl_AX(ax_z, out, k);
        set_and(out, phi, ax_z, k->n);
        if(set_eq(out, prev, k->n)) break;
    }
}

static void set_print(const char *name, const StateSet s, int n){
    printf("  %-10s = {", name);
    int first = 1;
    for(int i = 0; i < n; i++){
        if(s[i]){
            if(!first) printf(", ");
            printf("%d", i);
            first = 0;
        }
    }
    printf("}\n");
}

/* ═══ EXPERIMENT 1: EX and AX on branching tree ═══ */
static void experiment_single_step(void){
    printf("\n═══ EXPERIMENT 1: Single-step operators EX / AX ═══\n\n");

    /* State machine: 0 is the root with branches to 1, 2, 3.
     * 1 has p=1, 2 has p=1, 3 has p=0. All leaves are dead ends. */
    Kripke k; k_init(&k, 4);
    k.prop[0] = 0; k.prop[1] = 1; k.prop[2] = 1; k.prop[3] = 0;
    k_add(&k, 0, 1);
    k_add(&k, 0, 2);
    k_add(&k, 0, 3);
    k_print("state machine", &k);

    StateSet phi;
    set_from_prop(phi, &k);
    set_print("p         ", phi, k.n);

    StateSet ex_p, ax_p;
    ctl_EX(ex_p, phi, &k);
    ctl_AX(ax_p, phi, &k);
    set_print("EX p      ", ex_p, k.n);
    set_print("AX p      ", ax_p, k.n);

    printf("\n  EX p = {0} — root has SOME next state with p (state 1 or 2)\n");
    printf("  AX p = {1, 2, 3} — the leaves vacuously satisfy AX p\n");
    printf("         (no successors, so 'all' holds trivially).\n");
    printf("  Root is NOT in AX p because state 3 has p=0.\n");
}

/* ═══ EXPERIMENT 2: EF — reachability as fixed point ═══ */
static void experiment_EF(void){
    printf("\n═══ EXPERIMENT 2: EF p — reachability via fixed point ═══\n\n");

    Kripke k; k_init(&k, 6);
    k.prop[5] = 1;   /* only state 5 has p */
    k_add(&k, 0, 1);
    k_add(&k, 1, 2);
    k_add(&k, 2, 3);
    k_add(&k, 3, 4);
    k_add(&k, 4, 5);
    k_add(&k, 0, 3); /* shortcut: 0 → 3 */

    k_print("state machine", &k);

    StateSet phi;
    set_from_prop(phi, &k);
    set_print("p         ", phi, k.n);

    StateSet ef_p;
    ctl_EF(ef_p, phi, &k);
    set_print("EF p      ", ef_p, k.n);

    printf("\n  EF p contains every state from which state 5 is reachable.\n");
    printf("  All of 0..5 can reach 5, so EF p = {0,1,2,3,4,5}.\n");
    printf("  Computed as the least fixed point of p ∨ EX Z — started\n");
    printf("  with {5}, grew to {4,5}, then {3,4,5}, etc.\n");
}

/* ═══ EXPERIMENT 3: AF vs EF ═══ */
static void experiment_AF(void){
    printf("\n═══ EXPERIMENT 3: AF p — all paths reach p ═══\n\n");

    /* State 0 branches to 1 (good) and 2 (bad loop).
     * State 1 → 3 → (loop back).
     * State 2 → 2 (self-loop — infinite bad path without p).
     * Only state 1 has p. */
    Kripke k; k_init(&k, 4);
    k.prop[1] = 1;
    k_add(&k, 0, 1);
    k_add(&k, 0, 2);
    k_add(&k, 1, 3);
    k_add(&k, 3, 0);
    k_add(&k, 2, 2);   /* self-loop keeps the bad path infinite */

    k_print("state machine", &k);

    StateSet phi;
    set_from_prop(phi, &k);
    set_print("p         ", phi, k.n);

    StateSet ef, af;
    ctl_EF(ef, phi, &k);
    ctl_AF(af, phi, &k);
    set_print("EF p      ", ef, k.n);
    set_print("AF p      ", af, k.n);

    printf("\n  EF p includes state 0 (can go 0 → 1).\n");
    printf("  But AF p does NOT include 0 — the path 0 → 2 fails to\n");
    printf("  ever reach p. Existence of even one bad path breaks AF.\n");
    printf("\n  This is the characteristic distinction:\n");
    printf("    EF: exists a path reaching p\n");
    printf("    AF: all paths reach p\n");
    printf("  Modal logic with just □/◇ cannot express either one.\n");
}

/* ═══ EXPERIMENT 4: EG and AG ═══ */
static void experiment_EG(void){
    printf("\n═══ EXPERIMENT 4: EG p and AG p — 'always' along paths ═══\n\n");

    /* Four states; a loop 0 → 1 → 0 keeps p true; branch 0 → 2 → 3
     * loses p at state 3. */
    Kripke k; k_init(&k, 4);
    k.prop[0] = 1; k.prop[1] = 1; k.prop[2] = 1; k.prop[3] = 0;
    k_add(&k, 0, 1);
    k_add(&k, 1, 0);
    k_add(&k, 0, 2);
    k_add(&k, 2, 3);

    k_print("state machine", &k);

    StateSet phi;
    set_from_prop(phi, &k);
    set_print("p         ", phi, k.n);

    StateSet eg, ag;
    ctl_EG(eg, phi, &k);
    ctl_AG(ag, phi, &k);
    set_print("EG p      ", eg, k.n);
    set_print("AG p      ", ag, k.n);

    printf("\n  EG p includes states 0, 1 — there exists a path (the\n");
    printf("  0↔1 loop) along which p always holds.\n");
    printf("  AG p is empty (or just {1}) because from 0 we can go\n");
    printf("  0→2→3 where p fails.\n");
    printf("\n  Greatest fixed point started from p = {0,1,2} and\n");
    printf("  shrank: a state stays iff it has an EX Z successor.\n");
}

/* ═══ EXPERIMENT 5: Witness of irreducibility to modal ═══ */
static void experiment_vs_modal(void){
    printf("\n═══ EXPERIMENT 5: Modal cannot express EF (path quantification) ═══\n\n");

    /* Consider a long path 0 → 1 → 2 → 3 where only 3 has p. */
    Kripke k; k_init(&k, 4);
    k.prop[3] = 1;
    k_add(&k, 0, 1);
    k_add(&k, 1, 2);
    k_add(&k, 2, 3);

    StateSet phi;
    set_from_prop(phi, &k);

    /* Modal □^k p (iterated AX) for various k */
    StateSet ax[5];
    set_copy(ax[0], phi);
    for(int i = 1; i <= 4; i++) ctl_AX(ax[i], ax[i-1], &k);

    /* CTL EF p */
    StateSet ef;
    ctl_EF(ef, phi, &k);

    printf("  State machine: 0 → 1 → 2 → 3, only 3 has p.\n\n");
    set_print("p         ", phi, k.n);
    set_print("AX p      ", ax[1], k.n);
    set_print("AX AX p   ", ax[2], k.n);
    set_print("AX³ p    ", ax[3], k.n);
    set_print("EF p      ", ef, k.n);

    printf("\n  To check if state 0 can eventually reach p using modal\n");
    printf("  logic, we must compute AX^k p for EACH k from 0 upward\n");
    printf("  and union the results. The answer depends on the path\n");
    printf("  length, which modal formulas cannot quantify over.\n");
    printf("\n  CTL's EF p expresses this directly via the fixed point\n");
    printf("  EF p = p ∨ EX EF p, which modal logic cannot even write.\n");
    printf("  Path quantifiers are a STRICTLY MORE EXPRESSIVE primitive\n");
    printf("  than single-step modalities.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BRANCHING BITS: CTL with path quantifiers\n");
    printf("══════════════════════════════════════════\n");
    printf("Bits live on a branching state graph;\n");
    printf("temporal operators quantify over paths.\n");

    experiment_single_step();
    experiment_EF();
    experiment_AF();
    experiment_EG();
    experiment_vs_modal();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Branching bit = proposition on a state graph with\n");
    printf("     multiple successors per state\n");
    printf("  2. EX, AX as single-step quantifiers\n");
    printf("  3. EF, AF as least fixed points (μZ)\n");
    printf("  4. EG, AG as greatest fixed points (νZ)\n");
    printf("  5. Modal logic cannot express EF/AF/EG/AG because\n");
    printf("     it has no path-level quantification\n");
    printf("\n  Fourth TIME axis: BRANCHING / CTL.\n");
    printf("  Meta-group TIME now has 4 axes: stream, interval,\n");
    printf("  cyclic, branching — matching RELATION's count.\n");
    return 0;
}
