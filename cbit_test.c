/*
 * C-BIT TEST: Does matrix BP (d=2) improve over scalar BP?
 * ==========================================================
 *
 * THE experiment: if d=2 matrix messages improve SP/BP accuracy,
 * C-bits are real. If not, the theory is wrong.
 *
 * Method:
 * 1. Generate random 3-SAT, find solution with probSAT (ground truth)
 * 2. Run scalar BP (d=1): compute marginals, measure accuracy
 * 3. Run matrix BP (d=2): compute marginals, measure accuracy
 * 4. Compare: does d=2 give higher accuracy?
 *
 * Matrix BP:
 *   Messages are 2x2 matrices instead of scalars.
 *   M_{a->i}^s ∈ R^{2x2} for s ∈ {0,1}
 *   Update: M_{a->i}^s = Σ_{t,u satisfying} M_{j->a}^t × M_{k->a}^u
 *   Marginal: P(x_i=s) ∝ Tr(∏_a M_{a->i}^s)
 *
 * Compile: gcc -O3 -march=native -o cbit_test cbit_test.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       2000
#define MAX_CLAUSES 10000
#define MAX_K       3
#define MAX_DEGREE  100
#define D           2  /* matrix dimension */

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

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
static inline double rng_double(void){return(rng_next()>>11)*(1.0/9007199254740992.0);}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
    rng_seed(seed);memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
}

/* ═══════════════════════════════════════════
 * SCALAR BP (d=1) — baseline
 * ═══════════════════════════════════════════ */

/* BP messages: mu[ci][j][s] = message from clause ci to var cl_var[ci][j] for value s */
static double mu[MAX_CLAUSES][MAX_K][2];
/* Variable-to-clause: nu[ci][j][s] */
static double nu[MAX_CLAUSES][MAX_K][2];

static void scalar_bp_init(void){
    for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<MAX_K;j++)
            for(int s=0;s<2;s++)
                mu[ci][j][s]=0.5;
}

static double scalar_bp_sweep(double damp){
    int n=n_vars,m=n_clauses;
    double maxch=0;

    /* Compute nu (variable-to-clause) from mu (clause-to-variable) */
    for(int ci=0;ci<m;ci++){
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j];
            for(int s=0;s<2;s++){
                double prod=1.0;
                for(int d2=0;d2<vdeg[v];d2++){
                    int oci=vlist[v][d2],opos=vpos[v][d2];
                    if(oci==ci)continue;
                    prod*=mu[oci][opos][s];
                }
                nu[ci][j][s]=prod;
            }
            /* Normalize */
            double tot=nu[ci][j][0]+nu[ci][j][1];
            if(tot>1e-15){nu[ci][j][0]/=tot;nu[ci][j][1]/=tot;}
            else{nu[ci][j][0]=nu[ci][j][1]=0.5;}
        }
    }

    /* Compute mu (clause-to-variable) from nu */
    for(int ci=0;ci<m;ci++){
        int v0=cl_var[ci][0],s0=cl_sign[ci][0];
        int v1=cl_var[ci][1],s1=cl_sign[ci][1];
        int v2=cl_var[ci][2],s2=cl_sign[ci][2];

        for(int j=0;j<3;j++){
            int vi=cl_var[ci][j],si=cl_sign[ci][j];
            double new_mu[2];

            for(int xs=0;xs<2;xs++){
                /* Sum over other vars' assignments that satisfy clause */
                /* given x_i = xs */
                double sum=0;
                int j1=(j+1)%3, j2=(j+2)%3;
                for(int xt=0;xt<2;xt++){
                    for(int xu=0;xu<2;xu++){
                        /* Check if clause satisfied */
                        int li=(si==1)?xs:(1-xs);
                        int lt=(cl_sign[ci][j1]==1)?xt:(1-xt);
                        int lu=(cl_sign[ci][j2]==1)?xu:(1-xu);
                        if(li||lt||lu){
                            sum+=nu[ci][j1][xt]*nu[ci][j2][xu];
                        }
                    }
                }
                new_mu[xs]=sum;
            }

            /* Normalize */
            double tot=new_mu[0]+new_mu[1];
            if(tot>1e-15){new_mu[0]/=tot;new_mu[1]/=tot;}
            else{new_mu[0]=new_mu[1]=0.5;}

            /* Damp */
            for(int s=0;s<2;s++){
                double old=mu[ci][j][s];
                double upd=damp*old+(1-damp)*new_mu[s];
                double ch=fabs(upd-old);if(ch>maxch)maxch=ch;
                mu[ci][j][s]=upd;
            }
        }
    }
    return maxch;
}

