# Phase 4 Feature Engineering and Experimental Design

- Verdict: PHASE4_PASS_READY_FOR_ML_BASELINE
- Branch and HEAD: main / 7eeca79065d5f3f83ff476dbe377076376ff87e1
- Phase 3 prerequisite: PHASE3_PASS_RANDOM_COMPATIBLE
- Canonical inputs are unchanged; SHA-256 values are recorded in phase4_validation.json.
- Leakage rule: every feature for target t uses only earlier draws.
- Early history: first 101 rows per game excluded to provide 100 prior draws and 100 completed transitions.
- Chronology: floor 60% train, floor 20% validation, remainder test; test partition locked.
- No model training, hyperparameter search, test-performance calculation, number recommendations, JEV, or TypeSafe.

## Dataset summary

| Game | Features | Targets | Input draws | Excluded | Eligible | Gap null cells |
|---|---:|---:|---:|---:|---:|---:|
| 3d_lotto | 107 | 10 | 3718 | 101 | 3617 | 0 |
| lotto_6_42 | 391 | 42 | 1605 | 101 | 1504 | 0 |

## Chronological partitions

### 3d_lotto

| Partition | Rows | Start | End |
|---|---:|---|---|
| train | 2170 | 2016-04-16 | 2022-10-03 |
| validation | 723 | 2022-10-04 | 2024-10-07 |
| test | 724 | 2024-10-08 | 2026-10-07 |

### lotto_6_42

| Partition | Rows | Start | End |
|---|---:|---|---|
| train | 902 | 2016-08-30 | 2022-11-12 |
| validation | 300 | 2022-11-15 | 2024-10-22 |
| test | 302 | 2024-10-24 | 2026-10-06 |

## Validation

- Target domains and row sums: PASS.
- Feature and target stable keys: PASS.
- Rolling, expanding, lag, gap, overlap, fair-deviation, permutation, and future-perturbation audits: PASS.
- Two in-memory builds produced identical hashes: PASS.
- Phase 4 notebook execution and nbformat: PASS.
- Machine-readable evidence: data/features/chronological_splits.json, data/features/feature_dictionary.json, reports/phase4_validation.json.

## Interpretation limits

These matrices are descriptive historical inputs for a later chronological backtest. Feature variation does not establish predictive value. Phase 4 did not train models, select features using test labels, calculate test performance, or recommend numbers.
