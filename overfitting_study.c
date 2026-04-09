/*
 * OVERFITTING STUDY: Wrong vars are TOO WELL MATCHED locally.
 * ════════════════════════════════════════════════════════════
 *
 * Wrong (nearest): match_ratio = 0.655 (HIGH!)
 * Right (nearest): match_ratio = 0.540 (lower!)
 *
 * The wrong vars OVERFIT — they satisfy MORE local clause signs
 * than the correct vars. But they're globally wrong.
 *
 * STUDY:
 * 1. WHAT EXACTLY is overfit? Per-clause breakdown.
 * 2. LOCAL vs GLOBAL: Do wrong vars satisfy LOCAL clauses more?
 *    But break DISTANT clauses?
 * 3. TENSION vs NEAREST: Does tension point toward nearest or away?
 * 4. OVERFIT SCORE: Can we measure "overfittedness" per var?
 * 5. CAN WE DETECT overfit vars WITHOUT knowing the solution?
 * 6. WHAT DOES OVERFIT LOOK LIKE in continuous (physics) space?
 *
 * Compile: gcc -O3 -march=native -o overfit overfitting_study.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      20
#define MAX_CLAUSES 100
#define MAX_K      3
#define MAX_SOLUTIONS 10000

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){double u1=(rng_next()>>11)*(1.0/9007199254740992.0),u2=(rng_next()>>11)*(1.0/9007199254740992.0);if(u1<1e-15)u1=1e-15;return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);rng_seed(seed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;}}}

static int eval_a(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static int all_solutions[MAX_SOLUTIONS][MAX_N];
static int n_solutions;
static void find_all_solutions(int n){n_solutions=0;for(long long mask=0;mask<(1LL<<n)&&n_solutions<MAX_SOLUTIONS;mask++){int a[MAX_N];for(int v=0;v<n;v++)a[v]=(mask>>v)&1;if(eval_a(a)==n_clauses){memcpy(all_solutions[n_solutions],a,sizeof(int)*n);n_solutions++;}}}

static double x_cont[MAX_N];
static int assignment[MAX_N];
static void physics(int n,int steps,unsigned long long seed){rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.25*exp(-4*prog)+0.0001;double cr=3*prog;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0)x_cont[v]=0.01;if(x_cont[v]>1)x_cont[v]=0.99;}}for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

int main(void){
    printf("═══════════════════════════════════════\n");
    printf("OVERFITTING STUDY\n");
    printf("═══════════════════════════════════════\n\n");

    /* Accumulate for stats */
    double ow_match=0,or_match=0; int ow_n=0,or_n=0;
    double ow_tension_agree=0,or_tension_agree=0;
    double ow_neighbor_agree=0,or_neighbor_agree=0;
    double ow_clause_oversat=0,or_clause_oversat=0;
    double ow_x_confidence=0, or_x_confidence=0;
    double ow_degree=0, or_degree=0;
    double ow_tension_strength=0, or_tension_strength=0;
    double ow_clause_sat_count=0, or_clause_sat_count=0;

    for(int n=14;n<=16;n+=2){
        for(int seed=0;seed<500;seed++){
            generate(n,4.267,51000000ULL+seed);
            find_all_solutions(n);
            if(n_solutions<2)continue;

            physics(n,500,42+seed*31);
            int sat=eval_a(assignment);
            if(n_clauses-sat>n/3)continue;

            /* Find nearest */
            int min_h=n,ni=0;
            for(int si=0;si<n_solutions;si++){
                int h=0;for(int v=0;v<n;v++)if(assignment[v]!=all_solutions[si][v])h++;
                if(h<min_h){min_h=h;ni=si;}}
            if(min_h<1||min_h>n/2)continue;

            int *nearest=all_solutions[ni];

            /* Build adjacency */
            int adj[MAX_N][50],adj_n[MAX_N];
            memset(adj_n,0,sizeof(adj_n));
            for(int ci=0;ci<n_clauses;ci++)
                for(int a=0;a<3;a++)for(int b=a+1;b<3;b++){
                    int va=cl_var[ci][a],vb=cl_var[ci][b];
                    if(adj_n[va]<50)adj[va][adj_n[va]++]=vb;
                    if(adj_n[vb]<50)adj[vb][adj_n[vb]++]=va;}

            /* Per-var measurements */
            for(int v=0;v<n;v++){
                int is_wrong=(assignment[v]!=nearest[v]);

                /* 1. match_ratio */
                int match=0,total=0;
                for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                    if(cl_var[ci][j]==v){total++;int s=cl_sign[ci][j];
                        if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))match++;}
                double mr=total>0?(double)match/total:0.5;

                /* 2. Tension agreement with assignment */
                double p1=0,p0=0;
                for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                    if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}
                double tension=(p1+p0>0)?(p1-p0)/(p1+p0):0;
                double t_agree=(assignment[v]==1)?tension:-tension;

                /* 3. Neighbor agreement: do neighbors' values agree with v? */
                double n_agree=0;int nn2=0;
                for(int d=0;d<adj_n[v];d++){int u=adj[v][d];
                    /* For each clause containing both v and u:
                       does the combo (assignment[v], assignment[u]) satisfy it? */
                    for(int ci=0;ci<n_clauses;ci++){
                        int has_v=0,has_u=0,vs=-1,us=-1;
                        for(int j=0;j<3;j++){
                            if(cl_var[ci][j]==v){has_v=1;vs=cl_sign[ci][j];}
                            if(cl_var[ci][j]==u){has_u=1;us=cl_sign[ci][j];}}
                        if(has_v&&has_u){
                            int v_helps=((vs==1&&assignment[v]==1)||(vs==-1&&assignment[v]==0));
                            int u_helps=((us==1&&assignment[u]==1)||(us==-1&&assignment[u]==0));
                            n_agree+=(v_helps+u_helps);nn2++;}}}
                double neighbor_score=nn2>0?n_agree/nn2:0;

                /* 4. Clause over-satisfaction: avg sat_count of v's clauses */
                double avg_sc=0;int nc=0;
                for(int ci=0;ci<n_clauses;ci++){int has=0;
                    for(int j=0;j<3;j++)if(cl_var[ci][j]==v)has=1;
                    if(has){int sc=0;for(int j=0;j<3;j++){int vv=cl_var[ci][j],ss=cl_sign[ci][j];
                        if((ss==1&&assignment[vv]==1)||(ss==-1&&assignment[vv]==0))sc++;}
                        avg_sc+=sc;nc++;}}
                if(nc>0)avg_sc/=nc;

                /* 5. Continuous confidence |x - 0.5| */
                double conf=fabs(x_cont[v]-0.5);

                /* 6. Degree */
                int degree=0;
                for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                    if(cl_var[ci][j]==v)degree++;

                /* 7. |tension| = strength of signal */
                double t_str=fabs(tension);

                /* Store */
                if(is_wrong){
                    ow_match+=mr;ow_tension_agree+=t_agree;
                    ow_neighbor_agree+=neighbor_score;
                    ow_clause_oversat+=avg_sc;ow_x_confidence+=conf;
                    ow_degree+=degree;ow_tension_strength+=t_str;
                    ow_clause_sat_count+=avg_sc;ow_n++;
                }else{
                    or_match+=mr;or_tension_agree+=t_agree;
                    or_neighbor_agree+=neighbor_score;
                    or_clause_oversat+=avg_sc;or_x_confidence+=conf;
                    or_degree+=degree;or_tension_strength+=t_str;
                    or_clause_sat_count+=avg_sc;or_n++;
                }
            }

            if(ow_n>=300)break;
        }
    }

    if(ow_n>0&&or_n>0){
        printf("  %d wrong-to-nearest, %d right-to-nearest\n\n",ow_n,or_n);

        printf("  %25s | %8s | %8s | %6s | %s\n","property","WRONG","RIGHT","ratio","meaning");
        printf("  ");for(int i=0;i<75;i++)printf("-");printf("\n");

        struct{char*name;double w,r;char*meaning;}rows[]={
            {"match_ratio",ow_match/ow_n,or_match/or_n,"OVERFIT: too many matches"},
            {"tension_agreement",ow_tension_agree/ow_n,or_tension_agree/or_n,"tension SUPPORTS wrong"},
            {"neighbor_agreement",ow_neighbor_agree/ow_n,or_neighbor_agree/or_n,"neighbors AGREE with wrong"},
            {"clause_avg_sat_count",ow_clause_oversat/ow_n,or_clause_oversat/or_n,"clauses OVER-satisfied"},
            {"x_confidence |x-.5|",ow_x_confidence/ow_n,or_x_confidence/or_n,"physics CONFIDENCE"},
            {"degree",ow_degree/ow_n,or_degree/or_n,"graph degree"},
            {"|tension|",ow_tension_strength/ow_n,or_tension_strength/or_n,"signal strength"},
        };
        int nrows=7;

        for(int i=0;i<nrows;i++){
            double ratio=rows[i].r>0.001?rows[i].w/rows[i].r:999;
            char*sig="";
            if(fabs(ratio-1)>0.15)sig="★★";
            else if(fabs(ratio-1)>0.05)sig="★";
            printf("  %25s | %8.4f | %8.4f | %6.3f | %s %s\n",
                   rows[i].name,rows[i].w,rows[i].r,ratio,sig,rows[i].meaning);
        }
    }
    return 0;
}
