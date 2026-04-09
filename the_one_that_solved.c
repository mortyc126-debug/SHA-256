/*
 * THE ONE THAT SOLVED: What's different about solvable instances?
 * ═══════════════════════════════════════════════════════════════
 *
 * n=500: 1/10 solved by iterative ghost. WHY this one?
 *
 * Compare the solved instance vs the 9 that failed:
 * 1. Structure: unsat count, ghost count, cluster size
 * 2. Multi-reality consensus: how much do runs agree?
 * 3. Quality of majority vote: how many flips are correct?
 * 4. Convergence speed: how fast does iterative improve?
 * 5. WAVE PATTERN: is the correct flip a COHERENT pattern?
 *
 * Also: study the FLIP PATTERN that solved it.
 * Is it random or structured? Local or global?
 *
 * Compile: gcc -O3 -march=native -o solved_study the_one_that_solved.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      2000
#define MAX_CLAUSES 10000
#define MAX_K      3
#define MAX_DEGREE 200
#define N_RUNS     7

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
static int eval_a(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static double x_cont[MAX_N];
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

static void flip_var(int v){int old=assignment[v],nw=1-old;assignment[v]=nw;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}
static void walksat_phase(int flips){for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);flip_var(fv);}}

int main(void){
    printf("══════════════════════════════════════════════\n");
    printf("THE ONE THAT SOLVED vs THE NINE THAT DIDN'T\n");
    printf("══════════════════════════════════════════════\n\n");

    int nn=500;

    /* Profile each instance */
    for(int seed=0;seed<30;seed++){
        generate(nn,4.267,39000000ULL+seed);
        int n=nn, m=n_clauses, steps=2000+n*15;

        /* Initial */
        physics(steps,42+seed*31);
        recompute();rng_seed(seed*777);
        walksat_phase(n*200);
        int init_unsat=count_unsat();
        if(init_unsat<2)continue;

        /* Save initial state */
        int init_a[MAX_N];memcpy(init_a,assignment,sizeof(int)*n);

        /* Multi-run from initial */
        int run_a[N_RUNS][MAX_N];
        for(int r=0;r<N_RUNS;r++){
            memcpy(assignment,init_a,sizeof(int)*n);
            /* Warm physics from current */
            for(int v=0;v<n;v++)
                x_cont[v]=assignment[v]?0.85:0.15;
            rng_seed(42+r*7919+seed*99991);
            double vel2[MAX_N];memset(vel2,0,sizeof(double)*n);
            double force2[MAX_N];
            for(int step=0;step<500+n*3;step++){
                double prog=(double)step/(500+n*3);
                double T=0.12*exp(-3*prog)+0.0001;double cr=2+4*prog;
                memset(force2,0,sizeof(double)*n);
                for(int ci=0;ci<m;ci++){double lit[3],prod=1.0;
                    for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
                    if(prod<0.001)continue;double w=sqrt(prod);
                    for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force2[v]+=s*w*(prod/t);}}
                for(int v=0;v<n;v++){if(x_cont[v]>0.5)force2[v]+=cr*(1-x_cont[v]);else force2[v]-=cr*x_cont[v];
                    vel2[v]=0.9*vel2[v]+(force2[v]+rng_normal(0,T))*0.04;x_cont[v]+=vel2[v]*0.04;
                    if(x_cont[v]<0){x_cont[v]=0.01;vel2[v]=0;}if(x_cont[v]>1){x_cont[v]=0.99;vel2[v]=0;}}}
            for(int v=0;v<n;v++)run_a[r][v]=(x_cont[v]>0.5)?1:0;
        }

        memcpy(assignment,init_a,sizeof(int)*n);recompute();

        /* Measure consensus */
        double avg_agreement=0; /* avg across vars of max(p1, 1-p1) */
        int n_high_conf=0; /* vars where ≥80% runs agree */
        int n_disagree=0;  /* vars where primary differs from majority */
        double avg_cf=0;

        for(int v=0;v<n;v++){
            int sum=0;for(int r=0;r<N_RUNS;r++)sum+=run_a[r][v];
            double p1=(double)sum/N_RUNS;
            double conf=(p1>0.5)?p1:(1-p1);
            avg_agreement+=conf;
            if(conf>=0.8)n_high_conf++;
            int maj=(p1>0.5)?1:0;
            if(maj!=assignment[v])n_disagree++;

            /* CF */
            int ta[MAX_N];memcpy(ta,assignment,sizeof(int)*n);
            ta[v]=1-ta[v];avg_cf+=fabs(eval_a(ta)-eval_a(assignment));
        }
        avg_agreement/=n;
        avg_cf/=n;

        /* Try majority-guided solve */
        int save2[MAX_N];memcpy(save2,assignment,sizeof(int)*n);
        /* High-conf majority flip */
        for(int v=0;v<n;v++){
            int sum=0;for(int r=0;r<N_RUNS;r++)sum+=run_a[r][v];
            double p1=(double)sum/N_RUNS;
            int maj=(p1>=0.8)?1:(p1<=0.2)?0:-1;
            if(maj>=0&&maj!=assignment[v]){
                int ta[MAX_N];memcpy(ta,assignment,sizeof(int)*n);
                ta[v]=1-ta[v];int cf=eval_a(ta)-eval_a(assignment);
                if(cf>=-1)flip_var(v);}}
        recompute();
        int after_majority=count_unsat();

        /* WalkSAT from there */
        rng_seed(seed*55555);
        walksat_phase(n*500);
        int final_unsat=count_unsat();
        int solved=(final_unsat==0);

        memcpy(assignment,save2,sizeof(int)*n);recompute();

        printf("seed=%d: unsat=%2d → maj→%2d → walk→%2d | "
               "agree=%.2f hconf=%3d disag=%3d avgcf=%.2f | %s\n",
               seed, init_unsat, after_majority, final_unsat,
               avg_agreement, n_high_conf, n_disagree, avg_cf,
               solved?"★ SOLVED":"  failed");
    }
    return 0;
}
