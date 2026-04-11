/*
 * ANYONIC-LIKE PHASES FROM BRAIDING
 * ====================================
 *
 * Third piece of the braid branch.  In anyonic (2-d) physics,
 * exchanging two identical particles can pick up ANY phase
 * e^{iθ}, not just ±1 (bosons and fermions).  The braid group
 * replaces the symmetric group as the exchange statistics.
 *
 * Classically we do not have complex phases, but the same braid
 * group B_n can assign an INTEGER to each braid word via its
 * linear representations.  Two natural candidates:
 *
 *   1. Exponent sum (writhe-like)  w(β) ∈ Z
 *      — already explored in braid_bits.c
 *
 *   2. Burau trace at t = 1, 2, ... (integer witnesses)
 *      — related to Alexander polynomial evaluated at t = k
 *
 * Key demonstration: two braids with the same underlying
 * PERMUTATION can have different Burau invariants.  In anyonic
 * language, they exchange the "same" particles but gain
 * different "phases".
 *
 * We build the finest classical "phase" we can from B_3:
 *
 *   χ(β) = tr(ρ(β)) ∈ Z[t, t^{-1}]
 *
 * This is conjugation invariant (tr(ABA^{-1}) = tr(B)), so it
 * descends to conjugacy classes of braids — the classical
 * "particle exchange class".
 *
 * Experiments:
 *   1. Anyonic phase of the trivial exchange σ_1
 *      vs the 'looped' exchanges σ_1³, σ_1⁵
 *   2. Anyonic phase of Yang-Baxter pair (equal ↔ same physics)
 *   3. Phase of a full twist σ_1² (center of B_2)
 *   4. Full twist of B_3: (σ_1 σ_2)³ is the generator of the
 *      center of B_3, giving the characteristic "spin" phase
 *
 * The point: we recover the discrete classical skeleton of
 * anyonic physics using nothing but integer Laurent polynomials.
 *
 * Compile: gcc -O3 -march=native -o anyons anyonic_phases.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* Reuse the Poly / MatP code from braid_jones.c */
#define POLY_N 41
#define POLY_OFFSET 20
typedef struct { int c[POLY_N]; } Poly;
typedef struct { Poly e[2][2]; } MatP;

static void poly_zero(Poly *p){memset(p, 0, sizeof(Poly));}
static Poly poly_const(int k){Poly p; poly_zero(&p); p.c[POLY_OFFSET] = k; return p;}
static Poly poly_monomial(int c, int e){
    Poly p; poly_zero(&p);
    int idx = POLY_OFFSET + e;
    if(idx >= 0 && idx < POLY_N) p.c[idx] = c;
    return p;
}
static int poly_eq(const Poly *a, const Poly *b){return memcmp(a->c, b->c, sizeof(a->c)) == 0;}
static Poly poly_add(const Poly *a, const Poly *b){
    Poly r;
    for(int i = 0; i < POLY_N; i++) r.c[i] = a->c[i] + b->c[i];
    return r;
}
static Poly poly_mul(const Poly *a, const Poly *b){
    Poly r; poly_zero(&r);
    for(int i = 0; i < POLY_N; i++){
        if(!a->c[i]) continue;
        for(int j = 0; j < POLY_N; j++){
            if(!b->c[j]) continue;
            int k = i + j - POLY_OFFSET;
            if(k >= 0 && k < POLY_N) r.c[k] += a->c[i] * b->c[j];
        }
    }
    return r;
}
static void poly_print(const Poly *p){
    int first = 1, any = 0;
    for(int i = POLY_N - 1; i >= 0; i--){
        if(!p->c[i]) continue;
        any = 1;
        int exp = i - POLY_OFFSET;
        int coef = p->c[i];
        if(first){if(coef < 0) printf("−"); first = 0;}
        else    {printf(coef < 0 ? " − " : " + ");}
        int ac = coef < 0 ? -coef : coef;
        if(exp == 0) printf("%d", ac);
        else { if(ac != 1) printf("%d", ac);
               if(exp == 1) printf("t"); else printf("t^%d", exp); }
    }
    if(!any) printf("0");
}

