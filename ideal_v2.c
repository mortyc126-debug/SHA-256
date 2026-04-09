/*
 * IDEAL v2: Two INDEPENDENT experts, each in their zone
 * ═══════════════════════════════════════════════════════
 *
 * Expert A (Physics): good at high-tension vars
 * Expert B (SP): good at low-tension vars (cluster reasoning)
 *
 * Pipeline:
 * 1. Run Physics → assignment A, continuous x
 * 2. Run SP independently → assignment B
 * 3. For each var:
 *    if |tension| > 0.5: trust Physics (A)
 *    if |tension| < 0.2: trust SP (B)
 *    if 0.2-0.5: trust whichever has MORE confidence
 * 4. Where A and B AGREE: definitely keep
 * 5. Where A and B DISAGREE: try both, keep better
 * 6. Critical-guided finish for remaining unsat
 *
 * Compile: gcc -O3 -march=native -o ideal2 ideal_v2.c -lm
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
#define SP_MAX_ITER 300
#define SP_EPS     1e-3

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];

static unsigned long long rng_s[4];
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){double u1=(rng_next()>>11)*(1.0/9007199254740992.0),u2=(rng_next()>>11)*(1.0/9007199254740992.0);if(u1<1e-15)u1=1e-15;return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;rng_seed(seed);memset(vdeg,0,sizeof(int)*n);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
    for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;memset(var_fixed,-1,sizeof(int)*n);}

static int assignment[MAX_N];
static int clause_sc[MAX_CLAUSES];
static void recompute_sc(void){for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}}
static int count_unsat(void){int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0)c++;return c;}
static int eval_a(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static double x_cont[MAX_N];
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

static int unit_propagate(void){int changed=1;while(changed){changed=0;for(int ci=0;ci<n_clauses;ci++){if(!cl_active[ci])continue;int sat=0,fc=0,fv=-1,fs=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}else{fc++;fv=v;fs=s;}}if(sat){cl_active[ci]=0;continue;}if(fc==0)return 1;if(fc==1){var_fixed[fv]=(fs==1)?1:0;changed=1;}}}return 0;}

/* Standalone SP (completely independent from physics) */
static double eta[MAX_CLAUSES][MAX_K];

static int sp_solve_independent(int nn, int *sp_assignment){
    int n=nn,m=n_clauses;
    /* Reset */
    for(int ci=0;ci<m;ci++)cl_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)
        eta[ci][j]=(rng_next()%1000)/2000.0;

    while(1){
        int n_free=0;for(int v=0;v<n;v++)if(var_fixed[v]<0)n_free++;
        if(n_free==0)break;

        /* Converge SP */
        for(int iter=0;iter<SP_MAX_ITER;iter++){
            double maxch=0;
            for(int ci=0;ci<m;ci++){if(!cl_active[ci])continue;
                for(int p=0;p<3;p++){
                    int vi=cl_var[ci][p];if(var_fixed[vi]>=0){eta[ci][p]=0;continue;}
                    double product=1.0;
                    for(int pj=0;pj<3;pj++){if(pj==p)continue;int j=cl_var[ci][pj];
                        if(var_fixed[j]>=0){int sj=cl_sign[ci][pj];
                            if((sj==1&&var_fixed[j]==1)||(sj==-1&&var_fixed[j]==0)){product=0;break;}continue;}
                        int sja=cl_sign[ci][pj];double ps=1,pu=1;
                        for(int d=0;d<vdeg[j];d++){int bi=vlist[j][d],bp=vpos[j][d];
                            if(bi==ci||!cl_active[bi])continue;
                            int sat2=0;for(int k=0;k<3;k++){int vk=cl_var[bi][k];
                                if(var_fixed[vk]>=0){int sk=cl_sign[bi][k];
                                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))sat2=1;}}
                            if(sat2)continue;
                            int sjb=cl_sign[bi][bp];double e=eta[bi][bp];
                            if(sjb==sja)ps*=(1-e);else pu*=(1-e);}
                        double Pu=(1-pu)*ps,Ps=(1-ps)*pu,P0=pu*ps,Pc=(1-pu)*(1-ps);
                        double tot=Pu+Ps+P0+Pc;
                        product*=(tot>1e-15)?Pu/tot:0;}
                    double ne=product;double ch=fabs(ne-eta[ci][p]);if(ch>maxch)maxch=ch;
                    eta[ci][p]=0.5*ne+0.5*eta[ci][p];}}
            if(maxch<SP_EPS)break;}

        double max_eta=0;
        for(int ci=0;ci<m;ci++){if(!cl_active[ci])continue;
            for(int j=0;j<3;j++){if(var_fixed[cl_var[ci][j]]>=0)continue;
                if(eta[ci][j]>max_eta)max_eta=eta[ci][j];}}

        if(max_eta<0.01){
            /* Trivialized: assign remaining randomly by tension */
            for(int v=0;v<n;v++)if(var_fixed[v]<0){
                double p1=0,p0=0;
                for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pp=vpos[v][d];
                    if(cl_sign[ci][pp]==1)p1+=1.0/3;else p0+=1.0/3;}
                var_fixed[v]=(p1>p0)?1:0;}
            break;}

        /* Decimate */
        double Wp[MAX_N],Wm[MAX_N];
        for(int i=0;i<n;i++){Wp[i]=Wm[i]=0;if(var_fixed[i]>=0)continue;
            double pp2=1,pm2=1;
            for(int d=0;d<vdeg[i];d++){int ci=vlist[i][d],p2=vpos[i][d];
                if(!cl_active[ci])continue;
                int sat2=0;for(int k=0;k<3;k++){int vk=cl_var[ci][k];
                    if(vk!=i&&var_fixed[vk]>=0){int sk=cl_sign[ci][k];
                        if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0))sat2=1;}}
                if(sat2)continue;
                int s=cl_sign[ci][p2];double e=eta[ci][p2];
                if(s==1)pp2*=(1-e);else pm2*=(1-e);}
            double pip=(1-pp2)*pm2,pim=(1-pm2)*pp2,pi0=pp2*pm2;
            double tot=pip+pim+pi0;
            if(tot>1e-15){Wp[i]=pip/tot;Wm[i]=pim/tot;}}

        int tf=n_free/100;if(tf<1)tf=1;if(tf>20)tf=20;
        for(int f=0;f<tf;f++){
            double bb=-1;int bv=-1,bval=0;
            for(int v=0;v<n;v++){if(var_fixed[v]>=0)continue;
                double b=fabs(Wp[v]-Wm[v]);if(b>bb){bb=b;bv=v;bval=(Wp[v]>Wm[v])?1:0;}}
            if(bv<0)break;
            var_fixed[bv]=bval;
            for(int d=0;d<vdeg[bv];d++){int ci=vlist[bv][d],p2=vpos[bv][d];
                if(!cl_active[ci])continue;int s=cl_sign[ci][p2];
                if((s==1&&bval==1)||(s==-1&&bval==0))cl_active[ci]=0;}}

        if(unit_propagate()){
            for(int v=0;v<n;v++)if(var_fixed[v]<0)var_fixed[v]=(rng_next()&1);
            break;}
    }

    for(int v=0;v<n;v++)sp_assignment[v]=(var_fixed[v]>=0)?var_fixed[v]:0;
    return eval_a(sp_assignment);
}

