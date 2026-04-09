/*
 * THREE NEW IDEAS + COMBINATIONS from Bit Mechanics theory
 * ═══════════════════════════════════════════════════════
 *
 * A: CASCADE AMPLIFIER — multi-stage information amplification
 * B: CONSERVATION BREAK — inject external info to break E/S barrier
 * C: REVERSE PHYSICS — subtract vacuum force, expose pure error
 *
 * + combinations: A+B, A+C, B+C, A+B+C
 *
 * Compile: gcc -O3 -march=native -o three_ideas three_ideas.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      5000
#define MAX_CLAUSES 25000
#define MAX_K      3
#define MAX_DEGREE 200

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
static double rng_double(void){return(rng_next()>>11)*(1.0/9007199254740992.0);}
static double rng_normal(double m,double s){
    double u1=rng_double(),u2=rng_double();if(u1<1e-15)u1=1e-15;
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

static int evaluate(const int*a){
    int sat=0;for(int ci=0;ci<n_clauses;ci++)
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            if((s==1&&a[v]==1)||(s==-1&&a[v]==0)){sat++;break;}}
    return sat;}

/* ═══ PHYSICS ENGINE ═══ */
static double x[MAX_N], vel[MAX_N];

static void compute_tension(double *tension) {
    int n=n_vars;
    for(int v=0;v<n;v++){
        double p1=0,p0=0;
        for(int d=0;d<vdeg[v];d++){
            int ci=vlist[v][d],p=vpos[v][d];
            if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}
        tension[v]=(p1+p0>0)?(p1-p0)/(p1+p0):0;
    }
}

static void physics_step(int n, double T, double crystal, double dt) {
    int m=n_clauses;
    double force[MAX_N]; memset(force,0,sizeof(double)*n);
    for(int ci=0;ci<m;ci++){
        double lit[3],prod=1.0;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            lit[j]=(s==1)?x[v]:(1.0-x[v]);
            double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
        if(prod<0.0001)continue;double w=sqrt(prod);
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            double t=1.0-lit[j];if(t<1e-12)t=1e-12;
            force[v]+=s*w*(prod/t);}}
    for(int v=0;v<n;v++){
        if(x[v]>0.5)force[v]+=crystal*(1-x[v]);else force[v]-=crystal*x[v];
        vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*dt;
        x[v]+=vel[v]*dt;
        if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
        if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}
}

/* WalkSAT */
static int ws_solve(int *a, int max_flips){
    int m=n_clauses,n=n_vars;
    int sc[MAX_CLAUSES];
    for(int ci=0;ci<m;ci++){sc[ci]=0;for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&a[v]==1)||(s==-1&&a[v]==0))sc[ci]++;}}
    int unsat[MAX_CLAUSES],up[MAX_CLAUSES],nu=0;
    memset(up,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(sc[ci]==0){up[ci]=nu;unsat[nu++]=ci;}
    for(int f=0;f<max_flips&&nu>0;f++){
        int ci=unsat[rng_next()%nu];
        int bv=cl_var[ci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){
                int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];
                if(((os==1&&a[v]==1)||(os==-1&&a[v]==0))&&sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[ci][rng_next()%3]:bv);
        int old=a[fv],nw=1-old;a[fv]=nw;
        for(int d=0;d<vdeg[fv];d++){
            int oci=vlist[fv][d],opos=vpos[fv][d],os=cl_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){sc[oci]--;if(sc[oci]==0){up[oci]=nu;unsat[nu++]=oci;}}
            else if(!was&&now){sc[oci]++;if(sc[oci]==1){int p=up[oci];
                if(p>=0&&p<nu){int l=unsat[nu-1];unsat[p]=l;up[l]=p;up[oci]=-1;nu--;}}}}}
    return m-nu;}

/* ═════════════════════════════════════════════
 * IDEA A: CASCADE AMPLIFIER
 *
 * Stage 1: physics → 99% (amplification 4.45×)
 * Stage 2: EXTRACT residual, re-run physics on residual
 *          with BOOSTED parameters (more steps, slower cooling)
 * Stage 3: Extract 2nd residual, boost again
 * Each stage amplifies the remaining signal further
 * ═════════════════════════════════════════════ */

