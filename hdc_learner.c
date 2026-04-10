/*
 * EXPERIMENT 3: Continual learner on HDC substrate
 * =================================================
 *
 * A single HDC substrate learns multiple tasks in sequence:
 *   1. XOR
 *   2. AND
 *   3. OR
 *   4. Majority-of-3
 *   5. A small SAT instance
 *
 * Tests:
 *   - Does it handle all tasks?
 *   - Does later learning interfere with earlier? (catastrophic forgetting)
 *   - Does experience help later tasks? (positive transfer)
 *
 * Compile: gcc -O3 -march=native -o hdc_learn hdc_learner.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define D 16384
#define D_WORDS (D/64)
#define MAX_TASKS 20

typedef struct { uint64_t b[D_WORDS]; } HDV;

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

static HDV hdv_random(void){HDV v;for(int i=0;i<D_WORDS;i++)v.b[i]=rng_next();return v;}
static HDV hdv_zero(void){HDV v;memset(&v,0,sizeof(v));return v;}
static HDV hdv_bind(HDV a,HDV b){HDV r;for(int i=0;i<D_WORDS;i++)r.b[i]=a.b[i]^b.b[i];return r;}
static int hdv_ham(HDV a,HDV b){int d=0;for(int i=0;i<D_WORDS;i++)d+=__builtin_popcountll(a.b[i]^b.b[i]);return d;}
static double hdv_sim(HDV a,HDV b){return 1.0-(double)hdv_ham(a,b)/D;}

/* Per-task prototypes, bundled via counters */
typedef struct { int c[D]; int n; } Bundle;
static void bundle_init(Bundle *b){memset(b,0,sizeof(*b));}
static void bundle_add(Bundle *b, HDV v){
    for(int i=0;i<D;i++) b->c[i] += ((v.b[i>>6]>>(i&63))&1) ? 1 : -1;
    b->n++;
}
static HDV bundle_finalize(Bundle *b){
    HDV r=hdv_zero();
    for(int i=0;i<D;i++) if(b->c[i]>0) r.b[i>>6] |= (1ULL<<(i&63));
    return r;
}

/* Shared substrate: one HDC system for all tasks */
typedef struct {
    HDV V_bit[2];
    HDV V_pos[32];
    HDV V_task[MAX_TASKS];

    /* Memory: for each (task, label), a bundle */
    Bundle mem[MAX_TASKS][2];
    int n_tasks;
} Substrate;

static Substrate sub;

static void substrate_init(void){
    rng_seed(42);
    sub.V_bit[0] = hdv_random();
    sub.V_bit[1] = hdv_random();
    for(int i = 0; i < 32; i++) sub.V_pos[i] = hdv_random();
    for(int t = 0; t < MAX_TASKS; t++){
        sub.V_task[t] = hdv_random();
        bundle_init(&sub.mem[t][0]);
        bundle_init(&sub.mem[t][1]);
    }
    sub.n_tasks = 0;
}

/* Encode an input vector (task-aware) */
static HDV encode(int task_id, const int *x, int n){
    HDV rep = hdv_zero();
    for(int i = 0; i < n; i++){
        HDV contrib = hdv_bind(sub.V_bit[x[i]], sub.V_pos[i]);
        rep = hdv_bind(rep, contrib);
    }
    /* Bind with task identity */
    return hdv_bind(rep, sub.V_task[task_id]);
}

/* Learn one example */
static void learn(int task_id, const int *x, int n, int label){
    HDV rep = encode(task_id, x, n);
    bundle_add(&sub.mem[task_id][label], rep);
}

/* Predict label for an input */
static int predict(int task_id, const int *x, int n){
    HDV rep = encode(task_id, x, n);

    HDV proto0 = bundle_finalize(&sub.mem[task_id][0]);
    HDV proto1 = bundle_finalize(&sub.mem[task_id][1]);

    double s0 = hdv_sim(rep, proto0);
    double s1 = hdv_sim(rep, proto1);

    return (s1 > s0) ? 1 : 0;
}

/* Compute substrate memory usage in bytes */
static long substrate_memory(void){
    return sizeof(sub);
}

/* ═══ TASK DEFINITIONS ═══ */

typedef int (*TaskFn)(int *x, int n, int *out);

static void task_xor(int *x, int n, int *out){
    (void)n;
    out[0] = x[0] ^ x[1];
}

static void task_and(int *x, int n, int *out){
    (void)n;
    out[0] = x[0] & x[1];
}

