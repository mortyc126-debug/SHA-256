/*
 * BITBRAIN v5.2: + HIERARCHY (two sensory layers stacked)
 * ========================================================
 *
 * Sensory L1: low-level features (AND, OR detectors)
 * Sensory L2: high-level composition (takes L1 features as input)
 *
 * Like V1→V2 in visual cortex.
 *
 * Test: (A∧B) ⊕ (C∧D) — hierarchical composition
 *   Flat network: 300+ epochs
 *   Hierarchical: should be faster (L1 learns ANDs, L2 learns XOR)
 *
 * Compile: gcc -O3 -march=native -o bitbrain5_2 bitbrain_v5_2.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define L1_IN 4
#define L1_H 8
#define L1_OUT 4   /* L1 produces 4 intermediate features */
#define L2_IN 4    /* L2 takes L1 outputs */
#define L2_H 6
#define L2_OUT 1

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){
    unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];
    unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;
    s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);
    rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){
    rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;
    rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;
    for(int i=0;i<20;i++)rng_next();}

/* ═══ Layer 1: feature detectors ═══ */
typedef struct {
    int8_t W[L1_IN][L1_H];
    int8_t W2[L1_H][L1_OUT];
    int flip_prob;
} SensoryL1;

static void l1_init(SensoryL1 *s){
    for(int i=0;i<L1_IN;i++) for(int j=0;j<L1_H;j++) s->W[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<L1_H;i++) for(int j=0;j<L1_OUT;j++) s->W2[i][j] = (rng_next()&1)?1:-1;
    s->flip_prob = 30;
}

