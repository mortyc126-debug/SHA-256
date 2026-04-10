/*
 * NEURAL BIT POOL v2: with signed connections + error-driven learning
 * ====================================================================
 *
 * Fixes from v1:
 *   - Signed connections: each edge is excitatory (+) or inhibitory (-)
 *     Stored as 2 bits: (connected, sign)
 *   - Error-driven learning: adjust connections based on error signal
 *   - Random hidden layer (reservoir computing principle)
 *   - Output learned via perceptron rule (1-bit weights)
 *
 * Compile: gcc -O3 -march=native -o nbp2 neural_bit_pool_v2.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>

#define MAX_NEURONS  1024
#define POOL_SIZE    512

typedef struct {
    int8_t state[MAX_NEURONS];       /* -1, 0, +1 */
    int8_t threshold[MAX_NEURONS];
    uint64_t connected[MAX_NEURONS][MAX_NEURONS/64];
    uint64_t sign[MAX_NEURONS][MAX_NEURONS/64];  /* 0=+, 1=- */
    int n_active;
} NeuralPool;

static NeuralPool pool;

/* RNG */
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

static inline int bit_get(uint64_t *arr, int i){return (arr[i>>6]>>(i&63))&1;}
static inline void bit_set(uint64_t *arr, int i){arr[i>>6]|=(1ULL<<(i&63));}
static inline void bit_clear(uint64_t *arr, int i){arr[i>>6]&=~(1ULL<<(i&63));}

static void pool_init(int n){
    memset(&pool, 0, sizeof(pool));
    pool.n_active = n;
    for(int i = 0; i < n; i++) pool.threshold[i] = 0;
}

/* Add/remove signed connection */
static void pool_connect(int i, int j, int signed_val){
    if(i == j) return;
    bit_set(pool.connected[i], j);
    bit_set(pool.connected[j], i);
    if(signed_val < 0){
        bit_set(pool.sign[i], j);
        bit_set(pool.sign[j], i);
    } else {
        bit_clear(pool.sign[i], j);
        bit_clear(pool.sign[j], i);
    }
}

static int pool_weight(int i, int j){
    if(!bit_get(pool.connected[i], j)) return 0;
    return bit_get(pool.sign[i], j) ? -1 : 1;
}

/* Forward pass: compute state of each neuron (except inputs) from its connections */
static void pool_forward(int *input_ids, int n_in){
    /* Mark inputs as fixed (don't update) */
    for(int pass = 0; pass < 5; pass++){
        int8_t new_state[MAX_NEURONS];
        memcpy(new_state, pool.state, pool.n_active);

        for(int i = 0; i < pool.n_active; i++){
            /* Skip inputs */
            int is_input = 0;
            for(int k = 0; k < n_in; k++) if(input_ids[k] == i){is_input = 1; break;}
            if(is_input) continue;

            int sum = 0;
            for(int j = 0; j < pool.n_active; j++){
                if(bit_get(pool.connected[i], j)){
                    int w = bit_get(pool.sign[i], j) ? -1 : 1;
                    sum += w * pool.state[j];
                }
            }
            new_state[i] = (sum > pool.threshold[i]) ? 1 : -1;
        }

        memcpy(pool.state, new_state, pool.n_active);
    }
}

/* Error-driven learning: if output is wrong, flip some connections */
static void pool_learn(int output_id, int target, int *input_ids, int n_in){
    int current = pool.state[output_id];
    if(current == target) return; /* correct */

    /* Error: output should flip direction */
    /* Strategy: find connections to output that contribute wrong way, flip them */
    int error = target - current; /* ±2 */

    for(int j = 0; j < pool.n_active; j++){
        if(j == output_id) continue;
        if(!bit_get(pool.connected[output_id], j)) continue;

        int w = bit_get(pool.sign[output_id], j) ? -1 : 1;
        int s = pool.state[j];
        int contribution = w * s;

        /* If contribution is opposite to error, flip the sign */
        if(contribution * error < 0){
            if(rng_next() % 100 < 30){ /* 30% chance to flip */
                if(w > 0){
                    bit_set(pool.sign[output_id], j);
                    bit_set(pool.sign[j], output_id);
                } else {
                    bit_clear(pool.sign[output_id], j);
                    bit_clear(pool.sign[j], output_id);
                }
            }
        }
    }

    /* Also: add new connections if few active */
    int n_conn = 0;
    for(int j = 0; j < pool.n_active; j++)
        if(bit_get(pool.connected[output_id], j)) n_conn++;

    if(n_conn < pool.n_active / 4){
        /* Add a new random connection */
        for(int tries = 0; tries < 10; tries++){
            int j = rng_next() % pool.n_active;
            if(j != output_id && !bit_get(pool.connected[output_id], j)){
                /* Connect with sign that would help */
                int s = pool.state[j];
                int want_sign = (s * target > 0) ? +1 : -1;
                pool_connect(output_id, j, want_sign);
                break;
            }
        }
    }
}

