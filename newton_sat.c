/*
 * NEWTON-LIKE SAT: Second-order method to accelerate convergence
 * ═══════════════════════════════════════════════════════════════
 *
 * ADAM slows exponentially near saddle points.
 * Newton method uses CURVATURE (Hessian) to jump directly.
 *
 * Full Hessian = O(n²) storage = too expensive.
 * Instead: TARGETED NEWTON — only on the ~√n "middle" vars.
 *
 * Algorithm:
 * 1. ADAM for bulk (first 50K steps) → most vars converge
 * 2. Identify "middle" vars (|x-0.5| < 0.3) → ~√n vars
 * 3. For middle vars: compute LOCAL Hessian (only their interactions)
 * 4. Newton step on middle vars: Δx = -H⁻¹ ∇f
 * 5. Repeat until converged
 *
 * The key insight: only √n vars are stuck. The n²×n² Hessian
 * is actually only √n × √n for the stuck vars = O(n) size.
 *
 * Compile: gcc -O3 -march=native -o newton newton_sat.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N      1000
#define MAX_CLAUSES 5000
#define MAX_K      3
#define MAX_MID    100 /* max middle vars for Newton */

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);rng_seed(seed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;}}}

static int eval_disc(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static double x[MAX_N];

static void compute_grad(double *grad){
    int n=n_vars;memset(grad,0,sizeof(double)*n);
    for(int ci=0;ci<n_clauses;ci++){
        double lit[3],prod=1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            lit[j]=(s==1)?x[v]:(1-x[v]);double t=1-lit[j];if(t<1e-15)t=1e-15;prod*=t;}
        if(prod<1e-15)continue;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
            double t=1-lit[j];if(t<1e-15)t=1e-15;grad[v]+=s*(prod/t);}}}

/* ADAM phase */
static void adam_phase(int steps){
    int n=n_vars;
    double m_a[MAX_N],v_a[MAX_N];
    memset(m_a,0,sizeof(double)*n);memset(v_a,0,sizeof(double)*n);
    double b1=0.9,b2=0.999,lr=0.001;

    for(int step=0;step<steps;step++){
        double grad[MAX_N];compute_grad(grad);
        for(int v=0;v<n;v++){
            m_a[v]=b1*m_a[v]+(1-b1)*grad[v];
            v_a[v]=b2*v_a[v]+(1-b2)*grad[v]*grad[v];
            double mh=m_a[v]/(1-pow(b1,step+1));
            double vh=v_a[v]/(1-pow(b2,step+1));
            x[v]+=lr*mh/(sqrt(vh)+1e-8);
            if(x[v]<1e-6)x[v]=1e-6;if(x[v]>1-1e-6)x[v]=1-1e-6;
        }
    }
}

