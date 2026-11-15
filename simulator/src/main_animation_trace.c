/* Trace adapter for the unmodified kinetic-ising-nfold 1.0.0 engine.
 * Store ONLY accepted spin flips and the clock measured in attempted flips. */
#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "dynamics.h"
#include "ising.h"
#include "nfold.h"
#include "rng.h"

static int uint_arg(const char *s, uint64_t *v) {
    char *e=NULL;
    if (*s=='-') return -1;
    errno=0;
    unsigned long long x=strtoull(s,&e,10);
    if (errno || e==s || *e) return -1;
    *v=(uint64_t)x;
    return 0;
}
static int double_arg(const char *s, double *v) {
    char *e=NULL;
    errno=0;
    *v=strtod(s,&e);
    return (errno || e==s || *e || !isfinite(*v)) ? -1 : 0;
}
static void row(FILE *f,uint64_t clock,size_t site,uint64_t accepted,
                int64_t M,double E,uint64_t wait,int cls,double Q) {
    fprintf(f,"%" PRIu64 ",%zu,%" PRIu64 ",%" PRId64 ",%.15g,%" PRIu64 ",%d,%.15g\n",
            clock,site,accepted,M,E,wait,cls,Q);
}
int main(int argc,char **argv) {
    if (argc != 10) {
        fprintf(stderr,"Usage: %s standard|nfold glauber|metropolis L T J H MCSS seed output.csv\n",argv[0]);
        return 2;
    }
    int nf=0;
    if (!strcmp(argv[1],"standard")) nf=0;
    else if (!strcmp(argv[1],"nfold")) nf=1;
    else return 2;
    DynamicsType dyn;
    if (dynamics_parse(argv[2],&dyn)!=0) return 2;
    uint64_t L64,mcss,seed;
    double T,J,H;
    if (uint_arg(argv[3],&L64) || double_arg(argv[4],&T) ||
        double_arg(argv[5],&J) || double_arg(argv[6],&H) ||
        uint_arg(argv[7],&mcss) || uint_arg(argv[8],&seed) ||
        L64<4 || L64>200 || (L64%2)!=0 || mcss<1 || mcss>1000 || T<=0)
        return 2;
    size_t L=(size_t)L64;
    uint64_t N=L64*L64,limit=N*mcss;
    FILE *f=fopen(argv[9],"w");
    if (!f) { perror(argv[9]); return 1; }
    fprintf(f,"clock,site,accepted,M,E,wait,class,Q\n");
    Rng rng;
    rng_seed(&rng,seed,1u);
    int rc=0;
    if (nf) {
        NfoldConfig cfg={L,T,J,H,dyn,0u,limit};
        NfoldState state;
        rc=nfold_state_init(&state,&cfg);
        if (rc==0) {
            row(f,0u,0u,0u,state.lattice.M,state.lattice.E,0u,-1,state.Q);
            while (state.lattice.M>0 && state.equivalent_attempts<limit) {
                uint64_t wait=0;
                size_t site=0;
                int cls=-1;
                double Q_before=state.Q;
                rc=nfold_step(&state,&rng,&wait,&site,&cls);
                if (rc!=0) break;
                if (state.equivalent_attempts>limit) break; /* no event beyond window */
                row(f,state.equivalent_attempts,site,state.events,
                    state.lattice.M,state.lattice.E,wait,cls,Q_before);
            }
            nfold_state_free(&state);
        }
    } else {
        IsingLattice lat;
        rc=ising_init(&lat,L,J,H,+1);
        if (rc==0) {
            row(f,0u,0u,0u,lat.M,lat.E,0u,-1,-1.0);
            uint64_t attempts=0u,accepted=0u,last=0u;
            while (lat.M>0 && attempts<limit) {
                size_t site=(size_t)rng_bounded_u64(&rng,N);
                int cls=ising_class_index(&lat,site);
                double de=ising_delta_energy(&lat,site);
                double p=dynamics_probability(dyn,1.0/T,de);
                ++attempts;
                if (rng_uniform01(&rng)<p) {
                    ising_flip(&lat,site);
                    ++accepted;
                    row(f,attempts,site,accepted,lat.M,lat.E,attempts-last,cls,p);
                    last=attempts;
                }
            }
            ising_free(&lat);
        }
    }
    if (fclose(f)!=0) rc=-10;
    if (rc!=0) fprintf(stderr,"Error generating trace: %d\n",rc);
    return rc==0 ? 0 : 1;
}