static int idea_A_cascade(int n, int stages) {
    int m = n_clauses;
    double tension[MAX_N];
    compute_tension(tension);

    /* Stage 1: standard physics */
    for(int v=0;v<n;v++){x[v]=0.5+0.35*tension[v];vel[v]=0;}
    int steps1 = 1000 + n*10;
    for(int s=0;s<steps1;s++){
        double prog=(double)s/steps1;
        physics_step(n, 0.25*exp(-4*prog)+0.0001, 3.0*prog, 0.05);
    }
    int a[MAX_N];
    for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;
    if(evaluate(a)==m) return m;

    /* Stages 2+: find unsat region, re-run physics with focus */
    for(int stage=1; stage<stages; stage++) {
        /* Find unsat clauses and their variables */
        double weight[MAX_N]; memset(weight,0,sizeof(double)*n);
        int n_unsat = 0;
        for(int ci=0;ci<m;ci++){
            int sat=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                if((s==1&&a[v]==1)||(s==-1&&a[v]==0))sat=1;}
            if(!sat){
                n_unsat++;
                for(int j=0;j<3;j++) weight[cl_var[ci][j]] += 1.0;
                /* Also weight 2-hop neighbors */
                for(int j=0;j<3;j++){int v=cl_var[ci][j];
                    for(int d=0;d<vdeg[v]&&d<20;d++){
                        int oci=vlist[v][d];
                        for(int jj=0;jj<3;jj++)
                            weight[cl_var[oci][jj]]+=0.3;}}
            }
        }
        if(n_unsat==0) return m;

        /* Normalize weights */
        double max_w=0;
        for(int v=0;v<n;v++) if(weight[v]>max_w) max_w=weight[v];
        if(max_w>0) for(int v=0;v<n;v++) weight[v]/=max_w;

        /* Re-init: melt weighted region toward 0.5, keep the rest */
        for(int v=0;v<n;v++){
            double melt = weight[v]; /* 0=keep, 1=full melt */
            x[v] = x[v]*(1-melt*0.8) + 0.5*melt*0.8;
            vel[v] *= (1-melt);
        }

        /* Re-run physics with BOOSTED parameters */
        int steps_boost = 500 + n_unsat * 100; /* more steps per unsat clause */
        for(int s=0;s<steps_boost;s++){
            double prog=(double)s/steps_boost;
            double T = 0.15*exp(-3.0*prog)+0.0001;
            double crystal = 2.0 + 5.0*prog;
            /* Boost force on weighted vars */
            double force[MAX_N]; memset(force,0,sizeof(double)*n);
            for(int ci=0;ci<m;ci++){
                double lit[3],prod=1.0;
                for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];
                    lit[j]=(ss==1)?x[v]:(1.0-x[v]);
                    double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
                if(prod<0.0001)continue;
                double w=sqrt(prod)*(1.0+weight[cl_var[ci][0]]); /* boost */
                for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];
                    double t=1.0-lit[j];if(t<1e-12)t=1e-12;
                    force[v]+=ss*w*(prod/t);}}
            for(int v=0;v<n;v++){
                if(x[v]>0.5)force[v]+=crystal*(1-x[v]);
                else force[v]-=crystal*x[v];
                double noise = rng_normal(0,T) * (1+weight[v]);
                vel[v]=0.93*vel[v]+(force[v]+noise)*0.04;
                x[v]+=vel[v]*0.04;
                if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
                if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}
        }

        for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;
        if(evaluate(a)==m) return m;
    }

    return evaluate(a);
}

/* ═════════════════════════════════════════════
 * IDEA B: CONSERVATION BREAK
 *
 * E/S = 0.6 = const normally. Break it by injecting
 * external information: tension as a BIAS FIELD.
 *
 * Normal physics: F = clause_force + crystal + noise
 * Conservation break: F = clause_force + crystal + noise + λ·tension
 *
 * The tension field adds EXTERNAL information that
 * changes the E/S trajectory, potentially avoiding
 * the local minimum that traps standard physics.
 * ═════════════════════════════════════════════ */

