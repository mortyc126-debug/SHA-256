/*
 * CRYSTALLIZATION: grow the solution from frozen core
 * ====================================================
 *
 * Theory: don't SEARCH for solution, GROW it.
 * 1. SP → frozen core (seed crystal)
 * 2. BP on reduced formula → marginals for free vars
 * 3. Fix free vars one by one (most confident first)
 * 4. Update neighbors incrementally
 * 5. Backtrack on contradiction
 *
 * Predicted: O(n) total vs O(n^1.3) for probSAT
 *
 * Compile: gcc -O3 -march=native -o crystal crystal_solve.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       20000
#define MAX_CLAUSES 100000
#define MAX_K       3
#define MAX_DEGREE  200

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N];  /* -1=free, 0 or 1 */
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

/* SP surveys */
static double eta[MAX_CLAUSES][MAX_K];

/* BP marginals for free variables */
static double bp_msg[MAX_CLAUSES][MAX_K][2]; /* clause→var messages */
static double bp_marginal[MAX_N]; /* P(x_i = 1) */

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

/* ═══ SP (same as before) ═══ */
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

static void sp_compute_bias(double *W_plus, double *W_minus){
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

/* ═══ BP on reduced formula ═══ */
static void bp_init(void){
    for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<3;j++){bp_msg[ci][j][0]=0.5;bp_msg[ci][j][1]=0.5;}
}

static double bp_sweep(double damp){
    double mc=0;
    for(int ci=0;ci<n_clauses;ci++){
        if(!cl_active[ci])continue;
        for(int j=0;j<3;j++){
            int vi=cl_var[ci][j];
            if(var_fixed[vi]>=0)continue;

            int j1=(j+1)%3, j2=(j+2)%3;
            double new_mu[2];

            for(int xs=0;xs<2;xs++){
                double sum=0;
                for(int xt=0;xt<2;xt++){
                    for(int xu=0;xu<2;xu++){
                        /* Get effective values for j1 and j2 */
                        int v1=cl_var[ci][j1],v2=cl_var[ci][j2];
                        double p1,p2;

                        if(var_fixed[v1]>=0) p1=(xt==var_fixed[v1])?1.0:0.0;
                        else {
                            /* nu_{v1→ci}(xt) ∝ ∏_{b≠ci} μ_{b→v1}(xt) */
                            double prod=1.0;
                            for(int d2=0;d2<vdeg[v1];d2++){
                                int oci=vlist[v1][d2],opos=vpos[v1][d2];
                                if(oci==ci||!cl_active[oci])continue;
                                prod*=bp_msg[oci][opos][xt];}
                            p1=prod;
                        }
                        if(var_fixed[v2]>=0) p2=(xu==var_fixed[v2])?1.0:0.0;
                        else {
                            double prod=1.0;
                            for(int d2=0;d2<vdeg[v2];d2++){
                                int oci=vlist[v2][d2],opos=vpos[v2][d2];
                                if(oci==ci||!cl_active[oci])continue;
                                prod*=bp_msg[oci][opos][xu];}
                            p2=prod;
                        }

                        int li=(cl_sign[ci][j]==1)?xs:(1-xs);
                        int lt=(cl_sign[ci][j1]==1)?xt:(1-xt);
                        int lu=(cl_sign[ci][j2]==1)?xu:(1-xu);
                        if(li||lt||lu) sum+=p1*p2;
                    }}
                new_mu[xs]=sum;
            }
            double tot=new_mu[0]+new_mu[1];
            if(tot>1e-15){new_mu[0]/=tot;new_mu[1]/=tot;}
            else{new_mu[0]=new_mu[1]=0.5;}

            for(int s=0;s<2;s++){
                double old=bp_msg[ci][j][s];
                double upd=damp*old+(1-damp)*new_mu[s];
                double ch=fabs(upd-old);if(ch>mc)mc=ch;
                bp_msg[ci][j][s]=upd;
            }
        }
    }
    return mc;
}

static void bp_compute_marginals(void){
    for(int v=0;v<n_vars;v++){
        if(var_fixed[v]>=0){bp_marginal[v]=(var_fixed[v]==1)?1.0:0.0;continue;}
        double prod[2]={1.0,1.0};
        for(int d=0;d<vdeg[v];d++){
            int ci=vlist[v][d],pos=vpos[v][d];
            if(!cl_active[ci])continue;
            prod[0]*=bp_msg[ci][pos][0];
            prod[1]*=bp_msg[ci][pos][1];
        }
        double tot=prod[0]+prod[1];
        bp_marginal[v]=(tot>1e-15)?prod[1]/tot:0.5;
    }
}

/* ═══ Unit propagation ═══ */
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
    return 0;}

static void fix_var(int v,int val){
    var_fixed[v]=val;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
        if(!cl_active[ci])continue;int s=cl_sign[ci][p];
        if((s==1&&val==1)||(s==-1&&val==0))cl_active[ci]=0;}}