static void flip_var(int v){int old=assignment[v],nw=1-old;assignment[v]=nw;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}

static void critical_finish(int nn, int max_steps){
    recompute_sc();
    for(int iter=0;iter<max_steps;iter++){
        int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}
        if(uci<0)return;
        int bv=-1,bc=n_clauses+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[uci][j],c=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d];
                if(clause_sc[oci]==1){int opos=vpos[v][d],os=cl_sign[oci][opos];
                    if((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))c++;}}
            if(c==0){zb=v;break;}if(c<bc){bc=c;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<20)?cl_var[uci][rng_next()%3]:bv);
        flip_var(fv);
    }
}

int main(void){
    printf("════════════════════════════════════════════════\n");
    printf("IDEAL v2: Two independent experts, zoned trust\n");
    printf("════════════════════════════════════════════════\n\n");

    int test_n[]={100,200,300,500,750,1000,1500};
    int sizes=7;

    printf("%6s | %5s | %6s | %6s | %6s | %8s\n",
           "n","total","v2","spOnly","physWs","time_ms");
    printf("-------+-------+--------+--------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?15:(nn<=500?8:(nn<=1000?4:3));
        int steps=2000+nn*15;
        int s_v2=0,s_sp=0,s_pw=0,total=0;double tms=0;

        for(int seed=0;seed<ni*5&&total<ni;seed++){
            generate(nn,4.267,58000000ULL+seed);
            clock_t t0=clock();

            /* Expert A: Physics */
            physics(steps,42+seed*31);
            int phys_a[MAX_N]; memcpy(phys_a,assignment,sizeof(int)*nn);

            /* Expert B: SP (independent) */
            for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;
            memset(var_fixed,-1,sizeof(int)*nn);
            rng_seed(seed*77777);
            int sp_a[MAX_N];
            int sp_sat=sp_solve_independent(nn, sp_a);

            /* Tension for zoning */
            double tension[MAX_N];
            for(int v=0;v<nn;v++){double p1=0,p0=0;
                for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
                    if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}
                tension[v]=(p1+p0>0)?(p1-p0)/(p1+p0):0;}

            /* ═══ COMBINE: zoned trust ═══ */
            for(int v=0;v<nn;v++){
                double at=fabs(tension[v]);
                if(at>0.5){
                    assignment[v]=phys_a[v]; /* trust physics */
                } else if(at<0.2){
                    assignment[v]=sp_a[v]; /* trust SP */
                } else {
                    /* Middle zone: trust whichever agrees with tension sign */
                    int t_dir=(tension[v]>0)?1:0;
                    if(phys_a[v]==t_dir && sp_a[v]==t_dir) assignment[v]=t_dir;
                    else if(phys_a[v]==t_dir) assignment[v]=phys_a[v];
                    else if(sp_a[v]==t_dir) assignment[v]=sp_a[v];
                    else assignment[v]=sp_a[v]; /* defer to SP */
                }
            }

            /* Critical-guided finish */
            recompute_sc();
            rng_seed(seed*99);
            critical_finish(nn, nn*10);

            int v2_unsat=count_unsat();
            if(v2_unsat==0) s_v2++;

            /* Baseline: SP alone */
            memcpy(assignment,sp_a,sizeof(int)*nn);
            recompute_sc();rng_seed(seed*88);
            critical_finish(nn,nn*10);
            if(count_unsat()==0) s_sp++;

            /* Baseline: Physics+WalkSAT */
            memcpy(assignment,phys_a,sizeof(int)*nn);
            recompute_sc();
            for(int f=0;f<nn*500;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)break;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);flip_var(fv);}
            if(count_unsat()==0) s_pw++;

            total++;
            tms+=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;
        }

        printf("%6d | %2d/%2d | %4d   | %4d   | %4d   | %7.0fms\n",
               nn,total,total,s_v2,s_sp,s_pw,tms/total);
        fflush(stdout);
    }
    return 0;
}
