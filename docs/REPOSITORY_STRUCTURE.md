# Repository structure

The repository keeps original inputs, processed datasets, historical evidence, notebooks, and reusable Python code in separate locations. Moves preserve the selected base revision's bytes unless the migration manifest explicitly records a path adaptation.

## Current layout

```text
Magic_Lotto/
├── data/
│   ├── analysis/phase2/        Existing Phase 2 tables
│   ├── features/               Protected Phase 4 features and targets
│   ├── processed/              Existing normalized datasets
│   └── raw/                    Existing source files
├── docs/
│   ├── architecture/           Architecture, migration, import, and notebook guides
│   └── research/               Historical Phase 1 through Phase 3 reports
├── models/                     Existing model configuration
├── notebooks/                  Six existing research notebooks
├── reports/                    Historical and Phase 4+ evidence
├── research/legacy/scripts/    Historical Phase 3 Monte Carlo program
├── scripts/                    Phase utilities and compatibility entry points
├── src/magic_lotto/            Layered Python package
└── tests/                      Regression and repository-layout checks
```

`data/derived/` is not created because no derived data is introduced by this refactor. Existing Phase 4 feature and target artifacts stay under `data/features/`.

## Python package responsibilities

- `domain/` contains draw validation and encoding without filesystem or UI concerns.
- `application/` contains the Phase 7 use case, service, and repository/artifact-writer ports.
- `infrastructure/dao/` reads the existing Lotto 6/42 CSV; `infrastructure/repositories/` implements the training repository; `infrastructure/serialization/` writes Phase 7 artifacts.
- `research/` contains the preserved Phase 7 numerical analysis.
- `interfaces/` provides the Phase 7 CLI and shared notebook bootstrap.
- `paths.py` resolves repository paths. The former `scripts/` imports remain thin compatibility entry points.

No `infrastructure/sources/` adapter is implemented or activated. Source collection belongs to the separate Phase 8 proposal and requires its own approval.

## Historical files and evidence

Original and normalized data now live under `data/raw/` and `data/processed/`. Existing Phase 2 tables are under `data/analysis/phase2/`. Historical cleaning, Phase 2, and Phase 3 narrative reports are under `docs/research/`; machine-readable Phase 3 results remain under `reports/`. The Phase 3 program is at `research/legacy/scripts/monte_carlo_baseline.py` and retains its analysis while resolving repository paths from the new location.

See the [file migration map](architecture/FILE_MIGRATION_MAP.md) and [migration manifest](REPOSITORY_LAYOUT_MIGRATION.json) for old-to-new paths, byte counts, and hash evidence. Historical hash expectations are checked against their recorded Git revisions and paths; the migration does not rewrite them to match the selected base snapshot.

## Research boundaries

The existing verdict remains `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`. This layout change does not add a prediction algorithm or change research conclusions. Phase 7 reads only the 902-draw training partition, and validation and locked-test partitions remain sealed. See [Phase 7 method and limits](PHASE7_KMEANS_DESCRIPTIVE.md) and the [repository architecture](architecture/REPOSITORY_ARCHITECTURE.md).