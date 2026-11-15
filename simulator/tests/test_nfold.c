#include <stdlib.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>


#include "nfold.h"

#include "rng.h"

#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr, "CHECK failed: %s (%s:%d)\n", #expr, __FILE__, __LINE__); \
    exit(EXIT_FAILURE); \
} } while (0)

static int close_rel(double a, double b, double rel) {
    return fabs(a - b) <= rel * fmax(1.0, fabs(b));
}

static void test_initial_classes(void) {
    NfoldConfig cfg = {8u, 1.5, 1.0, -0.75, DYNAMICS_GLAUBER, 0u, 0u};
    NfoldState s;
    CHECK(nfold_state_init(&s, &cfg) == 0);
    CHECK(s.counts[0] == s.lattice.N);
    for (size_t c = 1; c < 10u; ++c) CHECK(s.counts[c] == 0u);
    CHECK(nfold_validate_classes(&s));
    nfold_state_free(&s);
}

static void test_incremental_bookkeeping(void) {
    NfoldConfig cfg = {16u, 2.0, 1.0, -3.0, DYNAMICS_GLAUBER, 0u, 0u};
    NfoldState s;
    Rng rng;
    CHECK(nfold_state_init(&s, &cfg) == 0);
    rng_seed(&rng, 20260929u, 3u);

    for (int step = 0; step < 3000 && s.lattice.M > -(int64_t)s.lattice.N; ++step) {
        uint64_t wait = 0;
        size_t site = 0;
        int c = -1;
        CHECK(nfold_step(&s, &rng, &wait, &site, &c) == 0);
        CHECK(wait >= 1u);
        CHECK(site < s.lattice.N);
        CHECK(c >= 0 && c < 10);
        CHECK(nfold_validate_classes(&s));

        const double exact_E = ising_recompute_energy(&s.lattice);
        const int64_t exact_M = ising_recompute_magnetization(&s.lattice);
        CHECK(fabs(s.lattice.E - exact_E) < 1e-9);
        CHECK(s.lattice.M == exact_M);

        size_t exact_counts[10];
        CHECK(ising_count_classes(&s.lattice, exact_counts) == s.lattice.N);
        for (size_t k = 0; k < 10u; ++k) {
            CHECK(exact_counts[k] == s.counts[k]);
        }
    }
    nfold_state_free(&s);
}

static void test_geometric_waiting_time(void) {
    const double qvals[] = {0.8, 0.25, 0.05, 0.005};
    const size_t nq = sizeof(qvals) / sizeof(qvals[0]);
    const uint64_t samples = 250000u;

    for (size_t iq = 0; iq < nq; ++iq) {
        const double Q = qvals[iq];
        const double mean_exact = 1.0 / Q;
        const double var_exact = (1.0 - Q) / (Q * Q);

        Rng rng;
        rng_seed(&rng, 777u + (uint64_t)iq, 91u + (uint64_t)iq);

        long double s1 = 0.0L, s2 = 0.0L;
        for (uint64_t n = 0; n < samples; ++n) {
            const uint64_t m = nfold_sample_wait(Q, &rng);
            CHECK(m != UINT64_MAX && m >= 1u);
            const long double x = (long double)m;
            s1 += x;
            s2 += x * x;
        }
        const double mean = (double)(s1 / (long double)samples);
        const double var = (double)(s2 / (long double)samples
                                  - (s1 / (long double)samples) * (s1 / (long double)samples));

        /* Fixed-seed statistical regression limits, deliberately much wider than sampling error. */
        CHECK(close_rel(mean, mean_exact, 0.015));
        CHECK(close_rel(var, var_exact, 0.06));
    }
}

static void test_class_selection_distribution(void) {
    const size_t counts[10] = {20u, 10u, 30u, 0u, 40u, 0u, 0u, 0u, 0u, 0u};
    const double p[10] = {0.1, 0.5, 0.2, 0.0, 0.05, 0, 0, 0, 0, 0};
    double weights[10];
    double total = 0.0;
    size_t N = 0;
    for (size_t c = 0; c < 10u; ++c) {
        weights[c] = (double)counts[c] * p[c];
        total += weights[c];
        N += counts[c];
    }

    const uint64_t samples = 300000u;
    uint64_t obs[10] = {0};
    Rng rng;
    rng_seed(&rng, 123u, 456u);
    for (uint64_t i = 0; i < samples; ++i) {
        double Q = -1.0;
        const int c = nfold_select_class(counts, p, &rng, &Q);
        CHECK(c >= 0 && c < 10);
        CHECK(close_rel(Q, total / (double)N, 1e-14));
        ++obs[(size_t)c];
    }

    for (size_t c = 0; c < 10u; ++c) {
        const double expected_prob = weights[c] / total;
        if (expected_prob == 0.0) {
            CHECK(obs[c] == 0u);
        } else {
            const double empirical = (double)obs[c] / (double)samples;
            CHECK(fabs(empirical - expected_prob) < 0.01);
        }
    }
}


static void test_uniform_member_index(void) {
    const uint64_t bound = 7u;
    const uint64_t samples = 350000u;
    uint64_t obs[7] = {0};
    Rng rng;
    rng_seed(&rng, 424242u, 17u);
    for (uint64_t i = 0; i < samples; ++i) {
        const uint64_t x = rng_bounded_u64(&rng, bound);
        CHECK(x < bound);
        ++obs[x];
    }
    const double expected = (double)samples / (double)bound;
    for (size_t i = 0; i < 7u; ++i) {
        CHECK(fabs((double)obs[i] - expected) / expected < 0.015);
    }
}

static void test_nfold_reproducibility(void) {
    NfoldConfig cfg = {8u, 1.5, 1.0, -3.0, DYNAMICS_GLAUBER, 1000000u, 0u};
    Rng a, b;
    rng_seed(&a, 991u, 5u);
    rng_seed(&b, 991u, 5u);
    NfoldResult ra, rb;
    CHECK(nfold_run(&cfg, &a, &ra) == 0);
    CHECK(nfold_run(&cfg, &b, &rb) == 0);
    CHECK(ra.events == rb.events);
    CHECK(ra.equivalent_attempts == rb.equivalent_attempts);
    CHECK(ra.final_M == rb.final_M);
    CHECK(ra.final_E == rb.final_E);
    CHECK(ra.reached_M0 && rb.reached_M0);
}

int main(void) {
    test_initial_classes();
    test_incremental_bookkeeping();
    test_geometric_waiting_time();
    test_class_selection_distribution();
    test_uniform_member_index();
    test_nfold_reproducibility();
    puts("test_nfold: PASS");
    return 0;
}
