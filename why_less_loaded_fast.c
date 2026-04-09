/*
 * WHY IS THE ONE LESS LOADED? — Fast C version
 * No keystone search needed! Just:
 * 1. Physics → assignment (99% sat)
 * 2. Find unsat clause → 3 suspects
 * 3. Measure critical count + match_ratio for each
 * 4. Compare THE ONE vs innocents (using MiniSat for ground truth)
 *
 * Compile: gcc -O3 -march=native -o why_fast why_less_loaded_fast.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      2000
#define MAX_CLAUSES 10000
#define MAX_K      3
#define MAX_DEGREE 100

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

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
static double rng_normal(double m,double s){
    double u1=(rng_next()>>11)*(1.0/9007199254740992.0);
    double u2=(rng_next()>>11)*(1.0/9007199254740992.0);
    if(u1<1e-15)u1=1e-15;
    return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
    rng_seed(seed);memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];
            cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];if(vdeg[v]<MAX_DEGREE){
                vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
}

static int eval_a(const int *a){
    int sat=0;for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            if((s==1&&a[v]==1)||(s==-1&&a[v]==0)){sat++;break;}}
    return sat;}

/* Physics */
static double x[MAX_N],vel[MAX_N];
static void physics(int steps,unsigned long long seed){
    int n=n_vars,m=n_clauses;rng_seed(seed);
    for(int v=0;v<n;v++){double p1=0,p0=0;
        for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
            if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}
        x[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}
    double force[MAX_N];
    for(int step=0;step<steps;step++){double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++){double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                lit[j]=(s==1)?x[v]:(1.0-x[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){if(x[v]>0.5)force[v]+=cr*(1-x[v]);else force[v]-=cr*x[v];
            vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;
            x[v]+=vel[v]*0.05;
            if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}
}

/* WalkSAT */
static int walksat(int *a, int flips){
    int m=n_clauses,n=n_vars;
    int sc[MAX_CLAUSES];
    for(int ci=0;ci<m;ci++){sc[ci]=0;for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&a[v]==1)||(s==-1&&a[v]==0))sc[ci]++;}}
    int u[MAX_CLAUSES],up[MAX_CLAUSES],nu=0;
    memset(up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(sc[ci]==0){up[ci]=nu;u[nu++]=ci;}
    for(int f=0;f<flips&&nu>0;f++){
        int ci=u[rng_next()%nu];int bv=cl_var[ci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&a[v]==1)||(os==-1&&a[v]==0))&&sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[ci][rng_next()%3]:bv);
        int old=a[fv],nw=1-old;a[fv]=nw;
        for(int d=0;d<vdeg[fv];d++){int oci=vlist[fv][d],opos=vpos[fv][d];
            int os=cl_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){sc[oci]--;if(sc[oci]==0){up[oci]=nu;u[nu++]=oci;}}
            else if(!was&&now){sc[oci]++;if(sc[oci]==1){int p=up[oci];
                if(p>=0&&p<nu){int l=u[nu-1];u[p]=l;up[l]=p;up[oci]=-1;nu--;}}}}}
    return m-nu;}

/* ════════════════════════════════════════════════
 * MEASURE: For each suspect in unsat clause
 * critical = clauses where suspect is ONLY saver
 * match_ratio = fraction of literal signs matching current value
 * ════════════════════════════════════════════════ */

typedef struct {
    int critical;       /* clauses where v is only saver */
    int match_signs;    /* literal appearances matching current value */
    int total_signs;    /* total literal appearances */
    int flip_delta;     /* Δsat if we flip v */
} SuspectInfo;

static void measure_suspect(int v, const int *a, SuspectInfo *info) {
    int n = n_vars, m = n_clauses;
    info->critical = 0;
    info->match_signs = 0;
    info->total_signs = 0;

    for(int d = 0; d < vdeg[v]; d++) {
        int ci = vlist[v][d], pos = vpos[v][d];
        int s = cl_sign[ci][pos];

        info->total_signs++;
        if((s==1 && a[v]==1) || (s==-1 && a[v]==0))
            info->match_signs++;

        /* Is v the ONLY saver of this clause? */
        int n_savers = 0;
        int v_saves = 0;
        for(int j = 0; j < 3; j++) {
            int vj = cl_var[ci][j], sj = cl_sign[ci][j];
            if((sj==1 && a[vj]==1) || (sj==-1 && a[vj]==0)) {
                n_savers++;
                if(vj == v) v_saves = 1;
            }
        }
        if(n_savers == 1 && v_saves)
            info->critical++;
    }

    /* flip_delta */
    int ta[MAX_N]; memcpy(ta, a, sizeof(int)*n);
    ta[v] = 1 - ta[v];
    info->flip_delta = eval_a(ta) - eval_a(a);
}

