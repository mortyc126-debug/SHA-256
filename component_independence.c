/*
 * COMPONENT INDEPENDENCE: Are the 39 unsat components truly independent?
 * ═════════════════════════════════════════════════════════════════════
 *
 * If we fix component A, does it affect component B?
 * This is THE critical question. If independent → polynomial.
 *
 * Tests:
 * 1. Fix one component (flip its min-critical) → count NEW unsat in others
 * 2. Fix ALL components one by one → does total improve monotonically?
 * 3. Fix ALL simultaneously → compare with one-by-one
 * 4. Cross-component clause sharing: do they share SATISFIED clauses?
 *    (Fixing A might break a clause shared with B)
 * 5. Size distribution: how big are components?
 * 6. What fraction of the problem is SOLVED by component-by-component?
 *
 * Compile: gcc -O3 -march=native -o comp_indep component_independence.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      5000
#define MAX_CLAUSES 25000
#define MAX_K      3
#define MAX_DEGREE 200
#define MAX_COMP   500

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
static void recompute(void){
    for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}}
static int count_unsat(void){
    int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0)c++;return c;}

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
    for(int d=0;d<vdeg[v];d++){
        int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
        int was=((s==1&&old==1)||(s==-1&&old==0));
        int now=((s==1&&nw==1)||(s==-1&&nw==0));
        if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}

static int walksat_phase(int flips){
    int m=n_clauses;
    for(int f=0;f<flips;f++){
        int uci=-1;for(int ci=0;ci<m;ci++)if(clause_sc[ci]==0){uci=ci;break;}
        if(uci<0)return 0;
        int bv=cl_var[uci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);
        flip_var(fv);}
    return count_unsat();}

static int get_critical(int v){
    int c=0;for(int d=0;d<vdeg[v];d++){
        int ci=vlist[v][d];if(clause_sc[ci]==1){
            int pos=vpos[v][d],s=cl_sign[ci][pos];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))c++;}}
    return c;}

/* Build components of unsat clauses */
static int comp_id[MAX_CLAUSES]; /* which component each unsat clause belongs to */
static int comp_clauses[MAX_COMP][100]; /* clause indices per component */
static int comp_size[MAX_COMP]; /* #clauses per component */
static int n_components;

static void build_components(void){
    int m=n_clauses;
    int unsat[MAX_CLAUSES],nu=0;
    for(int ci=0;ci<m;ci++){comp_id[ci]=-1;if(clause_sc[ci]==0)unsat[nu++]=ci;}

    n_components=0;
    memset(comp_size,0,sizeof(comp_size));

    for(int i=0;i<nu;i++){
        if(comp_id[unsat[i]]>=0)continue;
        int cid=n_components++;
        if(cid>=MAX_COMP)break;
        int q[MAX_CLAUSES],qh=0,qt=0;
        q[qt++]=i; comp_id[unsat[i]]=cid;
        while(qh<qt){
            int ci=unsat[q[qh++]];
            comp_clauses[cid][comp_size[cid]++]=ci;
            for(int j2=0;j2<nu;j2++){
                if(comp_id[unsat[j2]]>=0)continue;
                int sh=0;
                for(int a=0;a<3;a++)for(int b=0;b<3;b++)
                    if(cl_var[ci][a]==cl_var[unsat[j2]][b])sh=1;
                if(sh){comp_id[unsat[j2]]=cid;q[qt++]=j2;}}}}
}

