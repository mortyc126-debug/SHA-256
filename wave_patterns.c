/*
 * WAVE PATTERNS: Is the hard core a wave, not a set of points?
 * ════════════════════════════════════════════════════════════
 *
 * Individual vars are invisible. But maybe PATTERNS of vars are visible.
 * Like sound = not atoms but oscillation of MANY atoms together.
 *
 * STUDY:
 * 1. WRONG PATTERN: Among wrong vars — is there a SPATIAL pattern?
 *    Do wrong vars cluster in one region? Form a line? Random scatter?
 *
 * 2. FOURIER: Decompose the wrong-var vector into frequency modes.
 *    Is the error LOW-FREQUENCY (smooth wave) or HIGH-FREQUENCY (noise)?
 *
 * 3. COLD START DIVERSITY: Run 20 COLD starts. Compare the unsat clauses.
 *    Are the SAME clauses always unsat? Or DIFFERENT ones?
 *    If same → structural. If different → random luck.
 *
 * 4. INTERFERENCE BETWEEN COLD STARTS: Do two solutions from different
 *    cold starts, when COMBINED (e.g., var-by-var majority), give
 *    a BETTER solution than either alone?
 *
 * 5. THE DISTANCE BETWEEN REALITIES: Hamming distance between cold starts.
 *    Are they near each other? Or in completely different regions?
 *
 * 6. OVERLAP OF CORRECT VARS: Between cold starts, which vars are
 *    ALWAYS correct? Always wrong? Differ between starts?
 *
 * Compile: gcc -O3 -march=native -o wave_pat wave_patterns.c -lm
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
#define N_COLD     20

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

static void walksat_phase(int flips){for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);
    int old=assignment[fv],nw=1-old;assignment[fv]=nw;for(int d=0;d<vdeg[fv];d++){int ci=vlist[fv][d],pos=vpos[fv][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}}

int main(void){
    printf("═══════════════════════════════════════\n");
    printf("WAVE PATTERNS: Cold start diversity\n");
    printf("═══════════════════════════════════════\n\n");

    int nn=500;
    for(int seed=0;seed<5;seed++){
        generate(nn,4.267,40000000ULL+seed);
        int n=nn, m=n_clauses, steps=2000+n*15;

        /* 20 COLD starts: completely independent physics runs */
        int cold_a[N_COLD][MAX_N];
        int cold_unsat[N_COLD];
        int cold_sat_score[N_COLD];

        for(int r=0;r<N_COLD;r++){
            physics(steps, 100+r*13337+seed*99991); /* different seed = different reality */
            recompute();
            rng_seed(r*77777+seed);
            walksat_phase(n*200);
            memcpy(cold_a[r],assignment,sizeof(int)*n);
            cold_unsat[r]=count_unsat();
            cold_sat_score[r]=m-cold_unsat[r];
        }

        printf("n=%d seed=%d:\n",nn,seed);

        /* ═══ 1. Unsat distribution across cold starts ═══ */
        int min_u=m,max_u=0; double sum_u=0;
        for(int r=0;r<N_COLD;r++){
            if(cold_unsat[r]<min_u)min_u=cold_unsat[r];
            if(cold_unsat[r]>max_u)max_u=cold_unsat[r];
            sum_u+=cold_unsat[r];}
        printf("  Unsat: min=%d, max=%d, avg=%.1f, spread=%d\n",
               min_u,max_u,sum_u/N_COLD,max_u-min_u);

        /* ═══ 2. Hamming distances between cold starts ═══ */
        double sum_hamming=0; int n_pairs=0;
        int min_h=n, max_h=0;
        for(int i=0;i<N_COLD;i++)for(int j=i+1;j<N_COLD;j++){
            int h=0;for(int v=0;v<n;v++)if(cold_a[i][v]!=cold_a[j][v])h++;
            sum_hamming+=h;n_pairs++;
            if(h<min_h)min_h=h;if(h>max_h)max_h=h;}
        printf("  Hamming between starts: min=%d, max=%d, avg=%.0f (%.0f%%)\n",
               min_h,max_h,sum_hamming/n_pairs,100*sum_hamming/(n_pairs*n));

        /* ═══ 3. Per-var agreement: how many cold starts agree? ═══ */
        int always_same=0, mostly_same=0, split=0;
        double p1_vals[MAX_N];
        for(int v=0;v<n;v++){
            int sum=0;for(int r=0;r<N_COLD;r++)sum+=cold_a[r][v];
            p1_vals[v]=(double)sum/N_COLD;
            if(p1_vals[v]>=0.9||p1_vals[v]<=0.1)always_same++;
            else if(p1_vals[v]>=0.7||p1_vals[v]<=0.3)mostly_same++;
            else split++;}
        printf("  Vars: %d always same (>90%%), %d mostly (%d-%d%%), %d split\n",
               always_same,mostly_same,70,90,split);

        /* ═══ 4. COLD MAJORITY VOTE: combine 20 starts ═══ */
        int majority[MAX_N];
        for(int v=0;v<n;v++)majority[v]=(p1_vals[v]>0.5)?1:0;
        int maj_sat=eval_a(majority);
        printf("  Cold majority vote: %d/%d sat (%d unsat)\n",
               maj_sat,m,m-maj_sat);

        /* WalkSAT from majority */
        memcpy(assignment,majority,sizeof(int)*n);
        recompute();rng_seed(seed*111);
        walksat_phase(n*500);
        int maj_final=count_unsat();
        printf("  Cold majority + WalkSAT: %d unsat %s\n",
               maj_final,maj_final==0?"★ SOLVED":"");

        /* ═══ 5. BEST single run + WalkSAT ═══ */
        int best_r=0;for(int r=1;r<N_COLD;r++)if(cold_unsat[r]<cold_unsat[best_r])best_r=r;
        memcpy(assignment,cold_a[best_r],sizeof(int)*n);
        recompute();rng_seed(seed*222);
        walksat_phase(n*500);
        int best_final=count_unsat();
        printf("  Best single (%d unsat) + WalkSAT: %d unsat %s\n",
               cold_unsat[best_r],best_final,best_final==0?"★ SOLVED":"");

        /* ═══ 6. UNSAT CLAUSE OVERLAP: same clauses across starts? ═══ */
        int clause_unsat_count[MAX_CLAUSES];memset(clause_unsat_count,0,sizeof(int)*m);
        for(int r=0;r<N_COLD;r++){
            memcpy(assignment,cold_a[r],sizeof(int)*n);recompute();
            for(int ci=0;ci<m;ci++)if(clause_sc[ci]==0)clause_unsat_count[ci]++;}
        int always_unsat=0, sometimes_unsat=0, never_unsat=0;
        for(int ci=0;ci<m;ci++){
            if(clause_unsat_count[ci]==N_COLD)always_unsat++;
            else if(clause_unsat_count[ci]>0)sometimes_unsat++;
            else never_unsat++;}
        printf("  Clauses: %d always unsat, %d sometimes, %d never\n",
               always_unsat,sometimes_unsat,never_unsat);

        /* ═══ 7. WEIGHTED MAJORITY: weight by sat score ═══ */
        double weighted[MAX_N];memset(weighted,0,sizeof(double)*n);
        double total_w=0;
        for(int r=0;r<N_COLD;r++){
            double w=cold_sat_score[r]; /* weight = how good this run is */
            total_w+=w;
            for(int v=0;v<n;v++)weighted[v]+=w*cold_a[r][v];}
        int wmaj[MAX_N];
        for(int v=0;v<n;v++)wmaj[v]=(weighted[v]/total_w>0.5)?1:0;
        int wmaj_sat=eval_a(wmaj);
        memcpy(assignment,wmaj,sizeof(int)*n);recompute();rng_seed(seed*333);
        walksat_phase(n*500);
        int wmaj_final=count_unsat();
        printf("  Weighted majority: %d/%d sat, +WalkSAT: %d unsat %s\n",
               wmaj_sat,m,wmaj_final,wmaj_final==0?"★ SOLVED":"");

        printf("\n");
    }
    return 0;
}
