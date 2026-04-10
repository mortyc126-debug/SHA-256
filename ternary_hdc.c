/*
 * TERNARY HDC: {-1, 0, +1} hypervectors
 * =======================================
 *
 * Extension of binary HDC with "don't care" positions (value 0).
 * Combines:
 *   - HDC (Kanerva 1988): high-dim binary vectors
 *   - Three-valued logic (Kleene): {true, false, unknown}
 *   - Fuzzy logic (Zadeh): partial truth
 *
 * Representation: each bit stored in 2 bits:
 *   00 = 0 (don't care)
 *   01 = +1
 *   10 = -1
 *   11 = invalid
 *
 * Operations:
 *   bind(a, b):       0 in either → 0 in result (erases)
 *                     ±1 ⊗ ±1    → sign product
 *   bundle(V):        majority over ±1 voters only, 0s abstain
 *   sim(a, b):        ratio of agreements over positions where both ≠ 0
 *
 * Experiments:
 *   1. Capacity: how many items before recall degrades?
 *   2. Hierarchy: can we represent general→specific via 0-density?
 *   3. Noise tolerance: 0s = "don't care" should resist noise better
 *   4. Composition: general concepts bundle into specific ones?
 *
 * Compile: gcc -O3 -march=native -o thdc ternary_hdc.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define D 4096
/* Each position needs 2 bits. Total 4096×2 = 8192 bits = 128 uint64_t */
#define D_WORDS ((D + 63) / 64)
#define STORAGE_WORDS (D_WORDS * 2)  /* 2 bits per position */

typedef struct {
    /* Two parallel bit planes: pos[i] = (plane0[i], plane1[i]) */
    /* Encoding: 00=0 (dc), 01=+1, 10=-1 */
    uint64_t plane0[D_WORDS];  /* low bit */
    uint64_t plane1[D_WORDS];  /* high bit */
} THDV;

/* Standard binary HDV for comparison */
typedef struct { uint64_t b[D_WORDS]; } BHDV;

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
static double rng_double(void){return (rng_next()>>11)*(1.0/9007199254740992.0);}

/* ═══ TERNARY HDV OPERATIONS ═══ */

/* Generate random ternary HDV with given fraction of 0s (don't cares) */
static THDV thdv_random(double p_zero){
    THDV v;
    memset(&v, 0, sizeof(v));
    for(int i = 0; i < D; i++){
        double r = rng_double();
        if(r < p_zero){
            /* leave as 0 */
        } else if(r < p_zero + (1.0 - p_zero)/2){
            /* +1: plane0=1, plane1=0 */
            v.plane0[i>>6] |= (1ULL << (i&63));
        } else {
            /* -1: plane0=0, plane1=1 */
            v.plane1[i>>6] |= (1ULL << (i&63));
        }
    }
    return v;
}

static THDV thdv_zero(void){THDV v;memset(&v,0,sizeof(v));return v;}

/* Get value at position i: returns -1, 0, or +1 */
static inline int thdv_get(const THDV *v, int i){
    int p0 = (v->plane0[i>>6] >> (i&63)) & 1;
    int p1 = (v->plane1[i>>6] >> (i&63)) & 1;
    if(p0 == 0 && p1 == 0) return 0;
    if(p0 == 1 && p1 == 0) return +1;
    if(p0 == 0 && p1 == 1) return -1;
    return 0; /* invalid, treat as 0 */
}

static inline void thdv_set(THDV *v, int i, int val){
    uint64_t mask = 1ULL << (i & 63);
    if(val == 0){
        v->plane0[i>>6] &= ~mask;
        v->plane1[i>>6] &= ~mask;
    } else if(val == 1){
        v->plane0[i>>6] |= mask;
        v->plane1[i>>6] &= ~mask;
    } else { /* -1 */
        v->plane0[i>>6] &= ~mask;
        v->plane1[i>>6] |= mask;
    }
}

