# Magic Lotto

Magic Lotto is an educational research repository for analyzing historical Philippine lottery draws. It contains earlier work on 3D Lotto 9PM and Lotto 6/42; the Phase 8 proposal itself is scoped to Lotto 6/42 only.

## Research status

The recorded research verdict remains `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`. Existing analyses did not establish reproducible predictive signal. This does not prove prediction is impossible; it records that the tested data and methods established no reliable advantage. The repository is not a lottery prediction service, and this structural refactor does not add predictive behavior or change that verdict. Validation and locked-test partitions remain sealed.

## Repository layout

```text
Magic_Lotto/
├── data/
│   ├── analysis/phase2/        Existing Phase 2 tables
│   ├── features/               Existing protected Phase 4 artifacts
│   ├── processed/              Existing normalized datasets
│   └── raw/                    Existing source files
├── docs/
│   ├── architecture/           Architecture and migration guides
│   └── research/               Historical Phase 1 through Phase 3 reports
├── models/                     Existing model configuration
├── notebooks/                  Six existing research notebooks
├── reports/                    Existing Phase 3 and later evidence
├── research/legacy/scripts/    Historical Phase 3 Monte Carlo source
├── scripts/                    Existing phase utilities and compatibility entrypoints
├── src/magic_lotto/            Layered package for the train-only Phase 7 workflow
└── tests/                      Regression and notebook/path checks
```

See [repository structure](docs/REPOSITORY_STRUCTURE.md), the [architecture](docs/architecture/REPOSITORY_ARCHITECTURE.md), and the [file migration map](docs/architecture/FILE_MIGRATION_MAP.md). Exact old and new byte counts and SHA-256 values are recorded in [the migration manifest](docs/REPOSITORY_LAYOUT_MIGRATION.json).

## Install and run Phase 7

Python 3.10 or newer is required. Install the local package and notebook dependencies with:

```bash
python -m pip install -e ".[notebook]"
```

Run the existing descriptive analysis from the repository root:

```bash
magic-lotto-phase7 --null-replicates 100 --seed 162
```

The compatibility command remains available:

```bash
python scripts/phase7_kmeans_642.py --null-replicates 100 --seed 162
```

Phase 7 reads only the first 1,003 normalized records and validates its 902-draw training boundary. Its default outputs are written under `reports/phase7_kmeans_642/`. The analysis is descriptive; it does not use validation or locked-test records or reverse the recorded research verdict.

## Notebooks

Each notebook's first code cell finds or validates the repository root, installs the editable package and notebook extra in the active kernel, checks required inputs and imports, and reports the checkout identity. For local Jupyter, open the notebook from this checkout or set `MAGIC_LOTTO_ROOT` to it. In Colab, setup clones `main` into `/content/Magic_Lotto` only when it cannot find a checkout; set `MAGIC_LOTTO_REF` to request another branch. Setup never switches, resets, cleans, or overwrites an existing checkout.

See the [notebook execution guide](docs/architecture/NOTEBOOK_EXECUTION_GUIDE.md) for the six-notebook inventory and execution boundaries. Actual hosted Colab execution has not been verified in this refactor. For the Phase 7 method and limitations, see [the research note](docs/PHASE7_KMEANS_DESCRIPTIVE.md) and [the notebook](notebooks/lotto_phase7_kmeans_descriptive.ipynb). The [Phase 6B review notebook](notebooks/lotto_phase6b_model_semantic_review.ipynb) records the prior model-readiness review.