int main(void){
    printf("══════════════════════════════════════════════════════\n");
    printf("COMPONENT INDEPENDENCE TEST\n");
    printf("══════════════════════════════════════════════════════\n\n");

    int test_n[]={100, 200, 300, 500, 750, 1000};
    int sizes=6;

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?10:(nn<=500?6:3);
        int steps=2000+nn*15;

        double sum_interference=0, sum_fixed_by_seq=0;
        double sum_n_comp=0, sum_unsat=0;
        double sum_seq_solved=0, sum_simul_solved=0;
        int n_inst=0;

        for(int seed=0;seed<ni*5&&n_inst<ni;seed++){
            generate(nn,4.267,26000000ULL+seed);
            physics(steps,42+seed*31);
            recompute();
            rng_seed(seed*777);
            walksat_phase(nn*200);

            int m=n_clauses;
            int init_unsat=count_unsat();
            if(init_unsat<3||init_unsat>nn/3)continue;
            n_inst++;

            build_components();
            sum_n_comp+=n_components;
            sum_unsat+=init_unsat;

            /* ═══ TEST 1: Sequential component fixing ═══ */
            /* Fix components one at a time. After each: count NEW unsat elsewhere. */
            int save_a[MAX_N]; memcpy(save_a,assignment,sizeof(int)*nn);
            int total_interference=0;
            int seq_fixed=0;

            for(int cid=0;cid<n_components;cid++){
                /* Before fixing: count unsat in OTHER components */
                int other_unsat_before=0;
                for(int ci=0;ci<m;ci++)
                    if(clause_sc[ci]==0 && comp_id[ci]!=cid)
                        other_unsat_before++;

                /* Fix this component: flip min-critical for each clause */
                for(int k=0;k<comp_size[cid];k++){
                    int uci=comp_clauses[cid][k];
                    if(clause_sc[uci]>0)continue; /* already fixed by earlier flip */
                    int mc=nn+1,mv=-1;
                    for(int j=0;j<3;j++){int v=cl_var[uci][j];
                        int c=get_critical(v);if(c<mc){mc=c;mv=v;}}
                    if(mv>=0)flip_var(mv);
                }

                /* After fixing: count unsat in OTHER components */
                int other_unsat_after=0;
                for(int ci=0;ci<m;ci++)
                    if(clause_sc[ci]==0 && comp_id[ci]!=cid)
                        other_unsat_after++;

                int interference=other_unsat_after-other_unsat_before;
                total_interference+=abs(interference);

                /* Count how many component's own clauses got fixed */
                int own_fixed=0;
                for(int k=0;k<comp_size[cid];k++)
                    if(clause_sc[comp_clauses[cid][k]]>0)own_fixed++;
                seq_fixed+=own_fixed;
            }

            int seq_unsat=count_unsat();
            sum_interference+=(double)total_interference/n_components;
            sum_fixed_by_seq+=(double)(init_unsat-seq_unsat);
            if(seq_unsat==0) sum_seq_solved++;

            /* ═══ TEST 2: Simultaneous fixing (all at once) ═══ */
            memcpy(assignment,save_a,sizeof(int)*nn);
            recompute();
            build_components();

            /* For each component: find min-critical var per clause, collect ALL */
            int to_flip[MAX_N]; memset(to_flip,0,sizeof(int)*nn);
            for(int cid=0;cid<n_components;cid++){
                for(int k=0;k<comp_size[cid];k++){
                    int uci=comp_clauses[cid][k];
                    int mc=nn+1,mv=-1;
                    for(int j=0;j<3;j++){int v=cl_var[uci][j];
                        int c=get_critical(v);if(c<mc){mc=c;mv=v;}}
                    if(mv>=0)to_flip[mv]=1;}}

            for(int v=0;v<nn;v++)if(to_flip[v])flip_var(v);
            int simul_unsat=count_unsat();
            if(simul_unsat==0) sum_simul_solved++;

            /* Restore for next instance */
            memcpy(assignment,save_a,sizeof(int)*nn);
            recompute();
        }

        if(n_inst>0){
            printf("n=%4d (%d inst):\n",nn,n_inst);
            printf("  Avg unsat:       %.1f\n",sum_unsat/n_inst);
            printf("  Avg components:  %.1f\n",sum_n_comp/n_inst);
            printf("  Interference per component: %.2f "
                   "(0=independent, >0=interferes)\n",sum_interference/n_inst);
            printf("  Sequential fix reduces unsat by: %.1f\n",sum_fixed_by_seq/n_inst);
            printf("  Seq fully solved: %.0f/%d\n",sum_seq_solved,n_inst);
            printf("  Simul fully solved: %.0f/%d\n",sum_simul_solved,n_inst);
            printf("\n");
        }
        fflush(stdout);
    }
    return 0;
}
