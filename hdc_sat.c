/*
 * EXPERIMENT 1: HDC for SAT
 * ==========================
 *
 * Idea: encode SAT formula as hypervector, find solution by similarity.
 *
 * Each variable i → hypervector V_i
 * Each clause → sum of its 7 satisfying configurations (as bundled HDVs)
 * Formula → bundle of all clauses
 * Query: for assignment x, build its HDV, compare to formula
 *
 * Test: small SAT instances, see if HDC can distinguish SAT from UNSAT
 *       and find the actual solution.
 *
 * Compile: gcc -O3 -march=native -o hdc_sat hdc_sat.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <time.h>

#define D 16384
#define D_WORDS (D/64)

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

typedef struct {int c[D]; int n;} Bundle;
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

/* ═══ SAT encoding ═══ */

#define MAX_VARS 20

static HDV V_bit[2]; /* hypervectors for 0 and 1 */
static HDV V_pos[MAX_VARS]; /* position of each variable */

static HDV encode_assignment(const int *x, int n){
    HDV rep = hdv_zero();
    for(int i = 0; i < n; i++){
        HDV contrib = hdv_bind(V_bit[x[i]], V_pos[i]);
        rep = hdv_bind(rep, contrib);
    }
    return rep;
}

/* Encode a clause as bundle of all its satisfying assignments */
static HDV encode_clause_sat_set(int var[3], int sign[3], int n){
    Bundle b; bundle_init(&b);
    /* Enumerate 8 assignments of the 3 variables, add the 7 satisfying ones */
    for(int m = 0; m < 8; m++){
        int x[3] = {m&1, (m>>1)&1, (m>>2)&1};
        /* Check if satisfies clause */
        int sat = 0;
        for(int j = 0; j < 3; j++){
            if((sign[j] == 1 && x[j] == 1) || (sign[j] == -1 && x[j] == 0)){sat = 1; break;}
        }
        if(sat){
            /* Encode this partial assignment */
            HDV local = hdv_zero();
            for(int j = 0; j < 3; j++){
                HDV contrib = hdv_bind(V_bit[x[j]], V_pos[var[j]]);
                local = hdv_bind(local, contrib);
            }
            bundle_add(&b, local);
        }
    }
    return bundle_finalize(&b);
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("EXPERIMENT 1: HDC for SAT\n");
    printf("══════════════════════════════════════════\n");

    rng_seed(42);
    V_bit[0] = hdv_random();
    V_bit[1] = hdv_random();
    for(int i = 0; i < MAX_VARS; i++) V_pos[i] = hdv_random();

    /* Small test SAT: (x0∨x1∨x2) ∧ (¬x0∨x3∨x4) ∧ (x1∨¬x3∨x5) */
    int n = 6;
    int clauses[3][3] = {{0,1,2}, {0,3,4}, {1,3,5}};
    int signs[3][3] = {{1,1,1}, {-1,1,1}, {1,-1,1}};

    printf("Formula: (x0∨x1∨x2) ∧ (¬x0∨x3∨x4) ∧ (x1∨¬x3∨x5)\n");
    printf("Variables: %d, Clauses: %d\n\n", n, 3);

    /* Encode each clause as HDV */
    HDV clause_hdvs[3];
    for(int c = 0; c < 3; c++){
        clause_hdvs[c] = encode_clause_sat_set(clauses[c], signs[c], n);
    }

    /* Formula = bundle of clauses */
    Bundle fb; bundle_init(&fb);
    for(int c = 0; c < 3; c++) bundle_add(&fb, clause_hdvs[c]);
    HDV formula = bundle_finalize(&fb);

    /* Test: enumerate all 64 assignments, measure similarity to formula */
    printf("%4s | %6s | %6s | %s\n", "x", "hex", "sim", "SAT?");
    printf("-----+--------+--------+------\n");

    double max_sat = -1, max_unsat = -1;
    int best_sat = -1;
    int total_sat = 0;

    for(int m = 0; m < 64; m++){
        int x[6];
        for(int i = 0; i < 6; i++) x[i] = (m >> i) & 1;

        /* Check SAT */
        int sat = 1;
        for(int c = 0; c < 3; c++){
            int ok = 0;
            for(int j = 0; j < 3; j++){
                int v = clauses[c][j], s = signs[c][j];
                if((s==1 && x[v]==1) || (s==-1 && x[v]==0)){ok=1; break;}
            }
            if(!ok){sat = 0; break;}
        }

        /* Encode assignment and compare */
        HDV a = encode_assignment(x, n);
        double s = hdv_sim(a, formula);

        if(sat){
            total_sat++;
            if(s > max_sat){max_sat = s; best_sat = m;}
        } else {
            if(s > max_unsat) max_unsat = s;
        }
    }

    printf("\nStatistics:\n");
    printf("  Total SAT assignments: %d / 64\n", total_sat);
    printf("  Max similarity (SAT):   %.4f (best: 0x%02x)\n", max_sat, best_sat);
    printf("  Max similarity (UNSAT): %.4f\n", max_unsat);
    printf("  Gap: %.4f\n", max_sat - max_unsat);

    if(max_sat > max_unsat){
        printf("  ✓ SAT assignments are more similar to formula\n");
    } else {
        printf("  ✗ HDC cannot distinguish SAT from UNSAT\n");
    }

    /* Larger test: random 3-SAT at different sizes */
    printf("\n\nRandom 3-SAT test:\n");
    printf("%4s | %6s | %6s | gap | can_distinguish?\n", "n", "sat_max", "uns_max");
    printf("-----+--------+--------+--------+----\n");

    for(int nn = 5; nn <= 12; nn++){
        if(nn > MAX_VARS) break;

        rng_seed(1000 + nn);
        double ratio = 4.0;
        int m_c = (int)(ratio * nn);

        int cls[100][3], sgn[100][3];
        for(int c = 0; c < m_c; c++){
            cls[c][0] = rng_next() % nn;
            do{cls[c][1] = rng_next() % nn;}while(cls[c][1]==cls[c][0]);
            do{cls[c][2] = rng_next() % nn;}while(cls[c][2]==cls[c][0]||cls[c][2]==cls[c][1]);
            for(int j=0;j<3;j++) sgn[c][j] = (rng_next()&1) ? 1 : -1;
        }

        /* Build formula HDV */
        Bundle fb2; bundle_init(&fb2);
        for(int c = 0; c < m_c; c++){
            HDV ch = encode_clause_sat_set(cls[c], sgn[c], nn);
            bundle_add(&fb2, ch);
        }
        HDV form = bundle_finalize(&fb2);

        /* Enumerate */
        double msat = -1, muns = -1;
        int n_sat = 0;
        long long total = 1LL << nn;
        for(long long m2 = 0; m2 < total; m2++){
            int x[20];
            for(int i = 0; i < nn; i++) x[i] = (m2 >> i) & 1;
            int sat = 1;
            for(int c = 0; c < m_c; c++){
                int ok = 0;
                for(int j=0;j<3;j++){
                    int v=cls[c][j], s=sgn[c][j];
                    if((s==1&&x[v]==1)||(s==-1&&x[v]==0)){ok=1;break;}
                }
                if(!ok){sat=0;break;}
            }
            HDV a = encode_assignment(x, nn);
            double s = hdv_sim(a, form);
            if(sat){n_sat++; if(s>msat)msat=s;}
            else{if(s>muns)muns=s;}
        }

        printf("%4d | %6.4f | %6.4f | %+.4f | %s (%d sol)\n",
               nn, msat, muns, msat-muns,
               msat>muns ? "YES":"NO", n_sat);
    }

    return 0;
}
