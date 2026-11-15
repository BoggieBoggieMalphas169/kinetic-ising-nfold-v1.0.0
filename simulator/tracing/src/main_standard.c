#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "dynamics.h"
#include "rng.h"
#include "standard_mc.h"

typedef struct {
    size_t L;
    double T, J, H;
    uint64_t runs, seed, max_attempts;
    DynamicsType dynamics;
    const char *output;
    const char *trace_prefix;
    uint64_t trace_run, trace_every;
} Cli;

static void usage(const char *p) {
    fprintf(stderr,
        "Usage: %s [--L 32] [--T 1.5] [--J 1] [--H -3] [--runs 1000]\n"
        "          [--seed 1234] [--dynamics glauber|metropolis]\n"
        "          [--max-attempts 0] [--output file.csv]\n"
        "          [--trace-prefix PATH] [--trace-run 0] [--trace-every 10]\n", p);
}

static int parse_u64(const char *s, uint64_t *v) {
    char *end = NULL;
    errno = 0;
    unsigned long long x = strtoull(s, &end, 10);
    if (errno || !end || *end) return -1;
    *v = (uint64_t)x;
    return 0;
}
static int parse_size(const char *s, size_t *v) {
    uint64_t x;
    if (parse_u64(s, &x) != 0 || x > SIZE_MAX) return -1;
    *v = (size_t)x;
    return 0;
}
static int parse_double(const char *s, double *v) {
    char *end = NULL;
    errno = 0;
    double x = strtod(s, &end);
    if (errno || !end || *end) return -1;
    *v = x;
    return 0;
}

int main(int argc, char **argv) {
    Cli c = {32u, 1.5, 1.0, -3.0, 1000u, 1234u, 0u,
             DYNAMICS_GLAUBER, "standard.csv", NULL, 0u, 1u};
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--help")) {
            usage(argv[0]);
            return 0;
        }
        if (i + 1 >= argc) {
            usage(argv[0]);
            return 2;
        }
        const char *a = argv[i];
        const char *v = argv[++i];
        if (!strcmp(a, "--L")) {
            if (parse_size(v, &c.L)) return 2;
        } else if (!strcmp(a, "--T")) {
            if (parse_double(v, &c.T)) return 2;
        } else if (!strcmp(a, "--J")) {
            if (parse_double(v, &c.J)) return 2;
        } else if (!strcmp(a, "--H")) {
            if (parse_double(v, &c.H)) return 2;
        } else if (!strcmp(a, "--runs")) {
            if (parse_u64(v, &c.runs)) return 2;
        } else if (!strcmp(a, "--seed")) {
            if (parse_u64(v, &c.seed)) return 2;
        } else if (!strcmp(a, "--max-attempts")) {
            if (parse_u64(v, &c.max_attempts)) return 2;
        } else if (!strcmp(a, "--dynamics")) {
            if (dynamics_parse(v, &c.dynamics)) return 2;
        } else if (!strcmp(a, "--output")) {
            c.output = v;
        } else if (!strcmp(a, "--trace-prefix")) {
            c.trace_prefix = v;
        } else if (!strcmp(a, "--trace-run")) {
            if (parse_u64(v, &c.trace_run)) return 2;
        } else if (!strcmp(a, "--trace-every")) {
            if (parse_u64(v, &c.trace_every)) return 2;
        } else {
            fprintf(stderr, "Unknown argument: %s\n", a);
            return 2;
        }
    }

    if (c.trace_prefix && (!c.trace_prefix[0] || c.runs == 0u ||
                           c.trace_run >= c.runs || c.trace_every == 0u)) {
        fprintf(stderr, "Invalid trace configuration (run/every/prefix).\n");
        return 2;
    }
    FILE *f = fopen(c.output, "w");
    if (!f) {
        perror(c.output);
        return 1;
    }
    fprintf(f,
        "run,L,N,T,J,H,dynamics,algorithm,seed,stream,"
        "attempts,time_attempts,time_mcss,accepted,events,acceptance_rate,"
        "final_M,final_E,reached_M0,cpu_seconds\n");

    StandardConfig cfg = {c.L, c.T, c.J, c.H, c.dynamics, c.max_attempts};
    const uint64_t N = (uint64_t)c.L * (uint64_t)c.L;
    for (uint64_t run = 0; run < c.runs; ++run) {
        Rng rng;
        rng_seed(&rng, c.seed, run + 1u);
        StandardResult r;
        TraceWriter writer;
        TraceWriter *trace = NULL;
        if (c.trace_prefix && run == c.trace_run) {
            TraceMetadata meta = {"standard", dynamics_name(c.dynamics),
                                  c.T, c.J, c.H, c.seed, run + 1u, run};
            if (trace_open(&writer, c.trace_prefix, meta, c.trace_every) != 0) {
                fprintf(stderr, "Cannot create exclusive trace files; change --trace-prefix.\n");
                fclose(f);
                return 1;
            }
            trace = &writer;
        }
        const clock_t t0 = clock();
        const int rc = standard_run_traced(&cfg, &rng, &r, trace);
        const clock_t t1 = clock();
        const int trace_rc = trace ? trace_close(trace) : 0;
        if (trace_rc != 0) {
            fprintf(stderr, "Trace I/O close failed.\n");
            fclose(f);
            return 1;
        }
        if (rc != 0) {
            fprintf(stderr, "standard_run failed: %d\n", rc);
            fclose(f);
            return 1;
        }
        const double cpu = (double)(t1 - t0) / (double)CLOCKS_PER_SEC;
        fprintf(f,
            "%" PRIu64 ",%zu,%" PRIu64 ",%.17g,%.17g,%.17g,%s,standard,"
            "%" PRIu64 ",%" PRIu64 ","
            "%" PRIu64 ",%" PRIu64 ",%.17g,"
            "%" PRIu64 ",%" PRIu64 ",%.17g,"
            "%" PRId64 ",%.17g,%d,%.9g\n",
            run, c.L, N, c.T, c.J, c.H, dynamics_name(c.dynamics),
            c.seed, run + 1u,
            r.attempts, r.attempts, r.time_mcss,
            r.accepted, r.accepted, r.acceptance_rate,
            r.final_M, r.final_E, r.reached_M0, cpu);
    }

    fclose(f);
    return 0;
}
