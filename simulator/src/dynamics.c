#include "dynamics.h"

#include <ctype.h>
#include <math.h>
#include <string.h>

const char *dynamics_name(DynamicsType d) {
    return d == DYNAMICS_METROPOLIS ? "metropolis" : "glauber";
}

static int eq_icase(const char *a, const char *b) {
    while (*a && *b) {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
        ++a; ++b;
    }
    return *a == '\0' && *b == '\0';
}

int dynamics_parse(const char *text, DynamicsType *out) {
    if (!text || !out) return -1;
    if (eq_icase(text, "glauber") || eq_icase(text, "heatbath") || eq_icase(text, "heat-bath")) {
        *out = DYNAMICS_GLAUBER;
        return 0;
    }
    if (eq_icase(text, "metropolis")) {
        *out = DYNAMICS_METROPOLIS;
        return 0;
    }
    return -1;
}

double dynamics_probability(DynamicsType d, double beta, double delta_e) {
    if (d == DYNAMICS_METROPOLIS) {
        if (delta_e <= 0.0) return 1.0;
        const double x = -beta * delta_e;
        return x < -745.0 ? 0.0 : exp(x);
    }

    const double x = beta * delta_e;
    if (x >= 0.0) {
        if (x > 745.0) return 0.0;
        const double e = exp(-x);
        return e / (1.0 + e);
    }
    if (x < -745.0) return 1.0;
    return 1.0 / (1.0 + exp(x));
}

double dynamics_class_delta_energy(size_t class_index, double J, double H) {
    if (class_index >= 10u) return NAN;
    const int s = class_index < 5u ? +1 : -1;
    const int offset = class_index < 5u ? (int)class_index : (int)class_index - 5;
    const int q_up = 4 - offset;
    const int nn_sum = 2 * q_up - 4;
    return 2.0 * (double)s * (J * (double)nn_sum + H);
}

void dynamics_build_class_tables(DynamicsType d, double T, double J, double H,
                                 double delta_e[10], double probability[10]) {
    const double beta = 1.0 / T;
    for (size_t c = 0; c < 10u; ++c) {
        delta_e[c] = dynamics_class_delta_energy(c, J, H);
        probability[c] = dynamics_probability(d, beta, delta_e[c]);
    }
}
