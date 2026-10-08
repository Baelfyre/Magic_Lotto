# Phase 3: Monte Carlo Random Baseline

**Verdict: `PHASE3_PASS_RANDOM_COMPATIBLE`**

## Scope and method

This phase compares each observed diagnostic with fair synthetic histories of the same length. It does not predict lottery outcomes, recommend numbers, train a model, or call JEV/TypeSafe.

- Random seed: `162`; generator: `numpy.random.default_rng / PCG64`.
- Initial histories: `10,000` per game.
- Confirmation threshold: empirical `p < 0.01`; confirmation size: `100,000` histories for the flagged diagnostic only.
- Empirical p-values use the plus-one correction. Upper-tail tests count simulated statistics greater than or equal to the observation. Two-sided tests count simulated absolute deviations from the fair-process reference at least as large as the observed deviation.
- 3D draws use three independent uniform digits. Matching uses unordered multisets, preserving repeats; published order remains in the source data.
- Lotto 6/42 draws use a uniform sample of six distinct values from 1 through 42. Matching treats each draw as an unordered set.
- The 6/42 consecutive-overlap distribution test combines counts into 0, 1, 2, and 3+ to keep expected category counts usable; the report and JSON retain the full 0 through 6 histogram.
- NumPy `SeedSequence` substreams separate the two games and each possible confirmation diagnostic.

## Inputs

| Dataset | Resolved path | Rows | SHA-256 |
|---|---|---:|---|
| 3d_analysis_ready | `D:\Dev\Repositories\magic_Lotto\swertres_9pm_analysis_ready.csv` | 3,718 | `bed32547054a819e108f18d53af73db1f74db693202db066c64572846860959b` |
| 3d_phase2 | `D:\Dev\Repositories\magic_Lotto\swertres_9pm_phase2_analysis.csv` | 3,718 | `3b207b356349c0bf4e1677979c1077bea434071508e3f835e4fc75e9997d7d72` |
| 3d_digit_frequency | `D:\Dev\Repositories\magic_Lotto\swertres_9pm_digit_frequency.csv` | 10 | `4ad90a87cbaaca99a08001904b7bbef18e1561ed4b9c5a138f0253729b359681` |
| 6_42_cleaned | `D:\Dev\Repositories\magic_Lotto\lotto_6_42_cleaned_normalized.csv` | 1,605 | `980386a399077564d25de3a3a19aa3611969899895b9e3c06d7e9406599053a0` |
| 6_42_phase2 | `D:\Dev\Repositories\magic_Lotto\lotto_6_42_phase2_analysis.csv` | 1,605 | `a7ff6ac667ab9a4dd83c821ca6a7ad94b2866ab15299f5f0ad7e47818ac32958` |
| 6_42_number_frequency | `D:\Dev\Repositories\magic_Lotto\lotto_6_42_number_frequency.csv` | 42 | `1284586aaccc86f43da2e9676f425842dbf171dde36d8d8da2b4027789252456` |
| phase2_report | `D:\Dev\Repositories\magic_Lotto\phase2_randomness_diagnostics.md` | n/a | `c6318f74cc5685108f4bb278d6293b84771e0c29af7250888a789aec365cbce7` |

## 3D Lotto 9PM

History length: `3,718` draws, `2016-01-02` through `2026-10-07`.

| Diagnostic | Observed statistic | Fair reference | Initial p (10,000) | Confirmation p (100,000) | Final interpretation |
|---|---:|---|---:|---:|---|
| Pooled digit-frequency chi-square | 9.0536131 | Equal expected frequency for digits 0 through 9. | 0.43115688 | not triggered | consistent_with_fair_random_baseline |
| Maximum absolute digit-share deviation | 0.0058633674 | Maximum absolute share difference from 10%. | 0.32336766 | not triggered | consistent_with_fair_random_baseline |
| Repetition-pattern chi-square | 1.6441735 | Fair probabilities: all distinct 72%, one pair 27%, triple 1%. | 0.44485551 | not triggered | consistent_with_fair_random_baseline |
| Digit-sum mean | 13.357181 | 13.5 | 0.082291771 | not triggered | consistent_with_fair_random_baseline |
| Digit-sum sample variance | 24.575643 | 24.75 | 0.73482652 | not triggered | consistent_with_fair_random_baseline |
| Lag-1 digit-sum correlation | -0.003314066 | 0 | 0.83861614 | not triggered | consistent_with_fair_random_baseline |
| Mean consecutive unordered multiset overlap | 0.74495561 | 0.74226 | 0.81281872 | not triggered | consistent_with_fair_random_baseline |
| Consecutive multiset-overlap distribution chi-square | 0.62461537 | Exact fair-process multiset-overlap probabilities; categories 0, 1, and 2+ shared digits. | 0.73612639 | not triggered | consistent_with_fair_random_baseline |

