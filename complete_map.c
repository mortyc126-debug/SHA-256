/*
 * COMPLETE MAP: Hard core from EVERY dimension simultaneously
 * ═══════════════════════════════════════════════════════════
 *
 * Not attacking. MAPPING. Every measurement we can think of.
 *
 * PHYSICAL:  force, energy, velocity, temperature
 * INFORMATION: entropy, MI, redundancy, capacity
 * TOPOLOGICAL: degree, centrality, clustering, distance
 * SPECTRAL: eigenvalues of local subgraph
 * TEMPORAL: when vars committed during physics, stability
 * STATISTICAL: distributions, correlations, higher moments
 * RELATIONAL: how HC vars relate to each other and to non-HC
 * DUAL: view from clause space, not var space
 *
 * Output: ONE comprehensive table per instance
 *
 * Compile: gcc -O3 -march=native -o complete_map complete_map.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_N      1000
#define MAX_CLAUSES 5000
#define MAX_K      3
#define MAX_DEGREE 100

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
static double x_history[500][MAX_N]; /* trajectory */
static int n_history;

static void physics_with_history(int steps,unsigned long long seed){
    int n=n_vars;rng_seed(seed);double vel[MAX_N];
    for(int v=0;v<n;v++){double p1=0,p0=0;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];if(cl_sign[ci][p]==1)p1+=1.0/3;else p0+=1.0/3;}x_cont[v]=(p1+p0>0)?0.5+0.35*(p1-p0)/(p1+p0):0.5;vel[v]=0;}
    n_history=0;
    double force[MAX_N];
    for(int step=0;step<steps;step++){double prog=(double)step/steps;double T=0.30*exp(-4.0*prog)+0.0001;double cr=(prog<0.3)?0.5*prog/0.3:(prog<0.7)?0.5+2.5*(prog-0.3)/0.4:3.0+5.0*(prog-0.7)/0.3;
        memset(force,0,sizeof(double)*n);for(int ci=0;ci<n_clauses;ci++){double lit[3],prod=1.0;for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];lit[j]=(s==1)?x_cont[v]:(1.0-x_cont[v]);double t=1.0-lit[j];if(t<1e-12)t=1e-12;prod*=t;}if(prod<0.0001)continue;double w=sqrt(prod);for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];double t=1.0-lit[j];if(t<1e-12)t=1e-12;force[v]+=s*w*(prod/t);}}
        for(int v=0;v<n;v++){if(x_cont[v]>0.5)force[v]+=cr*(1-x_cont[v]);else force[v]-=cr*x_cont[v];vel[v]=0.93*vel[v]+(force[v]+rng_normal(0,T))*0.05;x_cont[v]+=vel[v]*0.05;if(x_cont[v]<0){x_cont[v]=0.01;vel[v]=fabs(vel[v])*0.3;}if(x_cont[v]>1){x_cont[v]=0.99;vel[v]=-fabs(vel[v])*0.3;}}
        if(step%10==0&&n_history<500){memcpy(x_history[n_history],x_cont,sizeof(double)*n);n_history++;}}
    for(int v=0;v<n;v++)assignment[v]=(x_cont[v]>0.5)?1:0;}

static void flip_var(int v){int old=assignment[v],nw=1-old;assignment[v]=nw;for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];int was=((s==1&&old==1)||(s==-1&&old==0));int now=((s==1&&nw==1)||(s==-1&&nw==0));if(was&&!now)clause_sc[ci]--;else if(!was&&now)clause_sc[ci]++;}}
static void walksat_phase(int flips){for(int f=0;f<flips;f++){int uci=-1;for(int ci=0;ci<n_clauses;ci++)if(clause_sc[ci]==0){uci=ci;break;}if(uci<0)return;int bv=cl_var[uci][0],bb=n_clauses+1,zb=-1;for(int j=0;j<3;j++){int v=cl_var[uci][j],br=0;for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d],os=cl_sign[oci][opos];if(((os==1&&assignment[v]==1)||(os==-1&&assignment[v]==0))&&clause_sc[oci]==1)br++;}if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}int fv=(zb>=0)?zb:((rng_next()%100<30)?cl_var[uci][rng_next()%3]:bv);flip_var(fv);}}

