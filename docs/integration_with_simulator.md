# Simulator integration and provenance

The Prompt-6 simulator archive is now physically included in this release under `simulator/`.
No simulator source file was reconstructed from documentation: the files are copied from the user-provided `ising_prompt6_FINAL_complete.zip` snapshot.

## Included simulator components

- `simulator/src/`: Standard Monte Carlo and n-fold C implementation.
- `simulator/include/`: public headers.
- `simulator/tests/`: C unit tests for physics and n-fold bookkeeping.
- `simulator/scripts/`: end-to-end validation, benchmarking, scalability and temperature-sweep tools.
- `simulator/results/`: the original Prompt-6 raw ensembles, summaries, reports and figures.
- `simulator/CMakeLists.txt` and `simulator/Makefile`: original standalone build system.

The repository root also provides wrapper `CMakeLists.txt` and `Makefile` files so the full project can be built from the root without modifying the validated Prompt-6 subtree.

## Connection to Prompt 8

Prompt 8 deliberately works from immutable compatibility copies in `results/legacy/prompt6/`. Those files are semantically identical to the corresponding Prompt-6 summaries, with an additional index column introduced by the historical import step. The full original Prompt-6 records remain under `simulator/results/` for auditability.

The frozen Prompt-8 analysis snapshot remains `snap_0cc46433731097c4`. Integrating the simulator does not rewrite that snapshot; it adds the source and raw evidence that produced the historical summaries.
