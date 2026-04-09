/*
 * SP v4: Fast Survey Propagation — focus on speed
 * ================================================
 *
 * Key insight: literature SP converges in 20-50 iterations.
 * If 100 iterations aren't enough, more won't help.
 *
 * Speed optimizations:
 *   - Max 100 iterations per SP round (not 1000)
 *   - Single damping ρ=0.1 (not 5 escalation steps)
 *   - 2% decimation per round (fast, ~50 rounds total)
 *   - No restart on SP non-convergence (just go to WalkSAT)
 *   - Warm start: keep eta from previous round
 *
 * Compile: gcc -O3 -march=native -o sp_v4 sp_v4.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       20000
#define MAX_CLAUSES 100000
#define MAX_K       3
#define MAX_DEGREE  300

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N];

static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

static double eta[MAX_CLAUSES][MAX_K];
static double W_plus[MAX_N], W_minus[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void) {
    unsigned long long s0=rng_s[0], s1=rng_s[1], s2=rng_s[2], s3=rng_s[3];
    unsigned long long r = ((s1*5)<<7|(s1*5)>>57)*9;
    unsigned long long t = s1<<17;
    s2^=s0; s3^=s1; s1^=s2; s0^=s3; s2^=t; s3=(s3<<45)|(s3>>19);
    rng_s[0]=s0; rng_s[1]=s1; rng_s[2]=s2; rng_s[3]=s3;
    return r;
}
static void rng_seed(unsigned long long s) {
    rng_s[0]=s; rng_s[1]=s*6364136223846793005ULL+1;
    rng_s[2]=s*1103515245ULL+12345; rng_s[3]=s^0xdeadbeefcafebabeULL;
    for(int i=0;i<20;i++) rng_next();
}
static double rng_double(void) {
    return (rng_next()>>11)*(1.0/9007199254740992.0);
}

static void generate(int n, double ratio, unsigned long long seed) {
    n_vars = n;
    n_clauses = (int)(ratio * n);
    if(n_clauses > MAX_CLAUSES) n_clauses = MAX_CLAUSES;
    rng_seed(seed);
    memset(vdeg, 0, sizeof(int)*n);
    for(int ci=0; ci<n_clauses; ci++) {
        int vs[3];
        vs[0] = rng_next() % n;
        do { vs[1] = rng_next() % n; } while(vs[1]==vs[0]);
        do { vs[2] = rng_next() % n; } while(vs[2]==vs[0] || vs[2]==vs[1]);
        for(int j=0; j<3; j++) {
            cl_var[ci][j] = vs[j];
            cl_sign[ci][j] = (rng_next()&1) ? 1 : -1;
            int v = vs[j];
            if(vdeg[v] < MAX_DEGREE) {
                vlist[v][vdeg[v]] = ci;
                vpos[v][vdeg[v]] = j;
                vdeg[v]++;
            }
        }
    }
    for(int ci=0; ci<n_clauses; ci++) cl_active[ci] = 1;
    memset(var_fixed, -1, sizeof(int)*n);
}

/* 3-state SP edge computation */
static inline double sp_edge(int ci, int pos_i) {
    double product = 1.0;
    for(int pj = 0; pj < 3; pj++) {
        if(pj == pos_i) continue;
        int j = cl_var[ci][pj];
        if(var_fixed[j] >= 0) {
            int sj = cl_sign[ci][pj];
            if((sj==1 && var_fixed[j]==1) || (sj==-1 && var_fixed[j]==0))
                return 0.0;
            continue;
        }
        int sign_j_a = cl_sign[ci][pj];
        double ps = 1.0, pu = 1.0;
        for(int d = 0; d < vdeg[j]; d++) {
            int bi = vlist[j][d], bp = vpos[j][d];
            if(bi == ci || !cl_active[bi]) continue;
            /* Quick sat check */
            int bsat = 0;
            for(int k=0; k<3; k++) {
                int vk = cl_var[bi][k];
                if(var_fixed[vk] >= 0) {
                    int sk = cl_sign[bi][k];
                    if((sk==1 && var_fixed[vk]==1) || (sk==-1 && var_fixed[vk]==0))
                        { bsat=1; break; }
                }
            }
            if(bsat) continue;
            double eb = eta[bi][bp];
            if(cl_sign[bi][bp] == sign_j_a) ps *= (1.0 - eb);
            else pu *= (1.0 - eb);
        }
        double Pu = (1.0 - pu) * ps;
        double Ps = (1.0 - ps) * pu;
        double P0 = pu * ps;
        double den = Pu + Ps + P0;
        product *= (den > 1e-15) ? (Pu / den) : 0.0;
    }
    return product;
}

