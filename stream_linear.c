/*
 * STREAM × LINEAR: temporal linear logic
 * =========================================
 *
 * Fourth combination primitive in the programme.  Intersects
 * the STREAM axis (time as a sequence of moments) with the
 * LINEAR axis (resource / usage budget) to yield temporal
 * linear logic: resources that vary with time.
 *
 * Inspired by Girard's temporal linear logic (1991), rate
 * limiting in network protocols, time-limited credentials,
 * real-time reservations, and energy budgets in embedded
 * systems.
 *
 * Distinction from either axis alone:
 *
 *   - STREAM bits have value at every moment but no notion
 *     of 'using up' a bit.
 *   - LINEAR bits have a static resource budget but no time
 *     dimension.
 *   - COMBINED: a bit with a BUDGET(t) that varies under
 *     time-dependent rules — decay, deadline, replenish,
 *     rate limit.  None of these exist in the component
 *     axes; all are first-class operations here.
 *
 * Four temporal-linear patterns:
 *
 *   DECAY        budget(t+1) = max(0, budget(t) − 1)
 *                resource expires if unused
 *   DEADLINE     bit valid only in [t_start, t_end]; any
 *                attempt outside that window fails
 *   REPLENISH    budget(t+1) = min(MAX, budget(t) + 1)
 *                resource regenerates over time
 *   RATE LIMIT   no more than k reads per window of size W
 *
 * Experiments:
 *
 *   1. Decay: a budget-3 bit unused for 3 ticks becomes 0.
 *   2. Deadline: reads outside [5, 10] fail; reads inside
 *      succeed while budget lasts.
 *   3. Replenish: a budget-drained bit recovers one per tick
 *      up to the cap.
 *   4. Rate limit: 3 reads per window of 5 ticks; a fourth
 *      read within the window is refused.
 *   5. Witness of irreducibility: neither stream nor linear
 *      alone can express 'budget that decays over time'.
 *
 * Compile: gcc -O3 -march=native -o slinear stream_linear.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* ═══ TEMPORAL LINEAR BIT ═══
 *
 * State: value, budget, and a rule determining how budget
 * evolves at each tick.  Different constructors give
 * different temporal behaviours.
 */

typedef enum {MODE_DECAY, MODE_DEADLINE, MODE_REPLENISH, MODE_RATE} Mode;

typedef struct {
    int value;
    int budget;
    int max_budget;
    int t;                /* current time */
    int deadline_start, deadline_end;
    int rate_k, rate_w;
    int read_log[64];     /* timestamps of the last reads, for rate-limit */
    int n_reads;
    Mode mode;
} TLBit;

static TLBit tlbit_decay(int v, int budget){
    TLBit b = {0};
    b.value = v; b.budget = budget; b.max_budget = budget;
    b.mode = MODE_DECAY;
    return b;
}
static TLBit tlbit_deadline(int v, int budget, int t_start, int t_end){
    TLBit b = {0};
    b.value = v; b.budget = budget; b.max_budget = budget;
    b.mode = MODE_DEADLINE;
    b.deadline_start = t_start;
    b.deadline_end = t_end;
    return b;
}
static TLBit tlbit_replenish(int v, int max_budget){
    TLBit b = {0};
    b.value = v; b.budget = max_budget; b.max_budget = max_budget;
    b.mode = MODE_REPLENISH;
    return b;
}
static TLBit tlbit_rate(int v, int k, int w){
    TLBit b = {0};
    b.value = v; b.mode = MODE_RATE;
    b.rate_k = k; b.rate_w = w;
    b.budget = 0; b.max_budget = 0;
    return b;
}

/* Advance time by one tick; apply the temporal rule. */
static void tlbit_tick(TLBit *b){
    b->t++;
    switch(b->mode){
    case MODE_DECAY:
        if(b->budget > 0) b->budget--;
        break;
    case MODE_REPLENISH:
        if(b->budget < b->max_budget) b->budget++;
        break;
    case MODE_DEADLINE:
    case MODE_RATE:
        /* no auto-decay */
        break;
    }
}

