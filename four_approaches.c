/*
 * 4 APPROACHES to improve SP decimation at threshold
 * ====================================================
 *
 * All share the same SP core + probSAT finish.
 * Differ in HOW they use SP information:
 *
 * A. BACKTRACKING: fix var, check if SP breaks → undo if so
 * B. CAUTIOUS: only fix vars with bias > 0.9 (frozen core only)
 * C. REINFORCED: soft field instead of hard decimation
 * D. ADAPTIVE cb: tune probSAT exponent for post-SP sub-formula
 *
 * Compile: gcc -O3 -march=native -o four_approaches four_approaches.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       10000
#define MAX_CLAUSES 50000
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
    for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
}

/* ═══ SP CORE (shared) ═══ */
static inline double sp_edge(int ci,int pi){
    double product=1.0;
    for(int pj=0;pj<3;pj++){
        if(pj==pi)continue;
        int j=cl_var[ci][pj];
        if(var_fixed[j]>=0){int sj=cl_sign[ci][pj];
            if((sj==1&&var_fixed[j]==1)||(sj==-1&&var_fixed[j]==0))return 0.0;continue;}
        int sja=cl_sign[ci][pj];double ps=1.0,pu=1.0;
        for(int d=0;d<vdeg[j];d++){
            int bi=vlist[j][d],bp=vpos[j][d];
            if(bi==ci||!cl_active[bi])continue;
            int bsat=0;for(int k=0;k<3;k++){int vk=cl_var[bi][k];
                if(var_fixed[vk]>=0){int sk=cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){bsat=1;break;}}}
            if(bsat)continue;
            double eb=eta[bi][bp];
            if(cl_sign[bi][bp]==sja)ps*=(1.0-eb);else pu*=(1.0-eb);}
        double Pu=(1.0-pu)*ps,Ps=(1.0-ps)*pu,P0=pu*ps;
        double den=Pu+Ps+P0;
        product*=(den>1e-15)?(Pu/den):0.0;}
    return product;}

static double sp_sweep(double rho){
    double mc=0;
    for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;
        for(int p=0;p<3;p++){if(var_fixed[cl_var[ci][p]]>=0)continue;
            double nv=sp_edge(ci,p),ov=eta[ci][p];
            double up=rho*ov+(1.0-rho)*nv;
            double ch=fabs(up-ov);if(ch>mc)mc=ch;eta[ci][p]=up;}}
    return mc;}

static int sp_converge(void){
    for(int iter=0;iter<200;iter++){double ch=sp_sweep(0.1);if(ch<1e-4)return 1;}
    for(int iter=0;iter<100;iter++){double ch=sp_sweep(0.3);if(ch<1e-4)return 1;}
    return 0;}

static void compute_bias(void){
    for(int i=0;i<n_vars;i++){
        W_plus[i]=W_minus[i]=0;if(var_fixed[i]>=0)continue;
        double pp=1.0,pm=1.0;
        for(int d=0;d<vdeg[i];d++){
            int ci=vlist[i][d],p=vpos[i][d];
            if(!cl_active[ci])continue;
            int sat=0;for(int k=0;k<3;k++){int vk=cl_var[ci][k];
                if(vk!=i&&var_fixed[vk]>=0){int sk=cl_sign[ci][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){sat=1;break;}}}
            if(sat)continue;double e=eta[ci][p];
            if(cl_sign[ci][p]==1)pp*=(1.0-e);else pm*=(1.0-e);}
        double pip=(1.0-pp)*pm,pim=(1.0-pm)*pp,pi0=pp*pm,tot=pip+pim+pi0;
        if(tot>1e-15){W_plus[i]=pip/tot;W_minus[i]=pim/tot;}}}

static double sp_max_eta(void){
    double mx=0;
    for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;
        for(int j=0;j<3;j++){if(var_fixed[cl_var[ci][j]]>=0)continue;
            if(eta[ci][j]>mx)mx=eta[ci][j];}}return mx;}

static int unit_prop(void){
    int changed=1;while(changed){changed=0;
        for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;
            int sat=0,fc=0,fv=-1,fs=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}
                else{fc++;fv=v;fs=s;}}
            if(sat){cl_active[ci]=0;continue;}
            if(fc==0)return 1;
            if(fc==1){var_fixed[fv]=(fs==1)?1:0;changed=1;}}}return 0;}

static void fix_var(int v,int val){
    var_fixed[v]=val;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
        if(!cl_active[ci])continue;int s=cl_sign[ci][p];
        if((s==1&&val==1)||(s==-1&&val==0))cl_active[ci]=0;}}

