#include "nfold.h"

#include <float.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

static size_t *member_ptr(NfoldState *s, size_t c, size_t pos) {
    return &s->members[c * s->lattice.N + pos];
}

static const size_t *member_ptr_const(const NfoldState *s, size_t c, size_t pos) {
    return &s->members[c * s->lattice.N + pos];
}

static void class_add(NfoldState *s, size_t site, size_t c) {
    const size_t pos = s->counts[c];
    *member_ptr(s, c, pos) = site;
    s->position[site] = pos;
    s->class_of[site] = (uint8_t)c;
    ++s->counts[c];
}

static void class_remove(NfoldState *s, size_t site, size_t c) {
    const size_t pos = s->position[site];
    const size_t last_pos = s->counts[c] - 1u;
    const size_t last_site = *member_ptr(s, c, last_pos);
    *member_ptr(s, c, pos) = last_site;
    s->position[last_site] = pos;
    --s->counts[c];
}

static void reclassify_site(NfoldState *s, size_t site) {
    const size_t old_c = (size_t)s->class_of[site];
    const size_t new_c = (size_t)ising_class_index(&s->lattice, site);
    if (old_c == new_c) return;
    class_remove(s, site, old_c);
    class_add(s, site, new_c);
}

static double total_probability(const size_t counts[10], const double p[10], size_t N) {
    double sum = 0.0;
    for (size_t c = 0; c < 10u; ++c) {
        sum += (double)counts[c] * p[c];
    }
    return sum / (double)N;
}

uint64_t nfold_sample_wait(double Q, Rng *rng) {
    if (!(Q > 0.0) || !rng) return UINT64_MAX;
    if (Q >= 1.0) return 1u;
    const double r = rng_open_closed(rng);
    const double denom = log1p(-Q);
    const double x = floor(log(r) / denom) + 1.0;
    if (!isfinite(x) || x >= (double)UINT64_MAX) return UINT64_MAX;
    if (x < 1.0) return 1u;
    return (uint64_t)x;
}

int nfold_select_class(const size_t counts[10], const double p[10], Rng *rng,
                       double *Q_out) {
    if (!counts || !p || !rng) return -1;
    size_t N = 0u;
    double total = 0.0;
    for (size_t c = 0; c < 10u; ++c) {
        N += counts[c];
        total += (double)counts[c] * p[c];
    }
    if (N == 0u || !(total > 0.0)) return -1;
    const double Q = total / (double)N;
    if (Q_out) *Q_out = Q;

    const double target = rng_uniform01(rng) * total;
    double cumulative = 0.0;
    int fallback = -1;
    for (size_t c = 0; c < 10u; ++c) {
        const double w = (double)counts[c] * p[c];
        if (w > 0.0) fallback = (int)c;
        cumulative += w;
        if (target < cumulative) return (int)c;
    }
    return fallback;
}

int nfold_state_init(NfoldState *state, const NfoldConfig *cfg) {
    if (!state || !cfg || cfg->T <= 0.0 || cfg->L < 3u) return -1;
    if (cfg->L > SIZE_MAX / cfg->L) return -1;
    const size_t requested_N = cfg->L * cfg->L;
    if (requested_N % 2u != 0u) return -2;
    memset(state, 0, sizeof(*state));
    if (ising_init(&state->lattice, cfg->L, cfg->J, cfg->H, +1) != 0) return -1;

    const size_t N = state->lattice.N;
    if (N > SIZE_MAX / (10u * sizeof(size_t))) {
        nfold_state_free(state);
        return -1;
    }
    state->members = (size_t *)malloc(10u * N * sizeof(*state->members));
    state->position = (size_t *)malloc(N * sizeof(*state->position));
    state->class_of = (uint8_t *)malloc(N * sizeof(*state->class_of));
    if (!state->members || !state->position || !state->class_of) {
        nfold_state_free(state);
        return -1;
    }
    for (size_t c = 0; c < 10u; ++c) state->counts[c] = 0u;
    for (size_t i = 0; i < N; ++i) {
        const size_t c = (size_t)ising_class_index(&state->lattice, i);
        class_add(state, i, c);
    }
    dynamics_build_class_tables(cfg->dynamics, cfg->T, cfg->J, cfg->H,
                                state->delta_e, state->p);
    state->Q = total_probability(state->counts, state->p, N);
    return 0;
}

void nfold_state_free(NfoldState *state) {
    if (!state) return;
    free(state->members);
    free(state->position);
    free(state->class_of);
    state->members = NULL;
    state->position = NULL;
    state->class_of = NULL;
    ising_free(&state->lattice);
    memset(state->counts, 0, sizeof(state->counts));
    memset(state->p, 0, sizeof(state->p));
    memset(state->delta_e, 0, sizeof(state->delta_e));
    state->Q = 0.0;
    state->events = 0u;
    state->equivalent_attempts = 0u;
}

