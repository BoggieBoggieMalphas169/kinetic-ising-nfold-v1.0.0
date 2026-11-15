#ifndef RNG_H
#define RNG_H

#include <stdint.h>

typedef struct {
    uint64_t state;
    uint64_t inc;
} Rng;

void rng_seed(Rng *rng, uint64_t seed, uint64_t stream);
uint32_t rng_u32(Rng *rng);
uint64_t rng_u64(Rng *rng);
double rng_uniform01(Rng *rng);          /* [0,1) */
double rng_open_closed(Rng *rng);        /* (0,1] */
uint64_t rng_bounded_u64(Rng *rng, uint64_t bound);

#endif
