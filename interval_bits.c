/*
 * INTERVAL BITS: Allen's temporal intervals as primitive
 * =========================================================
 *
 * Candidate for a second TIME-meta-group axis, testing the
 * hypothesis from hierarchy_v3.c that TIME is not really
 * closed at one axis (stream).
 *
 * Based on Allen's interval algebra (1983).  An interval bit
 * has an explicit temporal extent [t_start, t_end] and EXISTS
 * only within that range.  Outside the interval the bit is
 * undefined, not zero.
 *
 * The signature operations are the THIRTEEN BASIC RELATIONS
 * between two intervals:
 *
 *     x before y           x < y,  x.end  < y.start
 *     x meets y            x.end  == y.start
 *     x overlaps y         x.start < y.start < x.end < y.end
 *     x starts y           x.start == y.start,  x.end < y.end
 *     x during y           y.start < x.start, x.end < y.end
 *     x finishes y         y.start < x.start, x.end == y.end
 *     x equals y           x.start == y.start, x.end == y.end
 *     plus the 6 inverses (after, met-by, overlapped-by,
 *     started-by, contains, finished-by)
 *
 * These 13 relations partition every ordered pair of intervals
 * into exactly one bucket. The algebra is closed under
 * composition: given x R y and y S z, you can infer a (possibly
 * disjunctive) set of R's between x and z via Allen's table.
 *
 * Distinction from the fifteen previous axes:
 *
 *   - STREAM bits assign a value at EVERY moment. Interval bits
 *     exist only on a FINITE portion of the timeline.
 *   - CAUSAL bits have a partial order but NO duration — just
 *     "i precedes j", not "i lasts from 3 to 7".
 *   - RELATIONAL bits have no temporal structure at all.
 *   - MODAL bits have no duration either.
 *
 * The native operation of interval bits is "which of the 13
 * Allen relations holds?", computed in O(1) from two pairs of
 * endpoints. Stream bits CANNOT answer this in O(1) — they have
 * to iterate over the timeline comparing values.
 *
 * Experiments:
 *
 *   1. Build intervals and classify pairs into Allen's 13
 *      relations. Exhaustive test on a small set.
 *   2. Show that all 13 relations partition the pair space
 *      (every pair matches exactly one).
 *   3. Allen composition: given (x before y) and (y during z),
 *      what do we know about x vs z? Verify a few entries.
 *   4. Non-reducibility to stream: stream cannot answer "are
 *      these two events overlapping?" in O(1); interval bits
 *      can.
 *   5. Interval arithmetic: union, intersection, duration.
 *
 * Compile: gcc -O3 -march=native -o interval interval_bits.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* ═══ INTERVAL ═══ */
typedef struct {
    int start;
    int end;    /* inclusive end: [start, end] */
} Interval;

/* Allen's 13 relations as an enum. */
typedef enum {
    BEFORE, MEETS, OVERLAPS, STARTS, DURING, FINISHES, EQUALS,
    FINISHED_BY, CONTAINS, STARTED_BY, OVERLAPPED_BY, MET_BY, AFTER
} Allen;

static const char *allen_names[13] = {
    "before", "meets", "overlaps", "starts", "during", "finishes", "equals",
    "finished-by", "contains", "started-by", "overlapped-by", "met-by", "after"
};

/* Classify a pair of intervals into its unique Allen relation. */
static Allen allen_classify(Interval x, Interval y){
    if(x.end < y.start) return BEFORE;
    if(x.end == y.start && x.start < y.start) return MEETS;
    if(x.start > y.end) return AFTER;
    if(x.start == y.end && x.end > y.end) return MET_BY;

    if(x.start == y.start && x.end == y.end) return EQUALS;

    if(x.start == y.start){
        return x.end < y.end ? STARTS : STARTED_BY;
    }
    if(x.end == y.end){
        return x.start > y.start ? FINISHES : FINISHED_BY;
    }
    if(x.start > y.start && x.end < y.end) return DURING;
    if(x.start < y.start && x.end > y.end) return CONTAINS;
    if(x.start < y.start && x.end < y.end) return OVERLAPS;
    if(x.start > y.start && x.end > y.end) return OVERLAPPED_BY;

    /* Fallback (should not occur) */
    return EQUALS;
}

static int overlap(Interval x, Interval y){
    return !(x.end < y.start || y.end < x.start);
}

static Interval intersect(Interval x, Interval y){
    Interval r;
    r.start = x.start > y.start ? x.start : y.start;
    r.end   = x.end   < y.end   ? x.end   : y.end;
    return r;
}

static int duration(Interval x){return x.end - x.start + 1;}