int main(void){
    printf("══════════════════════════════════════════════\n");
    printf("COMPLETE MAP: Hard core from ALL dimensions\n");
    printf("══════════════════════════════════════════════\n\n");

    int nn=200;
    for(int seed=0;seed<30;seed++){
        generate(nn,4.267,35000000ULL+seed);
        int steps=2000+nn*15;
        physics_with_history(steps,42+seed*31);
        recompute();
        rng_seed(seed*777);
        walksat_phase(nn*200);

        int m=n_clauses,n=n_vars;
        int nu=count_unsat();
        if(nu<3)continue;

        /* Identify HC vars */
        int is_hc[MAX_N];memset(is_hc,0,sizeof(int)*n);
        int hc_v[MAX_N],nhv=0;
        for(int ci=0;ci<m;ci++){if(clause_sc[ci]!=0)continue;
            for(int j=0;j<3;j++){int v=cl_var[ci][j];if(!is_hc[v]){is_hc[v]=1;hc_v[nhv++]=v;}}}

        printf("n=%d seed=%d: %d unsat, %d HC vars, %d other vars\n\n",nn,seed,nu,nhv,n-nhv);

        /* ═══ COMPUTE ALL MEASUREMENTS ═══ */
        /* Per-var measurements, then averaged for HC vs other */
        double hc_vals[30][MAX_N], ot_vals[30][MAX_N];
        int hc_n=0,ot_n=0;
        char *names[30];int nm=0;

        for(int v=0;v<n;v++){
            int idx = is_hc[v] ? hc_n : ot_n;
            double *dst = is_hc[v] ? hc_vals[0] : ot_vals[0]; /* placeholder */
            int mi=0;

            /* 1. |x_cont - 0.5| — how far from undecided */
            double cont_dist = fabs(x_cont[v]-0.5);

            /* 2. |x_cont - assignment| — residual */
            double residual = fabs(x_cont[v]-assignment[v]);

            /* 3. Degree */
            double degree = vdeg[v];

            /* 4. match_ratio = signs matching current value */
            int match=0,total=0;
            for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],pos=vpos[v][d],s=cl_sign[ci][pos];
                total++;if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))match++;}
            double mr = total>0?(double)match/total:0.5;

            /* 5. Critical count */
            int critical=0;
            for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];
                if(clause_sc[ci]==1){int pos=vpos[v][d],s=cl_sign[ci][pos];
                    if((s==1&&assignment[v]==1)||(s==-1&&assignment[v]==0))critical++;}}

            /* 6. Frustrated clauses (unsat that v participates in) */
            int frustrated=0;
            for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];if(clause_sc[ci]==0)frustrated++;}

            /* 7. Fragile clauses (sat by 1 lit, involving v) */
            int fragile=0;
            for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];if(clause_sc[ci]==1)fragile++;}

            /* 8. Robust clauses (sat by 2+ lits) */
            int robust=0;
            for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];if(clause_sc[ci]>=2)robust++;}

            /* 9. Trajectory stability: std of x(t) in last 50% of physics */
            double traj_mean=0,traj_var=0;
            int t_start=n_history/2;
            for(int t=t_start;t<n_history;t++)traj_mean+=x_history[t][v];
            traj_mean/=fmax(n_history-t_start,1);
            for(int t=t_start;t<n_history;t++){double d=x_history[t][v]-traj_mean;traj_var+=d*d;}
            traj_var/=fmax(n_history-t_start,1);
            double traj_std=sqrt(traj_var);

            /* 10. Crossing count: how many times did x cross 0.5 during physics? */
            int crossings=0;
            for(int t=1;t<n_history;t++)
                if((x_history[t][v]-0.5)*(x_history[t-1][v]-0.5)<0)crossings++;

            /* 11. Commit time: first time |x-0.5| > 0.3 */
            int commit_time=n_history;
            for(int t=0;t<n_history;t++)
                if(fabs(x_history[t][v]-0.5)>0.3){commit_time=t;break;}

            /* 12. HC neighbor fraction */
            int hc_neighbors=0,total_neighbors=0;
            for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d];
                for(int j=0;j<3;j++){int w=cl_var[ci][j];if(w!=v){total_neighbors++;if(is_hc[w])hc_neighbors++;}}}
            double hc_frac=total_neighbors>0?(double)hc_neighbors/total_neighbors:0;

            /* Store */
            if(is_hc[v]){
                hc_vals[0][hc_n]=cont_dist;hc_vals[1][hc_n]=residual;
                hc_vals[2][hc_n]=degree;hc_vals[3][hc_n]=mr;
                hc_vals[4][hc_n]=critical;hc_vals[5][hc_n]=frustrated;
                hc_vals[6][hc_n]=fragile;hc_vals[7][hc_n]=robust;
                hc_vals[8][hc_n]=traj_std;hc_vals[9][hc_n]=crossings;
                hc_vals[10][hc_n]=commit_time;hc_vals[11][hc_n]=hc_frac;
                hc_n++;
            }else{
                ot_vals[0][ot_n]=cont_dist;ot_vals[1][ot_n]=residual;
                ot_vals[2][ot_n]=degree;ot_vals[3][ot_n]=mr;
                ot_vals[4][ot_n]=critical;ot_vals[5][ot_n]=frustrated;
                ot_vals[6][ot_n]=fragile;ot_vals[7][ot_n]=robust;
                ot_vals[8][ot_n]=traj_std;ot_vals[9][ot_n]=crossings;
                ot_vals[10][ot_n]=commit_time;ot_vals[11][ot_n]=hc_frac;
                ot_n++;
            }
        }

        /* ═══ PRINT COMPLETE MAP ═══ */
        char *prop_names[]={"cont_distance","residual","degree","match_ratio",
            "critical","frustrated","fragile","robust","traj_std",
            "crossings","commit_time","hc_neighbor_frac"};
        int n_props=12;

        printf("  %20s | %8s | %8s | %6s | %s\n","PROPERTY","HC","OTHER","RATIO","SIGNAL");
        printf("  " );for(int i=0;i<65;i++)printf("-");printf("\n");

        for(int p=0;p<n_props;p++){
            double hm=0,om=0;
            for(int i=0;i<hc_n;i++)hm+=hc_vals[p][i];hm/=fmax(hc_n,1);
            for(int i=0;i<ot_n;i++)om+=ot_vals[p][i];om/=fmax(ot_n,1);
            double ratio=(fabs(om)>0.001)?hm/om:(fabs(hm)>0.001?999:1);
            char *signal="";
            if(fabs(ratio-1)>0.5)signal="★★★ STRONG";
            else if(fabs(ratio-1)>0.25)signal="★★ moderate";
            else if(fabs(ratio-1)>0.10)signal="★ weak";
            printf("  %20s | %8.3f | %8.3f | %6.2f | %s\n",
                   prop_names[p],hm,om,ratio,signal);
        }

        printf("\n");
        break;
    }
    return 0;
}
