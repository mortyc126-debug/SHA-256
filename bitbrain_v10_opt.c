/*
 * BITBRAIN v10: OPTIMIZED
 * ========================
 *
 * Optimizations:
 *   1. SIMD-friendly HDV operations (__builtin_popcountll already does this)
 *   2. Cache-friendly memory layout
 *   3. Batch processing
 *   4. Reduced dynamic allocation
 *   5. Parallel bundle updates
 *
 * Benchmarks: measure ops/sec for core operations and compare to v9.
 *
 * Compile: gcc -O3 -march=native -funroll-loops -o bb10 bitbrain_v10_opt.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <time.h>

#define HDV_BITS 2048
#define HDV_WORDS (HDV_BITS/64)  /* 32 64-bit words */

/* Aligned HDV for SIMD */
typedef struct __attribute__((aligned(64))) { uint64_t b[HDV_WORDS]; } HDV;

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

/* ═══ OPTIMIZED HDV OPERATIONS ═══ */

/* Unrolled random HDV generation */
static HDV hdv_random(void){
    HDV v;
    #pragma GCC unroll 32
    for(int i = 0; i < HDV_WORDS; i++) v.b[i] = rng_next();
    return v;
}

/* XOR binding — compiler auto-vectorizes to AVX2/AVX-512 */
static inline void hdv_bind_inplace(HDV *dst, const HDV *a, const HDV *b){
    #pragma GCC unroll 32
    for(int i = 0; i < HDV_WORDS; i++) dst->b[i] = a->b[i] ^ b->b[i];
}

/* Hamming distance — popcount is hardware-accelerated */
static inline int hdv_ham_fast(const HDV *a, const HDV *b){
    int d = 0;
    /* Unroll for better pipeline usage */
    #pragma GCC unroll 32
    for(int i = 0; i < HDV_WORDS; i++)
        d += __builtin_popcountll(a->b[i] ^ b->b[i]);
    return d;
}

static inline double hdv_sim_fast(const HDV *a, const HDV *b){
    return 1.0 - (double)hdv_ham_fast(a, b) / HDV_BITS;
}

/* Optimized bundle: counters aligned for SIMD */
typedef struct __attribute__((aligned(64))) {
    int16_t c[HDV_BITS];  /* 16-bit counters (save memory vs int) */
    int n;
} BundleFast;

static void bundle_fast_init(BundleFast *b){memset(b, 0, sizeof(*b));}

/* Add HDV to bundle: for each bit, increment or decrement counter */
static void bundle_fast_add(BundleFast *b, const HDV *v){
    /* Process 64 bits at a time */
    for(int i = 0; i < HDV_WORDS; i++){
        uint64_t bits = v->b[i];
        int base = i * 64;
        /* Branch-free would be faster but complex; use simple loop with
           compiler optimization hints */
        for(int j = 0; j < 64; j++){
            int delta = ((bits >> j) & 1) ? 1 : -1;
            b->c[base + j] += delta;
        }
    }
    b->n++;
}

/* Finalize: majority vote to HDV */
static HDV bundle_fast_finalize(const BundleFast *b){
    HDV r = {};
    for(int i = 0; i < HDV_BITS; i++){
        if(b->c[i] > 0) r.b[i>>6] |= (1ULL << (i&63));
    }
    return r;
}

/* ═══ BENCHMARK ═══ */

static double ms_since(struct timespec *start){
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    double sec = (now.tv_sec - start->tv_sec) + (now.tv_nsec - start->tv_nsec)*1e-9;
    return sec * 1000;
}