int main(void) {
    printf("═══════════════════════════════════════════════════\n");
    printf("WHY LESS LOADED — Fast C, n=50-500\n");
    printf("═══════════════════════════════════════════════════\n\n");

    int test_n[] = {50, 100, 200, 300, 500};
    int sizes = 5;

    /* Accumulate stats */
    double one_critical_sum=0, inn_critical_sum=0;
    double one_match_sum=0, inn_match_sum=0;
    double one_delta_sum=0, inn_delta_sum=0;
    int one_count=0, inn_count=0;
    int one_identified=0; /* how often min(critical) picks THE ONE */

    for(int ti = 0; ti < sizes; ti++) {
        int nn = test_n[ti];
        int n_inst = (nn <= 200) ? 30 : 15;
        int steps = 2000 + nn*15;

        int loc_one_id = 0, loc_total = 0;
        double loc_one_crit=0, loc_inn_crit=0;
        double loc_one_match=0, loc_inn_match=0;
        double loc_one_delta=0, loc_inn_delta=0;
        int loc_one_n=0, loc_inn_n=0;

        for(int seed = 0; seed < n_inst*5 && loc_total < n_inst; seed++) {
            generate(nn, 4.267, 23000000ULL + seed);

            /* Physics → assignment */
            physics(steps, 42 + seed*31);
            int a[MAX_N];
            for(int v=0;v<nn;v++) a[v]=(x[v]>0.5)?1:0;
            int sat = eval_a(a);

            /* WalkSAT to get close to solution */
            rng_seed(seed*777);
            sat = walksat(a, nn*300);

            int m = n_clauses;
            if(sat < m - 5 || sat == m) continue; /* only near-misses */

            /* Find first unsat clause */
            int uci = -1;
            for(int ci=0;ci<m;ci++){
                int ok=0;
                for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                    if((s==1&&a[v]==1)||(s==-1&&a[v]==0)){ok=1;break;}}
                if(!ok){uci=ci;break;}}
            if(uci < 0) continue;

            /* Measure 3 suspects */
            SuspectInfo info[3];
            for(int j=0;j<3;j++)
                measure_suspect(cl_var[uci][j], a, &info[j]);

            /* Find which one has positive flip_delta (THE ONE candidate) */
            /* Actually: the one with highest flip_delta */
            int best_j = 0;
            for(int j=1;j<3;j++)
                if(info[j].flip_delta > info[best_j].flip_delta) best_j=j;

            /* Does min(critical) identify the same one? */
            int min_crit_j = 0;
            for(int j=1;j<3;j++)
                if(info[j].critical < info[min_crit_j].critical) min_crit_j=j;

            /* Does min(match_ratio) identify? */
            int min_match_j = 0;
            for(int j=1;j<3;j++){
                double mr_j = (double)info[j].match_signs / fmax(info[j].total_signs,1);
                double mr_m = (double)info[min_match_j].match_signs / fmax(info[min_match_j].total_signs,1);
                if(mr_j < mr_m) min_match_j=j;
            }

            loc_total++;
            if(min_crit_j == best_j) loc_one_id++;

            for(int j=0;j<3;j++){
                int is_best = (j == best_j);
                double mr = (double)info[j].match_signs / fmax(info[j].total_signs,1);
                if(is_best){
                    loc_one_crit += info[j].critical;
                    loc_one_match += mr;
                    loc_one_delta += info[j].flip_delta;
                    loc_one_n++;
                } else {
                    loc_inn_crit += info[j].critical;
                    loc_inn_match += mr;
                    loc_inn_delta += info[j].flip_delta;
                    loc_inn_n++;
                }
            }
        }

        if(loc_total > 0 && loc_one_n > 0 && loc_inn_n > 0) {
            printf("n=%4d (%2d instances):\n", nn, loc_total);
            printf("  critical:    ONE=%.2f  INN=%.2f  ratio=%.2f\n",
                   loc_one_crit/loc_one_n, loc_inn_crit/loc_inn_n,
                   (loc_one_crit/loc_one_n) / fmax(loc_inn_crit/loc_inn_n, 0.01));
            printf("  match_ratio: ONE=%.3f  INN=%.3f  ratio=%.2f\n",
                   loc_one_match/loc_one_n, loc_inn_match/loc_inn_n,
                   (loc_one_match/loc_one_n) / fmax(loc_inn_match/loc_inn_n, 0.01));
            printf("  flip_delta:  ONE=%.2f  INN=%.2f\n",
                   loc_one_delta/loc_one_n, loc_inn_delta/loc_inn_n);
            printf("  min(critical) finds THE ONE: %d/%d = %.0f%%\n\n",
                   loc_one_id, loc_total, 100.0*loc_one_id/loc_total);
        }

        one_critical_sum += loc_one_crit; inn_critical_sum += loc_inn_crit;
        one_match_sum += loc_one_match; inn_match_sum += loc_inn_match;
        one_count += loc_one_n; inn_count += loc_inn_n;
        one_identified += loc_one_id;
    }

    if(one_count > 0 && inn_count > 0) {
        printf("═══ OVERALL ═══\n");
        printf("critical:    ONE=%.2f  INN=%.2f  ratio=%.2f\n",
               one_critical_sum/one_count, inn_critical_sum/inn_count,
               (one_critical_sum/one_count)/fmax(inn_critical_sum/inn_count,0.01));
        printf("match_ratio: ONE=%.3f  INN=%.3f\n",
               one_match_sum/one_count, inn_match_sum/inn_count);
        printf("min(critical) detection rate: %d (overall)\n", one_identified);
    }

    return 0;
}
