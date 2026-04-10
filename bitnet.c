/*
 * BITNET: Bits as Neurons with PURE BIT-BASED LEARNING
 * =====================================================
 *
 * No floating point ANYWHERE. Not in weights, activations, or learning.
 *
 * Architecture:
 *   - Neurons: bits ±1
 *   - Weights: bits ±1 (signed connections)
 *   - Activation: sign(Σ w_ij × s_j)
 *   - Layers: input → hidden1 → hidden2 → output
 *
 * Learning (no gradients, pure bit flips):
 *   1. Forward pass: compute all neuron states
 *   2. Compare output to target
 *   3. For wrong outputs: find which weights contribute to error
 *   4. Flip those weights with probability based on "regret"
 *   5. Regret = how strongly the weight voted for wrong direction
 *   6. Repeat
 *
 * This is BIT-native error correction. Novel (as far as I know).
 *
 * Compile: gcc -O3 -march=native -o bitnet bitnet.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define MAX_LAYER_SIZE 256
#define MAX_LAYERS 8

typedef struct {
    int n_layers;
    int size[MAX_LAYERS];           /* size[l] = neurons in layer l */
    int8_t state[MAX_LAYERS][MAX_LAYER_SIZE]; /* ±1 */

    /* Weights: W[l][i][j] = weight from neuron i in layer l to neuron j in layer l+1 */
    int8_t W[MAX_LAYERS][MAX_LAYER_SIZE][MAX_LAYER_SIZE];
} BitNet;

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

/* ═══ INIT ═══ */
static void bn_init(BitNet *net, int n_layers, int *sizes){
    net->n_layers = n_layers;
    for(int l = 0; l < n_layers; l++) net->size[l] = sizes[l];

    /* Random initial weights: ±1 */
    for(int l = 0; l < n_layers - 1; l++){
        for(int i = 0; i < sizes[l]; i++){
            for(int j = 0; j < sizes[l+1]; j++){
                net->W[l][i][j] = (rng_next() & 1) ? 1 : -1;
            }
        }
    }
}

/* ═══ FORWARD PASS ═══ */
static void bn_forward(BitNet *net, const int8_t *input){
    /* Copy input to layer 0 */
    memcpy(net->state[0], input, net->size[0]);

    /* Propagate layer by layer */
    for(int l = 0; l < net->n_layers - 1; l++){
        for(int j = 0; j < net->size[l+1]; j++){
            int sum = 0;
            for(int i = 0; i < net->size[l]; i++){
                sum += net->W[l][i][j] * net->state[l][i];
            }
            /* sign activation (ties → +1) */
            net->state[l+1][j] = (sum >= 0) ? 1 : -1;
        }
    }
}

/* ═══ LEARNING: bit flip with regret ═══ */

/*
 * For each wrong output neuron:
 *   - target is wanted; current is sign(sum). Error direction = target - current.
 *   - For each contributing weight W[l-1][i][j]:
 *     - "contribution" = W[i][j] * state[l-1][i]
 *     - If contribution is opposite to target → this weight is "bad"
 *     - With some probability, flip it
 *
 * Crucially: after flipping output-layer weights, we CASCADE:
 *   - Find hidden neurons whose sign should flip to help output
 *   - For those hidden: find their input weights contributing wrong way
 *   - Flip recursively
 */
static void bn_train_step(BitNet *net, const int8_t *target, int flip_prob){
    int last = net->n_layers - 1;

    /* For each output neuron: compute "desired change" */
    int8_t desired[MAX_LAYERS][MAX_LAYER_SIZE];
    memset(desired, 0, sizeof(desired));

    for(int j = 0; j < net->size[last]; j++){
        if(net->state[last][j] != target[j]){
            desired[last][j] = target[j]; /* should be this */
        } else {
            desired[last][j] = 0; /* correct, no change needed */
        }
    }

    /* Backward cascade */
    for(int l = last; l > 0; l--){
        int prev = l - 1;
        /* For each neuron in layer l that needs to change */
        for(int j = 0; j < net->size[l]; j++){
            if(desired[l][j] == 0) continue;

            int target_val = desired[l][j];
            int current = net->state[l][j];

            if(current == target_val) continue; /* already correct */

            /* Find weights that are "voting wrong" and flip them */
            for(int i = 0; i < net->size[prev]; i++){
                int contribution = net->W[prev][i][j] * net->state[prev][i];
                /* contribution is +1 or -1 */
                if(contribution != target_val){
                    /* This weight is voting wrong — flip it with probability */
                    if((int)(rng_next() % 100) < flip_prob){
                        net->W[prev][i][j] = -net->W[prev][i][j];
                    }
                }
            }

            /* Request change in previous layer: neurons that agree with target should stay,
               neurons that disagree should flip */
            for(int i = 0; i < net->size[prev]; i++){
                /* If this neuron i is connected with weight that wants i to flip... */
                int w = net->W[prev][i][j];
                int want_i = target_val * w; /* target_val / w */
                if(net->state[prev][i] != want_i){
                    /* Accumulate desired change */
                    if(desired[prev][i] == 0) desired[prev][i] = want_i;
                    else if(desired[prev][i] == want_i) ; /* already wanted */
                    else desired[prev][i] = 0; /* conflict: do nothing */
                }
            }
        }
    }
}

