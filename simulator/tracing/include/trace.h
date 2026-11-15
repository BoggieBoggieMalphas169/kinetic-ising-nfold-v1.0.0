#ifndef ISING_TRACE_H
#define ISING_TRACE_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include "ising.h"

typedef struct {
    const char *algorithm;
    const char *dynamics;
    double T, J, H;
    uint64_t seed, stream, run;
} TraceMetadata;

typedef struct {
    FILE *frames;
    FILE *events;
    TraceMetadata meta;
    uint64_t frame;
    uint64_t every_events;
    uint64_t last_frame_attempts;
    uint64_t last_frame_events;
    int has_frame;
} TraceWriter;

/* A null writer is supported by the simulation engines (tracing disabled).
 * Prefix creates <prefix>_frames.csv and <prefix>_events.csv without overwriting.
 * A trace is for one selected run and every_events is an accepted-event stride.
 */
int trace_open(TraceWriter *writer, const char *prefix, TraceMetadata meta,
               uint64_t every_events);
int trace_initial(TraceWriter *writer, const IsingLattice *lat);
int trace_accepted(TraceWriter *writer, const IsingLattice *lat,
                   uint64_t attempts, uint64_t events, uint64_t wait_attempts,
                   size_t flipped_site);
int trace_final(TraceWriter *writer, const IsingLattice *lat,
                uint64_t attempts, uint64_t events);
int trace_close(TraceWriter *writer);

#endif
