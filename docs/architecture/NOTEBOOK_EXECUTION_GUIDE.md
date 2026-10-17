<!-- @codebase_provenance_JEO -->
# Notebook execution guide

The six existing notebooks remain in `notebooks/`. Each has one shared startup cell built by `scripts/notebook_bootstrap.py`. It finds a checkout using repository markers, sets the working directory to that root, installs the editable project with the notebook extra in the active Python environment, validates required files and imports, and reports the current Git branch and commit when available.

## Local Jupyter

Open a notebook from a repository checkout and run its first code cell. If the Jupyter kernel starts outside the checkout, set `MAGIC_LOTTO_ROOT` to the checkout directory before running setup. Local setup never clones a repository. Rerunning setup reuses the same checkout and does not switch, reset, clean, or overwrite it.

## Google Colab

Open the notebook from the desired repository revision and run the first code cell. If no checkout is found, setup clones the public repository's `main` branch into `/content/Magic_Lotto`. Set `MAGIC_LOTTO_REF` before setup to clone another branch. The notebook does not require a mounted Google Drive. It stops if the target directory exists but is not a valid repository, or if an existing checkout does not match the requested branch.

The setup cell uses the active kernel interpreter and invokes the installer as a subprocess argument list equivalent to:

```bash
python -m pip install -e ".[notebook]"
```

## Notebook inventory and boundaries

| Notebook | Inputs checked by startup | Execution status in this refactor |
|---|---|---|
| `lotto_statistical_analysis.ipynb` | Phase 1 through Phase 3 data and reports; legacy Phase 3 script | Static JSON, path, and import checks only; not executed |
| `lotto_phase4_feature_engineering.ipynb` | Phase 1 through Phase 3 inputs and saved Phase 4 artifacts | Static JSON, path, and import checks only; not executed |
| `lotto_phase5a_ml_validation.ipynb` | Saved Phase 5A validation outputs and split metadata | Static JSON, path, and import checks only; not executed |
| `lotto_phase5r_predictive_information.ipynb` | Saved Phase 5R evidence | Static JSON, path, and import checks only; not executed |
| `lotto_phase6b_model_semantic_review.ipynb` | Saved Phase 6B adjudications and Phase 5 summaries | Static JSON, path, and import checks only; not executed |
| `lotto_phase7_kmeans_descriptive.ipynb` | Cleaned Lotto 6/42 dataset and the Phase 7 package | Setup and train-only analysis validated separately; no validation or locked-test records read |

All six notebooks parse as valid Jupyter notebooks. Static checks verify that required paths are relative and exist, code cells parse, and no hard-coded Windows paths or `sys.path` injections remain. The Phase 4, Phase 5A, Phase 5R, Phase 6B, and statistical notebooks were not executed because they consume historical validation artifacts or may regenerate protected evidence. This is a deliberate execution boundary, not a claim that those notebook analyses were reproduced.

## Phase 7 train-only run

Install with:

```bash
python -m pip install -r requirements-phase7.txt
```

Run from the repository root:

```bash
magic-lotto-phase7 --null-replicates 100 --seed 162
```

The program reads the first 1,003 normalized records and uses only the established 902 training draws from `2016-08-30` through `2022-11-12`. It asserts zero validation and locked-test rows. Outputs are written to `reports/phase7_kmeans_642/` by default. The refactor validation run redirected outputs to a temporary directory outside the repository.

No actual hosted Google Colab session was available for this refactor. Local and mocked-Colab setup checks are not evidence of an actual Colab execution.
