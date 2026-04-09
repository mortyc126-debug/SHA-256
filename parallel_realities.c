/*
 * PARALLEL REALITIES: Hard core seen from dimensions we haven't tried
 * ═══════════════════════════════════════════════════════════════════
 *
 * Reality 1: Single assignment → HC nearly invisible (we proved this)
 *
 * NEW dimensions:
 *
 * A. MULTI-RUN: Run physics 20 times → at each var, measure VARIANCE
 *    across runs. HC vars might be MORE variable (unstable) or LESS.
 *
 * B. COUNTERFACTUAL: For each var, ask "what if it were different?"
 *    Compare: current satisfaction vs counterfactual satisfaction.
 *    HC vars: counterfactual might be BETTER (they're wrong).
 *
 * C. RELATIVE: Not absolute properties but RELATIVE to neighbors.
 *    Is HC var different from its NEIGHBORS in a unique way?
 *
 * D. TEMPORAL DERIVATIVE: Not x(t) but dx/dt at final state.
 *    The velocity/acceleration at the MOMENT of freezing.
 *
 * E. ENTROPY OF CLAUSE NEIGHBORHOOD: How much uncertainty
 *    remains in the clauses AROUND each var?
 *
 * F. ENERGY GRADIENT: If we compute continuous energy at x,
 *    what direction does the gradient point for HC vars?
 *
 * G. CROSS-REALITY CORRELATION: Between two different physics runs,
 *    do HC vars show DIFFERENT correlation patterns than non-HC?
 *
 * Compile: gcc -O3 -march=native -o parallel parallel_realities.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      1000
#define MAX_CLAUSES 5000
#define MAX_K      3
#define MAX_DEGREE 100
#define N_RUNS     20

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
    printf("═══════════════════════════════════════════\n");
    printf("PARALLEL REALITIES: Hidden dimensions\n");
    printf("═══════════════════════════════════════════\n\n");

    int nn=200;
    for(int seed=0;seed<30;seed++){
        generate(nn,4.267,36000000ULL+seed);
        int m=n_clauses,n=n_vars;

        /* ═══ A. MULTI-RUN: variance across N_RUNS physics runs ═══ */
        double run_vals[N_RUNS][MAX_N]; /* final x per run */
        int run_assign[N_RUNS][MAX_N];

        for(int r=0;r<N_RUNS;r++){
            physics(2000+nn*15, 42+seed*31+r*7919);
            memcpy(run_vals[r],x_cont,sizeof(double)*n);
            memcpy(run_assign[r],assignment,sizeof(int)*n);
        }

        /* Use run 0 as primary, do WalkSAT on it */
        memcpy(assignment,run_assign[0],sizeof(int)*n);
        recompute();
        rng_seed(seed*777);
        walksat_phase(nn*200);
        int nu=count_unsat();
        if(nu<3)continue;

        /* Identify HC from primary run */
        int is_hc[MAX_N];memset(is_hc,0,sizeof(int)*n);
        int nhv=0;
        for(int ci=0;ci<m;ci++){if(clause_sc[ci]!=0)continue;
            for(int j=0;j<3;j++){int v=cl_var[ci][j];if(!is_hc[v]){is_hc[v]=1;nhv++;}}}

        printf("n=%d seed=%d: %d unsat, %d HC vars\n\n",nn,seed,nu,nhv);

        /* Per-var multi-run measurements */
        double hc_variance=0,ot_variance=0;
        double hc_disagreement=0,ot_disagreement=0;
        double hc_run_entropy=0,ot_run_entropy=0;
        double hc_counterfactual=0,ot_counterfactual=0;
        double hc_neighbor_diff=0,ot_neighbor_diff=0;
        double hc_energy_grad=0,ot_energy_grad=0;
        double hc_cross_corr=0,ot_cross_corr=0;
        int hc_n=0,ot_n=0;

        for(int v=0;v<n;v++){
            /* A. Variance across runs */
            double mean=0;
            for(int r=0;r<N_RUNS;r++)mean+=run_vals[r][v];
            mean/=N_RUNS;
            double var=0;
            for(int r=0;r<N_RUNS;r++){double d=run_vals[r][v]-mean;var+=d*d;}
            var/=N_RUNS;

            /* A2. Disagreement: fraction of runs that disagree with primary */
            int disagree=0;
            for(int r=1;r<N_RUNS;r++)
                if(run_assign[r][v]!=assignment[v])disagree++;
            double disagree_frac=(double)disagree/(N_RUNS-1);

            /* A3. Run entropy: H(binary distribution across runs) */
            double p1_runs=0;
            for(int r=0;r<N_RUNS;r++)p1_runs+=run_assign[r][v];
            p1_runs/=N_RUNS;
            double rent=0;
            if(p1_runs>0.001&&p1_runs<0.999)
                rent=-p1_runs*log2(p1_runs)-(1-p1_runs)*log2(1-p1_runs);

            /* B. Counterfactual: if v were flipped, how many MORE clauses sat? */
            int a_test[MAX_N]; memcpy(a_test,assignment,sizeof(int)*n);
            a_test[v]=1-a_test[v];
            int cf_sat=eval_a(a_test);
            int cur_sat=eval_a(assignment);
            double cf_delta=(double)(cf_sat-cur_sat);

            /* C. Relative to neighbors: |value - mean(neighbor values)| */
            double nav=0; int nn_count=0;
            for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];
                for(int j=0;j<3;j++){int w=cl_var[ci][j];if(w!=v){
                    nav+=assignment[w];nn_count++;}}}
            if(nn_count>0)nav/=nn_count;
            double rel_diff=fabs(assignment[v]-nav);

            /* F. Energy gradient (soft): derivative of soft-sat w.r.t. x_v */
            double grad=0;
            for(int d=0;d<vdeg[v];d++){
                int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
                double lit[3],prod=1.0;
                for(int j=0;j<3;j++){int vv=cl_var[ci][j],ss=cl_sign[ci][j];
                    lit[j]=(ss==1)?x_cont[vv]:(1.0-x_cont[vv]);
                    double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
                double t=1.0-lit[pos];if(t<1e-12)t=1e-12;
                grad+=s*(prod/t);
            }

            /* G. Cross-reality correlation: does v's value correlate with
               the SATISFACTION of its clauses across runs? */
            double corr_sum=0;
            for(int r=0;r<N_RUNS;r++){
                /* In run r: how many of v's clauses are sat? */
                int vsat=0;
                for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];
                    int s2=0;for(int j=0;j<3;j++){int vv=cl_var[ci][j],ss=cl_sign[ci][j];
                        if((ss==1&&run_assign[r][vv]==1)||(ss==-1&&run_assign[r][vv]==0))s2=1;}
                    if(s2)vsat++;}
                corr_sum+=(run_assign[r][v]-0.5)*(vsat-vdeg[v]*0.875);
            }
            corr_sum/=N_RUNS;

            if(is_hc[v]){
                hc_variance+=var;hc_disagreement+=disagree_frac;
                hc_run_entropy+=rent;hc_counterfactual+=cf_delta;
                hc_neighbor_diff+=rel_diff;hc_energy_grad+=fabs(grad);
                hc_cross_corr+=corr_sum;hc_n++;
            }else{
                ot_variance+=var;ot_disagreement+=disagree_frac;
                ot_run_entropy+=rent;ot_counterfactual+=cf_delta;
                ot_neighbor_diff+=rel_diff;ot_energy_grad+=fabs(grad);
                ot_cross_corr+=corr_sum;ot_n++;
            }
        }

        /* Print results */
        printf("  %25s | %8s | %8s | %6s | %s\n","DIMENSION","HC","OTHER","RATIO","SIGNAL");
        printf("  ");for(int i=0;i<72;i++)printf("-");printf("\n");

        struct{char*name;double h,o;}rows[]={
            {"A. multi-run variance",hc_variance/fmax(hc_n,1),ot_variance/fmax(ot_n,1)},
            {"A2. run disagreement",hc_disagreement/fmax(hc_n,1),ot_disagreement/fmax(ot_n,1)},
            {"A3. run entropy",hc_run_entropy/fmax(hc_n,1),ot_run_entropy/fmax(ot_n,1)},
            {"B. counterfactual Δsat",hc_counterfactual/fmax(hc_n,1),ot_counterfactual/fmax(ot_n,1)},
            {"C. neighbor difference",hc_neighbor_diff/fmax(hc_n,1),ot_neighbor_diff/fmax(ot_n,1)},
            {"F. |energy gradient|",hc_energy_grad/fmax(hc_n,1),ot_energy_grad/fmax(ot_n,1)},
            {"G. cross-reality corr",hc_cross_corr/fmax(hc_n,1),ot_cross_corr/fmax(ot_n,1)},
        };
        int nrows=7;
        for(int i=0;i<nrows;i++){
            double r=(fabs(rows[i].o)>0.001)?rows[i].h/rows[i].o:
                     (fabs(rows[i].h)>0.001?999:1);
            char*sig="";
            if(fabs(r-1)>1.0||fabs(rows[i].h-rows[i].o)>0.1)sig="★★★ STRONG";
            else if(fabs(r-1)>0.5)sig="★★ moderate";
            else if(fabs(r-1)>0.15)sig="★ weak";
            printf("  %25s | %8.4f | %8.4f | %6.2f | %s\n",
                   rows[i].name,rows[i].h,rows[i].o,r,sig);
        }

        printf("\n");
        break;
    }
    return 0;
}
