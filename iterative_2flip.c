/*
 * ITERATIVE 2-FLIP: Exhaust 1-hop → find 2-flip → repeat
 * ═══════════════════════════════════════════════════════
 *
 * Pipeline:
 * 1. Physics → 99% sat
 * 2. WalkSAT warmup
 * 3. Exhaust 1-hop bypass (single flip, net>0)
 * 4. Search 2-flip among hard core vars (pairs with net>0)
 * 5. Apply best 2-flip
 * 6. Go to step 3 (new 1-hop bypass may open up)
 * 7. If no 2-flip: try 3-flip
 * 8. Repeat until solved or stuck
 *
 * Also track: does each level open new levels below?
 *
 * Compile: gcc -O3 -march=native -o iter2flip iterative_2flip.c -lm
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
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}
static double rng_normal(double m,double s){double u1=(rng_next()>>11)*(1.0/9007199254740992.0),u2=(rng_next()>>11)*(1.0/9007199254740992.0);if(u1<1e-15)u1=1e-15;return m+s*sqrt(-2*log(u1))*cos(2*M_PI*u2);}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;rng_seed(seed);memset(vdeg,0,sizeof(int)*n);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}}

static int assignment[MAX_N];
static int clause_sc[MAX_CLAUSES];
static void recompute(void){for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}}
static int count_unsat(void){int c=0;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0)c++;return c;}

static double x_g[MAX_N];
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_g[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_g[v]:(1.0-x_g[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_g[v]>0.5)force[v]+=cr*(1-x_g[v]);else force[v]-=cr*x_g[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_g[v]+=vel[v]*0.05;if(x_g[v]<0){x_g[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_g[v]>1){x_g[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}for(int v=0;v<n;v++)assignment[v]=(x_g[v]>0.5)?1:0;}

static void flip_var(int v){int old=assignment[v],nw=1-old;assignment[v]=nw;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}

static void walksat_phase(int flips){for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);flip_var(fv);}}

/* 1-hop bypass: find any single flip with net > 0 */
static int do_1hop(void){
    int improved=0;
    for(int ci=0;ci<n_clauses;ci++){
        if(clause_sc[ci]!=0)continue;
        for(int j=0;j<3;j++){int u=cl_var[ci][j];
            for(int d=0;d<vdeg[u]&&d<30;d++){int ci2=vlist[u][d];
                for(int j2=0;j2<3;j2++){int v=cl_var[ci2][j2];
                    int nv=1-assignment[v],fixes=0,breaks=0;
                    for(int dd=0;dd<vdeg[v];dd++){int cci=vlist[v][dd],cpos=vpos[v][dd],cs=cl_sign[cci][cpos];
                        if(clause_sc[cci]==0){if((cs==1&&nv==1)||(cs==-1&&nv==0))fixes++;}
                        else if(clause_sc[cci]==1){if((cs==1&&assignment[v]==1)||(cs==-1&&assignment[v]==0))breaks++;}}
                    if(fixes>breaks){flip_var(v);return 1;}}}}}
    return 0;
}

/* 2-flip: find pair among hard core vars with net > 0 */
static int do_2flip(void){
    int hc[MAX_N],nhc=0;
    int is_hc[MAX_N]; memset(is_hc,0,sizeof(int)*n_vars);
    for(int ci=0;ci<n_clauses;ci++){if(clause_sc[ci]!=0)continue;
        for(int j=0;j<3;j++){int v=cl_var[ci][j];if(!is_hc[v]){is_hc[v]=1;hc[nhc++]=v;}}}

    int best_net=-1,bv1=-1,bv2=-1;
    int pairs=0;
    for(int i=0;i<nhc&&pairs<10000;i++){
        for(int j=i+1;j<nhc&&pairs<10000;j++){
            int v1=hc[i],v2=hc[j];
            int before=count_unsat();
            flip_var(v1);flip_var(v2);
            int after=count_unsat();
            flip_var(v2);flip_var(v1);
            int net=before-after;
            if(net>best_net){best_net=net;bv1=v1;bv2=v2;}
            pairs++;}}

    if(best_net>0){flip_var(bv1);flip_var(bv2);return best_net;}
    return 0;
}

