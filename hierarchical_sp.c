/*
 * HIERARCHICAL SP: use full precision of marginals via threshold-based iterative decimation
 * ==========================================================================================
 *
 * Standard SP-decimation:
 *   Fix top-1% most biased → reconverge → fix top-1% → ... (100 rounds, O(n²))
 *
 * Our one-shot:
 *   Fix ALL biased variables at once → probSAT finish
 *
 * Hierarchical (this):
 *   Round 1: fix |P-0.5| > 0.40 → reconverge
 *   Round 2: fix |P-0.5| > 0.30 → reconverge
 *   Round 3: fix |P-0.5| > 0.20 → reconverge
 *   ...
 *   Final: probSAT on the core (genuinely free variables)
 *
 * Key: threshold-based (not count-based) uses the full precision of marginals.
 * As the formula simplifies, previously ambiguous marginals become clearer.
 *
 * Compile: gcc -O3 -march=native -o hier_sp hierarchical_sp.c -lm
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

/* ═══ 3-state SP ═══ */
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
    return product;
}

static double sp_sweep(double rho){
    double mc=0;
    for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;
        for(int p=0;p<3;p++){if(var_fixed[cl_var[ci][p]]>=0)continue;
            double nv=sp_edge(ci,p),ov=eta[ci][p];
            double up=rho*ov+(1.0-rho)*nv;
            double ch=fabs(up-ov);if(ch>mc)mc=ch;eta[ci][p]=up;}}
    return mc;
}

static int sp_converge(int warm){
    if(!warm){
        for(int ci=0;ci<n_clauses;ci++)
            for(int j=0;j<3;j++)
                eta[ci][j]=rng_double();
    }
    for(int iter=0;iter<200;iter++){double ch=sp_sweep(0.1);if(ch<1e-4)return 1;}
    for(int iter=0;iter<100;iter++){double ch=sp_sweep(0.3);if(ch<1e-4)return 1;}
    return 0;
}

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

static int unit_prop(void){
    int changed=1;while(changed){changed=0;
        for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;
            int sat=0,fc=0,fv=-1,fs=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}
                else{fc++;fv=v;fs=s;}}
            if(sat){cl_active[ci]=0;continue;}
            if(fc==0)return 1;
            if(fc==1){var_fixed[fv]=(fs==1)?1:0;changed=1;}}}
    return 0;
}

static void fix_var(int v,int val){
    var_fixed[v]=val;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
        if(!cl_active[ci])continue;int s=cl_sign[ci][p];
        if((s==1&&val==1)||(s==-1&&val==0))cl_active[ci]=0;}}

/* ═══ probSAT finish ═══ */
static int ps_a[MAX_N],ps_sc[MAX_CLAUSES],ps_ul[MAX_CLAUSES],ps_up[MAX_CLAUSES],ps_nu;

static int probsat(int n,int m,int max_flips,double cb){
    double pt[64];for(int b=0;b<64;b++)pt[b]=pow(1.0+b,-cb);
    for(int v=0;v<n;v++)ps_a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    memset(ps_sc,0,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
    ps_nu=0;memset(ps_up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(ps_sc[ci]==0){ps_up[ci]=ps_nu;ps_ul[ps_nu++]=ci;}
    for(int f=0;f<max_flips&&ps_nu>0;f++){
        int ci=ps_ul[rng_next()%ps_nu];
        double probs[3];double sum=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
            probs[j]=(br<64)?pt[br]:0;sum+=probs[j];}
        double r=rng_double()*sum;int fv;
        if(r<probs[0])fv=cl_var[ci][0];
        else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
        else fv=cl_var[ci][2];
        int old=ps_a[fv],nw=1-old;ps_a[fv]=nw;
        for(int d=0;d<vdeg[fv];d++){int oci=vlist[fv][d],opos=vpos[fv][d];
            int os=cl_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){ps_sc[oci]--;if(ps_sc[oci]==0){ps_up[oci]=ps_nu;ps_ul[ps_nu++]=oci;}}
            else if(!was&&now){ps_sc[oci]++;if(ps_sc[oci]==1){int p2=ps_up[oci];
                if(p2>=0&&p2<ps_nu){int l=ps_ul[ps_nu-1];ps_ul[p2]=l;ps_up[l]=p2;ps_up[oci]=-1;ps_nu--;}}}}}
    for(int v=0;v<n;v++)var_fixed[v]=ps_a[v];
    return m-ps_nu;
}

/* ═══ BASELINE: one-shot SP + probSAT ═══ */
static int solve_oneshot(int nn){
    int n=nn,m=n_clauses;
    if(unit_prop())return 0;
    rng_seed(42ULL+(unsigned long long)n*13);

    if(!sp_converge(0)) goto ps_only;

    compute_bias();

    /* Fix ALL variables with bias */
    for(int v=0;v<n;v++){
        if(var_fixed[v]>=0)continue;
        double b=fabs(W_plus[v]-W_minus[v]);
        if(b>0.001){
            fix_var(v,(W_plus[v]>W_minus[v])?1:0);
        }
    }
    unit_prop();

ps_only:
    ;
    int flips=n*10000;if(flips>50000000)flips=50000000;
    for(int a=0;a<5;a++){
        rng_seed(a*12345ULL+n*77ULL);
        if(probsat(n,m,flips,2.06)==m)return m;
    }
    return 0;
}

