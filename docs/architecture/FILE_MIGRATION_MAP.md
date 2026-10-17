<!-- @codebase_provenance_JEO -->
# File migration map

The selected base is `b67e31572187001c89266839871c9e28456b90e8`. The machine-readable [migration manifest](../REPOSITORY_LAYOUT_MIGRATION.json) records byte lengths and SHA-256 values for each relocation.

## Before and after directory landmarks

Before this change, the historical inputs, normalized data, Phase 2 tables, narrative reports, Phase 3 results, and Monte Carlo program were at the repository root. The existing directories held later-stage artifacts and tools:

```text
Magic_Lotto/
├── *.csv and source/report files
├── monte_carlo_baseline.py
├── data/features/
├── docs/
├── models/
├── notebooks/
├── reports/
└── scripts/
```

They now have explicit locations, alongside the Phase 7 package:

```text
Magic_Lotto/
├── data/{raw,processed,analysis/phase2,features}/
├── docs/{architecture,research}/
├── models/
├── notebooks/
├── reports/
├── research/legacy/scripts/
├── scripts/
├── src/magic_lotto/{application,domain,infrastructure,interfaces,research}/
└── tests/
```
## Relocated files

| Original path | Current path | Handling |
|---|---|---|
| `6-42.csv` | `data/raw/6-42.csv` | Byte-identical move |
| `swertres9pm.md` | `data/raw/swertres9pm.md` | Byte-identical move |
| `lotto_6_42_cleaned_normalized.csv` | `data/processed/lotto_6_42_cleaned_normalized.csv` | Byte-identical move; row order preserved |
| `swertres_9pm_cleaned_normalized.csv` | `data/processed/swertres_9pm_cleaned_normalized.csv` | Byte-identical move; row order preserved |
| `swertres_9pm_analysis_ready.csv` | `data/processed/swertres_9pm_analysis_ready.csv` | Byte-identical move; row order preserved |
| `lotto_6_42_number_frequency.csv` | `data/analysis/phase2/lotto_6_42_number_frequency.csv` | Byte-identical move |
| `lotto_6_42_phase2_analysis.csv` | `data/analysis/phase2/lotto_6_42_phase2_analysis.csv` | Byte-identical move |
| `swertres_9pm_digit_frequency.csv` | `data/analysis/phase2/swertres_9pm_digit_frequency.csv` | Byte-identical move |
| `swertres_9pm_phase2_analysis.csv` | `data/analysis/phase2/swertres_9pm_phase2_analysis.csv` | Byte-identical move |
| `monte_carlo_baseline.py` | `research/legacy/scripts/monte_carlo_baseline.py` | Moved and updated for package-root and current artifact-path resolution; statistical calculations retained |
| `lotto_data_cleaning_report.md` | `docs/research/lotto_data_cleaning_report.md` | Byte-identical move |
| `phase2_randomness_diagnostics.md` | `docs/research/phase2_randomness_diagnostics.md` | Byte-identical move |
| `phase3_monte_carlo_random_baseline.md` | `docs/research/phase3_monte_carlo_random_baseline.md` | Byte-identical move |
| `phase3_monte_carlo_results.json` | `reports/phase3_monte_carlo_results.json` | Byte-identical move |
| `phase3_simulation_distributions.csv` | `reports/phase3_simulation_distributions.csv` | Byte-identical move |

All nine relocated data files retain the selected-base bytes and SHA-256 hashes. The three moved historical reports and two Phase 3 result artifacts also retain their selected-base bytes. The Phase 3 script is the one path-adapted relocation; its resulting working-tree hash is recorded in the manifest.

## Historical references that do not match the selected snapshot

The historical hash expectations in `scripts/phase5a_ml_validation.py` and the Phase 3 report describe earlier source contents. A read-only Git-history check confirmed those expected hashes at their original paths:

| Historical source | Revision containing the recorded source |
|---|---|
| Six Phase 1/Phase 2 data and report files named in the manifest | `7eeca79065d5f3f83ff476dbe377076376ff87e1` |
| Phase 3 Monte Carlo script and statistical notebook snapshots | `12007b11786118bbc1a368d725e0627f922f2b8a` |

Those six current files have different hashes from their older recorded references, but their current contents exactly match the selected base and were not changed by the relocation. The historical constants and reports were not rewritten. As a result, old Phase 4/5 snapshot checks that require those older file hashes are not evidence that the selected-base files reproduce the older run; those checks remain fail-closed and need a separate research-provenance decision before rerunning those phases.

The original `data/features/` artifacts, all Phase 4 and later result files, and model settings were not relocated. The tracked Python bytecode cache was removed from version control and notebook checkpoints are ignored.