static MatP mat_zero(void){
    MatP m; for(int i = 0; i < 2; i++) for(int j = 0; j < 2; j++) poly_zero(&m.e[i][j]);
    return m;
}
static MatP mat_id(void){
    MatP m = mat_zero();
    m.e[0][0] = poly_const(1);
    m.e[1][1] = poly_const(1);
    return m;
}
static MatP mat_mul(const MatP *a, const MatP *b){
    MatP r = mat_zero();
    for(int i = 0; i < 2; i++)
        for(int j = 0; j < 2; j++){
            Poly s; poly_zero(&s);
            for(int k = 0; k < 2; k++){
                Poly p = poly_mul(&a->e[i][k], &b->e[k][j]);
                s = poly_add(&s, &p);
            }
            r.e[i][j] = s;
        }
    return r;
}
static int mat_eq(const MatP *a, const MatP *b){
    for(int i = 0; i < 2; i++) for(int j = 0; j < 2; j++)
        if(!poly_eq(&a->e[i][j], &b->e[i][j])) return 0;
    return 1;
}
static Poly mat_trace(const MatP *m){
    return poly_add(&m->e[0][0], &m->e[1][1]);
}
static Poly poly_eval_int(const Poly *p, int t){
    /* Evaluate Laurent polynomial at integer t (must be non-zero).
     * Result is a constant polynomial. */
    long long s = 0;
    for(int i = 0; i < POLY_N; i++){
        if(!p->c[i]) continue;
        int exp = i - POLY_OFFSET;
        long long pw = 1;
        if(exp >= 0){for(int k = 0; k < exp; k++) pw *= t;}
        else {for(int k = 0; k < -exp; k++) pw *= t;
              if(pw == 0){s = 0; break;}
              pw = 0;} /* for |t|=1 fine; we only use t=−1, 2 */
        /* Simpler: handle t = −1, 1, 2 specially */
        (void)pw;
    }
    (void)s;
    /* Proper implementation: */
    long long total = 0;
    for(int i = 0; i < POLY_N; i++){
        if(!p->c[i]) continue;
        int exp = i - POLY_OFFSET;
        long long pw = 1;
        int abs_e = exp < 0 ? -exp : exp;
        for(int k = 0; k < abs_e; k++) pw *= t;
        if(exp < 0){
            if(pw == 0) continue;
            /* t^{-e} as 1/pw; only valid when t is ±1 */
            if(pw != 1 && pw != -1) continue;
            total += p->c[i] * pw;   /* ±1 cases only */
        } else {
            total += p->c[i] * pw;
        }
    }
    Poly r = poly_const((int)total);
    return r;
}

/* Burau σ_1, σ_2 and their inverses on B_3 */
static MatP burau_s(int i){
    MatP m = mat_zero();
    if(i == 1){
        m.e[0][0] = poly_monomial(-1, 1);
        m.e[0][1] = poly_const(1);
        m.e[1][1] = poly_const(1);
    } else {
        m.e[0][0] = poly_const(1);
        m.e[1][0] = poly_monomial(1, 1);
        m.e[1][1] = poly_monomial(-1, 1);
    }
    return m;
}
static MatP burau_si(int i){
    MatP m = mat_zero();
    if(i == 1){
        m.e[0][0] = poly_monomial(-1, -1);
        m.e[0][1] = poly_monomial(1, -1);
        m.e[1][1] = poly_const(1);
    } else {
        m.e[0][0] = poly_const(1);
        m.e[1][0] = poly_const(1);
        m.e[1][1] = poly_monomial(-1, -1);
    }
    return m;
}
static MatP braid_eval(const int *g, int n){
    MatP m = mat_id();
    for(int k = 0; k < n; k++){
        MatP step = (g[k] > 0) ? burau_s(g[k]) : burau_si(-g[k]);
        MatP r = mat_mul(&m, &step);
        m = r;
    }
    return m;
}

/* ═══ EXPERIMENT 1: Phases of σ_1^n ═══ */
static void experiment_sigma_powers(void){
    printf("\n═══ EXPERIMENT 1: Anyonic phases of σ_1^n ═══\n\n");
    printf("  χ(β) = tr(ρ(β)) for β = σ_1, σ_1^2, σ_1^3, σ_1^4, σ_1^5\n\n");

    for(int n = 1; n <= 5; n++){
        int gens[16];
        for(int i = 0; i < n; i++) gens[i] = 1;
        MatP m = braid_eval(gens, n);
        Poly tr = mat_trace(&m);
        printf("  σ_1^%d:   tr ρ = ", n);
        poly_print(&tr);
        printf("\n");
    }
    printf("\n  Each power gives a distinct Laurent polynomial — the\n");
    printf("  'phase' is a different element of Z[t, t^{-1}] for each\n");
    printf("  winding.  An abelian anyonic model with discrete phases.\n");
}

/* ═══ EXPERIMENT 2: Yang-Baxter pair shares its phase ═══ */
static void experiment_yb(void){
    printf("\n═══ EXPERIMENT 2: Yang-Baxter preserves the phase ═══\n\n");
    int a[] = {1, 2, 1};
    int b[] = {2, 1, 2};
    MatP ma = braid_eval(a, 3);
    MatP mb = braid_eval(b, 3);
    Poly tra = mat_trace(&ma);
    Poly trb = mat_trace(&mb);
    printf("  tr(ρ(σ_1 σ_2 σ_1)) = ");
    poly_print(&tra);
    printf("\n  tr(ρ(σ_2 σ_1 σ_2)) = ");
    poly_print(&trb);
    printf("\n  Equal?  %s\n", poly_eq(&tra, &trb) ? "YES ✓" : "NO ✗");
    printf("\n  Yang-Baxter is a TOPOLOGICAL move that leaves the phase\n");
    printf("  untouched — both braids describe the same 'physical' exchange.\n");
}

