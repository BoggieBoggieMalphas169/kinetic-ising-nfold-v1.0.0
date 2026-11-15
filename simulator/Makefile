CC ?= gcc
CFLAGS ?= -O3 -std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wconversion
CPPFLAGS ?= -Iinclude
LDLIBS ?= -lm

CORE = src/rng.c src/ising.c src/dynamics.c src/standard_mc.c src/nfold.c

.PHONY: all test clean sanitize

all: ising_standard ising_nfold test_physics test_nfold

ising_standard: $(CORE) src/main_standard.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ $(LDLIBS) -o $@

ising_nfold: $(CORE) src/main_nfold.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ $(LDLIBS) -o $@

test_physics: $(CORE) tests/test_physics.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ $(LDLIBS) -o $@

test_nfold: $(CORE) tests/test_nfold.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ $(LDLIBS) -o $@

test: all
	./test_physics
	./test_nfold
	./ising_standard --L 8 --T 1.5 --J 1 --H -3 --runs 32 --seed 1234 --dynamics glauber --output results/validation/smoke_standard.csv
	./ising_nfold --L 8 --T 1.5 --J 1 --H -3 --runs 32 --seed 1234 --dynamics glauber --output results/validation/smoke_nfold.csv
	python3 scripts/check_csv_invariants.py results/validation/smoke_standard.csv --require-complete
	python3 scripts/check_csv_invariants.py results/validation/smoke_nfold.csv --require-complete

sanitize:
	cmake -S . -B build-sanitize -DISING_ENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=Debug
	cmake --build build-sanitize
	ctest --test-dir build-sanitize --output-on-failure

clean:
	rm -rf build build-sanitize ising_standard ising_nfold test_physics test_nfold
