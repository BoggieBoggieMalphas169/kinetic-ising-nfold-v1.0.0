#ifndef NFOLD_H
#define NFOLD_H

#include <stddef.h>
#include <stdint.h>

#include "dynamics.h"
#include "ising.h"
#include "rng.h"
#include "trace.h"

typedef struct {
    size_t L;
    double T;
    double J;
    double H;
    DynamicsType dynamics;
    uint64_t max_events;          /* 0 = unlimited */
    uint64_t max_time_attempts;   /* 0 = unlimited */
} NfoldConfig;

typedef struct {
    uint64_t events;
    uint64_t equivalent_attempts;
    double time_mcss;
    double mean_wait;
    int64_t final_M;
    double final_E;
    int reached_M0;
} NfoldResult;

typedef struct {
    IsingLattice lattice;
    size_t counts[10];
    size_t *members;      /* [class * N + position] */
    size_t *position;     /* position of each site within its class */
    uint8_t *class_of;    /* 0..9 for every site */
    double delta_e[10];
    double p[10];
    double Q;
    uint64_t events;
    uint64_t equivalent_attempts;
} NfoldState;

uint64_t nfold_sample_wait(double Q, Rng *rng);
int nfold_select_class(const size_t counts[10], const double p[10], Rng *rng,
                       double *Q_out);
int nfold_state_init(NfoldState *state, const NfoldConfig *cfg);
void nfold_state_free(NfoldState *state);
int nfold_validate_classes(const NfoldState *state);
int nfold_step(NfoldState *state, Rng *rng, uint64_t *wait_attempts,
               size_t *flipped_site, int *selected_class);
int nfold_run_traced(const NfoldConfig *cfg, Rng *rng, NfoldResult *result,
                     TraceWriter *trace);
int nfold_run(const NfoldConfig *cfg, Rng *rng, NfoldResult *result);

#endif
