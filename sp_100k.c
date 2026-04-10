/*
 * SP+probSAT targeting n=100,000
 * ================================
 *
 * Optimizations vs sp_probsat.c:
 *   1. Dynamic allocation (no MAX_N limits)
 *   2. Clause-active tracking via linked list (O(1) skip inactive)
 *   3. UP uses a queue instead of re-scanning all clauses
 *   4. Edge-indexed SP sweep (skip fixed vars efficiently)
 *   5. probSAT as finish phase
 *
 * Compile: gcc -O3 -march=native -o sp100k sp_100k.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

/* ═══ Dynamic structures ═══ */
static int n_vars, n_clauses;
static int (*cl_var)[3];
static int (*cl_sign)[3];
static int *cl_active;
static int *var_fixed;

/* Adjacency: variable → list of (clause, position) */
typedef struct { int ci, pos; } VarEdge;
static VarEdge **vadj;   /* vadj[v] = array of edges */
static int *vdeg;

/* SP surveys */
static double (*eta)[3];
static double *W_plus, *W_minus;

/* RNG */
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

static void alloc_instance(int n, int m) {
    cl_var = (int(*)[3])calloc(m, sizeof(int[3]));
    cl_sign = (int(*)[3])calloc(m, sizeof(int[3]));
    cl_active = (int*)calloc(m, sizeof(int));
    var_fixed = (int*)malloc(n * sizeof(int));
    vdeg = (int*)calloc(n, sizeof(int));
    vadj = (VarEdge**)calloc(n, sizeof(VarEdge*));
    eta = (double(*)[3])calloc(m, sizeof(double[3]));
    W_plus = (double*)calloc(n, sizeof(double));
    W_minus = (double*)calloc(n, sizeof(double));
}

static void free_instance(void) {
    free(cl_var); free(cl_sign); free(cl_active); free(var_fixed);
    for(int v=0;v<n_vars;v++) free(vadj[v]);
    free(vadj); free(vdeg); free(eta); free(W_plus); free(W_minus);
}

static void generate(int n, double ratio, unsigned long long seed) {
    n_vars = n;
    n_clauses = (int)(ratio * n);
    alloc_instance(n, n_clauses);
    rng_seed(seed);

    /* First pass: count degrees */
    unsigned long long save_rng[4];
    memcpy(save_rng, rng_s, sizeof(rng_s));

    for(int ci=0; ci<n_clauses; ci++) {
        int vs[3]; vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++) { rng_next(); vdeg[vs[j]]++; }
    }

    /* Allocate adjacency */
    for(int v=0;v<n;v++) {
        vadj[v] = (VarEdge*)malloc(vdeg[v] * sizeof(VarEdge));
        vdeg[v] = 0;
    }

    /* Second pass: fill */
    memcpy(rng_s, save_rng, sizeof(rng_s));
    for(int ci=0; ci<n_clauses; ci++) {
        int vs[3]; vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++) {
            cl_var[ci][j] = vs[j];
            cl_sign[ci][j] = (rng_next()&1) ? 1 : -1;
            int v = vs[j];
            vadj[v][vdeg[v]].ci = ci;
            vadj[v][vdeg[v]].pos = j;
            vdeg[v]++;
        }
    }
    for(int ci=0;ci<n_clauses;ci++) cl_active[ci] = 1;
    memset(var_fixed, -1, sizeof(int)*n);
}

/* ═══ 3-state SP ═══ */
static inline double sp_edge(int ci, int pi) {
    double product = 1.0;
    for(int pj=0; pj<3; pj++) {
        if(pj==pi) continue;
        int j = cl_var[ci][pj];
        if(var_fixed[j]>=0) {
            int sj = cl_sign[ci][pj];
            if((sj==1&&var_fixed[j]==1)||(sj==-1&&var_fixed[j]==0)) return 0.0;
            continue;
        }
        int sja = cl_sign[ci][pj];
        double ps=1.0, pu=1.0;
        for(int d=0; d<vdeg[j]; d++) {
            int bi=vadj[j][d].ci, bp=vadj[j][d].pos;
            if(bi==ci || !cl_active[bi]) continue;
            /* Check if clause b satisfied by fixed var */
            int bsat=0;
            for(int k=0;k<3;k++) {
                int vk=cl_var[bi][k];
                if(var_fixed[vk]>=0) {
                    int sk=cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){bsat=1;break;}
                }
            }
            if(bsat) continue;
            double eb = eta[bi][bp];
            if(cl_sign[bi][bp]==sja) ps*=(1.0-eb); else pu*=(1.0-eb);
        }
        double Pu=(1.0-pu)*ps, Ps=(1.0-ps)*pu, P0=pu*ps;
        double den=Pu+Ps+P0;
        product *= (den>1e-15) ? (Pu/den) : 0.0;
    }
    return product;
}

