/*
 * Test: fix ONE variable at a time (instead of 1%)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N       5000
#define MAX_CLAUSES 25000
#define MAX_K       3
#define MAX_DEGREE  200

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];
static double eta[MAX_CLAUSES][MAX_K];
static double W_plus[MAX_N], W_minus[MAX_N], W_zero[MAX_N];

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
static double rng_double(void){return(rng_next()>>11)*(1.0/9007199254740992.0);}

static void generate(int n, double ratio, unsigned long long seed){
    n_vars=n; n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES) n_clauses=MAX_CLAUSES;
    rng_seed(seed); memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3]; vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            cl_var[ci][j]=vs[j]; cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}
        }
    }
    for(int ci=0;ci<n_clauses;ci++) cl_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
}

static double sp_compute_edge(int ci, int pos_i) {
    int var_i = cl_var[ci][pos_i];
    if(var_fixed[var_i] >= 0) return 0;
    double product = 1.0;
    for(int pj = 0; pj < 3; pj++) {
        if(pj == pos_i) continue;
        int j = cl_var[ci][pj];
        if(var_fixed[j] >= 0) {
            int sj = cl_sign[ci][pj];
            if((sj==1 && var_fixed[j]==1) || (sj==-1 && var_fixed[j]==0)) return 0;
            continue;
        }
        int sign_j_in_a = cl_sign[ci][pj];
        double prod_s = 1.0, prod_u = 1.0;
        for(int d = 0; d < vdeg[j]; d++) {
            int bi = vlist[j][d], bp = vpos[j][d];
            if(bi == ci || !cl_active[bi]) continue;
            int b_sat = 0;
            for(int k=0; k<3; k++) {
                int vk = cl_var[bi][k];
                if(var_fixed[vk] >= 0) {
                    int sk = cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))
                        { b_sat=1; break; }
                }
            }
            if(b_sat) continue;
            int sign_j_in_b = cl_sign[bi][bp];
            double eta_b = eta[bi][bp];
            if(sign_j_in_b == sign_j_in_a) prod_s *= (1.0 - eta_b);
            else prod_u *= (1.0 - eta_b);
        }
        double P_u = (1.0 - prod_u) * prod_s;
        double P_s = (1.0 - prod_s) * prod_u;
        double P_0 = prod_u * prod_s;
        double denom = P_u + P_s + P_0;
        product *= (denom > 1e-15) ? (P_u / denom) : 0.0;
    }
    return product;
}

static double sp_iterate(double rho) {
    double max_change = 0;
    for(int ci = 0; ci < n_clauses; ci++) {
        if(!cl_active[ci]) continue;
        for(int p = 0; p < 3; p++) {
            if(var_fixed[cl_var[ci][p]] >= 0) continue;
            double nv = sp_compute_edge(ci, p);
            double ov = eta[ci][p];
            double up = rho * ov + (1.0 - rho) * nv;
            double ch = fabs(up - ov);
            if(ch > max_change) max_change = ch;
            eta[ci][p] = up;
        }
    }
    return max_change;
}

static void sp_compute_bias(void) {
    for(int i = 0; i < n_vars; i++) {
        W_plus[i] = W_minus[i] = 0; W_zero[i] = 1;
        if(var_fixed[i] >= 0) continue;
        double prod_plus = 1.0, prod_minus = 1.0;
        for(int d = 0; d < vdeg[i]; d++) {
            int ci = vlist[i][d], p = vpos[i][d];
            if(!cl_active[ci]) continue;
            int sat = 0;
            for(int k=0; k<3; k++) {
                int vk = cl_var[ci][k];
                if(vk != i && var_fixed[vk] >= 0) {
                    int sk = cl_sign[ci][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))
                        { sat=1; break; }
                }
            }
            if(sat) continue;
            int s = cl_sign[ci][p];
            double e = eta[ci][p];
            if(s == 1) prod_plus *= (1.0 - e);
            else prod_minus *= (1.0 - e);
        }
        double pi_plus  = (1.0 - prod_plus) * prod_minus;
        double pi_minus = (1.0 - prod_minus) * prod_plus;
        double pi_zero  = prod_plus * prod_minus;
        double total = pi_plus + pi_minus + pi_zero;
        if(total > 1e-15) {
            W_plus[i]  = pi_plus / total;
            W_minus[i] = pi_minus / total;
            W_zero[i]  = pi_zero / total;
        } else { W_zero[i] = 1.0; }
    }
}

static int unit_propagate(void) {
    int changed = 1;
    while(changed) {
        changed = 0;
        for(int ci=0; ci<n_clauses; ci++) {
            if(!cl_active[ci]) continue;
            int sat=0, fc=0, fv=-1, fs=0;
            for(int j=0; j<3; j++) {
                int v = cl_var[ci][j], s = cl_sign[ci][j];
                if(var_fixed[v] >= 0) {
                    if((s==1 && var_fixed[v]==1)||(s==-1 && var_fixed[v]==0)) sat = 1;
                } else { fc++; fv=v; fs=s; }
            }
            if(sat) { cl_active[ci]=0; continue; }
            if(fc==0) return 1;
            if(fc==1) { var_fixed[fv] = (fs==1) ? 1 : 0; changed=1; }
        }
    }
    return 0;
}

/* Try to converge with escalating damping + reinit */
static int sp_converge(int seed_hint) {
    /* Try with current surveys, escalating damping */
    double rhos[] = {0.2, 0.3, 0.5, 0.7, 0.85};
    for(int s = 0; s < 5; s++) {
        for(int iter = 0; iter < 300; iter++) {
            double ch = sp_iterate(rhos[s]);
            if(ch < 1e-4) return 1;
        }
    }
    /* Reinitialize and retry */
    for(int retry = 0; retry < 5; retry++) {
        rng_seed(seed_hint * 10007 + retry * 31337);
        for(int ci=0; ci<n_clauses; ci++) {
            if(!cl_active[ci]) continue;
            for(int j=0; j<3; j++) {
                if(var_fixed[cl_var[ci][j]] >= 0) continue;
                eta[ci][j] = rng_double();
            }
        }
        for(int s = 0; s < 5; s++) {
            for(int iter = 0; iter < 300; iter++) {
                double ch = sp_iterate(rhos[s]);
                if(ch < 1e-4) return 1;
            }
        }
    }
    return 0;
}