Observed pooled digit counts (expected count is 1,115.4 per digit): 0: 1154, 1: 1147, 2: 1123, 3: 1095, 4: 1122, 5: 1121, 6: 1091, 7: 1157, 8: 1050, 9: 1094.

Observed repetition-pattern counts: all_distinct: 2644, one_pair: 1033, triple: 41.

Fair-model expected repetition-pattern counts (all distinct, one pair, triple): 2676.96, 1003.86, 37.18.

Observed consecutive multiset-overlap counts for 0, 1, 2, and 3 shared digits: 1468, 1755, 468, 26.
Fair-model expected consecutive multiset-overlap counts for 0 through 3 shared digits: 1458.89, 1776.35, 462.65, 19.11.

## Lotto 6/42

History length: `1,605` draws, `2016-01-02` through `2026-10-06`.

| Diagnostic | Observed statistic | Fair reference | Initial p (10,000) | Confirmation p (100,000) | Final interpretation |
|---|---:|---|---:|---:|---|
| Marginal number-frequency chi-square | 24.120872 | Equal expected appearance counts; calibration uses without-replacement histories. | 0.9480052 | not triggered | consistent_with_fair_random_baseline |
| Maximum absolute number-count deviation | 23.714286 | Maximum absolute count difference from six appearances per draw distributed across 42 numbers. | 0.98280172 | not triggered | consistent_with_fair_random_baseline |
| Mean consecutive-draw set overlap | 0.86471322 | 0.85714286 | 0.70932907 | not triggered | consistent_with_fair_random_baseline |
| Consecutive set-overlap distribution chi-square | 4.0244406 | Hypergeometric probabilities; test categories 0, 1, 2, and 3+ shared numbers. | 0.26047395 | not triggered | consistent_with_fair_random_baseline |
| Mean odd-number count per draw | 3.0361371 | 3 | 0.21087891 | not triggered | consistent_with_fair_random_baseline |
| Odd-count distribution chi-square | 6.4715339 | Hypergeometric probabilities for selecting from 21 odd and 21 even values. | 0.35386461 | not triggered | consistent_with_fair_random_baseline |
| Draw-sum mean | 128.57632 | 129 | 0.54534547 | not triggered | consistent_with_fair_random_baseline |
| Draw-sum sample variance | 771.84782 | 774 | 0.93650635 | not triggered | consistent_with_fair_random_baseline |

Observed consecutive set-overlap counts for 0 through 6 shared numbers: 611, 654, 290, 43, 6, 0, 0.

Fair-model expected counts for those overlap categories: 595.57, 691.64, 270.17, 43.66, 2.89, 0.07, 0.00.

Observed odd-number counts per draw for 0 through 6 odd values: 14, 139, 363, 526, 408, 132, 23.
Fair-model expected odd-number counts per draw for 0 through 6 odd values: 16.60, 130.75, 384.55, 541.21, 384.55, 130.75, 16.60.

The observed total of `1387` repeated number appearances across adjacent draws is the sum of the overlap counts. Its rate is `0.864713` per transition; it shares the overlap-mean p-value because it is the same statistic scaled by the number of transitions.

## Interpretation and limitations

- `p >= 0.05` is consistent with variation commonly produced by this fair random baseline; it does not prove that the historical process was random.
- `0.01 <= p < 0.05` is weak evidence and is flagged for investigation only.
- `p < 0.01` triggers the specified 100,000-history confirmation for that diagnostic. A confirmed anomaly remains a statistical observation, not evidence that a number is more likely next.
- No multiple-comparison correction was added because this phase follows the specified per-diagnostic screening rule. Interpret a collection of p-values cautiously.
- The simulations assume independent fair draws as specified. They do not establish causality, predictive usefulness, or the future behavior of the lottery.

## Validation and Phase 4 readiness

- Canonical input structure and Phase 2 feature consistency: **PASS**.
- Simulated digit and number domains, draw lengths, 6/42 uniqueness, seeded p-value bounds, and required simulation counts: **PASS**.
- `Keys.env` was verified ignored and untracked without reading its contents. No JEV or TypeSafe service was called.
- Python import validation left this untracked bytecode cache in place: `__pycache__/monte_carlo_baseline.cpython-312.pyc`
- Reproducibility was checked by rerunning the complete script with the recorded seed and comparing the generated artifact hashes.
- Phase 3 is ready for human review and Phase 4 chronological-backtest planning. This result does not authorize Phase 4 execution or support a prediction claim.

The compact simulated-distribution summaries are in `phase3_simulation_distributions.csv`; machine-readable statistics and p-value counts are in `phase3_monte_carlo_results.json`.