static void scalar_bp_marginals(double *p1){
    int n=n_vars;
    for(int v=0;v<n;v++){
        double prod[2]={1.0,1.0};
        for(int d2=0;d2<vdeg[v];d2++){
            int ci=vlist[v][d2],pos=vpos[v][d2];
            prod[0]*=mu[ci][pos][0];
            prod[1]*=mu[ci][pos][1];
        }
        double tot=prod[0]+prod[1];
        p1[v]=(tot>1e-15)?prod[1]/tot:0.5;
    }
}

/* ═══════════════════════════════════════════
 * MATRIX BP (d=2) — the C-bit test
 * ═══════════════════════════════════════════
 *
 * Messages are 2x2 matrices.
 * M[ci][j][s] = 2x2 matrix, for clause ci, position j, value s
 */

typedef struct { double m[D][D]; } Mat;

static Mat mat_zero(void){ Mat r; memset(&r,0,sizeof(Mat)); return r; }
static Mat mat_id(void){ Mat r=mat_zero(); for(int i=0;i<D;i++)r.m[i][i]=1.0; return r; }
static Mat mat_rand(void){ Mat r; for(int i=0;i<D;i++)for(int j=0;j<D;j++)r.m[i][j]=rng_double()*0.5+0.25; return r; }
static Mat mat_add(Mat a, Mat b){ Mat r; for(int i=0;i<D;i++)for(int j=0;j<D;j++)r.m[i][j]=a.m[i][j]+b.m[i][j]; return r; }
static Mat mat_mul(Mat a, Mat b){ Mat r=mat_zero(); for(int i=0;i<D;i++)for(int j=0;j<D;j++)for(int k=0;k<D;k++)r.m[i][j]+=a.m[i][k]*b.m[k][j]; return r; }
static Mat mat_scale(Mat a, double s){ Mat r; for(int i=0;i<D;i++)for(int j=0;j<D;j++)r.m[i][j]=a.m[i][j]*s; return r; }
static double mat_trace(Mat a){ double t=0; for(int i=0;i<D;i++)t+=a.m[i][i]; return t; }
static double mat_norm(Mat a){ double s=0; for(int i=0;i<D;i++)for(int j=0;j<D;j++)s+=a.m[i][j]*a.m[i][j]; return sqrt(s); }
static Mat mat_damp(Mat old, Mat new2, double d){ Mat r; for(int i=0;i<D;i++)for(int j=0;j<D;j++)r.m[i][j]=d*old.m[i][j]+(1-d)*new2.m[i][j]; return r; }

/* Matrix messages */
static Mat M_mu[MAX_CLAUSES][MAX_K][2];  /* clause→var */
static Mat M_nu[MAX_CLAUSES][MAX_K][2];  /* var→clause */

static void matrix_bp_init(void){
    rng_seed(12345);
    for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<MAX_K;j++)
            for(int s=0;s<2;s++)
                M_mu[ci][j][s]=mat_rand();
}