/* One SP sweep — sequential with random permutation of clauses */
static int *clause_perm;
static int perm_size;

static void init_perm(void) {
    if(!clause_perm) clause_perm = (int*)malloc(MAX_CLAUSES * sizeof(int));
    perm_size = 0;
    for(int ci=0; ci<n_clauses; ci++)
        if(cl_active[ci]) clause_perm[perm_size++] = ci;
}

static void shuffle_perm(void) {
    for(int i=perm_size-1; i>0; i--) {
        int j = rng_next() % (i+1);
        int t = clause_perm[i]; clause_perm[i] = clause_perm[j]; clause_perm[j] = t;
    }
}

static double sp_sweep(double rho) {
    shuffle_perm();
    double max_ch = 0;
    for(int e = 0; e < perm_size; e++) {
        int ci = clause_perm[e];
        if(!cl_active[ci]) continue;
        for(int p = 0; p < 3; p++) {
            if(var_fixed[cl_var[ci][p]] >= 0) continue;
            double nv = sp_edge(ci, p);
            double ov = eta[ci][p];
            double up = rho * ov + (1.0 - rho) * nv;
            double ch = fabs(up - ov);
            if(ch > max_ch) max_ch = ch;
            eta[ci][p] = up;
        }
    }
    return max_ch;
}

/* Bias computation */
static void compute_bias(void) {
    for(int i = 0; i < n_vars; i++) {
        W_plus[i] = W_minus[i] = 0;
        if(var_fixed[i] >= 0) continue;
        double pp = 1.0, pm = 1.0;
        for(int d = 0; d < vdeg[i]; d++) {
            int ci = vlist[i][d], p = vpos[i][d];
            if(!cl_active[ci]) continue;
            int sat = 0;
            for(int k=0; k<3; k++) {
                int vk = cl_var[ci][k];
                if(vk != i && var_fixed[vk] >= 0) {
                    int sk = cl_sign[ci][k];
                    if((sk==1 && var_fixed[vk]==1) || (sk==-1 && var_fixed[vk]==0))
                        { sat=1; break; }
                }
            }
            if(sat) continue;
            double e = eta[ci][p];
            if(cl_sign[ci][p] == 1) pp *= (1.0 - e);
            else pm *= (1.0 - e);
        }
        double pi_p = (1.0 - pp) * pm;
        double pi_m = (1.0 - pm) * pp;
        double pi_0 = pp * pm;
        double tot = pi_p + pi_m + pi_0;
        if(tot > 1e-15) {
            W_plus[i] = pi_p / tot;
            W_minus[i] = pi_m / tot;
        }
    }
}

/* Unit propagation */
static int unit_prop(void) {
    int changed = 1;
    while(changed) {
        changed = 0;
        for(int ci=0; ci<n_clauses; ci++) {
            if(!cl_active[ci]) continue;
            int sat=0, fc=0, fv=-1, fs=0;
            for(int j=0; j<3; j++) {
                int v = cl_var[ci][j], s = cl_sign[ci][j];
                if(var_fixed[v] >= 0) {
                    if((s==1 && var_fixed[v]==1) || (s==-1 && var_fixed[v]==0)) sat=1;
                } else { fc++; fv=v; fs=s; }
            }
            if(sat) { cl_active[ci]=0; continue; }
            if(fc==0) return 1;
            if(fc==1) { var_fixed[fv]=(fs==1)?1:0; changed=1; }
        }
    }
    return 0;
}

