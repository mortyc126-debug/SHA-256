/*
 * CRITICAL DYNAMICS: How does critical count CHANGE over time and realities?
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Critical count is the FUNDAMENTAL observable (ratio 0.47-0.85 everywhere).
 * But we've only measured it ONCE (at final state).
 *
 * New dimensions:
 * 1. TEMPORAL: Track critical count DURING physics simulation.
 *    Does wrong vars' critical change differently from right?
 *
 * 2. MULTI-REALITY: Compute critical count in 5 cold starts.
 *    Is critical count STABLE across realities for right vars?
 *    UNSTABLE for wrong vars?
 *
 * 3. DERIVATIVE: Δcritical between two nearby states.
 *    If we perturb slightly, does critical react differently
 *    for wrong vs right?
 *
 * 4. RELATIVE CRITICAL: Not absolute count but rank among neighbors.
 *    Is wrong var the LOWEST critical in its neighborhood?
 *
 * Compile: gcc -O3 -march=native -o crit_dyn critical_dynamics.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      20
#define MAX_CLAUSES 100
#define MAX_K      3
#define MAX_SOLUTIONS 10000
#define N_RUNS     5

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

/* Compute critical count for var v given assignment a */
static int get_critical(int v, const int *a, int n){
    int crit=0;
    for(int ci=0;ci<n_clauses;ci++){
        int has=0,pos=-1;
        for(int j=0;j<3;j++)if(cl_var[ci][j]==v){has=1;pos=j;}
        if(!has)continue;
        int sc=0,v_saves=0;
        for(int j=0;j<3;j++){int vv=cl_var[ci][j],ss=cl_sign[ci][j];
            if((ss==1&&a[vv]==1)||(ss==-1&&a[vv]==0)){sc++;if(vv==v)v_saves=1;}}
        if(sc==1&&v_saves)crit++;}
    return crit;
}

/* Run physics and record snapshots */
static void physics_with_snapshots(int n, int steps, unsigned long long seed,
                                    int snap_a[][MAX_N], int *n_snaps){
    rng_seed(seed);double vel[MAX_N];
    for(int v=0;v<n;v++){double p1=0,p0=0;
        for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++)
            if(cl_var[ci][j]==v){if(cl_sign[ci][j]==1)p1+=1.0/3;else p0+=1.0/3;}
        x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}
    *n_snaps=0;
    double force[MAX_N];
    for(int step=0;step<steps;step++){
        double prog=(double)step/steps;double T=0.25*exp(-4*prog)+0.0001;double cr=3*prog;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];
            vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;
            if(x_cont[v]<0)x_cont[v]=0.01;if(x_cont[v]>1)x_cont[v]=0.99;}

        /* Snapshot at 25%, 50%, 75%, 100% */
        if(step==steps/4||step==steps/2||step==steps*3/4||step==steps-1){
            for(int v=0;v<n;v++)snap_a[*n_snaps][v]=(x_cont[v]>0.5)?1:0;
            (*n_snaps)++;}}
    for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;
}