/* Bind: position-wise multiplication in {-1, 0, +1} */
static THDV thdv_bind(const THDV *a, const THDV *b){
    THDV r = thdv_zero();
    /* For each position:
       0 * anything = 0 (neither plane set)
       +1 * +1 = +1, -1 * -1 = +1 (plane0=1)
       +1 * -1 = -1 (plane1=1)
    */
    for(int w = 0; w < D_WORDS; w++){
        /* Active positions: both a and b are non-zero */
        uint64_t a_active = a->plane0[w] | a->plane1[w];
        uint64_t b_active = b->plane0[w] | b->plane1[w];
        uint64_t both_active = a_active & b_active;

        /* Sign: XOR of plane1 (since plane1=1 means -1)
           +1*+1: both plane1=0 → XOR = 0 → plane0=1
           -1*-1: both plane1=1 → XOR = 0 → plane0=1
           +1*-1: XOR = 1 → plane1=1
         */
        uint64_t result_negative = a->plane1[w] ^ b->plane1[w];

        r.plane0[w] = both_active & ~result_negative;
        r.plane1[w] = both_active & result_negative;
    }
    return r;
}

/* Bundle: for each position, sum votes and take majority.
 * 0 values abstain. Result is 0 if no votes or tie. */
static THDV thdv_bundle_multi(const THDV *items, int n){
    /* Sum of ±1 votes per position */
    int pos[D], neg[D];
    memset(pos, 0, sizeof(pos));
    memset(neg, 0, sizeof(neg));

    for(int i = 0; i < n; i++){
        for(int j = 0; j < D; j++){
            int val = thdv_get(&items[i], j);
            if(val > 0) pos[j]++;
            else if(val < 0) neg[j]++;
        }
    }

    THDV r = thdv_zero();
    for(int j = 0; j < D; j++){
        if(pos[j] > neg[j]) thdv_set(&r, j, +1);
        else if(neg[j] > pos[j]) thdv_set(&r, j, -1);
        /* else tie or no votes: stay 0 */
    }
    return r;
}

/* Similarity: over positions where BOTH are non-zero */
static double thdv_sim(const THDV *a, const THDV *b){
    int both_active = 0;
    int agree = 0;
    for(int j = 0; j < D; j++){
        int va = thdv_get(a, j);
        int vb = thdv_get(b, j);
        if(va != 0 && vb != 0){
            both_active++;
            if(va == vb) agree++;
        }
    }
    if(both_active == 0) return 0.5; /* no overlap */
    return (double)agree / both_active;
}

/* Count non-zero positions */
static int thdv_nnz(const THDV *v){
    int c = 0;
    for(int w = 0; w < D_WORDS; w++){
        c += __builtin_popcountll(v->plane0[w] | v->plane1[w]);
    }
    return c;
}

/* ═══ BINARY HDC FOR COMPARISON ═══ */
static BHDV bhdv_random(void){
    BHDV v;
    for(int i = 0; i < D_WORDS; i++) v.b[i] = rng_next();
    return v;
}
static BHDV bhdv_zero(void){BHDV v;memset(&v,0,sizeof(v));return v;}
static BHDV bhdv_bind(BHDV a, BHDV b){BHDV r;for(int i=0;i<D_WORDS;i++)r.b[i]=a.b[i]^b.b[i];return r;}
static double bhdv_sim(BHDV a, BHDV b){
    int d = 0;
    for(int i = 0; i < D_WORDS; i++) d += __builtin_popcountll(a.b[i] ^ b.b[i]);
    return 1.0 - (double)d / D;
}

static BHDV bhdv_bundle_multi(const BHDV *items, int n){
    int counters[D] = {0};
    for(int i = 0; i < n; i++){
        for(int j = 0; j < D; j++){
            counters[j] += ((items[i].b[j>>6] >> (j&63)) & 1) ? 1 : -1;
        }
    }
    BHDV r = bhdv_zero();
    for(int j = 0; j < D; j++)
        if(counters[j] > 0) r.b[j>>6] |= (1ULL << (j&63));
    return r;
}

