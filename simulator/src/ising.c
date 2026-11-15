#include "ising.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

static size_t idx(size_t x, size_t y, size_t L) {
    return y * L + x;
}

int ising_init(IsingLattice *lat, size_t L, double J, double H, int initial_spin) {
    if (!lat || L < 3 || (initial_spin != 1 && initial_spin != -1)) {
        return -1;
    }
    if (L > SIZE_MAX / L) {
        return -1;
    }
    memset(lat, 0, sizeof(*lat));
    lat->L = L;
    lat->N = L * L;
    lat->J = J;
    lat->H = H;
    lat->spin = (int8_t *)malloc(lat->N * sizeof(*lat->spin));
    lat->nbr = (size_t *)malloc(4u * lat->N * sizeof(*lat->nbr));
    if (!lat->spin || !lat->nbr) {
        ising_free(lat);
        return -1;
    }

    for (size_t y = 0; y < L; ++y) {
        for (size_t x = 0; x < L; ++x) {
            const size_t i = idx(x, y, L);
            const size_t xm = (x + L - 1u) % L;
            const size_t xp = (x + 1u) % L;
            const size_t ym = (y + L - 1u) % L;
            const size_t yp = (y + 1u) % L;
            lat->nbr[4u * i + 0u] = idx(xm, y, L);
            lat->nbr[4u * i + 1u] = idx(xp, y, L);
            lat->nbr[4u * i + 2u] = idx(x, ym, L);
            lat->nbr[4u * i + 3u] = idx(x, yp, L);
        }
    }
    ising_fill(lat, initial_spin);
    return 0;
}

void ising_free(IsingLattice *lat) {
    if (!lat) return;
    free(lat->spin);
    free(lat->nbr);
    memset(lat, 0, sizeof(*lat));
}

void ising_fill(IsingLattice *lat, int spin_value) {
    if (!lat || !lat->spin || (spin_value != 1 && spin_value != -1)) return;
    for (size_t i = 0; i < lat->N; ++i) {
        lat->spin[i] = (int8_t)spin_value;
    }
    lat->M = (int64_t)spin_value * (int64_t)lat->N;
    lat->E = ising_recompute_energy(lat);
}

int ising_neighbor_sum(const IsingLattice *lat, size_t site) {
    int sum = 0;
    for (size_t k = 0; k < 4u; ++k) {
        sum += (int)lat->spin[lat->nbr[4u * site + k]];
    }
    return sum;
}

double ising_delta_energy(const IsingLattice *lat, size_t site) {
    const int s = (int)lat->spin[site];
    const int nn = ising_neighbor_sum(lat, site);
    return 2.0 * (double)s * (lat->J * (double)nn + lat->H);
}

void ising_flip(IsingLattice *lat, size_t site) {
    const int old_s = (int)lat->spin[site];
    const double de = ising_delta_energy(lat, site);
    lat->spin[site] = (int8_t)(-old_s);
    lat->M -= 2 * (int64_t)old_s;
    lat->E += de;
}

double ising_recompute_energy(const IsingLattice *lat) {
    double bond_sum = 0.0;
    double field_sum = 0.0;
    const size_t L = lat->L;
    for (size_t y = 0; y < L; ++y) {
        for (size_t x = 0; x < L; ++x) {
            const size_t i = idx(x, y, L);
            const int s = (int)lat->spin[i];
            const size_t right = idx((x + 1u) % L, y, L);
            const size_t down = idx(x, (y + 1u) % L, L);
            bond_sum += (double)(s * (int)lat->spin[right]);
            bond_sum += (double)(s * (int)lat->spin[down]);
            field_sum += (double)s;
        }
    }
    return -lat->J * bond_sum - lat->H * field_sum;
}

int64_t ising_recompute_magnetization(const IsingLattice *lat) {
    int64_t m = 0;
    for (size_t i = 0; i < lat->N; ++i) {
        m += (int64_t)lat->spin[i];
    }
    return m;
}

int ising_class_index(const IsingLattice *lat, size_t site) {
    int q_up = 0;
    for (size_t k = 0; k < 4u; ++k) {
        if (lat->spin[lat->nbr[4u * site + k]] > 0) {
            ++q_up;
        }
    }
    const int offset = 4 - q_up; /* q=4 -> first class, q=0 -> fifth */
    return (lat->spin[site] > 0) ? offset : (5 + offset);
}

size_t ising_count_classes(const IsingLattice *lat, size_t counts[10]) {
    for (size_t c = 0; c < 10u; ++c) counts[c] = 0u;
    for (size_t i = 0; i < lat->N; ++i) {
        const int c = ising_class_index(lat, i);
        ++counts[(size_t)c];
    }
    size_t total = 0u;
    for (size_t c = 0; c < 10u; ++c) total += counts[c];
    return total;
}