static double matrix_bp_sweep(double damp){
    int n=n_vars,m=n_clauses;
    double maxch=0;

    /* Compute M_nu from M_mu (variable-to-clause) */
    for(int ci=0;ci<m;ci++){
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j];
            for(int s=0;s<2;s++){
                Mat prod=mat_id();
                for(int d2=0;d2<vdeg[v];d2++){
                    int oci=vlist[v][d2],opos=vpos[v][d2];
                    if(oci==ci)continue;
                    prod=mat_mul(prod, M_mu[oci][opos][s]);
                }
                M_nu[ci][j][s]=prod;
            }
            /* Normalize by trace */
            double tr0=mat_trace(M_nu[ci][j][0]);
            double tr1=mat_trace(M_nu[ci][j][1]);
            double tot=tr0+tr1;
            if(tot>1e-15){
                M_nu[ci][j][0]=mat_scale(M_nu[ci][j][0],1.0/tot);
                M_nu[ci][j][1]=mat_scale(M_nu[ci][j][1],1.0/tot);
            }
        }
    }

    /* Compute M_mu from M_nu (clause-to-variable) */
    for(int ci=0;ci<m;ci++){
        for(int j=0;j<3;j++){
            int j1=(j+1)%3, j2=(j+2)%3;
            Mat new_mu[2];

            for(int xs=0;xs<2;xs++){
                Mat sum=mat_zero();
                for(int xt=0;xt<2;xt++){
                    for(int xu=0;xu<2;xu++){
                        int li=(cl_sign[ci][j]==1)?xs:(1-xs);
                        int lt=(cl_sign[ci][j1]==1)?xt:(1-xt);
                        int lu=(cl_sign[ci][j2]==1)?xu:(1-xu);
                        if(li||lt||lu){
                            /* KEY: matrix MULTIPLICATION, not scalar */
                            Mat contrib=mat_mul(M_nu[ci][j1][xt], M_nu[ci][j2][xu]);
                            sum=mat_add(sum, contrib);
                        }
                    }
                }
                new_mu[xs]=sum;
            }

            /* Normalize */
            double tr0=mat_trace(new_mu[0]);
            double tr1=mat_trace(new_mu[1]);
            double tot=tr0+tr1;
            if(tot>1e-15){
                new_mu[0]=mat_scale(new_mu[0],1.0/tot);
                new_mu[1]=mat_scale(new_mu[1],1.0/tot);
            }

            /* Damp and measure change */
            for(int s=0;s<2;s++){
                Mat diff;
                for(int a=0;a<D;a++)for(int b=0;b<D;b++)
                    diff.m[a][b]=new_mu[s].m[a][b]-M_mu[ci][j][s].m[a][b];
                double ch=mat_norm(diff);
                if(ch>maxch)maxch=ch;
                M_mu[ci][j][s]=mat_damp(M_mu[ci][j][s], new_mu[s], damp);
            }
        }
    }
    return maxch;
}

static void matrix_bp_marginals(double *p1){
    int n=n_vars;
    for(int v=0;v<n;v++){
        Mat prod[2];
        prod[0]=mat_id(); prod[1]=mat_id();
        for(int d2=0;d2<vdeg[v];d2++){
            int ci=vlist[v][d2],pos=vpos[v][d2];
            prod[0]=mat_mul(prod[0], M_mu[ci][pos][0]);
            prod[1]=mat_mul(prod[1], M_mu[ci][pos][1]);
        }
        double tr0=mat_trace(prod[0]);
        double tr1=mat_trace(prod[1]);
        double tot=tr0+tr1;
        p1[v]=(tot>1e-15)?tr1/tot:0.5;
    }
}

/* ═══════════════════════════════════════════
 * probSAT to find ground truth
 * ═══════════════════════════════════════════ */
static int ps_a[MAX_N],ps_sc[MAX_CLAUSES],ps_ul[MAX_CLAUSES],ps_up2[MAX_CLAUSES],ps_nu;

static int find_solution(int n, int m, int *sol){
    for(int attempt=0;attempt<30;attempt++){
        rng_seed(attempt*31337ULL);
        for(int v=0;v<n;v++)ps_a[v]=rng_next()&1;
        memset(ps_sc,0,sizeof(int)*m);
        for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){
            int v=cl_var[ci][j],s=cl_sign[ci][j];
            if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
        ps_nu=0;memset(ps_up2,-1,sizeof(int)*m);
        for(int ci=0;ci<m;ci++)if(ps_sc[ci]==0){ps_up2[ci]=ps_nu;ps_ul[ps_nu++]=ci;}
        double pt[64];for(int b=0;b<64;b++)pt[b]=pow(1.0+b,-2.06);
        for(int f=0;f<n*20000&&ps_nu>0;f++){
            int ci=ps_ul[rng_next()%ps_nu];
            double probs[3];double sum=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
                for(int d2=0;d2<vdeg[v];d2++){int oci=vlist[v][d2],opos=vpos[v][d2];
                    int os=cl_sign[oci][opos];
                    if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
                probs[j]=(br<64)?pt[br]:0;sum+=probs[j];}
            double r=rng_double()*sum;int fv;
            if(r<probs[0])fv=cl_var[ci][0];else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
            else fv=cl_var[ci][2];
            int old=ps_a[fv],nw=1-old;ps_a[fv]=nw;
            for(int d2=0;d2<vdeg[fv];d2++){int oci=vlist[fv][d2],opos=vpos[fv][d2];
                int os=cl_sign[oci][opos];
                int was=((os==1&&old==1)||(os==-1&&old==0));
                int now=((os==1&&nw==1)||(os==-1&&nw==0));
                if(was&&!now){ps_sc[oci]--;if(ps_sc[oci]==0){ps_up2[oci]=ps_nu;ps_ul[ps_nu++]=oci;}}
                else if(!was&&now){ps_sc[oci]++;if(ps_sc[oci]==1){int p=ps_up2[oci];
                    if(p>=0&&p<ps_nu){int l=ps_ul[ps_nu-1];ps_ul[p]=l;ps_up2[l]=p;ps_up2[oci]=-1;ps_nu--;}}}}}
        if(ps_nu==0){memcpy(sol,ps_a,sizeof(int)*n);return 1;}
    }
    return 0;
}