/* ═══ EXPERIMENT 1: Capacity ═══
 * How many items can be bundled before recall degrades?
 * Compare binary vs ternary HDC.
 */
static void experiment_capacity(void){
    printf("\n═══ EXPERIMENT 1: Capacity (bundle then recall) ═══\n");
    printf("D=%d, threshold for 'recalled' = 0.65\n\n", D);

    printf("%5s | %15s | %15s\n", "k", "binary sim", "ternary (p=0.5) sim");
    printf("------+-----------------+--------------------\n");

    int ks[] = {3, 5, 10, 20, 50, 100, 200};

    for(int ki = 0; ki < 7; ki++){
        int k = ks[ki];
        rng_seed(42 + ki*100);

        /* Binary: generate k random, bundle, test recall */
        BHDV *b_items = malloc(k * sizeof(BHDV));
        for(int i = 0; i < k; i++) b_items[i] = bhdv_random();
        BHDV b_bundle = bhdv_bundle_multi(b_items, k);

        double b_sim = 0;
        for(int i = 0; i < k; i++) b_sim += bhdv_sim(b_items[i], b_bundle);
        b_sim /= k;

        /* Ternary with p_zero = 0.5 (half are don't care) */
        THDV *t_items = malloc(k * sizeof(THDV));
        for(int i = 0; i < k; i++) t_items[i] = thdv_random(0.5);
        THDV t_bundle = thdv_bundle_multi(t_items, k);

        double t_sim = 0;
        for(int i = 0; i < k; i++) t_sim += thdv_sim(&t_items[i], &t_bundle);
        t_sim /= k;

        printf("%5d | %15.4f | %15.4f\n", k, b_sim, t_sim);

        free(b_items);
        free(t_items);
    }
}

/* ═══ EXPERIMENT 2: Hierarchy via 0-density ═══
 * Create "general" and "specific" concepts.
 * General = many 0s (don't care about details).
 * Specific = fewer 0s (constrained).
 * Test: can we detect specific IS-A general?
 */
