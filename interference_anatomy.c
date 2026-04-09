/*
 * INTERFERENCE ANATOMY: Through WHAT does fixing A break B?
 * ═══════════════════════════════════════════════════════════
 *
 * When we flip a var in component A, a clause in component B breaks.
 * That clause MUST contain the flipped var (otherwise it can't notice).
 * So the interference channel = SATISFIED clauses shared between
 * the suspect vars of different components.
 *
 * Study:
 * 1. CHANNEL: How many shared satisfied clauses between components?
 * 2. STRUCTURE: What do interference clauses look like?
 * 3. MINIMUM DAMAGE: Can we choose flips that AVOID interference?
 * 4. ITERATIVE: Does repeating critical-flip converge?
 * 5. THE NET: After K rounds of critical-flip, what's left?
 *
 * Compile: gcc -O3 -march=native -o interference interference_anatomy.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

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
static inline unsigned long long rng_next(void){
    unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];
    unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;
    s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);
    rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){
    rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;
    rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;
    for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){
    double u1=(rng_next()>>11)*(1.0/9007199254740992.0);
    double u2=(rng_next()>>11)*(1.0/9007199254740992.0);
    if(u1<1e-15)u1=1e-15;
    return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
    rng_seed(seed);memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];
            cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];if(vdeg[v]<MAX_DEGREE){
                vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
}

static int assignment[MAX_N];
static int clause_sc[MAX_CLAUSES];
static void recompute(void){for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;
    for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}}
static int count_unsat(void){int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0)c++;return c;}

static double x_g[MAX_N],vel_g[MAX_N];
static void physics(int steps,unsigned long long seed){
    int n=n_vars,m=n_clauses;rng_seed(seed);
    for(int v=0;v<n;v++){double p1=0,p0=0;
        for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
            if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}
        x_g[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel_g[v]=0;}
    double force[MAX_N];
    for(int step=0;step<steps;step++){double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++){double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                lit[j]=(s==1)?x_g[v]:(1.0-x_g[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){if(x_g[v]>0.5)force[v]+=cr*(1-x_g[v]);else force[v]-=cr*x_g[v];
            vel_g[v]=0.93*vel_g[v]+(force[v]+rng_normal(0,T))*0.05;
            x_g[v]+=vel_g[v]*0.05;
            if(x_g[v]<0){x_g[v]=0.01;vel_g[v]=fabs(vel_g[v])*0.3;}
            if(x_g[v]>1){x_g[v]=0.99;vel_g[v]=-fabs(vel_g[v])*0.3;}}}
    for(int v=0;v<n;v++) assignment[v]=(x_g[v]>0.5)?1:0;
}

static void flip_var(int v){
    int old=assignment[v],nw=1-old;assignment[v]=nw;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
        int was=((s==1&&old==1)||(s==-1&&old==0));
        int now=((s==1&&nw==1)||(s==-1&&nw==0));
        if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}

static void walksat_phase(int flips){
    int m=n_clauses;
    for(int f=0;f<flips;f++){
        int uci=-1;for(int ci=0;ci<m;ci++)if(clause_sc[ci]==0){uci=ci;break;}
        if(uci<0)return;
        int bv=cl_var[uci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);
        flip_var(fv);}}

static int get_critical(int v){
    int c=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];
        if(clause_sc[ci]==1){int pos=vpos[v][d],s=cl_sign[ci][pos];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))c++;}}
    return c;}

/* ═══ Get the TOTAL breaks for flipping v (not just critical of v's clauses,
       but all clauses that become unsat) ═══ */
static int get_total_breaks(int v){
    int breaks=0;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];
        if(clause_sc[ci]==1){int pos=vpos[v][d],s=cl_sign[ci][pos];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))breaks++;}}
    return breaks;}

/* ═══ Get total fixes for flipping v ═══ */
static int get_total_fixes(int v){
    int fixes=0;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];
        if(clause_sc[ci]==0){/* currently unsat — would flipping v fix it? */
            int pos=vpos[v][d],s=cl_sign[ci][pos];
            int new_val=1-assignment[v];
            if((s==1&&new_val==1)||(s==-1&&new_val==0))fixes++;}}
    return fixes;}

int main(void){
    printf("══════════════════════════════════════════════\n");
    printf("INTERFERENCE ANATOMY + ITERATIVE CONVERGENCE\n");
    printf("══════════════════════════════════════════════\n\n");

    int test_n[]={100, 200, 500, 1000};
    int sizes=4;

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?10:(nn<=500?5:3);
        int steps=2000+nn*15;

        for(int seed=0;seed<ni*5;seed++){
            generate(nn,4.267,27000000ULL+seed);
            physics(steps,42+seed*31);
            recompute();
            rng_seed(seed*777);
            walksat_phase(nn*200);

            int m=n_clauses;
            int init_unsat=count_unsat();
            if(init_unsat<3||init_unsat>nn/3)continue;

            printf("n=%d, seed=%d: initial unsat=%d\n",nn,seed,init_unsat);

            /* ═══ ITERATIVE CRITICAL FLIP ═══ */
            /* Round by round: pick unsat clause, flip min-critical, repeat */
            printf("  Round | unsat | fixed | broke | net\n");
            printf("  ------+-------+-------+-------+----\n");

            for(int round=0;round<30;round++){
                int before=count_unsat();
                if(before==0){printf("  SOLVED at round %d!\n",round);break;}

                /* Find first unsat clause */
                int uci=-1;
                for(int ci=0;ci<m;ci++)if(clause_sc[ci]==0){uci=ci;break;}
                if(uci<0)break;

                /* Among 3 suspects: pick the one with BEST net = fixes - breaks */
                int best_v=-1, best_net=-999;
                for(int j=0;j<3;j++){
                    int v=cl_var[uci][j];
                    int fixes=get_total_fixes(v);
                    int breaks=get_total_breaks(v);
                    int net=fixes-breaks;
                    if(net>best_net){best_net=net;best_v=v;}
                }

                int fixes_before=get_total_fixes(best_v);
                int breaks_before=get_total_breaks(best_v);
                flip_var(best_v);
                int after=count_unsat();

                printf("  %5d | %5d | %5d | %5d | %+3d\n",
                       round, after, fixes_before, breaks_before,
                       before-after);

                if(after==0){printf("  SOLVED at round %d!\n",round);break;}
            }

            int final_unsat=count_unsat();
            printf("  Final: %d unsat (from %d, reduction %.0f%%)\n\n",
                   final_unsat, init_unsat,
                   100.0*(init_unsat-final_unsat)/init_unsat);

            ni--;
            if(ni<=0)break;
        }
    }
    return 0;
}
