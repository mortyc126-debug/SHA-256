/*
 * VERIFY ANOMALIES: Check the 4 anomalies from math synthesis
 *
 * A1: match_ratio amplification (0.576 vs predicted 0.429)
 * A2: critical ratio (0.85 vs predicted 0.95)
 * A3: |tension| > 0.8 cutoff — theoretical prediction
 * A4: greedy path height vs n
 *
 * Also: DOES physics amplification vary with n?
 *
 * Compile: gcc -O3 -march=native -o verify_anom verify_anomalies.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      20
#define MAX_CLAUSES 100
#define MAX_SOLUTIONS 10000

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][3];
static int cl_sign[MAX_CLAUSES][3];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){double u1=(rng_next()>>11)*(1.0/9007199254740992.0),u2=(rng_next()>>11)*(1.0/9007199254740992.0);if(u1<1e-15)u1=1e-15;return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);rng_seed(seed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;}}}

static int eval_a(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static int all_sol[MAX_SOLUTIONS][MAX_N],n_sol;
static void find_all(int n){n_sol=0;for(long long m=0;m<(1LL<<n)&&n_sol<MAX_SOLUTIONS;m++){int a[MAX_N];for(int v=0;v<n;v++)a[v]=(m>>v)&1;if(eval_a(a)==n_clauses){memcpy(all_sol[n_sol],a,sizeof(int)*n);n_sol++;}}}

static double x_c[MAX_N];
static int asgn[MAX_N];
static void physics(int n,int steps,unsigned long long seed){rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}x_c[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.25*exp(-4*prog)+0.0001;double cr=3*prog;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_c[v]:(1.0-x_c[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_c[v]>0.5)force[v]+=cr*(1-x_c[v]);else force[v]-=cr*x_c[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_c[v]+=vel[v]*0.05;if(x_c[v]<0)x_c[v]=0.01;if(x_c[v]>1)x_c[v]=0.99;}}for(int v=0;v<n;v++)asgn[v]=(x_c[v]>0.5)?1:0;}

int main(void){
    printf("═══════════════════════════════════\n");
    printf("VERIFY ANOMALIES\n");
    printf("═══════════════════════════════════\n\n");

    for(int n=12;n<=18;n+=2){
        double sum_mr_wrong=0,sum_mr_right=0; int nw=0,nr=0;
        double sum_cr_wrong=0,sum_cr_right=0;
        double sum_t_wrong=0,sum_t_right=0;
        int wrong_high_t=0,right_high_t=0;
        double sum_hamming=0;
        int n_inst=0;

        for(int seed=0;seed<2000&&n_inst<80;seed++){
            generate(n,4.267,55000000ULL+seed);
            find_all(n);
            if(n_sol<2)continue;

            physics(n,500,42+seed*31);
            if(eval_a(asgn)<n_clauses-n/3)continue;

            int min_h=n,ni=0;
            for(int si=0;si<n_sol;si++){int h=0;for(int v=0;v<n;v++)if(asgn[v]!=all_sol[si][v])h++;if(h<min_h){min_h=h;ni=si;}}
            if(min_h<1)continue;
            int *near=all_sol[ni];
            n_inst++;
            sum_hamming+=min_h;

            for(int v=0;v<n;v++){
                int is_w=(asgn[v]!=near[v]);

                /* match_ratio */
                int match=0,total=0;
                for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                    if(cl_var[ci][j]==v){total++;int s=cl_sign[ci][j];
                        if((s==1&&asgn[v]==1)||(s==-1&&asgn[v]==0))match++;}
                double mr=total>0?(double)match/total:0.5;

                /* critical */
                int crit=0;
                for(int ci=0;ci<n_clauses;ci++){int has=0;
                    for(int j=0;j<3;j++)if(cl_var[ci][j]==v)has=1;
                    if(!has)continue;
                    int sc=0,vsaves=0;
                    for(int j=0;j<3;j++){int vv=cl_var[ci][j],ss=cl_sign[ci][j];
                        if((ss==1&&asgn[vv]==1)||(ss==-1&&asgn[vv]==0)){sc++;if(vv==v)vsaves=1;}}
                    if(sc==1&&vsaves)crit++;}

                /* |tension| */
                double p1=0,p0=0;
                for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                    if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}
                double at=(p1+p0>0)?fabs((p1-p0)/(p1+p0)):0;
                int high_t=(at>0.8);

                if(is_w){sum_mr_wrong+=mr;sum_cr_wrong+=crit;sum_t_wrong+=at;nw++;if(high_t)wrong_high_t++;}
                else{sum_mr_right+=mr;sum_cr_right+=crit;sum_t_right+=at;nr++;if(high_t)right_high_t++;}
            }
        }

        if(nw>0&&nr>0){
            printf("n=%d (%d inst, %d wrong, %d right):\n",n,n_inst,nw,nr);
            printf("  Hamming to nearest: %.1f (%.0f%%)\n",sum_hamming/n_inst,100*sum_hamming/(n_inst*n));

            double mr_w=sum_mr_wrong/nw, mr_r=sum_mr_right/nr;
            printf("\n  A1: match_ratio:\n");
            printf("    wrong = %.4f (predicted 3/7 = %.4f, Δ = %+.4f)\n",mr_w,3.0/7,mr_w-3.0/7);
            printf("    right = %.4f (predicted 4/7 = %.4f, Δ = %+.4f)\n",mr_r,4.0/7,mr_r-4.0/7);
            printf("    Physics amplification: wrong %+.1f%%, right %+.1f%%\n",
                   100*(mr_w-3.0/7)/(3.0/7), 100*(mr_r-4.0/7)/(4.0/7));

            double cr_w=sum_cr_wrong/nw, cr_r=sum_cr_right/nr;
            double cr_ratio=cr_w/cr_r;
            /* Predicted from match_ratio alone */
            double p_other_true=0.75*mr_r+0.25*mr_w;
            double p_other_false=1-p_other_true;
            double pred_cr_w=mr_w*p_other_false*p_other_false;
            double pred_cr_r=mr_r*p_other_false*p_other_false;
            double pred_ratio=pred_cr_w/pred_cr_r;

            printf("\n  A2: critical ratio:\n");
            printf("    measured: wrong=%.3f, right=%.3f, ratio=%.3f\n",cr_w,cr_r,cr_ratio);
            printf("    predicted from match_ratio: ratio=%.3f\n",pred_ratio);
            printf("    ANOMALY gap: %.3f (measured - predicted)\n",cr_ratio-pred_ratio);

            printf("\n  A3: |tension| > 0.8 cutoff:\n");
            printf("    wrong with |t|>0.8: %d (%.2f%%)\n",wrong_high_t,100.0*wrong_high_t/nw);
            printf("    right with |t|>0.8: %d (%.2f%%)\n",right_high_t,100.0*right_high_t/nr);
            /* Binomial prediction: P(|tension|>0.8) for d=13, ε=1/14 */
            /* |σ| = |2K-d|/d > 0.8 means K > 0.9d or K < 0.1d */
            /* P(K≥12 or K≤1) for Bin(13,4/7) */
            double p47=4.0/7;
            double p_high_correct=0,p_high_wrong=0;
            for(int k=0;k<=13;k++){
                double binom=1;for(int i=0;i<k;i++)binom*=p47*(13-i)/(i+1);
                for(int i=k;i<13;i++)binom*=(1-p47);
                double sigma=fabs(2.0*k/13-1);
                if(sigma>0.8){p_high_correct+=binom;}
                /* For wrong: votes are Bin(13,3/7) */
                double binom_w=1;double p37=3.0/7;
                for(int i=0;i<k;i++)binom_w*=p37*(13-i)/(i+1);
                for(int i=k;i<13;i++)binom_w*=(1-p37);
                if(sigma>0.8){p_high_wrong+=binom_w;}}
            printf("    Binomial prediction: P(|t|>0.8|correct)=%.4f, P(|t|>0.8|wrong)=%.4f\n",
                   p_high_correct,p_high_wrong);

            printf("\n  |tension| distribution:\n");
            double t_w=sum_t_wrong/nw, t_r=sum_t_right/nr;
            printf("    avg|t|: wrong=%.4f, right=%.4f, ratio=%.3f\n",t_w,t_r,t_w/t_r);
            /* Predicted from Binomial: E[|2Bin(13,p)/13-1|] */
            double e_abs_correct=0,e_abs_wrong=0;
            for(int k=0;k<=13;k++){
                double bc=1;for(int i=1;i<=k;i++)bc*=p47*(14-i)/i;for(int i=k;i<13;i++)bc*=(1-p47);
                e_abs_correct+=bc*fabs(2.0*k/13-1);
                double bw=1;double p37=3.0/7;for(int i=1;i<=k;i++)bw*=p37*(14-i)/i;for(int i=k;i<13;i++)bw*=(1-p37);
                e_abs_wrong+=bw*fabs(2.0*k/13-1);}
            printf("    predicted: E[|t||correct]=%.4f, E[|t||wrong]=%.4f, ratio=%.3f\n",
                   e_abs_correct,e_abs_wrong,e_abs_wrong/e_abs_correct);
            printf("    ANOMALY: measured ratio=%.3f vs predicted=%.3f\n",
                   t_w/t_r,e_abs_wrong/e_abs_correct);

            printf("\n");
        }
    }
    return 0;
}
