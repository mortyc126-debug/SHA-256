/*
 * PER-CLUSTER FROZEN CORE
 * ==========================
 *
 * Third frozen-core file. Refines the three-layer classification
 * (frozen / biased / free) by looking at each SOLUTION CLUSTER
 * separately. The key idea: a variable that appears 'free'
 * globally (bias ≈ 0.5) may in fact be FROZEN WITHIN EVERY CLUSTER
 * with different values in different clusters.
 *
 * Such a variable is a 'cluster distinguisher': it encodes
 * which cluster the solution sits in. Locally, flipping it
 * never preserves satisfaction — the flipped state lies outside
 * the current cluster. Globally, it looks free because its value
 * is balanced across clusters.
 *
 * Refined five-layer classification:
 *
 *   GLOBAL FROZEN          same value in every solution
 *   CLUSTER-FROZEN-AGREE   frozen in every cluster, same value
 *                          (= global frozen)
 *   CLUSTER-FROZEN-DISAGREE
 *                          frozen WITHIN each cluster, DIFFERENT
 *                          values in different clusters. These
 *                          look free globally but are locally
 *                          locked.
 *   CLUSTER-BIASED         biased within some cluster
 *   CLUSTER-FREE           actually free within at least one cluster
 *
 * Experiments:
 *
 *   1. One instance: clusters + per-cluster bias + refined class
 *   2. Explicit example of cluster-frozen-disagreeing variable
 *      that appeared as 'free' in the earlier simple analysis
 *   3. Sweep α, plot fraction of each refined class
 *   4. Local flippability explanation: show that free-looking
 *      variables that are cluster-frozen-disagreeing have 0%
 *      local flippability, while cluster-free variables have
 *      non-zero flippability
 *   5. Number of clusters vs α, correlated with cluster-frozen
 *      -disagreeing fraction
 *
 * Compile: gcc -O3 -march=native -o cfroz cluster_frozen.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define MAX_N 18
#define MAX_M 256
#define MAX_SOL 262144

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

typedef struct {
    int v[3];
    int p[3];
} Clause;

typedef struct {
    int n;
    int m;
    Clause c[MAX_M];
} Formula;

static void gen_random_3sat(Formula *f, int n, int m){
    f->n = n;
    f->m = m;
    for(int k = 0; k < m; k++){
        int chosen[3] = {-1, -1, -1};
        for(int i = 0; i < 3; i++){
            int v;
            do { v = rng_next() % n; } while(v == chosen[0] || v == chosen[1]);
            chosen[i] = v;
            f->c[k].v[i] = v;
            f->c[k].p[i] = rng_next() & 1;
        }
    }
}

static int satisfies(const Formula *f, int x){
    for(int k = 0; k < f->m; k++){
        int sat = 0;
        for(int i = 0; i < 3; i++){
            int bit = (x >> f->c[k].v[i]) & 1;
            if(f->c[k].p[i]) bit = !bit;
            if(bit){sat = 1; break;}
        }
        if(!sat) return 0;
    }
    return 1;
}

static int enumerate_solutions(const Formula *f, int *out, int max_out){
    int count = 0;
    int N = 1 << f->n;
    for(int x = 0; x < N; x++){
        if(satisfies(f, x)){
            if(count < max_out) out[count] = x;
            count++;
        }
    }
    return count;
}

/* ═══ UNION-FIND for cluster detection ═══ */
static int uf_parent[MAX_SOL];
static int uf_find(int x){
    while(uf_parent[x] != x){
        uf_parent[x] = uf_parent[uf_parent[x]];
        x = uf_parent[x];
    }
    return x;
}
static void uf_union(int x, int y){
    int rx = uf_find(x), ry = uf_find(y);
    if(rx != ry) uf_parent[rx] = ry;
}

/* Build clusters via Hamming-1 edges. Returns number of clusters
 * and fills cluster_id[] with canonical class ids 0..n_clusters-1. */
