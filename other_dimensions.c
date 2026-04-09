/*
 * HARD CORE IN OTHER DIMENSIONS
 * ═════════════════════════════
 *
 * k-flip is movement in {0,1}^n. Dead end.
 * Look at the hard core from DIFFERENT spaces:
 *
 * 1. CLAUSE SPACE: each clause = coordinate. Assignment → point in {0,1}^m.
 *    What shape is the hard core in CLAUSE space?
 *
 * 2. DIFFERENCE SPACE: diff between current assignment and physics continuous x.
 *    The residual x_continuous - x_discrete might reveal structure.
 *
 * 3. FORCE SPACE: at the stuck point, what are the FORCES on each var?
 *    The force field at equilibrium might point toward the solution.
 *
 * 4. CONSTRAINT FLOW: treat each unsat clause as a SOURCE of pressure.
 *    Where does the pressure FLOW? Does it point to the fix?
 *
 * 5. DUAL VIEW: instead of "which vars to flip", ask
 *    "which CLAUSES to relax". Remove a clause → problem easier.
 *    Which clauses, when removed, unlock the hard core?
 *
 * Compile: gcc -O3 -march=native -o other_dims other_dimensions.c -lm
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

static double x_cont[MAX_N]; /* continuous state from physics */
static void physics(int steps,unsigned long long seed){int n=n_vars;rng_seed(seed);double vel[MAX_N];for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}double force[MAX_N];for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}}for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

static void flip_var(int v){int old=assignment[v],nw=1-old;assignment[v]=nw;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}

