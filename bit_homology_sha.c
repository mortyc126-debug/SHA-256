/*
 * BIT HOMOLOGY OF SHA-256
 * =========================
 *
 * Stage G: apply our persistent-homology and spectral-graph tools
 * to state clouds produced by reduced-round SHA-256.  We already
 * know from bit_calculus and the Hamming correlation studies that
 * linear and statistical signals die by R=3. The question now is:
 *
 *     Do topological or spectral invariants persist LONGER than
 *     linear signals? Can persistent homology / Fiedler value
 *     distinguish reduced-round SHA-256 from a random oracle at
 *     rounds where Walsh spectra are already flat?
 *
 * Novel angle: every prior SHA-256 analysis measures point-wise
 * properties (bias, differential probabilities, correlations).
 * Topology measures GLOBAL SHAPE — connectedness, holes, clusters.
 * A round function that is statistically indistinguishable from
 * random at each bit could still leave macroscopic geometric
 * signatures in its reachable set.
 *
 * Invariants computed per dataset of N=80 state_R vectors:
 *
 *   1. Max persistence  (from union-find filtration on Hamming)
 *   2. Mean persistence
 *   3. Fiedler value λ_1 of the normalized Laplacian
 *   4. Largest eigengap λ_k+1 − λ_k  (cluster-count indicator)
 *   5. Cheeger bound  sqrt(2·λ_1)  (sparsest-cut proxy)
 *
 * Baseline: 80 uniformly random 256-bit vectors.  Any statistic
 * whose SHA-256 value lies outside the baseline's 95 % confidence
 * interval is a candidate topological signature.
 *
 * Compile: gcc -O3 -march=native -o bhsha bit_homology_sha.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define N_POINTS 80
#define N_RUNS 30      /* number of independent datasets per round count */

/* ═══ State vectors (256 bits) ═══ */
typedef struct { uint64_t b[4]; } State256;

static int state_ham(State256 a, State256 b){
    int d = 0;
    for(int i = 0; i < 4; i++) d += __builtin_popcountll(a.b[i] ^ b.b[i]);
    return d;
}
static double state_sim(State256 a, State256 b){
    return 1.0 - (double)state_ham(a, b) / 256.0;
}

/* ═══ SHA-256 CORE ═══ */
static const uint32_t K256[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};
static const uint32_t IV[8] = {
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
    0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
};
#define ROTR(x,n) (((x) >> (n)) | ((x) << (32-(n))))
#define SIG0(x)  (ROTR(x,2) ^ ROTR(x,13) ^ ROTR(x,22))
#define SIG1(x)  (ROTR(x,6) ^ ROTR(x,11) ^ ROTR(x,25))
#define CH(x,y,z)  (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))

static inline void sha256_round(uint32_t S[8], uint32_t Wt, int t){
    uint32_t T1 = S[7] + SIG1(S[4]) + CH(S[4],S[5],S[6]) + K256[t] + Wt;
    uint32_t T2 = SIG0(S[0]) + MAJ(S[0],S[1],S[2]);
    S[7]=S[6]; S[6]=S[5]; S[5]=S[4];
    S[4]=S[3]+T1;
    S[3]=S[2]; S[2]=S[1]; S[1]=S[0];
    S[0]=T1+T2;
}
static State256 state_pack(const uint32_t S[8]){
    State256 r;
    for(int i = 0; i < 4; i++)
        r.b[i] = ((uint64_t)S[2*i]) | ((uint64_t)S[2*i+1] << 32);
    return r;
}
static State256 sha256_Rrounds(const uint32_t *W, int R){
    uint32_t S[8]; memcpy(S, IV, sizeof(S));
    for(int t = 0; t < R; t++) sha256_round(S, W[t], t);
    return state_pack(S);
}

/* ═══ RNG ═══ */
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

static State256 random_state(void){
    State256 r;
    for(int i = 0; i < 4; i++) r.b[i] = rng_next();
    return r;
}

/* ═══ UNION-FIND ═══ */
static int uf_parent[N_POINTS];
static int uf_size[N_POINTS];
static void uf_init(int n){for(int i=0;i<n;i++){uf_parent[i]=i; uf_size[i]=1;}}
static int uf_find(int x){
    while(uf_parent[x] != x){uf_parent[x] = uf_parent[uf_parent[x]]; x = uf_parent[x];}
    return x;
}
static void uf_union(int x, int y){
    int rx = uf_find(x), ry = uf_find(y);
    if(rx == ry) return;
    if(uf_size[rx] < uf_size[ry]){int t = rx; rx = ry; ry = t;}
    uf_parent[ry] = rx; uf_size[rx] += uf_size[ry];
}