/* ═══════════════════════════════════════════
 * MAIN: the definitive test
 * ═══════════════════════════════════════════ */
int main(void){
    printf("══════════════════════════════════════════════════\n");
    printf("C-BIT TEST: Does d=2 improve over d=1?\n");
    printf("══════════════════════════════════════════════════\n");
    printf("This is THE experiment.\n\n");

    int test_n[]={50, 100, 200, 500};
    double test_alpha[]={3.5, 4.0, 4.2};

    for(int ai=0;ai<3;ai++){
        double alpha=test_alpha[ai];
        printf("α=%.1f:\n",alpha);
        printf("  %4s | %7s %7s | %7s %7s | %7s\n",
               "n","d=1 acc","d=1 conv","d=2 acc","d=2 conv","Δ(acc)");
        printf("  -----+-----------------+-----------------+--------\n");

        for(int ti=0;ti<4;ti++){
            int nn=test_n[ti];
            int ni=(nn<=100)?10:5;

            double sum_acc1=0, sum_acc2=0;
            int n_conv1=0, n_conv2=0, count=0;

            for(int seed=0;seed<ni*3&&count<ni;seed++){
                generate(nn,alpha,11000000ULL+seed);
                int n=nn,m=n_clauses;

                /* Find ground truth */
                int sol[MAX_N];
                if(!find_solution(n,m,sol)) continue;

                /* ── Scalar BP (d=1) ── */
                scalar_bp_init();
                int conv1=0;
                for(int iter=0;iter<500;iter++){
                    double ch=scalar_bp_sweep(0.3);
                    if(ch<1e-6){conv1=1;break;}
                }
                double p1_scalar[MAX_N];
                scalar_bp_marginals(p1_scalar);

                int correct1=0;
                for(int v=0;v<n;v++){
                    int pred=(p1_scalar[v]>0.5)?1:0;
                    if(pred==sol[v])correct1++;
                }
                double acc1=100.0*correct1/n;
                if(conv1)n_conv1++;

                /* ── Matrix BP (d=2) ── */
                matrix_bp_init();
                int conv2=0;
                for(int iter=0;iter<500;iter++){
                    double ch=matrix_bp_sweep(0.3);
                    if(ch<1e-6){conv2=1;break;}
                }
                double p1_matrix[MAX_N];
                matrix_bp_marginals(p1_matrix);

                int correct2=0;
                for(int v=0;v<n;v++){
                    int pred=(p1_matrix[v]>0.5)?1:0;
                    if(pred==sol[v])correct2++;
                }
                double acc2=100.0*correct2/n;
                if(conv2)n_conv2++;

                sum_acc1+=acc1; sum_acc2+=acc2;
                count++;
            }

            if(count>0){
                double avg1=sum_acc1/count, avg2=sum_acc2/count;
                printf("  %4d | %5.1f%%  %3d/%d   | %5.1f%%  %3d/%d   | %+.1f%%\n",
                       nn, avg1, n_conv1, count, avg2, n_conv2, count, avg2-avg1);
            }
            fflush(stdout);
        }
        printf("\n");
    }

    printf("═══ VERDICT ═══\n");
    printf("If Δ(acc) > 0 consistently: C-bits are REAL.\n");
    printf("If Δ(acc) ≈ 0: theory is wrong, d=2 adds nothing.\n");

    return 0;
}