int main(void){
    printf("══════════════════════════════════════════════════\n");
    printf("CRITICAL DYNAMICS: Time, reality, derivative\n");
    printf("══════════════════════════════════════════════════\n\n");

    int n=16;

    /* Accumulators */
    double w_crit_t[4]={0},r_crit_t[4]={0}; int wn_t[4]={0},rn_t[4]={0};
    double w_crit_var=0,r_crit_var=0; int wn_v=0,rn_v=0;
    double w_crit_min_rank=0,r_crit_min_rank=0; int wn_r=0,rn_r=0;
    double w_crit_reaction=0,r_crit_reaction=0; int wn_rx=0,rn_rx=0;

    int n_inst=0;
    for(int seed=0;seed<1000&&n_inst<60;seed++){
        generate(n,4.267,54000000ULL+seed);
        find_all_solutions(n);
        if(n_solutions<2)continue;

        /* Physics with snapshots */
        int snaps[4][MAX_N],ns;
        physics_with_snapshots(n,500,42+seed*31,snaps,&ns);
        if(ns<4)continue;

        int sat=eval_a(assignment);
        if(n_clauses-sat>n/3)continue;

        int min_h=n,ni=0;
        for(int si=0;si<n_solutions;si++){
            int h=0;for(int v=0;v<n;v++)if(assignment[v]!=all_solutions[si][v])h++;
            if(h<min_h){min_h=h;ni=si;}}
        if(min_h<1)continue;
        int *nearest=all_solutions[ni];
        n_inst++;

        /* ═══ 1. TEMPORAL: critical count at each snapshot ═══ */
        for(int t=0;t<4;t++){
            for(int v=0;v<n;v++){
                int c=get_critical(v,snaps[t],n);
                if(assignment[v]!=nearest[v]){w_crit_t[t]+=c;wn_t[t]++;}
                else{r_crit_t[t]+=c;rn_t[t]++;}}}

        /* ═══ 2. MULTI-REALITY: critical variance across cold starts ═══ */
        int run_a[N_RUNS][MAX_N];
        for(int r=0;r<N_RUNS;r++){
            int dummy[4][MAX_N];int dns;
            physics_with_snapshots(n,500,100+r*13337+seed*99991,dummy,&dns);
            memcpy(run_a[r],assignment,sizeof(int)*n);}

        for(int v=0;v<n;v++){
            double crits[N_RUNS];
            for(int r=0;r<N_RUNS;r++)crits[r]=get_critical(v,run_a[r],n);
            double mean=0;for(int r=0;r<N_RUNS;r++)mean+=crits[r];mean/=N_RUNS;
            double var=0;for(int r=0;r<N_RUNS;r++){double d=crits[r]-mean;var+=d*d;}var/=N_RUNS;
            if(assignment[v]!=nearest[v]){w_crit_var+=var;wn_v++;}
            else{r_crit_var+=var;rn_v++;}}

        /* ═══ 3. RELATIVE RANK: is var the min-critical in its neighborhood? ═══ */
        int adj[MAX_N][50],adj_n[MAX_N];memset(adj_n,0,sizeof(adj_n));
        for(int ci=0;ci<n_clauses;ci++)
            for(int a=0;a<3;a++)for(int b=a+1;b<3;b++){
                int va=cl_var[ci][a],vb=cl_var[ci][b];
                if(adj_n[va]<50)adj[va][adj_n[va]++]=vb;
                if(adj_n[vb]<50)adj[vb][adj_n[vb]++]=va;}

        for(int v=0;v<n;v++){
            int cv=get_critical(v,assignment,n);
            int lower=0,total2=0;
            for(int d=0;d<adj_n[v];d++){
                int cu=get_critical(adj[v][d],assignment,n);
                if(cu<cv)lower++;total2++;}
            double rank=total2>0?(double)lower/total2:0.5;
            /* rank ≈ 1 means v has HIGH critical (others are lower) */
            /* rank ≈ 0 means v has LOW critical (it IS the minimum) */
            if(assignment[v]!=nearest[v]){w_crit_min_rank+=rank;wn_r++;}
            else{r_crit_min_rank+=rank;rn_r++;}}

        /* ═══ 4. REACTION: If we flip v's best neighbor, how does v's critical change? ═══ */
        for(int v=0;v<n;v++){
            int cv_before=get_critical(v,assignment,n);
            /* Find v's neighbor with min critical */
            int min_nb=-1,min_c=999;
            for(int d=0;d<adj_n[v];d++){
                int u=adj[v][d],cu=get_critical(u,assignment,n);
                if(cu<min_c){min_c=cu;min_nb=u;}}
            if(min_nb<0)continue;
            /* Flip neighbor, measure v's critical change */
            int ta[MAX_N];memcpy(ta,assignment,sizeof(int)*n);
            ta[min_nb]=1-ta[min_nb];
            int cv_after=get_critical(v,ta,n);
            double reaction=(double)(cv_after-cv_before);
            if(assignment[v]!=nearest[v]){w_crit_reaction+=reaction;wn_rx++;}
            else{r_crit_reaction+=reaction;rn_rx++;}}
    }

    printf("  %d instances (n=%d)\n\n",n_inst,n);

    printf("  ═══ 1. TEMPORAL: critical count at different times ═══\n");
    printf("  %8s | %6s | %6s | %6s\n","time","WRONG","RIGHT","ratio");
    printf("  ---------+--------+--------+------\n");
    char *tnames[]={"25%","50%","75%","final"};
    for(int t=0;t<4;t++){
        double w=wn_t[t]>0?w_crit_t[t]/wn_t[t]:0;
        double r=rn_t[t]>0?r_crit_t[t]/rn_t[t]:0;
        double ratio=r>0.001?w/r:999;
        printf("  %8s | %6.3f | %6.3f | %5.3f%s\n",
               tnames[t],w,r,ratio,fabs(ratio-1)>0.1?" ★":"");
    }

    printf("\n  ═══ 2. MULTI-REALITY: critical count VARIANCE ═══\n");
    {double w=wn_v>0?w_crit_var/wn_v:0;
     double r=rn_v>0?r_crit_var/rn_v:0;
     double ratio=r>0.001?w/r:999;
     printf("  Variance: wrong=%.3f, right=%.3f, ratio=%.3f%s\n",
            w,r,ratio,fabs(ratio-1)>0.15?" ★★":"");}

    printf("\n  ═══ 3. RELATIVE RANK among neighbors ═══\n");
    {double w=wn_r>0?w_crit_min_rank/wn_r:0;
     double r=rn_r>0?r_crit_min_rank/rn_r:0;
     printf("  Rank: wrong=%.3f, right=%.3f (0=min critical, 1=max)\n",w,r);
     printf("  → Wrong vars are %s critical than neighbors\n",
            w<r?"LOWER":"higher or same");}

    printf("\n  ═══ 4. REACTION to neighbor flip ═══\n");
    {double w=wn_rx>0?w_crit_reaction/wn_rx:0;
     double r=rn_rx>0?r_crit_reaction/rn_rx:0;
     printf("  Reaction: wrong=%+.3f, right=%+.3f\n",w,r);
     printf("  → Wrong vars %s when neighbor flipped\n",
            w>r?"GAIN MORE critical":"react same or less");}

    return 0;
}