/* Targeted Newton on middle vars only */
static int newton_step(double threshold){
    int n=n_vars,m=n_clauses;

    /* Find middle vars */
    int mid[MAX_MID],nmid=0;
    int mid_idx[MAX_N]; memset(mid_idx,-1,sizeof(int)*n);
    for(int v=0;v<n&&nmid<MAX_MID;v++){
        if(fabs(x[v]-0.5)<threshold){mid[nmid]=v;mid_idx[v]=nmid;nmid++;}}

    if(nmid==0)return 0;
    if(nmid>MAX_MID)nmid=MAX_MID;

    /* Compute gradient for middle vars */
    double grad_mid[MAX_MID];
    double full_grad[MAX_N];
    compute_grad(full_grad);
    for(int i=0;i<nmid;i++)grad_mid[i]=full_grad[mid[i]];

    /* Compute Hessian for middle vars: H[i][j] = ∂²soft_sat/∂x_i∂x_j */
    double H[MAX_MID][MAX_MID];
    memset(H,0,sizeof(H));

    for(int ci=0;ci<m;ci++){
        double lit[3],prod=1;
        int v_in_mid[3],n_in_mid=0;
        for(int j=0;j<3;j++){
            int v=cl_var[ci][j],s=cl_sign[ci][j];
            lit[j]=(s==1)?x[v]:(1-x[v]);
            double t=1-lit[j];if(t<1e-15)t=1e-15;prod*=t;
            if(mid_idx[v]>=0)v_in_mid[n_in_mid++]=j;}
        if(n_in_mid<2||prod<1e-15)continue;

        /* Cross-derivatives: ∂²/∂x_a∂x_b = s_a×s_b × prod/(t_a×t_b) */
        for(int a=0;a<n_in_mid;a++){
            for(int b=a+1;b<n_in_mid;b++){
                int ja=v_in_mid[a],jb=v_in_mid[b];
                int va=cl_var[ci][ja],vb=cl_var[ci][jb];
                int sa=cl_sign[ci][ja],sb=cl_sign[ci][jb];
                double ta=1-lit[ja],tb=1-lit[jb];
                if(ta<1e-15)ta=1e-15;if(tb<1e-15)tb=1e-15;
                double d2=-sa*sb*prod/(ta*tb); /* negative because maximizing */
                int ia=mid_idx[va],ib=mid_idx[vb];
                if(ia>=0&&ib>=0&&ia<nmid&&ib<nmid){
                    H[ia][ib]+=d2;H[ib][ia]+=d2;}}
        }

        /* Diagonal: ∂²/∂x_a² */
        for(int a=0;a<n_in_mid;a++){
            int ja=v_in_mid[a];
            int va=cl_var[ci][ja];
            double ta=1-lit[ja];if(ta<1e-15)ta=1e-15;
            /* For product formula: ∂²sat/∂x² involves second derivative of product */
            /* Approximate diagonal Hessian: ∂²/∂x² ≈ -prod/(t²) for the lit term */
            int ia=mid_idx[va];
            if(ia>=0&&ia<nmid)
                H[ia][ia]+=-prod/(ta*ta);
        }
    }

    /* Regularize: H → H - λI (make negative definite for maximization) */
    for(int i=0;i<nmid;i++) H[i][i]-=0.1;

    /* Solve H × Δx = -grad using Gauss elimination */
    double aug[MAX_MID][MAX_MID+1];
    for(int i=0;i<nmid;i++){
        for(int j=0;j<nmid;j++) aug[i][j]=H[i][j];
        aug[i][nmid]=-grad_mid[i];}

    /* Gaussian elimination with partial pivoting */
    for(int col=0;col<nmid;col++){
        int piv=col;double pmax=fabs(aug[col][col]);
        for(int row=col+1;row<nmid;row++)
            if(fabs(aug[row][col])>pmax){pmax=fabs(aug[row][col]);piv=row;}
        if(pmax<1e-12)continue;
        if(piv!=col)for(int j=0;j<=nmid;j++){double t=aug[col][j];aug[col][j]=aug[piv][j];aug[piv][j]=t;}
        for(int row=col+1;row<nmid;row++){
            double f=aug[row][col]/aug[col][col];
            for(int j=col;j<=nmid;j++)aug[row][j]-=f*aug[col][j];}}

    /* Back-substitute */
    double dx[MAX_MID];
    for(int i=nmid-1;i>=0;i--){
        dx[i]=aug[i][nmid];
        for(int j=i+1;j<nmid;j++)dx[i]-=aug[i][j]*dx[j];
        if(fabs(aug[i][i])>1e-12)dx[i]/=aug[i][i];else dx[i]=0;
        /* Clamp step size */
        if(dx[i]>0.3)dx[i]=0.3;if(dx[i]<-0.3)dx[i]=-0.3;
    }

    /* Apply Newton step */
    for(int i=0;i<nmid;i++){
        x[mid[i]]+=dx[i];
        if(x[mid[i]]<1e-6)x[mid[i]]=1e-6;
        if(x[mid[i]]>1-1e-6)x[mid[i]]=1-1e-6;
    }

    return nmid;
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("NEWTON-LIKE SAT: ADAM + targeted Newton\n");
    printf("══════════════════════════════════════════\n\n");

    int test_n[]={50,100,200,300,500};
    int sizes=5;

    printf("%6s | %5s | %6s | %6s | %8s\n","n","total","newton","adam_o","time_ms");
    printf("-------+-------+--------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=100)?10:(nn<=300?5:3);
        int s_newton=0,s_adam=0,total=0;double tms=0;

        for(int seed=0;seed<ni*3&&total<ni;seed++){
            generate(nn,4.267,64000000ULL+seed);
            int m=n_clauses,n=nn;
            clock_t t0=clock();

            /* ═══ Method 1: ADAM + Newton ═══ */
            rng_seed(seed*111);
            for(int v=0;v<n;v++)x[v]=0.3+0.4*((rng_next()%10000)/10000.0);

            /* Phase 1: ADAM warmup */
            adam_phase(50000);

            /* Phase 2: Newton iterations on middle vars */
            for(int iter=0;iter<200;iter++){
                int nmid=newton_step(0.4);
                if(nmid==0)break;
                /* Interleave with short ADAM */
                adam_phase(500);
            }

            /* Final ADAM polish */
            adam_phase(100000);

            int a[MAX_N];for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
            int newton_sat=eval_disc(a);
            if(newton_sat==m)s_newton++;

            /* ═══ Method 2: Pure ADAM (same total budget) ═══ */
            rng_seed(seed*111);
            for(int v=0;v<n;v++)x[v]=0.3+0.4*((rng_next()%10000)/10000.0);
            adam_phase(250000); /* same total compute */
            for(int v=0;v<n;v++)a[v]=(x[v]>0.5)?1:0;
            int adam_sat=eval_disc(a);
            if(adam_sat==m)s_adam++;

            total++;
            clock_t t1=clock();
            tms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;

            if(total<=3)
                printf("  n=%d: newton=%d/%d unsat, adam=%d/%d unsat\n",
                       nn,m-newton_sat,m,m-adam_sat,m);
        }

        printf("%6d | %2d/%2d | %4d   | %4d   | %7.0fms\n",
               nn,total,total,s_newton,s_adam,tms/total);
        fflush(stdout);
    }
    return 0;
}