static void walksat_phase(int flips){for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);flip_var(fv);}}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("HARD CORE IN OTHER DIMENSIONS\n");
    printf("══════════════════════════════════════════\n\n");

    int nn=200; int steps=2000+nn*15;

    for(int seed=0;seed<30;seed++){
        generate(nn,4.267,34000000ULL+seed);
        physics(steps,42+seed*31);
        recompute();
        rng_seed(seed*777);
        walksat_phase(nn*200);

        int m=n_clauses, n=n_vars;
        int init_unsat=count_unsat();
        if(init_unsat<5)continue;

        printf("n=%d seed=%d: %d unsat\n\n",nn,seed,init_unsat);

        /* Collect hard core vars and clauses */
        int is_hc[MAX_N]; memset(is_hc,0,sizeof(int)*n);
        int hc_v[MAX_N],nhv=0;
        for(int ci=0;ci<m;ci++){if(clause_sc[ci]!=0)continue;
            for(int j=0;j<3;j++){int v=cl_var[ci][j];
                if(!is_hc[v]){is_hc[v]=1;hc_v[nhv++]=v;}}}

        /* ═══ 1. CONTINUOUS RESIDUAL: x_continuous vs x_discrete ═══ */
        printf("  ── 1. CONTINUOUS RESIDUAL ──\n");
        double res_hc=0, res_other=0;
        int n_hc=0, n_other=0;
        for(int v=0;v<n;v++){
            double residual = x_cont[v] - assignment[v]; /* how far from integer */
            double abs_res = fabs(residual);
            if(is_hc[v]){res_hc+=abs_res;n_hc++;}
            else{res_other+=abs_res;n_other++;}}
        printf("  HC vars avg |x_cont - x_disc|: %.4f\n",n_hc>0?res_hc/n_hc:0);
        printf("  Other vars:                     %.4f\n",n_other>0?res_other/n_other:0);
        printf("  → HC vars are %s from their rounded value\n",
               (res_hc/fmax(n_hc,1)) > (res_other/fmax(n_other,1))*1.2 ?
               "FARTHER" : "same distance");

        /* Where does x_continuous DISAGREE with the discrete? */
        int hc_disagree=0, other_disagree=0;
        for(int v=0;v<n;v++){
            int cont_pred = (x_cont[v]>0.5)?1:0;
            if(cont_pred != assignment[v]){
                if(is_hc[v])hc_disagree++;else other_disagree++;}}
        printf("  HC vars where x_cont disagrees: %d/%d (%.0f%%)\n",
               hc_disagree,nhv,100.0*hc_disagree/fmax(nhv,1));
        printf("  Other vars:                     %d/%d (%.0f%%)\n",
               other_disagree,n-nhv,100.0*other_disagree/fmax(n-nhv,1));

        /* ═══ 2. FORCE FIELD at stuck point ═══ */
        printf("\n  ── 2. FORCE FIELD AT STUCK POINT ──\n");
        /* Compute clause forces on the DISCRETE assignment */
        double force_hc=0, force_other=0;
        double force_dir_hc=0; /* does force point TOWARD flipping? */

        double forces[MAX_N]; memset(forces,0,sizeof(double)*n);
        for(int ci=0;ci<m;ci++){
            double lit[3],prod=1.0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                lit[j]=(s==1)?(double)assignment[v]:(1.0-(double)assignment[v]);
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}
            if(prod<0.0001)continue;
            double w=sqrt(prod);
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                double t=1.0-lit[j];if(t<1e-12)t=1e-12;
                forces[v]+=s*w*(prod/t);}}

        for(int v=0;v<n;v++){
            double f=fabs(forces[v]);
            /* Does force point toward flipping? */
            int flip_dir=(forces[v]>0)?1:0; /* force says go to 1 */
            int would_flip=(flip_dir!=assignment[v]);
            if(is_hc[v]){force_hc+=f;if(would_flip)force_dir_hc++;}
            else force_other+=f;}

        printf("  HC vars avg |force|: %.4f\n",nhv>0?force_hc/nhv:0);
        printf("  Other vars:          %.4f\n",(n-nhv)>0?force_other/(n-nhv):0);
        printf("  HC vars force→flip:  %d/%d (%.0f%%)\n",
               (int)force_dir_hc,nhv,100*force_dir_hc/fmax(nhv,1));
        printf("  → Force on HC vars is %s than others\n",
               (force_hc/fmax(nhv,1))>(force_other/fmax(n-nhv,1))*1.2?"STRONGER":"similar");

        /* ═══ 3. CLAUSE SATISFACTION LANDSCAPE ═══ */
        printf("\n  ── 3. CLAUSE LANDSCAPE ──\n");
        /* For each unsat clause: how far from being satisfied? */
        /* Measure: min flips among its 3 vars to satisfy it = 1 always */
        /* But: HOW MANY of its vars have the "wrong" value? */
        int unsat_with_0_wrong=0, unsat_with_1_wrong=0,
            unsat_with_2_wrong=0, unsat_with_3_wrong=0;
        for(int ci=0;ci<m;ci++){
            if(clause_sc[ci]!=0)continue;
            int n_would_satisfy=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                /* Would the OPPOSITE value satisfy this literal? */
                int nv=1-assignment[v];
                if((s==1&&nv==1)||(s==-1&&nv==0))n_would_satisfy++;}
            switch(n_would_satisfy){
                case 0:unsat_with_0_wrong++;break;
                case 1:unsat_with_1_wrong++;break;
                case 2:unsat_with_2_wrong++;break;
                case 3:unsat_with_3_wrong++;break;}}
        printf("  Unsat clauses: %d\n",init_unsat);
        printf("  0 vars would fix: %d (ALL vars already 'right' but clause still unsat?!)\n",unsat_with_0_wrong);
        printf("  1 var would fix:  %d\n",unsat_with_1_wrong);
        printf("  2 vars would fix: %d\n",unsat_with_2_wrong);
        printf("  3 vars would fix: %d (ALL wrong → any flip fixes)\n",unsat_with_3_wrong);

        /* ═══ 4. SATISFIED CLAUSE FRAGILITY near hard core ═══ */
        printf("\n  ── 4. FRAGILITY: Satisfied clauses near HC ──\n");
        int fragile_near=0, robust_near=0, fragile_far=0, robust_far=0;
        for(int ci=0;ci<m;ci++){
            if(clause_sc[ci]==0)continue;
            int near_hc=0;
            for(int j=0;j<3;j++)if(is_hc[cl_var[ci][j]])near_hc=1;
            if(clause_sc[ci]==1){if(near_hc)fragile_near++;else fragile_far++;}
            else{if(near_hc)robust_near++;else robust_far++;}}
        printf("  Near HC: %d fragile (sat by 1 lit), %d robust (sat by 2+)\n",
               fragile_near,robust_near);
        printf("  Far from HC: %d fragile, %d robust\n",fragile_far,robust_far);
        double frag_near_frac=fragile_near/(double)fmax(fragile_near+robust_near,1);
        double frag_far_frac=fragile_far/(double)fmax(fragile_far+robust_far,1);
        printf("  Fragility ratio: near=%.0f%% vs far=%.0f%%\n",
               100*frag_near_frac,100*frag_far_frac);

        /* ═══ 5. DUAL: Which SAT clauses, if relaxed, would help? ═══ */
        printf("\n  ── 5. DUAL: Relax one sat clause → does HC shrink? ──\n");
        /* For each sat clause touching HC: if we REMOVE it,
           does a previously impossible flip become possible? */
        int helpful_removals=0, total_checked=0;
        for(int ci=0;ci<m;ci++){
            if(clause_sc[ci]==0)continue;
            int touches_hc=0;
            for(int j=0;j<3;j++)if(is_hc[cl_var[ci][j]])touches_hc=1;
            if(!touches_hc)continue;

            /* If we pretend this clause doesn't exist: */
            /* Check if any HC var now has net>0 for flipping */
            clause_sc[ci]=99; /* temporarily "remove" */
            int helps=0;
            for(int j=0;j<3;j++){
                int v=cl_var[ci][j];
                if(!is_hc[v])continue;
                int nv=1-assignment[v],fixes=0,breaks=0;
                for(int d=0;d<vdeg[v];d++){
                    int cci=vlist[v][d]; if(clause_sc[cci]==99)continue;
                    int cpos=vpos[v][d],cs=cl_sign[cci][cpos];
                    if(clause_sc[cci]==0){if((cs==1&&nv==1)||(cs==-1&&nv==0))fixes++;}
                    else if(clause_sc[cci]==1){if((cs==1&&assignment[v]==1)||(cs==-1&&assignment[v]==0))breaks++;}}
                if(fixes>breaks)helps=1;}
            clause_sc[ci]=1; /* "restore" (approximate) */
            recompute(); /* proper restore */

            if(helps)helpful_removals++;
            total_checked++;
            if(total_checked>=100)break;
        }
        printf("  Checked %d sat clauses near HC\n",total_checked);
        printf("  Helpful removals: %d (%.0f%%)\n",
               helpful_removals,100.0*helpful_removals/fmax(total_checked,1));
        if(helpful_removals>0)
            printf("  → Some sat clauses BLOCK the HC. Relaxing them would help!\n");

        printf("\n");
        break; /* one instance */
    }
    return 0;
}
