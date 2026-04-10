/*
 * BITNET for SAT: can bit-native network learn to solve SAT?
 * ===========================================================
 *
 * Strategy: train a BitNet to predict solution bits given clause structure.
 *
 * Input: encoding of the formula (which clauses have which literals)
 * Output: prediction of variable values in a solution
 *
 * Training: use probSAT to find ground truth solutions, train network
 * on (formula, solution) pairs.
 *
 * Test: does the network generalize to new formulas?
 *
 * Compile: gcc -O3 -march=native -o bitnet_sat bitnet_sat.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define N_VARS 8  /* small SAT */
#define MAX_CLAUSES 34  /* α × n ≈ 4.27 * 8 */
#define MAX_LAYER 512
#define MAX_LAYERS 6

/* ═══ Tiny SAT generator ═══ */
typedef struct {
    int n_vars;
    int n_clauses;
    int cl_var[MAX_CLAUSES][3];
    int cl_sign[MAX_CLAUSES][3];
    int solution[N_VARS]; /* known solution */
} SATInstance;

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

/* Generate planted SAT: pick random solution, then generate clauses that are satisfied */
static int gen_planted_sat(SATInstance *sat, int n, int m, unsigned long long seed){
    rng_seed(seed);
    sat->n_vars = n;
    sat->n_clauses = m;

    /* Pick random solution */
    for(int i = 0; i < n; i++) sat->solution[i] = rng_next() & 1;

    /* Generate clauses guaranteed to be satisfied */
    for(int c = 0; c < m; c++){
        int vs[3];
        vs[0] = rng_next() % n;
        do{vs[1] = rng_next() % n;}while(vs[1] == vs[0]);
        do{vs[2] = rng_next() % n;}while(vs[2] == vs[0] || vs[2] == vs[1]);

        /* Try random signs, regenerate if all three false under solution */
        int tries = 0;
        while(tries < 20){
            for(int j = 0; j < 3; j++){
                sat->cl_var[c][j] = vs[j];
                sat->cl_sign[c][j] = (rng_next() & 1) ? 1 : -1;
            }
            /* Check satisfaction */
            int sat_ok = 0;
            for(int j = 0; j < 3; j++){
                int v = vs[j], s = sat->cl_sign[c][j];
                if((s == 1 && sat->solution[v] == 1) || (s == -1 && sat->solution[v] == 0)){
                    sat_ok = 1; break;
                }
            }
            if(sat_ok) break;
            tries++;
        }
    }
    return 1;
}

/* Encode formula as feature vector:
 * For each clause, for each literal position, encode which variable and sign
 * Feature vector length: m × 3 × (n + 1) = m × 3n + 3m (1-hot var + sign)
 *
 * To keep it simple, use sparse encoding:
 *   feature[c * 3 * (n + 1) + j * (n + 1) + var] = 1 (var indicator)
 *   feature[c * 3 * (n + 1) + j * (n + 1) + n]   = sign
 */
static int encode_formula(SATInstance *sat, int8_t *features){
    int idx = 0;
    int m = sat->n_clauses, n = sat->n_vars;
    for(int c = 0; c < m; c++){
        for(int j = 0; j < 3; j++){
            /* Variable as 1-hot */
            for(int v = 0; v < n; v++){
                features[idx++] = (sat->cl_var[c][j] == v) ? 1 : -1;
            }
            /* Sign */
            features[idx++] = (int8_t)sat->cl_sign[c][j];
        }
    }
    return idx;
}

/* ═══ BitNet ═══ */
typedef struct {
    int n_layers;
    int size[MAX_LAYERS];
    int8_t state[MAX_LAYERS][MAX_LAYER];
    int8_t W[MAX_LAYERS][MAX_LAYER][MAX_LAYER];
} BitNet;

static void bn_init(BitNet *net, int n_layers, int *sizes){
    net->n_layers = n_layers;
    for(int l = 0; l < n_layers; l++) net->size[l] = sizes[l];
    for(int l = 0; l < n_layers - 1; l++)
        for(int i = 0; i < sizes[l]; i++)
            for(int j = 0; j < sizes[l+1]; j++)
                net->W[l][i][j] = (rng_next() & 1) ? 1 : -1;
}

static void bn_forward(BitNet *net, const int8_t *input){
    memcpy(net->state[0], input, net->size[0]);
    for(int l = 0; l < net->n_layers - 1; l++){
        for(int j = 0; j < net->size[l+1]; j++){
            int sum = 0;
            for(int i = 0; i < net->size[l]; i++){
                sum += net->W[l][i][j] * net->state[l][i];
            }
            net->state[l+1][j] = (sum >= 0) ? 1 : -1;
        }
    }
}

