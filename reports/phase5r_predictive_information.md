# Phase 5R Predictive Information and Conditional Combination Modeling

- Verdict: **PHASE5R_INCONCLUSIVE**
- Branch / HEAD: `main` / `7eeca79065d5f3f83ff476dbe377076376ff87e1`
- Seed: 162; information and change-point permutations: 10,000; whole-draw bootstrap resamples: 10,000
- Locked test targets: not parsed, scored, visualized, tuned against, or used; only Phase 4 boundary metadata was read.
- Phase 5A validation was already examined; all Phase 5R validation results below are development evidence, not pristine final confirmation.
- Keys.env: ignored and untracked by Git metadata; contents not read. JEV and TypeSafe were not invoked.
- Git stage, commit, push, and merge: not performed.

## Scope and data boundaries

The analysis reads only the Phase 4 train and validation prefixes. The feature and target CSV readers stop after those prefix rows. Training information diagnostics and conditional rates use training only; stationarity uses train plus validation; sequential combination forecasts use prior-history features at each validation draw. Validation is explicitly development evidence because Phase 5A already used it.

| Game | Train | Validation | Locked test metadata only |
|---|---:|---:|---|
| 3d_lotto | 2170 (2016-04-16–2022-10-03) | 723 (2022-10-04–2024-10-07) | 724 (2024-10-08–2026-10-07) |
| lotto_6_42 | 902 (2016-08-30–2022-11-12) | 300 (2022-11-15–2024-10-22) | 302 (2024-10-24–2026-10-06) |

## Fair-random models

- 3D: all 220 unordered multisets were enumerated with multiplicity coefficients; fair probabilities sum to 1.000000000000. Every validation forecast distribution was checked to sum to one.
- Lotto 6/42: the fair fixed-cardinality normalizer is 5,245,786.0, matching C(42,6); the weighted model uses the exact sixth elementary symmetric polynomial.
- Independent synthetic enumeration matched the 6/42 dynamic-programming normalizer and valid-set probabilities.

## Information-theoretic diagnostics

Whole train draw rows were permuted 10,000 times; candidate features were rebuilt using only preceding shuffled rows for every permutation. 3D digit multiplicity and membership were assessed separately. Benjamini–Hochberg q-values are corrected within each game's full predefined diagnostic set.

| Game | Diagnostic family | Target measure | MI (nats / candidate) | Empirical p | BH q |
|---|---|---|---:|---:|---:|
| 3d_lotto | previous_10_frequency | multiplicity_count | 0.00286 | 0.07269 | 0.54331 |
| 3d_lotto | previous_10_frequency | membership | 0.00129 | 0.02190 | 0.35036 |
| 3d_lotto | previous_30_frequency | multiplicity_count | 0.00243 | 0.82092 | 0.82092 |
| 3d_lotto | previous_30_frequency | membership | 0.00082 | 0.76062 | 0.81197 |
| 3d_lotto | previous_100_frequency | multiplicity_count | 0.00287 | 0.34097 | 0.60616 |
| 3d_lotto | previous_100_frequency | membership | 0.00122 | 0.13939 | 0.54331 |
| 3d_lotto | expanding_historical_frequency | multiplicity_count | 0.00283 | 0.23728 | 0.60616 |
| 3d_lotto | expanding_historical_frequency | membership | 0.00106 | 0.60564 | 0.77765 |
| 3d_lotto | gap_since_seen | multiplicity_count | 0.00189 | 0.76122 | 0.81197 |
| 3d_lotto | gap_since_seen | membership | 0.00074 | 0.44686 | 0.64997 |
| 3d_lotto | previous_draw_appearance | multiplicity_count | 0.00065 | 0.63184 | 0.77765 |
| 3d_lotto | previous_draw_appearance | membership | 0.00028 | 0.29747 | 0.60616 |
| 3d_lotto | previous_100_frequency_deviation | multiplicity_count | 0.00287 | 0.34097 | 0.60616 |
| 3d_lotto | previous_100_frequency_deviation | membership | 0.00122 | 0.13939 | 0.54331 |
| 3d_lotto | approved_draw_context | multiplicity_count | 0.00296 | 0.43006 | 0.64997 |
| 3d_lotto | approved_draw_context | membership | 0.00128 | 0.16978 | 0.54331 |
| lotto_6_42 | previous_10_frequency | membership | 0.00133 | 0.55094 | 0.73459 |
| lotto_6_42 | previous_30_frequency | membership | 0.00307 | 0.01510 | 0.06039 |
| lotto_6_42 | previous_100_frequency | membership | 0.00307 | 0.04810 | 0.09619 |
| lotto_6_42 | expanding_historical_frequency | membership | 0.00368 | 0.00370 | 0.02960 |
| lotto_6_42 | gap_since_seen | membership | 0.00251 | 0.50395 | 0.73459 |
| lotto_6_42 | previous_draw_appearance | membership | 0.00000 | 1.00000 | 1.00000 |
| lotto_6_42 | previous_100_frequency_deviation | membership | 0.00307 | 0.04810 | 0.09619 |
| lotto_6_42 | approved_draw_context | membership | 0.00256 | 0.67243 | 0.76849 |

