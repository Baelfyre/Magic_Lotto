# Phase 6B Model-Specific JEV Review

Status: PHASE6B_MODEL_SEMANTIC_ADJUDICATION_COMPLETE

Local evidence classification: NO_TESTED_MODEL_READY

JEV answered bounded Noul and Choice questions from quantitative development evidence. The final classification above was computed locally using the stated rules.

## Requests and answers

### 3D semantic-contract assessment

- Request ID: 3d_semantic
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- 3d_target_matches_goal: Noul 0.710000

- 3d_primary_metric_matches_goal: Noul 0.850000

- 3d_secondary_overlap_is_primary_evidence: Noul 0.130000

### 3D predictive evidence and shrinkage

- Request ID: 3d_predictive
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- 3d_logistic_beats_fair_probability_baseline: Noul 0.190000

- 3d_logistic_improvement_temporally_stable: Noul 0.300000

- 3d_logistic_failure_interpretation: selected SECONDARY_METRIC_ONLY

  | Choice | Probability |
  |---|---:|
  | NO_OBSERVED_IMPROVEMENT | 0.350000 |
  | INSUFFICIENT_EVIDENCE | 0.010000 |
  | MODEL_SEMANTICS_INVALID | 0.090000 |
  | PREDICTIVE_IMPROVEMENT | 0.120000 |
  | SECONDARY_METRIC_ONLY | 0.430000 |
  | Response confidence | 0.290000 (response-distribution information only) |

- 3d_shrinkage_beats_fair: Noul 0.120000

### 6/42 semantic-contract assessment

- Request ID: 642_semantic
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- 642_target_matches_goal: Noul 0.700000

- 642_primary_metric_matches_goal: Noul 0.800000

- 642_hits_should_override_logscore: Noul 0.110000

### 6/42 logistic evidence

- Request ID: 642_logistic
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- 642_logistic_hit_gain_is_reliable: Noul 0.190000

- 642_logistic_probability_quality_improved: Noul 0.350000

- 642_logistic_calibration_is_acceptable: Noul 0.120000

- 642_logistic_failure_interpretation: selected RANKING_SIGNAL_WITHOUT_PROBABILITY_SUPPORT

  | Choice | Probability |
  |---|---:|
  | INSUFFICIENT_EVIDENCE | 0.010000 |
  | RANKING_SIGNAL_WITHOUT_PROBABILITY_SUPPORT | 0.670000 |
  | PREDICTIVE_IMPROVEMENT | 0.010000 |
  | CALIBRATION_FAILURE | 0.100000 |
  | NO_OBSERVED_IMPROVEMENT | 0.210000 |
  | Response confidence | 0.590000 (response-distribution information only) |

### 6/42 random-forest evidence

- Request ID: 642_random_forest
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- 642_rf_beats_simple_baselines: Noul 0.120000

- 642_rf_failure_interpretation: selected WEAK_UNSTABLE_SIGNAL

  | Choice | Probability |
  |---|---:|
  | PREDICTIVE_IMPROVEMENT | 0.000000 |
  | WEAK_UNSTABLE_SIGNAL | 0.840000 |
  | NO_OBSERVED_IMPROVEMENT | 0.140000 |
  | INSUFFICIENT_EVIDENCE | 0.020000 |
  | Response confidence | 0.790000 (response-distribution information only) |

### 6/42 shrinkage evidence

- Request ID: 642_shrinkage
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- 642_shrinkage_reduces_overfit: Noul 0.830000

- 642_shrinkage_beats_fair: Noul 0.150000

### Cross-method information-signal assessment

- Request ID: information_signal
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- 642_mi_real_association_under_test: Noul 0.730000

- 642_mi_establishes_predictive_utility: Noul 0.200000

- 642_mi_interpretation: selected SMALL_ASSOCIATION_WITHOUT_PREDICTIVE_GAIN

  | Choice | Probability |
  |---|---:|
  | METHOD_INVALID | 0.010000 |
  | SMALL_ASSOCIATION_WITHOUT_PREDICTIVE_GAIN | 0.830000 |
  | LIKELY_RANDOM_FALSE_POSITIVE | 0.110000 |
  | VALIDATED_PREDICTIVE_SIGNAL | 0.050000 |
  | UNRESOLVED | 0.000000 |
  | Response confidence | 0.790000 (response-distribution information only) |

### Method-failure diagnosis

- Request ID: method_failure
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- evidence_indicates_leakage: Noul 0.220000

- metrics_misaligned_with_goal: Noul 0.390000

- primary_failure_source: selected NO_DEMONSTRATED_SIGNAL

  | Choice | Probability |
  |---|---:|
  | CALIBRATION_FAILURE | 0.010000 |
  | MODEL_MISSPECIFICATION | 0.000000 |
  | INSUFFICIENT_SAMPLE_POWER | 0.060000 |
  | VALIDATION_REUSE_LIMITATION | 0.010000 |
  | NO_DEMONSTRATED_SIGNAL | 0.910000 |
  | UNRESOLVED | 0.000000 |
  | MATERIAL_METHOD_DEFECT | 0.010000 |
  | Response confidence | 0.890000 (response-distribution information only) |

### Model-specific test-gate assessment

- Request ID: test_gate
- Returned JEV model: jev-1.13.0
- HTTP status: 200

- any_model_has_primary_metric_advantage: Noul 0.530000

- any_model_has_stable_temporal_advantage: Noul 0.500000

- any_model_ready_for_locked_test: Noul 0.210000

## Deterministic aggregation

- Classification: NO_TESTED_MODEL_READY
- Phase 6B status: PHASE6B_MODEL_SEMANTIC_ADJUDICATION_COMPLETE
- Full Choice distributions are retained and are not objective correctness probabilities.

## Previous Phase 6 comparison

- Previous Phase 6 recorded status: STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL.
- Phase 6B sent no Phase 6 verdict, status, or confidence to JEV. This local comparison was added after all JEV requests completed.

## Locked test and credentials

- Locked test: SEALED. No target rows were read, scored, or predicted.
- Credential value and Authorization header were not recorded. Request, response, and output echo checks passed.
- Keys.env was verified ignored and untracked. Only TYPESAFE_API_KEY was loaded into process memory for the requests.

## Validation

- request_count: 9
- typed_answer_ids: PASS
- noul_bounds: PASS
- choice_distributions: PASS
- prior_phase6_not_in_request_states: PASS
- locked_test_boundary: PASS
- credential_echo_checks: PASS

## Files

- reports/phase6b_3d_semantic_adjudication.json
- reports/phase6b_3d_model_evidence.json
- reports/phase6b_642_semantic_adjudication.json
- reports/phase6b_642_model_evidence.json
- reports/phase6b_information_signal_adjudication.json
- reports/phase6b_model_semantic_summary.json
- scripts/phase6b_model_semantic_jev.py
