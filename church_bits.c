/*
 * CHURCH / HIGHER-ORDER BITS
 * =============================
 *
 * Candidate NINTH axis in the bit taxonomy.  Inspired by
 * Alonzo Church (1936) and his encoding of Booleans inside
 * pure lambda calculus.
 *
 * A Church bit is NOT a stored value.  It is a FUNCTION that
 * chooses between two alternatives:
 *
 *     TRUE   = λ x y . x       "pick the first option"
 *     FALSE  = λ x y . y       "pick the second option"
 *
 * The bit IS its behaviour.  There is no underlying {0, 1}
 * field to read; the bit has no 'value' separate from what it
 * does when applied to arguments.
 *
 * Logical operations become PURE lambda terms:
 *
 *     NOT p    = λ p x y . p y x
 *     AND p q  = λ p q . p q p              (if p then q else p)
 *     OR  p q  = λ p q . p p q
 *     XOR p q  = λ p q . p (NOT q) q
 *     IF  c t e = c t e                     (just apply)
 *
 * None of the eight earlier primitives does this:
 *
 *   binary       stores a number
 *   phase        stores a signed number
 *   prob         stores a distribution
 *   reversible   stores a number inside a circuit with history
 *   stream       stores a time-series
 *   braid        stores a matrix tag
 *   linear       stores a number plus a budget
 *   self-ref     stores a function AND its fixed point
 *   HIGHER-ORDER stores ONLY a function; no 'value' anywhere
 *
 * The ninth axis is thus HIGHER-ORDER / FUNCTIONAL.
 *
 * Implementation note: C cannot express arbitrary lambda
 * abstractions, but we simulate them with function pointers
 * carrying a small closure environment.  The encoding below
 * is faithful to Church: the bit is a function taking two
 * arguments and returning one of them.
 *
 * Compile: gcc -O3 -march=native -o church church_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ═══ CHURCH BIT = function pointer that selects ═══
 *
 * A 'value' in our universe is an `int *`.  A Church bit is a
 * function that takes two ints and returns one of them.
 */

typedef int (*Bit)(int, int);

static int TRUE_fn (int x, int y){(void)y; return x;}
static int FALSE_fn(int x, int y){(void)x; return y;}

static const Bit TRUE_bit  = TRUE_fn;
static const Bit FALSE_bit = FALSE_fn;

/* Decode back to {0, 1} — but only by APPLYING the function to
 * probes.  There is no 'value' field to read directly. */
static int decode(Bit b){
    return b(1, 0);   /* TRUE returns first argument → 1; FALSE → 0 */
}

/* ═══ LOGICAL OPERATIONS as pure Church terms ═══
 *
 * Because we cannot return a fresh closure in C, we encode
 * compound bits by storing their 'program' as an enum and
 * evaluating it on demand.  Semantically identical to building
 * a fresh lambda; only the representation is less elegant.
 */
typedef enum {
    CB_TRUE, CB_FALSE,
    CB_NOT, CB_AND, CB_OR, CB_XOR,
    CB_IF
} ChurchOp;

typedef struct ChurchBit ChurchBit;
struct ChurchBit {
    ChurchOp op;
    const ChurchBit *arg1, *arg2, *arg3;   /* up to 3 sub-bits */
};

/* Constants */
static const ChurchBit CT = {CB_TRUE,  NULL, NULL, NULL};
static const ChurchBit CF = {CB_FALSE, NULL, NULL, NULL};

/* Evaluator: recursively apply as if each compound bit were a
 * lambda abstraction waiting for its two arguments. */
static int apply(const ChurchBit *b, int x, int y){
    switch(b->op){
    case CB_TRUE:  return x;
    case CB_FALSE: return y;
    case CB_NOT:   return apply(b->arg1, y, x);   /* flip args */
    case CB_AND:   {
        /* AND p q = λxy . p (q x y) y  →  if p then q else FALSE */
        int q = apply(b->arg2, x, y);
        return apply(b->arg1, q, y);
    }
    case CB_OR: {
        /* OR p q = λxy . p x (q x y)  →  if p then TRUE else q */
        int q = apply(b->arg2, x, y);
        return apply(b->arg1, x, q);
    }
    case CB_XOR: {
        /* XOR p q = λxy . p (q y x) (q x y) */
        int qxy = apply(b->arg2, x, y);
        int qyx = apply(b->arg2, y, x);
        return apply(b->arg1, qyx, qxy);
    }
    case CB_IF: {
        /* IF c t e = c (apply t) (apply e), but here we interpret
         * the choice at the top level */
        int t = apply(b->arg2, x, y);
        int e = apply(b->arg3, x, y);
        return apply(b->arg1, t, e);
    }
    }
    return -1;
}
static int cb_decode(const ChurchBit *b){return apply(b, 1, 0);}