int nfold_validate_classes(const NfoldState *s) {
    if (!s || !s->members || !s->position || !s->class_of) return 0;
    const size_t N = s->lattice.N;
    size_t sum = 0u;
    for (size_t c = 0; c < 10u; ++c) {
        sum += s->counts[c];
        if (s->counts[c] > N) return 0;
        for (size_t pos = 0; pos < s->counts[c]; ++pos) {
            const size_t site = *member_ptr_const(s, c, pos);
            if (site >= N) return 0;
            if ((size_t)s->class_of[site] != c) return 0;
            if (s->position[site] != pos) return 0;
            if ((size_t)ising_class_index(&s->lattice, site) != c) return 0;
        }
    }
    if (sum != N) return 0;
    for (size_t site = 0; site < N; ++site) {
        const size_t c = (size_t)s->class_of[site];
        if (c >= 10u || s->position[site] >= s->counts[c]) return 0;
        if (*member_ptr_const(s, c, s->position[site]) != site) return 0;
        if ((size_t)ising_class_index(&s->lattice, site) != c) return 0;
    }
    return 1;
}

int nfold_step(NfoldState *s, Rng *rng, uint64_t *wait_attempts,
               size_t *flipped_site, int *selected_class) {
    if (!s || !rng) return -1;
    double Q = 0.0;
    const int c = nfold_select_class(s->counts, s->p, rng, &Q);
    if (c < 0) return -2;
    if (s->counts[(size_t)c] == 0u) return -3;

    const uint64_t wait = nfold_sample_wait(Q, rng);
    if (wait == UINT64_MAX || UINT64_MAX - s->equivalent_attempts < wait) return -4;

    const size_t pos = (size_t)rng_bounded_u64(rng, (uint64_t)s->counts[(size_t)c]);
    const size_t site = *member_ptr(s, (size_t)c, pos);

    size_t affected[5];
    size_t n_affected = 0u;
    affected[n_affected++] = site;
    for (size_t k = 0; k < 4u; ++k) {
        const size_t nb = s->lattice.nbr[4u * site + k];
        int seen = 0;
        for (size_t j = 0; j < n_affected; ++j) {
            if (affected[j] == nb) { seen = 1; break; }
        }
        if (!seen) affected[n_affected++] = nb;
    }

    ising_flip(&s->lattice, site);
    for (size_t j = 0; j < n_affected; ++j) {
        reclassify_site(s, affected[j]);
    }

    s->equivalent_attempts += wait;
    ++s->events;
    s->Q = total_probability(s->counts, s->p, s->lattice.N);

    if (wait_attempts) *wait_attempts = wait;
    if (flipped_site) *flipped_site = site;
    if (selected_class) *selected_class = c;
    return 0;
}

int nfold_run_traced(const NfoldConfig *cfg, Rng *rng, NfoldResult *result,
                     TraceWriter *trace) {
    if (!cfg || !rng || !result) return -1;
    NfoldState state;
    const int rc = nfold_state_init(&state, cfg);
    if (rc != 0) return rc;
    if (trace_initial(trace, &state.lattice) != 0) {
        nfold_state_free(&state);
        return -5;
    }

    while (state.lattice.M > 0) {
        if (cfg->max_events != 0u && state.events >= cfg->max_events) break;
        if (cfg->max_time_attempts != 0u &&
            state.equivalent_attempts >= cfg->max_time_attempts) break;
        uint64_t wait = 0u;
        size_t flipped_site = 0u;
        const int step_rc = nfold_step(&state, rng, &wait, &flipped_site, NULL);
        if (step_rc != 0) {
            nfold_state_free(&state);
            return step_rc;
        }
        if (trace_accepted(trace, &state.lattice, state.equivalent_attempts,
                           state.events, wait, flipped_site) != 0) {
            nfold_state_free(&state);
            return -5;
        }
        if (cfg->max_time_attempts != 0u &&
            state.equivalent_attempts > cfg->max_time_attempts) break;
    }

    if (trace_final(trace, &state.lattice, state.equivalent_attempts, state.events) != 0) {
        nfold_state_free(&state);
        return -5;
    }
    result->events = state.events;
    result->equivalent_attempts = state.equivalent_attempts;
    result->time_mcss = (double)state.equivalent_attempts / (double)state.lattice.N;
    result->mean_wait = state.events ? (double)state.equivalent_attempts / (double)state.events : 0.0;
    result->final_M = state.lattice.M;
    result->final_E = state.lattice.E;
    result->reached_M0 = (state.lattice.M == 0);
    nfold_state_free(&state);
    return 0;
}

int nfold_run(const NfoldConfig *cfg, Rng *rng, NfoldResult *result) {
    return nfold_run_traced(cfg, rng, result, NULL);
}
