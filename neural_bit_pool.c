/*
 * NEURAL BIT POOL: bits as neurons, pure bit operations
 * =====================================================
 *
 * Concept: a pool of bits that self-organizes into a neural network.
 *   - Each neuron is 32 bits (state + metadata)
 *   - Connections stored as bit matrix (adjacency)
 *   - Activation: sum connected neighbors, threshold
 *   - Hebbian learning: co-active neurons strengthen connection
 *   - Growth: recruit new neurons when needed
 *   - NO floating point — everything is bit operations
 *
 * Tests:
 *   1. Associative memory (Hopfield-like): learn patterns, recall from corrupted
 *   2. XOR function: learn 2-input XOR
 *   3. Parity function: generalize to 3-input parity
 *   4. Small SAT: solve a tiny formula
 *
 * Compile: gcc -O3 -march=native -o nbp neural_bit_pool.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>

#define MAX_NEURONS  2048
#define STATE_BITS   8
#define THRESH_BITS  8

/* Pool of neurons */
typedef struct {
    uint8_t state[MAX_NEURONS];      /* 0-255 */
    uint8_t threshold[MAX_NEURONS];  /* 0-255 */
    uint8_t flags[MAX_NEURONS];      /* bit0=active, bit1=input, bit2=output */
    uint64_t adj[MAX_NEURONS][MAX_NEURONS/64]; /* adjacency bit matrix */
    int n_active;                    /* number of currently active neurons */
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

/* Bit manipulation helpers */
static inline int bit_get(uint64_t *arr, int i){
    return (arr[i>>6] >> (i&63)) & 1;
}
static inline void bit_set(uint64_t *arr, int i){
    arr[i>>6] |= (1ULL << (i&63));
}
static inline void bit_clear(uint64_t *arr, int i){
    arr[i>>6] &= ~(1ULL << (i&63));
}

/* ═══ POOL OPERATIONS ═══ */

static void pool_init(void){
    memset(&pool, 0, sizeof(pool));
}

static int pool_grow(int n){
    int start = pool.n_active;
    int end = start + n;
    if(end > MAX_NEURONS) end = MAX_NEURONS;
    for(int i = start; i < end; i++){
        pool.flags[i] = 1; /* active */
        pool.threshold[i] = 128; /* mid threshold */
        pool.state[i] = 0;
    }
    pool.n_active = end;
    return end - start;
}

static void pool_connect(int i, int j){
    if(i != j){
        bit_set(pool.adj[i], j);
        bit_set(pool.adj[j], i); /* symmetric */
    }
}

static void pool_disconnect(int i, int j){
    bit_clear(pool.adj[i], j);
    bit_clear(pool.adj[j], i);
}

static int pool_connected(int i, int j){
    return bit_get(pool.adj[i], j);
}

static int pool_degree(int i){
    int d = 0;
    for(int k = 0; k < (pool.n_active+63)/64; k++){
        d += __builtin_popcountll(pool.adj[i][k]);
    }
    return d;
}

/* ═══ ACTIVATION ═══ */

/* One propagation step: update each neuron's state based on connected neighbors */
static void pool_step(void){
    uint8_t new_state[MAX_NEURONS];
    memcpy(new_state, pool.state, sizeof(new_state));

    for(int i = 0; i < pool.n_active; i++){
        if(!(pool.flags[i] & 1)) continue;

        /* Sum states of connected neurons */
        int sum = 0;
        int count = 0;
        for(int word = 0; word < (pool.n_active+63)/64; word++){
            uint64_t bits = pool.adj[i][word];
            while(bits){
                int bit = __builtin_ctzll(bits);
                int j = word*64 + bit;
                if(j < pool.n_active && (pool.flags[j] & 1)){
                    sum += pool.state[j];
                    count++;
                }
                bits &= bits - 1;
            }
        }

        /* Average and threshold */
        if(count > 0){
            int avg = sum / count;
            /* Leaky integration */
            int new_val = (pool.state[i] * 3 + avg) / 4;
            if(new_val > pool.threshold[i]) new_val = 255;
            else if(new_val < pool.threshold[i]/2) new_val = 0;
            new_state[i] = new_val;
        }
    }

    memcpy(pool.state, new_state, sizeof(new_state));
}

/* Propagate until stable or max_steps */
static int pool_settle(int max_steps){
    uint8_t prev[MAX_NEURONS];
    for(int step = 0; step < max_steps; step++){
        memcpy(prev, pool.state, pool.n_active);
        pool_step();
        if(memcmp(prev, pool.state, pool.n_active) == 0) return step;
    }
    return max_steps;
}

/* ═══ HEBBIAN LEARNING ═══ */

/* Strengthen connections between co-active neurons (active = state > 128) */
static void pool_hebbian(int reward){
    for(int i = 0; i < pool.n_active; i++){
        if(!(pool.flags[i] & 1) || pool.state[i] <= 128) continue;
        for(int j = i+1; j < pool.n_active; j++){
            if(!(pool.flags[j] & 1) || pool.state[j] <= 128) continue;
            if(reward > 0){
                /* Both active + reward → connect */
                pool_connect(i, j);
            } else {
                /* Both active + punish → weak random disconnect */
                if((rng_next() & 7) == 0) pool_disconnect(i, j);
            }
        }
    }
}

/* ═══ I/O ═══ */

static int input_neurons[32], n_inputs = 0;
static int output_neurons[32], n_outputs = 0;

static void set_input(int i, int val){
    if(i < n_inputs){
        int neuron = input_neurons[i];
        pool.state[neuron] = val ? 255 : 0;
        pool.flags[neuron] |= 2; /* mark input */
    }
}

static int get_output(int i){
    if(i < n_outputs){
        int neuron = output_neurons[i];
        return pool.state[neuron] > 128 ? 1 : 0;
    }
    return 0;
}

/* ═══ TEST 1: LEARN XOR ═══ */

static int test_xor(void){
    printf("\nTEST 1: Learning XOR\n");
    printf("────────────────────\n");

    pool_init();

    /* Create initial pool: 2 inputs, 1 output, plus hidden */
    pool_grow(20);
    n_inputs = 2;
    input_neurons[0] = 0;
    input_neurons[1] = 1;
    n_outputs = 1;
    output_neurons[0] = 2;

    /* Random initial connections */
    rng_seed(42);
    for(int i = 0; i < pool.n_active; i++)
        for(int j = i+1; j < pool.n_active; j++)
            if((rng_next() & 3) == 0) pool_connect(i, j);

    /* Training: XOR truth table */
    int xor_table[4][3] = {{0,0,0}, {0,1,1}, {1,0,1}, {1,1,0}};
    int correct = 0;

    for(int epoch = 0; epoch < 100; epoch++){
        int ep_correct = 0;
        for(int t = 0; t < 4; t++){
            /* Reset state */
            memset(pool.state, 0, pool.n_active);

            /* Set inputs */
            set_input(0, xor_table[t][0]);
            set_input(1, xor_table[t][1]);

            /* Propagate */
            pool_settle(10);

            /* Check output */
            int out = get_output(0);
            int target = xor_table[t][2];

            /* Hebbian with reward/punish */
            pool_hebbian(out == target ? 1 : -1);

            if(out == target) ep_correct++;
        }

        if(ep_correct == 4){
            correct++;
            if(correct >= 3) break; /* stable */
        } else {
            correct = 0;
        }

        if(epoch % 20 == 0){
            printf("  Epoch %3d: %d/4 correct\n", epoch, ep_correct);
        }
    }

    /* Final test */
    int final_correct = 0;
    for(int t = 0; t < 4; t++){
        memset(pool.state, 0, pool.n_active);
        set_input(0, xor_table[t][0]);
        set_input(1, xor_table[t][1]);
        pool_settle(10);
        if(get_output(0) == xor_table[t][2]) final_correct++;
    }

    printf("  Final: %d/4 correct (neurons: %d, connections: %d)\n",
           final_correct, pool.n_active, pool_degree(0));
    return final_correct == 4;
}

/* ═══ TEST 2: ASSOCIATIVE MEMORY ═══ */

static int test_memory(void){
    printf("\nTEST 2: Associative memory (Hopfield-like)\n");
    printf("──────────────────────────────────────────\n");

    pool_init();
    pool_grow(100);

    /* Store 5 random patterns */
    rng_seed(123);
    int patterns[5][100];
    for(int p = 0; p < 5; p++){
        for(int i = 0; i < 100; i++){
            patterns[p][i] = rng_next() & 1;
        }
    }

    /* Train: for each pattern, set states and strengthen connections */
    for(int p = 0; p < 5; p++){
        for(int i = 0; i < 100; i++){
            pool.state[i] = patterns[p][i] ? 255 : 0;
        }
        /* Hebbian: all co-active neurons connect */
        for(int i = 0; i < 100; i++){
            if(pool.state[i] <= 128) continue;
            for(int j = i+1; j < 100; j++){
                if(pool.state[j] > 128) pool_connect(i, j);
            }
        }
    }

    /* Test: present corrupted version of each pattern */
    int total_correct = 0, total_bits = 0;
    for(int p = 0; p < 5; p++){
        /* Corrupt 20% of bits */
        int corrupted[100];
        memcpy(corrupted, patterns[p], sizeof(corrupted));
        for(int k = 0; k < 20; k++){
            int i = rng_next() % 100;
            corrupted[i] = 1 - corrupted[i];
        }

        /* Set state to corrupted pattern */
        for(int i = 0; i < 100; i++){
            pool.state[i] = corrupted[i] ? 255 : 0;
        }

        /* Let it settle */
        pool_settle(20);

        /* Check recovery */
        int recovered = 0;
        for(int i = 0; i < 100; i++){
            int rec = pool.state[i] > 128 ? 1 : 0;
            if(rec == patterns[p][i]) recovered++;
        }
        total_correct += recovered;
        total_bits += 100;
        printf("  Pattern %d: recovered %d/100 bits\n", p, recovered);
    }

    printf("  Total: %d/%d bits recovered (%.1f%%)\n",
           total_correct, total_bits, 100.0*total_correct/total_bits);
    return total_correct * 100 / total_bits >= 80;
}

/* ═══ TEST 3: SMALL SAT ═══ */

/* Encode small SAT as pattern recognition:
   - Each variable is a neuron (bit)
   - Each clause creates inhibitory connections between "wrong" configurations
   - Train on known solutions
   - Present partial assignment, let it complete */

static int test_sat(void){
    printf("\nTEST 3: Small SAT via memory recall\n");
    printf("────────────────────────────────────\n");

    pool_init();
    int n_vars = 8;
    pool_grow(n_vars);

    /* Small formula:
       (x1 ∨ x2 ∨ x3) ∧ (¬x1 ∨ x4 ∨ x5) ∧ (x2 ∨ ¬x4 ∨ x6) ∧ (¬x3 ∨ ¬x5 ∨ x7) ∧ (x1 ∨ x6 ∨ x8) */
    int solutions[16][8]; int n_sols = 0;
    for(int mask = 0; mask < 256; mask++){
        int x[8];
        for(int i = 0; i < 8; i++) x[i] = (mask >> i) & 1;

        int ok = (x[0]||x[1]||x[2])
              && (!x[0]||x[3]||x[4])
              && (x[1]||!x[3]||x[5])
              && (!x[2]||!x[4]||x[6])
              && (x[0]||x[5]||x[7]);
        if(ok && n_sols < 16){
            memcpy(solutions[n_sols++], x, 8*sizeof(int));
        }
    }

    printf("  Formula has %d solutions\n", n_sols);

    /* Train network on all solutions */
    for(int s = 0; s < n_sols; s++){
        for(int i = 0; i < n_vars; i++){
            pool.state[i] = solutions[s][i] ? 255 : 0;
        }
        /* Hebbian */
        for(int i = 0; i < n_vars; i++){
            if(pool.state[i] <= 128) continue;
            for(int j = i+1; j < n_vars; j++){
                if(pool.state[j] > 128) pool_connect(i, j);
            }
        }
    }

    /* Now test: present 3 random bits of a solution, see if network completes */
    int tests = 10, recalled = 0;
    rng_seed(777);
    for(int t = 0; t < tests; t++){
        int s = rng_next() % n_sols;
        /* Set 3 random bits */
        int known[8] = {0};
        for(int k = 0; k < 3; k++){
            int i = rng_next() % n_vars;
            known[i] = 1;
            pool.state[i] = solutions[s][i] ? 255 : 0;
        }
        /* Unknown bits start at 128 (uncertain) */
        for(int i = 0; i < n_vars; i++){
            if(!known[i]) pool.state[i] = 128;
        }

        pool_settle(20);

        /* Check if completed to a valid solution */
        int rec[8];
        for(int i = 0; i < n_vars; i++) rec[i] = pool.state[i] > 128 ? 1 : 0;

        int ok = (rec[0]||rec[1]||rec[2])
              && (!rec[0]||rec[3]||rec[4])
              && (rec[1]||!rec[3]||rec[5])
              && (!rec[2]||!rec[4]||rec[6])
              && (rec[0]||rec[5]||rec[7]);

        if(ok) recalled++;
    }

    printf("  Recalled solutions: %d/%d\n", recalled, tests);
    return recalled >= tests / 2;
}

/* ═══ MAIN ═══ */
int main(void){
    printf("══════════════════════════════════════════\n");
    printf("NEURAL BIT POOL: proof of concept\n");
    printf("══════════════════════════════════════════\n");
    printf("Pool size: %d neurons, ~%d KB\n",
           MAX_NEURONS, (int)(sizeof(pool) / 1024));

    int t1 = test_xor();
    int t2 = test_memory();
    int t3 = test_sat();

    printf("\n═══ SUMMARY ═══\n");
    printf("XOR learning:     %s\n", t1 ? "PASS" : "FAIL");
    printf("Associative mem:  %s\n", t2 ? "PASS" : "FAIL");
    printf("Small SAT recall: %s\n", t3 ? "PASS" : "FAIL");

    if(t1 && t2 && t3){
        printf("\nConcept viable. Next: scale, growth, harder problems.\n");
    } else {
        printf("\nConcept has issues. Need redesign.\n");
    }

    return 0;
}