/* ═══ EXPERIMENT 1: Allen classification ═══ */
static void experiment_classify(void){
    printf("\n═══ EXPERIMENT 1: Classify pairs into Allen relations ═══\n\n");

    /* Reference interval */
    Interval x = {5, 10};
    printf("  Reference x = [5, 10]\n\n");
    printf("  y           | relation x R y\n");
    printf("  ------------+----------------\n");

    struct { Interval y; const char *desc; } tests[] = {
        {{1,  3},  "[1, 3]"},
        {{1,  5},  "[1, 5]"},
        {{3,  7},  "[3, 7]"},
        {{5,  8},  "[5, 8]"},
        {{5, 10},  "[5, 10]"},
        {{5, 15},  "[5, 15]"},
        {{7, 10},  "[7, 10]"},
        {{7,  9},  "[7, 9]"},
        {{3, 15},  "[3, 15]"},
        {{8, 15},  "[8, 15]"},
        {{10,15},  "[10, 15]"},
        {{12,15},  "[12, 15]"},
    };

    for(int i = 0; i < 12; i++){
        Allen r = allen_classify(x, tests[i].y);
        printf("  %-11s | %s\n", tests[i].desc, allen_names[r]);
    }

    printf("\n  Every pair is classified into exactly one of the 13\n");
    printf("  Allen relations. The classification is O(1) given the\n");
    printf("  four endpoints.\n");
}

/* ═══ EXPERIMENT 2: Partition verification ═══ */
static void experiment_partition(void){
    printf("\n═══ EXPERIMENT 2: All 13 relations are reachable ═══\n\n");

    int hits[13] = {0};
    /* Enumerate a modest space of pairs */
    for(int xs = 0; xs < 6; xs++)
        for(int xe = xs; xe < 6; xe++)
            for(int ys = 0; ys < 6; ys++)
                for(int ye = ys; ye < 6; ye++){
                    Interval a = {xs, xe};
                    Interval b = {ys, ye};
                    Allen r = allen_classify(a, b);
                    hits[r]++;
                }

    printf("  Enumeration over intervals with endpoints in 0..5:\n");
    for(int i = 0; i < 13; i++){
        printf("    %-14s : %d pairs\n", allen_names[i], hits[i]);
    }
    int total = 0;
    int reached = 0;
    for(int i = 0; i < 13; i++){total += hits[i]; if(hits[i]) reached++;}
    printf("  Total pairs: %d\n", total);
    printf("  Distinct relations reached: %d / 13\n", reached);
    printf("\n  Every one of the 13 Allen relations is witnessed by\n");
    printf("  at least one pair. The partition is exhaustive.\n");
}

/* ═══ EXPERIMENT 3: Allen composition (selected entries) ═══
 *
 * Given x R y and y S z, what are the possible relations
 * between x and z? Allen's table answers this for all 169
 * combinations.
 *
 * We verify a few well-known entries by exhaustive enumeration
 * over small examples.
 */
static void experiment_composition(void){
    printf("\n═══ EXPERIMENT 3: Allen composition (sampled) ═══\n\n");

    printf("  For each (R, S) we enumerate triples (x, y, z) with\n");
    printf("  x R y and y S z, and record which relations occur\n");
    printf("  between x and z.\n\n");

    struct { Allen R, S; const char *name; } tests[] = {
        {BEFORE, BEFORE,   "before ∘ before"},
        {BEFORE, DURING,   "before ∘ during"},
        {DURING, DURING,   "during ∘ during"},
        {OVERLAPS, OVERLAPS, "overlaps ∘ overlaps"},
        {MEETS, MEETS,     "meets ∘ meets"},
    };

    for(int t = 0; t < 5; t++){
        int seen[13] = {0};
        for(int xs = 0; xs < 6; xs++)
        for(int xe = xs; xe < 6; xe++)
        for(int ys = 0; ys < 6; ys++)
        for(int ye = ys; ye < 6; ye++)
        for(int zs = 0; zs < 6; zs++)
        for(int ze = zs; ze < 6; ze++){
            Interval x = {xs, xe}, y = {ys, ye}, z = {zs, ze};
            if(allen_classify(x, y) == tests[t].R &&
               allen_classify(y, z) == tests[t].S){
                seen[allen_classify(x, z)] = 1;
            }
        }
        printf("  %-22s → { ", tests[t].name);
        int first = 1;
        for(int i = 0; i < 13; i++){
            if(seen[i]){
                if(!first) printf(", ");
                printf("%s", allen_names[i]);
                first = 0;
            }
        }
        printf(" }\n");
    }

    printf("\n  before ∘ before = {before}  — transitive\n");
    printf("  meets ∘ meets = {before}     — two sequential meets\n");
    printf("                                  give 'before'\n");
    printf("  during ∘ during = {during}  — transitive containment\n");
    printf("  overlaps ∘ overlaps can produce multiple relations,\n");
    printf("  reflecting the fact that Allen's algebra is NOT a\n");
    printf("  single-valued composition — it has set-valued results.\n");
}

