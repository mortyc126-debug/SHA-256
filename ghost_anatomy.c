/*
 * GHOST ANATOMY: What ARE the ghost clusters? What's inside?
 * ═══════════════════════════════════════════════════════════
 *
 * At n=500: ghost clusters are too large (>12 vars) for brute force.
 * WHY are they large? What holds them together?
 *
 * Study:
 * 1. CLUSTER SIZE DISTRIBUTION: power law? normal? fixed?
 * 2. WHAT BINDS clusters: shared clauses? shared vars? topology?
 * 3. INTERNAL STRUCTURE: is a large cluster = chain of small ones?
 * 4. SOLUTION WITHIN CLUSTER: does the correct combo have a pattern?
 * 5. CAN WE PREDICT the correct combo without enumeration?
 * 6. PRE-PHYSICS: can we see ghosts BEFORE running physics?
 *    (from instance structure alone)
 *
 * Compile: gcc -O3 -march=native -o ghost_anat ghost_anatomy.c -lm
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
#define N_RUNS     5

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
    printf("═══════════════════════════════════════\n");
    printf("GHOST ANATOMY: Inside the clusters\n");
    printf("═══════════════════════════════════════\n\n");

    int test_n[]={200, 500};

    for(int ti=0;ti<2;ti++){
        int nn=test_n[ti]; int steps=2000+nn*15;

        for(int seed=0;seed<20;seed++){
            generate(nn,4.267,38000000ULL+seed);

            /* Multi-run */
            int run_a[N_RUNS][MAX_N];
            for(int r=0;r<N_RUNS;r++){
                physics(steps,42+r*7919+seed*31);
                memcpy(run_a[r],assignment,sizeof(int)*nn);}
            memcpy(assignment,run_a[0],sizeof(int)*nn);
            recompute();rng_seed(seed*777);
            walksat_phase(nn*200);

            int m=n_clauses,n=nn;
            int nu=count_unsat();
            if(nu<5)continue;

            /* Ghost detection */
            int is_ghost[MAX_N];memset(is_ghost,0,sizeof(int)*n);
            for(int ci=0;ci<m;ci++){if(clause_sc[ci]!=0)continue;
                for(int j=0;j<3;j++)is_ghost[cl_var[ci][j]]=1;}

            /* Also add high-disagreement vars */
            for(int v=0;v<n;v++){
                int dis=0;for(int r=1;r<N_RUNS;r++)if(run_a[r][v]!=assignment[v])dis++;
                if(dis>=N_RUNS/2)is_ghost[v]=1;}

            int ghosts[MAX_N],ng=0;
            for(int v=0;v<n;v++)if(is_ghost[v])ghosts[ng++]=v;

            /* Build clusters */
            int gc[MAX_N];memset(gc,-1,sizeof(int)*n);
            int clust_vars[200][100],clust_size[200];
            int nclust=0;
            memset(clust_size,0,sizeof(clust_size));

            for(int i=0;i<ng;i++){
                int v=ghosts[i];if(gc[v]>=0)continue;
                gc[v]=nclust;
                int q[MAX_N],qh=0,qt=0;q[qt++]=v;
                while(qh<qt){int u=q[qh++];
                    clust_vars[nclust][clust_size[nclust]++]=u;
                    if(clust_size[nclust]>=100)break;
                    for(int d=0;d<vdeg[u]&&d<30;d++){int ci=vlist[u][d];
                        for(int j=0;j<3;j++){int w=cl_var[ci][j];
                            if(is_ghost[w]&&gc[w]<0){gc[w]=nclust;q[qt++]=w;}}}}
                nclust++;
                if(nclust>=200)break;}

            printf("n=%d seed=%d: %d unsat, %d ghosts, %d clusters\n",nn,seed,nu,ng,nclust);

            /* ═══ 1. CLUSTER SIZE DISTRIBUTION ═══ */
            printf("\n  Size distribution:\n");
            int size_hist[50];memset(size_hist,0,sizeof(size_hist));
            int max_clust=0;
            for(int c=0;c<nclust;c++){
                int s=clust_size[c];if(s<50)size_hist[s]++;
                if(s>max_clust)max_clust=s;}
            for(int s=1;s<=max_clust&&s<50;s++){
                if(size_hist[s]==0)continue;
                printf("    size %2d: %d clusters ",s,size_hist[s]);
                for(int i=0;i<size_hist[s]&&i<30;i++)printf("█");printf("\n");}

            /* ═══ 2. INTERNAL STRUCTURE of largest cluster ═══ */
            int largest_c=0;
            for(int c=1;c<nclust;c++)if(clust_size[c]>clust_size[largest_c])largest_c=c;

            if(clust_size[largest_c]>=3){
                int lc_size=clust_size[largest_c];
                int*lc_vars=clust_vars[largest_c];

                printf("\n  Largest cluster (size=%d):\n",lc_size);

                /* How many unsat clauses are WITHIN this cluster? */
                int internal_unsat=0;
                for(int ci=0;ci<m;ci++){
                    if(clause_sc[ci]!=0)continue;
                    int in_clust=1;
                    for(int j=0;j<3;j++)if(gc[cl_var[ci][j]]!=largest_c)in_clust=0;
                    if(in_clust)internal_unsat++;}

                /* How is the cluster connected? Chain or mesh? */
                /* Count edges within cluster */
                int internal_edges=0;
                for(int i=0;i<lc_size;i++){int v=lc_vars[i];
                    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];
                        for(int j=0;j<3;j++){int w=cl_var[ci][j];
                            if(w!=v&&gc[w]==largest_c)internal_edges++;}}}
                internal_edges/=2;

                /* Diameter */
                int lc_is[MAX_N];memset(lc_is,0,sizeof(int)*n);
                for(int i=0;i<lc_size;i++)lc_is[lc_vars[i]]=1;
                int diameter=0;
                for(int start=0;start<lc_size&&start<3;start++){
                    int sv=lc_vars[start];
                    int dist[MAX_N];memset(dist,-1,sizeof(int)*n);dist[sv]=0;
                    int q[MAX_N],qh=0,qt=0;q[qt++]=sv;
                    while(qh<qt){int u=q[qh++];
                        for(int d=0;d<vdeg[u];d++){int ci=vlist[u][d];
                            for(int j=0;j<3;j++){int w=cl_var[ci][j];
                                if(lc_is[w]&&dist[w]<0){dist[w]=dist[u]+1;q[qt++]=w;
                                    if(dist[w]>diameter)diameter=dist[w];}}}}}

                printf("    Internal unsat: %d\n",internal_unsat);
                printf("    Internal edges: %d\n",internal_edges);
                printf("    Diameter: %d\n",diameter);
                printf("    Structure: %s\n",
                       diameter>=lc_size/2?"CHAIN":"MESH");

                /* ═══ 3. CAN we predict the correct flip combo? ═══ */
                /* For each var in cluster: what does multi-run MAJORITY say? */
                printf("\n    Per-var multi-run vote:\n");
                int majority_agrees=0, majority_disagrees=0;
                for(int i=0;i<lc_size&&i<20;i++){
                    int v=lc_vars[i];
                    int sum_runs=0;
                    for(int r=0;r<N_RUNS;r++)sum_runs+=run_a[r][v];
                    double p1=(double)sum_runs/N_RUNS;
                    int majority_val=(p1>0.5)?1:0;
                    int cur=assignment[v];

                    /* Counterfactual */
                    int ta[MAX_N];memcpy(ta,assignment,sizeof(int)*n);
                    ta[v]=1-ta[v]; int cf=eval_a(ta)-eval_a(assignment);

                    int would_flip=(majority_val!=cur);
                    printf("      x%d: cur=%d, majority=%.0f%%(→%d), cf=%+d %s\n",
                           v,cur,100*p1,majority_val,cf,
                           would_flip?"← FLIP":"  keep");
                    if(would_flip)majority_disagrees++;
                    else majority_agrees++;}

                printf("    Majority vote suggests flip: %d/%d vars\n",
                       majority_disagrees,majority_agrees+majority_disagrees);

                /* ═══ 4. Try majority-vote combo on this cluster ═══ */
                int save_a[MAX_N];memcpy(save_a,assignment,sizeof(int)*n);
                int before=count_unsat();

                for(int i=0;i<lc_size;i++){
                    int v=lc_vars[i];
                    int sum_runs=0;
                    for(int r=0;r<N_RUNS;r++)sum_runs+=run_a[r][v];
                    int majority_val=(sum_runs*2>N_RUNS)?1:0;
                    if(majority_val!=assignment[v])flip_var(v);}
                recompute();
                int after=count_unsat();

                printf("\n    Majority-vote flip: %d unsat → %d (Δ=%+d)\n",
                       before,after,before-after);

                memcpy(assignment,save_a,sizeof(int)*n);recompute();

                /* ═══ 5. Try INVERSE of current (since all-3-wrong) ═══ */
                for(int i=0;i<lc_size;i++)flip_var(lc_vars[i]);
                recompute();
                int after_inv=count_unsat();
                printf("    Full inversion:    %d unsat → %d (Δ=%+d)\n",
                       before,after_inv,before-after_inv);

                memcpy(assignment,save_a,sizeof(int)*n);recompute();

                /* ═══ 6. Try counterfactual-guided: flip vars with cf > 0 ═══ */
                int n_cf_flip=0;
                for(int i=0;i<lc_size;i++){
                    int v=lc_vars[i];
                    int ta2[MAX_N];memcpy(ta2,assignment,sizeof(int)*n);
                    ta2[v]=1-ta2[v];int cf=eval_a(ta2)-eval_a(assignment);
                    if(cf>=0){flip_var(v);n_cf_flip++;}}
                recompute();
                int after_cf=count_unsat();
                printf("    CF-guided flip (%d vars): %d → %d (Δ=%+d)\n",
                       n_cf_flip,before,after_cf,before-after_cf);

                memcpy(assignment,save_a,sizeof(int)*n);recompute();
            }

            printf("\n");
            break;
        }
    }
    return 0;
}