/* ═══ TEST: LEARN XOR ═══ */
static int test_xor_v2(void){
    printf("\nTEST: Learning XOR with signed connections + hidden layer\n");
    printf("──────────────────────────────────────────────────────────\n");

    pool_init(40);
    /* Layout:
       0, 1: inputs
       2-38: hidden (reservoir)
       39: output  */
    int input_ids[2] = {0, 1};
    int output_id = 39;

    /* Random hidden layer: each hidden neuron connects to random inputs with random signs */
    rng_seed(42);
    for(int h = 2; h < 39; h++){
        pool.threshold[h] = (rng_next() & 1) ? -1 : 1;
        /* Connect to both inputs with random signs */
        pool_connect(h, 0, (rng_next() & 1) ? 1 : -1);
        pool_connect(h, 1, (rng_next() & 1) ? 1 : -1);
    }

    /* Output starts disconnected, will learn */
    pool.threshold[output_id] = 0;

    /* XOR truth table */
    int xor_table[4][3] = {{-1,-1,-1}, {-1,+1,+1}, {+1,-1,+1}, {+1,+1,-1}};

    /* Training */
    int best = 0;
    for(int epoch = 0; epoch < 500; epoch++){
        int ep_correct = 0;
        for(int t = 0; t < 4; t++){
            pool.state[0] = xor_table[t][0];
            pool.state[1] = xor_table[t][1];

            pool_forward(input_ids, 2);

            int out = pool.state[output_id];
            int target = xor_table[t][2];

            if(out == target) ep_correct++;
            pool_learn(output_id, target, input_ids, 2);
        }

        if(ep_correct > best){
            best = ep_correct;
            printf("  Epoch %3d: %d/4 correct (best)\n", epoch, ep_correct);
            if(ep_correct == 4) break;
        }
    }

    /* Final test */
    int final = 0;
    for(int t = 0; t < 4; t++){
        pool.state[0] = xor_table[t][0];
        pool.state[1] = xor_table[t][1];
        pool_forward(input_ids, 2);
        if(pool.state[output_id] == xor_table[t][2]) final++;
    }

    printf("  Final: %d/4 correct\n", final);
    return final == 4;
}

/* ═══ TEST: PARITY of n bits ═══ */
static int test_parity(int n){
    printf("\nTEST: Learning parity of %d bits\n", n);
    printf("────────────────────────────────\n");

    /* For parity, we need hierarchical feature detectors */
    pool_init(n + 50 + 1); /* n inputs, 50 hidden, 1 output */
    int input_ids[16];
    for(int i = 0; i < n; i++) input_ids[i] = i;
    int output_id = n + 50;

    rng_seed(123);

    /* Random hidden layer connections */
    for(int h = n; h < n + 50; h++){
        pool.threshold[h] = 0;
        for(int k = 0; k < 3; k++){
            int inp = rng_next() % n;
            pool_connect(h, inp, (rng_next() & 1) ? 1 : -1);
        }
    }

    pool.threshold[output_id] = 0;

    int n_examples = 1 << n;
    int best = 0;
    for(int epoch = 0; epoch < 2000; epoch++){
        int correct = 0;
        for(int ex = 0; ex < n_examples; ex++){
            /* Set inputs */
            int parity = 0;
            for(int i = 0; i < n; i++){
                int bit = (ex >> i) & 1;
                pool.state[i] = bit ? 1 : -1;
                parity ^= bit;
            }

            pool_forward(input_ids, n);

            int out = pool.state[output_id];
            int target = parity ? 1 : -1;

            if(out == target) correct++;
            pool_learn(output_id, target, input_ids, n);
        }

        if(correct > best){
            best = correct;
            if(epoch % 100 == 0 || correct == n_examples)
                printf("  Epoch %4d: %d/%d correct\n", epoch, correct, n_examples);
            if(correct == n_examples) break;
        }
    }

    /* Final eval */
    int final = 0;
    for(int ex = 0; ex < n_examples; ex++){
        int parity = 0;
        for(int i = 0; i < n; i++){
            int bit = (ex >> i) & 1;
            pool.state[i] = bit ? 1 : -1;
            parity ^= bit;
        }
        pool_forward(input_ids, n);
        int target = parity ? 1 : -1;
        if(pool.state[output_id] == target) final++;
    }

    printf("  Final: %d/%d correct (%.0f%%)\n", final, n_examples, 100.0*final/n_examples);
    return final >= n_examples * 0.8;
}

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("NEURAL BIT POOL v2: signed connections\n");
    printf("═══════════════════════════════════════════\n");

    int t1 = test_xor_v2();
    int t2a = test_parity(3);
    int t2b = test_parity(4);

    printf("\n═══ SUMMARY ═══\n");
    printf("XOR:        %s\n", t1 ? "PASS" : "FAIL");
    printf("Parity-3:   %s\n", t2a ? "PASS" : "FAIL");
    printf("Parity-4:   %s\n", t2b ? "PASS" : "FAIL");

    return 0;
}