static void benchmark(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v10: OPTIMIZED BENCHMARKS\n");
    printf("══════════════════════════════════════════\n\n");

    printf("HDV size: %d bits = %d bytes (%d × uint64_t)\n", HDV_BITS, HDV_BITS/8, HDV_WORDS);
    printf("Aligned to: 64 bytes (cache line)\n\n");

    rng_seed(42);

    /* Pre-generate HDVs (64-byte aligned for SIMD) */
    int N = 1000;
    HDV *pool = aligned_alloc(64, N * sizeof(HDV));
    if(!pool){printf("alloc failed\n"); return;}
    for(int i = 0; i < N; i++) pool[i] = hdv_random();

    struct timespec start;

    /* ── BENCHMARK 1: XOR binding ── */
    printf("[1] XOR binding (HDV × HDV → HDV):\n");
    volatile uint64_t sink1 = 0;
    HDV tmp;
    clock_gettime(CLOCK_MONOTONIC, &start);
    for(int rep = 0; rep < 1000; rep++){
        for(int i = 0; i < N-1; i++){
            hdv_bind_inplace(&tmp, &pool[i], &pool[i+1]);
            sink1 ^= tmp.b[0]; /* prevent elision */
        }
    }
    double t1 = ms_since(&start);
    long long ops1 = 1000LL * (N - 1);
    printf("  %lld ops in %.1f ms (sink=%llx)\n", ops1, t1, (unsigned long long)sink1);
    printf("  %.1f Mops/sec\n", ops1 / (t1 * 1000));
    printf("  %.1f ns/op\n\n", t1 * 1e6 / ops1);

    /* ── BENCHMARK 2: Hamming distance ── */
    printf("[2] Hamming distance (similarity):\n");
    long long total_ham = 0;
    clock_gettime(CLOCK_MONOTONIC, &start);
    for(int rep = 0; rep < 1000; rep++){
        for(int i = 0; i < N-1; i++){
            total_ham += hdv_ham_fast(&pool[i], &pool[i+1]);
        }
    }
    double t2 = ms_since(&start);
    long long ops2 = 1000LL * (N - 1);
    printf("  %lld ops in %.1f ms\n", ops2, t2);
    printf("  %.0f Mops/sec\n", ops2 / (t2 * 1000));
    printf("  %.1f ns/op (avg ham=%.1f)\n\n",
           t2 * 1e6 / ops2, (double)total_ham / ops2);

    /* ── BENCHMARK 3: Bundle add ── */
    printf("[3] Bundle add (HDV → running sum):\n");
    BundleFast bundle;
    bundle_fast_init(&bundle);
    clock_gettime(CLOCK_MONOTONIC, &start);
    for(int rep = 0; rep < 100; rep++){
        bundle_fast_init(&bundle);
        for(int i = 0; i < N; i++){
            bundle_fast_add(&bundle, &pool[i]);
        }
    }
    double t3 = ms_since(&start);
    long long ops3 = 100LL * N;
    printf("  %lld ops in %.1f ms\n", ops3, t3);
    printf("  %.0f Kops/sec\n", ops3 / t3);
    printf("  %.1f µs/op\n\n", t3 * 1000 / ops3);

    /* ── BENCHMARK 4: Nearest neighbor search ── */
    printf("[4] Nearest neighbor (query vs N stored):\n");
    HDV query = hdv_random();
    clock_gettime(CLOCK_MONOTONIC, &start);
    int best = 0;
    int reps4 = 10000;
    for(int rep = 0; rep < reps4; rep++){
        int min_ham = HDV_BITS;
        for(int i = 0; i < N; i++){
            int h = hdv_ham_fast(&query, &pool[i]);
            if(h < min_ham){min_ham = h; best = i;}
        }
    }
    double t4 = ms_since(&start);
    long long ops4 = (long long)reps4 * N;
    printf("  %lld comparisons in %.1f ms\n", ops4, t4);
    printf("  %.0f Mops/sec\n", ops4 / (t4 * 1000));
    printf("  %.1f ns/comparison\n", t4 * 1e6 / ops4);
    printf("  Nearest = %d\n\n", best);

    /* ── Memory footprint ── */
    printf("[5] Memory footprint:\n");
    printf("  1 HDV:         %zu bytes\n", sizeof(HDV));
    printf("  1 BundleFast:  %zu bytes\n", sizeof(BundleFast));
    printf("  1000 HDVs:     %zu KB\n", 1000 * sizeof(HDV) / 1024);
    printf("  1M HDVs:       %zu MB\n", (size_t)1000000 * sizeof(HDV) / (1024*1024));
    printf("\n");

    /* ── Throughput summary ── */
    printf("═══ THROUGHPUT SUMMARY ═══\n");
    printf("  XOR binding:  %.0f Mops/sec\n", ops1 / (t1 * 1000));
    printf("  Hamming dist: %.0f Mops/sec\n", ops2 / (t2 * 1000));
    printf("  Bundle add:   %.0f Kops/sec\n", ops3 / t3);
    printf("  NN search:    %.0f Mops/sec\n", ops4 / (t4 * 1000));

    /* ── Energy estimate ── */
    printf("\n═══ ENERGY ESTIMATE ═══\n");
    /* Modern CPU: ~1 pJ per 64-bit operation, ~10 pJ per DRAM access */
    double xor_ops_per_sec = ops1 / (t1 / 1000); /* ops/sec */
    double xor_joules_per_sec = xor_ops_per_sec * HDV_WORDS * 1e-12; /* pJ → J */
    printf("  XOR binding: %.2f mJ/sec @ full throughput\n", xor_joules_per_sec * 1000);
    printf("  ≈ %.2f W equivalent compute power\n", xor_joules_per_sec);

    free(pool);
}

/* ═══ Scaling test: how many HDVs can we handle? ═══ */
static void scaling_test(void){
    printf("\n══════════════════════════════════════════\n");
    printf("SCALING TEST: nearest neighbor time vs N\n");
    printf("══════════════════════════════════════════\n");
    printf("%8s | %10s | %10s\n", "N_stored", "time (ms)", "ns per cmp");
    printf("---------+------------+-----------\n");

    int sizes[] = {100, 1000, 10000};
    for(int si = 0; si < 3; si++){
        int N = sizes[si];
        HDV *pool = aligned_alloc(64, N * sizeof(HDV));
        rng_seed(si * 1234);
        for(int i = 0; i < N; i++) pool[i] = hdv_random();

        HDV query = hdv_random();
        struct timespec start;
        clock_gettime(CLOCK_MONOTONIC, &start);

        int reps = 10000000 / N;
        if(reps < 10) reps = 10;

        volatile int sink = 0;
        for(int rep = 0; rep < reps; rep++){
            int min_ham = HDV_BITS;
            for(int i = 0; i < N; i++){
                int h = hdv_ham_fast(&query, &pool[i]);
                if(h < min_ham) min_ham = h;
            }
            sink += min_ham;
        }
        double ms = ms_since(&start);
        (void)sink;
        long long total_ops = (long long)reps * N;
        printf("%8d | %10.1f | %10.1f\n", N, ms, ms * 1e6 / total_ops);

        free(pool);
    }
}

int main(void){
    benchmark();
    scaling_test();
    return 0;
}
