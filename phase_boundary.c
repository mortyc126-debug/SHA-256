/*
 * PHASE BOUNDARY: The wall between two realities
 * ═══════════════════════════════════════════════
 *
 * Reality A = our assignment (99.6% sat, 36% wrong)
 * Reality B = true solution (100% sat)
 * Hamming distance = 36% of n
 *
 * What does the PATH between them look like?
 * Is there a smooth transition or a sharp barrier?
 *
 * EXPERIMENTS:
 * 1. INTERPOLATION: Walk from A to B, flipping vars one at a time.
 *    Plot satisfaction along the path. Smooth or valley?
 *
 * 2. RANDOM WALK: Random interpolation order vs optimal order.
 *    Does ORDER matter?
 *
 * 3. THE VALLEY: Is there a point where sat DROPS below both A and B?
 *    How deep? How wide?
 *
 * 4. OPTIMAL PATH: Greedily flip vars in order that MAXIMIZES sat
 *    at each step. Does greedy find a monotone path?
 *
 * 5. ENERGY LANDSCAPE CROSS-SECTION: measure sat at
 *    assignment = A*(1-t) + B*t for t in [0,1]
 *    (interpolation in continuous space, then round)
 *
 * Compile: gcc -O3 -march=native -o phase_b phase_boundary.c -lm
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
static inline unsigned long long rng_next(void){unsigned long long s0=rng_s[0],s1=rng_s[1],s2=rng_s[2],s3=rng_s[3];unsigned long long r=((s1*5)<<7|(s1*5)>>57)*9;unsigned long long t=s1<<17;s2^=s0;s3^=s1;s1^=s2;s0^=s3;s2^=t;s3=(s3<<45)|(s3>>19);rng_s[0]=s0;rng_s[1]=s1;rng_s[2]=s2;rng_s[3]=s3;return r;}
static void rng_seed(unsigned long long s){rng_s[0]=s;rng_s[1]=s*6364136223846793005ULL+1;rng_s[2]=s*1103515245ULL+12345;rng_s[3]=s^0xdeadbeefcafebabeULL;for(int i=0;i<20;i++)rng_next();}

static void generate(int n,double ratio,unsigned long long seed){n_vars=n;n_clauses=(int)(ratio*n);if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;rng_seed(seed);memset(vdeg,0,sizeof(int)*n);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);for(int j=0;j<3;j++){cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;int v=vs[j];if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}}}}

static int eval_a(const int*a){int s=0;for(int ci=0;ci<n_clauses;ci++)for(int j=0;j<3;j++){int v=cl_var[ci][j],ss=cl_sign[ci][j];if((ss==1&&a[v]==1)||(ss==-1&&a[v]==0)){s++;break;}}return s;}

static int solution[MAX_N];
static int get_minisat_solution(int n,unsigned long long iseed){
    char fn[256],ofn[256];sprintf(fn,"/tmp/pb_%llu.cnf",iseed);sprintf(ofn,"/tmp/pb_%llu.cnf.out",iseed);
    FILE*f=fopen(fn,"w");fprintf(f,"p cnf %d %d\n",n,n_clauses);
    rng_seed(iseed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);int signs[3];for(int j=0;j<3;j++)signs[j]=(rng_next()&1)?1:-1;fprintf(f,"%d %d %d 0\n",signs[0]*(vs[0]+1),signs[1]*(vs[1]+1),signs[2]*(vs[2]+1));}fclose(f);
    char cmd[512];sprintf(cmd,"timeout 30 minisat %s %s 2>/dev/null",fn,ofn);system(cmd);
    int ok=0;f=fopen(ofn,"r");if(f){char line[64];if(fgets(line,64,f)&&strncmp(line,"SAT",3)==0){ok=1;memset(solution,0,sizeof(int)*n);int v;while(fscanf(f,"%d",&v)==1){if(v>0&&v<=n)solution[v-1]=1;else if(v<0&&-v<=n)solution[-v-1]=0;if(v==0)break;}}fclose(f);}
    remove(fn);remove(ofn);return ok;}

static double x_cont[MAX_N];
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+((rng_next()>>11)*(2.0/9007199254740992.0)-1)*T)*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0)x_cont[v]=0.01;if(x_cont[v]>1)x_cont[v]=0.99;}}}

static int assignment[MAX_N];
static void walksat_quick(int n,int flips){
    int clause_sc[MAX_CLAUSES];
    for(int ci=0;ci<n_clauses;ci++){clause_sc[ci]=0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))clause_sc[ci]++;}}
    for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);int old=assignment[fv],nw=1-old;assignment[fv]=nw;for(int d=0;d<vdeg[fv];d++){int ci=vlist[fv][d],pos=vpos[fv][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}}

int main(void){
    printf("════════════════════════════════════════\n");
    printf("PHASE BOUNDARY: The wall between worlds\n");
    printf("════════════════════════════════════════\n\n");

    int nn=200;
    for(int seed=0;seed<10;seed++){
        unsigned long long iseed=46000000ULL+seed;
        generate(nn,4.267,iseed);
        int n=nn,m=n_clauses;
        if(!get_minisat_solution(n,iseed))continue;

        physics(2000+n*15,42+seed*31);
        for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;
        rng_seed(seed*777);walksat_quick(n,n*200);

        int A[MAX_N]; memcpy(A,assignment,sizeof(int)*n); /* our assignment */
        int B[MAX_N]; memcpy(B,solution,sizeof(int)*n);   /* true solution */

        int satA=eval_a(A), satB=eval_a(B);
        int diff[MAX_N],ndiff=0;
        for(int v=0;v<n;v++)if(A[v]!=B[v])diff[ndiff++]=v;

        if(ndiff<10)continue;

        printf("n=%d seed=%d: A=%d/%d sat, B=%d/%d sat, hamming=%d (%.0f%%)\n",
               nn,seed,satA,m,satB,m,ndiff,100.0*ndiff/n);

        /* ═══ 1. RANDOM INTERPOLATION: flip diff vars in random order ═══ */
        printf("\n  Random walk A→B (flip diff vars one at a time):\n");
        printf("  %6s | %6s | %6s\n","step","unsat","Δ");
        printf("  -------+--------+------\n");

        int cur[MAX_N]; memcpy(cur,A,sizeof(int)*n);
        /* Shuffle diff */
        for(int i=ndiff-1;i>0;i--){int j=rng_next()%(i+1);int t=diff[i];diff[i]=diff[j];diff[j]=t;}

        int prev_sat=satA;
        int min_sat=satA;
        int min_step=0;

        for(int i=0;i<=ndiff;i++){
            if(i>0) cur[diff[i-1]]=B[diff[i-1]]; /* flip one var toward B */
            int sat=eval_a(cur);
            int delta=sat-prev_sat;
            if(sat<min_sat){min_sat=sat;min_step=i;}
            if(i%(ndiff/10+1)==0 || i==ndiff)
                printf("  %6d | %6d | %+4d\n",i,m-sat,delta);
            prev_sat=sat;
        }

        printf("  VALLEY: min sat=%d (unsat=%d) at step %d/%d\n",
               min_sat,m-min_sat,min_step,ndiff);
        printf("  Depth: %d below A, %d below B\n",satA-min_sat,satB-min_sat);

        /* ═══ 2. GREEDY PATH: always flip the var that MAXIMIZES sat ═══ */
        printf("\n  Greedy path A→B:\n");
        memcpy(cur,A,sizeof(int)*n);
        int remaining[MAX_N],nrem=ndiff;
        for(int i=0;i<ndiff;i++)remaining[i]=diff[i];

        int greedy_min=satA, greedy_monotone=1;
        prev_sat=satA;

        for(int step=0;step<ndiff;step++){
            int best_idx=-1, best_sat=0;
            for(int i=0;i<nrem;i++){
                int v=remaining[i];
                cur[v]=B[v]; /* try flip */
                int sat=eval_a(cur);
                if(sat>best_sat){best_sat=sat;best_idx=i;}
                cur[v]=A[v]; /* undo — but A[v] might already be flipped */
                /* Actually need to track current state properly */
            }
            /* Simpler: try each remaining, pick best */
            best_sat=0; best_idx=0;
            for(int i=0;i<nrem;i++){
                int v=remaining[i];
                int save=cur[v]; cur[v]=B[v];
                int sat=eval_a(cur);
                cur[v]=save;
                if(sat>best_sat){best_sat=sat;best_idx=i;}}

            int v=remaining[best_idx];
            cur[v]=B[v];
            remaining[best_idx]=remaining[nrem-1];nrem--;

            if(best_sat<prev_sat)greedy_monotone=0;
            if(best_sat<greedy_min)greedy_min=best_sat;

            if(step%(ndiff/10+1)==0||step==ndiff-1)
                printf("  step %3d: flip x%d → %d sat (%+d)\n",
                       step,v,best_sat,best_sat-prev_sat);
            prev_sat=best_sat;
        }

        printf("  Greedy monotone: %s\n",greedy_monotone?"YES!":"no");
        printf("  Greedy min sat: %d (unsat=%d)\n",greedy_min,m-greedy_min);

        /* ═══ 3. CONTINUOUS INTERPOLATION ═══ */
        printf("\n  Continuous interpolation A×(1-t) + B×t:\n");
        printf("  %6s | %6s\n","t","unsat");
        printf("  -------+------\n");

        double xA[MAX_N],xB[MAX_N];
        for(int v=0;v<n;v++){xA[v]=(double)A[v];xB[v]=(double)B[v];}

        int cont_min=m;
        for(int ti=0;ti<=20;ti++){
            double t=ti/20.0;
            int interp[MAX_N];
            for(int v=0;v<n;v++){
                double val=xA[v]*(1-t)+xB[v]*t;
                interp[v]=(val>0.5)?1:0;}
            int sat=eval_a(interp);
            if(sat<cont_min)cont_min=sat;
            printf("  %6.2f | %6d\n",t,m-sat);
        }

        printf("  Continuous min unsat: %d\n",m-cont_min);

        printf("\n");
        break;
    }
    return 0;
}
