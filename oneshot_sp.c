/*
 * ONE-SHOT SP + probSAT: targeting n=100K+
 * ==========================================
 *
 * User insight: bits know their answer. Don't iterate.
 * 1. Run SP ONCE to convergence (~200 iterations)
 * 2. Set ALL vars to SP bias direction (no threshold)
 * 3. probSAT corrects the ~25% wrong bits
 *
 * This is 50× faster than iterative decimation
 * (1 convergence vs 50 rounds × reconvergence)
 *
 * Compile: gcc -O3 -march=native -o oneshot oneshot_sp.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

typedef struct { int ci, pos; } Edge;

static int n_vars, n_clauses;
static int (*cl_var)[3];
static int (*cl_sign)[3];
static Edge **vadj;
static int *vdeg;
static double (*eta)[3];

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

static void generate(int n, double ratio, unsigned long long seed) {
    n_vars = n;
    n_clauses = (int)(ratio * n);
    cl_var = calloc(n_clauses, sizeof(int[3]));
    cl_sign = calloc(n_clauses, sizeof(int[3]));
    vdeg = calloc(n, sizeof(int));
    vadj = calloc(n, sizeof(Edge*));
    eta = calloc(n_clauses, sizeof(double[3]));

    rng_seed(seed);
    /* Pass 1: count degrees */
    unsigned long long sv[4]; memcpy(sv, rng_s, 32);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){rng_next();vdeg[vs[j]]++;}}
    for(int v=0;v<n;v++){vadj[v]=malloc(vdeg[v]*sizeof(Edge));vdeg[v]=0;}

    /* Pass 2: fill */
    memcpy(rng_s, sv, 32);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];vadj[v][vdeg[v]].ci=ci;vadj[v][vdeg[v]].pos=j;vdeg[v]++;}}
}

static void cleanup(void){
    for(int v=0;v<n_vars;v++)free(vadj[v]);
    free(cl_var);free(cl_sign);free(vdeg);free(vadj);free(eta);
}

/* ═══ SP: one convergence, no decimation ═══ */
static double sp_sweep(int n, int m, double rho){
    double mc=0;
    for(int ci=0;ci<m;ci++){
        for(int pi=0;pi<3;pi++){
            double product=1.0;
            for(int pj=0;pj<3;pj++){
                if(pj==pi)continue;
                int j=cl_var[ci][pj];
                int sja=cl_sign[ci][pj];
                double ps=1.0,pu=1.0;
                for(int d=0;d<vdeg[j];d++){
                    int bi=vadj[j][d].ci,bp=vadj[j][d].pos;
                    if(bi==ci)continue;
                    double eb=eta[bi][bp];
                    if(cl_sign[bi][bp]==sja)ps*=(1.0-eb);else pu*=(1.0-eb);}
                double Pu=(1.0-pu)*ps,Ps=(1.0-ps)*pu,P0=pu*ps;
                double den=Pu+Ps+P0;
                product*=(den>1e-15)?(Pu/den):0.0;}
            double ov=eta[ci][pi];
            double up=rho*ov+(1.0-rho)*product;
            double ch=fabs(up-ov);if(ch>mc)mc=ch;
            eta[ci][pi]=up;}}
    return mc;
}

/* Compute bias from converged surveys */
static void compute_assignment(int n, int m, int *assign){
    for(int i=0;i<n;i++){
        double pp=1.0,pm=1.0;
        for(int d=0;d<vdeg[i];d++){
            int ci=vadj[i][d].ci,p=vadj[i][d].pos;
            double e=eta[ci][p];
            if(cl_sign[ci][p]==1)pp*=(1.0-e);else pm*=(1.0-e);}
        double pip=(1.0-pp)*pm,pim=(1.0-pm)*pp;
        assign[i]=(pip>=pim)?1:0;
    }
}

/* ═══ probSAT ═══ */
static int *ps_a,*ps_sc,*ps_ul,*ps_up;
static int ps_nu;

