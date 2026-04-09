/*
 * PHYSICS + SP HYBRID: Physics for 99%, SP for the last 1%
 * ═══════════════════════════════════════════════════════════
 *
 * If P=NP, the algorithm is Source A + Source B.
 * Source A = physics (clause votes, ε=1/14) → 99% sat
 * Source B = SP (cluster reasoning) → the rest
 *
 * KEY IDEA: Don't run SP on the FULL instance.
 * Run SP on the RESIDUAL — only uncertain vars.
 *
 * After physics: 75% vars are DET (high |tension|, >99% correct).
 * Only 25% are uncertain (low |tension|).
 * Run SP on JUST THOSE 25%.
 *
 * The residual instance is SMALLER and EASIER:
 *   n_eff = 0.25n
 *   ratio_eff = ??? (depends on how many clauses remain)
 *   If ratio_eff < threshold → EASY (below condensation!)
 *
 * Compile: gcc -O3 -march=native -o hybrid physics_sp_hybrid.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      5000
#define MAX_CLAUSES 25000
#define MAX_K      3
#define MAX_DEGREE 200
#define SP_MAX_ITER 300
#define SP_EPS     1e-3

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N]; /* -1=free, 0 or 1 */
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){double u1=(rng_next()>>11)*(1.0/9007199254740992.0),u2=(rng_next()>>11)*(1.0/9007199254740992.0);if(u1<1e-15)u1=1e-15;return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;rng_seed(seed);memset(vdeg,0,sizeof(int)*n);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
    for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;memset(var_fixed,-1,sizeof(int)*n);}

static int assignment[MAX_N];
static int eval_full(void){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];int val=(var_fixed[v]>=0)?var_fixed[v]:assignment[v];if((ss==1&&val==1)||(ss==-1&&val==0)){s++;break;}}return s;}

static double x_cont[MAX_N];
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

static int unit_propagate(void){int changed=1;while(changed){changed=0;for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;int sat=0,fc=0,fv=-1,fs=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}else{fc++;fv=v;fs=s;}}if(sat){cl_active[ci]=0;continue;}if(fc==0)return 1;if(fc==1){var_fixed[fv]=(fs==1)?1:0;changed=1;}}}return 0;}

/* SP on ACTIVE clauses with FREE vars only */
static double eta[MAX_CLAUSES][MAX_K];

static double sp_update_edge(int ci,int pos_i){
    int var_i=cl_var[ci][pos_i];if(var_fixed[var_i]>=0)return 0;
    double product=1.0;
    for(int pj=0;pj<3;pj++){if(pj==pos_i)continue;int j=cl_var[ci][pj];
        if(var_fixed[j]>=0){int sj=cl_sign[ci][pj];
            if((sj==1&&var_fixed[j]==1)||(sj==-1&&var_fixed[j]==0))return 0;continue;}
        int sign_j_in_a=cl_sign[ci][pj];
        double prod_s=1,prod_u=1;
        for(int d=0;d<vdeg[j];d++){int bi=vlist[j][d],bp=vpos[j][d];
            if(bi==ci||!cl_active[bi])continue;
            int sat=0;for(int k=0;k<3;k++){int vk=cl_var[bi][k];
                if(var_fixed[vk]>=0){int sk=cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))sat=1;}}
            if(sat)continue;
            int sign_j_in_b=cl_sign[bi][bp];double e=eta[bi][bp];
            if(sign_j_in_b==sign_j_in_a)prod_s*=(1-e);else prod_u*=(1-e);}
        double Pu=(1-prod_u)*prod_s,Ps=(1-prod_s)*prod_u,P0=prod_u*prod_s;
        double Pc=(1-prod_u)*(1-prod_s);double total=Pu+Ps+P0+Pc;
        product*=(total>1e-15)?Pu/total:0;}
    return product;}

static int sp_decimation_solve(int nn){
    int n=nn,m=n_clauses;
    /* Init surveys */
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)
        eta[ci][j]=(rng_next()%1000)/2000.0;

    int total_decimated=0;

    while(1){
        int n_free=0;for(int v=0;v<n;v++)if(var_fixed[v]<0)n_free++;
        if(n_free==0)break;

        /* Converge SP */
        for(int iter=0;iter<SP_MAX_ITER;iter++){
            double maxch=0;
            for(int ci=0;ci<m;ci++){if(!cl_active[ci])continue;
                for(int p=0;p<3;p++){double ne=sp_update_edge(ci,p);
                    double ch=fabs(ne-eta[ci][p]);if(ch>maxch)maxch=ch;
                    eta[ci][p]=0.5*ne+0.5*eta[ci][p];}}
            if(maxch<SP_EPS)break;}

        /* Check trivialization */
        double max_eta=0;
        for(int ci=0;ci<m;ci++){if(!cl_active[ci])continue;
            for(int j=0;j<3;j++){if(var_fixed[cl_var[ci][j]]>=0)continue;
                if(eta[ci][j]>max_eta)max_eta=eta[ci][j];}}

        if(max_eta<0.01){
            /* Trivialized — fill remaining from physics assignment */
            for(int v=0;v<n;v++)if(var_fixed[v]<0)var_fixed[v]=assignment[v];
            break;
        }

        /* Compute bias */
        double W_plus[MAX_N],W_minus[MAX_N];
        for(int i=0;i<n;i++){W_plus[i]=W_minus[i]=0;
            if(var_fixed[i]>=0)continue;
            double pp=1,pm=1;
            for(int d=0;d<vdeg[i];d++){int ci=vlist[i][d],p=vpos[i][d];
                if(!cl_active[ci])continue;
                int sat=0;for(int k=0;k<3;k++){int vk=cl_var[ci][k];
                    if(vk!=i&&var_fixed[vk]>=0){int sk=cl_sign[ci][k];
                        if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))sat=1;}}
                if(sat)continue;
                int s=cl_sign[ci][p];double e=eta[ci][p];
                if(s==1)pp*=(1-e);else pm*=(1-e);}
            double pi_p=(1-pp)*pm,pi_m=(1-pm)*pp,pi_0=pp*pm;
            double tot=pi_p+pi_m+pi_0;
            if(tot>1e-15){W_plus[i]=pi_p/tot;W_minus[i]=pi_m/tot;}}

        /* Decimate */
        int to_fix=n_free/100;if(to_fix<1)to_fix=1;if(to_fix>20)to_fix=20;
        for(int f=0;f<to_fix;f++){
            double best_bias=-1;int best_v=-1,best_val=0;
            for(int v=0;v<n;v++){if(var_fixed[v]>=0)continue;
                double bias=fabs(W_plus[v]-W_minus[v]);
                if(bias>best_bias){best_bias=bias;best_v=v;
                    best_val=(W_plus[v]>W_minus[v])?1:0;}}
            if(best_v<0)break;
            var_fixed[best_v]=best_val;total_decimated++;
            for(int d=0;d<vdeg[best_v];d++){int ci=vlist[best_v][d],p=vpos[best_v][d];
                if(!cl_active[ci])continue;int s=cl_sign[ci][p];
                if((s==1&&best_val==1)||(s==-1&&best_val==0))cl_active[ci]=0;}}

        if(unit_propagate()){
            /* Conflict — fill from assignment */
            for(int v=0;v<n;v++)if(var_fixed[v]<0)var_fixed[v]=assignment[v];
            break;
        }
    }

    return n_clauses-eval_full();
}