/* WalkSAT */
static int walksat(int max_flips) {
    int n = n_vars, m = n_clauses;
    int *a = (int*)malloc(n * sizeof(int));
    for(int v=0; v<n; v++)
        a[v] = (var_fixed[v]>=0) ? var_fixed[v] : ((rng_next()&1)?1:0);

    int *sc = (int*)calloc(m, sizeof(int));
    for(int ci=0; ci<m; ci++)
        for(int j=0; j<3; j++) {
            int v = cl_var[ci][j], s = cl_sign[ci][j];
            if((s==1 && a[v]==1) || (s==-1 && a[v]==0)) sc[ci]++;
        }

    int *ul = (int*)malloc(m * sizeof(int));
    int *up = (int*)malloc(m * sizeof(int));
    int nu = 0;
    memset(up, -1, sizeof(int)*m);
    for(int ci=0; ci<m; ci++)
        if(sc[ci]==0) { up[ci]=nu; ul[nu++]=ci; }

    for(int f=0; f<max_flips && nu>0; f++) {
        int ci = ul[rng_next() % nu];
        int bv = cl_var[ci][0], bb = m+1, zb = -1;
        for(int j=0; j<3; j++) {
            int v = cl_var[ci][j], br = 0;
            for(int d=0; d<vdeg[v]; d++) {
                int oci = vlist[v][d], opos = vpos[v][d];
                int os = cl_sign[oci][opos];
                if(((os==1 && a[v]==1) || (os==-1 && a[v]==0)) && sc[oci]==1) br++;
            }
            if(br == 0) { zb = v; break; }
            if(br < bb) { bb = br; bv = v; }
        }
        int fv = (zb>=0) ? zb : ((rng_next()%100<57) ? cl_var[ci][rng_next()%3] : bv);

        int old = a[fv], nw = 1-old;
        a[fv] = nw;
        for(int d=0; d<vdeg[fv]; d++) {
            int oci = vlist[fv][d], opos = vpos[fv][d];
            int os = cl_sign[oci][opos];
            int was = ((os==1 && old==1) || (os==-1 && old==0));
            int now = ((os==1 && nw==1) || (os==-1 && nw==0));
            if(was && !now) { sc[oci]--; if(sc[oci]==0) { up[oci]=nu; ul[nu++]=oci; } }
            else if(!was && now) { sc[oci]++; if(sc[oci]==1) {
                int p2=up[oci]; if(p2>=0&&p2<nu) { int l=ul[nu-1]; ul[p2]=l; up[l]=p2; up[oci]=-1; nu--; }
            }}
        }
    }
    for(int v=0; v<n; v++) var_fixed[v] = a[v];
    int res = m - nu;
    free(a); free(sc); free(ul); free(up);
    return res;
}

/* Fix a variable and propagate */
static void fix_var(int v, int val) {
    var_fixed[v] = val;
    for(int d=0; d<vdeg[v]; d++) {
        int ci = vlist[v][d], p = vpos[v][d];
        if(!cl_active[ci]) continue;
        int s = cl_sign[ci][p];
        if((s==1 && val==1) || (s==-1 && val==0))
            cl_active[ci] = 0;
    }
}

static int saved_active[MAX_CLAUSES];
static int saved_fixed[MAX_N];