static int idea_B_conservation_break(int n) {
    int m = n_clauses;
    double tension[MAX_N];
    compute_tension(tension);

    /* Init from tension */
    for(int v=0;v<n;v++){x[v]=0.5+0.35*tension[v];vel[v]=0;}

    int steps = 2000 + n*15;
    int a[MAX_N];
    int best_sat = 0;

    for(int s=0;s<steps;s++){
        double prog=(double)s/steps;
        double T=0.25*exp(-4*prog)+0.0001;
        double crystal=3.0*prog;

        /* Conservation-breaking parameter:
         * Strong at start (inject info), weakens as system converges */
        double lambda = 0.5 * (1.0 - prog); /* 0.5 → 0 */

        double force[MAX_N]; memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++){
            double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];
                lit[j]=(ss==1)?x[v]:(1.0-x[v]);
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;
                force[v]+=ss*w*(prod/t);}}

        for(int v=0;v<n;v++){
            if(x[v]>0.5)force[v]+=crystal*(1-x[v]);
            else force[v]-=crystal*x[v];
            /* CONSERVATION BREAK: add tension as external bias */
            force[v] += lambda * tension[v] * 2.0;
            vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;
            x[v]+=vel[v]*0.05;
            if(x[v]<0){x[v]=0.01;vel[v]=fabs(vel[v])*0.3;}
            if(x[v]>1){x[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}
        }

        if(s%50==49){
            for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;
            int sat=evaluate(a);
            if(sat>best_sat) best_sat=sat;
            if(sat==m) return m;
        }
    }
    for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;
    return evaluate(a);
}

/* ═════════════════════════════════════════════
 * IDEA C: REVERSE PHYSICS
 *
 * After physics: x_final is the result.
 * Vacuum force (tension) pushed x in a direction.
 * SUBTRACT the vacuum force to expose the ERROR field.
 *
 * error_field[v] = x_final[v] - (0.5 + 0.35*tension[v])
 * The error field = what physics CHANGED beyond tension.
 * Variables where error_field contradicts the final value
 * are candidates for being WRONG.
 *
 * Then: use error field to CORRECT the assignment.
 * ═════════════════════════════════════════════ */

static int idea_C_reverse(int n) {
    int m = n_clauses;
    double tension[MAX_N];
    compute_tension(tension);

    /* Run standard physics */
    for(int v=0;v<n;v++){x[v]=0.5+0.35*tension[v];vel[v]=0;}
    int steps = 1500 + n*10;
    for(int s=0;s<steps;s++){
        double prog=(double)s/steps;
        physics_step(n, 0.25*exp(-4*prog)+0.0001, 3.0*prog, 0.05);
    }

    int a[MAX_N];
    for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;
    if(evaluate(a)==m) return m;

    /* Compute error field: what did physics add beyond tension? */
    double error[MAX_N];
    for(int v=0;v<n;v++){
        double tension_prediction = 0.5 + 0.35*tension[v];
        error[v] = x[v] - tension_prediction;
    }

    /* Variables where error field CONTRADICTS the assignment
     * are suspicious: physics pushed them AWAY from tension
     * but they ended up there → might be wrong */
    double suspicion[MAX_N];
    for(int v=0;v<n;v++){
        /* If a[v]=1 (x>0.5) but error pushed toward 0: suspicious */
        /* If a[v]=0 (x<0.5) but error pushed toward 1: suspicious */
        double expected_dir = (a[v]==1) ? 1.0 : -1.0;
        double error_dir = (error[v] > 0) ? 1.0 : -1.0;
        /* Suspicion: high when directions disagree AND magnitude is large */
        if(expected_dir * error_dir < 0) {
            suspicion[v] = fabs(error[v]);
        } else {
            suspicion[v] = -fabs(error[v]); /* negative = unsuspicious */
        }
    }

    /* Flip most suspicious variables */
    for(int k=1; k<=20 && k<=n/4; k++){
        /* Find k-th most suspicious */
        int sorted[MAX_N]; for(int v=0;v<n;v++) sorted[v]=v;
        for(int i=0;i<k;i++) for(int j=i+1;j<n;j++)
            if(suspicion[sorted[j]]>suspicion[sorted[i]])
                {int t=sorted[i];sorted[i]=sorted[j];sorted[j]=t;}

        int test[MAX_N]; memcpy(test,a,sizeof(int)*n);
        for(int i=0;i<k;i++) test[sorted[i]]=1-test[sorted[i]];
        int sat=evaluate(test);
        if(sat==m) return m;
    }

    return evaluate(a);
}

/* ═════════════════════════════════════════════
 * COMBINATIONS
 * ═════════════════════════════════════════════ */

