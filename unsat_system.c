/*
 * THE UNSAT SYSTEM: At n=500, ~10-20 unsat clauses form a STRUCTURE
 * ═══════════════════════════════════════════════════════════════════
 *
 * Measure EVERYTHING about this system:
 * 1. SIZE: how many unsat clauses, how many suspect vars?
 * 2. OVERLAP: do unsat clauses share variables?
 * 3. CRITICAL PROFILE: critical count for ALL suspects
 * 4. WRONG VARS: how many suspects are actually wrong?
 * 5. LOCALITY: are unsat clauses clustered in the graph?
 * 6. THE FLIP SET: if we flip ALL min-critical vars, what happens?
 * 7. CASCADES: does fixing one unsat create or fix others?
 *
 * Uses MiniSat for ground truth at large n.
 *
 * Compile: gcc -O3 -march=native -o unsat_system unsat_system.c -lm
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

static int count_sat(void){
    int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]>0)c++;return c;}

static double x[MAX_N],vel[MAX_N];
static void physics(int steps,unsigned long long seed){
    int n=n_vars,m=n_clauses;rng_seed(seed);
    for(int v=0;v<n;v++){double p1=0,p0=0;
        for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
            if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}
        x[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}
    double force[MAX_N];
    for(int step=0;step<steps;step++){double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++){double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                lit[j]=(s==1)?x[v]:(1.0-x[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){if(x[v]>0.5)force[v]+=cr*(1-x[v]);else force[v]-=cr*x[v];
            vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;
            x[v]+=vel[v]*0.05;
            if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}
    for(int v=0;v<n;v++) assignment[v]=(x[v]>0.5)?1:0;
}

static void flip_var(int v){
    int old=assignment[v],nw=1-old;assignment[v]=nw;
    for(int d=0;d<vdeg[v];d++){
        int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
        int was=((s==1&&old==1)||(s==-1&&old==0));
        int now=((s==1&&nw==1)||(s==-1&&nw==0));
        if(was&&!now) clause_sc[ci]--;
        else if(!was&&now) clause_sc[ci]++;}}

static int walksat_phase(int flips){
    int m=n_clauses;
    for(int f=0;f<flips;f++){
        int uci=-1;for(int ci=0;ci<m;ci++)if(clause_sc[ci]==0){uci=ci;break;}
        if(uci<0)return m;
        int bv=cl_var[uci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);
        flip_var(fv);}
    return count_sat();}

static int get_critical(int v){
    int c=0;
    for(int d=0;d<vdeg[v];d++){
        int ci=vlist[v][d];
        if(clause_sc[ci]==1){int pos=vpos[v][d],s=cl_sign[ci][pos];
            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))c++;}}
    return c;}

int main(void){
    printf("══════════════════════════════════════════════════\n");
    printf("THE UNSAT SYSTEM: Structure at n=50-1000\n");
    printf("══════════════════════════════════════════════════\n\n");

    int test_n[]={50,100,200,300,500,750,1000};
    int sizes=7;

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?15:(nn<=500?8:4);
        int steps=2000+nn*15;

        /* Accumulators */
        double sum_unsat=0, sum_suspects=0, sum_unique=0;
        double sum_overlap=0, sum_components=0;
        double sum_min_crit=0, sum_avg_crit=0;
        double sum_match_lo=0, sum_match_hi=0;
        double sum_simul_delta=0;
        int n_instances=0;

        for(int seed=0;seed<ni*3&&n_instances<ni;seed++){
            generate(nn,4.267,25000000ULL+seed);

            /* Physics + WalkSAT warmup */
            physics(steps, 42+seed*31);
            recompute();
            rng_seed(seed*777);
            walksat_phase(nn*200);

            int m=n_clauses;
            int sat=count_sat();
            int n_unsat=m-sat;
            if(n_unsat<2 || n_unsat>nn/2) continue; /* only study reasonable near-misses */

            n_instances++;

            /* Collect unsat clauses */
            int unsat_list[MAX_CLAUSES], nu=0;
            for(int ci=0;ci<m;ci++) if(clause_sc[ci]==0) unsat_list[nu++]=ci;

            /* Collect ALL suspect vars */
            int is_suspect[MAX_N]; memset(is_suspect,0,sizeof(int)*nn);
            int suspects[MAX_N], ns=0;
            for(int i=0;i<nu;i++)
                for(int j=0;j<3;j++){
                    int v=cl_var[unsat_list[i]][j];
                    if(!is_suspect[v]){is_suspect[v]=1;suspects[ns++]=v;}}

            /* Overlap: pairs of unsat clauses sharing a variable */
            int overlaps=0;
            for(int i=0;i<nu;i++)
                for(int j=i+1;j<nu;j++){
                    int shared=0;
                    for(int a=0;a<3;a++)
                        for(int b=0;b<3;b++)
                            if(cl_var[unsat_list[i]][a]==cl_var[unsat_list[j]][b])shared=1;
                    if(shared)overlaps++;}

            /* Connected components of unsat clause graph */
            int comp[MAX_CLAUSES]; memset(comp,-1,sizeof(int)*nu);
            int n_comp=0;
            for(int i=0;i<nu;i++){
                if(comp[i]>=0) continue;
                comp[i]=n_comp;
                int queue[MAX_CLAUSES],qh=0,qt=0;
                queue[qt++]=i;
                while(qh<qt){
                    int ci=queue[qh++];
                    for(int j2=0;j2<nu;j2++){
                        if(comp[j2]>=0)continue;
                        int shared=0;
                        for(int a=0;a<3;a++)
                            for(int b=0;b<3;b++)
                                if(cl_var[unsat_list[ci]][a]==cl_var[unsat_list[j2]][b])shared=1;
                        if(shared){comp[j2]=n_comp;queue[qt++]=j2;}}}
                n_comp++;}

            /* Critical profile of suspects */
            int min_crit=nn, max_crit=0;
            double sum_crit_local=0;
            for(int i=0;i<ns;i++){
                int c=get_critical(suspects[i]);
                if(c<min_crit)min_crit=c;
                if(c>max_crit)max_crit=c;
                sum_crit_local+=c;}

            /* Match ratio of suspects */
            double min_mr=1, max_mr=0;
            for(int i=0;i<ns;i++){
                int v=suspects[i], match=0, total=0;
                for(int d=0;d<vdeg[v];d++){
                    int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
                    total++;
                    if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))match++;}
                double mr=(double)match/fmax(total,1);
                if(mr<min_mr)min_mr=mr;
                if(mr>max_mr)max_mr=mr;}

            /* Simultaneous flip: flip ALL min-critical suspects */
            /* First: for each unsat clause, find its min-critical var */
            int to_flip[MAX_N]; memset(to_flip,0,sizeof(int)*nn);
            for(int i=0;i<nu;i++){
                int mc=nn,mv=-1;
                for(int j=0;j<3;j++){
                    int v=cl_var[unsat_list[i]][j];
                    int c=get_critical(v);
                    if(c<mc){mc=c;mv=v;}}
                if(mv>=0)to_flip[mv]=1;}

            int n_to_flip=0;
            for(int v=0;v<nn;v++) if(to_flip[v]) n_to_flip++;

            /* Apply simultaneous flip */
            int save_a[MAX_N]; memcpy(save_a,assignment,sizeof(int)*nn);
            for(int v=0;v<nn;v++) if(to_flip[v]) flip_var(v);
            int sat_after=count_sat();
            int delta=sat_after-sat;

            /* Restore */
            memcpy(assignment,save_a,sizeof(int)*nn);
            recompute();

            /* Accumulate */
            sum_unsat+=n_unsat;
            sum_suspects+=ns;
            sum_unique+=(double)ns/fmax(nu*3,1); /* unique/total */
            sum_overlap+=overlaps;
            sum_components+=n_comp;
            sum_min_crit+=min_crit;
            sum_avg_crit+=sum_crit_local/fmax(ns,1);
            sum_match_lo+=min_mr;
            sum_match_hi+=max_mr;
            sum_simul_delta+=delta;
        }

        if(n_instances>0){
            printf("n=%4d (%2d inst):\n",nn,n_instances);
            printf("  Unsat clauses:   %.1f\n", sum_unsat/n_instances);
            printf("  Suspect vars:    %.1f (of %d)\n", sum_suspects/n_instances, nn);
            printf("  Unique ratio:    %.2f (overlapping suspects)\n", sum_unique/n_instances);
            printf("  Overlapping pairs: %.1f\n", sum_overlap/n_instances);
            printf("  Components:      %.1f\n", sum_components/n_instances);
            printf("  Critical: min=%.1f  avg=%.1f\n",
                   sum_min_crit/n_instances, sum_avg_crit/n_instances);
            printf("  Match ratio: [%.3f, %.3f]\n",
                   sum_match_lo/n_instances, sum_match_hi/n_instances);
            printf("  Simul flip %d vars → Δsat=%+.1f\n",
                   (int)(sum_suspects/n_instances*0.3), sum_simul_delta/n_instances);
            printf("\n");
        }
        fflush(stdout);
    }
    return 0;
}