/* ═══ TESTS ═══ */

static int test_function(BitNet *net, int n_in, int n_out,
                          void (*target_fn)(int8_t*, int8_t*)){
    int n_ex = 1 << n_in;
    int correct = 0;
    for(int ex = 0; ex < n_ex; ex++){
        int8_t input[MAX_LAYER_SIZE];
        int8_t target[MAX_LAYER_SIZE];
        for(int i = 0; i < n_in; i++) input[i] = ((ex >> i) & 1) ? 1 : -1;
        target_fn(input, target);

        bn_forward(net, input);

        int ok = 1;
        for(int j = 0; j < n_out; j++){
            if(net->state[net->n_layers-1][j] != target[j]){ok = 0; break;}
        }
        if(ok) correct++;
    }
    return correct;
}

static int train(BitNet *net, int n_in, int n_out,
                  void (*target_fn)(int8_t*, int8_t*), int max_epochs){
    int n_ex = 1 << n_in;
    int best = 0;

    for(int epoch = 0; epoch < max_epochs; epoch++){
        /* Train on all examples */
        for(int ex = 0; ex < n_ex; ex++){
            int8_t input[MAX_LAYER_SIZE];
            int8_t target[MAX_LAYER_SIZE];
            for(int i = 0; i < n_in; i++) input[i] = ((ex >> i) & 1) ? 1 : -1;
            target_fn(input, target);

            bn_forward(net, input);

            /* Flip probability decreases over time */
            int flip_prob = 50 - (epoch * 45 / max_epochs);
            if(flip_prob < 5) flip_prob = 5;

            bn_train_step(net, target, flip_prob);
        }

        /* Evaluate */
        int correct = test_function(net, n_in, n_out, target_fn);
        if(correct > best){
            best = correct;
            if(correct == n_ex) return epoch + 1;
        }
    }
    return -1; /* failed */
}

/* ═══ TARGET FUNCTIONS ═══ */

static void f_xor(int8_t *in, int8_t *out){ out[0] = in[0] * in[1]; }
static void f_and(int8_t *in, int8_t *out){ out[0] = (in[0]==1 && in[1]==1) ? 1 : -1; }
static void f_or(int8_t *in, int8_t *out){ out[0] = (in[0]==1 || in[1]==1) ? 1 : -1; }
static void f_majority3(int8_t *in, int8_t *out){
    int s = in[0] + in[1] + in[2];
    out[0] = (s > 0) ? 1 : -1;
}
static void f_parity3(int8_t *in, int8_t *out){
    out[0] = in[0] * in[1] * in[2];
}
static void f_parity4(int8_t *in, int8_t *out){
    out[0] = in[0] * in[1] * in[2] * in[3];
}

/* ═══ MAIN ═══ */
int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITNET: pure bit-based neural network\n");
    printf("══════════════════════════════════════════\n");
    printf("No floating point anywhere.\n\n");

    struct {
        const char *name;
        int n_in, n_out;
        void (*fn)(int8_t*, int8_t*);
    } tests[] = {
        {"XOR",       2, 1, f_xor},
        {"AND",       2, 1, f_and},
        {"OR",        2, 1, f_or},
        {"Majority3", 3, 1, f_majority3},
        {"Parity3",   3, 1, f_parity3},
        {"Parity4",   4, 1, f_parity4},
    };

    int n_tests = 6;

    printf("%12s | %9s | %7s | %10s | %7s\n",
           "Task", "Arch", "Result", "Epochs", "Status");
    printf("─────────────-+───────────+─────────+────────────+────────\n");

    for(int t = 0; t < n_tests; t++){
        /* Try architectures: 2 hidden layers of size 8, then 16 */
        int sizes[MAX_LAYERS];
        sizes[0] = tests[t].n_in;
        sizes[1] = 16;
        sizes[2] = 8;
        sizes[3] = tests[t].n_out;

        /* Multiple runs with different seeds */
        int best_epochs = -1;
        int best_correct = 0;
        int n_ex = 1 << tests[t].n_in;

        for(int trial = 0; trial < 10; trial++){
            BitNet net;
            rng_seed(42 + trial * 1000);
            bn_init(&net, 4, sizes);

            int epochs = train(&net, tests[t].n_in, tests[t].n_out, tests[t].fn, 500);
            int correct = test_function(&net, tests[t].n_in, tests[t].n_out, tests[t].fn);

            if(correct > best_correct){
                best_correct = correct;
                best_epochs = epochs;
            }
        }

        printf("%12s | %2d-16-8-%d | %2d/%-2d   | %10d | %s\n",
               tests[t].name, tests[t].n_in, tests[t].n_out,
               best_correct, n_ex, best_epochs,
               best_correct == n_ex ? "PASS" : "partial");
    }

    return 0;
}
