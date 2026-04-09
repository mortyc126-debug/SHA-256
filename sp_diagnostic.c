/*
 * SP DIAGNOSTIC: Where does it fail? Are instances even SAT?
 * ===========================================================
 *
 * At α=4.267 (threshold), ~50% of instances are UNSAT.
 * Our "solve rate" includes UNSAT instances → ceiling ~50%!
 *
 * This diagnostic:
 * 1. For each instance: run heavy WalkSAT to determine likely SAT/UNSAT
 * 2. Run SP and track: convergence? trivialization? n_vars fixed by SP?
 * 3. Report solve rate ONLY for likely-SAT instances
 *
 * Compile: gcc -O3 -march=native -o sp_diag sp_diagnostic.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

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
static double W_plus[MAX_N], W_minus[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void) {
    unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];
    unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;
    s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);
    rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;
}
static void rng_seed(unsigned long long s){
    rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;
    rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;
    for(int i=0;i<20;i++)rng_next();
}
static double rng_double(void){return(rng_next()>>11)*(1.0/9007199254740992.0);}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n; n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
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

/* Pure WalkSAT to test satisfiability */
static int pure_walksat(int n, int m, int max_flips, unsigned long long seed) {
    rng_seed(seed);
    int a[MAX_N];
    for(int v=0;v<n;v++) a[v]=rng_next()&1;
    int sc[MAX_CLAUSES];
    for(int ci=0;ci<m;ci++){sc[ci]=0;for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&a[v]==1)||(s==-1&&a[v]==0))sc[ci]++;}}
    int ul[MAX_CLAUSES],up[MAX_CLAUSES],nu=0;
    memset(up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++) if(sc[ci]==0){up[ci]=nu;ul[nu++]=ci;}

    for(int f=0;f<max_flips&&nu>0;f++){
        int ci=ul[rng_next()%nu];
        int bv=cl_var[ci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&a[v]==1)||(os==-1&&a[v]==0))&&sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<57)?cl_var[ci][rng_next()%3]:bv);
        int old=a[fv],nw=1-old;a[fv]=nw;
        for(int d=0;d<vdeg[fv];d++){int oci=vlist[fv][d],opos=vpos[fv][d];
            int os=cl_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){sc[oci]--;if(sc[oci]==0){up[oci]=nu;ul[nu++]=oci;}}
            else if(!was&&now){sc[oci]++;if(sc[oci]==1){int p=up[oci];
                if(p>=0&&p<nu){int l=ul[nu-1];ul[p]=l;up[l]=p;up[oci]=-1;nu--;}}}}}
    return nu;
}

/* Try hard to determine if instance is SAT */
static int is_likely_sat(int n, int m) {
    for(int trial=0; trial<20; trial++) {
        if(pure_walksat(n, m, n*10000, 42+trial*13337) == 0)
            return 1;
    }
    return 0;
}

/* 3-state SP edge */
static double sp_edge(int ci, int pos_i){
    double product=1.0;
    for(int pj=0;pj<3;pj++){
        if(pj==pos_i)continue;
        int j=cl_var[ci][pj];
        if(var_fixed[j]>=0){
            int sj=cl_sign[ci][pj];
            if((sj==1&&var_fixed[j]==1)||(sj==-1&&var_fixed[j]==0)) return 0.0;
            continue;
        }
        int sja=cl_sign[ci][pj];
        double ps=1.0,pu=1.0;
        for(int d=0;d<vdeg[j];d++){
            int bi=vlist[j][d],bp=vpos[j][d];
            if(bi==ci||!cl_active[bi])continue;
            int bsat=0;
            for(int k=0;k<3;k++){int vk=cl_var[bi][k];
                if(var_fixed[vk]>=0){int sk=cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){bsat=1;break;}}}
            if(bsat)continue;
            double eb=eta[bi][bp];
            if(cl_sign[bi][bp]==sja) ps*=(1.0-eb); else pu*=(1.0-eb);
        }
        double Pu=(1.0-pu)*ps, Ps=(1.0-ps)*pu, P0=pu*ps;
        double den=Pu+Ps+P0;
        product*=(den>1e-15)?(Pu/den):0.0;
    }
    return product;
}

/* SP sweep */
static double sp_sweep(double rho){
    double mc=0;
    for(int ci=0;ci<n_clauses;ci++){
        if(!cl_active[ci])continue;
        for(int p=0;p<3;p++){
            if(var_fixed[cl_var[ci][p]]>=0)continue;
            double nv=sp_edge(ci,p);
            double ov=eta[ci][p];
            double up=rho*ov+(1.0-rho)*nv;
            double ch=fabs(up-ov);
            if(ch>mc)mc=ch;
            eta[ci][p]=up;
        }
    }
    return mc;
}

