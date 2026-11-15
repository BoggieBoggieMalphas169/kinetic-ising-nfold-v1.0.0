#ifndef STANDARD_MC_H
#define STANDARD_MC_H

#include <stddef.h>
#include <stdint.h>

#include "dynamics.h"
#include "rng.h"

typedef struct {
    size_t L;
    double T;
    double J;
    double H;
    DynamicsType dynamics;
    uint64_t max_attempts; /* 0 = unlimited */
} StandardConfig;

typedef struct {
    uint64_t attempts;
    uint64_t accepted;
    double time_mcss;
    double acceptance_rate;
    int64_t final_M;
    double final_E;
    int reached_M0;
} StandardResult;

int standard_run(const StandardConfig *cfg, Rng *rng, StandardResult *result);

#endif
