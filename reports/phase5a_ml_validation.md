# Phase 5A ML Baseline Training and Chronological Validation

- Verdict: PHASE5A_INCONCLUSIVE
- Branch / HEAD: main / 7eeca79065d5f3f83ff476dbe377076376ff87e1
- Random seed: 162
- Git stage, commit, push, and merge: not performed
- Keys.env: ignored and untracked; contents not read
- JEV / TypeSafe: not invoked

## Scope and split

Only Phase 4 training rows were used for fitting and expanding-window tuning. Evaluation used the predefined validation rows. The locked test target values were not parsed, scored, charted, or used for selection.

| Game | Train | Validation | Locked test metadata |
|---|---:|---:|---|
| 3d_lotto | 2170 (2016-04-16 to 2022-10-03) | 723 (2022-10-04 to 2024-10-07) | 724 rows (2024-10-08 to 2026-10-07); metadata only |
| lotto_6_42 | 902 (2016-08-30 to 2022-11-12) | 300 (2022-11-15 to 2024-10-22) | 302 rows (2024-10-24 to 2026-10-06); metadata only |

## Candidate configurations

- 3D multinomial logistic regression: C grid [0.1, 1.0, 10.0]; selected C by expanding-window mean unordered-multiset NLL.
- Lotto 6/42 one-versus-rest logistic regression: C grid [0.1, 1.0, 10.0]; selected C by expanding-window mean hits@6.
- Lotto 6/42 random forest: {"bootstrap": true, "estimator": "RandomForestClassifier multioutput", "max_depth": 8, "max_features": "sqrt", "min_samples_leaf": 5, "n_estimators": 100, "n_jobs": 1, "random_state": 162, "tuning": false}; fixed comparator, no search.

## Chronological training-fold results

The full grid and per-fold baseline scores are in phase5a_metrics.json. Selected all-feature results:

| Game | Model | Fold | Train dates | Fold dates | Primary | Uniform/random | Historical |
|---|---|---:|---|---|---:|---:|---:|
| 3d_lotto | multinomial_logistic_regression | 1 | 2016-04-16 to 2017-10-17 | 2017-10-18 to 2019-04-26 | 2.84736 | 1.77155 | 1.77361 |
| 3d_lotto | multinomial_logistic_regression | 2 | 2016-04-16 to 2019-04-26 | 2019-04-27 to 2021-03-30 | 2.27170 | 1.77905 | 1.77996 |
| 3d_lotto | multinomial_logistic_regression | 3 | 2016-04-16 to 2021-03-30 | 2021-03-31 to 2022-10-03 | 1.97587 | 1.77709 | 1.77805 |
| lotto_6_42 | regularized_one_vs_rest_logistic_regression | 1 | 2016-08-30 to 2018-02-13 | 2018-02-15 to 2019-08-06 | 0.88444 | 0.85714 | 0.83556 |
| lotto_6_42 | regularized_one_vs_rest_logistic_regression | 2 | 2016-08-30 to 2019-08-06 | 2019-08-08 to 2021-05-27 | 0.86222 | 0.85714 | 0.81333 |
| lotto_6_42 | regularized_one_vs_rest_logistic_regression | 3 | 2016-08-30 to 2021-05-27 | 2021-05-29 to 2022-11-12 | 0.92000 | 0.85714 | 0.87111 |
| lotto_6_42 | random_forest_multioutput_comparator | 1 | 2016-08-30 to 2018-02-13 | 2018-02-15 to 2019-08-06 | 0.83111 | 0.85714 | 0.83556 |
| lotto_6_42 | random_forest_multioutput_comparator | 2 | 2016-08-30 to 2019-08-06 | 2019-08-08 to 2021-05-27 | 0.85333 | 0.85714 | 0.81333 |
| lotto_6_42 | random_forest_multioutput_comparator | 3 | 2016-08-30 to 2021-05-27 | 2021-05-29 to 2022-11-12 | 0.92444 | 0.85714 | 0.87111 |

## Validation metrics

### 3D Lotto