/* ═══ probSAT FINISH (shared) ═══ */
static int ps_a[MAX_N],ps_sc[MAX_CLAUSES],ps_ul[MAX_CLAUSES],ps_up[MAX_CLAUSES],ps_nu;

static void ps_init(int n,int m){
    for(int v=0;v<n;v++)ps_a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    memset(ps_sc,0,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
    ps_nu=0;memset(ps_up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(ps_sc[ci]==0){ps_up[ci]=ps_nu;ps_ul[ps_nu++]=ci;}}

static inline void ps_flip(int fv,int m){
    int old=ps_a[fv],nw=1-old;ps_a[fv]=nw;
    for(int d=0;d<vdeg[fv];d++){int oci=vlist[fv][d],opos=vpos[fv][d];
        int os=cl_sign[oci][opos];
        int was=((os==1&&old==1)||(os==-1&&old==0));
        int now=((os==1&&nw==1)||(os==-1&&nw==0));
        if(was&&!now){ps_sc[oci]--;if(ps_sc[oci]==0){ps_up[oci]=ps_nu;ps_ul[ps_nu++]=oci;}}
        else if(!was&&now){ps_sc[oci]++;if(ps_sc[oci]==1){int p2=ps_up[oci];
            if(p2>=0&&p2<ps_nu){int l=ps_ul[ps_nu-1];ps_ul[p2]=l;ps_up[l]=p2;ps_up[oci]=-1;ps_nu--;}}}}}

static int probsat(int n,int m,int max_flips,double cb){
    double pt[64];for(int b=0;b<64;b++)pt[b]=pow(1.0+b,-cb);
    ps_init(n,m);
    for(int f=0;f<max_flips&&ps_nu>0;f++){
        int ci=ps_ul[rng_next()%ps_nu];
        double probs[3];double sum=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
            probs[j]=(br<64)?pt[br]:pow(1.0+br,-cb);sum+=probs[j];}
        double r=rng_double()*sum;int fv;
        if(r<probs[0])fv=cl_var[ci][0];else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
        else fv=cl_var[ci][2];ps_flip(fv,m);}
    for(int v=0;v<n;v++)var_fixed[v]=ps_a[v];return m-ps_nu;}

static int probsat_multi(int n,int m,int flips,double cb,int attempts){
    for(int a=0;a<attempts;a++){
        rng_seed(a*12345ULL+n*77ULL);
        if(probsat(n,m,flips,cb)==m)return m;}
    return 0;}

/* ═══ STATE SAVE/RESTORE ═══ */
static int sv_active[MAX_CLAUSES],sv_fixed[MAX_N];
static double sv_eta[MAX_CLAUSES][MAX_K];

static void save_full(int n,int m){
    memcpy(sv_active,cl_active,sizeof(int)*m);
    memcpy(sv_fixed,var_fixed,sizeof(int)*n);
    memcpy(sv_eta,eta,sizeof(double)*m*MAX_K);}
static void restore_full(int n,int m){
    memcpy(cl_active,sv_active,sizeof(int)*m);
    memcpy(var_fixed,sv_fixed,sizeof(int)*n);
    memcpy(eta,sv_eta,sizeof(double)*m*MAX_K);}

/* ════════════════════════════════════════════════════════════
 * A. BASELINE: standard SP decimation (2% batch) + probSAT
 * ════════════════════════════════════════════════════════════ */
static int solve_baseline(int n){
    int m=n_clauses;
    if(unit_prop())return 0;
    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

    int nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
    while(nf<n){
        if(!sp_converge())break;
        if(sp_max_eta()<0.01)break;
        compute_bias();
        int nfree=n-nf,nfix=nfree/50;if(nfix<1)nfix=1;if(nfix>50)nfix=50;
        for(int f=0;f<nfix;f++){
            double bb=-1;int bv=-1,bval=0;
            for(int v=0;v<n;v++){if(var_fixed[v]>=0)continue;
                double b=fabs(W_plus[v]-W_minus[v]);if(b>bb){bb=b;bv=v;bval=(W_plus[v]>W_minus[v])?1:0;}}
            if(bv<0||bb<0.001)break;fix_var(bv,bval);nf++;}
        if(unit_prop())break;nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;}
    return probsat_multi(n,m,n*10000,2.06,5);}

/* ════════════════════════════════════════════════════════════
 * B. BACKTRACKING: undo bad decimations
 * ════════════════════════════════════════════════════════════ */
static int solve_backtrack(int n){
    int m=n_clauses;
    if(unit_prop())return 0;
    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

    int nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
    while(nf<n){
        if(!sp_converge())break;
        if(sp_max_eta()<0.01)break;
        compute_bias();

        /* Find most biased */
        double bb=-1;int bv=-1,bval=0;
        for(int v=0;v<n;v++){if(var_fixed[v]>=0)continue;
            double b=fabs(W_plus[v]-W_minus[v]);if(b>bb){bb=b;bv=v;bval=(W_plus[v]>W_minus[v])?1:0;}}
        if(bv<0||bb<0.001)break;

        /* Save state BEFORE fixing */
        save_full(n,m);

        /* Try preferred value */
        fix_var(bv,bval);nf++;
        int contradiction=unit_prop();

        if(contradiction){
            /* Undo, try opposite */
            restore_full(n,m);nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
            fix_var(bv,1-bval);nf++;
            if(unit_prop()){
                /* Both values fail → restore and skip this var */
                restore_full(n,m);nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
                break; /* give up SP, go to probSAT */
            }
        } else {
            /* Check if SP still converges after this fix */
            int conv2=0;
            for(int iter=0;iter<50;iter++){double ch=sp_sweep(0.1);if(ch<1e-4){conv2=1;break;}}
            if(!conv2){
                /* SP destabilized → try opposite */
                restore_full(n,m);nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
                fix_var(bv,1-bval);nf++;
                if(unit_prop()){restore_full(n,m);nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;break;}
            }
        }
        nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
    }
    return probsat_multi(n,m,n*10000,2.06,5);}

/* ════════════════════════════════════════════════════════════
 * C. CAUTIOUS: only fix frozen core (bias > 0.9)
 *    then switch to probSAT for the rest
 * ════════════════════════════════════════════════════════════ */
static int solve_cautious(int n){
    int m=n_clauses;
    if(unit_prop())return 0;
    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

    int nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
    while(nf<n){
        if(!sp_converge())break;
        if(sp_max_eta()<0.01)break;
        compute_bias();

        /* Only fix vars with VERY high bias (frozen core) */
        int fixed_any=0;
        for(int v=0;v<n;v++){
            if(var_fixed[v]>=0)continue;
            double b=fabs(W_plus[v]-W_minus[v]);
            if(b>0.9){ /* Very confident — frozen variable */
                int val=(W_plus[v]>W_minus[v])?1:0;
                fix_var(v,val);nf++;fixed_any=1;
            }
        }
        if(!fixed_any)break; /* No more frozen vars → probSAT */
        if(unit_prop())break;
        nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
    }
    return probsat_multi(n,m,n*10000,2.06,5);}

/* ════════════════════════════════════════════════════════════
 * D. REINFORCED: soft field instead of hard decimation
 * ════════════════════════════════════════════════════════════ */
static double reinf[MAX_N];

static int solve_reinforced(int n){
    int m=n_clauses;
    if(unit_prop())return 0;
    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();
    memset(reinf,0,sizeof(double)*n);

    /* Phase 1: converge SP */
    if(!sp_converge())goto finish;

    /* Phase 2: reinforcement loop */
    for(int rnd=0;rnd<200;rnd++){
        compute_bias();

        /* Incorporate reinforcement into bias */
        int n_polar=0;
        for(int i=0;i<n;i++){
            if(var_fixed[i]>=0){n_polar++;continue;}
            /* Effective bias = SP bias + reinforcement */
            double wp_eff=W_plus[i]*exp(reinf[i]);
            double wm_eff=W_minus[i]*exp(-reinf[i]);
            double tot=wp_eff+wm_eff;
            if(tot>1e-15){wp_eff/=tot;wm_eff/=tot;}
            if(fabs(wp_eff-wm_eff)>0.99)n_polar++;
            /* Update reinforcement */
            reinf[i]+=0.05*(W_plus[i]-W_minus[i]);
            if(reinf[i]>20)reinf[i]=20;if(reinf[i]<-20)reinf[i]=-20;
        }

        if(n_polar>=(int)(n*0.95))break;

        /* Re-converge SP (few sweeps) */
        for(int iter=0;iter<20;iter++){double ch=sp_sweep(0.15);if(ch<1e-4)break;}
    }

    /* Extract assignment from reinforcement */
    for(int v=0;v<n;v++){
        if(var_fixed[v]>=0)continue;
        var_fixed[v]=(reinf[v]>=0)?1:0;
    }

finish:
    return probsat_multi(n,m,n*10000,2.06,5);}

/* ════════════════════════════════════════════════════════════
 * E. ADAPTIVE cb: sweep cb for post-SP sub-formula
 * ════════════════════════════════════════════════════════════ */
static int solve_adaptive_cb(int n){
    int m=n_clauses;
    if(unit_prop())return 0;
    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

    int nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
    while(nf<n){
        if(!sp_converge())break;
        if(sp_max_eta()<0.01)break;
        compute_bias();
        int nfree=n-nf,nfix=nfree/50;if(nfix<1)nfix=1;if(nfix>50)nfix=50;
        for(int f=0;f<nfix;f++){
            double bb=-1;int bv=-1,bval=0;
            for(int v=0;v<n;v++){if(var_fixed[v]>=0)continue;
                double b=fabs(W_plus[v]-W_minus[v]);if(b>bb){bb=b;bv=v;bval=(W_plus[v]>W_minus[v])?1:0;}}
            if(bv<0||bb<0.001)break;fix_var(bv,bval);nf++;}
        if(unit_prop())break;nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;}

    /* Try multiple cb values */
    double cbs[]={1.5, 2.06, 2.5, 3.0};
    int flips=n*10000;
    for(int ci2=0;ci2<4;ci2++){
        for(int a=0;a<3;a++){
            rng_seed(a*12345ULL+ci2*77777ULL);
            if(probsat(n,m,flips,cbs[ci2])==m)return m;
        }
    }
    return 0;}

/* ════════════════════════════════════════════════════════════
 * BENCHMARK
 * ════════════════════════════════════════════════════════════ */
typedef int(*solver_fn)(int);

static void benchmark(const char*name, solver_fn solve, int nn, double ratio,
                       int ni, int *out_solved, int *out_total, double *out_ms){
    *out_solved=0;*out_total=0;*out_ms=0;
    for(int seed=0;seed<ni*3&&*out_total<ni;seed++){
        generate(nn,ratio,11000000ULL+seed);
        clock_t t0=clock();
        int sat=solve(nn);
        clock_t t1=clock();
        double ms=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
        *out_ms+=ms;(*out_total)++;
        if(sat==n_clauses)(*out_solved)++;
    }
    *out_ms/=(*out_total>0?*out_total:1);
}

int main(void){
    printf("══════════════════════════════════════════════════════\n");
    printf("4 APPROACHES to improve SP decimation at threshold\n");
    printf("══════════════════════════════════════════════════════\n\n");

    const char *names[]={"A.Baseline","B.Backtrack","C.Cautious","D.Reinforced","E.AdaptCb"};
    solver_fn solvers[]={solve_baseline,solve_backtrack,solve_cautious,solve_reinforced,solve_adaptive_cb};

    int test_n[]={200, 500, 1000};

    printf("α=4.267 (threshold):\n");
    printf("%-14s","n");
    for(int a=0;a<5;a++)printf("| %-14s",names[a]);
    printf("\n");
    for(int i=0;i<14+5*16;i++)printf("─");printf("\n");

    for(int ti=0;ti<3;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?20:(nn<=500?10:5);
        printf("%-14d",nn);

        for(int a=0;a<5;a++){
            int solved,total;double ms;
            benchmark(names[a],solvers[a],nn,4.267,ni,&solved,&total,&ms);
            printf("| %2d/%2d %3.0f%% %4.0fs ",solved,total,100.0*solved/total,ms/1000);
            fflush(stdout);
        }
        printf("\n");fflush(stdout);
    }

    printf("\n");

    /* Also test at α=4.0 for sanity */
    printf("α=4.0 (below threshold):\n");
    printf("%-14s","n");
    for(int a=0;a<5;a++)printf("| %-14s",names[a]);
    printf("\n");
    for(int i=0;i<14+5*16;i++)printf("─");printf("\n");

    int test_n2[]={1000, 2000};
    for(int ti=0;ti<2;ti++){
        int nn=test_n2[ti];
        int ni=5;
        printf("%-14d",nn);
        for(int a=0;a<5;a++){
            int solved,total;double ms;
            benchmark(names[a],solvers[a],nn,4.0,ni,&solved,&total,&ms);
            printf("| %2d/%2d %3.0f%% %4.0fs ",solved,total,100.0*solved/total,ms/1000);
            fflush(stdout);
        }
        printf("\n");fflush(stdout);
    }

    printf("\n═══ Which approach is best at threshold? ═══\n");
    return 0;
}