static double sp_sweep(double rho) {
    double mc=0;
    int m=n_clauses;
    for(int ci=0; ci<m; ci++) {
        if(!cl_active[ci]) continue;
        for(int p=0; p<3; p++) {
            if(var_fixed[cl_var[ci][p]]>=0) continue;
            double nv=sp_edge(ci,p), ov=eta[ci][p];
            double up=rho*ov+(1.0-rho)*nv;
            double ch=fabs(up-ov);
            if(ch>mc) mc=ch;
            eta[ci][p]=up;
        }
    }
    return mc;
}

static int sp_converge(void) {
    for(int iter=0;iter<200;iter++){double ch=sp_sweep(0.1);if(ch<1e-4)return 1;}
    for(int iter=0;iter<100;iter++){double ch=sp_sweep(0.3);if(ch<1e-4)return 1;}
    return 0;
}

static void compute_bias(void) {
    int n=n_vars;
    for(int i=0;i<n;i++) {
        W_plus[i]=W_minus[i]=0;
        if(var_fixed[i]>=0) continue;
        double pp=1.0, pm=1.0;
        for(int d=0; d<vdeg[i]; d++) {
            int ci=vadj[i][d].ci, p=vadj[i][d].pos;
            if(!cl_active[ci]) continue;
            int sat=0;
            for(int k=0;k<3;k++){int vk=cl_var[ci][k];
                if(vk!=i&&var_fixed[vk]>=0){int sk=cl_sign[ci][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){sat=1;break;}}}
            if(sat) continue;
            double e=eta[ci][p];
            if(cl_sign[ci][p]==1) pp*=(1.0-e); else pm*=(1.0-e);
        }
        double pip=(1.0-pp)*pm, pim=(1.0-pm)*pp, pi0=pp*pm;
        double tot=pip+pim+pi0;
        if(tot>1e-15){W_plus[i]=pip/tot;W_minus[i]=pim/tot;}
    }
}

/* UP with queue */
static int *up_queue;
static int up_head, up_tail;

static int unit_prop(void) {
    int n=n_vars, m=n_clauses;
    if(!up_queue) up_queue=(int*)malloc(n*sizeof(int));
    up_head=up_tail=0;

    /* Seed queue with recently fixed vars */
    for(int v=0;v<n;v++) if(var_fixed[v]>=0) up_queue[up_tail++%n]=v;

    /* Also scan for unit clauses */
    for(int ci=0;ci<m;ci++) {
        if(!cl_active[ci]) continue;
        int sat=0,fc=0,fv=-1,fs=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}
            else{fc++;fv=v;fs=s;}}
        if(sat){cl_active[ci]=0;continue;}
        if(fc==0)return 1;
        if(fc==1&&var_fixed[fv]<0){var_fixed[fv]=(fs==1)?1:0;up_queue[up_tail++%n]=fv;}
    }

    while(up_head!=up_tail) {
        int v=up_queue[up_head++%n];
        for(int d=0;d<vdeg[v];d++) {
            int ci=vadj[v][d].ci;
            if(!cl_active[ci]) continue;
            int sat=0,fc=0,fv=-1,fs=0;
            for(int j=0;j<3;j++){int vj=cl_var[ci][j],s=cl_sign[ci][j];
                if(var_fixed[vj]>=0){if((s==1&&var_fixed[vj]==1)||(s==-1&&var_fixed[vj]==0))sat=1;}
                else{fc++;fv=vj;fs=s;}}
            if(sat){cl_active[ci]=0;continue;}
            if(fc==0)return 1;
            if(fc==1&&var_fixed[fv]<0){var_fixed[fv]=(fs==1)?1:0;up_queue[up_tail++%n]=fv;}
        }
    }
    return 0;
}

static void fix_var(int v, int val) {
    var_fixed[v]=val;
    for(int d=0;d<vdeg[v];d++){
        int ci=vadj[v][d].ci, p=vadj[v][d].pos;
        if(!cl_active[ci]) continue;
        int s=cl_sign[ci][p];
        if((s==1&&val==1)||(s==-1&&val==0)) cl_active[ci]=0;
    }
}

/* ═══ probSAT ═══ */
static int *ps_a, *ps_sc, *ps_ul, *ps_up2;
static int ps_nu;

static void ps_alloc(int n, int m) {
    ps_a=(int*)malloc(n*sizeof(int));
    ps_sc=(int*)calloc(m,sizeof(int));
    ps_ul=(int*)malloc(m*sizeof(int));
    ps_up2=(int*)malloc(m*sizeof(int));
}
static void ps_free(void){free(ps_a);free(ps_sc);free(ps_ul);free(ps_up2);}

static void ps_init(int n,int m){
    for(int v=0;v<n;v++) ps_a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    memset(ps_sc,0,sizeof(int)*m);
    for(int ci=0;ci<m;ci++) for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
    ps_nu=0;memset(ps_up2,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++) if(ps_sc[ci]==0){ps_up2[ci]=ps_nu;ps_ul[ps_nu++]=ci;}
}

