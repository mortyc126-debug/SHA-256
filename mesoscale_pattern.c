/*
 * MESOSCALE PATTERN: What do the ~10 correct vars look like?
 * ═══════════════════════════════════════════════════════════
 *
 * We need ~10 vars from ~50 ghosts. What PATTERN do the right 10 form?
 *
 * Approach: Use MiniSat to get TRUE solution, then compare with our
 * physics assignment. The DIFF = the vars we need to flip.
 * Study the PATTERN of the diff.
 *
 * At n=200 (small enough for MiniSat): get truth, study the mesoscale.
 *
 * Questions:
 * 1. How many vars need flipping? (confirm ~10 = 2% at n=500)
 * 2. Are they CONNECTED? Form a subgraph?
 * 3. What CLAUSE structure connects them?
 * 4. What's their tension, match_ratio, ghost_score distribution?
 * 5. Is there a PATTERN that distinguishes THE RIGHT 10 from wrong 40?
 * 6. Do they form a PATH through the clause graph?
 * 7. What do they look like in MULTI-REALITY view?
 *
 * Compile: gcc -O3 -march=native -o meso_pattern mesoscale_pattern.c -lm
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

static double x_cont[MAX_N];
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

static void flip_var(int v){int old=assignment[v],nw=1-old;assignment[v]=nw;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}
static void walksat_phase(int flips){for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);flip_var(fv);}}

/* Get MiniSat solution as ground truth */
static int solution[MAX_N];
static int get_minisat_solution(int n, unsigned long long instance_seed){
    char fn[256],ofn[256];
    sprintf(fn,"/tmp/meso_%llu.cnf",instance_seed);
    sprintf(ofn,"/tmp/meso_%llu.cnf.out",instance_seed);
    FILE*f=fopen(fn,"w");
    fprintf(f,"p cnf %d %d\n",n,n_clauses);
    /* Regenerate same instance */
    rng_seed(instance_seed);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        int signs[3];for(int j=0;j<3;j++)signs[j]=(rng_next()&1)?1:-1;
        fprintf(f,"%d %d %d 0\n",signs[0]*(vs[0]+1),signs[1]*(vs[1]+1),signs[2]*(vs[2]+1));}
    fclose(f);

    char cmd[512];sprintf(cmd,"timeout 30 minisat %s %s 2>/dev/null",fn,ofn);
    system(cmd);

    int ok=0;
    f=fopen(ofn,"r");
    if(f){char line[64];
        if(fgets(line,64,f)&&strncmp(line,"SAT",3)==0){
            ok=1;memset(solution,0,sizeof(int)*n);
            if(fgets(line,sizeof(line),f)){/* first part */}
            /* Read all values */
            fclose(f);
            f=fopen(ofn,"r");fgets(line,64,f); /* skip SAT line */
            int v;
            while(fscanf(f,"%d",&v)==1){
                if(v>0&&v<=n)solution[v-1]=1;
                else if(v<0&&-v<=n)solution[-v-1]=0;
                if(v==0)break;}}
        if(f)fclose(f);}
    remove(fn);remove(ofn);
    return ok;
}

