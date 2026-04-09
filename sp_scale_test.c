/*
 * SP SCALE TEST: Can SP solve n=5000, 10000 at α=4.0-4.1?
 *
 * Compile: gcc -O3 -march=native -o sp_scale sp_scale_test.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAX_N       20000
#define MAX_CLAUSES 100000
#define MAX_K       3
#define MAX_DEGREE  300

static int n_vars, n_clauses;
static int cl_var[MAX_CLAUSES][MAX_K];
static int cl_sign[MAX_CLAUSES][MAX_K];
static int cl_active[MAX_CLAUSES];
static int var_fixed[MAX_N];
static int vlist[MAX_N][MAX_DEGREE];
static int vpos[MAX_N][MAX_DEGREE];
static int vdeg[MAX_N];
static double eta[MAX_CLAUSES][MAX_K];
static double W_plus[MAX_N], W_minus[MAX_N];

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
static double rng_double(void){return(rng_next()>>11)*(1.0/9007199254740992.0);}

static void generate(int n,double ratio,unsigned long long seed){
    n_vars=n;n_clauses=(int)(ratio*n);
    if(n_clauses>MAX_CLAUSES)n_clauses=MAX_CLAUSES;
    rng_seed(seed);memset(vdeg,0,sizeof(int)*n);
    for(int ci=0;ci<n_clauses;ci++){
        int vs[3];vs[0]=rng_next()%n;
        do{vs[1]=rng_next()%n;}while(vs[1]==vs[0]);
        do{vs[2]=rng_next()%n;}while(vs[2]==vs[0]||vs[2]==vs[1]);
        for(int j=0;j<3;j++){
            cl_var[ci][j]=vs[j];cl_sign[ci][j]=(rng_next()&1)?1:-1;
            int v=vs[j];
            if(vdeg[v]<MAX_DEGREE){vlist[v][vdeg[v]]=ci;vpos[v][vdeg[v]]=j;vdeg[v]++;}
        }
    }
    for(int ci=0;ci<n_clauses;ci++)cl_active[ci]=1;
    memset(var_fixed,-1,sizeof(int)*n);
}

static inline double sp_edge(int ci,int pos_i){
    double product=1.0;
    for(int pj=0;pj<3;pj++){
        if(pj==pos_i)continue;
        int j=cl_var[ci][pj];
        if(var_fixed[j]>=0){int sj=cl_sign[ci][pj];
            if((sj==1&&var_fixed[j]==1)||(sj==-1&&var_fixed[j]==0))return 0.0;continue;}
        int sja=cl_sign[ci][pj];double ps=1.0,pu=1.0;
        for(int d=0;d<vdeg[j];d++){
            int bi=vlist[j][d],bp=vpos[j][d];
            if(bi==ci||!cl_active[bi])continue;
            int bsat=0;for(int k=0;k<3;k++){int vk=cl_var[bi][k];
                if(var_fixed[vk]>=0){int sk=cl_sign[bi][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){bsat=1;break;}}}
            if(bsat)continue;
            double eb=eta[bi][bp];
            if(cl_sign[bi][bp]==sja)ps*=(1.0-eb);else pu*=(1.0-eb);
        }
        double Pu=(1.0-pu)*ps,Ps=(1.0-ps)*pu,P0=pu*ps;
        double den=Pu+Ps+P0;
        product*=(den>1e-15)?(Pu/den):0.0;
    }
    return product;
}

static double sp_sweep(double rho){
    double mc=0;
    for(int ci=0;ci<n_clauses;ci++){
        if(!cl_active[ci])continue;
        for(int p=0;p<3;p++){
            if(var_fixed[cl_var[ci][p]]>=0)continue;
            double nv=sp_edge(ci,p),ov=eta[ci][p];
            double up=rho*ov+(1.0-rho)*nv;
            double ch=fabs(up-ov);if(ch>mc)mc=ch;
            eta[ci][p]=up;
        }
    }
    return mc;
}

static void compute_bias(void){
    for(int i=0;i<n_vars;i++){
        W_plus[i]=W_minus[i]=0;if(var_fixed[i]>=0)continue;
        double pp=1.0,pm=1.0;
        for(int d=0;d<vdeg[i];d++){
            int ci=vlist[i][d],p=vpos[i][d];
            if(!cl_active[ci])continue;
            int sat=0;for(int k=0;k<3;k++){int vk=cl_var[ci][k];
                if(vk!=i&&var_fixed[vk]>=0){int sk=cl_sign[ci][k];
                    if((sk==1&&var_fixed[vk]==1)||(sk==-1&&var_fixed[vk]==0)){sat=1;break;}}}
            if(sat)continue;
            double e=eta[ci][p];
            if(cl_sign[ci][p]==1)pp*=(1.0-e);else pm*=(1.0-e);
        }
        double pip=(1.0-pp)*pm,pim=(1.0-pm)*pp,pi0=pp*pm;
        double tot=pip+pim+pi0;
        if(tot>1e-15){W_plus[i]=pip/tot;W_minus[i]=pim/tot;}
    }
}

static int unit_prop(void){
    int changed=1;while(changed){changed=0;
        for(int ci=0;ci<n_clauses;ci++){
            if(!cl_active[ci])continue;
            int sat=0,fc=0,fv=-1,fs=0;
            for(int j=0;j<3;j++){int v=cl_var[ci][j],s=cl_sign[ci][j];
                if(var_fixed[v]>=0){if((s==1&&var_fixed[v]==1)||(s==-1&&var_fixed[v]==0))sat=1;}
                else{fc++;fv=v;fs=s;}}
            if(sat){cl_active[ci]=0;continue;}
            if(fc==0)return 1;
            if(fc==1){var_fixed[fv]=(fs==1)?1:0;changed=1;}}}
    return 0;
}

static int walksat(int max_flips){
    int n=n_vars,m=n_clauses;
    int *a=(int*)malloc(n*sizeof(int));
    for(int v=0;v<n;v++)a[v]=(var_fixed[v]>=0)?var_fixed[v]:((rng_next()&1)?1:0);
    int *sc=(int*)calloc(m,sizeof(int));
    for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++){
        int v=cl_var[ci][j],s=cl_sign[ci][j];
        if((s==1&&a[v]==1)||(s==-1&&a[v]==0))sc[ci]++;}
    int *ul=(int*)malloc(m*sizeof(int)),*up2=(int*)malloc(m*sizeof(int));
    int nu=0;memset(up2,-1,sizeof(int)*m);
    for(int ci=0;ci<m;ci++)if(sc[ci]==0){up2[ci]=nu;ul[nu++]=ci;}
    for(int f=0;f<max_flips&&nu>0;f++){
        int ci=ul[rng_next()%nu];
        int bv=cl_var[ci][0],bb=m+1,zb=-1;
        for(int j=0;j<3;j++){int v=cl_var[ci][j],br=0;
            for(int d=0;d<vdeg[v];d++){int oci=vlist[v][d],opos=vpos[v][d];
                int os=cl_sign[oci][opos];
                if(((os==1&&a[v]==1)||(os==-1&&a[v]==0))&&sc[oci]==1)br++;}
            if(br==0){zb=v;break;}if(br<bb){bb=br;bv=v;}}
        int fv=(zb>=0)?zb:((rng_next()%100<57)?cl_var[ci][rng_next()%3]:bv);
        int old=a[fv],nw=1-old;a[fv]=nw;
        for(int d=0;d<vdeg[fv];d++){int oci=vlist[fv][d],opos=vpos[fv][d];
            int os=cl_sign[oci][opos];
            int was=((os==1&&old==1)||(os==-1&&old==0));
            int now=((os==1&&nw==1)||(os==-1&&nw==0));
            if(was&&!now){sc[oci]--;if(sc[oci]==0){up2[oci]=nu;ul[nu++]=oci;}}
            else if(!was&&now){sc[oci]++;if(sc[oci]==1){int p3=up2[oci];
                if(p3>=0&&p3<nu){int l=ul[nu-1];ul[p3]=l;up2[l]=p3;up2[oci]=-1;nu--;}}}}}
    for(int v=0;v<n;v++)var_fixed[v]=a[v];
    int res=m-nu;free(a);free(sc);free(ul);free(up2);return res;
}

static void fix_var(int v,int val){
    var_fixed[v]=val;
    for(int d=0;d<vdeg[v];d++){int ci=vlist[v][d],p=vpos[v][d];
        if(!cl_active[ci])continue;int s=cl_sign[ci][p];
        if((s==1&&val==1)||(s==-1&&val==0))cl_active[ci]=0;}
}

static int saved_a[MAX_CLAUSES],saved_f[MAX_N];

static int sp_solve(int nn){
    int n=nn,m=n_clauses;
    if(unit_prop())return 0;
    memcpy(saved_a,cl_active,sizeof(int)*m);
    memcpy(saved_f,var_fixed,sizeof(int)*n);

    for(int restart=0;restart<3;restart++){
        if(restart>0){memcpy(cl_active,saved_a,sizeof(int)*m);memcpy(var_fixed,saved_f,sizeof(int)*n);}
        int nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;

        rng_seed(42ULL+restart*9973ULL+(unsigned long long)n*13);
        for(int ci=0;ci<m;ci++)for(int j=0;j<3;j++)eta[ci][j]=rng_double();

        while(nf<n){
            int conv=0;
            for(int iter=0;iter<200;iter++){
                double ch=sp_sweep(0.1);if(ch<1e-4){conv=1;break;}}
            if(!conv)for(int iter=0;iter<100;iter++){
                double ch=sp_sweep(0.3);if(ch<1e-4){conv=1;break;}}
            if(!conv)break;

            double max_eta=0;
            for(int ci=0;ci<m;ci++){if(!cl_active[ci])continue;
                for(int j=0;j<3;j++){if(var_fixed[cl_var[ci][j]]>=0)continue;
                    if(eta[ci][j]>max_eta)max_eta=eta[ci][j];}}
            if(max_eta<0.01)break;

            compute_bias();
            int nfree=n-nf;
            int nfix=nfree/50;if(nfix<1)nfix=1;if(nfix>100)nfix=100;

            for(int f=0;f<nfix;f++){
                double bb=-1;int bv=-1,bval=0;
                for(int v=0;v<n;v++){if(var_fixed[v]>=0)continue;
                    double b=fabs(W_plus[v]-W_minus[v]);
                    if(b>bb){bb=b;bv=v;bval=(W_plus[v]>W_minus[v])?1:0;}}
                if(bv<0||bb<0.001)break;
                fix_var(bv,bval);nf++;
            }
            if(unit_prop())break;
            nf=0;for(int v=0;v<n;v++)if(var_fixed[v]>=0)nf++;
        }

        int flips=n*5000;if(flips>20000000)flips=20000000;
        for(int ws=0;ws<3;ws++){
            rng_seed(restart*77777ULL+ws*12345ULL+nf);
            int sat=walksat(flips);if(sat==m)return sat;
        }
    }
    rng_seed(999999ULL);return walksat(n_vars*10000);
}

int main(void){
    printf("═══════════════════════════════════════════\n");
    printf("SP SCALE TEST: α=4.0-4.1, n up to 20000\n");
    printf("═══════════════════════════════════════════\n\n");

    double ratios[] = {4.0, 4.1};
    int test_n[] = {1000, 2000, 3000, 5000, 7500, 10000, 15000, 20000};

    for(int ri=0; ri<2; ri++) {
        printf("α=%.1f:\n", ratios[ri]);

        for(int ti=0; ti<8; ti++) {
            int nn=test_n[ti];
            int ni=3;

            int solved=0,total=0;
            double tms=0;

            for(int seed=0; seed<ni*3 && total<ni; seed++) {
                generate(nn, ratios[ri], 11000000ULL+seed);
                clock_t t0=clock();
                rng_seed(seed*31337ULL);
                int sat=sp_solve(nn);
                clock_t t1=clock();
                double ms=(double)(t1-t0)*1000.0/CLOCKS_PER_SEC;
                tms+=ms;
                total++;
                if(sat==n_clauses) solved++;
                printf("  n=%5d seed=%d: %s (%.1fs)\n",
                       nn, seed, sat==n_clauses?"SOLVED":"failed", ms/1000);
                fflush(stdout);
            }

            printf("  → n=%d: %d/%d solved (%.0f%%, avg %.1fs)\n\n",
                   nn,solved,total,100.0*solved/total,tms/total/1000);
            fflush(stdout);

            if(tms/total > 120000 && solved == 0) {
                printf("  (stopping: >2min/instance)\n");
                break;
            }
        }
        printf("\n");
    }

    return 0;
}