int main(void) {
    int nn = 1000;
    generate(nn, 4.267, 11000000ULL);
    unit_propagate();
    int n_fixed = 0;
    for(int v=0;v<nn;v++) if(var_fixed[v]>=0) n_fixed++;

    /* Initialize surveys */
    rng_seed(42);
    for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<3;j++)
            eta[ci][j] = rng_double();

    printf("Single-variable decimation, n=%d\n\n", nn);

    int round = 0;
    int sp_failures = 0;
    while(n_fixed < nn && round < 1200) {
        round++;

        int conv = sp_converge(round);
        if(!conv) {
            sp_failures++;
            if(round <= 200 || round % 50 == 0)
                printf("Rd %4d: fixed=%4d, SP FAILED (#%d)\n", round, n_fixed, sp_failures);

            /* When SP fails, fix a random free variable with random value */
            for(int v=0; v<nn; v++) {
                if(var_fixed[v] < 0) {
                    var_fixed[v] = rng_next() & 1;
                    n_fixed++;
                    for(int d=0; d<vdeg[v]; d++) {
                        int ci = vlist[v][d], p = vpos[v][d];
                        if(!cl_active[ci]) continue;
                        int s = cl_sign[ci][p];
                        if((s==1 && var_fixed[v]==1) || (s==-1 && var_fixed[v]==0))
                            cl_active[ci] = 0;
                    }
                    break;
                }
            }
            if(unit_propagate()) {
                printf("Rd %4d: CONTRADICTION at n_fixed=%d\n", round, n_fixed);
                break;
            }
            n_fixed = 0;
            for(int v=0;v<nn;v++) if(var_fixed[v]>=0) n_fixed++;
            continue;
        }

        /* Check trivialization */
        double max_eta = 0;
        for(int ci=0;ci<n_clauses;ci++) {
            if(!cl_active[ci]) continue;
            for(int j=0;j<3;j++) {
                if(var_fixed[cl_var[ci][j]] >= 0) continue;
                if(eta[ci][j] > max_eta) max_eta = eta[ci][j];
            }
        }
        if(max_eta < 0.01) {
            printf("Rd %4d: TRIVIAL (free=%d)\n", round, nn-n_fixed);
            break;
        }

        /* Fix THE single most biased variable */
        sp_compute_bias();
        double best_bias = -1;
        int best_var = -1, best_val = 0;
        for(int v=0; v<nn; v++) {
            if(var_fixed[v] >= 0) continue;
            double b = fabs(W_plus[v] - W_minus[v]);
            if(b > best_bias) { best_bias = b; best_var = v; best_val = (W_plus[v] > W_minus[v]) ? 1 : 0; }
        }
        if(best_var < 0 || best_bias < 0.001) {
            printf("Rd %4d: No biased var (best=%.4f)\n", round, best_bias);
            break;
        }

        var_fixed[best_var] = best_val;
        n_fixed++;
        for(int d=0; d<vdeg[best_var]; d++) {
            int ci = vlist[best_var][d], p = vpos[best_var][d];
            if(!cl_active[ci]) continue;
            int s = cl_sign[ci][p];
            if((s==1 && best_val==1) || (s==-1 && best_val==0))
                cl_active[ci] = 0;
        }

        if(unit_propagate()) {
            n_fixed = 0;
            for(int v=0;v<nn;v++) if(var_fixed[v]>=0) n_fixed++;
            printf("Rd %4d: CONTRADICTION (fixed=%d)\n", round, n_fixed);
            break;
        }
        n_fixed = 0;
        for(int v=0;v<nn;v++) if(var_fixed[v]>=0) n_fixed++;

        if(round <= 20 || round % 50 == 0)
            printf("Rd %4d: fixed=%4d, bias=%.4f\n", round, n_fixed, best_bias);
    }

    printf("\nFinal: %d/%d fixed, SP failures: %d\n", n_fixed, nn, sp_failures);
    return 0;
}