These are training-period diagnostic associations, not evidence that a specific candidate is more likely in a future draw. A statistically small q-value alone does not establish useful full-combination prediction.

## Temporal dependence and stationarity

Temporal conditional rates, paired whole-draw bootstrap intervals, fair marginal references, and the corresponding information-permutation diagnostics are in `phase5r_temporal_dependence.csv`. The detailed stationarity file contains rolling entropy, marginal-deviation, draw-context, Jensen–Shannon, and bounded change-point rows.

### 3d_lotto
- Jensen–Shannon digit_marginal between thirds 1 and 2: 0.00037 bits.
- Jensen–Shannon digit_marginal between thirds 1 and 3: 0.00042 bits.
- Jensen–Shannon digit_marginal between thirds 2 and 3: 0.00048 bits.
- Jensen–Shannon pattern_distribution between thirds 1 and 2: 0.00002 bits.
- Jensen–Shannon pattern_distribution between thirds 1 and 3: 0.00030 bits.
- Jensen–Shannon pattern_distribution between thirds 2 and 3: 0.00036 bits.
- No bounded mean-shift screen passed within-family BH q < 0.05; this does not prove strict stationarity.
### lotto_6_42
- Jensen–Shannon number_marginal between thirds 1 and 2: 0.00527 bits.
- Jensen–Shannon odd_count_distribution between thirds 1 and 2: 0.00333 bits.
- Jensen–Shannon number_marginal between thirds 1 and 3: 0.00664 bits.
- Jensen–Shannon odd_count_distribution between thirds 1 and 3: 0.00992 bits.
- Jensen–Shannon number_marginal between thirds 2 and 3: 0.00551 bits.
- Jensen–Shannon odd_count_distribution between thirds 2 and 3: 0.01051 bits.
- No bounded mean-shift screen passed within-family BH q < 0.05; this does not prove strict stationarity.

## Bayesian shrinkage and complete-combination scores

3D forecasts use Dirichlet priors centered at 0.10 with total concentrations 10, 100, and 1,000. Lotto 6/42 uses Beta priors centered at 6/42; posterior marginal estimates become positive odds weights for the exact six-element product-weight model. Each estimate uses only Phase 4 prior-history counts for its target draw.