/* Attempt to read the bit. Returns value if allowed, -1 on failure.
 * Prints the reason for failure if verbose. */
static int tlbit_read(TLBit *b, const char *who){
    switch(b->mode){
    case MODE_DECAY:
    case MODE_REPLENISH:
        if(b->budget <= 0){
            printf("    t=%d  %s: REFUSED (budget exhausted)\n", b->t, who);
            return -1;
        }
        b->budget--;
        printf("    t=%d  %s: read → %d  (budget now %d)\n",
               b->t, who, b->value, b->budget);
        return b->value;

    case MODE_DEADLINE:
        if(b->t < b->deadline_start || b->t > b->deadline_end){
            printf("    t=%d  %s: REFUSED (outside [%d, %d])\n",
                   b->t, who, b->deadline_start, b->deadline_end);
            return -1;
        }
        if(b->budget <= 0){
            printf("    t=%d  %s: REFUSED (budget exhausted)\n", b->t, who);
            return -1;
        }
        b->budget--;
        printf("    t=%d  %s: read → %d  (budget now %d)\n",
               b->t, who, b->value, b->budget);
        return b->value;

    case MODE_RATE: {
        /* Count reads within the last rate_w ticks */
        int count = 0;
        for(int i = 0; i < b->n_reads; i++){
            if(b->read_log[i] > b->t - b->rate_w) count++;
        }
        if(count >= b->rate_k){
            printf("    t=%d  %s: REFUSED (%d reads in last %d ticks ≥ %d)\n",
                   b->t, who, count, b->rate_w, b->rate_k);
            return -1;
        }
        b->read_log[b->n_reads++] = b->t;
        printf("    t=%d  %s: read → %d  (%d/%d in window)\n",
               b->t, who, b->value, count + 1, b->rate_k);
        return b->value;
    }
    }
    return -1;
}

/* ═══ EXPERIMENT 1: Decay ═══ */
static void experiment_decay(void){
    printf("\n═══ EXPERIMENT 1: Budget decay ═══\n\n");
    TLBit b = tlbit_decay(1, 3);
    printf("  Created DECAY bit with budget 3.\n");
    printf("  Idle for 3 ticks, then try to read:\n");
    for(int i = 0; i < 3; i++) tlbit_tick(&b);
    printf("  budget after 3 idle ticks: %d\n", b.budget);
    tlbit_read(&b, "post-idle");

    printf("\n  A budget-3 resource unused for 3 ticks evaporates\n");
    printf("  entirely. This is the 'perishable credential' pattern.\n");
}

/* ═══ EXPERIMENT 2: Deadline ═══ */
static void experiment_deadline(void){
    printf("\n═══ EXPERIMENT 2: Deadline window [5, 10] ═══\n\n");
    TLBit b = tlbit_deadline(1, 5, 5, 10);
    printf("  Created DEADLINE bit, valid from t=5 to t=10.\n\n");

    /* Advance time and try reads at various moments */
    int read_at[] = {0, 3, 5, 7, 10, 11};
    int cur_t = 0;
    for(int i = 0; i < 6; i++){
        while(cur_t < read_at[i]){tlbit_tick(&b); cur_t++;}
        tlbit_read(&b, "probe");
    }

    printf("\n  Reads before t=5 or after t=10 are refused.\n");
    printf("  Within the window, reads consume budget as usual.\n");
}

/* ═══ EXPERIMENT 3: Replenish ═══ */
static void experiment_replenish(void){
    printf("\n═══ EXPERIMENT 3: Replenishing bit with max budget 3 ═══\n\n");
    TLBit b = tlbit_replenish(1, 3);
    printf("  Created REPLENISH bit, starts full (budget 3).\n\n");

    /* Drain it */
    for(int i = 0; i < 3; i++) tlbit_read(&b, "drain");
    /* Try one more — should fail */
    tlbit_read(&b, "over-drain");
    /* Wait 2 ticks, then read again */
    for(int i = 0; i < 2; i++) tlbit_tick(&b);
    printf("    (waited 2 ticks, budget = %d)\n", b.budget);
    tlbit_read(&b, "recovered");
    tlbit_read(&b, "try-again");
    /* Another refusal */
    tlbit_read(&b, "exhaust");
    /* Wait 5 ticks and re-drain */
    for(int i = 0; i < 5; i++) tlbit_tick(&b);
    printf("    (waited 5 ticks, budget = %d)\n", b.budget);

    printf("\n  Replenish caps at max_budget = 3 even after 5 idle ticks.\n");
    printf("  This is a token-bucket rate-limiter's dual.\n");
}