/* ═══ PERSISTENT HOMOLOGY (H_0) ═══ */
typedef struct { int i, j; double sim; } Edge;
static int edge_cmp(const void *a, const void *b){
    double sa = ((const Edge*)a)->sim;
    double sb = ((const Edge*)b)->sim;
    if(sa > sb) return -1;
    if(sa < sb) return 1;
    return 0;
}
static void compute_persistence(State256 *pts, int n, double *birth, double *death){
    int ne = n*(n-1)/2;
    Edge *E = malloc(ne * sizeof(Edge));
    int idx = 0;
    for(int i = 0; i < n; i++){
        for(int j = i+1; j < n; j++){
            E[idx].i = i; E[idx].j = j;
            E[idx].sim = state_sim(pts[i], pts[j]);
            idx++;
        }
    }
    qsort(E, ne, sizeof(Edge), edge_cmp);
    uf_init(n);
    for(int i = 0; i < n; i++){birth[i] = 1.0; death[i] = -1;}
    for(int e = 0; e < ne; e++){
        int ci = uf_find(E[e].i);
        int cj = uf_find(E[e].j);
        if(ci != cj){
            int younger, older;
            if(birth[ci] < birth[cj]){younger = ci; older = cj;}
            else if(birth[ci] > birth[cj]){younger = cj; older = ci;}
            else {younger = (ci < cj) ? cj : ci; older = (ci < cj) ? ci : cj;}
            (void)older;
            death[younger] = E[e].sim;
            uf_union(E[e].i, E[e].j);
        }
    }
    double min_sim = 1.0;
    for(int e = 0; e < ne; e++) if(E[e].sim < min_sim) min_sim = E[e].sim;
    for(int i = 0; i < n; i++) if(death[i] < 0) death[i] = min_sim;
    free(E);
}

/* ═══ JACOBI EIGENSOLVER ═══ */
static void jacobi(double *A, int n, double *ev, double *V){
    for(int i = 0; i < n; i++)
        for(int j = 0; j < n; j++) V[i*n+j] = (i==j) ? 1.0 : 0.0;
    for(int sweep = 0; sweep < 60; sweep++){
        double off = 0;
        for(int i = 0; i < n; i++)
            for(int j = i+1; j < n; j++) off += A[i*n+j]*A[i*n+j];
        if(off < 1e-20) break;
        for(int p = 0; p < n-1; p++){
            for(int q = p+1; q < n; q++){
                double apq = A[p*n+q];
                if(fabs(apq) < 1e-15) continue;
                double app = A[p*n+p];
                double aqq = A[q*n+q];
                double theta = (aqq - app) / (2.0 * apq);
                double t;
                if(theta >= 0) t = 1.0 / (theta + sqrt(1.0+theta*theta));
                else           t = 1.0 / (theta - sqrt(1.0+theta*theta));
                double c = 1.0 / sqrt(1.0+t*t);
                double s = t * c;
                A[p*n+p] = app - t*apq;
                A[q*n+q] = aqq + t*apq;
                A[p*n+q] = 0; A[q*n+p] = 0;
                for(int r = 0; r < n; r++){
                    if(r != p && r != q){
                        double arp = A[r*n+p];
                        double arq = A[r*n+q];
                        A[r*n+p] = c*arp - s*arq;
                        A[p*n+r] = A[r*n+p];
                        A[r*n+q] = s*arp + c*arq;
                        A[q*n+r] = A[r*n+q];
                    }
                }
                for(int r = 0; r < n; r++){
                    double vrp = V[r*n+p];
                    double vrq = V[r*n+q];
                    V[r*n+p] = c*vrp - s*vrq;
                    V[r*n+q] = s*vrp + c*vrq;
                }
            }
        }
    }
    for(int i = 0; i < n; i++) ev[i] = A[i*n+i];
    for(int i = 0; i < n-1; i++){
        int min = i;
        for(int j = i+1; j < n; j++) if(ev[j] < ev[min]) min = j;
        if(min != i){
            double t = ev[i]; ev[i] = ev[min]; ev[min] = t;
            for(int r = 0; r < n; r++){
                double tv = V[r*n+i]; V[r*n+i] = V[r*n+min]; V[r*n+min] = tv;
            }
        }
    }
}

