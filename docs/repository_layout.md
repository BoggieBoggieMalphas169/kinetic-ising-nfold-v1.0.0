# Repository layout

```text
.
├── simulator/                 Prompt-6 validated C simulator and raw validation data
│   ├── src/
│   ├── include/
│   ├── tests/
│   ├── scripts/
│   ├── results/
│   ├── CMakeLists.txt
│   └── Makefile
├── scripts/                   Prompt-8 analysis/release tooling
│   ├── analysis/
│   ├── plotting/
│   └── tables/
├── results/
│   ├── legacy/prompt6/        immutable compatibility summaries
│   ├── processed/
│   ├── metadata/
│   ├── snapshots/
│   └── final_tables/
├── figures/
│   ├── final/
│   └── supplementary/
├── docs/
├── tests/                     Python analysis/release tests
├── release/
├── CMakeLists.txt             top-level simulator build wrapper
├── Makefile                   top-level simulator build wrapper
├── requirements.txt           combined Python environment
├── README.md
├── LICENSE
└── CITATION.cff
```

The architecture keeps the validated simulation engine and the later statistical-analysis layer separate while packaging both in one versioned repository.
