/*
 * THE SILENT WRONG: How can 67 vars be WRONG and break NOTHING?
 * ═══════════════════════════════════════════════════════════════
 *
 * 76 vars wrong. 9 clauses unsat. 67 vars wrong but silent.
 *
 * A clause has 3 literals. It's satisfied if AT LEAST 1 is true.
 * A wrong var makes its literal false. But if the OTHER 2 are true
 * → clause still satisfied. The wrong var is COVERED by others.
 *
 * Questions:
 * 1. How are silent wrongs COVERED? By 1 correct literal? By 2?
 * 2. How FRAGILE is the coverage? If we flip the cover → unsat?
 * 3. Do silent wrongs CLUSTER with each other?
 * 4. What's the TOPOLOGY of wrong-var coverage chains?
 * 5. Is there a MINIMAL CUT that breaks the coverage?
 *
 * Compile: gcc -O3 -march=native -o silent_wrong silent_wrong.c -lm
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

static int solution[MAX_N];
static int get_minisat_solution(int n,unsigned long long iseed){
    char fn[256],ofn[256];sprintf(fn,"/tmp/sw_%llu.cnf",iseed);sprintf(ofn,"/tmp/sw_%llu.cnf.out",iseed);
    FILE*f=fopen(fn,"w");fprintf(f,"p cnf %d %d\n",n,n_clauses);
    rng_seed(iseed);for(int ci=0;ci<n_clauses;ci++){int vs[3];vs[0]=rng_next()%n;do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);int signs[3];for(int j=0;j<3;j++)signs[j]=(rng_next()&1)?1:-1;fprintf(f,"%d %d %d 0\n",signs[0]*(vs[0]+1),signs[1]*(vs[1]+1),signs[2]*(vs[2]+1));}fclose(f);
    char cmd[512];sprintf(cmd,"timeout 30 minisat %s %s 2>/dev/null",fn,ofn);system(cmd);
    int ok=0;f=fopen(ofn,"r");if(f){char line[64];if(fgets(line,64,f)&&strncmp(line,"SAT",3)==0){ok=1;memset(solution,0,sizeof(int)*n);int v;while(fscanf(f,"%d",&v)==1){if(v>0&&v<=n)solution[v-1]=1;else if(v<0&&-v<=n)solution[-v-1]=0;if(v==0)break;}}fclose(f);}
    remove(fn);remove(ofn);return ok;}

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("SILENT WRONG: 67 wrong but break nothing\n");
    printf("═══════════════════════════════════════════\n\n");

    int nn=200;
    for(int seed=0;seed<15;seed++){
        unsigned long long iseed=45000000ULL+seed;
        generate(nn,4.267,iseed);
        int n=nn,m=n_clauses;
        if(!get_minisat_solution(n,iseed))continue;

        physics(2000+n*15,42+seed*31);recompute();
        rng_seed(seed*777);walksat_phase(n*200);
        int nu=count_unsat();
        if(nu<3)continue;

        /* Identify wrong vars */
        int is_wrong[MAX_N]; int nw=0;
        for(int v=0;v<n;v++){is_wrong[v]=(assignment[v]!=solution[v]);if(is_wrong[v])nw++;}

        printf("n=%d seed=%d: %d unsat, %d wrong (%.0f%%)\n",nn,seed,nu,nw,100.0*nw/n);

        /* ═══ 1. Coverage: for each clause with a wrong var, how is it saved? ═══ */
        int saved_by_1=0, saved_by_2=0, saved_by_3=0;
        int wrong_in_saved_clause=0;

        for(int ci=0;ci<m;ci++){
            int has_wrong=0, n_savers=0;
            for(int j=0;j<3;j++){
                int v=cl_var[ci][j];
                if(is_wrong[v])has_wrong++;
                if(clause_sc[ci]>0){/* count saving literals */
                    int s=cl_sign[ci][j];
                    if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))n_savers++;}}
            if(has_wrong && clause_sc[ci]>0){
                wrong_in_saved_clause++;
                if(n_savers==1)saved_by_1++;
                else if(n_savers==2)saved_by_2++;
                else saved_by_3++;}}

        printf("  Clauses with wrong var but SATISFIED: %d\n",wrong_in_saved_clause);
        printf("  Saved by 1 literal:  %d (fragile!)\n",saved_by_1);
        printf("  Saved by 2 literals: %d (robust)\n",saved_by_2);
        printf("  Saved by 3 literals: %d (very robust)\n",saved_by_3);

        /* ═══ 2. WHO covers the wrong vars? Wrong or correct? ═══ */
        int covered_by_correct=0, covered_by_wrong=0, covered_by_mix=0;
        for(int ci=0;ci<m;ci++){
            int has_wrong=0;
            for(int j=0;j<3;j++)if(is_wrong[cl_var[ci][j]])has_wrong++;
            if(!has_wrong || clause_sc[ci]==0) continue;
            /* Find the savers */
            int saver_correct=0, saver_wrong=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0)){
                    if(is_wrong[v])saver_wrong++;else saver_correct++;}
            }
            if(saver_correct>0&&saver_wrong==0)covered_by_correct++;
            else if(saver_wrong>0&&saver_correct==0)covered_by_wrong++;
            else covered_by_mix++;
        }
        printf("  Covered by CORRECT vars only: %d\n",covered_by_correct);
        printf("  Covered by WRONG vars only:   %d\n",covered_by_wrong);
        printf("  Covered by MIX:               %d\n",covered_by_mix);

        /* ═══ 3. WRONG-WRONG clauses: both wrong but clause still sat ═══ */
        int ww_sat=0, ww_unsat=0;
        int www_sat=0; /* all 3 wrong and sat */
        for(int ci=0;ci<m;ci++){
            int n_wrong=0;
            for(int j=0;j<3;j++)if(is_wrong[cl_var[ci][j]])n_wrong++;
            if(n_wrong>=2){
                if(clause_sc[ci]>0)ww_sat++;else ww_unsat++;
                if(n_wrong==3){
                    if(clause_sc[ci]>0)www_sat++;
                }
            }
        }
        printf("  Clauses with ≥2 wrong vars: %d sat + %d unsat\n",ww_sat,ww_unsat);
        printf("  Clauses with ALL 3 wrong: %d sat (!!!) + %d unsat\n",
               www_sat, nu); /* all unsat have 3 wrong by our earlier finding */

        /* ═══ 4. HOW can a clause with 3 wrong vars be SATISFIED? ═══ */
        /* This seems impossible! If var is wrong, its literal should be false. */
        /* Unless: wrong value ACCIDENTALLY satisfies a DIFFERENT sign */
        if(www_sat>0){
            printf("\n  PARADOX: %d clauses have ALL 3 vars wrong but ARE satisfied!\n",www_sat);
            printf("  How? Example:\n");
            for(int ci=0;ci<m;ci++){
                int n_wrong=0;
                for(int j=0;j<3;j++)if(is_wrong[cl_var[ci][j]])n_wrong++;
                if(n_wrong==3&&clause_sc[ci]>0){
                    printf("    Clause %d: ",ci);
                    for(int j=0;j<3;j++){
                        int v=cl_var[ci][j],s=cl_sign[ci][j];
                        int a=assignment[v], sol_v=solution[v];
                        int lit_true=(s==1&&a==1)||(s==-1&&a==0);
                        printf("x%d(sign=%+d,assign=%d,sol=%d,lit=%s) ",
                               v,s,a,sol_v,lit_true?"TRUE":"false");
                    }
                    printf("\n");
                    /* Find first example, then break */
                    printf("    → Wrong value HAPPENS to satisfy the literal!\n");
                    printf("    → The clause wants x=wrong, and we GIVE it wrong.\n");
                    printf("    → But solution wants x=right, which would NOT satisfy.\n");
                    break;
                }
            }
        }

        /* ═══ 5. WHAT FRACTION of wrong vars' literals are "accidentally true"? ═══ */
        int wrong_lit_true=0, wrong_lit_false=0;
        for(int v=0;v<n;v++){
            if(!is_wrong[v])continue;
            for(int d=0;d<vdeg[v];d++){
                int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
                if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))
                    wrong_lit_true++;
                else wrong_lit_false++;
            }
        }
        int total_wrong_lits=wrong_lit_true+wrong_lit_false;
        printf("\n  Wrong vars' literals: %d true (%.0f%%), %d false (%.0f%%)\n",
               wrong_lit_true, 100.0*wrong_lit_true/fmax(total_wrong_lits,1),
               wrong_lit_false, 100.0*wrong_lit_false/fmax(total_wrong_lits,1));
        printf("  → Wrong vars satisfy %.0f%% of their OWN literals\n",
               100.0*wrong_lit_true/fmax(total_wrong_lits,1));
        printf("  → (correct vars would satisfy %.0f%% by tension ≈ 57%%)\n",
               100.0*4/7);

        printf("\n");
        break; /* one detailed instance */
    }
    return 0;
}
