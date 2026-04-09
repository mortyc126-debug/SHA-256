/*
 * RECALCULATE: All key findings with NEAREST solution as target
 * ═══════════════════════════════════════════════════════════════
 *
 * Our "36% wrong, coherent alternative reality, equilibrium" —
 * all were computed against WRONG solution. Redo with nearest.
 *
 * At n=14-16 (can enumerate all solutions):
 * 1. How many vars wrong to NEAREST?
 * 2. Greedy path to NEAREST: how flat?
 * 3. Are the ~10% wrong vars detectable?
 *    (ghost score, match_ratio, counterfactual)
 * 4. Pendulum: still period 2 to nearest?
 * 5. All-3-wrong: still true for nearest?
 * 6. Silent wrong: still 90% invisible?
 *
 * Compile: gcc -O3 -march=native -o recalc recalculate_nearest.c -lm
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
    printf("══════════════════════════════════════════════════\n");
    printf("RECALCULATE: Everything with NEAREST solution\n");
    printf("══════════════════════════════════════════════════\n\n");

    /* Accumulate stats */
    double sum_nearest_frac=0, sum_first_frac=0;
    double sum_nearest_mr_wrong=0, sum_nearest_mr_right=0;
    double sum_nearest_cf_wrong=0, sum_nearest_cf_right=0;
    double sum_all3wrong_nearest=0, sum_all3wrong_first=0;
    double sum_greedy_max_nearest=0, sum_greedy_max_first=0;
    int n_inst=0;

    for(int n=14;n<=16;n+=2){
        for(int seed=0;seed<300&&n_inst<40;seed++){
            generate(n,4.267,50000000ULL+seed);
            find_all_solutions(n);
            if(n_solutions<2)continue;

            physics(n,500,42+seed*31);
            int sat=eval_a(assignment);
            int unsat=n_clauses-sat;
            if(unsat>n/2)continue; /* skip bad runs */

            /* Find NEAREST and FIRST solution */
            int min_h=n,nearest_idx=0;
            for(int si=0;si<n_solutions;si++){
                int h=0;for(int v=0;v<n;v++)if(assignment[v]!=all_solutions[si][v])h++;
                if(h<min_h){min_h=h;nearest_idx=si;}}

            int *nearest=all_solutions[nearest_idx];
            int *first=all_solutions[0];
            int first_h=0;for(int v=0;v<n;v++)if(assignment[v]!=first[v])first_h++;

            if(min_h<1)continue; /* already solved */

            n_inst++;
            sum_nearest_frac+=(double)min_h/n;
            sum_first_frac+=(double)first_h/n;

            /* ═══ match_ratio for wrong vars (nearest) ═══ */
            for(int v=0;v<n;v++){
                int match=0,total=0;
                for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                    if(cl_var[ci][j]==v){total++;int s=cl_sign[ci][j];
                        if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))match++;}
                double mr=total>0?(double)match/total:0.5;
                if(assignment[v]!=nearest[v])sum_nearest_mr_wrong+=mr;
                else sum_nearest_mr_right+=mr;
            }

            /* ═══ counterfactual for wrong vars (nearest) ═══ */
            for(int v=0;v<n;v++){
                int ta[MAX_N];memcpy(ta,assignment,sizeof(int)*n);ta[v]=1-ta[v];
                double cf=eval_a(ta)-sat;
                if(assignment[v]!=nearest[v])sum_nearest_cf_wrong+=fabs(cf);
                else sum_nearest_cf_right+=fabs(cf);
            }

            /* ═══ all-3-wrong in unsat clauses (nearest vs first) ═══ */
            for(int ci=0;ci<n_clauses;ci++){
                if(eval_a(assignment)!=n_clauses){ /* check each unsat */
                    int clause_sat=0;
                    for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                        if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sat=1;}
                    if(!clause_sat){
                        int n3_near=0,n3_first=0;
                        for(int j=0;j<3;j++){
                            if(assignment[cl_var[ci][j]]!=nearest[cl_var[ci][j]])n3_near++;
                            if(assignment[cl_var[ci][j]]!=first[cl_var[ci][j]])n3_first++;}
                        if(n3_near==3)sum_all3wrong_nearest++;
                        if(n3_first==3)sum_all3wrong_first++;
                    }
                }
            }

            /* ═══ Greedy path to NEAREST vs FIRST ═══ */
            /* To nearest */
            {int diff_n[MAX_N],nd=0;
             for(int v=0;v<n;v++)if(assignment[v]!=nearest[v])diff_n[nd++]=v;
             int cur[MAX_N];memcpy(cur,assignment,sizeof(int)*n);
             int max_unsat_n=0;
             for(int step=0;step<nd;step++){
                 int best_v=-1,best_sat=0;
                 for(int i=0;i<nd;i++){int v=diff_n[i];if(cur[v]==nearest[v])continue;
                     int save=cur[v];cur[v]=nearest[v];int s2=eval_a(cur);cur[v]=save;
                     if(s2>best_sat){best_sat=s2;best_v=diff_n[i];}}
                 if(best_v<0)break;cur[best_v]=nearest[best_v];
                 int u=n_clauses-eval_a(cur);if(u>max_unsat_n)max_unsat_n=u;}
             sum_greedy_max_nearest+=max_unsat_n;}

            /* To first */
            {int diff_f[MAX_N],nd=0;
             for(int v=0;v<n;v++)if(assignment[v]!=first[v])diff_f[nd++]=v;
             int cur[MAX_N];memcpy(cur,assignment,sizeof(int)*n);
             int max_unsat_f=0;
             for(int step=0;step<nd;step++){
                 int best_v=-1,best_sat=0;
                 for(int i=0;i<nd;i++){int v=diff_f[i];if(cur[v]==first[v])continue;
                     int save=cur[v];cur[v]=first[v];int s2=eval_a(cur);cur[v]=save;
                     if(s2>best_sat){best_sat=s2;best_v=diff_f[i];}}
                 if(best_v<0)break;cur[best_v]=first[best_v];
                 int u=n_clauses-eval_a(cur);if(u>max_unsat_f)max_unsat_f=u;}
             sum_greedy_max_first+=max_unsat_f;}
        }
    }

    if(n_inst>0){
        int n_avg=15; /* approximate n for stats */
        int wrong_near_n=(int)(sum_nearest_frac/n_inst*n_avg);
        int wrong_first_n=(int)(sum_first_frac/n_inst*n_avg);
        int right_near_n=n_avg-wrong_near_n;
        int right_first_n=n_avg-wrong_first_n;

        printf("  %d instances (n=14-16):\n\n",n_inst);

        printf("  ═══ HAMMING DISTANCE ═══\n");
        printf("  To NEAREST: %.0f%% of n\n",100*sum_nearest_frac/n_inst);
        printf("  To FIRST:   %.0f%% of n\n",100*sum_first_frac/n_inst);
        printf("  Ratio: %.2f× closer to nearest\n\n",
               (sum_first_frac/n_inst)/(sum_nearest_frac/n_inst));

        printf("  ═══ match_ratio (wrong vars) ═══\n");
        printf("  Wrong (nearest): %.3f\n",sum_nearest_mr_wrong/(n_inst*wrong_near_n));
        printf("  Right (nearest): %.3f\n",sum_nearest_mr_right/(n_inst*right_near_n));
        printf("  Wrong (first):   ~0.500 (from earlier)\n\n");

        printf("  ═══ counterfactual |Δsat| ═══\n");
        printf("  Wrong (nearest): %.3f\n",sum_nearest_cf_wrong/(n_inst*wrong_near_n));
        printf("  Right (nearest): %.3f\n",sum_nearest_cf_right/(n_inst*right_near_n));
        printf("  Ratio: %.2f\n\n",
               (sum_nearest_cf_wrong/(n_inst*fmax(wrong_near_n,1))) /
               (sum_nearest_cf_right/(n_inst*fmax(right_near_n,1))));

        printf("  ═══ GREEDY PATH max unsat ═══\n");
        printf("  To NEAREST: %.1f\n",sum_greedy_max_nearest/n_inst);
        printf("  To FIRST:   %.1f\n",sum_greedy_max_first/n_inst);
        printf("  → Path to nearest is %s\n",
               sum_greedy_max_nearest<sum_greedy_max_first?"FLATTER!":"same or worse");
    }
    return 0;
}