/* 3-flip: find triple among hard core vars */
static int do_3flip(void){
    int hc[MAX_N],nhc=0;
    int is_hc[MAX_N]; memset(is_hc,0,sizeof(int)*n_vars);
    for(int ci=0;ci<n_clauses;ci++){if(clause_sc[ci]!=0)continue;
        for(int j=0;j<3;j++){int v=cl_var[ci][j];if(!is_hc[v]){is_hc[v]=1;hc[nhc++]=v;}}}

    if(nhc>50)nhc=50; /* cap for speed */
    int best_net=-1,bv1=-1,bv2=-1,bv3=-1;
    int trips=0;
    for(int i=0;i<nhc&&trips<20000;i++){
        for(int j=i+1;j<nhc&&trips<20000;j++){
            for(int k=j+1;k<nhc&&trips<20000;k++){
                int v1=hc[i],v2=hc[j],v3=hc[k];
                int before=count_unsat();
                flip_var(v1);flip_var(v2);flip_var(v3);
                int after=count_unsat();
                flip_var(v3);flip_var(v2);flip_var(v1);
                int net=before-after;
                if(net>best_net){best_net=net;bv1=v1;bv2=v2;bv3=v3;}
                trips++;}}}

    if(best_net>0){flip_var(bv1);flip_var(bv2);flip_var(bv3);return best_net;}
    return 0;
}

int main(void){
    printf("══════════════════════════════════════════════\n");
    printf("ITERATIVE MULTI-FLIP: 1-hop → 2-flip → 3-flip\n");
    printf("══════════════════════════════════════════════\n\n");

    int test_n[]={50,100,200,300,500,750,1000};
    int sizes=7;

    printf("%6s | %5s | %6s | %6s | %6s | %8s\n",
           "n","total","solved","remain","reduce","time_ms");
    printf("-------+-------+--------+--------+--------+----------\n");

    for(int ti=0;ti<sizes;ti++){
        int nn=test_n[ti];
        int ni=(nn<=200)?15:(nn<=500?8:4);
        int steps=2000+nn*15;

        int total=0,solved=0;
        double sum_reduce=0, total_ms=0;

        for(int seed=0;seed<ni*5&&total<ni;seed++){
            generate(nn,4.267,33000000ULL+seed);
            clock_t t0=clock();

            physics(steps,42+seed*31);
            recompute();
            rng_seed(seed*777);
            walksat_phase(nn*200);

            int init_unsat=count_unsat();
            if(init_unsat<1){total++;if(init_unsat==0)solved++;
                clock_t t1=clock();total_ms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;continue;}

            /* Iterative: 1-hop → 2-flip → 1-hop → 2-flip → 3-flip → ... */
            for(int cycle=0;cycle<50;cycle++){
                if(count_unsat()==0)break;

                /* Exhaust 1-hop */
                while(do_1hop());
                if(count_unsat()==0)break;

                /* Try 2-flip */
                int net2=do_2flip();
                if(net2>0)continue; /* got improvement, try more 1-hop */

                /* Try 3-flip */
                int net3=do_3flip();
                if(net3>0)continue;

                break; /* stuck at all levels */
            }

            int final_unsat=count_unsat();
            if(final_unsat==0)solved++;
            double red=(init_unsat>0)?(double)(init_unsat-final_unsat)/init_unsat:0;
            sum_reduce+=red;
            total++;

            clock_t t1=clock();
            total_ms+=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
        }

        if(total>0)
            printf("%6d | %2d/%2d | %4d   | %5.1f  | %5.0f%% | %7.0fms\n",
                   nn,total,total,solved,
                   (1-sum_reduce/total)*(sum_reduce>0?100:0),
                   100*sum_reduce/total,total_ms/total);
        fflush(stdout);
    }

    printf("\nIf solved > previous methods at n=500+: MULTI-FLIP WORKS!\n");
    printf("Previous best: PhysicsSAT 4/20 at n=500, SP 2/5 at n=750\n");
    return 0;
}
