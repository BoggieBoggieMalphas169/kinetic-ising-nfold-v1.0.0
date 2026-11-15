#ifndef ISING_H
#define ISING_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    size_t L;
    size_t N;
    double J;
    double H;
    int8_t *spin;
    size_t *nbr; /* four neighbours per site: left, right, up, down */
    int64_t M;
    double E;
} IsingLattice;

int ising_init(IsingLattice *lat, size_t L, double J, double H, int initial_spin);
void ising_free(IsingLattice *lat);
void ising_fill(IsingLattice *lat, int spin_value);
int ising_neighbor_sum(const IsingLattice *lat, size_t site);
double ising_delta_energy(const IsingLattice *lat, size_t site);
void ising_flip(IsingLattice *lat, size_t site);
double ising_recompute_energy(const IsingLattice *lat);
int64_t ising_recompute_magnetization(const IsingLattice *lat);
int ising_class_index(const IsingLattice *lat, size_t site); /* 0..9 */
size_t ising_count_classes(const IsingLattice *lat, size_t counts[10]);

#endif