| Method | Mean unordered NLL / digit | Mean multiset overlap | Digit Brier | ECE |
|---|---:|---:|---:|---:|
| uniform_random | 1.773298 | 0.74260 | 0.900000 | 0.00000 |
| expanding_historical_frequency | 1.773773 | 0.84509 | 0.900094 | 0.00212 |
| multinomial_logistic_regression/frequency_and_deviation | 1.832436 | 0.83817 | 0.913292 | 0.02654 |
| multinomial_logistic_regression/recency_and_gap | 1.788949 | 0.75657 | 0.903158 | 0.01387 |
| multinomial_logistic_regression/draw_context | 1.790310 | 0.80498 | 0.903376 | 0.01367 |
| multinomial_logistic_regression/all_features | 1.899246 | 0.79945 | 0.929506 | 0.03970 |

The unordered likelihood is computed as minus one third of log[(3! / product(count[d]!)) * product(p[d]^count[d])]. Hamilton allocation assigns three integer predicted counts using descending fractional remainders and lower-digit tie-breaks.

### Lotto 6/42

| Method | Mean hits@6 | Recall@6 | Precision@6 | Brier | Marginal log loss | Jaccard | ECE |
|---|---:|---:|---:|---:|---:|---:|---:|
| regularized_one_vs_rest_logistic_regression/frequency_and_deviation | 0.89000 | 0.14833 | 0.14833 | 0.346813 | 2.230398 | 0.08530 | 0.35414 |
| random_forest_multioutput_comparator/frequency_and_deviation | 0.87000 | 0.14500 | 0.14500 | 0.123149 | 0.412921 | 0.08415 | 0.00401 |
| regularized_one_vs_rest_logistic_regression/recency_and_gap | 0.86333 | 0.14389 | 0.14389 | 0.139074 | 0.465265 | 0.08371 | 0.08559 |
| random_forest_multioutput_comparator/recency_and_gap | 0.86000 | 0.14333 | 0.14333 | 0.122933 | 0.412067 | 0.08274 | 0.00177 |
| regularized_one_vs_rest_logistic_regression/draw_context | 0.91000 | 0.15167 | 0.15167 | 0.126003 | 0.421401 | 0.08839 | 0.03322 |
| random_forest_multioutput_comparator/draw_context | 0.87000 | 0.14500 | 0.14500 | 0.123267 | 0.413486 | 0.08428 | 0.00726 |
| regularized_one_vs_rest_logistic_regression/all_features | 0.92333 | 0.15389 | 0.15389 | 0.371240 | 2.604837 | 0.08935 | 0.37866 |
| random_forest_multioutput_comparator/all_features | 0.88333 | 0.14722 | 0.14722 | 0.123135 | 0.412987 | 0.08529 | 0.00365 |
| uniform_random | 0.85714 | 0.14286 | 0.14286 | 0.122449 | 0.410116 | n/a | 0.00000 |
| expanding_historical_frequency | 0.90000 | 0.15000 | 0.15000 | 0.122591 | 0.410704 | 0.08733 | 0.00000 |
| recent_30_frequency | 0.79333 | 0.13222 | 0.13222 | 0.126724 | 0.473228 | 0.07709 | 0.04905 |

The fair-random primary expectation is 6 * 6 / 42 = 0.8571428571 hits per draw. Random-set empirical comparisons use hypergeometric hit simulations.

## Monte Carlo comparisons

| Game / candidate | Initial simulations | Final simulations | Observed | Random mean | 95% random interval | Initial p | Final empirical p | Confirmation |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 3d_lotto / multinomial_logistic_regression/all_features | 10000 | 10000 | 0.799447 | 0.742596 | [0.692946, 0.792531] | 0.0135986 | 0.0135986 | not triggered |
| lotto_6_42 / regularized_one_vs_rest_logistic_regression | 10000 | 10000 | 0.923333 | 0.856678 | [0.766667, 0.950000] | 0.0826917 | 0.0826917 | not triggered |
| lotto_6_42 / random_forest_multioutput_comparator | 10000 | 10000 | 0.883333 | 0.856678 | [0.766667, 0.950000] | 0.293171 | 0.293171 | not triggered |

P-values are one-sided upper-tail empirical values using (1 + exceedances) / (1 + simulations). The two predefined 6/42 model comparisons use a Bonferroni-adjusted p-value in the advancement gate. A raw initial p below 0.01 triggers a separate 100000-simulation confirmation stream.

## Bootstrap uncertainty

Whole validation draws were resampled 10,000 times for percentile 95% intervals.