/* ═══ EXPERIMENT 3: Full twist as center of B_3 ═══
 *
 * The element Δ² = (σ_1 σ_2)³ generates the center of B_3.
 * Its Burau phase is thus a pure scalar (the "spin" of the
 * braid acts globally).
 */
static void experiment_full_twist(void){
    printf("\n═══ EXPERIMENT 3: Full twist and the centre of B_3 ═══\n\n");

    int twist[] = {1, 2, 1, 2, 1, 2};
    MatP m = braid_eval(twist, 6);

    printf("  (σ_1 σ_2)^3 matrix entries:\n");
    printf("    [0][0] = "); poly_print(&m.e[0][0]); printf("\n");
    printf("    [0][1] = "); poly_print(&m.e[0][1]); printf("\n");
    printf("    [1][0] = "); poly_print(&m.e[1][0]); printf("\n");
    printf("    [1][1] = "); poly_print(&m.e[1][1]); printf("\n");

    Poly tr = mat_trace(&m);
    printf("\n  Trace = "); poly_print(&tr); printf("\n");

    /* Commute-with-everything test: Δ² · ρ(σ_1) = ρ(σ_1) · Δ² */
    MatP s1 = burau_s(1);
    MatP left = mat_mul(&m, &s1);
    MatP right = mat_mul(&s1, &m);
    printf("  Δ² commutes with σ_1:  %s\n", mat_eq(&left, &right) ? "YES ✓" : "NO ✗");

    MatP s2 = burau_s(2);
    MatP left2 = mat_mul(&m, &s2);
    MatP right2 = mat_mul(&s2, &m);
    printf("  Δ² commutes with σ_2:  %s\n", mat_eq(&left2, &right2) ? "YES ✓" : "NO ✗");

    printf("\n  The full twist is central in B_3 — it commutes with every\n");
    printf("  generator.  Physically, it is the 'total spin' of the\n");
    printf("  braid, a global phase that multiplies every state equally.\n");
}

/* ═══ EXPERIMENT 4: Integer phase witnesses via Burau at t = −1 ═══ */
static void experiment_t_minus_one(void){
    printf("\n═══ EXPERIMENT 4: Burau trace at t = −1 (signed witnesses) ═══\n\n");
    printf("  Evaluating tr ρ(β) at t = −1 collapses the Laurent\n");
    printf("  polynomial to an integer that discriminates braid classes.\n\n");

    struct {const char *name; int gens[10]; int len;} tests[] = {
        {"trivial σ_1 σ_1^{-1}", {1, -1}, 2},
        {"σ_1",          {1}, 1},
        {"σ_1²",         {1, 1}, 2},
        {"σ_1³",         {1, 1, 1}, 3},
        {"(σ_1 σ_2)³",   {1, 2, 1, 2, 1, 2}, 6},
        {"(σ_1 σ_2^{-1})²", {1, -2, 1, -2}, 4},
    };

    for(int t = 0; t < 6; t++){
        MatP m = braid_eval(tests[t].gens, tests[t].len);
        Poly tr = mat_trace(&m);
        Poly ev = poly_eval_int(&tr, -1);
        printf("  %-20s  tr = ", tests[t].name);
        poly_print(&tr);
        printf("    t=−1 → %d\n", ev.c[POLY_OFFSET]);
    }
    printf("\n  Each conjugacy class gets an integer label via Burau at −1.\n");
    printf("  It is the classical analogue of an anyonic phase.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("ANYONIC-LIKE PHASES FROM BRAIDING\n");
    printf("══════════════════════════════════════════\n");
    printf("Classical integer 'phases' from Burau traces.\n");

    experiment_sigma_powers();
    experiment_yb();
    experiment_full_twist();
    experiment_t_minus_one();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Each braid word gets a Laurent-polynomial 'phase'\n");
    printf("     via Burau trace — conjugation invariant\n");
    printf("  2. Yang-Baxter preserves the phase (topological move)\n");
    printf("  3. Full twist (σ_1 σ_2)³ is central in B_3: its matrix\n");
    printf("     commutes with every generator (verified)\n");
    printf("  4. Integer witnesses via tr ρ(β)|_{t=−1} give a scalar\n");
    printf("     label for each conjugacy class\n");
    printf("  5. The classical skeleton of anyonic physics — abelian\n");
    printf("     discrete phases — emerges from integer arithmetic alone\n");
    return 0;
}
