#ifndef DYNAMICS_H
#define DYNAMICS_H

#include <stddef.h>

typedef enum {
    DYNAMICS_GLAUBER = 0,
    DYNAMICS_METROPOLIS = 1
} DynamicsType;

const char *dynamics_name(DynamicsType d);
int dynamics_parse(const char *text, DynamicsType *out);
double dynamics_probability(DynamicsType d, double beta, double delta_e);
double dynamics_class_delta_energy(size_t class_index, double J, double H);
void dynamics_build_class_tables(DynamicsType d, double T, double J, double H,
                                 double delta_e[10], double probability[10]);

#endif
