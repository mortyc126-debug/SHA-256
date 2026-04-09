/*
 * TENSION AS ORACLE: Does |tension| predict wrong-to-nearest at scale?
 * ════════════════════════════════════════════════════════════════════
 *
 * At n=14-16: wrong vars have |tension|=0.177 vs right=0.246 (0.72×)
 * But we need MiniSat for ground truth at small n.
 *
 * Questions:
 * 1. Does the 0.72 ratio STRENGTHEN or weaken at larger n?
 * 2. If we threshold |tension| < T_cut → what fraction are wrong?
 * 3. Can we build a DETECTOR: "vars with lowest |tension| are wrong"?
 * 4. How does this relate to the DET/RAND split (T=0.75)?
 * 5. The DEEPEST question: is |tension| the FUNDAMENTAL variable
 *    that determines correctness? Not a signal — THE signal?
 *
 * Test at n=14,16 (brute force solutions) with many instances.
 *
 * Compile: gcc -O3 -march=native -o tension_oracle tension_as_oracle.c -lm
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
    printf("TENSION AS ORACLE: Predict wrong-to-nearest by |t|\n");
    printf("══════════════════════════════════════════════════\n\n");

    for(int n=14;n<=18;n+=2){
        /* Accumulate: for each |tension| bin, count wrong/right */
        int bins=10;
        int bin_wrong[10],bin_right[10];
        memset(bin_wrong,0,sizeof(bin_wrong));
        memset(bin_right,0,sizeof(bin_right));
        int total_wrong=0,total_right=0;

        /* Also: rank-based detection */
        double sum_rank_wrong=0; /* avg rank of wrong vars when sorted by |t| */
        int n_rank=0;

        int n_inst=0;
        for(int seed=0;seed<1000&&n_inst<60;seed++){
            generate(n,4.267,52000000ULL+seed);
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
            n_inst++;

            /* Compute |tension| for each var */
            double abs_t[MAX_N];
            for(int v=0;v<n;v++){
                double p1=0,p0=0;
                for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                    if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}
                abs_t[v]=(p1+p0>0)?fabs((p1-p0)/(p1+p0)):0;
            }

            /* Bin by |tension| */
            for(int v=0;v<n;v++){
                int b=(int)(abs_t[v]*bins);if(b>=bins)b=bins-1;
                if(assignment[v]!=nearest[v]){bin_wrong[b]++;total_wrong++;}
                else{bin_right[b]++;total_right++;}}

            /* Rank: sort vars by |tension| ascending. Where do wrong vars rank? */
            int sorted[MAX_N];
            for(int v=0;v<n;v++)sorted[v]=v;
            for(int i=0;i<n-1;i++)for(int j=i+1;j<n;j++)
                if(abs_t[sorted[j]]<abs_t[sorted[i]]){int t=sorted[i];sorted[i]=sorted[j];sorted[j]=t;}

            for(int rank=0;rank<n;rank++){
                if(assignment[sorted[rank]]!=nearest[sorted[rank]]){
                    sum_rank_wrong+=(double)rank/n; /* normalized rank 0..1 */
                    n_rank++;}}
        }

        printf("n=%d (%d instances, %d wrong, %d right):\n\n",n,n_inst,total_wrong,total_right);

        /* Print bins */
        printf("  |tension| range | P(wrong) | wrong | right | signal\n");
        printf("  ----------------+----------+-------+-------+-------\n");
        for(int b=0;b<bins;b++){
            double lo=(double)b/bins, hi=(double)(b+1)/bins;
            int tw=bin_wrong[b], tr=bin_right[b];
            int tot=tw+tr;
            double pw=tot>0?(double)tw/tot:0;
            double baseline=(double)total_wrong/(total_wrong+total_right);
            char *sig="";
            if(pw>baseline*1.3)sig="★★ HIGH WRONG";
            else if(pw>baseline*1.1)sig="★ slightly high";
            else if(pw<baseline*0.7)sig="★★ LOW WRONG";
            else if(pw<baseline*0.9)sig="★ slightly low";
            printf("  [%.1f, %.1f)      | %6.1f%% | %5d | %5d | %s\n",
                   lo,hi,100*pw,tw,tr,sig);
        }

        double avg_rank=n_rank>0?sum_rank_wrong/n_rank:0.5;
        printf("\n  Wrong vars avg rank (by ascending |t|): %.3f (0=lowest |t|, 1=highest)\n",avg_rank);
        printf("  → Wrong vars tend to have %s |tension|\n",avg_rank<0.4?"LOW":"medium/high");

        printf("\n");
    }
    return 0;
}
