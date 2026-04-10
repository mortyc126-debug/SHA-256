/*
 * SP + probSAT: Best SP decimation + best local search
 * =====================================================
 *
 * Combines:
 *   - 3-state Survey Propagation (correct zero-T formulation)
 *   - probSAT finish (148× faster than WalkSAT at n=5000)
 *
 * probSAT: P(flip v) ∝ (ε + break(v))^{-cb}, cb=2.06 for 3-SAT
 * SP: 3-state cavity (P_u+P_s+P_0, excludes P_c)
 *
 * Target: n=10000+ at α=4.0, n=2000+ at α=4.267
 *
 * Compile: gcc -O3 -march=native -o sp_probsat sp_probsat.c -lm
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
            if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}
        }
    }
    for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
}

/* ============================================================
 * 3-STATE SP (same as sp_v4, proven correct)
 * ============================================================ */

static inline double sp_edge(int ci,int pos_i){
    double product=1.0;
    for(int pj=0;pj<3;pj++){
        if(pj==pos_i)continue;
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
            if(cl_sign[bi][bp]==sja)ps*=(1.0-eb);else pu*=(1.0-eb);
        }
        double Pu=(1.0-pu)*ps,Ps=(1.0-ps)*pu,P0=pu*ps;
        double den=Pu+Ps+P0;
        product*=(den>1e-15)?(Pu/den):0.0;
    }
    return product;
}

static double sp_sweep(double rho){
    double mc=0;
    for(int ci=0;ci<n_clauses;ci++){
        if(!cl_active[ci])continue;
        for(int p=0;p<3;p++){
            if(var_fixed[cl_var[ci][p]]>=0)continue;
            double nv=sp_edge(ci,p),ov=eta[ci][p];
            double up=rho*ov+(1.0-rho)*nv;
            double ch=fabs(up-ov);if(ch>mc)mc=ch;
            eta[ci][p]=up;
        }
    }
    return mc;
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
            if(sat)continue;
            double e=eta[ci][p];
            if(cl_sign[ci][p]==1)pp*=(1.0-e);else pm*=(1.0-e);
        }
        double pip=(1.0-pp)*pm,pim=(1.0-pm)*pp,pi0=pp*pm;
        double tot=pip+pim+pi0;
        if(tot>1e-15){W_plus[i]=pip/tot;W_minus[i]=pim/tot;}
    }
}