/* ═══ probSAT (for comparison) ═══ */
static int ps_a[MAX_N],ps_sc[MAX_CLAUSES],ps_ul[MAX_CLAUSES],ps_up[MAX_CLAUSES],ps_nu;
static int probsat_solve(int n,int m,int max_flips){
    for(int v=0;v<n;v++)ps_a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    memset(ps_sc,0,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
    ps_nu=0;memset(ps_up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(ps_sc[ci]==0){ps_up[ci]=ps_nu;ps_ul[ps_nu++]=ci;}
    double pt[64];for(int b=0;b<64;b++)pt[b]=pow(1.0+b,-2.06);
    for(int f=0;f<max_flips&&ps_nu>0;f++){
        int ci=ps_ul[rng_next()%ps_nu];
        double probs[3];double sum=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
            probs[j]=(br<64)?pt[br]:0;sum+=probs[j];}
        double r=rng_double()*sum;int fv;
        if(r<probs[0])fv=cl_var[ci][0];else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
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
    return m-ps_nu;}

/* ═══ EVALUATE ═══ */
static int evaluate(void){
    int sat=0;
    for(int ci=0;ci<n_clauses;ci++){
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            int val=(var_fixed[v]>=0)?var_fixed[v]:0;
            if((s==1&&val==1)||(s==-1&&val==0)){sat++;break;}}}
    return sat;}

/* ═══ CRYSTALLIZATION SOLVER ═══ */
static int sv_active[MAX_CLAUSES],sv_fixed[MAX_N];

static int crystal_solve(int nn){
    int n=nn,m=n_clauses;

    /* Phase 1: SP → frozen core */
    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

    int sp_conv=0;
    for(int iter=0;iter<200;iter++){double ch=sp_sweep(0.1);if(ch<1e-4){sp_conv=1;break;}}
    if(!sp_conv)for(int iter=0;iter<100;iter++){double ch=sp_sweep(0.3);if(ch<1e-4){sp_conv=1;break;}}

    if(sp_conv){
        double W_plus[MAX_N],W_minus[MAX_N];
        sp_compute_bias(W_plus,W_minus);

        /* Fix ONLY strongly biased (frozen core) */
        for(int v=0;v<n;v++){
            double b=fabs(W_plus[v]-W_minus[v]);
            if(b>0.9){
                int val=(W_plus[v]>W_minus[v])?1:0;
                fix_var(v,val);
            }
        }
        if(unit_prop()) goto fallback;
    }

    /* Phase 2: BP on reduced formula */
    bp_init();
    {
        int bp_conv=0;
        for(int iter=0;iter<200;iter++){
            double ch=bp_sweep(0.3);
            if(ch<1e-6){bp_conv=1;break;}
        }
        bp_compute_marginals();
    }

    /* Phase 3: Crystallization — grow from frozen core */
    {
        /* Save state for backtracking */
        memcpy(sv_active,cl_active,sizeof(int)*m);
        memcpy(sv_fixed,var_fixed,sizeof(int)*n);

        int n_fixed=0;
        for(int v=0;v<n;v++)if(var_fixed[v]>=0)n_fixed++;

        int max_backtracks=n;
        int backtracks=0;

        while(n_fixed<n && backtracks<max_backtracks){
            /* Find most confident unfixed variable */
            double best_conf=-1;
            int best_v=-1,best_val=0;
            for(int v=0;v<n;v++){
                if(var_fixed[v]>=0)continue;
                double conf=fabs(bp_marginal[v]-0.5);
                if(conf>best_conf){
                    best_conf=conf;best_v=v;
                    best_val=(bp_marginal[v]>0.5)?1:0;
                }
            }
            if(best_v<0)break;

            /* Fix it */
            fix_var(best_v,best_val);
            n_fixed++;

            /* Unit propagation */
            if(unit_prop()){
                /* Contradiction! Backtrack */
                backtracks++;
                memcpy(cl_active,sv_active,sizeof(int)*m);
                memcpy(var_fixed,sv_fixed,sizeof(int)*n);
                n_fixed=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)n_fixed++;

                /* Try opposite value */
                fix_var(best_v,1-best_val);
                n_fixed++;
                bp_marginal[best_v]=1-best_val; /* update marginal */
                if(unit_prop()) goto fallback;

                /* Update save point */
                memcpy(sv_active,cl_active,sizeof(int)*m);
                memcpy(sv_fixed,var_fixed,sizeof(int)*n);
            } else {
                /* Success — update save point */
                memcpy(sv_active,cl_active,sizeof(int)*m);
                memcpy(sv_fixed,var_fixed,sizeof(int)*n);
            }

            /* Incremental BP update: just recompute marginals for neighbors */
            for(int d=0;d<vdeg[best_v];d++){
                int ci=vlist[best_v][d];
                if(!cl_active[ci])continue;
                for(int j=0;j<3;j++){
                    int vj=cl_var[ci][j];
                    if(var_fixed[vj]>=0)continue;
                    /* Quick marginal recompute for vj */
                    double prod0=1.0,prod1=1.0;
                    for(int d2=0;d2<vdeg[vj];d2++){
                        int oci=vlist[vj][d2],opos=vpos[vj][d2];
                        if(!cl_active[oci])continue;
                        prod0*=bp_msg[oci][opos][0];
                        prod1*=bp_msg[oci][opos][1];
                    }
                    double tot=prod0+prod1;
                    bp_marginal[vj]=(tot>1e-15)?prod1/tot:0.5;
                }
            }
        }

        if(evaluate()==m) return m;
    }

fallback:
    /* Fallback: probSAT */
    rng_seed(77777ULL);
    return probsat_solve(n,m,n*10000);
}