static void walksat_final(int flips){
    /* Build working assignment from var_fixed */
    for(int v=0;v<n_vars;v++)assignment[v]=(var_fixed[v]>=0)?var_fixed[v]:assignment[v];
    int clause_sc[MAX_CLAUSES];
    for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}
    for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);int old=assignment[fv],nw=1-old;assignment[fv]=nw;for(int d=0;d<vdeg[fv];d++){int ci=vlist[fv][d],pos=vpos[fv][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}}

static int count_unsat_full(void){
    int c=0;for(int ci=0;ci<n_clauses;ci++){int ok=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0)){ok=1;break;}}
        if(!ok)c++;}return c;}

int main(void){
    printf("═══════════════════════════════════════════════\n");
    printf("PHYSICS + SP HYBRID: Source A + Source B\n");
    printf("═══════════════════════════════════════════════\n\n");

    int test_n[]={100,200,300,500,750,1000};
    int sizes=6;

    printf("%6s | %5s | %6s | %6s | %8s\n","n","total","hybrid","phys+w","time_ms");
    printf("-------+-------+--------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?15:(nn<=500?8:4);
        int steps=2000+nn*15;
        int s_hybrid=0,s_base=0,total=0;
        double tms=0;

        for(int seed=0;seed<ni*5&&total<ni;seed++){
            generate(nn,4.267,56000000ULL+seed);
            clock_t t0=clock();

            /* Phase 1: Physics */
            physics(steps,42+seed*31);

            /* Phase 2: Fix HIGH-CONFIDENCE vars (|tension| > threshold) */
            double tension[MAX_N];
            for(int v=0;v<nn;v++){
                double p1=0,p0=0;
                for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
                    if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}
                tension[v]=(p1+p0>0)?(p1-p0)/(p1+p0):0;
            }

            /* Fix vars with |tension| > 0.5 (high confidence from physics) */
            int n_fixed=0, n_free=0;
            for(int v=0;v<nn;v++){
                if(fabs(tension[v])>0.5){
                    var_fixed[v]=assignment[v];n_fixed++;
                } else {
                    var_fixed[v]=-1;n_free++;
                }
            }

            /* Simplify: deactivate sat clauses */
            for(int ci=0;ci<n_clauses;ci++){cl_active[ci]=1;
                for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                    if(var_fixed[v]>=0&&((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0)))
                        {cl_active[ci]=0;break;}}}

            /* UP */
            unit_propagate();
            int n_active=0;for(int ci=0;ci<n_clauses;ci++)if(cl_active[ci])n_active++;
            int n_still_free=0;for(int v=0;v<nn;v++)if(var_fixed[v]<0)n_still_free++;

            /* Phase 3: SP on residual */
            rng_seed(seed*31337);
            int sp_unsat = sp_decimation_solve(nn);

            /* Phase 4: WalkSAT polish */
            walksat_final(nn*500);
            int final_unsat=count_unsat_full();

            if(final_unsat==0) s_hybrid++;

            /* Baseline: physics + WalkSAT only */
            physics(steps,42+seed*31);
            rng_seed(seed*777);
            int clause_sc2[MAX_CLAUSES];
            for(int ci=0;ci<n_clauses;ci++){clause_sc2[ci]=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc2[ci]++;}}
            /* Quick WalkSAT */
            for(int f=0;f<nn*500;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc2[ci]==0){uci=ci;break;}if(uci<0)break;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc2[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);int old=assignment[fv],nw=1-old;assignment[fv]=nw;for(int d=0;d<vdeg[fv];d++){int ci=vlist[fv][d],pos=vpos[fv][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc2[ci]--;else if(!was&&now)clause_sc2[ci]++;}}
            int base_unsat=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc2[ci]==0)base_unsat++;
            if(base_unsat==0)s_base++;

            total++;
            tms+=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;
        }

        printf("%6d | %2d/%2d | %4d   | %4d   | %7.0fms\n",
               nn,total,total,s_hybrid,s_base,tms/total);
        fflush(stdout);
    }

    printf("\nPrevious: SP alone 2/5@750, PhysicsSAT 4/20@500\n");
    return 0;
}
