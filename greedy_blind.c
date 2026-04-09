/*
 * BLIND GREEDY: Find vars to flip WITHOUT knowing the solution
 * ═════════════════════════════════════════════════════════════
 *
 * We know: greedy path A→B has max 8 unsat (nearly flat).
 * Greedy picks the var whose flip gives HIGHEST sat.
 * With oracle (knowing B): this works perfectly.
 *
 * WITHOUT oracle: we don't know WHICH vars to consider.
 * But: any var with counterfactual Δsat > 0 IMPROVES.
 * And: we can RANK all n vars by Δsat.
 *
 * BLIND GREEDY:
 * 1. For every var v: compute Δsat if we flip v
 * 2. Flip the var with HIGHEST Δsat (if > 0)
 * 3. Repeat until no improving flip exists or solved
 *
 * This is essentially WalkSAT but without restriction to unsat clauses.
 * WalkSAT only considers vars IN unsat clauses.
 * BLIND GREEDY considers ALL vars.
 *
 * The difference: WalkSAT is LOCAL (vars in unsat clause).
 * Blind greedy is GLOBAL (best flip anywhere).
 *
 * Also test: RESTRICTED GREEDY — only consider vars with
 * ghost properties (disagreement, low counterfactual).
 *
 * Compile: gcc -O3 -march=native -o greedy_blind greedy_blind.c -lm
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

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){double u1=(rng_next()>>11)*(1.0/9007199254740992.0),u2=(rng_next()>>11)*(1.0/9007199254740992.0);if(u1<1e-15)u1=1e-15;return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;rng_seed(seed);memset(vdeg,0,sizeof(int)*n);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}}

static int assignment[MAX_N];
static int clause_sc[MAX_CLAUSES];
static void recompute(void){for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}}
static int count_unsat(void){int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0)c++;return c;}

static double x_cont[MAX_N];
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

static void flip_var(int v){int old=assignment[v],nw=1-old;assignment[v]=nw;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}

static void walksat_phase(int flips){for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);flip_var(fv);}}

/* BLIND GREEDY: check ALL vars, flip the one with best Δsat */
static int blind_greedy_step(int n){
    int best_v=-1, best_delta=-999;
    for(int v=0;v<n;v++){
        /* Compute Δsat for flipping v */
        int fixes=0, breaks=0;
        for(int d=0;d<vdeg[v];d++){
            int ci=vlist[v][d], pos=vpos[v][d], s=cl_sign[ci][pos];
            if(clause_sc[ci]==0){
                /* Currently unsat: would flipping v fix it? */
                int nv=1-assignment[v];
                if((s==1&&nv==1)||(s==-1&&nv==0)) fixes++;
            } else if(clause_sc[ci]==1){
                /* Currently sat by 1: is v the sole saver? */
                if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0)) breaks++;
            }
        }
        int delta=fixes-breaks;
        if(delta>best_delta){best_delta=delta;best_v=v;}
    }
    if(best_delta>0 && best_v>=0){
        flip_var(best_v);
        return best_delta;
    }
    /* No improving flip → try zero-cost flip (net=0) with probability */
    if(best_delta==0 && best_v>=0 && (rng_next()%3==0)){
        flip_var(best_v);
        return 0;
    }
    return -1; /* stuck */
}

int main(void){
    printf("══════════════════════════════════════════════\n");
    printf("BLIND GREEDY: Best flip from ALL vars\n");
    printf("══════════════════════════════════════════════\n\n");

    int test_n[]={100,200,300,500,750,1000};
    int sizes=6;

    printf("%6s | %5s | %6s | %6s | %6s | %8s\n",
           "n","total","blind","walkst","physws","time_ms");
    printf("-------+-------+--------+--------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?15:(nn<=500?8:4);
        int steps=2000+nn*15;

        int s_blind=0,s_walk=0,s_phys=0,total=0;
        double tms=0;

        for(int seed=0;seed<ni*3&&total<ni;seed++){
            generate(nn,4.267,47000000ULL+seed);
            int n=nn,m=n_clauses;
            clock_t t0=clock();

            /* Physics */
            physics(steps,42+seed*31);
            recompute();
            int phys_unsat=count_unsat();
            if(phys_unsat==0){s_blind++;s_walk++;s_phys++;total++;
                tms+=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;continue;}

            /* Save state */
            int save_a[MAX_N]; memcpy(save_a,assignment,sizeof(int)*n);

            /* Method 1: BLIND GREEDY (our new approach) */
            /* Start from physics output, apply blind greedy */
            int max_steps=n*5;
            for(int s=0;s<max_steps;s++){
                if(count_unsat()==0)break;
                int delta=blind_greedy_step(n);
                if(delta<0)break; /* stuck */
            }
            if(count_unsat()==0) s_blind++;
            int blind_final=count_unsat();

            /* Method 2: WalkSAT from same start */
            memcpy(assignment,save_a,sizeof(int)*n);
            recompute();
            rng_seed(seed*777);
            walksat_phase(n*500);
            if(count_unsat()==0) s_walk++;

            /* Method 3: Physics+WalkSAT (baseline) */
            memcpy(assignment,save_a,sizeof(int)*n);
            recompute();
            rng_seed(seed*888);
            walksat_phase(n*200);
            if(count_unsat()==0) s_phys++;

            total++;
            tms+=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;
        }

        printf("%6d | %2d/%2d | %4d   | %4d   | %4d   | %7.0fms\n",
               nn,total,total,s_blind,s_walk,s_phys,tms/total);
        fflush(stdout);
    }

    printf("\nBlind greedy = WalkSAT without clause restriction.\n");
    printf("It considers ALL vars, not just those in unsat clauses.\n");
    return 0;
}
