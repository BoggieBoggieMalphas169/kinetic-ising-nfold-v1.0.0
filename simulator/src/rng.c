#include "rng.h"

#include <assert.h>
#include <stdint.h>

/* PCG-XSH-RR 64/32. */
uint32_t rng_u32(Rng *rng) {
    const uint64_t oldstate = rng->state;
    rng->state = oldstate * UINT64_C(6364136223846793005) + rng->inc;
    const uint32_t xorshifted = (uint32_t)(((oldstate >> 18u) ^ oldstate) >> 27u);
    const uint32_t rot = (uint32_t)(oldstate >> 59u);
    return (xorshifted >> rot) | (xorshifted << ((0u - rot) & 31u));
}

void rng_seed(Rng *rng, uint64_t seed, uint64_t stream) {
    rng->state = 0u;
    rng->inc = (stream << 1u) | 1u;
    (void)rng_u32(rng);
    rng->state += seed;
    (void)rng_u32(rng);
}

uint64_t rng_u64(Rng *rng) {
    const uint64_t hi = (uint64_t)rng_u32(rng);
    const uint64_t lo = (uint64_t)rng_u32(rng);
    return (hi << 32) | lo;
}

double rng_uniform01(Rng *rng) {
    /* 53 random bits -> exact multiple of 2^-53 in [0,1). */
    const uint64_t x = rng_u64(rng) >> 11;
    return (double)x * (1.0 / 9007199254740992.0);
}

double rng_open_closed(Rng *rng) {
    return 1.0 - rng_uniform01(rng);
}

uint64_t rng_bounded_u64(Rng *rng, uint64_t bound) {
    assert(bound > 0u);
    const uint64_t threshold = (uint64_t)(-bound) % bound;
    for (;;) {
        const uint64_t r = rng_u64(rng);
        if (r >= threshold) {
            return r % bound;
        }
    }
}