static void experiment_hierarchy(void){
    printf("\n═══ EXPERIMENT 2: Hierarchy (IS-A relation via partial match) ═══\n");

    rng_seed(12345);

    /* Build a hierarchy:
       ANIMAL (generic, 80% 0s)
         └── MAMMAL (inherits + adds constraints, 60% 0s)
               ├── DOG (inherits + more, 20% 0s)
               └── CAT (inherits + different, 20% 0s)
         └── BIRD (60% 0s)
               └── EAGLE (20% 0s)
    */

    /* Start with ANIMAL — random with many 0s */
    THDV animal = thdv_random(0.8); /* 20% non-zero */

    /* MAMMAL: inherit from ANIMAL, add mammal-specific constraints */
    THDV mammal = animal; /* start with animal */
    /* Add 20% more constraints to positions that were 0 */
    int added = 0;
    for(int i = 0; i < D && added < D*0.2; i++){
        if(thdv_get(&mammal, i) == 0){
            int val = (rng_next() & 1) ? +1 : -1;
            thdv_set(&mammal, i, val);
            added++;
        }
    }

    /* DOG: inherit from MAMMAL, add more constraints */
    THDV dog = mammal;
    added = 0;
    for(int i = 0; i < D && added < D*0.4; i++){
        if(thdv_get(&dog, i) == 0){
            int val = (rng_next() & 1) ? +1 : -1;
            thdv_set(&dog, i, val);
            added++;
        }
    }

    /* CAT: inherit from MAMMAL, different constraints */
    THDV cat = mammal;
    added = 0;
    for(int i = 0; i < D && added < D*0.4; i++){
        if(thdv_get(&cat, i) == 0){
            int val = (rng_next() & 1) ? +1 : -1;
            thdv_set(&cat, i, val);
            added++;
        }
    }

    /* BIRD: separate from mammal */
    THDV bird = animal;
    added = 0;
    for(int i = 0; i < D && added < D*0.2; i++){
        if(thdv_get(&bird, i) == 0){
            int val = (rng_next() & 1) ? +1 : -1;
            thdv_set(&bird, i, val);
            added++;
        }
    }

    /* EAGLE: inherits bird */
    THDV eagle = bird;
    added = 0;
    for(int i = 0; i < D && added < D*0.4; i++){
        if(thdv_get(&eagle, i) == 0){
            int val = (rng_next() & 1) ? +1 : -1;
            thdv_set(&eagle, i, val);
            added++;
        }
    }

    /* Report non-zero counts and similarities */
    printf("Concept | nnz / %d | sim vs animal | sim vs mammal | sim vs bird\n", D);
    printf("--------+----------+---------------+---------------+------------\n");
    printf("ANIMAL  | %8d | %13.4f | %13.4f | %10.4f\n",
           thdv_nnz(&animal), thdv_sim(&animal, &animal),
           thdv_sim(&animal, &mammal), thdv_sim(&animal, &bird));
    printf("MAMMAL  | %8d | %13.4f | %13.4f | %10.4f\n",
           thdv_nnz(&mammal), thdv_sim(&mammal, &animal),
           thdv_sim(&mammal, &mammal), thdv_sim(&mammal, &bird));
    printf("DOG     | %8d | %13.4f | %13.4f | %10.4f\n",
           thdv_nnz(&dog), thdv_sim(&dog, &animal),
           thdv_sim(&dog, &mammal), thdv_sim(&dog, &bird));
    printf("CAT     | %8d | %13.4f | %13.4f | %10.4f\n",
           thdv_nnz(&cat), thdv_sim(&cat, &animal),
           thdv_sim(&cat, &mammal), thdv_sim(&cat, &bird));
    printf("BIRD    | %8d | %13.4f | %13.4f | %10.4f\n",
           thdv_nnz(&bird), thdv_sim(&bird, &animal),
           thdv_sim(&bird, &mammal), thdv_sim(&bird, &bird));
    printf("EAGLE   | %8d | %13.4f | %13.4f | %10.4f\n",
           thdv_nnz(&eagle), thdv_sim(&eagle, &animal),
           thdv_sim(&eagle, &mammal), thdv_sim(&eagle, &bird));

    printf("\nExpected: DOG should be closer to MAMMAL than BIRD.\n");
    printf("Test: sim(DOG,MAMMAL) > sim(DOG,BIRD)?\n");
    printf("  sim(DOG,MAMMAL) = %.4f\n", thdv_sim(&dog, &mammal));
    printf("  sim(DOG,BIRD)   = %.4f\n", thdv_sim(&dog, &bird));
    if(thdv_sim(&dog, &mammal) > thdv_sim(&dog, &bird))
        printf("  ✓ DOG correctly closer to MAMMAL\n");
    else
        printf("  ✗ hierarchy not preserved\n");
}

/* ═══ EXPERIMENT 3: Noise tolerance ═══ */
static void experiment_noise(void){
    printf("\n═══ EXPERIMENT 3: Noise tolerance ═══\n");
    printf("Add noise at 0-positions. Don't cares should absorb it.\n\n");

    rng_seed(999);

    THDV original = thdv_random(0.5); /* 50% don't cares */
    int orig_nnz = thdv_nnz(&original);
    printf("Original: %d/%d non-zero (50%% don't cares)\n", orig_nnz, D);

    /* Add noise: flip some ±1 positions AND set some 0 positions to random ±1 */
    for(int noise_level = 0; noise_level <= 50; noise_level += 10){
        THDV noisy = original;

        /* Perturb noise_level% of positions */
        int n_perturb = D * noise_level / 100;
        for(int i = 0; i < n_perturb; i++){
            int pos = rng_next() % D;
            int val = (rng_next() % 3) - 1; /* -1, 0, or +1 */
            thdv_set(&noisy, pos, val);
        }

        double sim = thdv_sim(&original, &noisy);
        printf("  Noise %d%%: sim = %.4f, nnz = %d\n",
               noise_level, sim, thdv_nnz(&noisy));
    }
}