/* ═══ PER-DATASET INVARIANTS ═══ */
typedef struct {
    double max_persistence;
    double mean_persistence;
    double lambda1;
    double eigengap_max;
    double cheeger;
} Invariants;

static void build_laplacian(State256 *pts, int n, double *L){
    double *W = calloc(n*n, sizeof(double));
    double *deg = calloc(n, sizeof(double));
    for(int i = 0; i < n; i++){
        for(int j = i+1; j < n; j++){
            double s = state_sim(pts[i], pts[j]);
            double w = 2.0*s - 1.0;
            if(w < 0) w = 0;
            W[i*n+j] = w; W[j*n+i] = w;
            deg[i] += w; deg[j] += w;
        }
    }
    for(int i = 0; i < n; i++){
        for(int j = 0; j < n; j++){
            if(i == j) L[i*n+j] = (deg[i] > 1e-12) ? 1.0 : 0.0;
            else {
                double d = sqrt(deg[i]*deg[j]);
                L[i*n+j] = (d > 1e-12) ? -W[i*n+j]/d : 0.0;
            }
        }
    }
    free(W); free(deg);
}

static Invariants compute_invariants(State256 *pts, int n){
    Invariants inv;

    /* Persistence */
    double *birth = malloc(n*sizeof(double));
    double *death = malloc(n*sizeof(double));
    compute_persistence(pts, n, birth, death);
    double maxp = 0, sump = 0;
    for(int i = 0; i < n; i++){
        double d = death[i];
        double p = birth[i] - d;
        if(p > maxp) maxp = p;
        sump += p;
    }
    inv.max_persistence = maxp;
    inv.mean_persistence = sump / n;
    free(birth); free(death);

    /* Spectral */
    double *L = malloc(n*n*sizeof(double));
    double *V = malloc(n*n*sizeof(double));
    double *ev = malloc(n*sizeof(double));
    build_laplacian(pts, n, L);
    jacobi(L, n, ev, V);
    inv.lambda1 = ev[1];
    double gap_max = 0;
    for(int i = 0; i < 10 && i+1 < n; i++){
        double g = ev[i+1] - ev[i];
        if(g > gap_max) gap_max = g;
    }
    inv.eigengap_max = gap_max;
    inv.cheeger = sqrt(2.0 * (ev[1] > 0 ? ev[1] : 0));
    free(L); free(V); free(ev);

    return inv;
}

/* Build an SHA dataset: N points from state_R with random W sequences */
static void build_sha_dataset(State256 *out, int n, int R){
    for(int i = 0; i < n; i++){
        uint32_t W[64];
        for(int j = 0; j < R; j++) W[j] = (uint32_t)rng_next();
        out[i] = sha256_Rrounds(W, R);
    }
}
static void build_random_dataset(State256 *out, int n){
    for(int i = 0; i < n; i++) out[i] = random_state();
}

