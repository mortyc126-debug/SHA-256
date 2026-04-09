/*
 * GHOST HUNTER: Combine ALL signals to find and fix HC vars
 * ═══════════════════════════════════════════════════════════
 *
 * Everything we know in one solver:
 *
 * Phase 1: Physics × 5 runs → multi-reality map
 * Phase 2: WalkSAT warmup on best run
 * Phase 3: For EVERY var compute:
 *          - counterfactual Δsat (flip cost)
 *          - multi-run disagreement
 *          - match_ratio
 *          Combined score → rank vars by "ghostliness"
 * Phase 4: Top ghosts grouped into clusters (shared clauses)
 * Phase 5: Per cluster (2-5 vars): try all 2^k combos
 * Phase 6: Accept combo that improves sat, repeat
 *
 * Compile: gcc -O3 -march=native -o ghost_hunter ghost_hunter.c -lm
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

static int ghost_solve(int nn){
    int n=nn, m=n_clauses;
    int steps=2000+n*15;

    /* ═══ Phase 1: Multi-reality physics ═══ */
    int run_a[N_RUNS][MAX_N];
    int best_run=0, best_sat=0;
    for(int r=0;r<N_RUNS;r++){
        physics(steps, 42+r*7919);
        memcpy(run_a[r],assignment,sizeof(int)*n);
        recompute();
        int s=m-count_unsat();
        if(s>best_sat){best_sat=s;best_run=r;}
    }

    /* ═══ Phase 2: WalkSAT warmup on best run ═══ */
    memcpy(assignment,run_a[best_run],sizeof(int)*n);
    recompute();
    rng_seed(12345);
    walksat_phase(n*300);
    if(count_unsat()==0) return 1;

    /* ═══ Phase 3: Ghost score for every var ═══ */
    double ghost_score[MAX_N];
    for(int v=0;v<n;v++){
        /* Signal A: counterfactual Δsat */
        int ta[MAX_N];memcpy(ta,assignment,sizeof(int)*n);
        ta[v]=1-ta[v];
        double cf_delta=(double)(eval_a(ta)-eval_a(assignment));
        /* Normalize: smaller |delta| = more ghostly */
        double ghost_cf = 1.0/(1.0+fabs(cf_delta));

        /* Signal B: multi-run disagreement */
        int disagree=0;
        for(int r=0;r<N_RUNS;r++)
            if(run_a[r][v]!=assignment[v])disagree++;
        double ghost_dis=(double)disagree/N_RUNS;

        /* Signal C: match_ratio < 0.5 */
        int match=0,total=0;
        for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
            total++;if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))match++;}
        double mr=total>0?(double)match/total:0.5;
        double ghost_mr=(mr<0.5)?(0.5-mr)*4:0; /* 0 if mr>0.5, up to 1 if mr=0.25 */

        /* Combined: weighted sum */
        ghost_score[v] = 0.5*ghost_cf + 0.3*ghost_dis + 0.2*ghost_mr;
    }

    /* ═══ Phase 4: Find ghost clusters ═══ */
    /* Sort vars by ghost score descending */
    int sorted[MAX_N];
    for(int v=0;v<n;v++)sorted[v]=v;
    for(int i=0;i<n-1&&i<200;i++)
        for(int j=i+1;j<n;j++)
            if(ghost_score[sorted[j]]>ghost_score[sorted[i]])
                {int t=sorted[i];sorted[i]=sorted[j];sorted[j]=t;}

    /* Take top ghosts (those in unsat clauses + high score) */
    int is_ghost[MAX_N];memset(is_ghost,0,sizeof(int)*n);
    /* First: all vars in unsat clauses */
    for(int ci=0;ci<m;ci++){if(clause_sc[ci]!=0)continue;
        for(int j=0;j<3;j++)is_ghost[cl_var[ci][j]]=1;}
    /* Add high-score vars */
    for(int i=0;i<n&&i<n/5;i++)
        if(ghost_score[sorted[i]]>0.4)is_ghost[sorted[i]]=1;

    int ghosts[MAX_N],ng=0;
    for(int v=0;v<n;v++)if(is_ghost[v])ghosts[ng++]=v;

    /* Build ghost clusters (connected via shared clauses) */
    int gc[MAX_N]; memset(gc,-1,sizeof(int)*n);
    int nclust=0;
    for(int i=0;i<ng;i++){
        int v=ghosts[i];if(gc[v]>=0)continue;
        gc[v]=nclust;
        /* BFS within ghosts */
        int q[MAX_N],qh=0,qt=0;q[qt++]=v;
        while(qh<qt){int u=q[qh++];
            for(int d=0;d<vdeg[u];d++){int ci=vlist[u][d];
                for(int j=0;j<3;j++){int w=cl_var[ci][j];
                    if(is_ghost[w]&&gc[w]<0){gc[w]=nclust;q[qt++]=w;}}}}
        nclust++;
    }

    /* ═══ Phase 5: Per cluster enumeration ═══ */
    int save_a[MAX_N];memcpy(save_a,assignment,sizeof(int)*n);
    int total_improved=0;

    for(int c=0;c<nclust;c++){
        /* Collect vars in this cluster */
        int cv[MAX_N],ncv=0;
        for(int i=0;i<ng;i++)if(gc[ghosts[i]]==c)cv[ncv++]=ghosts[i];

        if(ncv>12)ncv=12; /* cap cluster size for speed */

        /* Try all 2^ncv combos, find best */
        int best_mask=0, best_delta=-999;
        int before_sat=eval_a(assignment);

        for(int mask=1;mask<(1<<ncv);mask++){
            int ta[MAX_N];memcpy(ta,assignment,sizeof(int)*n);
            for(int i=0;i<ncv;i++)
                if(mask&(1<<i))ta[cv[i]]=1-ta[cv[i]];
            int after=eval_a(ta);
            int delta=after-before_sat;
            if(delta>best_delta){best_delta=delta;best_mask=mask;}
        }

        /* Apply best combo if it improves */
        if(best_delta>0){
            for(int i=0;i<ncv;i++)
                if(best_mask&(1<<i))flip_var(cv[i]);
            recompute();
            total_improved+=best_delta;
        }
    }

    if(count_unsat()==0) return 2;

    /* ═══ Phase 6: Final WalkSAT polish ═══ */
    rng_seed(99999);
    walksat_phase(n*500);
    if(count_unsat()==0) return 3;

    return 0;
}

int main(void){
    printf("═══════════════════════════════════════\n");
    printf("GHOST HUNTER: All signals combined\n");
    printf("═══════════════════════════════════════\n\n");

    int test_n[]={50,100,200,300,500,750,1000,1500};
    int sizes=8;

    printf("%6s | %5s | %6s | %8s\n","n","total","solved","time_ms");
    printf("-------+-------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?20:(nn<=500?10:5);
        int solved=0,total=0;
        double tms=0;

        for(int seed=0;seed<ni*5&&total<ni;seed++){
            generate(nn,4.267,37000000ULL+seed);
            clock_t t0=clock();
            int r=ghost_solve(nn);
            clock_t t1=clock();
            tms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
            total++;
            if(r>0)solved++;
        }

        printf("%6d | %2d/%2d | %4d   | %7.0fms\n",nn,total,total,solved,tms/total);
        fflush(stdout);
    }

    printf("\nPrevious bests:\n");
    printf("  PhysicsSAT:    4/20@500, 1/10@750\n");
    printf("  SP (correct):  2/10@500, 2/5@750\n");
    return 0;
}