static int combo_ABC(int n) {
    int m = n_clauses;

    /* B first: conservation-breaking physics */
    int sat_B = idea_B_conservation_break(n);
    if(sat_B == m) return m;

    /* Save state, try C (reverse analysis) on B's output */
    double x_save[MAX_N]; memcpy(x_save, x, sizeof(double)*n);

    /* C: reverse physics on B's result */
    /* x already has B's result, compute error field */
    double tension[MAX_N]; compute_tension(tension);
    int a[MAX_N];
    for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;

    double error[MAX_N], suspicion[MAX_N];
    for(int v=0;v<n;v++){
        error[v] = x[v] - (0.5+0.35*tension[v]);
        double ed = (error[v]>0)?1:-1;
        double ad = (a[v]==1)?1:-1;
        suspicion[v] = (ed*ad<0) ? fabs(error[v]) : -fabs(error[v]);
    }

    /* Try flipping suspicious from B's result */
    for(int k=1;k<=15;k++){
        int sorted[MAX_N]; for(int v=0;v<n;v++) sorted[v]=v;
        for(int i=0;i<k;i++) for(int j=i+1;j<n;j++)
            if(suspicion[sorted[j]]>suspicion[sorted[i]])
                {int t=sorted[i];sorted[i]=sorted[j];sorted[j]=t;}
        int test[MAX_N]; memcpy(test,a,sizeof(int)*n);
        for(int i=0;i<k;i++) test[sorted[i]]=1-test[sorted[i]];
        if(evaluate(test)==m) return m;
    }

    /* A: cascade amplification on whatever's left */
    memcpy(x, x_save, sizeof(double)*n);
    int sat_A = idea_A_cascade(n, 3);
    if(sat_A == m) return m;

    /* Final WalkSAT from best */
    for(int v=0;v<n;v++) a[v]=(x[v]>0.5)?1:0;
    rng_seed(n*777);
    return ws_solve(a, n*500);
}

/* ═════════════════════════════════════════════
 * BENCHMARK
 * ═════════════════════════════════════════════ */

int main(void){
    printf("═══════════════════════════════════════════════════\n");
    printf("THREE IDEAS FROM BIT MECHANICS + COMBINATIONS\n");
    printf("═══════════════════════════════════════════════════\n\n");

    int test_n[]={50,100,200,300,500,750,1000};
    int sizes=7;

    printf("%6s | %4s | %4s | %4s | %4s | %4s | %8s\n",
           "n","A","B","C","A+B+C","+ws","time_ms");
    printf("-------+------+------+------+------+------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?20:(nn<=500?10:5);

        int sA=0,sB=0,sC=0,sABC=0,sWS=0,total=0;
        double tms=0;

        for(int seed=0;seed<ni*3&&total<ni;seed++){
            generate(nn,4.267,12000000ULL+seed);
            clock_t t0=clock();

            /* A: Cascade */
            rng_seed(seed*111);
            int satA=idea_A_cascade(nn,3);
            if(satA==n_clauses) sA++;

            /* B: Conservation break */
            rng_seed(seed*222);
            int satB=idea_B_conservation_break(nn);
            if(satB==n_clauses) sB++;

            /* C: Reverse */
            rng_seed(seed*333);
            int satC=idea_C_reverse(nn);
            if(satC==n_clauses) sC++;

            /* A+B+C combo */
            rng_seed(seed*444);
            int satABC=combo_ABC(nn);
            if(satABC==n_clauses) sABC++;

            /* +WS: best of all + WalkSAT */
            int best=satA; if(satB>best)best=satB; if(satC>best)best=satC; if(satABC>best)best=satABC;
            if(best<n_clauses){
                int a[MAX_N]; for(int v=0;v<nn;v++) a[v]=(x[v]>0.5)?1:0;
                rng_seed(seed*555);
                int satWS=ws_solve(a,nn*500);
                if(satWS==n_clauses) sWS++;
            } else sWS++;

            total++;
            clock_t t1=clock();
            tms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
        }

        printf("%6d | %2d/%2d| %2d/%2d| %2d/%2d| %2d/%2d| %2d/%2d| %7.0fms\n",
               nn,sA,total,sB,total,sC,total,sABC,total,sWS,total,tms/total);
        fflush(stdout);
    }

    printf("\nComparison: PhysicsSAT=3/20@500, SP_correct=2/5@750\n");
    return 0;
}