static int probsat_solve(int n, int m, const int *init, int max_flips, double cb){
    if(!ps_a){ps_a=malloc(n*sizeof(int));ps_sc=calloc(m,sizeof(int));
        ps_ul=malloc(m*sizeof(int));ps_up=malloc(m*sizeof(int));}

    memcpy(ps_a,init,n*sizeof(int));
    memset(ps_sc,0,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
    ps_nu=0;memset(ps_up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(ps_sc[ci]==0){ps_up[ci]=ps_nu;ps_ul[ps_nu++]=ci;}

    double pt[64];for(int b=0;b<64;b++)pt[b]=pow(1.0+b,-cb);

    for(int f=0;f<max_flips&&ps_nu>0;f++){
        int ci=ps_ul[rng_next()%ps_nu];
        double probs[3];double sum=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){
                int oci=vadj[v][d].ci,opos=vadj[v][d].pos;
                int os=cl_sign[oci][opos];
                if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
            probs[j]=(br<64)?pt[br]:0;sum+=probs[j];}
        double r=rng_double()*sum;int fv;
        if(r<probs[0])fv=cl_var[ci][0];
        else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
        else fv=cl_var[ci][2];

        int old=ps_a[fv],nw=1-old;ps_a[fv]=nw;
        for(int d=0;d<vdeg[fv];d++){
            int oci=vadj[fv][d].ci,opos=vadj[fv][d].pos;
            int os=cl_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){ps_sc[oci]--;if(ps_sc[oci]==0){ps_up[oci]=ps_nu;ps_ul[ps_nu++]=oci;}}
            else if(!was&&now){ps_sc[oci]++;if(ps_sc[oci]==1){int p2=ps_up[oci];
                if(p2>=0&&p2<ps_nu){int l=ps_ul[ps_nu-1];ps_ul[p2]=l;ps_up[l]=p2;ps_up[oci]=-1;ps_nu--;}}}}
    }
    return ps_nu;
}

static int solve_oneshot(int n, int m){
    /* Step 1: SP convergence — ONCE */
    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

    int conv=0;
    for(int iter=0;iter<300;iter++){
        double ch=sp_sweep(n,m,0.1);
        if(ch<1e-4){conv=1;break;}
    }
    if(!conv){
        for(int iter=0;iter<200;iter++){
            double ch=sp_sweep(n,m,0.3);
            if(ch<1e-4){conv=1;break;}
        }
    }

    /* Step 2: Extract assignment from SP bias — ALL bits */
    int *assign=malloc(n*sizeof(int));
    if(conv){
        compute_assignment(n,m,assign);
    } else {
        /* SP didn't converge: random init */
        for(int v=0;v<n;v++) assign[v]=rng_next()&1;
    }

    /* Count initial unsat */
    int init_unsat=0;
    for(int ci=0;ci<m;ci++){
        int ok=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            if((s==1&&assign[v]==1)||(s==-1&&assign[v]==0)){ok=1;break;}}
        if(!ok)init_unsat++;
    }

    /* Step 3: probSAT to fix remaining errors */
    ps_a=NULL;ps_sc=NULL;ps_ul=NULL;ps_up=NULL;
    ps_a=malloc(n*sizeof(int));ps_sc=calloc(m,sizeof(int));
    ps_ul=malloc(m*sizeof(int));ps_up=malloc(m*sizeof(int));

    int flips=n*10000;if(flips>200000000)flips=200000000;
    int result=0;

    /* Try multiple cb values */
    double cbs[]={2.06, 1.5, 2.5, 3.0};
    for(int ci2=0;ci2<4&&!result;ci2++){
        for(int a=0;a<3&&!result;a++){
            rng_seed(a*12345ULL+ci2*77777ULL);
            if(probsat_solve(n,m,assign,flips,cbs[ci2])==0) result=1;
        }
    }

    free(assign);free(ps_a);free(ps_sc);free(ps_ul);free(ps_up);
    ps_a=NULL;
    return result;
}

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("ONE-SHOT SP: bits know → probSAT corrects\n");
    printf("═══════════════════════════════════════════\n");
    printf("1 SP convergence, 0 decimation rounds\n\n");

    int test_n[]={1000,2000,5000,10000,20000,50000,75000,100000,150000,200000};

    printf("α=4.0:\n");
    for(int ti=0;ti<10;ti++){
        int nn=test_n[ti];
        int ni=(nn<=5000)?3:(nn<=50000?2:1);
        int solved=0,total=0;
        double tms=0;

        for(int seed=0;seed<ni*3&&total<ni;seed++){
            generate(nn,4.0,11000000ULL+seed);
            clock_t t0=clock();
            int ok=solve_oneshot(nn,n_clauses);
            clock_t t1=clock();
            double ms=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            tms+=ms;total++;if(ok)solved++;
            printf("  n=%6d seed=%d: %s (%.1fs)\n",nn,seed,ok?"SOLVED":"fail",ms/1000);
            fflush(stdout);
            cleanup();
        }
        printf("  → %d/%d (%.0f%%, avg %.1fs)\n\n",solved,total,100.0*solved/total,tms/total/1000);
        if(tms/total>600000&&solved==0){printf("  (stopping)\n");break;}
    }

    return 0;
}