| Game / model | Primary metric | 95% CI | Difference vs fair random | Difference vs historical baseline(s) |
|---|---|---|---|---|
| 3d_lotto / multinomial_logistic_regression/all_features | mean_multinomial_negative_log_likelihood_per_digit | [1.876654, 1.922089] | [0.104905, 0.147036] | expanding_historical_frequency: [0.104269, 0.146715] |
| 3d_lotto / multinomial_logistic_regression/frequency_and_deviation | mean_multinomial_negative_log_likelihood_per_digit | [1.816029, 1.848434] | n/a | n/a |
| 3d_lotto / multinomial_logistic_regression/recency_and_gap | mean_multinomial_negative_log_likelihood_per_digit | [1.778624, 1.799547] | n/a | n/a |
| 3d_lotto / multinomial_logistic_regression/draw_context | mean_multinomial_negative_log_likelihood_per_digit | [1.778051, 1.802980] | n/a | n/a |
| lotto_6_42 / regularized_one_vs_rest_logistic_regression | mean_hits_at_6 | [0.833333, 1.013333] | [-0.023810, 0.156190] | expanding_historical_frequency: [-0.093333, 0.146667]; recent_30_frequency: [0.000000, 0.263333] |
| lotto_6_42 / random_forest_multioutput_comparator | mean_hits_at_6 | [0.793333, 0.973333] | [-0.063810, 0.116190] | expanding_historical_frequency: [-0.113333, 0.076750]; recent_30_frequency: [-0.036667, 0.216667] |
| lotto_6_42 / regularized_one_vs_rest_logistic_regression/frequency_and_deviation | mean_hits_at_6 | [0.806667, 0.976667] | n/a | n/a |
| lotto_6_42 / random_forest_multioutput_comparator/frequency_and_deviation | mean_hits_at_6 | [0.780000, 0.960000] | n/a | n/a |
| lotto_6_42 / regularized_one_vs_rest_logistic_regression/recency_and_gap | mean_hits_at_6 | [0.770000, 0.956667] | n/a | n/a |
| lotto_6_42 / random_forest_multioutput_comparator/recency_and_gap | mean_hits_at_6 | [0.773333, 0.946667] | n/a | n/a |
| lotto_6_42 / regularized_one_vs_rest_logistic_regression/draw_context | mean_hits_at_6 | [0.820000, 1.003333] | n/a | n/a |
| lotto_6_42 / random_forest_multioutput_comparator/draw_context | mean_hits_at_6 | [0.776667, 0.960000] | n/a | n/a |
| lotto_6_42 / regularized_one_vs_rest_logistic_regression/all_features | mean_hits_at_6 | [0.833333, 1.013333] | n/a | n/a |
| lotto_6_42 / random_forest_multioutput_comparator/all_features | mean_hits_at_6 | [0.793333, 0.973333] | n/a | n/a |

## Feature-group ablation

| Game | Model | Feature group | Selected C | Primary validation metric |
|---|---|---|---:|---:|
| 3d_lotto | multinomial_logistic_regression | frequency_and_deviation | 0.1 | 1.832436 |
| 3d_lotto | multinomial_logistic_regression | recency_and_gap | 0.1 | 1.788949 |
| 3d_lotto | multinomial_logistic_regression | draw_context | 0.1 | 1.790310 |
| 3d_lotto | multinomial_logistic_regression | all_features | 0.1 | 1.899246 |
| lotto_6_42 | regularized_one_vs_rest_logistic_regression | frequency_and_deviation | 1 | 0.890000 |
| lotto_6_42 | random_forest_multioutput_comparator | frequency_and_deviation | fixed | 0.870000 |
| lotto_6_42 | regularized_one_vs_rest_logistic_regression | recency_and_gap | 0.1 | 0.863333 |
| lotto_6_42 | random_forest_multioutput_comparator | recency_and_gap | fixed | 0.860000 |
| lotto_6_42 | regularized_one_vs_rest_logistic_regression | draw_context | 0.1 | 0.910000 |
| lotto_6_42 | random_forest_multioutput_comparator | draw_context | fixed | 0.870000 |
| lotto_6_42 | regularized_one_vs_rest_logistic_regression | all_features | 1 | 0.923333 |
| lotto_6_42 | random_forest_multioutput_comparator | all_features | fixed | 0.883333 |

