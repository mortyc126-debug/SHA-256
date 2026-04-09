/*
 * FRACTAL DEPTH: Does bypass at K hops remove another ~20% each level?
 * ═══════════════════════════════════════════════════════════════════
 *
 * Test: after 2-hop bypass exhausted, try 3-hop. Then 4-hop.
 * If each level removes ~20% → fractal → O(n log n) total.
 * If deeper levels remove LESS → exponential barrier remains.
 *
 * Also: measure what the REMAINING hard core looks like.
 * Is it the same structure? Same pendulums? Or something new?
 *
 * Compile: gcc -O3 -march=native -o fractal fractal_depth.c -lm
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
    for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}}

static int assignment[MAX_N];
static int clause_sc[MAX_CLAUSES];
static void recompute(void){for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;
    for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}}
static int count_unsat(void){int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0)c++;return c;}

static double x_g[MAX_N],vel_g[MAX_N];
static void physics(int steps,unsigned long long seed){
    int n=n_vars;rng_seed(seed);
    for(int v=0;v<n;v++){double p1=0,p0=0;
        for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
            if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}
        x_g[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel_g[v]=0;}
    double force[MAX_N];
    for(int step=0;step<steps;step++){double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;
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
    for(int v=0;v<n;v++) assignment[v]=(x_g[v]>0.5)?1:0;}

static void flip_var(int v){
    int old=assignment[v],nw=1-old;assignment[v]=nw;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
        int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));
        if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}

static void walksat_phase(int flips){
    for(int f=0;f<flips;f++){
        int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}
        if(uci<0)return;
        int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);
        flip_var(fv);}}

/* Find best bypass at exactly K hops from unsat clause */
static int find_bypass_at_hop(int uci, int max_hops){
    int n=n_vars;
    /* BFS from vars in unsat clause to find vars at distance ≤ max_hops */
    int dist[MAX_N]; memset(dist,-1,sizeof(int)*n);
    int queue[MAX_N], qh=0, qt=0;

    /* Seed: vars in the unsat clause = distance 0 */
    int clause_vars[3];
    for(int j=0;j<3;j++){
        int v=cl_var[uci][j]; clause_vars[j]=v;
        dist[v]=0; queue[qt++]=v;}

    /* BFS on variable graph (connected via shared clauses) */
    while(qh<qt){
        int u=queue[qh++];
        if(dist[u]>=max_hops)continue;
        for(int d=0;d<vdeg[u]&&d<30;d++){
            int ci=vlist[u][d];
            for(int j=0;j<3;j++){
                int w=cl_var[ci][j];
                if(dist[w]<0){dist[w]=dist[u]+1;queue[qt++]=w;}}}}

    /* Search all vars at distance 1..max_hops for best net */
    int best_v=-1, best_net=-999, best_dist=0;
    for(int i=0;i<qt;i++){
        int v=queue[i];
        if(dist[v]<1)continue; /* skip clause vars themselves (distance 0) */
        int nv=1-assignment[v], fixes=0, breaks=0;
        for(int d=0;d<vdeg[v];d++){
            int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
            if(clause_sc[ci]==0){if((s==1&&nv==1)||(s==-1&&nv==0))fixes++;}
            else if(clause_sc[ci]==1){if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))breaks++;}}
        int net=fixes-breaks;
        if(net>best_net){best_net=net;best_v=v;best_dist=dist[v];}}

    return (best_net>0)?best_v:-1;
}

int main(void){
    printf("═══════════════════════════════════════\n");
    printf("FRACTAL DEPTH: Does deeper bypass help?\n");
    printf("═══════════════════════════════════════\n\n");

    int test_n[]={100, 200, 500};

    for(int ti=0;ti<3;ti++){
        int nn=test_n[ti]; int steps=2000+nn*15;
        int ni = (nn<=200)?8:4;

        double hop_reduction[6] = {0}; /* reduction at each hop level */
        int hop_count[6] = {0};

        for(int seed=0;seed<ni*5&&hop_count[0]<ni;seed++){
            generate(nn,4.267,31000000ULL+seed);
            physics(steps,42+seed*31);
            recompute();
            rng_seed(seed*777);
            walksat_phase(nn*200);

            int init_unsat=count_unsat();
            if(init_unsat<3)continue;
            hop_count[0]++;

            printf("n=%d seed=%d: init=%d → ",nn,seed,init_unsat);

            int prev_unsat=init_unsat;

            /* Try bypass at increasing hop distances */
            for(int hop=1;hop<=5;hop++){
                int improved=1;
                while(improved){
                    improved=0;
                    int nu=count_unsat();
                    if(nu==0)break;
                    /* Try each unsat clause */
                    for(int ci=0;ci<n_clauses;ci++){
                        if(clause_sc[ci]!=0)continue;
                        int bv=find_bypass_at_hop(ci, hop);
                        if(bv>=0){flip_var(bv);improved=1;break;}
                    }
                }
                int after=count_unsat();
                double red=(prev_unsat>0)?(double)(prev_unsat-after)/prev_unsat:0;
                hop_reduction[hop]+=red;
                hop_count[hop]++;

                printf("%dhop→%d ",hop,after);
                if(after==0){printf("SOLVED!");break;}
                prev_unsat=after;
            }
            printf("\n");
        }

        printf("\nn=%d summary:\n",nn);
        printf("  hop | avg reduction | cumulative\n");
        printf("  ----+---------------+-----------\n");
        double cumul=0;
        for(int hop=1;hop<=5;hop++){
            if(hop_count[hop]==0)break;
            double avg=hop_reduction[hop]/hop_count[hop];
            cumul=1-(1-cumul)*(1-avg);
            printf("  %3d | %12.1f%% | %9.1f%%\n",hop,100*avg,100*cumul);
        }
        printf("\n");
    }
    return 0;
}
