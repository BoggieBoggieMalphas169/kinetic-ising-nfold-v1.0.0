# Contributing

## Recommended workflow

1. Create a branch from `main`.
2. Keep raw simulation output immutable.
3. Add or update tests for every contract or analysis change.
4. Run `pytest -q`.
5. Run `python scripts/release_check.py --structural`.
6. Regenerate 8D artifacts only when their source analysis changes.
7. Create a new snapshot rather than editing a frozen snapshot in place.

## Data rules

- Never edit a raw CSV to make an analysis pass.
- Never concatenate run-level and comparison-level datasets.
- Preserve `time_mcss`, n-fold `events`, equivalent attempts, and CPU time as
  distinct quantities.
- A cross-campaign repeated physical point is provenance, not automatically a duplicate.
- Keep `INCONCLUSIVE` results visible; do not reclassify them to improve the headline result.

## Simulator integration

When the C simulator core is merged, preserve its history if possible and keep
its output schema compatible with `docs/integration_with_simulator.md`.
