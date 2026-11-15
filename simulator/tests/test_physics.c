#include <stdlib.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>


#include "dynamics.h"

#include "ising.h"

#include "rng.h"

#include "standard_mc.h"

#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr, "CHECK failed: %s (%s:%d)\n", #expr, __FILE__, __LINE__); \
    exit(EXIT_FAILURE); \
} } while (0)

static int nearly_equal(double a, double b, double tol) {
    return fabs(a - b) <= tol * fmax(1.0, fmax(fabs(a), fabs(b)));
}

static void test_all_up_down_energy(void) {
    IsingLattice lat;
    CHECK(ising_init(&lat, 8u, 1.0, -0.75, +1) == 0);
    const double N = (double)lat.N;

    /* On a square periodic lattice there are 2N distinct nearest-neighbour bonds. */
    const double e_up = -2.0 * 1.0 * N - (-0.75) * N;
    CHECK(nearly_equal(lat.E, e_up, 1e-14));
    CHECK(lat.M == (int64_t)lat.N);

    ising_fill(&lat, -1);
    const double e_down = -2.0 * 1.0 * N + (-0.75) * N;
    CHECK(nearly_equal(lat.E, e_down, 1e-14));
    CHECK(lat.M == -(int64_t)lat.N);
    ising_free(&lat);
}

static void test_incremental_energy_and_magnetization(void) {
    IsingLattice lat;
    Rng rng;
    CHECK(ising_init(&lat, 16u, 1.0, -0.75, +1) == 0);
    rng_seed(&rng, 1234567u, 9u);

    for (int step = 0; step < 20000; ++step) {
        const size_t i = (size_t)rng_bounded_u64(&rng, (uint64_t)lat.N);
        const double old_E = lat.E;
        const int64_t old_M = lat.M;
        const int old_s = (int)lat.spin[i];
        const double de = ising_delta_energy(&lat, i);
        const int cls = ising_class_index(&lat, i);
        CHECK(nearly_equal(de,
                           dynamics_class_delta_energy((size_t)cls, lat.J, lat.H),
                           1e-14));

        ising_flip(&lat, i);

        CHECK(nearly_equal(lat.E - old_E, de, 1e-13));
        CHECK(lat.M == old_M - 2 * (int64_t)old_s);
        CHECK(nearly_equal(lat.E, ising_recompute_energy(&lat), 1e-12));
        CHECK(lat.M == ising_recompute_magnetization(&lat));

        size_t counts[10];
        CHECK(ising_count_classes(&lat, counts) == lat.N);
    }
    ising_free(&lat);
}

static void test_class_definition(void) {
    IsingLattice lat;
    CHECK(ising_init(&lat, 8u, 1.0, -3.0, +1) == 0);

    size_t counts[10];
    CHECK(ising_count_classes(&lat, counts) == lat.N);
    CHECK(counts[0] == lat.N);
    for (size_t c = 1; c < 10u; ++c) CHECK(counts[c] == 0u);

    /* Flip one spin: it becomes down with four up neighbours -> class 5 (zero-based). */
    const size_t center = 3u * lat.L + 3u;
    ising_flip(&lat, center);
    CHECK(ising_class_index(&lat, center) == 5);

    /* Its four up neighbours now have three up neighbours -> class 1. */
    for (size_t k = 0; k < 4u; ++k) {
        CHECK(ising_class_index(&lat, lat.nbr[4u * center + k]) == 1);
    }
    ising_free(&lat);
}

static void test_probabilities(void) {
    const double beta = 2.0 / 3.0;

    CHECK(dynamics_probability(DYNAMICS_METROPOLIS, beta, -2.0) == 1.0);
    CHECK(dynamics_probability(DYNAMICS_METROPOLIS, beta, 0.0) == 1.0);
    CHECK(nearly_equal(dynamics_probability(DYNAMICS_METROPOLIS, beta, 2.0),
                        exp(-beta * 2.0), 1e-14));

    CHECK(nearly_equal(dynamics_probability(DYNAMICS_GLAUBER, beta, 0.0), 0.5, 1e-14));
    CHECK(nearly_equal(dynamics_probability(DYNAMICS_GLAUBER, beta, 2.0),
                        1.0 / (1.0 + exp(beta * 2.0)), 1e-14));

    double de[10], p[10];
    dynamics_build_class_tables(DYNAMICS_GLAUBER, 1.5, 1.0, -0.75, de, p);
    for (size_t c = 0; c < 10u; ++c) {
        CHECK(isfinite(de[c]));
        CHECK(p[c] >= 0.0 && p[c] <= 1.0);
    }
}

static void test_standard_reproducibility(void) {
    StandardConfig cfg = {8u, 1.5, 1.0, -3.0, DYNAMICS_GLAUBER, 10000000u};
    Rng a, b;
    rng_seed(&a, 42u, 1u);
    rng_seed(&b, 42u, 1u);
    StandardResult ra, rb;
    CHECK(standard_run(&cfg, &a, &ra) == 0);
    CHECK(standard_run(&cfg, &b, &rb) == 0);
    CHECK(ra.attempts == rb.attempts);
    CHECK(ra.accepted == rb.accepted);
    CHECK(ra.final_M == rb.final_M);
    CHECK(ra.final_E == rb.final_E);
    CHECK(ra.reached_M0 && rb.reached_M0);
}

int main(void) {
    test_all_up_down_energy();
    test_incremental_energy_and_magnetization();
    test_class_definition();
    test_probabilities();
    test_standard_reproducibility();
    puts("test_physics: PASS");
    return 0;
}
