/* Level 2 observational runner. Core physics is reused, never changed.
   Standalone executable: no modifications to the production runners. */
#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dynamics.h"
#include "ising.h"
#include "nfold.h"
#include "rng.h"

typedef struct {
    size_t L;
    double T, J, H;
    uint64_t seed, stream, trace_every, snapshot_every, max_steps, max_frames;
    int nfold;
    DynamicsType dynamics;
    const char *trace_path;
    const char *frames_prefix;
} Opt;

static void usage(const char *exe) {
    fprintf(stderr,
        "Usage: %s --algorithm standard|nfold --L 32 --T 1.5 --J 1 --H -0.75\n"
        "  --dynamics glauber|metropolis --seed 1234 --stream 1\n"
        "  --trace path.csv --frames-prefix path/frame --trace-every 10\n"
        "  --snapshot-every 200 --max-frames 120 --max-steps 0\n"
        "  max-steps counts attempted updates (Standard) or accepted events (n-fold); 0=unlimited\n", exe);
}
static int read_u64(const char *s, uint64_t *out) {
    if (!s || *s == '-' || *s == '+') return -1;
    errno = 0;
    char *end = NULL;
    unsigned long long x = strtoull(s, &end, 10);
    if (errno || !end || end == s || *end) return -1;
    *out = (uint64_t)x;
    return 0;
}
static int read_double(const char *s, double *out) {
    errno = 0;
    char *end = NULL;
    double x = strtod(s, &end);
    if (errno || !end || end == s || *end || !isfinite(x)) return -1;
    *out = x;
    return 0;
}
static int parse(int argc, char **argv, Opt *o) {
    *o = (Opt){32, 1.5, 1.0, -0.75, 1234, 1, 10, 200, 0, 120, 0,
                DYNAMICS_GLAUBER, NULL, NULL};
    for (int k = 1; k < argc; ++k) {
        if (!strcmp(argv[k], "--help")) { usage(argv[0]); return 1; }
        if (k + 1 == argc) return -1;
        const char *a = argv[k], *v = argv[++k];
        uint64_t integer = 0;
        if (!strcmp(a, "--L")) {
            if (read_u64(v, &integer) || integer > SIZE_MAX) return -1;
            o->L = (size_t)integer;
        } else if (!strcmp(a, "--T")) {
            if (read_double(v, &o->T)) return -1;
        } else if (!strcmp(a, "--J")) {
            if (read_double(v, &o->J)) return -1;
        } else if (!strcmp(a, "--H")) {
            if (read_double(v, &o->H)) return -1;
        } else if (!strcmp(a, "--seed")) {
            if (read_u64(v, &o->seed)) return -1;
        } else if (!strcmp(a, "--stream")) {
            if (read_u64(v, &o->stream)) return -1;
        } else if (!strcmp(a, "--trace-every")) {
            if (read_u64(v, &o->trace_every)) return -1;
        } else if (!strcmp(a, "--snapshot-every")) {
            if (read_u64(v, &o->snapshot_every)) return -1;
        } else if (!strcmp(a, "--max-frames")) {
            if (read_u64(v, &o->max_frames)) return -1;
        } else if (!strcmp(a, "--max-steps")) {
            if (read_u64(v, &o->max_steps)) return -1;
        } else if (!strcmp(a, "--algorithm")) {
            if (!strcmp(v, "nfold")) o->nfold = 1;
            else if (!strcmp(v, "standard")) o->nfold = 0;
            else return -1;
        } else if (!strcmp(a, "--dynamics")) {
            if (dynamics_parse(v, &o->dynamics)) return -1;
        } else if (!strcmp(a, "--trace")) {
            o->trace_path = v;
        } else if (!strcmp(a, "--frames-prefix")) {
            o->frames_prefix = v;
        } else return -1;
    }
    if (o->L < 4 || o->L % 2 || o->T <= 0 || o->J <= 0 || o->H >= 0 ||
        !o->trace_path || !o->frames_prefix || !o->trace_every ||
        !o->snapshot_every || !o->max_frames || o->L > SIZE_MAX / o->L)
        return -1;
    return 0;
}
static void trace_line(FILE *file, const Opt *o, const IsingLattice *lat,
                       uint64_t attempts, uint64_t events, int final) {
    fprintf(file, "%s,%s,%zu,%.17g,%.17g,%.17g,"
                  "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%.17g,%.17g,%.17g,%d,%d\n",
            o->nfold ? "nfold" : "standard", dynamics_name(o->dynamics),
            lat->L, o->T, o->J, o->H,
            o->seed, attempts, events, (double)attempts / (double)lat->N,
            (double)lat->M / (double)lat->N, lat->E / (double)lat->N,
            lat->M <= 0, final);
}
static int frame(const Opt *o, const IsingLattice *lat, uint64_t attempts,
                 uint64_t events, uint64_t *count, int final) {
    if (*count >= o->max_frames && !final) return 0;
    char filename[4096];
    int n = snprintf(filename, sizeof(filename), "%s_%06" PRIu64 ".csv",
                     o->frames_prefix, *count);
    if (n < 0 || (size_t)n >= sizeof(filename)) return -1;
    FILE *f = fopen(filename, "wx"); /* do not replace existing frame */
    if (!f) { perror(filename); return -1; }
    for (size_t y = 0; y < lat->L; ++y) {
        for (size_t x = 0; x < lat->L; ++x)
            fprintf(f, "%s%d", x ? "," : "", (int)lat->spin[y * lat->L + x]);
        fputc('\n', f);
    }
    if (fclose(f)) return -1;
    char index_path[4096];
    n = snprintf(index_path, sizeof(index_path), "%s_index.csv", o->frames_prefix);
    if (n < 0 || (size_t)n >= sizeof(index_path)) return -1;
    FILE *idx = fopen(index_path, "a");
    if (!idx) return -1;
    /* Store only the basename to keep the index portable across computers. */
    const char *basename = strrchr(filename, '/');
    const char *windows_sep = strrchr(filename, '\\');
    if (windows_sep && (!basename || windows_sep > basename)) basename = windows_sep;
    basename = basename ? basename + 1 : filename;
    fprintf(idx, "%s,%" PRIu64 ",%" PRIu64 ",%.17g,%.17g,%.17g,%d\n",
            basename, attempts, events, (double)attempts / (double)lat->N,
            (double)lat->M / (double)lat->N, lat->E / (double)lat->N, final);
    if (fclose(idx)) return -1;
    ++*count;
    return 0;
}
int main(int argc, char **argv) {
    Opt o;
    const int p = parse(argc, argv, &o);
    if (p == 1) return 0;
    if (p != 0) { usage(argv[0]); return 2; }
    FILE *f = fopen(o.trace_path, "wx");
    if (!f) { perror(o.trace_path); return 1; }
    fprintf(f, "algorithm,dynamics,L,T,J,H,seed,attempts,events,time_mcss,m_per_spin,e_per_spin,reached_M0,final\n");
    char idxfile[4096];
    if (snprintf(idxfile, sizeof(idxfile), "%s_index.csv", o.frames_prefix) >= (int)sizeof(idxfile)) {
        fclose(f); return 2;
    }
    FILE *idx = fopen(idxfile, "wx");
    if (!idx) { perror(idxfile); fclose(f); return 1; }
    fputs("file,attempts,events,time_mcss,m_per_spin,e_per_spin,final\n", idx);
    fclose(idx);
    Rng rng;
    rng_seed(&rng, o.seed, o.stream);
    IsingLattice lat_standard = {0};
    NfoldState state = {0};
    NfoldConfig cfg = {o.L, o.T, o.J, o.H, o.dynamics, 0, 0};
    int rc = o.nfold ? nfold_state_init(&state, &cfg)
                     : ising_init(&lat_standard, o.L, o.J, o.H, +1);
    if (rc) { fprintf(stderr, "Cannot init lattice: %d\n", rc); fclose(f); return 1; }
    IsingLattice *lat = o.nfold ? &state.lattice : &lat_standard;
    const double beta = 1.0 / o.T;
    uint64_t attempts = 0, events = 0, frames = 0;
    trace_line(f, &o, lat, attempts, events, 0);
    if (frame(&o, lat, attempts, events, &frames, 0)) { rc = -1; goto cleanup; }
    while (lat->M > 0) {
        if (o.max_steps && (o.nfold ? events : attempts) >= o.max_steps) break;
        if (o.nfold) {
            uint64_t wait = 0;
            rc = nfold_step(&state, &rng, &wait, NULL, NULL);
            if (rc) break;
            attempts = state.equivalent_attempts;
            events = state.events;
        } else {
            const size_t site = (size_t)rng_bounded_u64(&rng, (uint64_t)lat->N);
            const double de = ising_delta_energy(lat, site);
            const double prob = dynamics_probability(o.dynamics, beta, de);
            ++attempts;
            if (rng_uniform01(&rng) < prob) {
                ising_flip(lat, site);
                ++events;
            } else continue; /* only record physical configuration changes */
        }
        if (events % o.trace_every == 0 && lat->M > 0)
            trace_line(f, &o, lat, attempts, events, 0);
        if (events % o.snapshot_every == 0 && lat->M > 0 &&
            frame(&o, lat, attempts, events, &frames, 0)) { rc = -1; break; }
    }
    if (!rc) {
        trace_line(f, &o, lat, attempts, events, 1);
        if (frame(&o, lat, attempts, events, &frames, 1)) rc = -1;
    }
cleanup:
    if (o.nfold) nfold_state_free(&state);
    else ising_free(&lat_standard);
    if (fclose(f)) rc = -1;
    if (rc) { fprintf(stderr, "Trace run failed: %d\n", rc); return 1; }
    printf("algorithm=%s events=%" PRIu64 " attempts=%" PRIu64 " frames=%" PRIu64 "\n",
           o.nfold ? "nfold" : "standard", events, attempts, frames);
    return 0;
}