int main(void){
    printf("═══════════════════════════════════════════════════\n");
    printf("MESOSCALE PATTERN: The shape of the ~10 right vars\n");
    printf("═══════════════════════════════════════════════════\n\n");

    int test_n[]={200,300,500};

    for(int ti=0;ti<3;ti++){
        int nn=test_n[ti]; int steps=2000+nn*15;

        for(int seed=0;seed<15;seed++){
            unsigned long long iseed=44000000ULL+seed;
            generate(nn,4.267,iseed);
            int n=nn,m=n_clauses;

            /* Get MiniSat truth */
            if(!get_minisat_solution(n,iseed))continue;

            /* Physics + WalkSAT */
            physics(steps,42+seed*31);
            recompute();rng_seed(seed*777);
            walksat_phase(n*200);

            int nu=count_unsat();
            if(nu<3)continue;

            /* THE DIFF: vars where assignment ≠ solution */
            int diff[MAX_N],ndiff=0;
            int is_diff[MAX_N]; memset(is_diff,0,sizeof(int)*n);
            for(int v=0;v<n;v++){
                if(assignment[v]!=solution[v]){
                    diff[ndiff++]=v;is_diff[v]=1;}}

            /* Ghost vars (in unsat clauses) */
            int is_ghost[MAX_N]; memset(is_ghost,0,sizeof(int)*n);
            int n_ghost=0;
            for(int ci=0;ci<m;ci++){if(clause_sc[ci]!=0)continue;
                for(int j=0;j<3;j++){int v=cl_var[ci][j];
                    if(!is_ghost[v]){is_ghost[v]=1;n_ghost++;}}}

            /* How many diff are ghosts? How many ghosts are diff? */
            int diff_and_ghost=0,diff_not_ghost=0,ghost_not_diff=0;
            for(int i=0;i<ndiff;i++)
                if(is_ghost[diff[i]])diff_and_ghost++;else diff_not_ghost++;
            for(int v=0;v<n;v++)
                if(is_ghost[v]&&!is_diff[v])ghost_not_diff++;

            printf("n=%d seed=%d: %d unsat, %d wrong vars, %d ghosts\n",
                   nn,seed,nu,ndiff,n_ghost);
            printf("  Wrong ∩ ghost: %d | Wrong only: %d | Ghost only: %d\n",
                   diff_and_ghost,diff_not_ghost,ghost_not_diff);
            printf("  Wrong vars = %.1f%% of n\n",100.0*ndiff/n);

            /* ═══ CONNECTIVITY of diff vars ═══ */
            int diff_adj[MAX_N][50],diff_adj_n[MAX_N];
            memset(diff_adj_n,0,sizeof(int)*n);
            for(int ci=0;ci<m;ci++){
                int in_diff[3],nd2=0;
                for(int j=0;j<3;j++)if(is_diff[cl_var[ci][j]])in_diff[nd2++]=cl_var[ci][j];
                for(int a=0;a<nd2;a++)for(int b=a+1;b<nd2;b++){
                    int va=in_diff[a],vb=in_diff[b];
                    if(diff_adj_n[va]<50)diff_adj[va][diff_adj_n[va]++]=vb;
                    if(diff_adj_n[vb]<50)diff_adj[vb][diff_adj_n[vb]++]=va;}}

            /* Components of diff subgraph */
            int comp[MAX_N]; memset(comp,-1,sizeof(int)*n);
            int ncomp=0;
            for(int i=0;i<ndiff;i++){int v=diff[i];if(comp[v]>=0)continue;
                comp[v]=ncomp;int q[MAX_N],qh=0,qt=0;q[qt++]=v;
                while(qh<qt){int u=q[qh++];
                    for(int d=0;d<diff_adj_n[u];d++){int w=diff_adj[u][d];
                        if(comp[w]<0){comp[w]=ncomp;q[qt++]=w;}}}
                ncomp++;}

            /* Component sizes */
            int comp_sizes[200]; memset(comp_sizes,0,sizeof(comp_sizes));
            for(int i=0;i<ndiff;i++)if(comp[diff[i]]<200)comp_sizes[comp[diff[i]]]++;
            int max_comp=0;
            for(int c=0;c<ncomp;c++)if(comp_sizes[c]>max_comp)max_comp=comp_sizes[c];

            printf("  Diff components: %d (largest=%d)\n",ncomp,max_comp);

            /* ═══ DIFF VARS: ghost score properties ═══ */
            /* Are the right vars (diff) distinguishable from wrong ghosts? */
            double diff_match=0,ghost_nd_match=0;
            int n_diff_m=0,n_gnd_m=0;
            for(int v=0;v<n;v++){
                int match=0,total=0;
                for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
                    total++;if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))match++;}
                double mr=total>0?(double)match/total:0.5;
                if(is_diff[v]){diff_match+=mr;n_diff_m++;}
                else if(is_ghost[v]){ghost_nd_match+=mr;n_gnd_m++;}}
            if(n_diff_m>0&&n_gnd_m>0)
                printf("  match_ratio: wrong=%.3f, ghost_but_correct=%.3f\n",
                       diff_match/n_diff_m,ghost_nd_match/n_gnd_m);

            /* ═══ How many cold starts agree on wrong vars? ═══ */
            int n_runs=5;
            int run_a[5][MAX_N];
            for(int r=0;r<n_runs;r++){
                physics(steps,100+r*13337+seed*99991);
                recompute();rng_seed(r*77+seed);
                walksat_phase(n*200);
                memcpy(run_a[r],assignment,sizeof(int)*n);}
            /* Restore primary */
            /* For diff vars: in how many runs does majority = solution? */
            int maj_correct=0,maj_wrong=0;
            for(int i=0;i<ndiff;i++){int v=diff[i];
                int sum=0;for(int r=0;r<n_runs;r++)sum+=run_a[r][v];
                int maj=(sum*2>n_runs)?1:0;
                if(maj==solution[v])maj_correct++;else maj_wrong++;}
            printf("  Majority gives CORRECT for diff vars: %d/%d (%.0f%%)\n",
                   maj_correct,ndiff,100.0*maj_correct/fmax(ndiff,1));

            /* Among non-diff (correct) vars: majority correct? */
            int maj_cor_nd=0,n_nd=0;
            for(int v=0;v<n;v++){if(is_diff[v])continue;n_nd++;
                int sum=0;for(int r=0;r<n_runs;r++)sum+=run_a[r][v];
                int maj=(sum*2>n_runs)?1:0;
                /* Primary assignment is correct for non-diff */
                /* But we used primary for walksat... check against solution */
                if(maj==solution[v])maj_cor_nd++;}
            printf("  Majority gives CORRECT for right vars: %d/%d (%.0f%%)\n",
                   maj_cor_nd,n_nd,100.0*maj_cor_nd/fmax(n_nd,1));

            printf("\n");
            if(ti>=1)break; /* one instance for n=300,500 */
        }
    }
    return 0;
}