/* ═══ ONE-SHOT SP + probSAT (for comparison) ═══ */
static int oneshot_solve(int nn){
    int n=nn,m=n_clauses;

    rng_seed(42ULL+(unsigned long long)n*13);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

    for(int iter=0;iter<200;iter++){double ch=sp_sweep(0.1);if(ch<1e-4)break;}
    for(int iter=0;iter<100;iter++){double ch=sp_sweep(0.3);if(ch<1e-4)break;}

    double W_plus[MAX_N],W_minus[MAX_N];
    sp_compute_bias(W_plus,W_minus);
    for(int v=0;v<n;v++) var_fixed[v]=(W_plus[v]>=W_minus[v])?1:0;

    rng_seed(12345ULL);
    return probsat_solve(n,m,n*10000);
}

/* ═══ BENCHMARK ═══ */
int main(void){
    printf("═══════════════════════════════════════════════════\n");
    printf("CRYSTALLIZATION vs ONE-SHOT+probSAT\n");
    printf("═══════════════════════════════════════════════════\n");
    printf("Crystal: SP→frozen core→BP→grow one by one\n");
    printf("OneShot: SP→fix all→probSAT repair\n\n");

    int test_n[]={200,500,1000,2000,5000,10000};

    printf("α=4.0:\n");
    printf("%6s | %14s | %14s\n","n","Crystal","OneShot+probSAT");
    printf("-------+----------------+----------------\n");

    for(int ti=0;ti<6;ti++){
        int nn=test_n[ti];
        int ni=(nn<=500)?10:(nn<=2000?5:3);

        int cs=0,os=0,ct=0;
        double cms=0,oms=0;

        for(int seed=0;seed<ni*3&&ct<ni;seed++){
            /* Crystal */
            generate(nn,4.0,11000000ULL+seed);
            clock_t t0=clock();
            int r1=crystal_solve(nn);
            clock_t t1=clock();
            double ms1=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            if(r1==n_clauses)cs++;
            cms+=ms1;

            /* OneShot */
            generate(nn,4.0,11000000ULL+seed);
            for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;
            memset(var_fixed,-1,sizeof(int)*nn);
            clock_t t2=clock();
            int r2=oneshot_solve(nn);
            clock_t t3=clock();
            double ms2=(double)(t3-t2)*1000.0/CLOCKS_PER_SEC;
            if(r2==n_clauses)os++;
            oms+=ms2;

            ct++;
        }

        printf("%6d | %2d/%2d %6.0fms | %2d/%2d %6.0fms | %.1f×\n",
               nn,cs,ct,cms/ct,os,ct,oms/ct,
               (cms/ct>0)?(oms/ct)/(cms/ct):0);
        fflush(stdout);
    }

    printf("\nα=4.267 (threshold):\n");
    printf("%6s | %14s | %14s\n","n","Crystal","OneShot+probSAT");
    printf("-------+----------------+----------------\n");

    for(int ti=0;ti<4;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?20:(nn<=500?10:5);

        int cs=0,os=0,ct=0;
        double cms=0,oms=0;

        for(int seed=0;seed<ni*3&&ct<ni;seed++){
            generate(nn,4.267,11000000ULL+seed);
            clock_t t0=clock();
            int r1=crystal_solve(nn);
            clock_t t1=clock();
            if(r1==n_clauses)cs++;
            cms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;

            generate(nn,4.267,11000000ULL+seed);
            for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;
            memset(var_fixed,-1,sizeof(int)*nn);
            clock_t t2=clock();
            int r2=oneshot_solve(nn);
            clock_t t3=clock();
            if(r2==n_clauses)os++;
            oms+=(double)(t3-t2)*1000.0/CLOCKS_PER_SEC;

            ct++;
        }

        printf("%6d | %2d/%2d %6.0fms | %2d/%2d %6.0fms | %.1f×\n",
               nn,cs,ct,cms/ct,os,ct,oms/ct,
               (cms/ct>0)?(oms/ct)/(cms/ct):0);
        fflush(stdout);
    }

    return 0;
}
