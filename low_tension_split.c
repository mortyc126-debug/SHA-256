/*
 * LOW TENSION SPLIT: Among low |t| vars, what separates wrong from right?
 * ════════════════════════════════════════════════════════════════════════
 *
 * |tension| < 0.3: ~25% wrong, ~75% right.
 * WHAT distinguishes the 25% from the 75%?
 *
 * Measure EVERYTHING about low-tension vars:
 * 1. Tension SIGN (not magnitude) — does sign agree with assignment?
 * 2. Neighbor tensions — are neighbors also low?
 * 3. Clause structure — how many clauses, what types?
 * 4. x_continuous — where exactly in [0,1]?
 * 5. 2nd order: tension OF neighbors
 * 6. Cross-clause consistency — do clauses agree with each other?
 * 7. Number of BARELY-SAT clauses
 * 8. Degree distribution among low-t vars
 * 9. Does this var appear in "conflicting" clauses (opposite signs)?
 * 10. Distance to nearest high-tension var
 *
 * Compile: gcc -O3 -march=native -o lt_split low_tension_split.c -lm
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
    printf("═══════════════════════════════════════════\n");
    printf("LOW TENSION SPLIT: Wrong vs right at |t|<0.3\n");
    printf("═══════════════════════════════════════════\n\n");

    /* Accumulate */
    typedef struct{double val;int count;} Acc;
    #define NP 12
    Acc wrong[NP],right[NP];
    char *names[NP]={"tension_sign_agree","avg_neighbor_|t|","n_conflicting_clauses",
        "x_distance_from_0.5","neighbor_tension_agree","barely_sat_clauses",
        "degree","pos_sign_fraction","n_low_t_neighbors","clause_agreement",
        "self_cancel_score","critical_count"};
    memset(wrong,0,sizeof(wrong));memset(right,0,sizeof(right));

    int n=16; /* focus on n=16 */
    for(int seed=0;seed<1000;seed++){
        generate(n,4.267,53000000ULL+seed);
        find_all_solutions(n);
        if(n_solutions<2)continue;

        physics(n,500,42+seed*31);
        int sat=eval_a(assignment);
        if(n_clauses-sat>n/3)continue;

        int min_h=n,ni=0;
        for(int si=0;si<n_solutions;si++){
            int h=0;for(int v=0;v<n;v++)if(assignment[v]!=all_solutions[si][v])h++;
            if(h<min_h){min_h=h;ni=si;}}
        if(min_h<1)continue;
        int *nearest=all_solutions[ni];

        /* Compute tensions */
        double tension[MAX_N];
        for(int v=0;v<n;v++){double p1=0,p0=0;
            for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}
            tension[v]=(p1+p0>0)?(p1-p0)/(p1+p0):0;}

        /* Adjacency */
        int adj[MAX_N][50],adj_n[MAX_N]; memset(adj_n,0,sizeof(adj_n));
        for(int ci=0;ci<n_clauses;ci++)
            for(int a=0;a<3;a++)for(int b=a+1;b<3;b++){
                int va=cl_var[ci][a],vb=cl_var[ci][b];
                if(adj_n[va]<50)adj[va][adj_n[va]++]=vb;
                if(adj_n[vb]<50)adj[vb][adj_n[vb]++]=va;}

        /* Per low-tension var */
        for(int v=0;v<n;v++){
            if(fabs(tension[v])>=0.3)continue; /* only low tension */

            int is_wrong=(assignment[v]!=nearest[v]);
            Acc *dst=is_wrong?wrong:right;

            int mi=0;

            /* 1. Tension sign agrees with assignment? */
            double sign_agree=(assignment[v]==1)?tension[v]:-tension[v];
            dst[mi].val+=sign_agree;dst[mi].count++;mi++;

            /* 2. Avg |tension| of neighbors */
            double avg_nt=0;int nn2=0;
            for(int d=0;d<adj_n[v];d++){avg_nt+=fabs(tension[adj[v][d]]);nn2++;}
            if(nn2>0)avg_nt/=nn2;
            dst[mi].val+=avg_nt;dst[mi].count++;mi++;

            /* 3. Number of "conflicting" clauses (has both + and - signs for v) */
            int pos=0,neg=0;
            for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
                if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)pos++;else neg++;}
            int conflicts=(pos<neg)?pos:neg; /* min(pos,neg) = conflicting pairs */
            dst[mi].val+=conflicts;dst[mi].count++;mi++;

            /* 4. |x_continuous - 0.5| */
            double xd=fabs(x_cont[v]-0.5);
            dst[mi].val+=xd;dst[mi].count++;mi++;

            /* 5. Neighbor tension agreement: do neighbors' tensions agree with v? */
            double nta=0;
            for(int d=0;d<adj_n[v];d++){
                int u=adj[v][d];
                /* Agreement: both positive or both negative tension */
                nta+=(tension[v]*tension[u]>0)?1:0;}
            if(nn2>0)nta/=nn2;
            dst[mi].val+=nta;dst[mi].count++;mi++;

            /* 6. Barely-sat clauses involving v */
            int barely=0;
            for(int ci=0;ci<n_clauses;ci++){int has=0;
                for(int j=0;j<3;j++)if(cl_var[ci][j]==v)has=1;
                if(!has)continue;
                int sc=0;for(int j=0;j<3;j++){int vv=cl_var[ci][j],ss=cl_sign[ci][j];
                    if((ss==1&&assignment[vv]==1)||(ss==-1&&assignment[vv]==0))sc++;}
                if(sc==1)barely++;}
            dst[mi].val+=barely;dst[mi].count++;mi++;

            /* 7. Degree */
            dst[mi].val+=pos+neg;dst[mi].count++;mi++;

            /* 8. Fraction of positive signs */
            dst[mi].val+=(double)pos/(pos+neg+1);dst[mi].count++;mi++;

            /* 9. Number of low-tension neighbors */
            int nlt=0;
            for(int d=0;d<adj_n[v];d++)
                if(fabs(tension[adj[v][d]])<0.2)nlt++;
            dst[mi].val+=nlt;dst[mi].count++;mi++;

            /* 10. Clause agreement: for each pair of v's clauses,
                   do they "agree" on v's direction? */
            double ca=0;int np2=0;
            for(int ci=0;ci<n_clauses;ci++){int si_v=-99;
                for(int j=0;j<3;j++)if(cl_var[ci][j]==v)si_v=cl_sign[ci][j];
                if(si_v==-99)continue;
                for(int cj=ci+1;cj<n_clauses;cj++){int sj_v=-99;
                    for(int j=0;j<3;j++)if(cl_var[cj][j]==v)sj_v=cl_sign[cj][j];
                    if(sj_v==-99)continue;
                    ca+=(si_v==sj_v)?1:0;np2++;}}
            if(np2>0)ca/=np2;
            dst[mi].val+=ca;dst[mi].count++;mi++;

            /* 11. Self-cancellation: |tension + avg(neighbor tensions)| */
            double sc=0;
            if(nn2>0){double nt=0;for(int d=0;d<adj_n[v];d++)nt+=tension[adj[v][d]];
                nt/=nn2;sc=fabs(tension[v]+nt);}
            dst[mi].val+=sc;dst[mi].count++;mi++;

            /* 12. Critical count */
            int crit=0;
            for(int ci=0;ci<n_clauses;ci++){int has=0,pos2=-1;
                for(int j=0;j<3;j++)if(cl_var[ci][j]==v){has=1;pos2=j;}
                if(!has)continue;
                int sc2=0,v_saves=0;
                for(int j=0;j<3;j++){int vv=cl_var[ci][j],ss=cl_sign[ci][j];
                    if((ss==1&&assignment[vv]==1)||(ss==-1&&assignment[vv]==0)){sc2++;
                        if(vv==v)v_saves=1;}}
                if(sc2==1&&v_saves)crit++;}
            dst[mi].val+=crit;dst[mi].count++;mi++;
        }

        if(wrong[0].count>=200)break;
    }

    printf("  Among vars with |tension| < 0.3:\n");
    printf("  %d wrong-to-nearest, %d right-to-nearest\n\n",
           wrong[0].count,right[0].count);

    printf("  %25s | %8s | %8s | %6s | %s\n","property","WRONG","RIGHT","ratio","signal");
    printf("  ");for(int i=0;i<70;i++)printf("-");printf("\n");

    for(int i=0;i<NP;i++){
        double w=wrong[i].count>0?wrong[i].val/wrong[i].count:0;
        double r=right[i].count>0?right[i].val/right[i].count:0;
        double ratio=fabs(r)>0.001?w/r:(fabs(w)>0.001?999:1);
        char*sig="";
        if(fabs(ratio-1)>0.25)sig="★★★";
        else if(fabs(ratio-1)>0.15)sig="★★";
        else if(fabs(ratio-1)>0.08)sig="★";
        printf("  %25s | %8.4f | %8.4f | %6.3f | %s\n",
               names[i],w,r,ratio,sig);
    }

    return 0;
}
