# @codebase_provenance_JEO
"""Run the Phase 6B model-specific JEV evidence assessment."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import jev_client


ROOT = Path(__file__).resolve().parents[1]
API_KEY_NAME = "TYPESAFE_API_KEY"
PHASE = "PHASE_6B_JEV_MODEL_SEMANTIC_READJUDICATION"
CHOICE_SUM_TOLERANCE = 1e-6
OUTPUTS = {
    "3d_semantic": "phase6b_3d_semantic_adjudication.json",
    "3d_model_evidence": "phase6b_3d_model_evidence.json",
    "642_semantic": "phase6b_642_semantic_adjudication.json",
    "642_model_evidence": "phase6b_642_model_evidence.json",
    "information_signal": "phase6b_information_signal_adjudication.json",
    "summary": "phase6b_model_semantic_summary.json",
    "review": "phase6b_model_semantic_review.md",
}
REQUIRED_INPUTS = (
    "models/phase5a_model_config.json",
    "data/features/feature_dictionary.json",
    "reports/phase5a_metrics.json",
    "reports/phase5r_evidence.json",
    "reports/phase5r_information_tests.csv",
    "reports/phase5r_combination_probability_metrics.csv",
    "reports/phase5r_bayesian_shrinkage.csv",
    "reports/phase5r_stationarity.csv",
    "reports/phase5r_temporal_dependence.csv",
)


def _noul(question: str, true_meaning: str, false_meaning: str) -> dict[str, Any]:
    return {
        "type": "noul",
        "question": question,
        "true_meaning": true_meaning,
        "false_meaning": false_meaning,
    }


def _choice(question: str, choices: dict[str, str]) -> dict[str, Any]:
    return {"type": "choice", "question": question, "choices": choices}


REQUEST_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "3d_semantic",
        "title": "3D semantic-contract assessment",
        "questions": {
            "3d_target_matches_goal": _noul(
                "Does the evaluated 3D model output correspond to a probability model for the complete next unordered three-digit multiset rather than merely recurring individual digits?",
                "The model output can be interpreted consistently as a next-draw probability distribution over valid complete 3D outcomes.",
                "The model output does not represent the intended complete next-draw probability target.",
            ),
            "3d_primary_metric_matches_goal": _noul(
                "Does complete-combination negative log likelihood directly evaluate whether the model assigned better probability to the actual next 3D draw?",
                "The metric is aligned with the intended probability-prediction objective.",
                "The metric does not adequately measure the stated prediction objective.",
            ),
            "3d_secondary_overlap_is_primary_evidence": _noul(
                "Should multiset overlap be treated as stronger evidence of predictive probability quality than complete-combination likelihood?",
                "Overlap should dominate the probability score when judging prediction quality.",
                "Overlap is secondary and should not override a worse proper probability score.",
            ),
        },
    },
    {
        "id": "3d_predictive",
        "title": "3D predictive evidence and shrinkage",
        "questions": {
            "3d_logistic_beats_fair_probability_baseline": _noul(
                "Does the 3D logistic model show evidence that it assigns better probabilities to future complete draws than the fair baseline?",
                "The primary proper-scoring evidence supports predictive improvement.",
                "The primary proper-scoring evidence does not support predictive improvement.",
            ),
            "3d_logistic_improvement_temporally_stable": _noul(
                "Is any apparent 3D logistic advantage directionally stable across chronological periods?",
                "The evidence shows consistent temporal improvement.",
                "The apparent advantage is absent, inconsistent, or unstable across time.",
            ),
            "3d_logistic_failure_interpretation": _choice(
                "Which interpretation best matches the 3D logistic evidence?",
                {
                    "PREDICTIVE_IMPROVEMENT": "The model demonstrates meaningful improvement in complete-draw probability prediction.",
                    "SECONDARY_METRIC_ONLY": "Some secondary metric appears favorable, but the primary probability evidence does not support improvement.",
                    "NO_OBSERVED_IMPROVEMENT": "The model does not outperform the relevant probability baselines.",
                    "MODEL_SEMANTICS_INVALID": "The model or metric does not represent the intended prediction target.",
                    "INSUFFICIENT_EVIDENCE": "The available evidence cannot resolve the model's predictive value.",
                },
            ),
            "3d_shrinkage_beats_fair": _noul(
                "Did any evaluated 3D Bayesian-shrinkage setting improve complete-combination probability scoring over the fair baseline?",
                "At least one shrinkage model has supported improvement.",
                "No tested shrinkage setting established improvement.",
            ),
        },
    },
    {
        "id": "642_semantic",
        "title": "6/42 semantic-contract assessment",
        "questions": {
            "642_target_matches_goal": _noul(
                "Does the fixed-cardinality 6/42 combination model represent probabilities over valid complete six-number sets rather than only independent number recurrence?",
                "The model evaluates complete valid six-number outcomes.",
                "The model is semantically misaligned with the complete-draw prediction target.",
            ),
            "642_primary_metric_matches_goal": _noul(
                "Does complete-set negative log likelihood directly evaluate whether the model assigned better probability to the actual next 6/42 combination?",
                "The metric directly matches the intended probabilistic prediction objective.",
                "The metric is not an appropriate primary measure for the stated prediction objective.",
            ),
            "642_hits_should_override_logscore": _noul(
                "Should a higher hits-at-6 point estimate override worse complete-combination probability scoring when deciding whether the model learned useful next-draw probability information?",
                "The hit-count point estimate is sufficient to override the proper probability score.",
                "The hit-count result is secondary and cannot by itself establish improved probabilistic prediction.",
            ),
        },
    },
    {
        "id": "642_logistic",
        "title": "6/42 logistic evidence",
        "questions": {
            "642_logistic_hit_gain_is_reliable": _noul(
                "Does the evidence support interpreting the higher 6/42 logistic hits-at-6 point estimate as a reliable predictive improvement?",
                "The hit-count improvement is supported by uncertainty and comparison evidence.",
                "The hit-count increase is not sufficiently supported to establish predictive improvement.",
            ),
            "642_logistic_probability_quality_improved": _noul(
                "Does the 6/42 logistic model improve probability quality relative to the relevant baselines?",
                "Calibration and proper probability scoring support improvement.",
                "Probability scoring or calibration does not support improvement.",
            ),
            "642_logistic_calibration_is_acceptable": _noul(
                "Is the reported 6/42 logistic calibration adequate for interpreting its output as useful next-draw probabilities?",
                "Calibration is sufficiently controlled for probabilistic interpretation.",
                "Calibration is poor enough to materially weaken probabilistic interpretation.",
            ),
            "642_logistic_failure_interpretation": _choice(
                "Which interpretation best matches the 6/42 logistic evidence?",
                {
                    "PREDICTIVE_IMPROVEMENT": "The model demonstrates meaningful improvement in complete-draw prediction.",
                    "RANKING_SIGNAL_WITHOUT_PROBABILITY_SUPPORT": "The ranking metric looks somewhat better, but probability quality and uncertainty do not establish predictive improvement.",
                    "CALIBRATION_FAILURE": "The model's primary problem is severe probability miscalibration.",
                    "NO_OBSERVED_IMPROVEMENT": "The model does not reliably outperform the relevant baselines.",
                    "INSUFFICIENT_EVIDENCE": "The evidence cannot resolve whether the model is useful.",
                },
            ),
        },
    },
    {
        "id": "642_random_forest",
        "title": "6/42 random-forest evidence",
        "questions": {
            "642_rf_beats_simple_baselines": _noul(
                "Does the 6/42 random forest reliably outperform the fair and expanding-frequency baselines?",
                "The evidence supports reliable improvement.",
                "The evidence does not establish reliable improvement.",
            ),
            "642_rf_failure_interpretation": _choice(
                "Which interpretation best matches the 6/42 random-forest evidence?",
                {
                    "PREDICTIVE_IMPROVEMENT": "The model demonstrates predictive improvement.",
                    "WEAK_UNSTABLE_SIGNAL": "Some periods appear favorable but the effect is not stable enough for a predictive claim.",
                    "NO_OBSERVED_IMPROVEMENT": "The model does not outperform relevant baselines.",
                    "INSUFFICIENT_EVIDENCE": "The evidence is insufficient to determine predictive value.",
                },
            ),
        },
    },
    {
        "id": "642_shrinkage",
        "title": "6/42 shrinkage evidence",
        "questions": {
            "642_shrinkage_reduces_overfit": _noul(
                "Did stronger Bayesian shrinkage move the 6/42 historical-frequency model closer to fair-baseline probability performance?",
                "Shrinkage reduced the historical model's probability-score deficit.",
                "Shrinkage did not reduce the deficit.",
            ),
            "642_shrinkage_beats_fair": _noul(
                "Did any evaluated 6/42 Bayesian-shrinkage model outperform the fair complete-combination likelihood baseline?",
                "At least one shrinkage setting demonstrated complete-combination probability improvement.",
                "No tested shrinkage setting demonstrated improvement.",
            ),
        },
    },
    {
        "id": "information_signal",
        "title": "Cross-method information-signal assessment",
        "questions": {
            "642_mi_real_association_under_test": _noul(
                "Within the defined permutation test and multiple-testing procedure, does the expanding-frequency result provide evidence of a small statistical association?",
                "The tested development data contain evidence of a small association under the stated procedure.",
                "The result does not provide evidence beyond the permutation null under the stated procedure.",
            ),
            "642_mi_establishes_predictive_utility": _noul(
                "Does the detected mutual-information association establish useful prediction of future complete 6/42 draws?",
                "The association translated into validated complete-draw predictive value.",
                "The association did not establish validated complete-draw predictive value.",
            ),
            "642_mi_interpretation": _choice(
                "Which interpretation best fits the relationship between the mutual-information result and the validation results?",
                {
                    "VALIDATED_PREDICTIVE_SIGNAL": "The information finding produced validated improvement in future complete-draw prediction.",
                    "SMALL_ASSOCIATION_WITHOUT_PREDICTIVE_GAIN": "A small statistical association was detected but did not improve complete-draw validation performance.",
                    "LIKELY_RANDOM_FALSE_POSITIVE": "The evidence most strongly supports interpreting the result as a chance discovery.",
                    "METHOD_INVALID": "The information-test design is invalid for the stated question.",
                    "UNRESOLVED": "The evidence cannot distinguish among these interpretations.",
                },
            ),
        },
    },
    {
        "id": "method_failure",
        "title": "Method-failure diagnosis",
        "questions": {
            "evidence_indicates_leakage": _noul(
                "Does the supplied validation evidence indicate material future-data leakage in the evaluated pipeline?",
                "A leakage defect materially compromises the reported results.",
                "No supplied evidence establishes material future-data leakage.",
            ),
            "metrics_misaligned_with_goal": _noul(
                "Are the complete-combination proper scoring metrics materially misaligned with the stated goal of predicting the complete next draw?",
                "The primary metrics do not measure the intended target.",
                "The primary metrics are appropriately aligned with the intended prediction target.",
            ),
            "primary_failure_source": _choice(
                "Given the supplied evidence, what best describes why the tested methods did not establish predictive improvement?",
                {
                    "NO_DEMONSTRATED_SIGNAL": "The tested historical information did not produce reproducible out-of-sample predictive improvement.",
                    "MODEL_MISSPECIFICATION": "The evidence suggests the models were materially inappropriate for the underlying predictive structure.",
                    "CALIBRATION_FAILURE": "The dominant issue is that predicted probabilities were poorly calibrated.",
                    "INSUFFICIENT_SAMPLE_POWER": "The main limitation is insufficient data to resolve a potentially useful effect.",
                    "VALIDATION_REUSE_LIMITATION": "Repeated use of the development validation set prevents a strong conclusion.",
                    "MATERIAL_METHOD_DEFECT": "A methodological defect invalidates the present evidence.",
                    "UNRESOLVED": "The supplied evidence cannot identify a dominant explanation.",
                },
            ),
        },
    },
    {
        "id": "test_gate",
        "title": "Model-specific test-gate assessment",
        "questions": {
            "any_model_has_primary_metric_advantage": _noul(
                "Does any tested model demonstrate a supported improvement over the fair baseline on its primary complete-draw probability metric?",
                "At least one tested model has primary-metric evidence supporting improvement.",
                "No tested model has such evidence.",
            ),
            "any_model_has_stable_temporal_advantage": _noul(
                "Does any tested model demonstrate a directionally stable predictive advantage across chronological validation periods?",
                "At least one model shows stable temporal improvement.",
                "No tested model shows stable temporal improvement.",
            ),
            "any_model_ready_for_locked_test": _noul(
                "Based only on the supplied model-specific evidence and the predefined gate, is any tested candidate ready to be frozen for a separately authorized locked-test evaluation?",
                "At least one specific candidate satisfies the stated evidence requirements.",
                "No tested candidate satisfies the stated evidence requirements.",
            ),
        },
    },
)


class Phase6BError(RuntimeError):
    def __init__(self, error_code: str, http_status: int | None = None) -> None:
        self.error_code = error_code
        self.http_status = http_status
        super().__init__(error_code)


def _read_json(relative_path: str) -> dict[str, Any]:
    try:
        value = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        raise Phase6BError("InputJSONInvalid") from None
    if not isinstance(value, dict):
        raise Phase6BError("InputJSONShapeInvalid")
    return value


def _numeric_tree(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            cleaned = _numeric_tree(item)
            if cleaned is not None:
                result[str(key)] = cleaned
        return result
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _numeric_tree(item)) is not None]
    return None


def _scalar_tree(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            cleaned = _scalar_tree(item)
            if cleaned is not None:
                result[str(key)] = cleaned
        return result
    return None


def _scalar_fields(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if isinstance(item, bool)
        or (
            isinstance(item, (int, float))
            and math.isfinite(item)
        )
    }


def _require_inputs() -> None:
    if any(not (ROOT / path).is_file() for path in REQUIRED_INPUTS):
        raise Phase6BError("RequiredInputMissing")
    if not (ROOT / "Keys.env").is_file():
        raise Phase6BError("CredentialFileMissing")
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", "Keys.env"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", "Keys.env"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if not ignored or tracked:
        raise Phase6BError("CredentialGitBoundaryInvalid")


def _read_information_tests() -> list[dict[str, Any]]:
    path = ROOT / "reports/phase5r_information_tests.csv"
    fields = (
        "game",
        "diagnostic_family",
        "target_measure",
        "observed_mutual_information_nats_per_candidate",
        "permutations",
        "empirical_p_add_one",
        "bh_q_within_game",
        "null_mean",
        "null_95_percentile",
        "complete_draw_rows_permuted",
        "permutation_features_recomputed_from_prior_rows",
        "train_only",
    )
    selected = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not set(fields).issubset(reader.fieldnames or ()):
                raise Phase6BError("InformationCSVStructureInvalid")
            for row in reader:
                if row.get("game") != "lotto_6_42" or row.get("diagnostic_family") not in (
                    "expanding_historical_frequency",
                    "previous_30_frequency",
                ):
                    continue
                record: dict[str, Any] = {
                    "game": row["game"],
                    "diagnostic_family": row["diagnostic_family"],
                    "target_measure": row["target_measure"],
                }
                for name in fields[3:]:
                    value = row[name]
                    if name == "permutations":
                        record[name] = int(value)
                    elif name in (
                        "complete_draw_rows_permuted",
                        "permutation_features_recomputed_from_prior_rows",
                        "train_only",
                    ):
                        record[name] = value.strip().lower() == "true"
                    else:
                        record[name] = float(value)
                selected.append(record)
    except Phase6BError:
        raise
    except (OSError, UnicodeError, ValueError, csv.Error):
        raise Phase6BError("InformationCSVInvalid") from None
    if {row["diagnostic_family"] for row in selected} != {
        "expanding_historical_frequency",
        "previous_30_frequency",
    } or any(not row["train_only"] for row in selected):
        raise Phase6BError("InformationRowsMissingOrOutOfScope")
    return selected


def _periods(metrics: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for game in ("3d_lotto", "lotto_6_42"):
        result[game] = {}
        for part in ("train", "validation"):
            row = metrics.get("partitions", {}).get(game, {}).get(part)
            if not isinstance(row, dict):
                raise Phase6BError("DevelopmentPartitionMissing")
            record = {
                "start_date": row.get("start_date"),
                "end_date": row.get("end_date"),
                "row_count": row.get("row_count"),
            }
            if not all(record.values()):
                raise Phase6BError("DevelopmentPartitionInvalid")
            result[game][part] = record
    return result


def _folds(
    metrics: dict[str, Any], config: dict[str, Any], game: str, model: str
) -> list[dict[str, Any]]:
    model_alias = "random_forest" if model == "random_forest_multioutput_comparator" else "logistic"
    expected_groups = list(config["feature_groups"])
    selection = metrics["cv"]["selection"][game].get(model_alias, {})
    rows = []
    for row in metrics["cv"]["fold_results"]:
        if row.get("game") != game or row.get("model") != model:
            continue
        group = row["feature_group"]
        selected_c = selection.get(group, {}).get("selected_c") if model_alias == "logistic" else None
        if model_alias == "logistic" and row.get("c") != selected_c:
            continue
        if model_alias == "random_forest" and row.get("c") is not None:
            continue
        fields = [
            "feature_group", "fold", "train_start_date", "train_end_date",
            "validation_start_date", "validation_end_date", "train_rows",
            "validation_rows", "c",
        ]
        if game == "3d_lotto":
            fields += [
                "mean_multinomial_negative_log_likelihood_per_digit",
                "uniform_nll", "expanding_frequency_nll", "mean_multiset_overlap",
            ]
        else:
            fields += [
                "mean_hits_at_6", "fair_random_expected_hits",
                "expanding_frequency_hits", "recent_30_frequency_hits",
            ]
        rows.append({key: row[key] for key in fields if key in row})
    rows.sort(key=lambda row: (row["feature_group"], row["fold"]))
    if {row["feature_group"] for row in rows} != set(expected_groups):
        raise Phase6BError("ChronologicalFoldGroupsInvalid")
    if any(
        [row["fold"] for row in rows if row["feature_group"] == group] != [1, 2, 3]
        for group in expected_groups
    ):
        raise Phase6BError("ChronologicalFoldCountInvalid")
    return rows


def _game_metrics(metrics: dict[str, Any], game: str) -> dict[str, Any]:
    result = metrics["validation"][game]
    return {
        "primary_metric": result["primary_metric"],
        "primary_direction": result["primary_direction"],
        "methods": {
            name: _scalar_fields(values) for name, values in result["methods"].items()
        },
    }


def _game_evidence(
    metrics: dict[str, Any], config: dict[str, Any], game: str
) -> dict[str, Any]:
    model_names = (
        ("multinomial_logistic_regression",)
        if game == "3d_lotto"
        else (
            "regularized_one_vs_rest_logistic_regression",
            "random_forest_multioutput_comparator",
        )
    )
    return {
        "primary_metric": metrics["validation"][game]["primary_metric"],
        "primary_direction": metrics["validation"][game]["primary_direction"],
        "validation_methods": _game_metrics(metrics, game)["methods"],
        "selected_chronological_folds": {
            model: _folds(metrics, config, game, model) for model in model_names
        },
        "bootstrap": _numeric_tree(metrics["bootstrap"]["games"][game]),
        "monte_carlo": _numeric_tree(metrics["random_baseline"]["games"][game]),
        "calibration": _scalar_tree(metrics.get("calibration", {}).get(game, {})),
        "feature_ablation": [
            {
                "model": row["model"],
                "feature_group": row["feature_group"],
                "selected_c": row.get("selected_c"),
                "metrics": _numeric_tree(
                    {
                        key: value
                        for key, value in row.items()
                        if key not in ("game", "model", "feature_group", "selected_c")
                    }
                ),
            }
            for row in metrics["feature_ablation"]
            if row.get("game") == game
        ],
    }


def _phase5r_game(p5r: dict[str, Any], game: str) -> dict[str, Any]:
    stationarity = p5r["stationarity"][game]
    return {
        "complete_combination_validation": {
            "fair_log_score_nats": p5r["combination_validation"][game]["fair_log_score_nats"],
            "models": _scalar_tree(p5r["combination_validation"][game]["models"]),
        },
        "paired_row_bootstrap": _numeric_tree(p5r["bootstrap"][game]),
        "fair_random_monte_carlo": {
            "initial_simulations_per_model": p5r["fair_random_monte_carlo"][game]["initial_simulations_per_model"],
            "confirmation_simulations": p5r["fair_random_monte_carlo"][game]["confirmation_simulations"],
            "escalated_models": p5r["fair_random_monte_carlo"][game]["escalated_models"],
            "models": {
                name: {
                    key: row[key]
                    for key in (
                        "complete_fair_random_validation_histories",
                        "confirmation_escalated",
                        "empirical_p_add_one",
                        "fair_null_simulation_mean",
                        "forecast_path_fixed_to_observed_history",
                        "initial_empirical_p_add_one",
                        "initial_simulations",
                        "observed_mean_log_score_advantage_vs_fair",
                        "simulations",
                    )
                    if key in row
                }
                for name, row in p5r["fair_random_monte_carlo"][game]["models"].items()
            },
        },
        "bayesian_shrinkage": _scalar_tree(p5r["shrinkage"][game]),
        "calibration": _scalar_tree(p5r["calibration"][game]),
        "stationarity": {
            "data_scope": stationarity["data_scope"],
            "rolling_window_draws": stationarity["rolling_window_draws"],
            "rolling_stride_draws": stationarity["rolling_stride_draws"],
            "change_point_permutations": stationarity["change_point_permutations"],
            "chronological_windows": [
                {
                    key: row[key]
                    for key in ("third", "start_date", "end_date", "row_count")
                }
                for row in stationarity["chronological_windows"]
            ],
            "change_points": [
                {
                    key: row[key]
                    for key in (
                        "metric", "p_value", "bh_q_within_change_family",
                        "maximum_standardized_mean_shift", "permutations",
                    )
                }
                for row in stationarity["change_points"]
            ],
            "jensen_shannon": [
                {
                    key: row[key]
                    for key in ("metric", "window_a", "window_b", "js_divergence_bits")
                }
                for row in stationarity["jensen_shannon"]
            ],
        },
    }


def _build_bundle() -> dict[str, Any]:
    _require_inputs()
    config = _read_json("models/phase5a_model_config.json")
    feature_dictionary = _read_json("data/features/feature_dictionary.json")
    p5a = _read_json("reports/phase5a_metrics.json")
    p5r = _read_json("reports/phase5r_evidence.json")
    if not all(key in feature_dictionary for key in ("3d_lotto", "lotto_6_42")):
        raise Phase6BError("FeatureDictionaryInvalid")
    if not all(key in config.get("models", {}) for key in ("3d_lotto", "lotto_6_42")):
        raise Phase6BError("ModelConfigurationInvalid")
    if len(p5a.get("cv", {}).get("fold_results", [])) != 84:
        raise Phase6BError("ChronologicalCVSourceInvalid")
    periods = _periods(p5a)
    information_tests = _read_information_tests()
    phase5a = {
        game: _game_evidence(p5a, config, game)
        for game in ("3d_lotto", "lotto_6_42")
    }
    phase5r = {
        game: _phase5r_game(p5r, game)
        for game in ("3d_lotto", "lotto_6_42")
    }
    return {
        "target_definitions": {
            "3d_lotto": {
                "outcome": "unordered multiset of three digits; repeated digits are preserved",
                "complete_combination_probability": True,
            },
            "lotto_6_42": {
                "outcome": "unordered set of six distinct numbers from 1 through 42",
                "complete_combination_probability": True,
            },
        },
        "development_periods": periods,
        "model_configuration": {
            "3d_lotto": config["models"]["3d_lotto"],
            "lotto_6_42": config["models"]["lotto_6_42"],
        },
        "feature_group_meanings": config["feature_groups"],
        "chronological_validation_protocol": {
            key: config["time_series_cv"][key]
            for key in ("method", "n_splits", "shuffle", "scope")
        },
        "random_baseline_configuration": {
            key: config["random_baseline"][key]
            for key in (
                "seed", "initial_simulations", "confirmation_trigger_p_below",
                "confirmation_simulations", "empirical_p",
            )
        },
        "predefined_phase5a_candidate_gate": {
            key: config["decision_rule"][key]
            for key in (
                "maximum_adjusted_empirical_p", "minimum_folds_better",
                "maximum_ece", "bootstrap_interval_rule",
                "3d_lotto_primary_rule", "lotto_6_42_primary_rule",
            )
        },
        "phase5a": phase5a,
        "phase5r": phase5r,
        "information_tests": information_tests,
    }


def _request_questions(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for question_id, question in spec["questions"].items():
        if question["type"] == "noul":
            result[question_id] = {
                "type": "noul",
                "instructions": question["question"],
                "criteria": {
                    "true": question["true_meaning"],
                    "false": question["false_meaning"],
                },
            }
        else:
            result[question_id] = {
                "type": "choice",
                "instructions": question["question"],
                "criteria": question["choices"],
            }
    return result


def _select_phase5a(
    game: dict[str, Any], model_names: tuple[str, ...]
) -> dict[str, Any]:
    baselines = {
        "uniform_random",
        "expanding_historical_frequency",
        "recent_30_frequency",
    }
    return {
        "primary_metric": game["primary_metric"],
        "primary_direction": game["primary_direction"],
        "validation_methods": {
            name: values
            for name, values in game["validation_methods"].items()
            if name in baselines or any(name.startswith(model) for model in model_names)
        },
        "selected_chronological_folds": {
            model: game["selected_chronological_folds"][model]
            for model in model_names
            if model in game["selected_chronological_folds"]
        },
        "bootstrap": {
            name: values
            for name, values in game["bootstrap"].items()
            if name in model_names
            or any(name.startswith(model + "/") for model in model_names)
        },
        "monte_carlo": {
            key: value
            for key, value in game["monte_carlo"].items()
            if key != "candidates"
        }
        | {
            "candidates": {
                name: values
                for name, values in game["monte_carlo"].get("candidates", {}).items()
                if any(name.startswith(model) for model in model_names)
            }
        },
        "calibration": {
            name: values
            for name, values in game["calibration"].items()
            if name in baselines or any(name.startswith(model) for model in model_names)
        },
        "feature_ablation": [
            row
            for row in game["feature_ablation"]
            if row["model"] in model_names
        ],
    }


def _compact_phase5r(game: dict[str, Any]) -> dict[str, Any]:
    bootstrap = {}
    for model, row in game["paired_row_bootstrap"].items():
        bootstrap[model] = {
            key: row[key]
            for key in (
                "bootstrap_ci95_vs_fair",
                "segment_log_score_advantage_vs_fair",
                "segments_better_than_fair",
                "bootstrap_ci95_vs_raw_expanding",
                "segment_log_score_difference_vs_raw_expanding",
                "segments_better_than_raw_expanding",
                "bootstrap_resamples",
                "whole_validation_draw_rows_resampled",
            )
            if key in row
        }
    combination = game["complete_combination_validation"]
    score_fields = (
        "mean_combination_nll_nats",
        "mean_log_score_advantage_vs_fair",
        "mean_log_score_difference_vs_raw",
        "mean_hits_at_6",
        "hits_at_6_fair_expectation",
        "marginal_brier",
    )
    shrinkage_fields = (
        "prior_center",
        "prior_strength",
        "mean_posterior_probability_across_candidate_draws",
        "mean_absolute_difference_from_raw_frequency",
        "maximum_absolute_difference_from_raw_frequency",
    )
    monte_carlo_fields = (
        "confirmation_escalated",
        "empirical_p_add_one",
        "initial_empirical_p_add_one",
        "initial_simulations",
        "observed_mean_log_score_advantage_vs_fair",
        "simulations",
    )
    return {
        "complete_combination_validation": {
            key: combination[key]
            for key in ("fair_log_score_nats", "valid_set_count")
            if key in combination
        }
        | {
            "models": {
                model: {key: row[key] for key in score_fields if key in row}
                for model, row in combination["models"].items()
            }
        },
        "paired_row_bootstrap": bootstrap,
        "fair_random_monte_carlo": {
            "initial_simulations_per_model": game["fair_random_monte_carlo"][
                "initial_simulations_per_model"
            ],
            "confirmation_simulations": game["fair_random_monte_carlo"][
                "confirmation_simulations"
            ],
            "escalated_models": game["fair_random_monte_carlo"]["escalated_models"],
            "models": {
                model: {
                    key: row[key] for key in monte_carlo_fields if key in row
                }
                for model, row in game["fair_random_monte_carlo"]["models"].items()
            },
        },
        "bayesian_shrinkage": {
            model: {key: row[key] for key in shrinkage_fields if key in row}
            for model, row in game["bayesian_shrinkage"].items()
        },
        "calibration": game["calibration"],
    }


def _gate_phase5a(game: dict[str, Any]) -> dict[str, Any]:
    folds = []
    for model, model_rows in game["selected_chronological_folds"].items():
        for row in model_rows:
            record = {
                "model": model,
                "feature_group": row["feature_group"],
                "fold": row["fold"],
            }
            if "mean_multinomial_negative_log_likelihood_per_digit" in row:
                record.update(
                    {
                        "primary_score": row[
                            "mean_multinomial_negative_log_likelihood_per_digit"
                        ],
                        "fair_baseline": row["uniform_nll"],
                        "historical_baseline": row["expanding_frequency_nll"],
                        "secondary_overlap": row["mean_multiset_overlap"],
                    }
                )
            else:
                record.update(
                    {
                        "primary_score": row["mean_hits_at_6"],
                        "fair_baseline": row["fair_random_expected_hits"],
                        "historical_baseline": row["expanding_frequency_hits"],
                        "recent_baseline": row["recent_30_frequency_hits"],
                    }
                )
            folds.append(record)
    return {
        "primary_metric": game["primary_metric"],
        "primary_direction": game["primary_direction"],
        "validation_methods": game["validation_methods"],
        "chronological_fold_scores": folds,
        "bootstrap": game["bootstrap"],
        "monte_carlo": game["monte_carlo"],
        "calibration": game["calibration"],
    }


def _request_states(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    target3d = bundle["target_definitions"]["3d_lotto"]
    target642 = bundle["target_definitions"]["lotto_6_42"]
    logistic3d = ("multinomial_logistic_regression",)
    logistic642 = ("regularized_one_vs_rest_logistic_regression",)
    forest642 = ("random_forest_multioutput_comparator",)
    all642 = logistic642 + forest642
    compact3d = _select_phase5a(bundle["phase5a"]["3d_lotto"], logistic3d)
    compact642_logistic = _select_phase5a(
        bundle["phase5a"]["lotto_6_42"], logistic642
    )
    compact642_forest = _select_phase5a(bundle["phase5a"]["lotto_6_42"], forest642)
    compact642_all = _select_phase5a(bundle["phase5a"]["lotto_6_42"], all642)
    complete3d = _compact_phase5r(bundle["phase5r"]["3d_lotto"])
    complete642 = _compact_phase5r(bundle["phase5r"]["lotto_6_42"])
    gate3d = _gate_phase5a(bundle["phase5a"]["3d_lotto"])
    gate642 = _gate_phase5a(bundle["phase5a"]["lotto_6_42"])
    method_phase5r = {
        game: {
            "complete_combination_validation": bundle["phase5r"][game][
                "complete_combination_validation"
            ],
            "paired_row_bootstrap": complete["paired_row_bootstrap"],
        }
        for game, complete in (("3d_lotto", complete3d), ("lotto_6_42", complete642))
    }
    evidence3d = {
        "target": target3d,
        "development_periods": bundle["development_periods"]["3d_lotto"],
        "model_configuration": bundle["model_configuration"]["3d_lotto"],
        "feature_group_meanings": bundle["feature_group_meanings"],
        "phase5a_validation_evidence": compact3d,
        "phase5r_complete_draw_evidence": complete3d,
    }
    evidence642 = {
        "target": target642,
        "development_periods": bundle["development_periods"]["lotto_6_42"],
        "model_configuration": bundle["model_configuration"]["lotto_6_42"],
        "feature_group_meanings": bundle["feature_group_meanings"],
        "phase5a_validation_evidence": compact642_all,
        "phase5r_complete_draw_evidence": complete642,
    }
    return {
        "3d_semantic": {
            "target": target3d,
            "model_configuration": evidence3d["model_configuration"],
            "primary_metric": {
                "phase5a_name": bundle["phase5a"]["3d_lotto"]["primary_metric"],
                "phase5a_direction": bundle["phase5a"]["3d_lotto"]["primary_direction"],
                "phase5r_complete_combination_validation": bundle["phase5r"]["3d_lotto"][
                    "complete_combination_validation"
                ],
            },
            "secondary_metric": "mean_multiset_overlap",
            "phase5a_validation_metrics": compact3d["validation_methods"],
        },
        "3d_predictive": evidence3d,
        "642_semantic": {
            "target": target642,
            "phase5a_model_configurations": bundle["model_configuration"]["lotto_6_42"],
            "phase5a_validation_metrics": compact642_all["validation_methods"],
            "phase5r_complete_combination_validation": bundle["phase5r"]["lotto_6_42"][
                "complete_combination_validation"
            ],
            "phase5r_combination_calibration": bundle["phase5r"]["lotto_6_42"]["calibration"],
        },
        "642_logistic": {
            "target": target642,
            "model": bundle["model_configuration"]["lotto_6_42"]["logistic"],
            "development_periods": bundle["development_periods"]["lotto_6_42"],
            "feature_group_meanings": bundle["feature_group_meanings"],
            "validation_evidence": compact642_logistic,
            "complete_combination_frequency_model_comparison": complete642,
        },
        "642_random_forest": {
            "target": target642,
            "model": bundle["model_configuration"]["lotto_6_42"]["random_forest"],
            "development_periods": bundle["development_periods"]["lotto_6_42"],
            "feature_group_meanings": bundle["feature_group_meanings"],
            "validation_evidence": compact642_forest,
        },
        "642_shrinkage": {
            "target": target642,
            "complete_combination_validation": complete642["complete_combination_validation"],
            "paired_row_bootstrap": complete642["paired_row_bootstrap"],
            "fair_random_monte_carlo": complete642["fair_random_monte_carlo"],
            "bayesian_shrinkage": complete642["bayesian_shrinkage"],
        },
        "information_signal": {
            "target": target642,
            "mutual_information_tests": bundle["information_tests"],
            "complete_combination_validation": complete642["complete_combination_validation"],
            "bayesian_shrinkage": complete642["bayesian_shrinkage"],
            "paired_row_bootstrap": complete642["paired_row_bootstrap"],
            "temporal_validation_segments": {
                model: row["segment_log_score_advantage_vs_fair"]
                for model, row in complete642["paired_row_bootstrap"].items()
                if "segment_log_score_advantage_vs_fair" in row
            },
        },
        "method_failure": {
            "target_definitions": bundle["target_definitions"],
            "development_periods": bundle["development_periods"],
            "chronological_validation_protocol": bundle["chronological_validation_protocol"],
            "model_configuration": bundle["model_configuration"],
            "feature_group_meanings": bundle["feature_group_meanings"],
            "random_baseline_configuration": bundle["random_baseline_configuration"],
            "phase5a_validation": {
                "3d_lotto": gate3d,
                "lotto_6_42": gate642,
            },
            "phase5r_complete_draw_validation": method_phase5r,
            "mutual_information_tests": bundle["information_tests"],
        },
        "test_gate": {
            "target_definitions": bundle["target_definitions"],
            "predefined_phase5a_candidate_gate": bundle["predefined_phase5a_candidate_gate"],
            "random_baseline_configuration": bundle["random_baseline_configuration"],
            "development_periods": bundle["development_periods"],
            "phase5a_validation": {
                "3d_lotto": gate3d,
                "lotto_6_42": gate642,
            },
            "phase5r_complete_draw_validation": {
                "3d_lotto": complete3d,
                "lotto_6_42": complete642,
            },
        },
    }


def _walk(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield "key", str(key)
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)
    elif isinstance(value, str):
        yield "value", value


def _validate_bundle(states: dict[str, dict[str, Any]]) -> None:
    if len(REQUEST_SPECS) != 9 or set(states) != {row["id"] for row in REQUEST_SPECS}:
        raise Phase6BError("RequestSetInvalid")
    for spec in REQUEST_SPECS:
        if not spec["questions"] or any(
            question["type"] not in ("noul", "choice")
            for question in spec["questions"].values()
        ):
            raise Phase6BError("QuestionTypeInvalid")
        if set(_request_questions(spec)) != set(spec["questions"]):
            raise Phase6BError("QuestionIdsInvalid")
        for kind, value in _walk(states[spec["id"]]):
            if kind == "key" and value.casefold() in {
                "verdict", "final_status", "confidence", "previous_phase6",
                "previous_jev", "jev_verdict", "locked_test_outcomes",
                "target_rows", "test_rows",
            }:
                raise Phase6BError("AnchoringFieldDetected")
            upper = value.upper()
            if "STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL" in upper:
                raise Phase6BError("PriorStatusDetected")
            if "GOOD MODEL" in upper or "BAD MODEL" in upper:
                raise Phase6BError("HumanLabelDetected")
            if kind == "value" and "KEYS.ENV" in upper:
                raise Phase6BError("CredentialPathInState")
    for relative in OUTPUTS.values():
        if (ROOT / "reports" / relative).exists():
            raise Phase6BError("OutputAlreadyExists")


def _normalise_answer(answer: Any, question: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(answer, dict) or answer.get("type") != question["type"]:
        raise Phase6BError("TypedAnswerInvalid")
    if question["type"] == "noul":
        value = answer.get("noul")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise Phase6BError("TypedNoulInvalid")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise Phase6BError("TypedNoulInvalid")
        return {"type": "noul", "noul": float(value)}

    selected = answer.get("choice")
    if not isinstance(selected, str) or selected not in question["choices"]:
        raise Phase6BError("TypedChoiceInvalid")
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != set(question["choices"]):
        raise Phase6BError("ChoiceDistributionInvalid")
    distribution = {}
    for key, value in probabilities.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise Phase6BError("ChoiceDistributionInvalid")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise Phase6BError("ChoiceDistributionInvalid")
        distribution[key] = float(value)
    if abs(sum(distribution.values()) - 1.0) > CHOICE_SUM_TOLERANCE:
        raise Phase6BError("ChoiceDistributionInvalid")
    result = {"type": "choice", "choice": selected, "probabilities": distribution}
    confidence = answer.get("confidence")
    if confidence is not None:
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise Phase6BError("ChoiceConfidenceInvalid")
        result["confidence"] = float(confidence)
        result["confidence_note"] = "reported response-distribution information only"
    return result


def _validate_response(
    spec: dict[str, Any], data: dict[str, Any], api_key: str
) -> dict[str, Any]:
    serialized = json.dumps(data, ensure_ascii=False)
    if api_key in serialized or "Bearer " in serialized:
        raise Phase6BError("CredentialEchoDetected")
    model = data.get("model")
    if not isinstance(model, str) or not model.lower().startswith("jev-"):
        raise Phase6BError("ModelIdentifierInvalid")
    answers = data.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(spec["questions"]):
        raise Phase6BError("AnswerIdsInvalid")
    return {
        question_id: _normalise_answer(answers[question_id], question)
        for question_id, question in spec["questions"].items()
    }


def _request_result(
    spec: dict[str, Any], state: dict[str, Any], api_key: str
) -> dict[str, Any]:
    questions = _request_questions(spec)
    request_json = json.dumps(
        {"state": state, "model": jev_client.MODEL_ALIAS, "questions": questions},
        ensure_ascii=False,
    )
    if api_key in request_json or "Bearer " in request_json:
        raise Phase6BError("CredentialInRequestBlocked")
    try:
        http_status, data = jev_client.request_system_one(state, questions)
    except jev_client.JevClientError as error:
        raise Phase6BError(error.error_class, error.http_status) from None
    return {
        "request_id": spec["id"],
        "title": spec["title"],
        "model_alias_requested": jev_client.MODEL_ALIAS,
        "model_identifier_returned": data.get("model"),
        "http_status": http_status,
        "state": state,
        "questions": questions,
        "answers": _validate_response(spec, data, api_key),
    }


def _load_api_key() -> str:
    value = os.environ.get(API_KEY_NAME)
    if value:
        return value
    found: str | None = None
    try:
        with (ROOT / "Keys.env").open("r", encoding="utf-8") as stream:
            for line in stream:
                item = line.strip()
                if item.startswith("export "):
                    item = item[7:].lstrip()
                name, separator, raw = item.partition("=")
                if not separator or name.strip() != API_KEY_NAME:
                    continue
                if found is not None:
                    raise Phase6BError("CredentialConfigurationInvalid")
                raw = raw.strip()
                if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
                    raw = raw[1:-1]
                if not raw:
                    raise Phase6BError("CredentialUnavailable")
                found = raw
    except Phase6BError:
        raise
    except (OSError, UnicodeError):
        raise Phase6BError("CredentialUnavailable") from None
    if not found:
        raise Phase6BError("CredentialUnavailable")
    os.environ[API_KEY_NAME] = found
    return found


def _aggregate(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    answers = {}
    for result in results.values():
        answers.update(result["answers"])
    primary = answers["any_model_has_primary_metric_advantage"]["noul"]
    stable = answers["any_model_has_stable_temporal_advantage"]["noul"]
    ready = answers["any_model_ready_for_locked_test"]["noul"]
    leakage = answers["evidence_indicates_leakage"]["noul"]
    misaligned = answers["metrics_misaligned_with_goal"]["noul"]
    defect = answers["primary_failure_source"]["choice"]
    if primary >= 0.70 and stable >= 0.70 and ready >= 0.70:
        classification = "CANDIDATE_EVIDENCE_PRESENT"
    elif ready <= 0.30:
        classification = "NO_TESTED_MODEL_READY"
    elif leakage >= 0.70 or misaligned >= 0.70 or defect == "MATERIAL_METHOD_DEFECT":
        classification = "METHOD_REVIEW_REQUIRED"
    else:
        classification = "HUMAN_REVIEW_REQUIRED"
    status = {
        "CANDIDATE_EVIDENCE_PRESENT": "PHASE6B_HUMAN_REVIEW_REQUIRED",
        "NO_TESTED_MODEL_READY": "PHASE6B_MODEL_SEMANTIC_ADJUDICATION_COMPLETE",
        "METHOD_REVIEW_REQUIRED": "PHASE6B_METHOD_REVIEW_REQUIRED",
        "HUMAN_REVIEW_REQUIRED": "PHASE6B_HUMAN_REVIEW_REQUIRED",
    }[classification]
    return {
        "classification": classification,
        "phase6b_status": status,
        "rule_inputs": {
            "any_model_has_primary_metric_advantage": primary,
            "any_model_has_stable_temporal_advantage": stable,
            "any_model_ready_for_locked_test": ready,
            "evidence_indicates_leakage": leakage,
            "metrics_misaligned_with_goal": misaligned,
            "primary_failure_source": defect,
        },
        "rules": [
            {
                "result": "CANDIDATE_EVIDENCE_PRESENT",
                "when": "primary >= 0.70 and stable >= 0.70 and ready >= 0.70",
            },
            {"result": "NO_TESTED_MODEL_READY", "when": "ready <= 0.30"},
            {
                "result": "METHOD_REVIEW_REQUIRED",
                "when": "leakage >= 0.70 or metrics_misaligned >= 0.70 or primary_failure_source == MATERIAL_METHOD_DEFECT",
            },
            {"result": "HUMAN_REVIEW_REQUIRED", "when": "no prior rule matches"},
        ],
        "authority_note": "Computed locally from the supplied thresholds; JEV was not asked to select a project status.",
    }


def _previous_phase6_status() -> str:
    # Read only after all Phase 6B JEV requests have completed.
    prior = _read_json("reports/phase6_jev_adjudication.json")
    status = prior.get("status")
    if not isinstance(status, str) or not status:
        raise Phase6BError("PreviousPhase6StatusUnavailable")
    return status


def _render_markdown(
    results: dict[str, dict[str, Any]],
    aggregation: dict[str, Any],
    previous_status: str,
    validation: dict[str, Any],
) -> str:
    lines = [
        "# Phase 6B Model-Specific JEV Review",
        "",
        "Status: " + aggregation["phase6b_status"],
        "",
        "Local evidence classification: " + aggregation["classification"],
        "",
        "JEV answered bounded Noul and Choice questions from quantitative development evidence. The final classification above was computed locally using the stated rules.",
        "",
        "## Requests and answers",
        "",
    ]
    for request_id, result in results.items():
        lines.extend(
            [
                "### " + result["title"],
                "",
                "- Request ID: " + request_id,
                "- Returned JEV model: " + result["model_identifier_returned"],
                "- HTTP status: " + str(result["http_status"]),
                "",
            ]
        )
        for question_id, answer in result["answers"].items():
            if answer["type"] == "noul":
                lines.append(
                    "- " + question_id + ": Noul " + format(answer["noul"], ".6f")
                )
            else:
                lines.append(
                    "- " + question_id + ": selected " + answer["choice"]
                )
                lines.append("")
                lines.append("  | Choice | Probability |")
                lines.append("  |---|---:|")
                for choice_id, probability in answer["probabilities"].items():
                    lines.append(
                        "  | " + choice_id + " | " + format(probability, ".6f") + " |"
                    )
                if "confidence" in answer:
                    lines.append(
                        "  | Response confidence | "
                        + format(answer["confidence"], ".6f")
                        + " (response-distribution information only) |"
                    )
            lines.append("")
    lines.extend(
        [
            "## Deterministic aggregation",
            "",
            "- Classification: " + aggregation["classification"],
            "- Phase 6B status: " + aggregation["phase6b_status"],
            "- Full Choice distributions are retained and are not objective correctness probabilities.",
            "",
            "## Previous Phase 6 comparison",
            "",
            "- Previous Phase 6 recorded status: " + previous_status + ".",
            "- Phase 6B sent no Phase 6 verdict, status, or confidence to JEV. This local comparison was added after all JEV requests completed.",
            "",
            "## Locked test and credentials",
            "",
            "- Locked test: SEALED. No target rows were read, scored, or predicted.",
            "- Credential value and Authorization header were not recorded. Request, response, and output echo checks passed.",
            "- Keys.env was verified ignored and untracked. Only TYPESAFE_API_KEY was loaded into process memory for the requests.",
            "",
            "## Validation",
            "",
        ]
    )
    for name, value in validation.items():
        lines.append("- " + name + ": " + str(value))
    lines.extend(["", "## Files", ""])
    for name, relative in OUTPUTS.items():
        if name != "review":
            lines.append("- reports/" + relative)
    lines.extend(["- scripts/phase6b_model_semantic_jev.py", ""])
    return "\n".join(lines)


def _record_for_output(
    request_ids: tuple[str, ...],
    results: dict[str, dict[str, Any]],
    phase6b_status: str,
) -> dict[str, Any]:
    return {
        "schema_version": "phase6b-typed-model-evidence/v1",
        "phase": PHASE,
        "phase6b_status": phase6b_status,
        "requests": [results[request_id] for request_id in request_ids],
    }


def _write_outputs(
    results: dict[str, dict[str, Any]],
    aggregation: dict[str, Any],
    previous_status: str,
    api_key: str,
) -> None:
    status = aggregation["phase6b_status"]
    summary = {
        "schema_version": "phase6b-model-semantic-summary/v1",
        "phase": PHASE,
        "phase6b_status": status,
        "request_count": len(results),
        "returned_models_by_request": {
            key: result["model_identifier_returned"] for key, result in results.items()
        },
        "requests": list(results.values()),
        "deterministic_aggregation": aggregation,
        "previous_phase6_comparison": {
            "previous_phase6_status": previous_status,
            "phase6b_classification": aggregation["classification"],
            "jev_was_not_asked_to_compare_statuses": True,
        },
        "locked_test": {
            "status": "SEALED",
            "target_rows_read": False,
            "scores_calculated": False,
            "predictions_generated": False,
        },
        "credential_safety": {
            "credential_value_recorded": False,
            "authorization_header_recorded": False,
            "credential_echo_check": "PASS",
            "keys_env_ignored": True,
            "keys_env_tracked": False,
        },
    }
    validation = {
        "request_count": len(results),
        "typed_answer_ids": "PASS",
        "noul_bounds": "PASS",
        "choice_distributions": "PASS",
        "prior_phase6_not_in_request_states": "PASS",
        "locked_test_boundary": "PASS",
        "credential_echo_checks": "PASS",
    }
    summary["validation"] = validation
    documents: dict[str, Any] = {
        OUTPUTS["3d_semantic"]: _record_for_output(("3d_semantic",), results, status),
        OUTPUTS["3d_model_evidence"]: _record_for_output(("3d_predictive",), results, status),
        OUTPUTS["642_semantic"]: _record_for_output(("642_semantic",), results, status),
        OUTPUTS["642_model_evidence"]: _record_for_output(
            ("642_logistic", "642_random_forest", "642_shrinkage"), results, status
        ),
        OUTPUTS["information_signal"]: _record_for_output(
            ("information_signal",), results, status
        ),
        OUTPUTS["summary"]: summary,
        OUTPUTS["review"]: _render_markdown(results, aggregation, previous_status, validation),
    }
    serialized = {}
    for name, value in documents.items():
        raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        if api_key in raw or "Bearer " in raw:
            raise Phase6BError("CredentialOutputBlocked")
        serialized[name] = raw
    output_dir = ROOT / "reports"
    if any((output_dir / name).exists() for name in serialized):
        raise Phase6BError("OutputAlreadyExists")
    temporary = []
    try:
        for name, raw in serialized.items():
            path = output_dir / name
            temp_path = path.with_name(path.name + ".phase6b-tmp")
            if temp_path.exists():
                raise Phase6BError("TemporaryOutputExists")
            temp_path.write_text(raw, encoding="utf-8", newline="\n")
            temporary.append((temp_path, path))
        for temp_path, path in temporary:
            temp_path.replace(path)
    except (OSError, Phase6BError):
        for temp_path, _ in temporary:
            temp_path.unlink(missing_ok=True)
        raise
    for path in (output_dir / name for name in serialized):
        raw = path.read_text(encoding="utf-8")
        if api_key in raw or "Bearer " in raw:
            raise Phase6BError("CredentialOutputDetected")


def _self_check() -> None:
    choice = {
        "type": "choice",
        "choice": "A",
        "probabilities": {"A": 0.25, "B": 0.75},
        "confidence": 0.8,
    }
    normalized = _normalise_answer(
        choice, {"type": "choice", "choices": {"A": "first", "B": "second"}}
    )
    assert normalized["probabilities"] == {"A": 0.25, "B": 0.75}
    assert normalized["confidence_note"] == "reported response-distribution information only"
    assert _normalise_answer(
        {"type": "noul", "noul": 0.5}, {"type": "noul"}
    )["noul"] == 0.5
    try:
        _normalise_answer(
            {
                "type": "choice",
                "choice": "A",
                "probabilities": {"A": 0.2, "B": 0.2},
            },
            {"type": "choice", "choices": {"A": "first", "B": "second"}},
        )
    except Phase6BError as error:
        assert error.error_code == "ChoiceDistributionInvalid"
    else:
        raise AssertionError("invalid Choice distribution passed")


def _validate_existing_outputs(api_key: str) -> None:
    for name in OUTPUTS.values():
        path = ROOT / "reports" / name
        if not path.is_file():
            raise Phase6BError("OutputMissing")
        raw = path.read_text(encoding="utf-8")
        if api_key in raw or "Bearer " in raw:
            raise Phase6BError("CredentialOutputDetected")
        if path.suffix == ".json" and not isinstance(json.loads(raw), dict):
            raise Phase6BError("OutputJSONShapeInvalid")
    print("PHASE6B_OUTPUT_VALIDATION_PASS")


def _run(validate_only: bool, validate_outputs: bool) -> int:
    try:
        if validate_outputs:
            _validate_existing_outputs(_load_api_key())
            return 0
        bundle = _build_bundle()
        states = _request_states(bundle)
        _validate_bundle(states)
        _self_check()
        if validate_only:
            print(
                "PHASE6B_PREFLIGHT_PASS requests="
                + str(len(REQUEST_SPECS))
                + " questions="
                + str(sum(len(spec["questions"]) for spec in REQUEST_SPECS))
                + " typed=noul,choice outputs_absent=true locked_test_rows_read=false"
            )
            return 0
        api_key = _load_api_key()
        results = {}
        for index, spec in enumerate(REQUEST_SPECS, start=1):
            result = _request_result(spec, states[spec["id"]], api_key)
            results[spec["id"]] = result
            print(
                "PHASE6B_REQUEST_PASS "
                + str(index)
                + "/"
                + str(len(REQUEST_SPECS))
                + " id="
                + spec["id"]
                + " model="
                + result["model_identifier_returned"]
            )
        aggregation = _aggregate(results)
        previous_status = _previous_phase6_status()
        _write_outputs(results, aggregation, previous_status, api_key)
        print(
            "PHASE6B_RUN_PASS requests="
            + str(len(results))
            + " classification="
            + aggregation["classification"]
            + " status="
            + aggregation["phase6b_status"]
        )
        return 0
    except jev_client.JevClientError as error:
        print(
            "PHASE6B_BLOCKED error="
            + error.error_class
            + " http_status="
            + str(error.http_status)
        )
        return 2
    except Phase6BError as error:
        status = "PHASE6B_BLOCKED"
        if error.error_code in {
            "TypedAnswerInvalid",
            "TypedNoulInvalid",
            "TypedChoiceInvalid",
            "ChoiceDistributionInvalid",
            "ChoiceConfidenceInvalid",
            "AnswerIdsInvalid",
        }:
            status = "PHASE6B_VALIDATION_FAILED"
        print(
            status
            + " error="
            + error.error_code
            + " http_status="
            + str(error.http_status)
        )
        return 2
    except (OSError, json.JSONDecodeError, UnicodeError, AssertionError) as error:
        print("PHASE6B_VALIDATION_FAILED error=" + type(error).__name__)
        return 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--validate-outputs", action="store_true")
    args = parser.parse_args()
    return _run(args.validate_only, args.validate_outputs)


if __name__ == "__main__":
    raise SystemExit(main())