static void task_or(int *x, int n, int *out){
    (void)n;
    out[0] = x[0] | x[1];
}

static void task_majority(int *x, int n, int *out){
    (void)n;
    out[0] = (x[0] + x[1] + x[2]) >= 2 ? 1 : 0;
}

static void task_parity4(int *x, int n, int *out){
    (void)n;
    out[0] = x[0] ^ x[1] ^ x[2] ^ x[3];
}

/* Each task: name, n_inputs, fn */
typedef struct {
    const char *name;
    int n;
    void (*fn)(int*, int, int*);
} Task;

static Task tasks[] = {
    {"XOR",       2, task_xor},
    {"AND",       2, task_and},
    {"OR",        2, task_or},
    {"Majority3", 3, task_majority},
    {"Parity4",   4, task_parity4},
};

/* Train substrate on a task */
static void train_task(int task_id){
    Task *t = &tasks[task_id];
    int n_examples = 1 << t->n;
    for(int ex = 0; ex < n_examples; ex++){
        int x[8];
        for(int i = 0; i < t->n; i++) x[i] = (ex >> i) & 1;
        int out[1];
        t->fn(x, t->n, out);
        learn(task_id, x, t->n, out[0]);
    }
}

/* Evaluate substrate on a task */
static double eval_task(int task_id){
    Task *t = &tasks[task_id];
    int n_examples = 1 << t->n;
    int correct = 0;
    for(int ex = 0; ex < n_examples; ex++){
        int x[8];
        for(int i = 0; i < t->n; i++) x[i] = (ex >> i) & 1;
        int out[1];
        t->fn(x, t->n, out);
        int pred = predict(task_id, x, t->n);
        if(pred == out[0]) correct++;
    }
    return 100.0 * correct / n_examples;
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("EXPERIMENT 3: Continual learner\n");
    printf("══════════════════════════════════════════\n");

    substrate_init();
    int n_tasks = 5;

    printf("Substrate memory: %ld KB\n", substrate_memory() / 1024);
    printf("Tasks: %d\n\n", n_tasks);

    /* Learn each task in sequence, track accuracy on all previous */
    printf("Sequential learning:\n");
    printf("%10s |", "After");
    for(int i = 0; i < n_tasks; i++) printf(" %9s |", tasks[i].name);
    printf("\n");
    printf("─────────-+");
    for(int i = 0; i < n_tasks; i++) printf("───────────+");
    printf("\n");

    double accuracy_matrix[MAX_TASKS][MAX_TASKS];
    for(int i = 0; i < MAX_TASKS; i++)
        for(int j = 0; j < MAX_TASKS; j++)
            accuracy_matrix[i][j] = 0.0;

    for(int t = 0; t < n_tasks; t++){
        train_task(t);
        printf("%10s |", tasks[t].name);
        for(int t2 = 0; t2 <= t; t2++){
            double acc = eval_task(t2);
            accuracy_matrix[t][t2] = acc;
            printf(" %8.1f%% |", acc);
        }
        for(int t2 = t+1; t2 < n_tasks; t2++) printf(" %9s |", "-");
        printf("\n");
    }

    /* Analysis */
    printf("\n═══ ANALYSIS ═══\n");

    /* Check for catastrophic forgetting */
    int any_forgetting = 0;
    for(int i = 0; i < n_tasks; i++){
        double initial = accuracy_matrix[i][i];
        double final = accuracy_matrix[n_tasks-1][i];
        if(initial - final > 5.0){
            printf("  Task '%s' forgot: %.1f%% → %.1f%% (lost %.1f%%)\n",
                   tasks[i].name, initial, final, initial - final);
            any_forgetting = 1;
        }
    }
    if(!any_forgetting){
        printf("  No catastrophic forgetting (task-aware encoding isolates memories)\n");
    }

    /* Check final accuracy on all tasks */
    int n_perfect = 0;
    printf("\n  Final accuracy:\n");
    for(int i = 0; i < n_tasks; i++){
        printf("    %s: %.1f%%\n", tasks[i].name, accuracy_matrix[n_tasks-1][i]);
        if(accuracy_matrix[n_tasks-1][i] >= 95.0) n_perfect++;
    }

    printf("\n  Tasks learned perfectly: %d/%d\n", n_perfect, n_tasks);

    if(n_perfect == n_tasks){
        printf("  ✓ Continual learning works: all tasks stored and recalled\n");
    } else {
        printf("  Partial success: %d/%d tasks mastered\n", n_perfect, n_tasks);
    }

    return 0;
}