/* ═══ EXPERIMENT 1: TRUE and FALSE as pure functions ═══ */
static void experiment_constants(void){
    printf("\n═══ EXPERIMENT 1: Church TRUE and FALSE ═══\n\n");

    printf("  TRUE  = λxy.x   →  TRUE_bit(7, 42) = %d\n", TRUE_bit(7, 42));
    printf("  FALSE = λxy.y   →  FALSE_bit(7, 42) = %d\n", FALSE_bit(7, 42));

    printf("\n  decode(TRUE)  = %d\n", decode(TRUE_bit));
    printf("  decode(FALSE) = %d\n", decode(FALSE_bit));

    printf("\n  There is no stored value. The 'bit' is literally the\n");
    printf("  function that returns x when given TRUE, y when FALSE.\n");
    printf("  Decoding is just probing the function with (1, 0).\n");
}

/* ═══ EXPERIMENT 2: All 4 single-bit ops via Church terms ═══ */
static void experiment_ops(void){
    printf("\n═══ EXPERIMENT 2: Logical ops as pure function composition ═══\n\n");

    /* not_T = NOT TRUE = FALSE */
    ChurchBit not_T = {CB_NOT, &CT, NULL, NULL};
    ChurchBit not_F = {CB_NOT, &CF, NULL, NULL};

    printf("  NOT TRUE  = %d  (expected 0)\n", cb_decode(&not_T));
    printf("  NOT FALSE = %d  (expected 1)\n", cb_decode(&not_F));

    ChurchBit TT = {CB_AND, &CT, &CT, NULL};
    ChurchBit TF = {CB_AND, &CT, &CF, NULL};
    ChurchBit FT = {CB_AND, &CF, &CT, NULL};
    ChurchBit FF = {CB_AND, &CF, &CF, NULL};

    printf("\n  AND truth table:\n");
    printf("    T AND T = %d\n", cb_decode(&TT));
    printf("    T AND F = %d\n", cb_decode(&TF));
    printf("    F AND T = %d\n", cb_decode(&FT));
    printf("    F AND F = %d\n", cb_decode(&FF));

    ChurchBit oTT = {CB_OR, &CT, &CT, NULL};
    ChurchBit oTF = {CB_OR, &CT, &CF, NULL};
    ChurchBit oFT = {CB_OR, &CF, &CT, NULL};
    ChurchBit oFF = {CB_OR, &CF, &CF, NULL};
    printf("\n  OR truth table:\n");
    printf("    T OR T = %d\n", cb_decode(&oTT));
    printf("    T OR F = %d\n", cb_decode(&oTF));
    printf("    F OR T = %d\n", cb_decode(&oFT));
    printf("    F OR F = %d\n", cb_decode(&oFF));

    ChurchBit xTT = {CB_XOR, &CT, &CT, NULL};
    ChurchBit xTF = {CB_XOR, &CT, &CF, NULL};
    ChurchBit xFT = {CB_XOR, &CF, &CT, NULL};
    ChurchBit xFF = {CB_XOR, &CF, &CF, NULL};
    printf("\n  XOR truth table:\n");
    printf("    T XOR T = %d\n", cb_decode(&xTT));
    printf("    T XOR F = %d\n", cb_decode(&xTF));
    printf("    F XOR T = %d\n", cb_decode(&xFT));
    printf("    F XOR F = %d\n", cb_decode(&xFF));
}

/* ═══ EXPERIMENT 3: IF as a native construct ═══
 *
 * In Church encoding, IF c t e is literally c applied to t and e
 * — no separate 'if statement' is needed.  The bit itself IS the
 * control flow.
 */