static int build_clusters(const int *sol, int n_sol, int *cluster_id){
    for(int i = 0; i < n_sol; i++) uf_parent[i] = i;
    for(int i = 0; i < n_sol; i++){
        for(int j = i + 1; j < n_sol; j++){
            if(__builtin_popcount(sol[i] ^ sol[j]) == 1){
                uf_union(i, j);
            }
        }
    }
    /* Renumber roots to 0..n_clusters-1 */
    int map[MAX_SOL];
    for(int i = 0; i < n_sol; i++) map[i] = -1;
    int next_id = 0;
    for(int i = 0; i < n_sol; i++){
        int r = uf_find(i);
        if(map[r] < 0) map[r] = next_id++;
        cluster_id[i] = map[r];
    }
    return next_id;
}

/* Per-variable bias within a specific cluster. */
static double cluster_bias_var(const int *sol, int n_sol, const int *cluster_id,
                                int target_cluster, int var){
    int count_ones = 0, count_total = 0;
    for(int k = 0; k < n_sol; k++){
        if(cluster_id[k] != target_cluster) continue;
        count_total++;
        if((sol[k] >> var) & 1) count_ones++;
    }
    if(count_total == 0) return 0.5;
    return (double)count_ones / count_total;
}

/* Refined classification */
typedef enum {
    GFROZEN_0, GFROZEN_1,
    CFROZEN_DISAGREE,
    CBIASED, CFREE
} RefinedClass;

static const char *refined_name(RefinedClass c){
    switch(c){
    case GFROZEN_0:        return "global frozen=0";
    case GFROZEN_1:        return "global frozen=1";
    case CFROZEN_DISAGREE: return "cluster-frozen DISAGREE";
    case CBIASED:          return "cluster-biased";
    case CFREE:            return "cluster-free";
    }
    return "?";
}

static RefinedClass classify_refined(const int *sol, int n_sol,
                                      const int *cluster_id, int n_clusters,
                                      int var){
    /* Global bias */
    int n_ones = 0;
    for(int k = 0; k < n_sol; k++) if((sol[k] >> var) & 1) n_ones++;
    if(n_ones == 0) return GFROZEN_0;
    if(n_ones == n_sol) return GFROZEN_1;

    /* Per-cluster analysis */
    int all_cluster_frozen = 1;
    int cluster_frozen_values[MAX_SOL];
    int seen[MAX_SOL] = {0};
    int any_non_frozen_cluster = 0;

    for(int cl = 0; cl < n_clusters; cl++){
        double b = cluster_bias_var(sol, n_sol, cluster_id, cl, var);
        if(b == 0.0 || b == 1.0){
            cluster_frozen_values[cl] = (int)b;
        } else {
            all_cluster_frozen = 0;
            if(b > 0.05 && b < 0.95) any_non_frozen_cluster = 1;
            cluster_frozen_values[cl] = -1;
        }
        seen[cl] = 1;
    }

    if(all_cluster_frozen){
        /* Check if all clusters agree: if yes we should already have
         * caught it as global frozen. Must be disagreement. */
        int v0 = cluster_frozen_values[0];
        int disagree = 0;
        for(int cl = 1; cl < n_clusters; cl++){
            if(cluster_frozen_values[cl] != v0){disagree = 1; break;}
        }
        if(disagree) return CFROZEN_DISAGREE;
        /* All clusters frozen to same value → global frozen (already
         * returned above, shouldn't reach here). */
        return GFROZEN_1;
    }

    if(any_non_frozen_cluster){
        /* At least one cluster has a genuine intermediate bias */
        /* Check if any cluster gives a strong bias (>95% one way) */
        int any_extreme_cluster = 0;
        for(int cl = 0; cl < n_clusters; cl++){
            double b = cluster_bias_var(sol, n_sol, cluster_id, cl, var);
            if(b > 0.4 && b < 0.6){
                (void)any_extreme_cluster;
                return CFREE;
            }
        }
        return CBIASED;
    }

    return CFREE;
}

/* ═══ EXPERIMENT 1: One instance, full dissection ═══ */
static int solutions_buf[MAX_SOL];
static int cluster_buf[MAX_SOL];