/* ═══ EXPERIMENT 4: Non-reducibility to stream ═══ */
static void experiment_vs_stream(void){
    printf("\n═══ EXPERIMENT 4: Overlap query — O(1) vs O(T) ═══\n\n");

    printf("  Question: do intervals x = [3, 8] and y = [6, 12] overlap?\n\n");

    Interval x = {3, 8};
    Interval y = {6, 12};

    /* Interval-bit answer: O(1) via Allen classification */
    Allen r = allen_classify(x, y);
    int overlaps_ib = overlap(x, y);
    printf("  Interval bit answer: one comparison of endpoints.\n");
    printf("    Allen relation = %s\n", allen_names[r]);
    printf("    Overlap?       = %s\n\n", overlaps_ib ? "YES" : "no");

    /* Stream-bit answer: encode each as a bit stream and iterate */
    int T = 15;
    int stream_x[15], stream_y[15];
    for(int t = 0; t < T; t++){
        stream_x[t] = (t >= x.start && t <= x.end) ? 1 : 0;
        stream_y[t] = (t >= y.start && t <= y.end) ? 1 : 0;
    }
    printf("  Stream bit answer: scan %d timeline slots.\n", T);
    printf("    x stream: ");
    for(int t = 0; t < T; t++) printf("%d", stream_x[t]);
    printf("\n    y stream: ");
    for(int t = 0; t < T; t++) printf("%d", stream_y[t]);
    printf("\n");
    int any_both = 0;
    for(int t = 0; t < T; t++) if(stream_x[t] && stream_y[t]){any_both = 1; break;}
    printf("    Overlap?  = %s\n\n", any_both ? "YES" : "no");

    printf("  Both answers agree — but interval bits answer in O(1)\n");
    printf("  from endpoints; stream bits need O(T) to scan the\n");
    printf("  timeline. The 13 Allen relations are all O(1) for\n");
    printf("  interval bits and at best O(T) for stream bits.\n");
    printf("\n  This is a STRUCTURAL advantage, not a constant factor:\n");
    printf("  'precedes', 'during', 'meets' are PRIMITIVE operations\n");
    printf("  for interval bits and DERIVED operations for streams.\n");
}

/* ═══ EXPERIMENT 5: Interval arithmetic ═══ */
static void experiment_arithmetic(void){
    printf("\n═══ EXPERIMENT 5: Duration, intersection, relation to causal ═══\n\n");

    Interval a = {3, 10};
    Interval b = {7, 15};
    Interval c = {20, 25};

    printf("  a = [%d, %d]  duration = %d\n", a.start, a.end, duration(a));
    printf("  b = [%d, %d]  duration = %d\n", b.start, b.end, duration(b));
    printf("  c = [%d, %d]  duration = %d\n", c.start, c.end, duration(c));

    Interval ab = intersect(a, b);
    printf("\n  a ∩ b = [%d, %d]  duration = %d   (overlap region)\n",
           ab.start, ab.end, duration(ab));

    Interval ac = intersect(a, c);
    printf("  a ∩ c = [%d, %d]  (empty: start > end → no overlap)\n",
           ac.start, ac.end);
    printf("  a Allen c = %s\n", allen_names[allen_classify(a, c)]);

    printf("\n  Contrast with causal bits: causal says 'a precedes c'\n");
    printf("  but HAS NO DURATION. Interval bits say 'a precedes c'\n");
    printf("  AND 'a lasts 8 time units' AND 'a ends 10 before c starts'.\n");
    printf("\n  Causal is temporal ORDER without time.\n");
    printf("  Interval is temporal ORDER with explicit EXTENT.\n");
    printf("  Both are in the temporal family but capture different\n");
    printf("  aspects — causal the skeleton, interval the measure.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("INTERVAL BITS: Allen's temporal intervals\n");
    printf("══════════════════════════════════════════\n");
    printf("A bit has explicit start and end; the 13 Allen\n");
    printf("relations are primitive operations on pairs.\n");

    experiment_classify();
    experiment_partition();
    experiment_composition();
    experiment_vs_stream();
    experiment_arithmetic();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Interval bit = explicit [start, end] extent\n");
    printf("  2. Allen's 13 relations as primitive O(1) operations\n");
    printf("  3. All 13 relations witnessed by exhaustive enumeration\n");
    printf("  4. Allen composition table (before∘before = before,\n");
    printf("     meets∘meets = before, overlaps∘overlaps is\n");
    printf("     set-valued, etc.)\n");
    printf("  5. Non-reducibility to stream: O(1) vs O(T) for\n");
    printf("     every temporal relation query\n");
    printf("  6. Interval vs causal: interval adds DURATION to the\n");
    printf("     pure partial-order skeleton of causal\n");
    printf("\n  Proposed SECOND TIME axis: INTERVAL / DURATION.\n");
    printf("  Confirms that the TIME meta-group is not closed at\n");
    printf("  one axis. Stream and interval are the first two\n");
    printf("  entries; more may exist.\n");
    return 0;
}
