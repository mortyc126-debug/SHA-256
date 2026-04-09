/*
 * CONVERGENCE: Does adding more cold starts NARROW the split zone?
 * ═══════════════════════════════════════════════════════════════
 *
 * With 20 starts: 167 split vars (33%).
 * With 50 starts: ???
 * With 100 starts: ???
 *
 * If split zone SHRINKS → eventually we converge to solution.
 * If it stays at ~33% → multiverse doesn't help.
 *
 * Also: what FRACTION of always-same vars are ACTUALLY correct?
 * If >99% → consensus zone IS the solution (for those vars).
 *
 * Compile: gcc -O3 -march=native -o convergence convergence_rate.c -lm
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
#define MAX_RUNS   100

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
static double x_cont[MAX_N];
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

static void walksat_phase(int n,int flips){int clause_sc[MAX_CLAUSES];for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);int old=assignment[fv],nw=1-old;assignment[fv]=nw;for(int d=0;d<vdeg[fv];d++){int ci=vlist[fv][d],pos=vpos[fv][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}}

static int solution[MAX_N];
static int get_minisat_solution(int n,unsigned long long iseed){char fn[256],ofn[256];sprintf(fn,"/tmp/cv_%llu.cnf",iseed);sprintf(ofn,"/tmp/cv_%llu.cnf.out",iseed);FILE*f=fopen(fn,"w");fprintf(f,"p cnf %d %d\n",n,n_clauses);rng_seed(iseed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);int signs[3];for(int j=0;j<3;j++)signs[j]=(rng_next()&1)?1:-1;fprintf(f,"%d %d %d 0\n",signs[0]*(vs[0]+1),signs[1]*(vs[1]+1),signs[2]*(vs[2]+1));}fclose(f);char cmd[512];sprintf(cmd,"timeout 30 minisat %s %s 2>/dev/null",fn,ofn);system(cmd);int ok=0;f=fopen(ofn,"r");if(f){char line[64];if(fgets(line,64,f)&&strncmp(line,"SAT",3)==0){ok=1;memset(solution,0,sizeof(int)*n);int v;while(fscanf(f,"%d",&v)==1){if(v>0&&v<=n)solution[v-1]=1;else if(v<0&&-v<=n)solution[-v-1]=0;if(v==0)break;}}fclose(f);}remove(fn);remove(ofn);return ok;}

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("CONVERGENCE: Does more realities help?\n");
    printf("═══════════════════════════════════════════\n\n");

    int nn=200;
    for(int seed=0;seed<5;seed++){
        unsigned long long iseed=48000000ULL+seed;
        generate(nn,4.267,iseed);
        int n=nn;
        if(!get_minisat_solution(n,iseed))continue;

        /* Run N cold starts, accumulate vote counts */
        int vote_1[MAX_N]; memset(vote_1,0,sizeof(int)*n); /* count of runs where v=1 */
        int total_runs=0;

        int run_a[MAX_RUNS][MAX_N];

        printf("n=%d seed=%d:\n",nn,seed);
        printf("  %6s | %6s | %6s | %6s | %6s | %6s\n",
               "N_runs","always","split","cons_correct","split_correct","maj_unsat");
        printf("  -------+--------+--------+--------------+--------------+----------\n");

        for(int r=0;r<MAX_RUNS;r++){
            physics(2000+n*15, 100+r*13337+seed*99991);
            rng_seed(r*77+seed);
            walksat_phase(n,n*200);
            memcpy(run_a[r],assignment,sizeof(int)*n);
            total_runs++;

            for(int v=0;v<n;v++) vote_1[v]+=assignment[v];

            /* Analyze at checkpoints */
            if(r==4||r==9||r==19||r==49||r==99){
                int N=r+1;
                int always_same=0, split=0;
                int consensus_correct=0, consensus_total=0;
                int split_majority_correct=0, split_total=0;

                for(int v=0;v<n;v++){
                    double p1=(double)vote_1[v]/N;
                    if(p1>=0.9||p1<=0.1){
                        always_same++;
                        int consensus_val=(p1>0.5)?1:0;
                        consensus_total++;
                        if(consensus_val==solution[v])consensus_correct++;
                    } else {
                        split++;
                        int maj_val=(p1>0.5)?1:0;
                        split_total++;
                        if(maj_val==solution[v])split_majority_correct++;
                    }
                }

                /* Majority vote */
                int maj[MAX_N];
                for(int v=0;v<n;v++)maj[v]=(vote_1[v]*2>N)?1:0;
                int sat=0;
                for(int ci=0;ci<n_clauses;ci++)
                    for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                        if((s==1&&maj[v]==1)||(s==-1&&maj[v]==0)){sat++;break;}}

                printf("  %6d | %4d   | %4d   | %4d/%4d     | %4d/%4d     | %6d\n",
                       N, always_same, split,
                       consensus_correct,consensus_total,
                       split_majority_correct,split_total,
                       n_clauses-sat);
            }
        }
        printf("\n");
        break;
    }
    return 0;
}