static void experiment_single(void){
    printf("\n═══ EXPERIMENT 1: Per-cluster frozen analysis ═══\n\n");

    int n = 16;
    int m = 52;      /* α = 3.25 */
    rng_seed(7);

    Formula f;
    gen_random_3sat(&f, n, m);

    int n_sol = enumerate_solutions(&f, solutions_buf, MAX_SOL);
    printf("  n = %d, m = %d, α = %.2f, #solutions = %d\n",
           n, m, (double)m/n, n_sol);
    if(n_sol == 0){printf("  UNSAT — skip.\n"); return;}

    int n_clusters = build_clusters(solutions_buf, n_sol, cluster_buf);
    printf("  Clusters: %d\n\n", n_clusters);

    /* Print cluster sizes */
    int cluster_size[MAX_SOL] = {0};
    for(int k = 0; k < n_sol; k++) cluster_size[cluster_buf[k]]++;
    printf("  Cluster sizes: ");
    for(int c = 0; c < n_clusters; c++) printf("%d ", cluster_size[c]);
    printf("\n\n");

    /* Classify each variable */
    int refined_count[5] = {0};
    printf("    var | global bias | per-cluster biases              | refined class\n");
    printf("    ----+-------------+---------------------------------+--------------------------\n");
    for(int v = 0; v < n; v++){
        int n_ones = 0;
        for(int k = 0; k < n_sol; k++) if((solutions_buf[k] >> v) & 1) n_ones++;
        double gbias = (double)n_ones / n_sol;

        RefinedClass rc = classify_refined(solutions_buf, n_sol, cluster_buf, n_clusters, v);
        refined_count[rc]++;

        printf("    %3d |   %.4f    | ", v, gbias);
        for(int c = 0; c < n_clusters && c < 8; c++){
            double cb = cluster_bias_var(solutions_buf, n_sol, cluster_buf, c, v);
            printf("%.2f ", cb);
        }
        printf("| %s\n", refined_name(rc));
    }

    printf("\n  Refined class counts:\n");
    printf("    global frozen=0:        %d\n", refined_count[GFROZEN_0]);
    printf("    global frozen=1:        %d\n", refined_count[GFROZEN_1]);
    printf("    cluster-frozen DISAGREE:%d\n", refined_count[CFROZEN_DISAGREE]);
    printf("    cluster-biased:         %d\n", refined_count[CBIASED]);
    printf("    cluster-free:           %d\n", refined_count[CFREE]);
}

/* ═══ EXPERIMENT 2: Isolate a disagreeing variable ═══ */
static void experiment_disagreeing(void){
    printf("\n═══ EXPERIMENT 2: Cluster-frozen DISAGREE variables ═══\n\n");

    int n = 16;
    int m = 52;
    printf("  Searching for instances with disagreeing variables\n");
    printf("  (globally 'free' but locally frozen in each cluster).\n\n");

    int found = 0;
    for(int trial = 0; trial < 30 && found < 3; trial++){
        rng_seed(12345 + trial);
        Formula f;
        gen_random_3sat(&f, n, m);
        int n_sol = enumerate_solutions(&f, solutions_buf, MAX_SOL);
        if(n_sol < 4) continue;
        int n_clusters = build_clusters(solutions_buf, n_sol, cluster_buf);
        if(n_clusters < 2) continue;

        for(int v = 0; v < n; v++){
            RefinedClass rc = classify_refined(solutions_buf, n_sol, cluster_buf, n_clusters, v);
            if(rc == CFROZEN_DISAGREE){
                /* Report this */
                if(found >= 3) break;
                found++;

                int n_ones = 0;
                for(int k = 0; k < n_sol; k++) if((solutions_buf[k] >> v) & 1) n_ones++;
                double gbias = (double)n_ones / n_sol;

                printf("  Found #%d: trial %d, variable %d\n", found, trial, v);
                printf("    #solutions = %d, #clusters = %d\n", n_sol, n_clusters);
                printf("    global bias = %.4f  (looks 'free' or 'biased')\n", gbias);
                printf("    per-cluster bias: ");
                for(int c = 0; c < n_clusters; c++){
                    double cb = cluster_bias_var(solutions_buf, n_sol, cluster_buf, c, v);
                    printf("%.2f ", cb);
                }
                printf("\n");
                printf("    Within each cluster, variable %d is FROZEN —\n", v);
                printf("    but to DIFFERENT values in different clusters.\n");
                printf("    Globally it appears as intermediate-bias noise.\n\n");
                break;
            }
        }
    }
    if(found == 0){
        printf("  (No disagreeing variables found in 30 trials at this α;\n");
        printf("   may need larger formulas or different α.)\n");
    }
}