## Calibration and consistency

- Calibration screening threshold: ECE <= 0.100; this is a diagnostic screen, not a proof of calibration.
- Fold consistency requirement: at least 2 of 3 chronological folds improve over each required baseline.
- Repeatability checks: {"all_probabilities_finite": true, "bit_generator": "PCG64", "initial_monte_carlo_reproducibility_checked": true, "random_seed": 162, "selected_validation_pipeline_refits": {"3d_lotto": {"maximum_absolute_probability_difference": 1.1102230246251565e-16, "same_seed_refit_matches": true}, "lotto_6_42": {"forest_maximum_absolute_probability_difference": 0.0, "forest_same_seed_refit_matches": true, "logistic_maximum_absolute_probability_difference": 0.0, "logistic_same_seed_refit_matches": true}}}
- Fit warnings: {"convergence": 0, "other": [{"category": "FutureWarning", "count": 1722, "message": "'penalty' was deprecated in version 1.8 and will be removed in 1.10. To avoid this warning, leave 'penalty' set to its default value and use 'l1_ratio' or 'C' instead. Use l1_ratio=0 instead of penalty='l2', l1_ratio=1 instead of penalty='l1', l1_ratio set to a float between 0 and 1 instead of penalty='elasticnet', and C=np.inf instead of penalty=None."}]}

## Advancement decision

Phase 5B candidate-ready: False.

| Candidate | Eligible | Reasons |
|---|---|---|
| 3d_lotto/multinomial_logistic_regression/all_features | False | primary_point_improvement_over_fair_random; primary_point_improvement_over_historical_baselines; bootstrap_interval_excludes_zero_vs_fair_random; bootstrap_interval_excludes_zero_vs_historical_baselines; consistent_across_chronological_folds |
| lotto_6_42/regularized_one_vs_rest_logistic_regression/all_features | False | bootstrap_interval_excludes_zero_vs_fair_random; bootstrap_interval_excludes_zero_vs_historical_baselines; monte_carlo_empirical_p_passes_gate; calibration_screen_passes |
| lotto_6_42/random_forest_multioutput_comparator/all_features | False | primary_point_improvement_over_historical_baselines; bootstrap_interval_excludes_zero_vs_fair_random; bootstrap_interval_excludes_zero_vs_historical_baselines; monte_carlo_empirical_p_passes_gate; consistent_across_chronological_folds |

## Test-contamination audit

- Result: PASS
- Test targets parsed: no.
- Test metrics calculated: no.
- Test-dependent selection or visualization: no.
- Phase 4 split boundaries changed: no.

## Validation

- Notebook: PASS
- nbformat: PASS
- Phase 4 artifacts unchanged: PASS
- Keys.env ignored/untracked: True/True; contents not read.

## Limitations

- Chronological training folds were used to tune C, so fold consistency is a diagnostic and not an independent holdout.
- Validation results are finite-sample historical evidence. The locked test partition remains unevaluated.

## Safest next action

Do not open the locked test. Review the validation uncertainty and candidate consistency before any separately authorized next phase.

## Output hashes

- models/phase5a_model_config.json: 5467ed08377e0ab727d8166f27e069cfc3ae9287f56cf10bc118703a077f142e
- notebooks/lotto_phase5a_ml_validation.ipynb: 6b92f0467f5e03a26495ae9d4a8e5cc370c8bfa1db44fc47a376938d69086c72
- reports/phase5a_metrics.json: de16b54d7e43404e34046f8d335febe36ce02d6ed00e6b761e2c6aa8a0183f75
- reports/phase5a_random_baseline_distributions.csv: 27ed1bfce5bb067405c2cbd94698c551debb61ffa0eee3cb39a678391020802b
- reports/phase5a_validation_predictions/3d_validation_predictions.csv: 19fd7a7556087b784c9b0f4c3431b4e981249268f913c905f2751d640e03eb21
- reports/phase5a_validation_predictions/642_validation_predictions.csv: 442bf9fa0f0cff54ce6a74937f7a62c0fff3b3fb73d8409b1ac8f315c5382317
- scripts/phase5a_ml_validation.py: 2c713a63ecc4d089e4b3712ebcf51792a0dd9330a5ed0e86d6c491d311f97fb7