static inline void ps_flip(int fv,int m){
    int old=ps_a[fv],nw=1-old;ps_a[fv]=nw;
    for(int d=0;d<vdeg[fv];d++){
        int oci=vadj[fv][d].ci, opos=vadj[fv][d].pos;
        int os=cl_sign[oci][opos];
        int was=((os==1&&old==1)||(os==-1&&old==0));
        int now=((os==1&&nw==1)||(os==-1&&nw==0));
        if(was&&!now){ps_sc[oci]--;if(ps_sc[oci]==0){ps_up2[oci]=ps_nu;ps_ul[ps_nu++]=oci;}}
        else if(!was&&now){ps_sc[oci]++;if(ps_sc[oci]==1){int p2=ps_up2[oci];
            if(p2>=0&&p2<ps_nu){int l=ps_ul[ps_nu-1];ps_ul[p2]=l;ps_up2[l]=p2;ps_up2[oci]=-1;ps_nu--;}}}
    }
}

static int probsat_run(int n,int m,int max_flips){
    double cb=2.06;
    double pt[64];for(int b=0;b<64;b++)pt[b]=pow(1.0+b,-cb);
    ps_init(n,m);
    for(int f=0;f<max_flips&&ps_nu>0;f++){
        int ci=ps_ul[rng_next()%ps_nu];
        double probs[3];double sum=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){
                int oci=vadj[v][d].ci, opos=vadj[v][d].pos;
                int os=cl_sign[oci][opos];
                if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
            probs[j]=(br<64)?pt[br]:pow(1.0+br,-cb);sum+=probs[j];}
        double r=rng_double()*sum;int fv;
        if(r<probs[0])fv=cl_var[ci][0];else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
        else fv=cl_var[ci][2];
        ps_flip(fv,m);
    }
    for(int v=0;v<n;v++)var_fixed[v]=ps_a[v];
    return m-ps_nu;
}

/* ═══ SOLVER ═══ */
static int solve(int nn){
    int n=nn, m=n_clauses;
    up_queue=NULL;

    if(unit_prop()){free(up_queue);up_queue=NULL;return 0;}

    /* Init surveys */
    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++) for(int j=0;j<3;j++) eta[ci][j]=rng_double();

    int nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;

    while(nf<n){
        if(!sp_converge()) break;
        double max_eta=0;
        for(int ci=0;ci<m;ci++){if(!cl_active[ci])continue;
            for(int j=0;j<3;j++){if(var_fixed[cl_var[ci][j]]>=0)continue;
                if(eta[ci][j]>max_eta)max_eta=eta[ci][j];}}
        if(max_eta<0.01) break;

        compute_bias();
        int nfree=n-nf, nfix=nfree/50;
        if(nfix<1)nfix=1;if(nfix>200)nfix=200;

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

    /* probSAT finish */
    ps_alloc(n,m);
    int flips=n*10000;if(flips>100000000)flips=100000000;
    int result=0;
    for(int attempt=0;attempt<5;attempt++){
        rng_seed(attempt*12345ULL+nf);
        if(probsat_run(n,m,flips)==m){result=m;break;}
    }
    ps_free();
    free(up_queue);up_queue=NULL;
    return result;
}

/* ═══ BENCHMARK ═══ */
int main(void){
    printf("══════════════════════════════════════════\n");
    printf("SP+probSAT: targeting n=100,000\n");
    printf("══════════════════════════════════════════\n\n");

    int test_n[]={1000, 2000, 5000, 10000, 20000, 50000, 75000, 100000};

    printf("α=4.0:\n");
    printf("%8s | %5s | %8s\n","n","solved","time");
    printf("---------+-------+---------\n");

    for(int ti=0;ti<8;ti++){
        int nn=test_n[ti];
        int ni=(nn<=5000)?3:(nn<=20000?2:1);
        int solved=0,total=0;
        double tms=0;

        for(int seed=0;seed<ni*3&&total<ni;seed++){
            generate(nn,4.0,11000000ULL+seed);
            clock_t t0=clock();
            rng_seed(seed*31337ULL);
            int sat=solve(nn);
            clock_t t1=clock();
            double ms=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            tms+=ms;total++;
            if(sat==n_clauses)solved++;
            printf("  n=%6d seed=%d: %s (%.1fs)\n",nn,seed,
                   sat==n_clauses?"SOLVED":"failed",ms/1000);
            fflush(stdout);
            free_instance();
        }
        printf("  → %d/%d (%.0f%%, avg %.1fs)\n\n",solved,total,100.0*solved/total,tms/total/1000);
        fflush(stdout);
        if(tms/total>300000&&solved==0){printf("  (stopping)\n");break;}
    }

    return 0;
}
