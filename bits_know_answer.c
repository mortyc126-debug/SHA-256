/*
 * BITS KNOW THEIR ANSWER: one-shot SP + trust the confident bits
 * ═══════════════════════════════════════════════════════════════
 *
 * Idea: instead of iterative decimation (fix few → reconverge → fix few),
 * run SP ONCE, trust ALL variables with |bias| > threshold, then
 * probSAT only needs to solve the remaining "uncertain" variables.
 *
 * The "confident bits" already KNOW their answer from the clause structure.
 * We're not solving them — we're LISTENING to them.
 *
 * Test: vary the trust threshold from 0.1 to 0.9.
 * Lower threshold = trust more bits = smaller remaining problem.
 * But: trusting wrong bits = catastrophic.
 *
 * Key question: what fraction of "confident" bits are actually correct?
 *
 * Compile: gcc -O3 -march=native -o bits_know bits_know_answer.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       10000
#define MAX_CLAUSES 50000
#define MAX_K       3
#define MAX_DEGREE  200

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];
static double eta[MAX_CLAUSES][MAX_K];
static double W_plus[MAX_N], W_minus[MAX_N];
static int var_fixed[MAX_N];
static int cl_active[MAX_CLAUSES];

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
static inline double rng_double(void){return(rng_next()>>11)*(1.0/9007199254740992.0);}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
    rng_seed(seed);memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
    for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
}

/* SP core */
static inline double sp_edge(int ci,int pi){
    double product=1.0;
    for(int pj=0;pj<3;pj++){
        if(pj==pi)continue;
        int j=cl_var[ci][pj];
        if(var_fixed[j]>=0){int sj=cl_sign[ci][pj];
            if((sj==1&&var_fixed[j]==1)||(sj==-1&&var_fixed[j]==0))return 0.0;continue;}
        int sja=cl_sign[ci][pj];double ps=1.0,pu=1.0;
        for(int d=0;d<vdeg[j];d++){
            int bi=vlist[j][d],bp=vpos[j][d];
            if(bi==ci||!cl_active[bi])continue;
            int bsat=0;for(int k=0;k<3;k++){int vk=cl_var[bi][k];
                if(var_fixed[vk]>=0){int sk=cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){bsat=1;break;}}}
            if(bsat)continue;
            double eb=eta[bi][bp];
            if(cl_sign[bi][bp]==sja)ps*=(1.0-eb);else pu*=(1.0-eb);}
        double Pu=(1.0-pu)*ps,Ps=(1.0-ps)*pu,P0=pu*ps;
        double den=Pu+Ps+P0;
        product*=(den>1e-15)?(Pu/den):0.0;}
    return product;}

static double sp_sweep(double rho){
    double mc=0;
    for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;
        for(int p=0;p<3;p++){if(var_fixed[cl_var[ci][p]]>=0)continue;
            double nv=sp_edge(ci,p),ov=eta[ci][p];
            double up=rho*ov+(1.0-rho)*nv;
            double ch=fabs(up-ov);if(ch>mc)mc=ch;eta[ci][p]=up;}}
    return mc;}

static void compute_bias(void){
    for(int i=0;i<n_vars;i++){
        W_plus[i]=W_minus[i]=0;if(var_fixed[i]>=0)continue;
        double pp=1.0,pm=1.0;
        for(int d=0;d<vdeg[i];d++){
            int ci=vlist[i][d],p=vpos[i][d];
            if(!cl_active[ci])continue;
            int sat=0;for(int k=0;k<3;k++){int vk=cl_var[ci][k];
                if(vk!=i&&var_fixed[vk]>=0){int sk=cl_sign[ci][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){sat=1;break;}}}
            if(sat)continue;double e=eta[ci][p];
            if(cl_sign[ci][p]==1)pp*=(1.0-e);else pm*=(1.0-e);}
        double pip=(1.0-pp)*pm,pim=(1.0-pm)*pp,pi0=pp*pm,tot=pip+pim+pi0;
        if(tot>1e-15){W_plus[i]=pip/tot;W_minus[i]=pim/tot;}}}

/* probSAT */
static int ps_a[MAX_N],ps_sc[MAX_CLAUSES],ps_ul[MAX_CLAUSES],ps_up[MAX_CLAUSES],ps_nu;