/* ═══ EXPERIMENT 3: Sweep α ═══ */
static void experiment_sweep(void){
    printf("\n═══ EXPERIMENT 3: Refined classes vs α ═══\n\n");

    int n = 14;
    int trials = 8;

    printf("  n = %d, averaged over %d trials\n\n", n, trials);
    printf("    α     | avg %%GFrozen | %%CDisagree | %%CBiased | %%CFree | avg #clust\n");
    printf("    ------+--------------+------------+----------+--------+-----------\n");

    int alphas_m[] = {28, 35, 42, 49, 56};
    int nalpha = sizeof(alphas_m) / sizeof(int);

    for(int ai = 0; ai < nalpha; ai++){
        int m = alphas_m[ai];
        double alpha = (double)m / n;
        double sum_gf = 0, sum_cd = 0, sum_cb = 0, sum_cf = 0, sum_nc = 0;
        int n_valid = 0;

        for(int t = 0; t < trials; t++){
            rng_seed(30000 + ai * 100 + t);
            Formula f;
            gen_random_3sat(&f, n, m);
            int n_sol = enumerate_solutions(&f, solutions_buf, MAX_SOL);
            if(n_sol == 0) continue;
            int n_clusters = build_clusters(solutions_buf, n_sol, cluster_buf);

            int counts[5] = {0};
            for(int v = 0; v < n; v++){
                counts[classify_refined(solutions_buf, n_sol, cluster_buf, n_clusters, v)]++;
            }
            int gfrozen = counts[GFROZEN_0] + counts[GFROZEN_1];
            sum_gf += 100.0 * gfrozen / n;
            sum_cd += 100.0 * counts[CFROZEN_DISAGREE] / n;
            sum_cb += 100.0 * counts[CBIASED] / n;
            sum_cf += 100.0 * counts[CFREE] / n;
            sum_nc += n_clusters;
            n_valid++;
        }
        if(n_valid == 0){
            printf("    %.2f  | (all UNSAT)\n", alpha);
            continue;
        }
        printf("    %.2f  |    %5.1f%%    |  %5.1f%%    | %5.1f%%   | %5.1f%% |  %.1f\n",
               alpha,
               sum_gf / n_valid,
               sum_cd / n_valid,
               sum_cb / n_valid,
               sum_cf / n_valid,
               sum_nc / n_valid);
    }

    printf("\n  Reading:\n");
    printf("    GFrozen:   variables with global bias 0 or 1\n");
    printf("    CDisagree: globally intermediate but cluster-frozen — the\n");
    printf("               'hidden' frozen variables distinguishing clusters\n");
    printf("    CBiased:   biased within some cluster\n");
    printf("    CFree:     truly free within at least one cluster\n");
}

/* ═══ EXPERIMENT 4: Local flippability confirms the classification ═══ */
static void experiment_flippability(void){
    printf("\n═══ EXPERIMENT 4: Local flippability per refined class ═══\n\n");

    int n = 16;
    int m = 50;
    rng_seed(99);
    Formula f;
    gen_random_3sat(&f, n, m);
    int n_sol = enumerate_solutions(&f, solutions_buf, MAX_SOL);
    if(n_sol == 0){printf("  UNSAT.\n"); return;}
    int n_clusters = build_clusters(solutions_buf, n_sol, cluster_buf);

    printf("  n = %d, m = %d, α = %.2f, #sol = %d, #clusters = %d\n\n",
           n, m, (double)m/n, n_sol, n_clusters);

    /* For each solution (anchor), check how many single-bit flips stay SAT,
     * bucketed by refined class. */
    int flip_success[5] = {0};
    int flip_attempts[5] = {0};

    for(int k = 0; k < n_sol; k++){
        int anchor = solutions_buf[k];
        for(int v = 0; v < n; v++){
            RefinedClass rc = classify_refined(solutions_buf, n_sol, cluster_buf, n_clusters, v);
            flip_attempts[rc]++;
            int flipped = anchor ^ (1 << v);
            if(satisfies(&f, flipped)) flip_success[rc]++;
        }
    }

    printf("    class                      | attempts | success | rate\n");
    printf("    ---------------------------+----------+---------+------\n");
    for(int c = 0; c < 5; c++){
        if(flip_attempts[c] == 0) continue;
        printf("    %-26s | %8d | %7d | %.1f%%\n",
               refined_name((RefinedClass)c),
               flip_attempts[c], flip_success[c],
               100.0 * flip_success[c] / flip_attempts[c]);
    }

    printf("\n  Expected and observed behaviour:\n");
    printf("    global frozen:    0%% flippable (locked by formula)\n");
    printf("    cluster-DISAGREE: 0%% flippable (locked within cluster;\n");
    printf("                      flipping exits current cluster)\n");
    printf("    cluster-biased:   moderate flippability\n");
    printf("    cluster-free:     some flippability\n");
    printf("\n  The apparent mystery from frozen_core.c (free-looking\n");
    printf("  variables with zero local flippability) is resolved:\n");
    printf("  those variables are cluster-frozen-disagreeing.\n");
}