static int unit_prop(void){
    int changed=1;
    while(changed){changed=0;
        for(int ci=0;ci<n_clauses;ci++){
            if(!cl_active[ci])continue;
            int sat=0,fc=0,fv=-1,fs=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}
                else{fc++;fv=v;fs=s;}}
            if(sat){cl_active[ci]=0;continue;}
            if(fc==0)return 1;
            if(fc==1){var_fixed[fv]=(fs==1)?1:0;changed=1;}}}
    return 0;
}

int main(void) {
    printf("═══════════════════════════════════════════\n");
    printf("SP DIAGNOSTIC: SAT/UNSAT + SP behavior\n");
    printf("═══════════════════════════════════════════\n\n");

    int test_n[] = {100, 200, 300, 500, 1000};

    for(int ti=0; ti<5; ti++) {
        int nn = test_n[ti];
        int ni = (nn<=200) ? 20 : (nn<=500 ? 10 : 5);

        int n_sat=0, n_unsat=0, sp_solved=0, sp_solved_sat_only=0;

        printf("n=%d:\n", nn);

        for(int seed=0; seed < ni; seed++) {
            generate(nn, 4.267, 11000000ULL + seed);
            int n=nn, m=n_clauses;

            /* 1. Is it SAT? */
            int sat = is_likely_sat(n, m);
            if(sat) n_sat++; else n_unsat++;

            /* 2. Run SP with diagnostics */
            for(int ci=0;ci<m;ci++) cl_active[ci]=1;
            memset(var_fixed,-1,sizeof(int)*n);
            if(unit_prop()) {
                printf("  seed=%d: %s, UP contradiction\n", seed, sat?"SAT":"unsat?");
                continue;
            }

            rng_seed(42ULL);
            for(int ci=0;ci<m;ci++) for(int j=0;j<3;j++) eta[ci][j]=rng_double();

            /* Run SP */
            int sp_conv=0, sp_iters=0;
            double final_ch=99;
            for(int iter=0; iter<200; iter++) {
                double ch = sp_sweep(0.1);
                sp_iters = iter+1;
                final_ch = ch;
                if(ch < 1e-4) { sp_conv=1; break; }
            }

            /* Check eta stats */
            double max_eta=0, sum_eta=0; int cnt=0;
            int n_biased=0;
            for(int ci=0;ci<m;ci++){
                if(!cl_active[ci])continue;
                for(int j=0;j<3;j++){
                    if(var_fixed[cl_var[ci][j]]>=0)continue;
                    if(eta[ci][j]>max_eta)max_eta=eta[ci][j];
                    sum_eta+=eta[ci][j]; cnt++;
                    if(eta[ci][j]>0.01)n_biased++;
                }}

            /* Compute bias */
            for(int i=0;i<n;i++){
                W_plus[i]=W_minus[i]=0;
                if(var_fixed[i]>=0)continue;
                double pp=1.0,pm=1.0;
                for(int d=0;d<vdeg[i];d++){
                    int ci=vlist[i][d],p=vpos[i][d];
                    if(!cl_active[ci])continue;
                    int ssat=0;
                    for(int k=0;k<3;k++){int vk=cl_var[ci][k];
                        if(vk!=i&&var_fixed[vk]>=0){int sk=cl_sign[ci][k];
                            if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){ssat=1;break;}}}
                    if(ssat)continue;
                    double e=eta[ci][p];
                    if(cl_sign[ci][p]==1) pp*=(1.0-e); else pm*=(1.0-e);
                }
                double pip=(1.0-pp)*pm, pim=(1.0-pm)*pp, pi0=pp*pm;
                double tot=pip+pim+pi0;
                if(tot>1e-15){W_plus[i]=pip/tot;W_minus[i]=pim/tot;}
            }

            /* Count strongly biased vars */
            int n_strong=0, nf=0;
            for(int v=0;v<n;v++){
                if(var_fixed[v]>=0){nf++;continue;}
                if(fabs(W_plus[v]-W_minus[v])>0.5) n_strong++;
            }

            int trivial = (max_eta < 0.01);

            printf("  seed=%2d: %s | conv=%s(%3d iters, Δ=%.1e) | max_η=%.3f avg=%.4f | biased=%d/%d strong=%d | %s\n",
                seed, sat?"SAT":"UNS",
                sp_conv?"Y":"N", sp_iters, final_ch,
                max_eta, cnt>0?sum_eta/cnt:0, n_biased, cnt, n_strong,
                trivial?"TRIVIAL":"nontrivial");
        }

        printf("  Summary: %d SAT, %d likely UNSAT out of %d\n\n",
               n_sat, n_unsat, ni);
    }

    return 0;
}
