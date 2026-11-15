# Reproducibility

This integrated release preserves both the simulator that generated the Prompt-6 evidence and the frozen Prompt-8 analysis built from that evidence.

## Level 1 — simulator reproduction

Build and test the C engine from the repository root:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

The validated Standard and n-fold executables are generated from `simulator/src/` and linked against the shared model/dynamics code in the same subtree.

A quick new-simulation check can then be run with:

```bash
python simulator/scripts/run_validation.py   --standard-exe build/simulator/ising_standard   --nfold-exe build/simulator/ising_nfold   --quick
```

On multi-config Windows generators, use the executables under `build/simulator/Release/`.

The original production ensembles used in Prompt 6 are preserved under `simulator/results/`, including the validation, lattice-size scalability and temperature-sweep datasets.

## Level 2 — analysis reproduction

Create the Python environment and execute the test suite:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pytest -q
```

The Prompt-8 compatibility copies of the historical summary tables are under:

```text
results/legacy/prompt6/
```

The analysis chain can be rebuilt from those summaries with:

```bash
python -m scripts.analysis.build_compatibility
python -m scripts.analysis.build_catalog
python -m scripts.analysis.build_quality_snapshot
```

The published scientific analyses are tied to the frozen snapshot:

```text
snap_0cc46433731097c4
```

Regenerate publication figures and tables with:

```bash
python -m scripts.reproduce_8D
```

## Relationship between original Prompt-6 summaries and Prompt-8 copies

The three original summary tables are located at:

```text
simulator/results/production_report_L32/validation_summary.csv
simulator/results/scalability_L/scalability_summary.csv
simulator/results/temperature_sweep/temperature_sweep_summary.csv
```

Prompt 8 imported semantically identical copies into `results/legacy/prompt6/`; those compatibility files contain one additional historical `index` column. Automated integration tests compare every shared field numerically/textually so that drift between the source summaries and compatibility copies is detected.

## Snapshot integrity

Verify the scientific snapshot with:

```bash
python -m scripts.analysis.build_quality_snapshot --verify results/snapshots/snap_0cc46433731097c4
```

The snapshot is intentionally immutable. A future scientific rerun should create a new snapshot rather than editing the published one.

## Release integrity

The repository release has an independent SHA-256 manifest:

```bash
python scripts/release_check.py --verify-frozen
```

This verifies repository files; it is distinct from snapshot verification. Both checks should pass before tagging a release.

## Deterministic release bundle

After freezing the manifest:

```bash
python scripts/freeze_release_manifest.py
python scripts/build_release_bundle.py
```

The release builder uses stable file ordering and fixed ZIP timestamps, so identical input files generate an identical archive hash.