| Game | Model | Mean combination NLL | Mean log-score advantage vs fair | 95% bootstrap CI vs fair | CI vs raw expansion | Positive validation thirds vs fair | MC p | Calibration screen |
|---|---|---:|---:|---|---|---:|---:|---|
| 3d_lotto | fair_random | 5.31989 | 0.00000 | [0.00000, 0.00000] | [-0.00252, 0.00535] | 0/3 | n/a | True |
| 3d_lotto | raw_expanding_frequency | 5.32132 | -0.00143 | [-0.00535, 0.00252] | [0.00000, 0.00000] | 1/3 | 0.48555 | True |
| 3d_lotto | dirichlet_kappa_10 | 5.32132 | -0.00142 | [-0.00535, 0.00252] | [-0.00000, 0.00001] | 1/3 | 0.48555 | True |
| 3d_lotto | dirichlet_kappa_100 | 5.32128 | -0.00139 | [-0.00526, 0.00251] | [-0.00001, 0.00009] | 1/3 | 0.48485 | True |
| 3d_lotto | dirichlet_kappa_1000 | 5.32099 | -0.00109 | [-0.00457, 0.00241] | [-0.00012, 0.00078] | 1/3 | 0.48135 | True |
| lotto_6_42 | fair_random | 15.47294 | 0.00000 | [0.00000, 0.00000] | [0.00619, 0.04421] | 0/3 | n/a | False |
| lotto_6_42 | raw_expanding_frequency | 15.49795 | -0.02502 | [-0.04421, -0.00619] | [0.00000, 0.00000] | 0/3 | 0.86701 | True |
| lotto_6_42 | beta_kappa_10 | 15.49761 | -0.02468 | [-0.04369, -0.00601] | [0.00018, 0.00051] | 0/3 | 0.86691 | True |
| lotto_6_42 | beta_kappa_100 | 15.49487 | -0.02193 | [-0.03957, -0.00459] | [0.00156, 0.00463] | 0/3 | 0.86581 | False |
| lotto_6_42 | beta_kappa_1000 | 15.48270 | -0.00977 | [-0.02002, 0.00033] | [0.00643, 0.02417] | 0/3 | 0.86201 | True |

Monte Carlo comparisons use 10,000 complete fair-random validation histories per model and escalate only an initial empirical p-value below 0.01 to 100,000. Forecasts are held fixed to the observed leakage-safe history, so these p-values are conditional comparisons and remain development evidence. Bootstrap intervals resample complete validation draw rows.

The calibration screen uses 10 equal-width probability bins and 10,000 whole-draw bootstrap resamples. A screen pass means no nonempty bin's 95% interval for observed-minus-predicted marginal rate excluded zero; it is not a formal calibration guarantee. The ECE and bin details are in the evidence JSON.

## Decision and limitations

BH q < 0.05 plus paired 95% bootstrap intervals above zero versus fair and raw expansion, positive direction in all three validation thirds, conditional fair-null Monte Carlo p <= 0.05, and no detected marginal miscalibration under the whole-draw bootstrap screen

The Phase 5A validation history has already been examined, so Phase 5R cannot provide pristine confirmation. No model may be described as finally predictive from these results alone. No draw recommendation is produced. Physical dynamics, quantum prediction, and player-choice optimization remain unsupported because the required measurements are absent.

Safest next action: Stop model expansion and keep the locked test untouched. The current evidence does not justify freezing a Phase 5R candidate for the one-time test evaluation; use any future confirmation only in a separately authorized phase after an explicit model freeze.

## Validation and provenance

- `assert_based_3d_and_642_mathematical_self_checks`: PASS
- `phase3_phase4_phase5a_preflight_and_hashes`: PASS
- `train_validation_only_prefix_parsing`: PASS
- `target_structure_and_feature_key_alignment`: PASS
- `phase4_split_boundaries_preserved`: PASS
- `3d_all_220_probabilities_normalized_for_every_validation_forecast`: PASS
- `642_exact_elementary_symmetric_normalizer_and_valid_six_set_support`: PASS
- `temporal_features_use_only_information_before_target`: PASS by Phase 4 evidence and the Phase 5R recomputation audit
- `information_and_change_point_permutations`: PASS
- `bootstrap_and_monte_carlo_counts`: PASS
- `locked_test_rows_parsed_or_scored`: NO
- `jev_typesafe_or_keys_env_contents_accessed`: NO
- `clean_kernel_notebook_execution`: PASS
- `nbformat_validation`: PASS
- `git_diff_check`: PASS
- `generated_text_whitespace_check`: PASS
- `prior_phase_artifact_integrity`: PASS