static int sp_solve(int nn) {
    int n = nn, m = n_clauses;

    if(unit_prop()) return 0;
    memcpy(saved_active, cl_active, sizeof(int)*m);
    memcpy(saved_fixed, var_fixed, sizeof(int)*n);

    for(int restart = 0; restart < 3; restart++) {
        if(restart > 0) {
            memcpy(cl_active, saved_active, sizeof(int)*m);
            memcpy(var_fixed, saved_fixed, sizeof(int)*n);
        }

        int nf = 0;
        for(int v=0; v<n; v++) if(var_fixed[v]>=0) nf++;

        /* Init surveys */
        rng_seed(42ULL + restart * 9973ULL + (unsigned long long)n * 13);
        for(int ci=0; ci<m; ci++)
            for(int j=0; j<3; j++)
                eta[ci][j] = rng_double();

        init_perm();

        while(nf < n) {
            /* Converge SP: max 100 iterations, rho=0.1 */
            int conv = 0;
            for(int iter = 0; iter < 100; iter++) {
                double ch = sp_sweep(0.1);
                if(ch < 1e-4) { conv=1; break; }
            }
            /* If not converged, try heavier damping briefly */
            if(!conv) {
                for(int iter = 0; iter < 50; iter++) {
                    double ch = sp_sweep(0.3);
                    if(ch < 1e-4) { conv=1; break; }
                }
            }
            if(!conv) break; /* give up SP, switch to WalkSAT */

            /* Check trivialization */
            double max_eta = 0;
            for(int ci=0; ci<m; ci++) {
                if(!cl_active[ci]) continue;
                for(int j=0; j<3; j++) {
                    if(var_fixed[cl_var[ci][j]] >= 0) continue;
                    if(eta[ci][j] > max_eta) max_eta = eta[ci][j];
                }
            }
            if(max_eta < 0.01) break; /* trivialized → WalkSAT */

            /* Compute bias and fix most biased variables */
            compute_bias();

            int nfree = n - nf;
            int nfix = nfree / 50; /* 2% per round */
            if(nfix < 1) nfix = 1;
            if(nfix > 100) nfix = 100;

            for(int f = 0; f < nfix; f++) {
                double bb = -1;
                int bv = -1, bval = 0;
                for(int v=0; v<n; v++) {
                    if(var_fixed[v] >= 0) continue;
                    double b = fabs(W_plus[v] - W_minus[v]);
                    if(b > bb) { bb=b; bv=v; bval=(W_plus[v]>W_minus[v])?1:0; }
                }
                if(bv < 0 || bb < 0.001) break;
                fix_var(bv, bval);
                nf++;
            }

            if(unit_prop()) break;
            nf = 0;
            for(int v=0; v<n; v++) if(var_fixed[v]>=0) nf++;
            init_perm();
        }

        /* WalkSAT finish */
        int flips = n * 3000;
        if(flips > 10000000) flips = 10000000;

        for(int ws = 0; ws < 5; ws++) {
            rng_seed(restart * 77777ULL + ws * 12345ULL + nf);
            int sat = walksat(flips);
            if(sat == m) return sat;
        }
    }

    rng_seed(999999ULL);
    return walksat(n_vars * 10000);
}

int main(void) {
    printf("====================================================\n");
    printf("SP v4: FAST 3-state SP + 2%% decimation\n");
    printf("====================================================\n");
    printf("Max 150 SP iters/round, rho=0.1/0.3, 2%% batch\n\n");

    int test_n[] = {100, 200, 300, 500, 750, 1000, 2000, 3000, 5000, 10000};
    int sizes = 10;

    printf("%6s | %5s | %6s | %8s | %s\n",
           "n", "total", "solved", "time_ms", "rate");
    printf("-------+-------+--------+----------+------\n");

    for(int ti=0; ti<sizes; ti++) {
        int nn = test_n[ti];
        int ni;
        if(nn <= 200) ni = 20;
        else if(nn <= 500) ni = 10;
        else if(nn <= 2000) ni = 5;
        else ni = 3;

        int solved = 0, total = 0;
        double tms = 0;

        for(int seed=0; seed < ni * 3 && total < ni; seed++) {
            generate(nn, 4.267, 11000000ULL + seed);
            clock_t t0 = clock();
            rng_seed(seed * 31337ULL);
            int sat = sp_solve(nn);
            clock_t t1 = clock();
            double ms = (double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            tms += ms;
            total++;
            if(sat == n_clauses) solved++;
        }

        printf("%6d | %2d/%2d | %4d   | %7.0fms | %3.0f%%\n",
               nn, solved, total, solved, tms/total,
               100.0*solved/total);
        fflush(stdout);

        if(tms/total > 120000 && solved == 0) {
            printf("  (stopping: >2min/instance with 0%% rate)\n");
            break;
        }
    }

    printf("\n=== HISTORY ===\n");
    printf("sp_correct (4-state):  n=750 40%%, n=1000 0%%\n");
    printf("sp_v2 (3-state, 1var): n=750 40%%, n=1000 20%%, n=2000 0%%\n");
    printf("sp_v4 (this):          (results above)\n");
    printf("Literature:            n=100000+ at threshold\n");

    return 0;
}