static void bn_train(BitNet *net, const int8_t *target, int flip_prob){
    int last = net->n_layers - 1;
    int8_t desired[MAX_LAYERS][MAX_LAYER];
    memset(desired, 0, sizeof(desired));

    for(int j = 0; j < net->size[last]; j++){
        if(net->state[last][j] != target[j]) desired[last][j] = target[j];
    }

    for(int l = last; l > 0; l--){
        int prev = l - 1;
        for(int j = 0; j < net->size[l]; j++){
            if(desired[l][j] == 0) continue;
            int target_val = desired[l][j];
            int current = net->state[l][j];
            if(current == target_val) continue;

            for(int i = 0; i < net->size[prev]; i++){
                int contribution = net->W[prev][i][j] * net->state[prev][i];
                if(contribution != target_val){
                    if((int)(rng_next() % 100) < flip_prob){
                        net->W[prev][i][j] = -net->W[prev][i][j];
                    }
                }
            }

            for(int i = 0; i < net->size[prev]; i++){
                int w = net->W[prev][i][j];
                int want_i = target_val * w;
                if(net->state[prev][i] != want_i){
                    if(desired[prev][i] == 0) desired[prev][i] = want_i;
                    else if(desired[prev][i] != want_i) desired[prev][i] = 0;
                }
            }
        }
    }
}

/* ═══ MAIN EXPERIMENT ═══ */
int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITNET for SAT: learning to solve from examples\n");
    printf("══════════════════════════════════════════\n\n");

    int n = N_VARS;
    int m = 20; /* 8 vars × 2.5 ratio = 20 clauses (below threshold, easier) */
    int feature_size = m * 3 * (n + 1); /* 20 * 3 * 9 = 540 */

    printf("n_vars = %d, n_clauses = %d\n", n, m);
    printf("Feature size: %d\n", feature_size);

    /* Network: input → hidden × 2 → output (n bits) */
    int sizes[] = {feature_size, 128, 64, n};
    BitNet net;
    rng_seed(2024);
    bn_init(&net, 4, sizes);

    printf("Architecture: %d → %d → %d → %d\n\n",
           sizes[0], sizes[1], sizes[2], sizes[3]);

    /* Generate training set: 500 planted SAT instances */
    int n_train = 500;
    SATInstance *train = malloc(n_train * sizeof(SATInstance));
    int8_t *train_features = malloc((long)n_train * feature_size);
    int8_t *train_targets = malloc((long)n_train * n);

    for(int i = 0; i < n_train; i++){
        gen_planted_sat(&train[i], n, m, i + 1);
        encode_formula(&train[i], &train_features[(long)i * feature_size]);
        for(int v = 0; v < n; v++){
            train_targets[(long)i * n + v] = train[i].solution[v] ? 1 : -1;
        }
    }

    printf("Training set: %d instances\n", n_train);

    /* Train */
    int best_train_acc = 0;
    printf("\nTraining...\n");
    for(int epoch = 0; epoch < 200; epoch++){
        /* Shuffle order */
        for(int ex = 0; ex < n_train; ex++){
            bn_forward(&net, &train_features[(long)ex * feature_size]);

            int flip_prob = 30 - epoch * 20 / 200;
            if(flip_prob < 3) flip_prob = 3;

            bn_train(&net, &train_targets[(long)ex * n], flip_prob);
        }

        /* Evaluate */
        if(epoch % 10 == 0){
            int correct_bits = 0;
            int fully_correct = 0;
            for(int ex = 0; ex < n_train; ex++){
                bn_forward(&net, &train_features[(long)ex * feature_size]);
                int all_ok = 1;
                for(int v = 0; v < n; v++){
                    if(net.state[net.n_layers-1][v] == train_targets[(long)ex * n + v]){
                        correct_bits++;
                    } else {
                        all_ok = 0;
                    }
                }
                if(all_ok) fully_correct++;
            }
            int total_bits = n_train * n;
            printf("  Epoch %3d: %d/%d bits (%.1f%%), %d/%d full (%.1f%%)\n",
                   epoch, correct_bits, total_bits, 100.0*correct_bits/total_bits,
                   fully_correct, n_train, 100.0*fully_correct/n_train);
            if(correct_bits > best_train_acc) best_train_acc = correct_bits;
        }
    }

    /* Test: generate FRESH instances, see if it generalizes */
    printf("\nTesting on 100 fresh instances...\n");
    int test_bits = 0, test_full = 0;
    for(int i = 0; i < 100; i++){
        SATInstance test_sat;
        int8_t features[1024];
        gen_planted_sat(&test_sat, n, m, 100000 + i);
        encode_formula(&test_sat, features);

        bn_forward(&net, features);

        int all_ok = 1;
        for(int v = 0; v < n; v++){
            int pred = net.state[net.n_layers-1][v] > 0 ? 1 : 0;
            if(pred == test_sat.solution[v]){
                test_bits++;
            } else {
                all_ok = 0;
            }
        }
        if(all_ok) test_full++;
    }

    printf("Test accuracy: %d/%d bits (%.1f%%), %d/100 full solutions\n",
           test_bits, 100*n, (double)test_bits/(100*n)*100, test_full);

    if(test_full >= 10){
        printf("\n✓ BitNet GENERALIZES to new SAT instances!\n");
    } else if(test_bits > 50*n){
        printf("\n~ BitNet learns something but doesn't generalize fully\n");
    } else {
        printf("\n✗ BitNet does not generalize\n");
    }

    free(train);
    free(train_features);
    free(train_targets);
    return 0;
}