/* ═══ HIERARCHICAL: iterative threshold-based decimation ═══ */
static int solve_hierarchical(int nn){
    int n=nn,m=n_clauses;
    if(unit_prop())return 0;
    rng_seed(42ULL+(unsigned long long)n*13);

    /* Thresholds: start high, decrease */
    double thresholds[]={0.80, 0.60, 0.40, 0.25, 0.15, 0.08, 0.04, 0.02, 0.01};
    int n_thr=9;

    for(int ti=0;ti<n_thr;ti++){
        /* Converge SP (warm start if not first iteration) */
        if(!sp_converge(ti>0)) break;

        compute_bias();

        /* Fix all variables with bias > threshold */
        int n_fixed=0;
        for(int v=0;v<n;v++){
            if(var_fixed[v]>=0)continue;
            double b=fabs(W_plus[v]-W_minus[v]);
            if(b>thresholds[ti]){
                fix_var(v,(W_plus[v]>W_minus[v])?1:0);
                n_fixed++;
            }
        }

        if(n_fixed==0)continue; /* no progress at this threshold */

        if(unit_prop())break;

        /* Count remaining free variables */
        int n_free=0;
        for(int v=0;v<n;v++)if(var_fixed[v]<0)n_free++;

        if(n_free==0)break; /* all fixed */
    }

    /* probSAT on remaining */
    int flips=n*10000;if(flips>50000000)flips=50000000;
    for(int a=0;a<5;a++){
        rng_seed(a*12345ULL+n*77ULL);
        if(probsat(n,m,flips,2.06)==m)return m;
    }
    return 0;
}

/* ═══ HIERARCHICAL+: with per-iteration stats ═══ */
static int solve_hierarchical_verbose(int nn, int *n_iterations, int *n_after_sp){
    int n=nn,m=n_clauses;
    *n_iterations=0;
    *n_after_sp=0;

    if(unit_prop())return 0;
    rng_seed(42ULL+(unsigned long long)n*13);

    double thresholds[]={0.80, 0.60, 0.40, 0.25, 0.15, 0.08, 0.04, 0.02, 0.01};
    int n_thr=9;

    for(int ti=0;ti<n_thr;ti++){
        if(!sp_converge(ti>0)) break;
        compute_bias();

        int n_fixed=0;
        for(int v=0;v<n;v++){
            if(var_fixed[v]>=0)continue;
            double b=fabs(W_plus[v]-W_minus[v]);
            if(b>thresholds[ti]){
                fix_var(v,(W_plus[v]>W_minus[v])?1:0);
                n_fixed++;
            }
        }

        if(n_fixed==0)continue;
        (*n_iterations)++;

        if(unit_prop())break;

        int n_free=0;
        for(int v=0;v<n;v++)if(var_fixed[v]<0)n_free++;
        if(n_free==0)break;
    }

    /* Count what's left after SP phase */
    for(int v=0;v<n;v++)if(var_fixed[v]<0)(*n_after_sp)++;

    int flips=n*10000;if(flips>50000000)flips=50000000;
    for(int a=0;a<5;a++){
        rng_seed(a*12345ULL+n*77ULL);
        if(probsat(n,m,flips,2.06)==m)return m;
    }
    return 0;
}

/* ═══ BENCHMARK ═══ */
int main(void){
    printf("══════════════════════════════════════════════════════\n");
    printf("HIERARCHICAL SP: using full precision of marginals\n");
    printf("══════════════════════════════════════════════════════\n\n");

    int test_n[]={500, 1000, 2000, 5000};
    double test_alpha[]={4.0, 4.267};

    for(int ai=0;ai<2;ai++){
        double alpha=test_alpha[ai];
        printf("α=%.3f:\n",alpha);
        printf("  %5s | %10s | %10s | insight\n","n","oneshot","hierarchical");
        printf("  ------+------------+------------+---------\n");

        for(int ti=0;ti<4;ti++){
            int nn=test_n[ti];
            int ni=(nn<=1000)?10:(nn<=2000?5:3);

            int solved_os=0,solved_h=0,total=0;
            double tms_os=0,tms_h=0;
            int sum_iters=0,sum_core=0;

            for(int seed=0;seed<ni*3&&total<ni;seed++){
                /* One-shot */
                generate(nn,alpha,11000000ULL+seed);
                clock_t t0=clock();
                rng_seed(seed*31337ULL);
                int sat_os=solve_oneshot(nn);
                clock_t t1=clock();
                tms_os+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
                if(sat_os==n_clauses)solved_os++;

                /* Hierarchical */
                generate(nn,alpha,11000000ULL+seed);
                int iters=0,core=0;
                clock_t t2=clock();
                rng_seed(seed*31337ULL);
                int sat_h=solve_hierarchical_verbose(nn,&iters,&core);
                clock_t t3=clock();
                tms_h+=(double)(t3-t2)*1000.0/CLOCKS_PER_SEC;
                if(sat_h==n_clauses)solved_h++;
                sum_iters+=iters;
                sum_core+=core;

                total++;
            }

            printf("  %5d | %2d/%2d %4.1fs | %2d/%2d %4.1fs | iters=%.1f core=%.0f%%\n",
                   nn,solved_os,total,tms_os/total/1000,
                   solved_h,total,tms_h/total/1000,
                   (double)sum_iters/total,
                   100.0*sum_core/total/nn);
            fflush(stdout);
        }
        printf("\n");
    }

    printf("=== КЛЮЧЕВОЕ ===\n");
    printf("Если hierarchical > oneshot:\n");
    printf("  → иерархический порог извлекает БОЛЬШЕ информации\n");
    printf("  → точность маргиналов матter!\n");
    printf("Если hierarchical ≈ oneshot:\n");
    printf("  → SP уже всё что можно\n");
    printf("  → дополнительные биты точности БЕСПОЛЕЗНЫ\n");

    return 0;
}