/* Mean and standard deviation of a sequence */
static void mean_std(double *v, int n, double *mean, double *std){
    double s = 0, s2 = 0;
    for(int i = 0; i < n; i++){s += v[i]; s2 += v[i]*v[i];}
    *mean = s / n;
    double var = s2/n - (*mean)*(*mean);
    *std = sqrt(var > 0 ? var : 0);
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BIT HOMOLOGY OF SHA-256\n");
    printf("══════════════════════════════════════════\n");
    printf("Comparing topological and spectral invariants of\n");
    printf("reduced-round SHA-256 state clouds against a random oracle.\n");
    printf("N points per dataset = %d, datasets per config = %d\n\n",
           N_POINTS, N_RUNS);

    int rounds[] = {1, 2, 3, 4, 6, 8, 16, 64};
    int nR = 8;

    double *mp_sha  = malloc(N_RUNS*sizeof(double));
    double *mnp_sha = malloc(N_RUNS*sizeof(double));
    double *l1_sha  = malloc(N_RUNS*sizeof(double));
    double *gap_sha = malloc(N_RUNS*sizeof(double));

    /* Baseline: random oracle */
    printf("Computing RANDOM baseline (%d runs)...\n", N_RUNS);
    rng_seed(42);
    double bl_mp[N_RUNS], bl_mnp[N_RUNS], bl_l1[N_RUNS], bl_gap[N_RUNS];
    State256 pts[N_POINTS];
    for(int r = 0; r < N_RUNS; r++){
        build_random_dataset(pts, N_POINTS);
        Invariants inv = compute_invariants(pts, N_POINTS);
        bl_mp[r]  = inv.max_persistence;
        bl_mnp[r] = inv.mean_persistence;
        bl_l1[r]  = inv.lambda1;
        bl_gap[r] = inv.eigengap_max;
    }
    double bl_mp_m, bl_mp_s; mean_std(bl_mp, N_RUNS, &bl_mp_m, &bl_mp_s);
    double bl_mnp_m, bl_mnp_s; mean_std(bl_mnp, N_RUNS, &bl_mnp_m, &bl_mnp_s);
    double bl_l1_m, bl_l1_s; mean_std(bl_l1, N_RUNS, &bl_l1_m, &bl_l1_s);
    double bl_gap_m, bl_gap_s; mean_std(bl_gap, N_RUNS, &bl_gap_m, &bl_gap_s);

    printf("\nBaseline (random 256-bit vectors):\n");
    printf("  max persistence:  %.5f ± %.5f\n", bl_mp_m, bl_mp_s);
    printf("  mean persistence: %.5f ± %.5f\n", bl_mnp_m, bl_mnp_s);
    printf("  λ_1 (Fiedler):    %.5f ± %.5f\n", bl_l1_m, bl_l1_s);
    printf("  max eigengap:     %.5f ± %.5f\n", bl_gap_m, bl_gap_s);

    /* SHA-256 datasets across rounds */
    printf("\n%4s | %18s | %18s | %18s | %18s\n",
           "R", "max pers (σ)", "mean pers (σ)", "lambda_1 (σ)", "eigengap (σ)");
    printf("-----+--------------------+--------------------+--------------------+-------------------\n");

    for(int ri = 0; ri < nR; ri++){
        int R = rounds[ri];
        rng_seed(1000 + R);
        for(int r = 0; r < N_RUNS; r++){
            build_sha_dataset(pts, N_POINTS, R);
            Invariants inv = compute_invariants(pts, N_POINTS);
            mp_sha[r]  = inv.max_persistence;
            mnp_sha[r] = inv.mean_persistence;
            l1_sha[r]  = inv.lambda1;
            gap_sha[r] = inv.eigengap_max;
        }
        double mp_m, mp_s; mean_std(mp_sha, N_RUNS, &mp_m, &mp_s);
        double mnp_m, mnp_s; mean_std(mnp_sha, N_RUNS, &mnp_m, &mnp_s);
        double l1_m, l1_s; mean_std(l1_sha, N_RUNS, &l1_m, &l1_s);
        double gap_m, gap_s; mean_std(gap_sha, N_RUNS, &gap_m, &gap_s);

        /* z-score deviations from baseline */
        double z_mp  = (mp_m  - bl_mp_m)  / (bl_mp_s  > 1e-12 ? bl_mp_s  : 1e-12);
        double z_mnp = (mnp_m - bl_mnp_m) / (bl_mnp_s > 1e-12 ? bl_mnp_s : 1e-12);
        double z_l1  = (l1_m  - bl_l1_m)  / (bl_l1_s  > 1e-12 ? bl_l1_s  : 1e-12);
        double z_gap = (gap_m - bl_gap_m) / (bl_gap_s > 1e-12 ? bl_gap_s : 1e-12);
        (void)z_gap; /* shown inline */

        printf(" %3d | %7.5f (%+6.2fσ) | %7.5f (%+6.2fσ) | %7.5f (%+6.2fσ) | %7.5f (%+6.2fσ)\n",
               R, mp_m, z_mp, mnp_m, z_mnp, l1_m, z_l1, gap_m, z_gap);
    }

    printf("\nInterpretation:\n");
    printf("  |z| < 2   — statistic matches random oracle baseline\n");
    printf("  |z| ≥ 2   — potential topological signature\n");
    printf("  |z| ≥ 4   — strong signature, well above noise\n\n");

    printf("Any |z| ≥ 2 at R where linear structure is already dead\n");
    printf("(R ≥ 3 per bit_calculus.c) is a NEW finding: a topological\n");
    printf("invariant surviving beyond the linear-cryptanalysis horizon.\n");

    free(mp_sha); free(mnp_sha); free(l1_sha); free(gap_sha);
    return 0;
}
