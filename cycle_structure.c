/*
 * THE CYCLE: Is the fix→break loop CLOSED or RANDOM WALK?
 * ═══════════════════════════════════════════════════════
 *
 * Track WHICH clauses break and fix over many rounds.
 * Questions:
 * 1. Do the SAME clauses keep cycling? Or new ones each time?
 * 2. How long is the cycle? (period)
 * 3. Which VARIABLES keep getting flipped back and forth?
 * 4. Is the cycle DETERMINISTIC (same sequence) or CHAOTIC?
 * 5. What's the ORBIT — set of states the system visits?
 *
 * Compile: gcc -O3 -march=native -o cycle_struct cycle_structure.c -lm
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
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];
            cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];if(vdeg[v]<MAX_DEGREE){
                vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}
}

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
    for(int v=0;v<n;v++) assignment[v]=(x_g[v]>0.5)?1:0;
}

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
    printf("═══════════════════════════════════════\n");
    printf("CYCLE STRUCTURE: Closed or random walk?\n");
    printf("═══════════════════════════════════════\n\n");

    int test_n[]={100, 200, 500};

    for(int ti=0;ti<3;ti++){
        int nn=test_n[ti];
        int steps=2000+nn*15;

        for(int seed=0;seed<20;seed++){
            generate(nn,4.267,28000000ULL+seed);
            physics(steps,42+seed*31);
            recompute();
            rng_seed(seed*777);
            walksat_phase(nn*200);

            int m=n_clauses;
            int init_unsat=count_unsat();
            if(init_unsat<3||init_unsat>nn/4)continue;

            /* Track clause and variable activity over 100 rounds */
            int clause_unsat_count[MAX_CLAUSES]; memset(clause_unsat_count,0,sizeof(int)*m);
            int var_flip_count[MAX_N]; memset(var_flip_count,0,sizeof(int)*nn);
            int flipped_var_log[200];
            int fixed_clause_log[200];
            int broke_clause_log[200];

            /* Track assignment fingerprints to detect cycles */
            /* Simple hash: sum of v*assignment[v] */
            unsigned long long state_hashes[200];

            int n_rounds = (init_unsat < 10) ? 60 : 100;
            if(n_rounds > 200) n_rounds = 200;

            for(int round=0;round<n_rounds;round++){
                int uci=-1;
                for(int ci=0;ci<m;ci++)if(clause_sc[ci]==0){uci=ci;break;}
                if(uci<0)break;

                /* Pick min-critical among 3 suspects */
                int mc=m+1,mv=-1;
                for(int j=0;j<3;j++){int v=cl_var[uci][j],c=0;
                    for(int d=0;d<vdeg[v];d++){int cci=vlist[v][d];
                        if(clause_sc[cci]==1){int pos=vpos[v][d],s=cl_sign[cci][pos];
                            if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))c++;}}
                    if(c<mc){mc=c;mv=v;}}

                /* Record what gets fixed and broken */
                flipped_var_log[round]=mv;
                fixed_clause_log[round]=uci;
                broke_clause_log[round]=-1;

                /* Track which clause BECOMES unsat */
                flip_var(mv);
                for(int ci=0;ci<m;ci++){
                    if(clause_sc[ci]==0){
                        clause_unsat_count[ci]++;
                        /* Was this newly broken? */
                        if(ci!=uci) broke_clause_log[round]=ci;
                    }
                }
                var_flip_count[mv]++;

                /* State hash */
                unsigned long long h=0;
                for(int v=0;v<nn;v++) h += (unsigned long long)(v+1)*assignment[v]*2654435761ULL;
                state_hashes[round]=h;
            }

            /* ═══ ANALYSIS ═══ */
            printf("n=%d, seed=%d: %d unsat, %d rounds\n",nn,seed,init_unsat,n_rounds);

            /* 1. How many UNIQUE clauses ever become unsat? */
            int unique_unsat=0;
            for(int ci=0;ci<m;ci++) if(clause_unsat_count[ci]>0) unique_unsat++;
            printf("  Unique clauses ever unsat: %d (of %d initial)\n",
                   unique_unsat, init_unsat);
            printf("  → %s\n", unique_unsat <= init_unsat*2 ?
                   "CLOSED cycle (same clauses)" : "OPEN walk (new clauses)");

            /* 2. How many UNIQUE variables get flipped? */
            int unique_flipped=0;
            for(int v=0;v<nn;v++) if(var_flip_count[v]>0) unique_flipped++;
            printf("  Unique vars flipped: %d\n", unique_flipped);

            /* 3. Most frequently flipped vars */
            printf("  Top flipped vars: ");
            for(int top=0;top<5;top++){
                int maxv=-1,maxc=0;
                for(int v=0;v<nn;v++)
                    if(var_flip_count[v]>maxc){maxc=var_flip_count[v];maxv=v;}
                if(maxv<0)break;
                printf("x%d(%dx) ",maxv,maxc);
                var_flip_count[maxv]=0; /* mark as reported */
            }
            printf("\n");

            /* 4. Most frequently unsat clauses */
            printf("  Top unsat clauses: ");
            for(int top=0;top<5;top++){
                int maxci=-1,maxc=0;
                for(int ci=0;ci<m;ci++)
                    if(clause_unsat_count[ci]>maxc){maxc=clause_unsat_count[ci];maxci=ci;}
                if(maxci<0)break;
                printf("c%d(%dx) ",maxci,maxc);
                clause_unsat_count[maxci]=0;
            }
            printf("\n");

            /* 5. Detect exact cycle: same state hash repeats? */
            int cycle_len=0;
            for(int i=1;i<n_rounds&&!cycle_len;i++){
                for(int j=0;j<i;j++){
                    if(state_hashes[i]==state_hashes[j]){
                        cycle_len=i-j;
                        printf("  EXACT CYCLE detected: period=%d (rounds %d→%d)\n",
                               cycle_len,j,i);
                        break;}}}
            if(!cycle_len) printf("  No exact cycle in %d rounds\n",n_rounds);

            /* 6. fix→break chain: is it the SAME clause bouncing? */
            int same_bounce=0, diff_bounce=0;
            for(int r=1;r<n_rounds;r++){
                if(fixed_clause_log[r]==broke_clause_log[r-1]) same_bounce++;
                else diff_bounce++;
            }
            printf("  Fix(r) = Broke(r-1): %d/%d (%.0f%%) ← %s\n",
                   same_bounce, same_bounce+diff_bounce,
                   100.0*same_bounce/(same_bounce+diff_bounce+1),
                   same_bounce > diff_bounce ? "PING-PONG!" : "spreading");

            printf("\n");
            break; /* one instance per n */
        }
    }
    return 0;
}
