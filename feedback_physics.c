/*
 * FEEDBACK PHYSICS: Unsat clauses reshape the energy landscape
 * ═══════════════════════════════════════════════════════════
 *
 * Not fixing vars. Not flipping. RESHAPING THE SURFACE.
 *
 * Pipeline:
 * 1. Physics → 99% sat → find 9 unsat clauses
 * 2. BOOST weight of those 9 clauses (×10, ×100)
 * 3. Re-run physics FROM SCRATCH on weighted instance
 * 4. New unsat clauses emerge → boost them too
 * 5. Repeat: the landscape EVOLVES toward the solution cluster
 *
 * The idea: unsat clauses are SIGNPOSTS pointing to the right cluster.
 * Each cycle, physics explores a DIFFERENT valley because the
 * energy landscape has changed.
 *
 * Also test: boost ALL cold-start unsat clauses (union of 20 runs)
 *
 * Compile: gcc -O3 -march=native -o feedback feedback_physics.c -lm
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
static double cl_weight[MAX_CLAUSES]; /* dynamic weights! */
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){double u1=(rng_next()>>11)*(1.0/9007199254740992.0),u2=(rng_next()>>11)*(1.0/9007199254740992.0);if(u1<1e-15)u1=1e-15;return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;rng_seed(seed);memset(vdeg,0,sizeof(int)*n);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
    for(int ci=0;ci<n_clauses;ci++)cl_weight[ci]=1.0;}

static int assignment[MAX_N];
static int clause_sc[MAX_CLAUSES];
static void recompute(void){for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}}
static int count_unsat(void){int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0)c++;return c;}

static double x_cont[MAX_N];

/* Physics with WEIGHTED clauses */
static void weighted_physics(int steps,unsigned long long seed){
    int n=n_vars,m=n_clauses;rng_seed(seed);double vel[MAX_N];
    for(int v=0;v<n;v++){double p1=0,p0=0;
        for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
            double w=cl_weight[ci]/3.0;
            if(cl_sign[ci][p]==1)p1+=w;else p0+=w;}
        x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}
    double force[MAX_N];
    for(int step=0;step<steps;step++){
        double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++){
            double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;
            double w=sqrt(prod) * cl_weight[ci]; /* WEIGHTED force! */
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;
                force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){
            if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);
            else force[v]-=cr*x_cont[v];
            vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;
            x_cont[v]+=vel[v]*0.05;
            if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}
    for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;
}

static void walksat_phase(int flips){for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);int old=assignment[fv],nw=1-old;assignment[fv]=nw;for(int d=0;d<vdeg[fv];d++){int ci=vlist[fv][d],pos=vpos[fv][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}}

static int feedback_solve(int nn, double boost_factor, int n_cycles){
    int n=nn, m=n_clauses;
    int steps=2000+n*15;
    int best_unsat=m;
    int best_a[MAX_N];

    /* Reset weights */
    for(int ci=0;ci<m;ci++) cl_weight[ci]=1.0;

    for(int cycle=0;cycle<n_cycles;cycle++){
        /* Physics with current weights */
        weighted_physics(steps, 42+cycle*13337);
        recompute();

        /* WalkSAT polish */
        rng_seed(cycle*77777);
        walksat_phase(n*200);

        int nu=count_unsat();
        if(nu<best_unsat){best_unsat=nu;memcpy(best_a,assignment,sizeof(int)*n);}
        if(nu==0) return 0; /* SOLVED */

        /* FEEDBACK: boost unsat clauses */
        for(int ci=0;ci<m;ci++){
            if(clause_sc[ci]==0){
                cl_weight[ci]*=boost_factor; /* amplify unsat */
                if(cl_weight[ci]>1000)cl_weight[ci]=1000; /* cap */
            } else {
                /* Slight decay on satisfied clauses */
                cl_weight[ci]*=0.99;
                if(cl_weight[ci]<0.1)cl_weight[ci]=0.1;
            }
        }
    }

    /* Final attempt: restore best, WalkSAT hard */
    memcpy(assignment,best_a,sizeof(int)*n);
    recompute();
    rng_seed(99999);
    walksat_phase(n*500);
    return count_unsat();
}

int main(void){
    printf("══════════════════════════════════════════════════\n");
    printf("FEEDBACK PHYSICS: Reshape landscape from unsat\n");
    printf("══════════════════════════════════════════════════\n\n");

    int test_n[]={100,200,300,500,750,1000};
    int sizes=6;

    /* Test different boost factors and cycle counts */
    double boosts[]={2.0, 5.0, 10.0};
    int n_boosts=3;

    for(int bi=0;bi<n_boosts;bi++){
        double bf=boosts[bi];
        printf("─── Boost factor = %.0f× ───\n",bf);
        printf("%6s | %5s | %6s | %6s | %8s\n","n","total","solved","best_u","time_ms");
        printf("-------+-------+--------+--------+----------\n");

        for(int ti=0;ti<sizes;ti++){
            int nn=test_n[ti];
            int ni=(nn<=200)?15:(nn<=500?8:4);
            int cycles=(nn<=200)?20:10;
            int solved=0,total=0;double sum_best=0,tms=0;

            for(int seed=0;seed<ni*3&&total<ni;seed++){
                generate(nn,4.267,42000000ULL+seed);
                clock_t t0=clock();
                int final_u=feedback_solve(nn,bf,cycles);
                clock_t t1=clock();
                tms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
                total++;
                if(final_u==0)solved++;
                sum_best+=final_u;
            }

            printf("%6d | %2d/%2d | %4d   | %5.1f  | %7.0fms\n",
                   nn,total,total,solved,sum_best/total,tms/total);
            fflush(stdout);
        }
        printf("\n");
    }

    printf("Previous best at n=500: PhysicsSAT 4/20, SP 2/10, Ghost 1/10\n");
    return 0;
}
