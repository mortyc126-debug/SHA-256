/*
 * PENDULUM ANATOMY: The two clauses, the trapped variable, the bypass
 * ═══════════════════════════════════════════════════════════════════
 *
 * Variable x sits between clause_A and clause_B.
 * A needs x=1, B needs x=0 (or vice versa). No single value works.
 *
 * Study:
 * 1. WHO is the pendulum var? What are the two clauses?
 * 2. WHAT are the OTHER vars in those two clauses? (5 total: 2+2+pendulum)
 * 3. Is there a BYPASS? A different var in A or B whose flip resolves both?
 * 4. DEPTH: Is the bypass itself a pendulum? (recursive trapping)
 * 5. The FULL CONFLICT GRAPH: all pendulum pairs in the instance
 *
 * Compile: gcc -O3 -march=native -o pendulum pendulum_anatomy.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      2000
#define MAX_CLAUSES 10000
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
static double rng_normal(double m,double s){
    double u1=(rng_next()>>11)*(1.0/9007199254740992.0);
    double u2=(rng_next()>>11)*(1.0/9007199254740992.0);
    if(u1<1e-15)u1=1e-15;
    return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
    rng_seed(seed);memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}}

static int assignment[MAX_N];
static int clause_sc[MAX_CLAUSES];
static void recompute(void){for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;
    for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}}
static int count_unsat(void){int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0)c++;return c;}

static double x_g[MAX_N],vel_g[MAX_N];
static void physics(int steps,unsigned long long seed){
    int n=n_vars;rng_seed(seed);
    for(int v=0;v<n;v++){double p1=0,p0=0;
        for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
            if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}
        x_g[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel_g[v]=0;}
    double force[MAX_N];
    for(int step=0;step<steps;step++){double prog=(double)step/steps;
        double T=0.30*exp(-4.0*prog)+0.0001;
        double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);
        for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                lit[j]=(s==1)?x_g[v]:(1.0-x_g[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){if(x_g[v]>0.5)force[v]+=cr*(1-x_g[v]);else force[v]-=cr*x_g[v];
            vel_g[v]=0.93*vel_g[v]+(force[v]+rng_normal(0,T))*0.05;
            x_g[v]+=vel_g[v]*0.05;
            if(x_g[v]<0){x_g[v]=0.01;vel_g[v]=fabs(vel_g[v])*0.3;}
            if(x_g[v]>1){x_g[v]=0.99;vel_g[v]=-fabs(vel_g[v])*0.3;}}}
    for(int v=0;v<n;v++) assignment[v]=(x_g[v]>0.5)?1:0;}

static void flip_var(int v){
    int old=assignment[v],nw=1-old;assignment[v]=nw;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
        int was=((s==1&&old==1)||(s==-1&&old==0));
        int now=((s==1&&nw==1)||(s==-1&&nw==0));
        if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}

static void walksat_phase(int flips){
    for(int f=0;f<flips;f++){
        int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}
        if(uci<0)return;
        int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);
        flip_var(fv);}}

int main(void){
    printf("══════════════════════════════════════\n");
    printf("PENDULUM ANATOMY\n");
    printf("══════════════════════════════════════\n\n");

    int test_n[]={100, 200, 500};

    for(int ti=0;ti<3;ti++){
        int nn=test_n[ti]; int steps=2000+nn*15;

        for(int seed=0;seed<30;seed++){
            generate(nn,4.267,29000000ULL+seed);
            physics(steps,42+seed*31);
            recompute();
            rng_seed(seed*777);
            walksat_phase(nn*200);

            int m=n_clauses;
            int init_unsat=count_unsat();
            if(init_unsat<2||init_unsat>nn/4)continue;

            /* Find the pendulum: flip min-critical twice, track which var oscillates */
            int save_a[MAX_N]; memcpy(save_a,assignment,sizeof(int)*nn);

            /* Round 1: find first unsat, flip min-critical */
            int uci_A=-1;
            for(int ci=0;ci<m;ci++)if(clause_sc[ci]==0){uci_A=ci;break;}
            if(uci_A<0)continue;

            int mc=m+1,pend_var=-1;
            for(int j=0;j<3;j++){int v=cl_var[uci_A][j],c=0;
                for(int d=0;d<vdeg[v];d++){int cci=vlist[v][d];
                    if(clause_sc[cci]==1){int pos=vpos[v][d],s=cl_sign[cci][pos];
                        if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))c++;}}
                if(c<mc){mc=c;pend_var=v;}}
            if(pend_var<0)continue;

            /* Flip → find which clause breaks */
            flip_var(pend_var);
            int uci_B=-1;
            for(int ci=0;ci<m;ci++)if(clause_sc[ci]==0 && ci!=uci_A){uci_B=ci;break;}

            /* Restore */
            memcpy(assignment,save_a,sizeof(int)*nn);
            recompute();

            if(uci_B<0)continue;

            /* ═══ ANATOMY ═══ */
            printf("n=%d, seed=%d: pendulum var x%d\n",nn,seed,pend_var);
            printf("  Clause A (c%d): ",uci_A);
            for(int j=0;j<3;j++) printf("x%d(%+d) ",cl_var[uci_A][j],cl_sign[uci_A][j]);
            printf("\n  Clause B (c%d): ",uci_B);
            for(int j=0;j<3;j++) printf("x%d(%+d) ",cl_var[uci_B][j],cl_sign[uci_B][j]);

            /* What sign does each clause want for pendulum var? */
            int sign_A=0, sign_B=0;
            for(int j=0;j<3;j++){
                if(cl_var[uci_A][j]==pend_var) sign_A=cl_sign[uci_A][j];
                if(cl_var[uci_B][j]==pend_var) sign_B=cl_sign[uci_B][j];}
            printf("\n  A wants x%d=%d, B wants x%d=%d",
                   pend_var,sign_A==1?1:0,pend_var,sign_B==1?1:0);
            printf(" → %s\n",sign_A==sign_B?"SAME (not conflict!)":"OPPOSITE (conflict!)");

            /* Other vars in A and B */
            printf("\n  Other vars in A: ");
            int others_A[4],nA=0;
            for(int j=0;j<3;j++)if(cl_var[uci_A][j]!=pend_var)
                {others_A[nA]=cl_var[uci_A][j];
                 printf("x%d(val=%d) ",others_A[nA],assignment[others_A[nA]]);nA++;}
            printf("\n  Other vars in B: ");
            int others_B[4],nB=0;
            for(int j=0;j<3;j++)if(cl_var[uci_B][j]!=pend_var)
                {others_B[nB]=cl_var[uci_B][j];
                 printf("x%d(val=%d) ",others_B[nB],assignment[others_B[nB]]);nB++;}
            printf("\n");

            /* ═══ BYPASS SEARCH ═══ */
            /* For each other var in A and B: what happens if we flip IT instead? */
            printf("\n  BYPASS SEARCH: flip other vars instead of pendulum\n");
            printf("  %5s | %5s | %5s | %5s | %s\n",
                   "var","val→","fixes","breaks","result");
            printf("  ------+-------+-------+-------+--------\n");

            int best_bypass=-1, best_net=-999;

            for(int pass=0;pass<2;pass++){
                int *others = (pass==0)?others_A:others_B;
                int no = (pass==0)?nA:nB;
                for(int k=0;k<no;k++){
                    int v=others[k];
                    int new_val=1-assignment[v];

                    /* Count fixes and breaks */
                    int fixes=0, breaks=0;
                    for(int d=0;d<vdeg[v];d++){
                        int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
                        if(clause_sc[ci]==0){
                            if((s==1&&new_val==1)||(s==-1&&new_val==0))fixes++;}
                        else if(clause_sc[ci]==1){
                            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))breaks++;}}

                    int net=fixes-breaks;
                    char *result = (net>0)?"IMPROVES":(net==0?"neutral":"WORSENS");
                    printf("  x%4d | %d→%d   | %5d | %5d | %s\n",
                           v,assignment[v],new_val,fixes,breaks,result);

                    if(net>best_net){best_net=net;best_bypass=v;}
                }
            }

            if(best_bypass>=0 && best_net>0){
                printf("\n  BYPASS FOUND: x%d (net=%+d)\n",best_bypass,best_net);
                /* Try it: flip bypass var */
                flip_var(best_bypass);
                int after=count_unsat();
                printf("  After bypass flip: %d unsat (was %d)\n",after,init_unsat);

                /* Is the pendulum still stuck? */
                int pend_still_unsat=0;
                if(clause_sc[uci_A]==0) pend_still_unsat++;
                if(clause_sc[uci_B]==0) pend_still_unsat++;
                printf("  Pendulum clauses still unsat: %d/2\n",pend_still_unsat);

                memcpy(assignment,save_a,sizeof(int)*nn);
                recompute();
            } else {
                printf("\n  NO BYPASS with positive net among direct neighbors.\n");

                /* Try 2-hop: vars that share a clause with others_A or others_B */
                printf("  Searching 2-hop bypass...\n");
                int best2=-1, best2_net=-999;
                int checked=0;

                for(int pass=0;pass<2;pass++){
                    int *others=(pass==0)?others_A:others_B;
                    int no=(pass==0)?nA:nB;
                    for(int k=0;k<no;k++){
                        int u=others[k];
                        for(int d=0;d<vdeg[u]&&d<20;d++){
                            int ci2=vlist[u][d];
                            for(int j2=0;j2<3;j2++){
                                int v2=cl_var[ci2][j2];
                                if(v2==pend_var||v2==u)continue;
                                int nv=1-assignment[v2];
                                int fixes2=0,breaks2=0;
                                for(int dd=0;dd<vdeg[v2];dd++){
                                    int cci=vlist[v2][dd],cpos=vpos[v2][dd],cs=cl_sign[cci][cpos];
                                    if(clause_sc[cci]==0){
                                        if((cs==1&&nv==1)||(cs==-1&&nv==0))fixes2++;}
                                    else if(clause_sc[cci]==1){
                                        if((cs==1&&assignment[v2]==1)||(cs==-1&&assignment[v2]==0))breaks2++;}}
                                int net2=fixes2-breaks2;
                                if(net2>best2_net){best2_net=net2;best2=v2;}
                                checked++;}}}}

                printf("  Checked %d 2-hop vars. ",checked);
                if(best2>=0 && best2_net>0){
                    printf("BYPASS at x%d (net=%+d)\n",best2,best2_net);
                    flip_var(best2);
                    int after2=count_unsat();
                    printf("  After 2-hop bypass: %d unsat (was %d)\n",after2,init_unsat);
                    memcpy(assignment,save_a,sizeof(int)*nn);
                    recompute();
                } else {
                    printf("No positive-net 2-hop bypass either.\n");
                }
            }

            printf("\n");
            break; /* one instance per n */
        }
    }
    return 0;
}
