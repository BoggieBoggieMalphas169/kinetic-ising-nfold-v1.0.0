#include "trace.h"

#include <inttypes.h>
#include <stdlib.h>
#include <string.h>

static char *make_name(const char *prefix, const char *suffix) {
    const size_t a = strlen(prefix), b = strlen(suffix);
    if (a > SIZE_MAX - b - 1u) return NULL;
    char *out = (char *)malloc(a + b + 1u);
    if (!out) return NULL;
    memcpy(out, prefix, a);
    memcpy(out + a, suffix, b + 1u);
    return out;
}

int trace_open(TraceWriter *writer, const char *prefix, TraceMetadata meta,
               uint64_t every_events) {
    if (!writer || !prefix || !prefix[0] || !meta.algorithm || !meta.dynamics ||
        every_events == 0u) return -1;
    memset(writer, 0, sizeof(*writer));
    char *fpath = make_name(prefix, "_frames.csv");
    char *epath = make_name(prefix, "_events.csv");
    if (!fpath || !epath) { free(fpath); free(epath); return -1; }
    /* C11 exclusive create: existing traces are never overwritten. */
    writer->frames = fopen(fpath, "wx");
    if (!writer->frames) { free(fpath); free(epath); return -2; }
    writer->events = fopen(epath, "wx");
    if (!writer->events) {
        fclose(writer->frames);
        writer->frames = NULL;
        remove(fpath);
        free(fpath);
        free(epath);
        return -2;
    }
    free(fpath);
    free(epath);
    writer->meta = meta;
    writer->every_events = every_events;
    if (fputs("frame,run,algorithm,dynamics,L,T,J,H,seed,stream,attempts,time_mcss,events,M,E,spin_bits\n", writer->frames) < 0 ||
        fputs("event,run,attempts,wait_attempts,time_mcss,site,spin_after,M,E\n", writer->events) < 0) {
        (void)trace_close(writer);
        return -3;
    }
    return 0;
}

static int frame_write(TraceWriter *w, const IsingLattice *lat,
                       uint64_t attempts, uint64_t events) {
    if (!w || !w->frames || !lat) return -1;
    const TraceMetadata *m = &w->meta;
    if (fprintf(w->frames,
                "%" PRIu64 ",%" PRIu64 ",%s,%s,%zu,%.17g,%.17g,%.17g,"
                "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%.17g,%" PRIu64
                ",%" PRId64 ",%.17g,",
                w->frame, m->run, m->algorithm, m->dynamics, lat->L,
                m->T, m->J, m->H, m->seed, m->stream,
                attempts, (double)attempts / (double)lat->N, events,
                lat->M, lat->E) < 0) return -1;
    for (size_t i = 0; i < lat->N; ++i) {
        if (fputc(lat->spin[i] > 0 ? '1' : '0', w->frames) == EOF) return -1;
    }
    if (fputc('\n', w->frames) == EOF) return -1;
    w->last_frame_attempts = attempts;
    w->last_frame_events = events;
    w->has_frame = 1;
    ++w->frame;
    return 0;
}

int trace_initial(TraceWriter *w, const IsingLattice *lat) {
    return w ? frame_write(w, lat, 0u, 0u) : 0;
}

int trace_accepted(TraceWriter *w, const IsingLattice *lat,
                   uint64_t attempts, uint64_t events, uint64_t wait_attempts,
                   size_t flipped_site) {
    if (!w) return 0;
    if (!lat || !w->events || flipped_site >= lat->N || !events) return -1;
    if (fprintf(w->events, "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
                ",%.17g,%zu,%d,%" PRId64 ",%.17g\n",
                events, w->meta.run, attempts, wait_attempts,
                (double)attempts / (double)lat->N, flipped_site,
                lat->spin[flipped_site] > 0 ? 1 : 0, lat->M, lat->E) < 0) return -1;
    if (events % w->every_events == 0u) {
        return frame_write(w, lat, attempts, events);
    }
    return 0;
}

int trace_final(TraceWriter *w, const IsingLattice *lat,
                uint64_t attempts, uint64_t events) {
    if (!w) return 0;
    if (w->has_frame && w->last_frame_events == events &&
        w->last_frame_attempts == attempts) return 0;
    return frame_write(w, lat, attempts, events);
}

int trace_close(TraceWriter *w) {
    if (!w) return -1;
    int rc = 0;
    if (w->events && fclose(w->events) != 0) rc = -1;
    if (w->frames && fclose(w->frames) != 0) rc = -1;
    w->events = NULL;
    w->frames = NULL;
    return rc;
}