static void ps_init(int n,int m){
    for(int v=0;v<n;v++)ps_a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    memset(ps_sc,0,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
    ps_nu=0;memset(ps_up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(ps_sc[ci]==0){ps_up[ci]=ps_nu;ps_ul[ps_nu++]=ci;}}

static inline void ps_flip(int fv,int m){
    int old=ps_a[fv],nw=1-old;ps_a[fv]=nw;
    for(int d=0;d<vdeg[fv];d++){int oci=vlist[fv][d],opos=vpos[fv][d];
        int os=cl_sign[oci][opos];
        int was=((os==1&&old==1)||(os==-1&&old==0));
        int now=((os==1&&nw==1)||(os==-1&&nw==0));
        if(was&&!now){ps_sc[oci]--;if(ps_sc[oci]==0){ps_up[oci]=ps_nu;ps_ul[ps_nu++]=oci;}}
        else if(!was&&now){ps_sc[oci]++;if(ps_sc[oci]==1){int p2=ps_up[oci];
            if(p2>=0&&p2<ps_nu){int l=ps_ul[ps_nu-1];ps_ul[p2]=l;ps_up[l]=p2;ps_up[oci]=-1;ps_nu--;}}}}}

static int probsat(int n,int m,int max_flips,double cb){
    double pt[64];for(int b=0;b<64;b++)pt[b]=pow(1.0+b,-cb);
    ps_init(n,m);
    for(int f=0;f<max_flips&&ps_nu>0;f++){
        int ci=ps_ul[rng_next()%ps_nu];
        double probs[3];double sum=0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
            probs[j]=(br<64)?pt[br]:pow(1.0+br,-cb);sum+=probs[j];}
        double r=rng_double()*sum;int fv;
        if(r<probs[0])fv=cl_var[ci][0];else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
        else fv=cl_var[ci][2];ps_flip(fv,m);}
    for(int v=0;v<n;v++)var_fixed[v]=ps_a[v];return m-ps_nu;}

int main(void){
    printf("═══════════════════════════════════════════════════════\n");
    printf("BITS KNOW THEIR ANSWER: one-shot SP + trust + probSAT\n");
    printf("═══════════════════════════════════════════════════════\n\n");

    int test_n[]={200, 500, 1000, 2000};
    double thresholds[]={0.0, 0.1, 0.3, 0.5, 0.7, 0.9};

    printf("α=4.267 (threshold):\n\n");

    for(int ti=0;ti<4;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?20:(nn<=500?10:5);

        printf("n=%d:\n",nn);
        printf("  %10s | %5s | %6s | %5s | %6s | %5s\n",
               "threshold","fixed","%%fix","solved","rate","time");
        printf("  -----------+-------+--------+--------+--------+------\n");

        for(int thi=0;thi<6;thi++){
            double thresh=thresholds[thi];
            int solved=0,total=0;
            double tms=0;
            double avg_fixed=0, avg_correct=0;

            for(int seed=0;seed<ni*3&&total<ni;seed++){
                generate(nn,4.267,11000000ULL+seed);
                int n=nn,m=n_clauses;

                /* Step 1: Run SP ONCE */
                rng_seed(42ULL+(unsigned long long)n*13);
                for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

                int conv=0;
                for(int iter=0;iter<200;iter++){double ch=sp_sweep(0.1);if(ch<1e-4){conv=1;break;}}
                if(!conv)for(int iter=0;iter<100;iter++){double ch=sp_sweep(0.3);if(ch<1e-4){conv=1;break;}}

                if(!conv){total++;continue;} /* SP didn't converge */

                /* Step 2: Compute biases */
                compute_bias();

                /* Step 3: Trust ALL bits with |bias| > threshold */
                clock_t t0=clock();
                int n_trusted=0;
                for(int v=0;v<n;v++){
                    double b=fabs(W_plus[v]-W_minus[v]);
                    if(b>thresh){
                        int val=(W_plus[v]>W_minus[v])?1:0;
                        var_fixed[v]=val;
                        n_trusted++;
                        /* Deactivate satisfied clauses */
                        for(int d=0;d<vdeg[v];d++){
                            int ci=vlist[v][d],p=vpos[v][d];
                            if(!cl_active[ci])continue;
                            int s=cl_sign[ci][p];
                            if((s==1&&val==1)||(s==-1&&val==0))cl_active[ci]=0;
                        }
                    }
                }
                avg_fixed+=n_trusted;

                /* Step 4: probSAT the rest — try multiple cb */
                int sat=0;
                double cbs[]={1.5, 2.06, 2.5, 3.0};
                int flips=n*10000;
                for(int ci2=0;ci2<4&&!sat;ci2++){
                    for(int a=0;a<3&&!sat;a++){
                        rng_seed(a*12345ULL+ci2*77777ULL);
                        if(probsat(n,m,flips,cbs[ci2])==m) sat=1;
                    }
                }

                clock_t t1=clock();
                tms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
                total++;
                if(sat)solved++;
            }

            printf("  bias>%.1f   | %5.0f | %4.0f%%  | %3d/%2d | %4.0f%%  | %4.0fs\n",
                   thresh, avg_fixed/total, 100.0*avg_fixed/(total*nn),
                   solved, total, 100.0*solved/total, tms/total/1000);
            fflush(stdout);
        }
        printf("\n");
    }

    /* ═══ EXPERIMENT 2: How accurate are the "confident bits"? ═══ */
    printf("\n═══ ACCURACY OF CONFIDENT BITS ═══\n");
    printf("For each threshold: what %% of trusted bits are actually correct?\n");
    printf("(Using probSAT solution as ground truth)\n\n");

    for(int ti=0;ti<3;ti++){
        int nn=(int[]){200,500,1000}[ti];
        int ni=(nn<=200)?10:5;

        printf("n=%d:\n",nn);
        printf("  %10s | %5s | %6s | %8s\n","threshold","trust","%%correct","wrong_bits");
        printf("  -----------+-------+--------+----------\n");

        for(int thi=1;thi<6;thi++){
            double thresh=thresholds[thi];
            double avg_trust=0,avg_correct=0,avg_wrong=0;
            int count=0;

            for(int seed=0;seed<ni*3&&count<ni;seed++){
                generate(nn,4.267,11000000ULL+seed);
                int n=nn,m=n_clauses;

                /* First: find a solution with probSAT */
                int sol[MAX_N];
                int found=0;
                for(int a=0;a<20&&!found;a++){
                    rng_seed(a*31337ULL);
                    for(int v=0;v<n;v++)ps_a[v]=rng_next()&1;
                    memset(ps_sc,0,sizeof(int)*m);
                    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){
                        int v=cl_var[ci][j],s=cl_sign[ci][j];
                        if((s==1&&ps_a[v]==1)||(s==-1&&ps_a[v]==0))ps_sc[ci]++;}
                    ps_nu=0;memset(ps_up,-1,sizeof(int)*m);
                    for(int ci=0;ci<m;ci++)if(ps_sc[ci]==0){ps_up[ci]=ps_nu;ps_ul[ps_nu++]=ci;}
                    double pt[64];for(int b=0;b<64;b++)pt[b]=pow(1.0+b,-2.06);
                    for(int f=0;f<n*20000&&ps_nu>0;f++){
                        int ci=ps_ul[rng_next()%ps_nu];
                        double probs[3];double sum=0;
                        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
                            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                                int os=cl_sign[oci][opos];
                                if(((os==1&&ps_a[v]==1)||(os==-1&&ps_a[v]==0))&&ps_sc[oci]==1)br++;}
                            probs[j]=(br<64)?pt[br]:0;sum+=probs[j];}
                        double r=rng_double()*sum;int fv;
                        if(r<probs[0])fv=cl_var[ci][0];else if(r<probs[0]+probs[1])fv=cl_var[ci][1];
                        else fv=cl_var[ci][2];ps_flip(fv,m);}
                    if(ps_nu==0){memcpy(sol,ps_a,sizeof(int)*n);found=1;}
                }
                if(!found) continue;

                /* Run SP */
                for(int ci=0;ci<m;ci++)cl_active[ci]=1;
                memset(var_fixed,-1,sizeof(int)*n);
                rng_seed(42ULL+(unsigned long long)n*13);
                for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();
                int conv=0;
                for(int iter=0;iter<200;iter++){double ch=sp_sweep(0.1);if(ch<1e-4){conv=1;break;}}
                if(!conv) continue;

                compute_bias();

                /* Check accuracy at this threshold */
                int n_trust=0,n_correct=0;
                for(int v=0;v<n;v++){
                    double b=fabs(W_plus[v]-W_minus[v]);
                    if(b>thresh){
                        n_trust++;
                        int predicted=(W_plus[v]>W_minus[v])?1:0;
                        if(predicted==sol[v]) n_correct++;
                    }
                }
                avg_trust+=n_trust;
                avg_correct+=(n_trust>0?100.0*n_correct/n_trust:0);
                avg_wrong+=(n_trust-n_correct);
                count++;
            }

            if(count>0)
                printf("  bias>%.1f   | %5.0f | %5.1f%%  | %5.1f\n",
                       thresh, avg_trust/count, avg_correct/count, avg_wrong/count);
        }
        printf("\n");
    }

    return 0;
}
