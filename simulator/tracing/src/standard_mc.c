#include "standard_mc.h"

#include <math.h>
#include <stddef.h>

#include "ising.h"

int standard_run_traced(const StandardConfig *cfg, Rng *rng, StandardResult *result,
                        TraceWriter *trace) {
    if (!cfg || !rng || !result || cfg->T <= 0.0 || cfg->L < 3u) return -1;
    if (cfg->L > SIZE_MAX / cfg->L) return -1;
    const size_t N = cfg->L * cfg->L;
    if (N % 2u != 0u) return -2; /* M=0 is unreachable for odd N */

    IsingLattice lat;
    if (ising_init(&lat, cfg->L, cfg->J, cfg->H, +1) != 0) return -1;

    const double beta = 1.0 / cfg->T;
    uint64_t attempts = 0u;
    uint64_t accepted = 0u;
    uint64_t previous_accept_attempt = 0u;
    if (trace_initial(trace, &lat) != 0) { ising_free(&lat); return -5; }

    while (lat.M > 0) {
        if (cfg->max_attempts != 0u && attempts >= cfg->max_attempts) break;
        const size_t site = (size_t)rng_bounded_u64(rng, (uint64_t)lat.N);
        const double de = ising_delta_energy(&lat, site);
        const double p = dynamics_probability(cfg->dynamics, beta, de);
        ++attempts;
        if (rng_uniform01(rng) < p) {
            ising_flip(&lat, site);
            ++accepted;
            if (trace_accepted(trace, &lat, attempts, accepted,
                               attempts - previous_accept_attempt, site) != 0) {
                ising_free(&lat);
                return -5;
            }
            previous_accept_attempt = attempts;
        }
    }

    if (trace_final(trace, &lat, attempts, accepted) != 0) { ising_free(&lat); return -5; }
    result->attempts = attempts;
    result->accepted = accepted;
    result->time_mcss = (double)attempts / (double)lat.N;
    result->acceptance_rate = attempts ? (double)accepted / (double)attempts : 0.0;
    result->final_M = lat.M;
    result->final_E = lat.E;
    result->reached_M0 = (lat.M == 0);
    ising_free(&lat);
    return 0;
}

int standard_run(const StandardConfig *cfg, Rng *rng, StandardResult *result) {
    return standard_run_traced(cfg, rng, result, NULL);
}