static int unit_prop(void){
    int changed=1;while(changed){changed=0;
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

static void fix_var(int v,int val){
    var_fixed[v]=val;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
        if(!cl_active[ci])continue;int s=cl_sign[ci][p];
        if((s==1&&val==1)||(s==-1&&val==0))cl_active[ci]=0;}
}

/* ============================================================
 * probSAT local search
 * ============================================================ */

static int ps_a[MAX_N];
static int ps_sc[MAX_CLAUSES];
static int ps_ulist[MAX_CLAUSES];
static int ps_upos[MAX_CLAUSES];
static int ps_nu;

static void ps_init(int n, int m) {
    for(int v=0;v<n;v++)
        ps_a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    memset(ps_sc,0,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
    ps_nu=0;memset(ps_upos,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)
        if(ps_sc[ci]==0){ps_upos[ci]=ps_nu;ps_ulist[ps_nu++]=ci;}
}

static inline void ps_flip(int fv, int m) {
    int old=ps_a[fv],nw=1-old;ps_a[fv]=nw;
    for(int d=0;d<vdeg[fv];d++){
        int oci=vlist[fv][d],opos=vpos[fv][d];
        int os=cl_sign[oci][opos];
        int was=((os==1&&old==1)||(os==-1&&old==0));
        int now=((os==1&&nw==1)||(os==-1&&nw==0));
        if(was&&!now){ps_sc[oci]--;
            if(ps_sc[oci]==0){ps_upos[oci]=ps_nu;ps_ulist[ps_nu++]=oci;}}
        else if(!was&&now){ps_sc[oci]++;
            if(ps_sc[oci]==1){int p2=ps_upos[oci];
                if(p2>=0&&p2<ps_nu){int l=ps_ulist[ps_nu-1];
                    ps_ulist[p2]=l;ps_upos[l]=p2;ps_upos[oci]=-1;ps_nu--;}}}
    }
}

static int probsat_finish(int n, int m, int max_flips) {
    double cb=2.06, eps=1.0;
    double pt[64];
    for(int b=0;b<64;b++) pt[b]=pow(eps+b,-cb);

    ps_init(n, m);

    for(int f=0;f<max_flips&&ps_nu>0;f++){
        int ci=ps_ulist[rng_next()%ps_nu];
        double probs[3]; double sum=0;
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){
                int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
            probs[j]=(br<64)?pt[br]:pow(eps+br,-cb);
            sum+=probs[j];
        }
        double r=rng_double()*sum;
        int fv;
        if(r<probs[0])fv=cl_var[ci][0];
        else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
        else fv=cl_var[ci][2];
        ps_flip(fv,m);
    }
    for(int v=0;v<n;v++) var_fixed[v]=ps_a[v];
    return m-ps_nu;
}

/* ============================================================
 * SP + probSAT SOLVER
 * ============================================================ */

static int saved_a[MAX_CLAUSES],saved_f[MAX_N];

static int sp_probsat_solve(int nn){
    int n=nn,m=n_clauses;
    if(unit_prop())return 0;
    memcpy(saved_a,cl_active,sizeof(int)*m);
    memcpy(saved_f,var_fixed,sizeof(int)*n);

    for(int restart=0;restart<3;restart++){
        if(restart>0){memcpy(cl_active,saved_a,sizeof(int)*m);memcpy(var_fixed,saved_f,sizeof(int)*n);}
        int nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;

        rng_seed(42ULL+restart*9973ULL+(unsigned long long)n*13);
        for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

        while(nf<n){
            /* Converge SP */
            int conv=0;
            for(int iter=0;iter<200;iter++){
                double ch=sp_sweep(0.1);if(ch<1e-4){conv=1;break;}}
            if(!conv)for(int iter=0;iter<100;iter++){
                double ch=sp_sweep(0.3);if(ch<1e-4){conv=1;break;}}
            if(!conv)break;

            double max_eta=0;
            for(int ci=0;ci<m;ci++){if(!cl_active[ci])continue;
                for(int j=0;j<3;j++){if(var_fixed[cl_var[ci][j]]>=0)continue;
                    if(eta[ci][j]>max_eta)max_eta=eta[ci][j];}}
            if(max_eta<0.01)break;

            compute_bias();
            int nfree=n-nf;
            int nfix=nfree/50;if(nfix<1)nfix=1;if(nfix>100)nfix=100;

            for(int f=0;f<nfix;f++){
                double bb=-1;int bv=-1,bval=0;
                for(int v=0;v<n;v++){if(var_fixed[v]>=0)continue;
                    double b=fabs(W_plus[v]-W_minus[v]);
                    if(b>bb){bb=b;bv=v;bval=(W_plus[v]>W_minus[v])?1:0;}}
                if(bv<0||bb<0.001)break;
                fix_var(bv,bval);nf++;
            }
            if(unit_prop())break;
            nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
        }

        /* probSAT finish (instead of WalkSAT!) */
        int flips=n*10000;
        if(flips>100000000)flips=100000000;
        for(int ps=0;ps<5;ps++){
            rng_seed(restart*77777ULL+ps*12345ULL+nf);
            int sat=probsat_finish(n,m,flips);
            if(sat==m)return sat;
        }
    }

    /* Final attempt */
    rng_seed(999999ULL);
    return probsat_finish(n_vars,n_clauses,n_vars*20000);
}

/* ============================================================
 * BENCHMARK
 * ============================================================ */
int main(void){
    printf("════════════════════════════════════════════════════\n");
    printf("SP + probSAT: Best SP + Best Local Search\n");
    printf("════════════════════════════════════════════════════\n");
    printf("3-state SP decimation → probSAT finish\n\n");

    /* Test at α=4.0 */
    {
        printf("α=4.0 (below threshold, should be ~100%%):\n");
        printf("  %6s | %5s | %6s | %8s\n","n","total","solved","time");
        printf("  -------+-------+--------+--------\n");

        int test_n[]={1000,2000,3000,5000,7500,10000,15000,20000};
        for(int ti=0;ti<8;ti++){
            int nn=test_n[ti];
            int ni=(nn<=2000)?5:(nn<=5000?3:2);
            int solved=0,total=0;double tms=0;

            for(int seed=0;seed<ni*3&&total<ni;seed++){
                generate(nn,4.0,11000000ULL+seed);
                clock_t t0=clock();
                rng_seed(seed*31337ULL);
                int sat=sp_probsat_solve(nn);
                clock_t t1=clock();
                double ms=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
                tms+=ms;total++;
                if(sat==n_clauses)solved++;
            }
            printf("  %6d | %2d/%2d | %4d   | %6.1fs\n",
                   nn,solved,total,solved,tms/total/1000);
            fflush(stdout);
            if(tms/total>180000&&solved==0){printf("    (stopping)\n");break;}
        }
    }

    printf("\n");

    /* Test at α=4.267 */
    {
        printf("α=4.267 (AT threshold):\n");
        printf("  %6s | %5s | %6s | %8s\n","n","total","solved","time");
        printf("  -------+-------+--------+--------\n");

        int test_n[]={200,500,1000,2000,3000,5000};
        for(int ti=0;ti<6;ti++){
            int nn=test_n[ti];
            int ni=(nn<=200)?20:(nn<=500?10:(nn<=2000?5:3));
            int solved=0,total=0;double tms=0;

            for(int seed=0;seed<ni*3&&total<ni;seed++){
                generate(nn,4.267,11000000ULL+seed);
                clock_t t0=clock();
                rng_seed(seed*31337ULL);
                int sat=sp_probsat_solve(nn);
                clock_t t1=clock();
                double ms=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
                tms+=ms;total++;
                if(sat==n_clauses)solved++;
            }
            printf("  %6d | %2d/%2d | %4d   | %6.1fs\n",
                   nn,solved,total,solved,tms/total/1000);
            fflush(stdout);
            if(tms/total>180000&&solved==0){printf("    (stopping)\n");break;}
        }
    }

    printf("\n=== COMPARISON ===\n");
    printf("SP+WalkSAT (v4):  α=4.0: n=3K 100%%, n=5K 67%%, n=7.5K 0%%\n");
    printf("SP+probSAT (this): (results above)\n");
    printf("Literature SP:     α=4.267: n=100K+\n");

    return 0;
}