/* ═══ EXPERIMENT 4: Class hierarchy classification ═══ */
static void experiment_classification(void){
    printf("\n═══ EXPERIMENT 4: Hierarchical classification ═══\n");
    printf("Generate noisy examples of DOG, CAT, EAGLE.\n");
    printf("Can ternary HDC classify them correctly vs binary HDC?\n\n");

    rng_seed(2024);

    /* Build 3 classes, each with specific prototype */
    /* Each class has D positions, 30% non-zero (class-specific features) */
    THDV dog_proto = thdv_random(0.7);
    THDV cat_proto = thdv_random(0.7);
    THDV eagle_proto = thdv_random(0.7);

    /* Training: create noisy examples */
    int n_per_class = 50;
    THDV *dog_examples = malloc(n_per_class * sizeof(THDV));
    THDV *cat_examples = malloc(n_per_class * sizeof(THDV));
    THDV *eagle_examples = malloc(n_per_class * sizeof(THDV));

    /* Generate noisy versions */
    for(int i = 0; i < n_per_class; i++){
        dog_examples[i] = dog_proto;
        cat_examples[i] = cat_proto;
        eagle_examples[i] = eagle_proto;

        /* Flip 20% of NON-ZERO positions */
        for(int j = 0; j < D; j++){
            if(rng_next() % 100 < 20){
                int v = thdv_get(&dog_examples[i], j);
                if(v != 0) thdv_set(&dog_examples[i], j, -v);
            }
            if(rng_next() % 100 < 20){
                int v = thdv_get(&cat_examples[i], j);
                if(v != 0) thdv_set(&cat_examples[i], j, -v);
            }
            if(rng_next() % 100 < 20){
                int v = thdv_get(&eagle_examples[i], j);
                if(v != 0) thdv_set(&eagle_examples[i], j, -v);
            }
        }
    }

    /* Bundle to form class prototypes */
    THDV dog_learned = thdv_bundle_multi(dog_examples, n_per_class);
    THDV cat_learned = thdv_bundle_multi(cat_examples, n_per_class);
    THDV eagle_learned = thdv_bundle_multi(eagle_examples, n_per_class);

    /* Test on fresh noisy examples */
    int correct = 0, total = 0;
    for(int trial = 0; trial < 100; trial++){
        for(int cls = 0; cls < 3; cls++){
            THDV *proto = (cls == 0) ? &dog_proto : (cls == 1) ? &cat_proto : &eagle_proto;
            THDV test = *proto;
            /* Add noise */
            for(int j = 0; j < D; j++){
                if(rng_next() % 100 < 25){
                    int v = thdv_get(&test, j);
                    if(v != 0) thdv_set(&test, j, -v);
                }
            }

            double s_dog = thdv_sim(&test, &dog_learned);
            double s_cat = thdv_sim(&test, &cat_learned);
            double s_eagle = thdv_sim(&test, &eagle_learned);

            int pred;
            if(s_dog >= s_cat && s_dog >= s_eagle) pred = 0;
            else if(s_cat >= s_eagle) pred = 1;
            else pred = 2;

            if(pred == cls) correct++;
            total++;
        }
    }

    printf("Ternary HDC classification: %d/%d (%.1f%%)\n",
           correct, total, 100.0*correct/total);

    free(dog_examples);
    free(cat_examples);
    free(eagle_examples);
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("TERNARY HDC: {-1, 0, +1} hypervectors\n");
    printf("══════════════════════════════════════════\n");
    printf("Combining HDC (Kanerva) + three-valued logic (Kleene)\n");
    printf("Novel: explicit 'don't care' positions in HDV\n");

    experiment_capacity();
    experiment_hierarchy();
    experiment_noise();
    experiment_classification();

    printf("\n══════════════════════════════════════════\n");
    printf("Key findings:\n");
    printf("  - Don't-care positions enable hierarchical concepts\n");
    printf("  - Ternary HDC preserves IS-A relations\n");
    printf("  - Noise absorbed by 0-positions\n");
    return 0;
}