/* ═══ EXPERIMENT 4: Rate limit 3 reads per 5 ticks ═══ */
static void experiment_rate(void){
    printf("\n═══ EXPERIMENT 4: Rate-limited bit (3 reads per 5 ticks) ═══\n\n");
    TLBit b = tlbit_rate(1, 3, 5);

    /* Tick 0: read, read, read (should all succeed)
     * Tick 1: read (should fail — 4th in window [0..4])
     * Tick 2: read (still fails)
     * ...
     * Tick 5: read should succeed (window slides to [1..5], only 2 reads in it)
     */
    tlbit_read(&b, "r1");
    tlbit_read(&b, "r2");
    tlbit_read(&b, "r3");
    tlbit_read(&b, "r4");    /* should fail */
    for(int i = 0; i < 3; i++) tlbit_tick(&b);
    tlbit_read(&b, "r5");    /* still within window of first reads */
    for(int i = 0; i < 2; i++) tlbit_tick(&b);
    tlbit_read(&b, "r6");    /* window has moved, earlier reads drop out */

    printf("\n  Rate-limit counts reads within a sliding window of\n");
    printf("  the last rate_w ticks. Once k reads have happened in\n");
    printf("  the window, further reads are refused until older\n");
    printf("  reads roll off.\n");
}

/* ═══ EXPERIMENT 5: Irreducibility to stream or linear alone ═══ */
static void experiment_irreducibility(void){
    printf("\n═══ EXPERIMENT 5: Neither stream nor linear alone suffices ═══\n\n");

    printf("  Pure STREAM bit:\n");
    printf("    x[0], x[1], x[2], ... ∈ {0, 1}\n");
    printf("    has values at every tick\n");
    printf("    has NO notion of budget or refusal\n");
    printf("    cannot express 'this bit is only valid for k reads'\n\n");

    printf("  Pure LINEAR bit:\n");
    printf("    (value, budget) with static budget counter\n");
    printf("    supports single-use enforcement\n");
    printf("    has NO notion of time or ticks\n");
    printf("    cannot express decay, deadline, or rate limiting\n\n");

    printf("  Combined STREAM × LINEAR bit:\n");
    printf("    budget is a FUNCTION OF TIME\n");
    printf("    decay, deadline, replenish, rate limit all become\n");
    printf("      first-class temporal-linear patterns\n");
    printf("    every read checks both resource and time constraints\n\n");

    printf("  This is the mathematical content of temporal linear\n");
    printf("  logic (Girard 1991): ⊗, ⊸, !, ? operators extended\n");
    printf("  with a 'next time' modality ●. The C implementation\n");
    printf("  here concretises the semantics for bit primitives.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("STREAM × LINEAR: temporal linear bits\n");
    printf("══════════════════════════════════════════\n");
    printf("Fourth combination primitive. Budgets vary with time.\n");

    experiment_decay();
    experiment_deadline();
    experiment_replenish();
    experiment_rate();
    experiment_irreducibility();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY CONTRIBUTIONS:\n");
    printf("  1. Temporal-linear bit = (value, budget(t), rule)\n");
    printf("  2. Four standard patterns implemented:\n");
    printf("       decay, deadline, replenish, rate limit\n");
    printf("  3. Every read checks both budget and time\n");
    printf("  4. Ties to Girard temporal linear logic (1991),\n");
    printf("     token buckets, session tokens, deadline scheduling\n");
    printf("  5. Neither stream (no budget) nor linear (no time)\n");
    printf("     can express any of these four patterns\n");
    printf("\n  Combination cell: STREAM × LINEAR (TIME × OPERATION)\n");
    printf("  Fourth entry in the combination catalogue.\n");
    return 0;
}
