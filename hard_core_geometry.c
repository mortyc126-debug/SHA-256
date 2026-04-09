/*
 * HARD CORE GEOMETRY: What space does the absolute hard core live in?
 * ═══════════════════════════════════════════════════════════════════
 *
 * After 1-hop bypass: ~65% of unsat clauses remain.
 * No single flip helps. These need multi-flip.
 *
 * What IS this object? Measurements:
 *
 * 1. DIMENSION: How many vars are involved? (effective DOF of the hard core)
 * 2. CONNECTIVITY: How connected is the hard core internally?
 * 3. DISTANCE to solution: How many bits are wrong in the hard core?
 * 4. MINIMUM MULTI-FLIP: What's the smallest set of simultaneous flips?
 * 5. EIGENSTRUCTURE: SVD/spectrum of the hard core subproblem
 * 6. SOLUTION DENSITY: How many solutions exist near the current assignment?
 * 7. LANDSCAPE: What does the energy surface look like around the hard core?
 * 8. EMBEDDING: Where in the FULL instance does the hard core sit?
 *
 * Compile: gcc -O3 -march=native -o hard_geom hard_core_geometry.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

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

/* Exhaust 1-hop bypass */
static void exhaust_1hop(void){
    int improved=1;
    while(improved){improved=0;
        for(int ci=0;ci<n_clauses;ci++){
            if(clause_sc[ci]!=0)continue;
            /* Try each var in this clause and its 1-hop neighbors */
            for(int j=0;j<3;j++){int u=cl_var[ci][j];
                for(int d=0;d<vdeg[u]&&d<30;d++){
                    int ci2=vlist[u][d];
                    for(int j2=0;j2<3;j2++){
                        int v=cl_var[ci2][j2];
                        int nv=1-assignment[v],fixes=0,breaks=0;
                        for(int dd=0;dd<vdeg[v];dd++){
                            int cci=vlist[v][dd],cpos=vpos[v][dd],cs=cl_sign[cci][cpos];
                            if(clause_sc[cci]==0){if((cs==1&&nv==1)||(cs==-1&&nv==0))fixes++;}
                            else if(clause_sc[cci]==1){if((cs==1&&assignment[v]==1)||(cs==-1&&assignment[v]==0))breaks++;}}
                        if(fixes>breaks){flip_var(v);improved=1;goto next_clause;}}}}
            next_clause:;
        }
    }
}

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("HARD CORE GEOMETRY: Dimension, Shape, Depth\n");
    printf("═══════════════════════════════════════════\n\n");

    int test_n[]={100, 200, 500};

    for(int ti=0;ti<3;ti++){
        int nn=test_n[ti]; int steps=2000+nn*15;

        double sum_hc_clauses=0, sum_hc_vars=0, sum_hc_components=0;
        double sum_hc_density=0, sum_hc_diameter=0;
        double sum_min_multiflip=0;
        int n_inst=0;

        for(int seed=0;seed<30&&n_inst<6;seed++){
            generate(nn,4.267,32000000ULL+seed);
            physics(steps,42+seed*31);
            recompute();
            rng_seed(seed*777);
            walksat_phase(nn*200);

            int init_unsat=count_unsat();
            if(init_unsat<3)continue;

            /* Exhaust 1-hop bypass */
            exhaust_1hop();
            int hc_unsat=count_unsat();
            if(hc_unsat<2)continue;
            n_inst++;

            /* ═══ 1. DIMENSION: vars in hard core ═══ */
            int is_hc_var[MAX_N]; memset(is_hc_var,0,sizeof(int)*nn);
            int hc_vars[MAX_N], nhv=0;
            int hc_clauses[MAX_CLAUSES], nhc=0;

            for(int ci=0;ci<n_clauses;ci++){
                if(clause_sc[ci]!=0)continue;
                hc_clauses[nhc++]=ci;
                for(int j=0;j<3;j++){
                    int v=cl_var[ci][j];
                    if(!is_hc_var[v]){is_hc_var[v]=1;hc_vars[nhv++]=v;}}}

            /* ═══ 2. CONNECTIVITY: components within hard core ═══ */
            int comp[MAX_CLAUSES]; memset(comp,-1,sizeof(int)*nhc);
            int ncomp=0;
            for(int i=0;i<nhc;i++){
                if(comp[i]>=0)continue;
                comp[i]=ncomp;
                int q[MAX_CLAUSES],qh=0,qt=0;q[qt++]=i;
                while(qh<qt){int ci=hc_clauses[q[qh++]];
                    for(int i2=0;i2<nhc;i2++){if(comp[i2]>=0)continue;
                        int sh=0;
                        for(int a=0;a<3;a++)for(int b=0;b<3;b++)
                            if(cl_var[ci][a]==cl_var[hc_clauses[i2]][b])sh=1;
                        if(sh){comp[i2]=ncomp;q[qt++]=i2;}}}
                ncomp++;}

            /* ═══ 3. DENSITY: clauses per var in hard core ═══ */
            double density = (nhv>0)?(double)nhc/nhv:0;

            /* ═══ 4. DIAMETER of hard core graph ═══ */
            /* BFS within hard core vars */
            int hc_adj[MAX_N][30], hc_adj_n[MAX_N];
            memset(hc_adj_n,0,sizeof(int)*nn);
            for(int i=0;i<nhc;i++){
                int ci=hc_clauses[i];
                for(int a=0;a<3;a++)for(int b=a+1;b<3;b++){
                    int va=cl_var[ci][a],vb=cl_var[ci][b];
                    if(is_hc_var[va]&&is_hc_var[vb]){
                        if(hc_adj_n[va]<30)hc_adj[va][hc_adj_n[va]++]=vb;
                        if(hc_adj_n[vb]<30)hc_adj[vb][hc_adj_n[vb]++]=va;}}}

            int diameter=0;
            for(int start_i=0;start_i<nhv&&start_i<5;start_i++){
                int sv=hc_vars[start_i];
                int dist[MAX_N]; memset(dist,-1,sizeof(int)*nn);
                dist[sv]=0;int q[MAX_N],qh=0,qt=0;q[qt++]=sv;
                while(qh<qt){int u=q[qh++];
                    for(int d=0;d<hc_adj_n[u];d++){int w=hc_adj[u][d];
                        if(dist[w]<0){dist[w]=dist[u]+1;q[qt++]=w;
                            if(dist[w]>diameter)diameter=dist[w];}}}
            }

            /* ═══ 5. MINIMUM MULTI-FLIP: try all 2-flips ═══ */
            int best_2flip_net=-999;
            int best_v1=-1,best_v2=-1;
            /* Only try pairs within hard core (nhv vars, nhv^2 pairs) */
            int pairs_tried=0;
            for(int i=0;i<nhv&&pairs_tried<5000;i++){
                for(int j=i+1;j<nhv&&pairs_tried<5000;j++){
                    int v1=hc_vars[i],v2=hc_vars[j];
                    /* Compute net of flipping v1 AND v2 simultaneously */
                    int before=count_unsat();
                    flip_var(v1);flip_var(v2);
                    int after=count_unsat();
                    flip_var(v2);flip_var(v1); /* undo */
                    int net=before-after;
                    if(net>best_2flip_net){best_2flip_net=net;best_v1=v1;best_v2=v2;}
                    pairs_tried++;}}

            sum_hc_clauses+=nhc;
            sum_hc_vars+=nhv;
            sum_hc_components+=ncomp;
            sum_hc_density+=density;
            sum_hc_diameter+=diameter;
            sum_min_multiflip+=best_2flip_net;

            printf("n=%d seed=%d: init=%d → 1hop→%d (hard core)\n",nn,seed,init_unsat,hc_unsat);
            printf("  HC clauses: %d, HC vars: %d, components: %d\n",nhc,nhv,ncomp);
            printf("  Density: %.2f cls/var, diameter: %d\n",density,diameter);
            printf("  Best 2-flip: net=%+d (x%d,x%d) from %d pairs\n",
                   best_2flip_net,best_v1,best_v2,pairs_tried);
            if(best_2flip_net>0)
                printf("  → 2-FLIP EXISTS that improves! (%+d)\n",best_2flip_net);
            else
                printf("  → No 2-flip improves either\n");
            printf("\n");
        }

        if(n_inst>0){
            printf("n=%d AVERAGES (%d inst):\n",nn,n_inst);
            printf("  HC clauses: %.1f, HC vars: %.1f (%.1f%% of n)\n",
                   sum_hc_clauses/n_inst,sum_hc_vars/n_inst,
                   100*sum_hc_vars/(n_inst*nn));
            printf("  Components: %.1f, Density: %.2f, Diameter: %.1f\n",
                   sum_hc_components/n_inst,sum_hc_density/n_inst,
                   sum_hc_diameter/n_inst);
            printf("  Best 2-flip net: %+.1f\n\n",sum_min_multiflip/n_inst);
        }
    }
    return 0;
}