static void l1_forward(SensoryL1 *s, const int8_t *in, int8_t *out){
    int8_t h[L1_H];
    for(int j=0;j<L1_H;j++){
        int sum=0;for(int i=0;i<L1_IN;i++) sum += s->W[i][j]*in[i];
        h[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<L1_OUT;j++){
        int sum=0;for(int i=0;i<L1_H;i++) sum += s->W2[i][j]*h[i];
        out[j] = (sum>=0)?1:-1;
    }
}

/* Train L1 with given "features of interest" as auxiliary targets */
static void l1_train_feature(SensoryL1 *s, const int8_t *in, int feat_idx, int target){
    int8_t h[L1_H];
    for(int j=0;j<L1_H;j++){
        int sum=0;for(int i=0;i<L1_IN;i++) sum += s->W[i][j]*in[i];
        h[j] = (sum>=0)?1:-1;
    }
    int sum = 0;
    for(int i=0;i<L1_H;i++) sum += s->W2[i][feat_idx]*h[i];
    int out = (sum>=0)?1:-1;
    if(out == target) return;

    int8_t want_h[L1_H] = {0};
    for(int i=0;i<L1_H;i++){
        int contrib = s->W2[i][feat_idx]*h[i];
        if(contrib != target){
            if((int)(rng_next()%100) < s->flip_prob) s->W2[i][feat_idx] = -s->W2[i][feat_idx];
        }
        want_h[i] = target * s->W2[i][feat_idx];
    }
    for(int j=0;j<L1_H;j++){
        if(want_h[j] == h[j]) continue;
        for(int i=0;i<L1_IN;i++){
            int contrib = s->W[i][j]*in[i];
            if(contrib != want_h[j]){
                if((int)(rng_next()%100) < s->flip_prob) s->W[i][j] = -s->W[i][j];
            }
        }
    }
}

/* ═══ Layer 2: composition ═══ */
typedef struct {
    int8_t W[L2_IN][L2_H];
    int8_t W2[L2_H];
    int flip_prob;
} SensoryL2;

static void l2_init(SensoryL2 *s){
    for(int i=0;i<L2_IN;i++) for(int j=0;j<L2_H;j++) s->W[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<L2_H;i++) s->W2[i] = (rng_next()&1)?1:-1;
    s->flip_prob = 30;
}

static int8_t l2_forward(SensoryL2 *s, const int8_t *in){
    int8_t h[L2_H];
    for(int j=0;j<L2_H;j++){
        int sum=0;for(int i=0;i<L2_IN;i++) sum += s->W[i][j]*in[i];
        h[j] = (sum>=0)?1:-1;
    }
    int sum = 0;
    for(int i=0;i<L2_H;i++) sum += s->W2[i]*h[i];
    return (sum>=0)?1:-1;
}

static void l2_train(SensoryL2 *s, const int8_t *in, int target){
    int8_t h[L2_H];
    for(int j=0;j<L2_H;j++){
        int sum=0;for(int i=0;i<L2_IN;i++) sum += s->W[i][j]*in[i];
        h[j] = (sum>=0)?1:-1;
    }
    int out_sum = 0;
    for(int i=0;i<L2_H;i++) out_sum += s->W2[i]*h[i];
    int out = (out_sum>=0)?1:-1;
    if(out == target) return;

    int8_t want_h[L2_H] = {0};
    for(int i=0;i<L2_H;i++){
        int contrib = s->W2[i]*h[i];
        if(contrib != target){
            if((int)(rng_next()%100) < s->flip_prob) s->W2[i] = -s->W2[i];
        }
        want_h[i] = target * s->W2[i];
    }
    for(int j=0;j<L2_H;j++){
        if(want_h[j] == h[j]) continue;
        for(int i=0;i<L2_IN;i++){
            int contrib = s->W[i][j]*in[i];
            if(contrib != want_h[j]){
                if((int)(rng_next()%100) < s->flip_prob) s->W[i][j] = -s->W[i][j];
            }
        }
    }
}

/* ═══ Hierarchical sensory: L1 → L2 ═══ */
typedef struct {
    SensoryL1 l1;
    SensoryL2 l2;
} Hierarchical;

static void hier_init(Hierarchical *h){
    l1_init(&h->l1);
    l2_init(&h->l2);
}

static int8_t hier_forward(Hierarchical *h, const int8_t *in){
    int8_t features[L1_OUT];
    l1_forward(&h->l1, in, features);
    return l2_forward(&h->l2, features);
}

/* Train hierarchical end-to-end.
 * Strategy: train L1 with auxiliary features that are USEFUL for L2.
 * For our task: L1 learns AND-like features, L2 learns XOR on them. */
static void hier_train(Hierarchical *h, const int8_t *in, int target){
    /* Get current L1 features */
    int8_t features[L1_OUT];
    l1_forward(&h->l1, in, features);

    /* Train L2 on these features */
    l2_train(&h->l2, features, target);

    /* For L1, we don't have direct targets for its features.
       Use a trick: pick a random L1 feature, flip it, see if L2 would
       predict correctly. If yes — that feature should have been different. */
    for(int f = 0; f < L1_OUT; f++){
        int8_t flipped[L1_OUT];
        memcpy(flipped, features, L1_OUT);
        flipped[f] = -flipped[f];
        int flipped_pred = l2_forward(&h->l2, flipped);
        int orig_pred = l2_forward(&h->l2, features);

        /* If flipping this feature would help, train L1 to produce flipped */
        if(orig_pred != target && flipped_pred == target){
            /* Feature f should have been -features[f] */
            l1_train_feature(&h->l1, in, f, -features[f]);
        }
    }
}

/* ═══ Flat baseline ═══ */
#define F_IN 4
#define F_H1 16
#define F_H2 8

typedef struct {
    int8_t W1[F_IN][F_H1];
    int8_t W2[F_H1][F_H2];
    int8_t W3[F_H2];
    int flip_prob;
} Flat;

static void flat_init(Flat *f){
    for(int i=0;i<F_IN;i++) for(int j=0;j<F_H1;j++) f->W1[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<F_H1;i++) for(int j=0;j<F_H2;j++) f->W2[i][j] = (rng_next()&1)?1:-1;
    for(int i=0;i<F_H2;i++) f->W3[i] = (rng_next()&1)?1:-1;
    f->flip_prob = 30;
}

static int8_t flat_forward(Flat *f, const int8_t *in){
    int8_t h1[F_H1], h2[F_H2];
    for(int j=0;j<F_H1;j++){
        int sum=0;for(int i=0;i<F_IN;i++) sum += f->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<F_H2;j++){
        int sum=0;for(int i=0;i<F_H1;i++) sum += f->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int sum = 0;
    for(int i=0;i<F_H2;i++) sum += f->W3[i]*h2[i];
    return (sum>=0)?1:-1;
}

static void flat_train(Flat *f, const int8_t *in, int target){
    int8_t h1[F_H1], h2[F_H2];
    for(int j=0;j<F_H1;j++){
        int sum=0;for(int i=0;i<F_IN;i++) sum += f->W1[i][j]*in[i];
        h1[j] = (sum>=0)?1:-1;
    }
    for(int j=0;j<F_H2;j++){
        int sum=0;for(int i=0;i<F_H1;i++) sum += f->W2[i][j]*h1[i];
        h2[j] = (sum>=0)?1:-1;
    }
    int out_sum = 0;
    for(int i=0;i<F_H2;i++) out_sum += f->W3[i]*h2[i];
    int out = (out_sum>=0)?1:-1;
    if(out == target) return;

    int8_t want_h2[F_H2] = {0};
    for(int i=0;i<F_H2;i++){
        int contrib = f->W3[i]*h2[i];
        if(contrib != target){
            if((int)(rng_next()%100) < f->flip_prob) f->W3[i] = -f->W3[i];
        }
        want_h2[i] = target * f->W3[i];
    }
    int8_t want_h1[F_H1] = {0};
    for(int j=0;j<F_H2;j++){
        if(want_h2[j] == h2[j]) continue;
        for(int i=0;i<F_H1;i++){
            int contrib = f->W2[i][j]*h1[i];
            if(contrib != want_h2[j]){
                if((int)(rng_next()%100) < f->flip_prob) f->W2[i][j] = -f->W2[i][j];
            }
        }
        for(int i=0;i<F_H1;i++){
            int w = f->W2[i][j];
            int wnt = want_h2[j]*w;
            if(want_h1[i] == 0) want_h1[i] = wnt;
            else if(want_h1[i] != wnt) want_h1[i] = 0;
        }
    }
    for(int j=0;j<F_H1;j++){
        if(want_h1[j] == 0 || want_h1[j] == h1[j]) continue;
        for(int i=0;i<F_IN;i++){
            int contrib = f->W1[i][j]*in[i];
            if(contrib != want_h1[j]){
                if((int)(rng_next()%100) < f->flip_prob) f->W1[i][j] = -f->W1[i][j];
            }
        }
    }
}

/* ═══ TEST: (A∧B) ⊕ (C∧D) ═══ */
static int target_compositional(const int8_t *in){
    int ab = (in[0]==1 && in[1]==1) ? 1 : -1;
    int cd = (in[2]==1 && in[3]==1) ? 1 : -1;
    return ab * cd; /* XOR in ±1 representation */
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v5.2: + HIERARCHY\n");
    printf("══════════════════════════════════════════\n\n");

    printf("Task: (A∧B) ⊕ (C∧D)\n");
    printf("  Compositional: learn AND features first, then XOR them\n\n");

    /* All 16 examples */
    int8_t inputs[16][4];
    int targets[16];
    for(int m = 0; m < 16; m++){
        for(int i = 0; i < 4; i++) inputs[m][i] = ((m>>i)&1)?1:-1;
        targets[m] = target_compositional(inputs[m]);
    }

    int max_epochs = 500;

    /* ── Flat baseline ── */
    printf("FLAT network (F_IN=4 → H1=16 → H2=8 → 1):\n");
    int flat_best = 0;
    int flat_epochs = -1;
    for(int trial = 0; trial < 5; trial++){
        Flat f;
        rng_seed(42 + trial * 100);
        flat_init(&f);
        for(int epoch = 0; epoch < max_epochs; epoch++){
            for(int m = 0; m < 16; m++) flat_train(&f, inputs[m], targets[m]);
            if(epoch > 50 && f.flip_prob > 5) f.flip_prob--;
            int correct = 0;
            for(int m = 0; m < 16; m++) if(flat_forward(&f, inputs[m]) == targets[m]) correct++;
            if(correct > flat_best){
                flat_best = correct;
                if(correct == 16){
                    flat_epochs = epoch;
                    goto flat_done;
                }
            }
        }
    }
    flat_done:
    if(flat_epochs >= 0) printf("  ✓ Converged in %d epochs\n", flat_epochs);
    else printf("  Best: %d/16\n", flat_best);

    /* ── Hierarchical ── */
    printf("\nHIERARCHICAL (L1: 4→8→4, L2: 4→6→1):\n");
    int hier_best = 0;
    int hier_epochs = -1;
    for(int trial = 0; trial < 5; trial++){
        Hierarchical h;
        rng_seed(42 + trial * 100);
        hier_init(&h);
        for(int epoch = 0; epoch < max_epochs; epoch++){
            for(int m = 0; m < 16; m++) hier_train(&h, inputs[m], targets[m]);
            if(epoch > 50){
                if(h.l1.flip_prob > 5) h.l1.flip_prob--;
                if(h.l2.flip_prob > 5) h.l2.flip_prob--;
            }
            int correct = 0;
            for(int m = 0; m < 16; m++) if(hier_forward(&h, inputs[m]) == targets[m]) correct++;
            if(correct > hier_best){
                hier_best = correct;
                if(correct == 16){
                    hier_epochs = epoch;
                    goto hier_done;
                }
            }
        }
    }
    hier_done:
    if(hier_epochs >= 0) printf("  ✓ Converged in %d epochs\n", hier_epochs);
    else printf("  Best: %d/16\n", hier_best);

    printf("\n═══ COMPARISON ═══\n");
    printf("Flat:          best=%d/16, epochs=%d\n", flat_best, flat_epochs);
    printf("Hierarchical:  best=%d/16, epochs=%d\n", hier_best, hier_epochs);

    if(flat_epochs < 0 && hier_epochs >= 0){
        printf("\n✓ Hierarchy succeeds where flat fails\n");
    } else if(hier_epochs >= 0 && flat_epochs >= 0 && hier_epochs < flat_epochs){
        printf("\n✓ Hierarchy %dx faster (%d vs %d)\n",
               flat_epochs/hier_epochs, hier_epochs, flat_epochs);
    } else if(hier_epochs >= 0 && flat_epochs >= 0){
        printf("\n~ Hierarchy: %d vs flat %d (hierarchy slower)\n",
               hier_epochs, flat_epochs);
    } else {
        printf("\n~ Both: flat %d, hier %d\n", flat_best, hier_best);
    }

    return 0;
}
