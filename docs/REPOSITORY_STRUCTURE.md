# Repository structure

This guide describes where the research files are kept today. Some earlier files remain in the top folder because the saved research records refer to their current paths.

## Main folder layout

```text
Magic_Lotto/
├── data/
│   └── features/
├── docs/
├── models/
├── notebooks/
├── reports/
│   └── phase5a_validation_predictions/
├── scripts/
├── __pycache__/
└── README.md
```

The README shows the main folders only. The `__pycache__/` folder is an existing Python-generated cache, not research material.

## What each folder contains

- `data/features/` contains tables prepared from earlier draws, target tables, a record of the date splits, and a guide to the prepared columns.
- `scripts/` contains the Phase 4 feature preparation, Phase 5A validation, Phase 5R analysis, and Phase 6A JEV scripts, plus the JEV client.
- `notebooks/` contains the statistical analysis, feature preparation, Phase 5A validation, and Phase 5R analysis notebooks.
- `models/` contains `phase5a_model_config.json`, the saved settings used in Phase 5A testing.
- `reports/` contains Phase 4 through Phase 6 results and checks. The Phase 5A validation prediction files are in `reports/phase5a_validation_predictions/`.
- `docs/` contains the final project documentation, including this guide.

## Important files in the top folder

### Original and cleaned data

- `6-42.csv` and `swertres9pm.md` are the original source files.
- `lotto_6_42_cleaned_normalized.csv` and `swertres_9pm_cleaned_normalized.csv` contain the cleaned draw records.
- `swertres_9pm_analysis_ready.csv` is the 3D Lotto file prepared for analysis.
- `lotto_6_42_number_frequency.csv`, `lotto_6_42_phase2_analysis.csv`, `swertres_9pm_digit_frequency.csv`, and `swertres_9pm_phase2_analysis.csv` are Phase 2 results.

### Research records

- `lotto_data_cleaning_report.md` records the data cleaning work.
- `phase2_randomness_diagnostics.md` records the Phase 2 checks.
- `monte_carlo_baseline.py` is the Phase 3 random baseline program.
- `phase3_monte_carlo_random_baseline.md`, `phase3_monte_carlo_results.json`, and `phase3_simulation_distributions.csv` record the Phase 3 method and results.

## Why earlier files remain in the top folder

Phase 3 records the paths and hashes of its input files and program. Phase 4 and Phase 5 scripts, notebooks, and validation records also refer to the existing data and program paths. Phase 6 records refer to earlier evidence by its current path and hash. Moving these files would require changing those records and could weaken the research history. No earlier files were moved or copied during this review.

## Current research status

The final recorded status is `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`. The Phase 6 evidence says the locked test remains sealed and has not been scored.