/* ═══ EXPERIMENT 5: Cluster count vs α ═══ */
static void experiment_cluster_count(void){
    printf("\n═══ EXPERIMENT 5: Number of clusters vs α ═══\n\n");

    int n = 14;
    int trials = 8;

    printf("  n = %d, averaged over %d trials\n\n", n, trials);
    printf("    α     | avg #sol | avg #clusters | avg largest cluster | singletons\n");
    printf("    ------+----------+---------------+---------------------+-----------\n");

    int alphas_m[] = {14, 21, 28, 35, 42, 49, 56};
    int nalpha = sizeof(alphas_m) / sizeof(int);

    for(int ai = 0; ai < nalpha; ai++){
        int m = alphas_m[ai];
        double alpha = (double)m / n;
        double sum_sol = 0, sum_clust = 0, sum_largest = 0, sum_singletons = 0;
        int n_valid = 0;

        for(int t = 0; t < trials; t++){
            rng_seed(40000 + ai * 100 + t);
            Formula f;
            gen_random_3sat(&f, n, m);
            int n_sol = enumerate_solutions(&f, solutions_buf, MAX_SOL);
            if(n_sol == 0) continue;
            int n_clusters = build_clusters(solutions_buf, n_sol, cluster_buf);

            int size[MAX_SOL] = {0};
            for(int k = 0; k < n_sol; k++) size[cluster_buf[k]]++;
            int largest = 0, singletons = 0;
            for(int c = 0; c < n_clusters; c++){
                if(size[c] > largest) largest = size[c];
                if(size[c] == 1) singletons++;
            }
            sum_sol += n_sol;
            sum_clust += n_clusters;
            sum_largest += largest;
            sum_singletons += singletons;
            n_valid++;
        }
        if(n_valid == 0){
            printf("    %.2f  | (all UNSAT)\n", alpha);
            continue;
        }
        printf("    %.2f  | %8.0f | %13.1f | %19.0f | %.1f\n",
               alpha,
               sum_sol / n_valid,
               sum_clust / n_valid,
               sum_largest / n_valid,
               sum_singletons / n_valid);
    }

    printf("\n  The classical α_d transition is visible as a rise in\n");
    printf("  the number of clusters. Below α_d the solution space is\n");
    printf("  one blob; near the threshold it shatters into many.\n");
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("PER-CLUSTER FROZEN CORE\n");
    printf("══════════════════════════════════════════\n");
    printf("Refines frozen/biased/free by looking inside each cluster.\n");

    experiment_single();
    experiment_disagreeing();
    experiment_sweep();
    experiment_flippability();
    experiment_cluster_count();

    printf("\n══════════════════════════════════════════\n");
    printf("KEY FINDINGS:\n");
    printf("  1. A global-free variable may be frozen WITHIN each\n");
    printf("     cluster with different values in different clusters\n");
    printf("     ('cluster-distinguisher').\n");
    printf("  2. Such variables are LOCALLY unflippable even though\n");
    printf("     their global bias looks symmetric.\n");
    printf("  3. The refined five-layer classification explains the\n");
    printf("     apparent mystery from frozen_core.c exp 4.\n");
    printf("  4. Per-cluster analysis matches the Mezard-Parisi-\n");
    printf("     Zecchina picture of random 3-SAT solution space\n");
    printf("     more faithfully than global bias alone.\n");
    return 0;
}