static void experiment_if(void){
    printf("\n═══ EXPERIMENT 3: IF is just function application ═══\n\n");

    /* IF TRUE then FALSE else TRUE = FALSE */
    ChurchBit if1 = {CB_IF, &CT, &CF, &CT};
    ChurchBit if2 = {CB_IF, &CF, &CF, &CT};

    printf("  IF TRUE  then FALSE else TRUE  = %d  (expected 0)\n", cb_decode(&if1));
    printf("  IF FALSE then FALSE else TRUE  = %d  (expected 1)\n", cb_decode(&if2));

    printf("\n  Nesting: (IF TRUE then (IF FALSE then T else F) else T)\n");
    ChurchBit inner = {CB_IF, &CF, &CT, &CF};   /* → F */
    ChurchBit outer = {CB_IF, &CT, &inner, &CT}; /* → inner = F */
    printf("    result = %d  (expected 0)\n", cb_decode(&outer));

    printf("\n  Control flow is reduced to function application.\n");
    printf("  The bit doesn't 'have' a branch decision — it IS the\n");
    printf("  branch decision.\n");
}

/* ═══ EXPERIMENT 4: Functional extensionality check ═══
 *
 * Two Church bits b1, b2 are equal iff they agree on every
 * input pair (x, y).  We verify NOT (NOT T) = T this way.
 */
static int bits_equal(const ChurchBit *a, const ChurchBit *b){
    /* Exhaustively test on probes (0,1), (1,0), (0,0), (1,1) */
    int probes[4][2] = {{0,1},{1,0},{0,0},{1,1}};
    for(int i = 0; i < 4; i++){
        int ra = apply(a, probes[i][0], probes[i][1]);
        int rb = apply(b, probes[i][0], probes[i][1]);
        if(ra != rb) return 0;
    }
    return 1;
}

static void experiment_extensional(void){
    printf("\n═══ EXPERIMENT 4: Functional extensionality ═══\n\n");

    /* NOT (NOT TRUE) should be extensionally equal to TRUE */
    ChurchBit nt = {CB_NOT, &CT, NULL, NULL};       /* NOT T = F */
    ChurchBit nnt = {CB_NOT, &nt, NULL, NULL};      /* NOT (NOT T) = T */
    printf("  NOT (NOT TRUE) extensionally equal to TRUE?  %s\n",
           bits_equal(&nnt, &CT) ? "YES ✓" : "NO ✗");

    /* De Morgan: NOT (p AND q) = (NOT p) OR (NOT q) */
    ChurchBit and_tf = {CB_AND, &CT, &CF, NULL};
    ChurchBit lhs = {CB_NOT, &and_tf, NULL, NULL};
    ChurchBit nt2 = {CB_NOT, &CT, NULL, NULL};
    ChurchBit nf2 = {CB_NOT, &CF, NULL, NULL};
    ChurchBit rhs = {CB_OR, &nt2, &nf2, NULL};
    printf("  De Morgan  NOT(T AND F) = NOT T OR NOT F ?   %s\n",
           bits_equal(&lhs, &rhs) ? "YES ✓" : "NO ✗");

    /* Absorption: p AND (p OR q) = p */
    ChurchBit p_or_q = {CB_OR, &CT, &CF, NULL};
    ChurchBit absorb = {CB_AND, &CT, &p_or_q, NULL};
    printf("  Absorption  T AND (T OR F) = T ?              %s\n",
           bits_equal(&absorb, &CT) ? "YES ✓" : "NO ✗");

    printf("\n  Boolean identities are VERIFIED by extensional equality\n");
    printf("  of the underlying functions, not by comparing stored\n");
    printf("  values. The primitive is the function itself.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("CHURCH / HIGHER-ORDER BITS\n");
    printf("══════════════════════════════════════════\n");
    printf("A bit is a function from two arguments to one: the\n");
    printf("primitive has no 'value', only behaviour.\n");

    experiment_constants();
    experiment_ops();
    experiment_if();
    experiment_extensional();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. TRUE = λxy.x, FALSE = λxy.y; no stored data\n");
    printf("  2. NOT, AND, OR, XOR as pure Church terms\n");
    printf("  3. IF is just function application\n");
    printf("  4. Boolean identities verified by extensional equality\n");
    printf("     (same output on every probe pair) not by value match\n");
    printf("\n  Proposed NINTH axis: HIGHER-ORDER / FUNCTIONAL.\n");
    printf("  A Church bit has no 'value' separate from its action.\n");
    printf("  The primitive is the function itself, not a datum.\n");
    return 0;
}
