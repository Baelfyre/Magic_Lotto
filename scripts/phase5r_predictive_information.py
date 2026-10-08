# @codebase_provenance_JEO
"""Leakage-bounded Phase 5R information and combination probability analysis."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SEED = 162
PERMUTATIONS = 10_000
BOOTSTRAPS = 10_000
MC_INITIAL = 10_000
MC_CONFIRMATION = 100_000
ALPHA = 0.05
SHRINKAGE_STRENGTHS = (10.0, 100.0, 1000.0)
TRAIN_ONLY_BURN_IN = 100
ROLLING_WINDOW = 250
ROLLING_STRIDE = 100
CHANGE_MIN_SEGMENT = 200
CHANGE_STRIDE = 25

EXPECTED_SPLITS = {
    "3d_lotto": {
        "train": (2170, "2016-04-16", "2022-10-03", "103", "2283"),
        "validation": (723, "2022-10-04", "2024-10-07", "2284", "3006"),
        "test": (724, "2024-10-08", "2026-10-07", "3007", "3730"),
    },
    "lotto_6_42": {
        "train": (902, "2016-08-30", "2022-11-12", "103", "1008"),
        "validation": (300, "2022-11-15", "2024-10-22", "1009", "1308"),
        "test": (302, "2024-10-24", "2026-10-06", "1309", "1610"),
    },
}

EXPECTED_PREEXISTING_UNTRACKED = {
    "__pycache__/monte_carlo_baseline.cpython-312.pyc",
    "data/features/3d_features.csv",
    "data/features/3d_targets.csv",
    "data/features/642_features.csv",
    "data/features/642_targets.csv",
    "data/features/chronological_splits.json",
    "data/features/feature_dictionary.json",
    "models/phase5a_model_config.json",
    "monte_carlo_baseline.py",
    "notebooks/lotto_phase4_feature_engineering.ipynb",
    "notebooks/lotto_phase5a_ml_validation.ipynb",
    "notebooks/lotto_statistical_analysis.ipynb",
    "phase3_monte_carlo_random_baseline.md",
    "phase3_monte_carlo_results.json",
    "phase3_simulation_distributions.csv",
    "reports/phase4_feature_engineering.md",
    "reports/phase4_validation.json",
    "reports/phase5a_metrics.json",
    "reports/phase5a_ml_validation.md",
    "reports/phase5a_random_baseline_distributions.csv",
    "reports/phase5a_validation.json",
    "reports/phase5a_validation_predictions/3d_validation_predictions.csv",
    "reports/phase5a_validation_predictions/642_validation_predictions.csv",
    "scripts/phase4_feature_engineering.py",
    "scripts/phase5a_ml_validation.py",
}

PHASE5R_PATHS = {
    "scripts/phase5r_predictive_information.py",
    "reports/phase5r_information_tests.csv",
    "reports/phase5r_information_permutations.csv",
    "reports/phase5r_temporal_dependence.csv",
    "reports/phase5r_stationarity.csv",
    "reports/phase5r_bayesian_shrinkage.csv",
    "reports/phase5r_combination_probability_metrics.csv",
    "reports/phase5r_evidence.json",
    "reports/phase5r_predictive_information.md",
    "notebooks/lotto_phase5r_predictive_information.ipynb",
}

PRIOR_PHASE_FILES = [
    "6-42.csv",
    "lotto_6_42_cleaned_normalized.csv",
    "lotto_6_42_number_frequency.csv",
    "lotto_6_42_phase2_analysis.csv",
    "lotto_data_cleaning_report.md",
    "phase2_randomness_diagnostics.md",
    "swertres_9pm_analysis_ready.csv",
    "swertres_9pm_cleaned_normalized.csv",
    "swertres_9pm_digit_frequency.csv",
    "swertres_9pm_phase2_analysis.csv",
    "swertres9pm.md",
    "monte_carlo_baseline.py",
    "phase3_monte_carlo_random_baseline.md",
    "phase3_monte_carlo_results.json",
    "phase3_simulation_distributions.csv",
    "notebooks/lotto_statistical_analysis.ipynb",
    "scripts/phase4_feature_engineering.py",
    "data/features/3d_features.csv",
    "data/features/3d_targets.csv",
    "data/features/642_features.csv",
    "data/features/642_targets.csv",
    "data/features/chronological_splits.json",
    "data/features/feature_dictionary.json",
    "reports/phase4_validation.json",
    "reports/phase4_feature_engineering.md",
    "notebooks/lotto_phase4_feature_engineering.ipynb",
    "scripts/phase5a_ml_validation.py",
    "models/phase5a_model_config.json",
    "reports/phase5a_metrics.json",
    "reports/phase5a_random_baseline_distributions.csv",
    "reports/phase5a_validation_predictions/3d_validation_predictions.csv",
    "reports/phase5a_validation_predictions/642_validation_predictions.csv",
    "reports/phase5a_validation.json",
    "reports/phase5a_ml_validation.md",
    "notebooks/lotto_phase5a_ml_validation.ipynb",
]


class Phase5RError(RuntimeError):
    """Raised when a Phase 5R precondition or validation fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5RError(message)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def status_paths() -> tuple[list[str], list[str]]:
    result = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    require(result.returncode == 0, "BLOCKED: Git status could not be read")
    raw = result.stdout.split("\0")
    statuses: list[str] = []
    paths: list[str] = []
    for item in raw:
        if not item:
            continue
        statuses.append(item[:2])
        paths.append(item[3:].replace("\\", "/"))
    return statuses, paths


def verify_prior_phase_state() -> tuple[dict[str, Any], dict[str, str]]:
    top = git("rev-parse", "--show-toplevel")
    require(top.returncode == 0, "BLOCKED: repository is not a Git worktree")
    require(Path(top.stdout.strip()).resolve() == ROOT.resolve(), "BLOCKED: unexpected Git root")
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    remotes = git("remote")
    require(branch.returncode == head.returncode == remotes.returncode == 0, "BLOCKED: Git metadata unavailable")
    require(branch.stdout.strip() and len(head.stdout.strip()) == 40, "BLOCKED: branch or HEAD unavailable")
    require(git("diff", "--quiet").returncode == 0, "BLOCKED: tracked worktree has changes")
    require(git("diff", "--cached", "--quiet").returncode == 0, "BLOCKED: Git index is not clean")

    tracked_keys = git("ls-files", "--error-unmatch", "--", "Keys.env")
    ignored_keys = git("check-ignore", "-q", "--", "Keys.env")
    require(ignored_keys.returncode == 0, "BLOCKED: Keys.env is not ignored by Git")
    require(tracked_keys.returncode != 0, "BLOCKED_SECRET_TRACKED: Keys.env is tracked")

    statuses, paths = status_paths()
    require(all(status == "??" for status in statuses), "BLOCKED: tracked or staged pre-existing changes exist")
    current_prior = set(paths) - PHASE5R_PATHS
    require(current_prior == EXPECTED_PREEXISTING_UNTRACKED,
            f"BLOCKED: pre-existing untracked state differs: {sorted(current_prior ^ EXPECTED_PREEXISTING_UNTRACKED)}")

    required_files = {path for path in PRIOR_PHASE_FILES if path != "__pycache__/monte_carlo_baseline.cpython-312.pyc"}
    missing = sorted(path for path in required_files if not (ROOT / path).is_file())
    require(not missing, f"BLOCKED: canonical Phase 1 through Phase 5A artifacts missing: {missing}")

    p3 = read_json(ROOT / "phase3_monte_carlo_results.json")
    p4 = read_json(ROOT / "reports/phase4_validation.json")
    p5a = read_json(ROOT / "reports/phase5a_validation.json")
    require(p3.get("verdict") == "PHASE3_PASS_RANDOM_COMPATIBLE", "BLOCKED: Phase 3 verdict changed")
    p3_validation = p3.get("validation", {})
    require(
        p3_validation.get("canonical_input_structure") == "PASS"
        and p3_validation.get("phase2_feature_consistency") == "PASS"
        and str(p3_validation.get("seeded_full_rerun_artifact_hash_check", "")).startswith("PASS:")
        and p3_validation.get("jev_or_typesafe_called") is False
        and p3_validation.get("keys_env_contents_read") is False,
        "BLOCKED: Phase 3 canonical validation evidence is incomplete",
    )
    require(p4.get("verdict") == "PHASE4_PASS_READY_FOR_ML_BASELINE", "BLOCKED: Phase 4 verdict changed")
    p4_checks = p4.get("validation_checks", {})
    require(
        p4_checks.get("chronological_splits") == "PASS"
        and p4_checks.get("feature_target_key_alignment") == "PASS"
        and p4_checks.get("target_invariants_3d") == "PASS"
        and p4_checks.get("target_invariants_6_42") == "PASS"
        and p4_checks.get("temporal_leakage_audits") == "PASS"
        and p4_checks.get("test_performance_calculated") is False
        and p4_checks.get("jev_or_typesafe_called") is False,
        "BLOCKED: Phase 4 structural, leakage, or locked-test evidence is incomplete",
    )
    require(p5a.get("verdict") == "PHASE5A_INCONCLUSIVE", "BLOCKED: Phase 5A verdict changed")
    contamination = p5a.get("test_contamination_audit", {})
    require(
        contamination.get("all_checks_pass") is True
        and contamination.get("test_target_values_loaded") is False
        and contamination.get("test_targets_used_for_fit") is False
        and contamination.get("test_targets_used_for_selection") is False
        and contamination.get("test_metrics_calculated") is False
        and contamination.get("test_target_dependent_visualization") is False
        and contamination.get("phase4_boundaries_preserved") is True,
        "BLOCKED: Phase 5A locked-test audit is not clean",
    )
    security = p5a.get("security", {})
    require(
        security.get("keys_env_ignored") is True
        and security.get("keys_env_tracked") is False
        and security.get("keys_env_contents_read") is False
        and security.get("jev_invoked") is False
        and security.get("typesafe_invoked") is False,
        "BLOCKED: Phase 5A security evidence is incomplete",
    )
    p5a_preflight = p5a.get("preflight", {})
    require(
        p5a_preflight.get("phase1_to_phase3_snapshot_hashes_match") is True
        and p5a_preflight.get("phase4_output_hashes_match") is True
        and p5a_preflight.get("phase2_canonical_hashes_match") is True
        and p5a_preflight.get("split_boundaries_match_manifest") is True,
        "BLOCKED: Phase 5A canonical Phase 1 through Phase 4 chain verification is incomplete",
    )

    split = read_json(ROOT / "data/features/chronological_splits.json")
    require(split.get("test_partition_locked") is True and split.get("shuffle") is False,
            "BLOCKED: split manifest is not a locked chronological split")
    for game, partitions in EXPECTED_SPLITS.items():
        observed = split.get("games", {}).get(game, {}).get("partitions", {})
        for part, (count, start, end, first_source, last_source) in partitions.items():
            metadata = observed.get(part, {})
            require(metadata.get("row_count") == count
                    and metadata.get("start_date") == start
                    and metadata.get("end_date") == end
                    and metadata.get("first_record_key", {}).get("source_row") == first_source
                    and metadata.get("last_record_key", {}).get("source_row") == last_source,
                    f"BLOCKED: Phase 4 {game} {part} boundary changed")

    dictionary = read_json(ROOT / "data/features/feature_dictionary.json")
    global_temporal_rule = dictionary.get("global_temporal_rule", "").casefold()
    require("target" in global_temporal_rule and ("prior" in global_temporal_rule or "less than" in global_temporal_rule),
            "BLOCKED: Phase 4 global feature temporal rule is missing")
    for game in ("3d_lotto", "lotto_6_42"):
        entries = dictionary.get(game, {}).get("features", {})
        require(bool(entries), f"BLOCKED: Phase 4 {game} feature dictionary is missing")
        require(all("strictly prior" in entry.get("temporal_rule", "") for entry in entries.values()),
                f"BLOCKED: Phase 4 {game} feature temporal audit failed")

    recorded_p5a_hashes = p5a.get("artifact_hashes", {})
    require(bool(recorded_p5a_hashes), "BLOCKED: Phase 5A saved artifact hashes missing")
    for relative_path, expected_hash in recorded_p5a_hashes.items():
        path = ROOT / relative_path
        require(path.is_file() and sha256_file(path) == expected_hash,
                f"BLOCKED: Phase 5A canonical artifact hash mismatch: {relative_path}")

    prior_hashes = {relative_path: sha256_file(ROOT / relative_path) for relative_path in PRIOR_PHASE_FILES}
    state = {
        "repository": str(ROOT.resolve()),
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "configured_remotes": [value for value in remotes.stdout.splitlines() if value],
        "tracked_worktree_clean": True,
        "index_clean": True,
        "pre_modification_status": sorted(paths),
        "preexisting_untracked_matches_phase5a_scope": True,
        "keys_env_ignored": True,
        "keys_env_tracked": False,
        "keys_env_contents_read": False,
        "phase3_verdict": p3["verdict"],
        "phase4_verdict": p4["verdict"],
        "phase5a_verdict": p5a["verdict"],
        "phase5a_test_contamination_audit_passed": True,
        "phase4_split_boundaries_unchanged": True,
        "locked_test_metadata_only": {
            game: {
                "row_count": EXPECTED_SPLITS[game]["test"][0],
                "start_date": EXPECTED_SPLITS[game]["test"][1],
                "end_date": EXPECTED_SPLITS[game]["test"][2],
            }
            for game in EXPECTED_SPLITS
        },
        "phase5a_artifact_hashes_match": True,
    }
    return state, prior_hashes


def csv_prefix(path: Path, row_count: int) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        rows = list(itertools.islice(reader, row_count))
    require(len(rows) == row_count, f"BLOCKED: {path.relative_to(ROOT)} has fewer than {row_count} development rows")
    return headers, rows


def parse_numeric_rows(rows: list[dict[str, str]], columns: list[str]) -> np.ndarray:
    result = np.empty((len(rows), len(columns)), dtype=np.float64)
    for row_index, row in enumerate(rows):
        for column_index, name in enumerate(columns):
            raw = row[name]
            result[row_index, column_index] = np.nan if raw == "" else float(raw)
    return result


def load_development_data() -> dict[str, dict[str, Any]]:
    split = read_json(ROOT / "data/features/chronological_splits.json")
    loaded: dict[str, dict[str, Any]] = {}
    for game, partitions in EXPECTED_SPLITS.items():
        train_n = partitions["train"][0]
        validation_n = partitions["validation"][0]
        dev_n = train_n + validation_n
        feature_path = ROOT / ("data/features/3d_features.csv" if game == "3d_lotto" else "data/features/642_features.csv")
        target_path = ROOT / ("data/features/3d_targets.csv" if game == "3d_lotto" else "data/features/642_targets.csv")
        feature_headers, feature_rows = csv_prefix(feature_path, dev_n)
        target_headers, target_rows = csv_prefix(target_path, dev_n)
        require(feature_headers[:2] == ["draw_date", "source_row"]
                and target_headers[:2] == ["draw_date", "source_row"],
                f"BLOCKED: {game} row-key schema changed")
        feature_names = feature_headers[2:]
        target_names = target_headers[2:]
        require(len(set(feature_names)) == len(feature_names), f"BLOCKED: {game} feature columns duplicate")
        require(len(set(target_names)) == len(target_names), f"BLOCKED: {game} target columns duplicate")
        require(not set(feature_names) & set(target_names), f"BLOCKED: {game} target columns appear in feature matrix")
        fkeys = [(row["draw_date"], row["source_row"]) for row in feature_rows]
        tkeys = [(row["draw_date"], row["source_row"]) for row in target_rows]
        require(fkeys == tkeys, f"BLOCKED: {game} feature/target development keys are misaligned")
        require(len(set(fkeys)) == len(fkeys), f"BLOCKED: {game} duplicate development row key")
        require(fkeys == sorted(fkeys, key=lambda item: (item[0], int(item[1]))),
                f"BLOCKED: {game} development rows are not chronological")
        manifest = split["games"][game]["partitions"]
        require(fkeys[0] == (manifest["train"]["first_record_key"]["draw_date"], manifest["train"]["first_record_key"]["source_row"])
                and fkeys[train_n - 1] == (manifest["train"]["last_record_key"]["draw_date"], manifest["train"]["last_record_key"]["source_row"])
                and fkeys[train_n] == (manifest["validation"]["first_record_key"]["draw_date"], manifest["validation"]["first_record_key"]["source_row"])
                and fkeys[-1] == (manifest["validation"]["last_record_key"]["draw_date"], manifest["validation"]["last_record_key"]["source_row"]),
                f"BLOCKED: {game} train/validation row boundary differs from the manifest")

        y = np.asarray([[int(row[name]) for name in target_names] for row in target_rows], dtype=np.int16)
        require(np.all(np.isfinite(y)), f"BLOCKED: {game} development target is non-finite")
        if game == "3d_lotto":
            require(y.shape[1] == 10 and np.all((y >= 0) & (y <= 3)) and np.all(y.sum(axis=1) == 3),
                    "BLOCKED: 3D development targets are not unordered three-digit multisets")
            require(target_names == [f"target_digit_{d}" for d in range(10)], "BLOCKED: 3D target order changed")
        else:
            require(y.shape[1] == 42 and np.all((y == 0) | (y == 1)) and np.all(y.sum(axis=1) == 6),
                    "BLOCKED: 6/42 development targets are not six-distinct-number sets")
            require(target_names == [f"target_{n:02d}" for n in range(1, 43)], "BLOCKED: 6/42 target order changed")

        x = parse_numeric_rows(feature_rows, feature_names)
        require(np.all(np.isfinite(x) | np.isnan(x)), f"BLOCKED: {game} features contain invalid numeric values")
        index = {name: i for i, name in enumerate(feature_names)}
        expected_columns = (
            [f"digit_{d}_{suffix}" for d in range(10) for suffix in
             ([f"count_prev_{w}" for w in (10, 30, 100)] + ["expanding_count", "freq_expanding", "gap_since_seen", "count_prev_draw", "freq_deviation_prev_100"])]
            if game == "3d_lotto" else
            [f"num_{n:02d}_{suffix}" for n in range(1, 43) for suffix in
             ([f"count_prev_{w}" for w in (10, 30, 100)] + ["expanding_count", "freq_expanding", "gap_since_seen", "seen_prev_draw", "freq_deviation_prev_100"])]
        )
        require(all(name in index for name in expected_columns), f"BLOCKED: {game} Phase 4 feature families are incomplete")

        loaded[game] = {
            "train_n": train_n,
            "validation_n": validation_n,
            "dev_n": dev_n,
            "features": x,
            "feature_names": feature_names,
            "feature_index": index,
            "targets": y,
            "dates": [row["draw_date"] for row in target_rows],
            "source_rows": [row["source_row"] for row in target_rows],
            "dev_read_rows": dev_n,
            "locked_test_rows_parsed": 0,
            "partition_metadata": {
                name: {
                    "row_count": partitions[name][0],
                    "start_date": partitions[name][1],
                    "end_date": partitions[name][2],
                }
                for name in ("train", "validation", "test")
            },
        }
    return loaded


def feature_column(data: dict[str, Any], name: str) -> np.ndarray:
    return data["features"][:, data["feature_index"][name]]


def family_arrays(y: np.ndarray, game: str) -> dict[str, Any]:
    n, candidates = y.shape
    require(n > TRAIN_ONLY_BURN_IN, f"BLOCKED: {game} training data is too short for 100-draw burn-in")
    times = np.arange(TRAIN_ONLY_BURN_IN, n)
    cumulative = np.vstack([np.zeros((1, candidates), dtype=np.float64), np.cumsum(y, axis=0, dtype=np.float64)])
    groups: dict[str, Any] = {}
    for window in (10, 30, 100):
        groups[f"previous_{window}_frequency"] = cumulative[times] - cumulative[times - window]
    prior_counts = cumulative[times]
    groups["expanding_historical_frequency"] = prior_counts / prior_counts.sum(axis=1, keepdims=True)

    last_seen = np.maximum.accumulate(
        np.where(y > 0, np.arange(n, dtype=np.int32)[:, None], -1), axis=0
    )
    prior_last = last_seen[times - 1]
    gaps = times[:, None] - 1 - prior_last
    gaps = np.where(prior_last < 0, times[:, None] + 1, gaps)
    groups["gap_since_seen"] = gaps.astype(np.float64)
    groups["previous_draw_appearance"] = (y[times - 1] > 0).astype(np.float64)
    fair = 0.1 if game == "3d_lotto" else 6.0 / 42.0
    units_per_draw = 3.0 if game == "3d_lotto" else 6.0
    groups["previous_100_frequency_deviation"] = (
        (cumulative[times] - cumulative[times - 100]) / (100.0 * units_per_draw) - fair
    )

    digit_values = np.arange(10, dtype=np.float64) if game == "3d_lotto" else np.arange(1, 43, dtype=np.float64)
    draw_sum = y @ digit_values
    previous_sum = draw_sum[times - 1]
    sum_cumulative = np.r_[0.0, np.cumsum(draw_sum)]
    mean_prev30 = (sum_cumulative[times] - sum_cumulative[times - 30]) / 30.0
    overlap = np.zeros(n, dtype=np.float64)
    overlap[1:] = np.minimum(y[1:], y[:-1]).sum(axis=1)
    if game == "3d_lotto":
        distinct = np.count_nonzero(y, axis=1)
        max_count = y.max(axis=1)
        pattern = np.where(distinct == 3, 0, np.where(max_count == 3, 2, 1))
        context = np.column_stack([
            previous_sum,
            mean_prev30,
            (pattern[times - 1] == 1).astype(np.float64),
            (pattern[times - 1] == 2).astype(np.float64),
            overlap[times - 1],
        ])
        context_names = ["previous_draw_sum", "mean_sum_prev_30", "previous_pattern_one_pair", "previous_pattern_triple", "previous_multiset_overlap"]
    else:
        odd_count = y @ (digit_values.astype(int) % 2)
        context = np.column_stack([
            previous_sum,
            mean_prev30,
            odd_count[times - 1],
            overlap[times - 1],
        ]).astype(np.float64)
        context_names = ["previous_draw_sum", "mean_sum_prev_30", "previous_draw_odd_count", "previous_set_overlap"]
    groups["context"] = {name: context[:, i] for i, name in enumerate(context_names)}
    groups["target"] = y[times]
    groups["times"] = times
    return groups


def quantile_edges(values: np.ndarray) -> list[np.ndarray]:
    edges: list[np.ndarray] = []
    for column in range(values.shape[1]):
        x = values[:, column]
        x = x[np.isfinite(x)]
        if not len(x):
            edges.append(np.array([], dtype=np.float64))
        else:
            edges.append(np.unique(np.quantile(x, [0.2, 0.4, 0.6, 0.8])))
    return edges


def bin_matrix(values: np.ndarray, edges: list[np.ndarray]) -> np.ndarray:
    binned = np.empty(values.shape, dtype=np.int8)
    for column, cuts in enumerate(edges):
        col = np.nan_to_num(values[:, column], nan=float(np.nanmax(values[:, column][np.isfinite(values[:, column])]) + 1) if np.any(np.isfinite(values[:, column])) else 1.0)
        binned[:, column] = np.searchsorted(cuts, col, side="right").astype(np.int8)
    return binned


def mutual_information(bins: np.ndarray, target: np.ndarray, categories: int) -> float:
    n, candidates = target.shape
    require(bins.shape == target.shape and n > 0, "FAILED: MI inputs are not aligned")
    candidates_idx = np.broadcast_to(np.arange(candidates, dtype=np.int32), (n, candidates))
    code = (bins.astype(np.int32) * candidates + candidates_idx) * categories + target.astype(np.int32)
    counts = np.bincount(code.ravel(), minlength=5 * candidates * categories).reshape(5, candidates, categories)
    px_y = counts / float(n)
    px = px_y.sum(axis=2, keepdims=True)
    py = px_y.sum(axis=0, keepdims=True)
    denominator = px * py
    valid = (px_y > 0) & (denominator > 0)
    terms = np.zeros_like(px_y)
    terms[valid] = px_y[valid] * np.log(px_y[valid] / denominator[valid])
    candidate_mi = terms.sum(axis=(0, 2))
    return float(candidate_mi.mean())


def information_permutations(game: str, y_train: np.ndarray, rng: np.random.Generator) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    observed = family_arrays(y_train, game)
    target_count = observed["target"].astype(np.int8)
    target_present = (target_count > 0).astype(np.int8)
    test_defs: list[tuple[str, str, list[str]]] = []
    simple_groups = [
        "previous_10_frequency", "previous_30_frequency", "previous_100_frequency",
        "expanding_historical_frequency", "gap_since_seen", "previous_draw_appearance",
        "previous_100_frequency_deviation",
    ]
    features_by_group: dict[str, Any] = {name: observed[name] for name in simple_groups}
    edges_by_group = {name: quantile_edges(values) for name, values in features_by_group.items()}
    context_edges: dict[str, np.ndarray] = {}
    for name, values in observed["context"].items():
        context_edges[name] = np.unique(np.quantile(values, [0.2, 0.4, 0.6, 0.8]))
    context_names = list(observed["context"])
    for group in simple_groups:
        test_defs.append((group, "multiplicity_count" if game == "3d_lotto" else "membership", []))
        if game == "3d_lotto":
            test_defs.append((group, "membership", []))
    test_defs.append(("approved_draw_context", "multiplicity_count" if game == "3d_lotto" else "membership", context_names))
    if game == "3d_lotto":
        test_defs.append(("approved_draw_context", "membership", context_names))

    observed_stats: list[float] = []
    targets_by_measure = {"multiplicity_count": target_count, "membership": target_present}
    for family, measure, context_members in test_defs:
        y = targets_by_measure[measure]
        if family == "approved_draw_context":
            values = observed["context"]
            scores = []
            for name in context_members:
                x = values[name]
                cuts = context_edges[name]
                b = np.broadcast_to(np.searchsorted(cuts, x, side="right")[:, None], y.shape)
                scores.append(mutual_information(b, y, 4 if measure == "multiplicity_count" else 2))
            observed_stats.append(max(scores))
        else:
            b = bin_matrix(features_by_group[family], edges_by_group[family])
            observed_stats.append(mutual_information(b, y, 4 if measure == "multiplicity_count" else 2))

    null = np.empty((PERMUTATIONS, len(test_defs)), dtype=np.float64)
    for permutation_index in range(PERMUTATIONS):
        if permutation_index and permutation_index % 2500 == 0:
            print(f"[phase5r] {game} information permutations {permutation_index:,}/{PERMUTATIONS:,}", flush=True)
        permuted = y_train[rng.permutation(len(y_train))]
        generated = family_arrays(permuted, game)
        targets = {
            "multiplicity_count": generated["target"].astype(np.int8),
            "membership": (generated["target"] > 0).astype(np.int8),
        }
        for test_index, (family, measure, context_members) in enumerate(test_defs):
            target = targets[measure]
            categories = 4 if measure == "multiplicity_count" else 2
            if family == "approved_draw_context":
                values = generated["context"]
                scores = []
                for name in context_members:
                    b = np.broadcast_to(np.searchsorted(context_edges[name], values[name], side="right")[:, None], target.shape)
                    scores.append(mutual_information(b, target, categories))
                null[permutation_index, test_index] = max(scores)
            else:
                b = bin_matrix(generated[family], edges_by_group[family])
                null[permutation_index, test_index] = mutual_information(b, target, categories)

    p_values = (1 + np.sum(null >= np.asarray(observed_stats)[None, :], axis=0)) / (PERMUTATIONS + 1)
    q_values = benjamini_hochberg(p_values)
    results = []
    permutation_rows = []
    for i, (family, measure, _) in enumerate(test_defs):
        results.append({
            "game": game,
            "diagnostic_family": family,
            "target_measure": measure,
            "observed_mutual_information_nats_per_candidate": float(observed_stats[i]),
            "permutations": PERMUTATIONS,
            "empirical_p_add_one": float(p_values[i]),
            "bh_q_within_game": float(q_values[i]),
            "null_mean": float(null[:, i].mean()),
            "null_95_percentile": float(np.quantile(null[:, i], 0.95)),
            "complete_draw_rows_permuted": True,
            "permutation_features_recomputed_from_prior_rows": True,
            "train_only": True,
        })
        permutation_rows.extend({
            "game": game,
            "diagnostic_family": family,
            "target_measure": measure,
            "permutation_index": j + 1,
            "mutual_information_nats_per_candidate": float(null[j, i]),
        } for j in range(PERMUTATIONS))
    return results, permutation_rows


def benjamini_hochberg(p_values: np.ndarray | list[float]) -> np.ndarray:
    p = np.asarray(p_values, dtype=np.float64)
    order = np.argsort(p, kind="stable")
    q = np.empty_like(p)
    running = 1.0
    m = len(p)
    for rank_pos in range(m - 1, -1, -1):
        index = order[rank_pos]
        running = min(running, p[index] * m / (rank_pos + 1))
        q[index] = running
    return np.clip(q, 0.0, 1.0)


def cell_state_bins(values: np.ndarray, binary: bool = False) -> tuple[np.ndarray, list[str]]:
    n, candidates = values.shape
    codes = np.empty((n, candidates), dtype=np.int8)
    labels: set[int] = set()
    if binary:
        codes = (values > 0).astype(np.int8)
        return codes, ["absent", "present"]
    for j in range(candidates):
        column = values[:, j]
        finite = column[np.isfinite(column)]
        if not len(finite):
            codes[:, j] = 0
            continue
        cuts = np.unique(np.quantile(finite, [0.2, 0.4, 0.6, 0.8]))
        filled = np.nan_to_num(column, nan=float(np.max(finite) + 1.0))
        codes[:, j] = np.searchsorted(cuts, filled, side="right")
        labels.update(int(v) for v in np.unique(codes[:, j]))
    return codes, [f"quantile_bin_{v + 1}" for v in sorted(labels)]


def phase4_temporal_groups(game: str, data: dict[str, Any], y: np.ndarray) -> dict[str, np.ndarray]:
    train_n = data["train_n"]
    features = data["features"][:train_n]
    index = data["feature_index"]
    count = 10 if game == "3d_lotto" else 42
    if game == "3d_lotto":
        stems = [f"digit_{d}" for d in range(10)]
        previous_suffix = "count_prev_draw"
    else:
        stems = [f"num_{n:02d}" for n in range(1, 43)]
        previous_suffix = "seen_prev_draw"
    result = {
        "previous_draw_appearance": np.column_stack([
            features[:, index[f"{stem}_{previous_suffix}"]] for stem in stems
        ]),
        "previous_10_frequency": np.column_stack([
            features[:, index[f"{stem}_count_prev_10"]] for stem in stems
        ]),
        "previous_30_frequency": np.column_stack([
            features[:, index[f"{stem}_count_prev_30"]] for stem in stems
        ]),
        "previous_100_frequency": np.column_stack([
            features[:, index[f"{stem}_count_prev_100"]] for stem in stems
        ]),
        "gap_since_seen": np.column_stack([
            features[:, index[f"{stem}_gap_since_seen"]] for stem in stems
        ]),
    }
    require(all(matrix.shape == (train_n, count) for matrix in result.values()),
            f"FAILED: {game} temporal features do not align with train outcomes")
    return result


def temporal_bootstrap(game: str, y: np.ndarray, groups: dict[str, np.ndarray], rng: np.random.Generator) -> list[dict[str, Any]]:
    n, candidates = y.shape
    presence = (y > 0).astype(np.float64)
    column_specs: list[tuple[str, str, np.ndarray, np.ndarray, np.ndarray]] = []
    for group, values in groups.items():
        codes, labels = cell_state_bins(values, binary=(group == "previous_draw_appearance"))
        for category in sorted(np.unique(codes).tolist()):
            mask = (codes == category)
            denom = mask.sum(axis=1).astype(np.float64)
            numer = (mask * presence).sum(axis=1).astype(np.float64)
            counts = (mask * y).sum(axis=1).astype(np.float64)
            state = (("absent", "present")[category] if group == "previous_draw_appearance"
                     else f"quantile_bin_{category + 1}")
            if denom.sum() > 0:
                column_specs.append((group, state, denom, numer, counts))

    den_mat = np.column_stack([spec[2] for spec in column_specs])
    num_mat = np.column_stack([spec[3] for spec in column_specs])
    count_mat = np.column_stack([spec[4] for spec in column_specs])
    draws_present = presence.sum(axis=1)
    boot_delta = np.empty((BOOTSTRAPS, len(column_specs)), dtype=np.float64)
    boot_multiplicity = np.empty_like(boot_delta)
    batch_size = 32
    all_candidates = float(candidates)
    for start in range(0, BOOTSTRAPS, batch_size):
        stop = min(start + batch_size, BOOTSTRAPS)
        indices = rng.integers(0, n, size=(stop - start, n))
        den_sample = np.take(den_mat, indices, axis=0).sum(axis=1)
        num_sample = np.take(num_mat, indices, axis=0).sum(axis=1)
        count_sample = np.take(count_mat, indices, axis=0).sum(axis=1)
        baseline = np.take(draws_present, indices, axis=0).sum(axis=1) / (n * all_candidates)
        rates = np.divide(num_sample, den_sample, out=np.full_like(num_sample, np.nan), where=den_sample > 0)
        means = np.divide(count_sample, den_sample, out=np.full_like(count_sample, np.nan), where=den_sample > 0)
        boot_delta[start:stop] = rates - baseline[:, None]
        boot_multiplicity[start:stop] = means

    output: list[dict[str, Any]] = []
    fair_baseline = 1.0 - (1.0 - 0.1) ** 3 if game == "3d_lotto" else 6.0 / 42.0
    for j, (group, state, denom, numer, counts) in enumerate(column_specs):
        conditional = numer.sum() / denom.sum()
        empirical_baseline = draws_present.sum() / (n * candidates)
        ci = np.nanquantile(boot_delta[:, j], [0.025, 0.975])
        multiplicity_mean = counts.sum() / denom.sum()
        multiplicity_ci = np.nanquantile(boot_multiplicity[:, j], [0.025, 0.975])
        output.append({
            "game": game,
            "feature_group": group,
            "state": state,
            "training_draws": n,
            "candidate_draw_cells": int(denom.sum()),
            "draws_with_state": int(np.count_nonzero(denom)),
            "conditional_presence_rate": float(conditional),
            "unconditional_empirical_presence_rate": float(empirical_baseline),
            "fair_marginal_presence_probability": float(fair_baseline),
            "rate_difference_from_empirical_baseline": float(conditional - empirical_baseline),
            "paired_draw_bootstrap_delta_ci95_low": float(ci[0]),
            "paired_draw_bootstrap_delta_ci95_high": float(ci[1]),
            "conditional_mean_multiplicity": float(multiplicity_mean) if game == "3d_lotto" else None,
            "multiplicity_bootstrap_ci95_low": float(multiplicity_ci[0]) if game == "3d_lotto" else None,
            "multiplicity_bootstrap_ci95_high": float(multiplicity_ci[1]) if game == "3d_lotto" else None,
            "bootstrap_resamples": BOOTSTRAPS,
            "whole_draw_rows_resampled": True,
        })
    return output


def js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    p = np.asarray(p, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    p = p / p.sum()
    q = q / q.sum()
    middle = 0.5 * (p + q)
    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * kl(p, middle) + 0.5 * kl(q, middle)


def change_statistic(values: np.ndarray, minimum: int = CHANGE_MIN_SEGMENT, stride: int = CHANGE_STRIDE) -> tuple[float, int]:
    x = np.asarray(values, dtype=np.float64)
    x = x[np.isfinite(x)]
    n = len(x)
    require(n >= 2 * minimum, "BLOCKED: change-point series is too short for bounded scan")
    cuts = np.arange(minimum, n - minimum + 1, stride, dtype=np.int32)
    if not len(cuts) or cuts[-1] != n - minimum:
        cuts = np.unique(np.r_[cuts, n - minimum])
    cumulative = np.r_[0.0, np.cumsum(x)]
    cumulative_sq = np.r_[0.0, np.cumsum(x * x)]
    n1 = cuts.astype(np.float64)
    n2 = n - n1
    mean1 = cumulative[cuts] / n1
    mean2 = (cumulative[n] - cumulative[cuts]) / n2
    var1 = np.maximum(cumulative_sq[cuts] / n1 - mean1 * mean1, 0.0)
    var2 = np.maximum((cumulative_sq[n] - cumulative_sq[cuts]) / n2 - mean2 * mean2, 0.0)
    z = np.abs(mean1 - mean2) / np.sqrt(np.maximum(var1 / n1 + var2 / n2, 1e-15))
    index = int(np.argmax(z))
    return float(z[index]), int(cuts[index])


def series_summaries(y: np.ndarray, game: str) -> dict[str, np.ndarray]:
    values = np.arange(10) if game == "3d_lotto" else np.arange(1, 43)
    sums = y @ values
    overlap = np.full(len(y), np.nan, dtype=np.float64)
    overlap[1:] = np.minimum(y[1:], y[:-1]).sum(axis=1)
    if game == "3d_lotto":
        distinct = np.count_nonzero(y, axis=1)
        return {
            "draw_sum": sums.astype(np.float64),
            "all_distinct_indicator": (distinct == 3).astype(np.float64),
            "triple_indicator": (y.max(axis=1) == 3).astype(np.float64),
            "previous_draw_overlap": overlap,
        }
    return {
        "draw_sum": sums.astype(np.float64),
        "odd_count": (y @ (values % 2)).astype(np.float64),
        "previous_draw_overlap": overlap,
    }


def stationarity_analysis(game: str, y: np.ndarray, dates: list[str], rng: np.random.Generator) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    n, candidates = y.shape
    rows: list[dict[str, Any]] = []
    start_indices = list(range(0, max(n - ROLLING_WINDOW + 1, 1), ROLLING_STRIDE))
    final_start = max(0, n - ROLLING_WINDOW)
    if final_start not in start_indices:
        start_indices.append(final_start)
    for start in sorted(set(start_indices)):
        end = min(start + ROLLING_WINDOW, n)
        block = y[start:end]
        if game == "3d_lotto":
            counts = block.sum(axis=0).astype(np.float64)
            marginal = counts / counts.sum()
            entropy = -float(np.sum(marginal[marginal > 0] * np.log(marginal[marginal > 0])))
            distinct = np.count_nonzero(block, axis=1)
            pattern = np.where(distinct == 3, "all_distinct", np.where(block.max(axis=1) == 3, "triple", "one_pair"))
            overlap = np.minimum(block[1:], block[:-1]).sum(axis=1) if len(block) > 1 else np.array([np.nan])
            summaries = {
                "marginal_digit_entropy_nats": entropy,
                "marginal_max_absolute_deviation_from_fair": float(np.max(np.abs(marginal - 0.1))),
                "draw_sum_mean": float((block @ np.arange(10)).mean()),
                "pattern_all_distinct_rate": float(np.mean(pattern == "all_distinct")),
                "pattern_one_pair_rate": float(np.mean(pattern == "one_pair")),
                "pattern_triple_rate": float(np.mean(pattern == "triple")),
                "previous_draw_overlap_mean": float(np.nanmean(overlap)),
            }
        else:
            counts = block.sum(axis=0).astype(np.float64)
            marginal = counts / counts.sum()
            entropy = -float(np.sum(marginal[marginal > 0] * np.log(marginal[marginal > 0])))
            numbers = np.arange(1, 43)
            odd = block @ (numbers % 2)
            overlap = np.minimum(block[1:], block[:-1]).sum(axis=1) if len(block) > 1 else np.array([np.nan])
            summaries = {
                "marginal_number_entropy_nats": entropy,
                "marginal_max_absolute_deviation_from_fair": float(np.max(np.abs(counts / len(block) - 6 / 42))),
                "draw_sum_mean": float((block @ numbers).mean()),
                "odd_count_mean": float(odd.mean()),
                "previous_draw_overlap_mean": float(np.nanmean(overlap)),
            }
        for metric, value in summaries.items():
            rows.append({
                "game": game,
                "diagnostic_type": "rolling_window",
                "metric": metric,
                "start_date": dates[start],
                "end_date": dates[end - 1],
                "start_index_in_development_prefix": start,
                "end_index_exclusive": end,
                "window_draws": end - start,
                "value": value,
                "p_value": None,
                "bh_q_within_change_family": None,
                "interpretation_limit": "descriptive only; train plus validation development prefix",
            })

    thirds = [part for part in np.array_split(np.arange(n), 3) if len(part)]
    if game == "3d_lotto":
        categories = np.where(np.count_nonzero(y, axis=1) == 3, 0, np.where(y.max(axis=1) == 3, 2, 1))
        distributions = [("digit_marginal", None), ("pattern_distribution", None)]
    else:
        numbers = np.arange(1, 43)
        odd = y @ (numbers % 2)
        distributions = [
            ("number_marginal", y[index].sum(axis=0).astype(np.float64)) for index in []
        ]
        distributions = [("number_marginal", y[part].sum(axis=0).astype(np.float64)) for part in thirds]
        # All pairwise chronological-window comparisons use full draw rows.
    js_results: list[dict[str, Any]] = []
    if game == "3d_lotto":
        for metric, _ in distributions:
            for i in range(3):
                for j in range(i + 1, 3):
                    if metric == "digit_marginal":
                        left = y[thirds[i]].sum(axis=0).astype(np.float64)
                        right = y[thirds[j]].sum(axis=0).astype(np.float64)
                    else:
                        pat = np.where(np.count_nonzero(y, axis=1) == 3, 0, np.where(y.max(axis=1) == 3, 2, 1))
                        left = np.bincount(pat[thirds[i]], minlength=3).astype(np.float64)
                        right = np.bincount(pat[thirds[j]], minlength=3).astype(np.float64)
                    value = js_divergence(left, right)
                    entry = {"game": game, "metric": metric, "window_a": i + 1, "window_b": j + 1, "js_divergence_bits": value}
                    js_results.append(entry)
                    rows.append({
                        "game": game, "diagnostic_type": "jensen_shannon_between_thirds", "metric": metric,
                        "start_date": dates[thirds[i][0]], "end_date": dates[thirds[j][-1]],
                        "start_index_in_development_prefix": int(thirds[i][0]), "end_index_exclusive": int(thirds[j][-1] + 1),
                        "window_draws": f"{len(thirds[i])}:{len(thirds[j])}", "value": value,
                        "p_value": None, "bh_q_within_change_family": None,
                        "interpretation_limit": "descriptive divergence; not evidence of a physical mechanism",
                    })
    else:
        numbers = np.arange(1, 43)
        odd = y @ (numbers % 2)
        odd_categories = np.bincount(odd.astype(int), minlength=7).astype(np.float64)
        for i in range(3):
            for j in range(i + 1, 3):
                for metric, left, right in (
                    ("number_marginal", y[thirds[i]].sum(axis=0).astype(np.float64), y[thirds[j]].sum(axis=0).astype(np.float64)),
                    ("odd_count_distribution", np.bincount(odd[thirds[i]].astype(int), minlength=7).astype(np.float64), np.bincount(odd[thirds[j]].astype(int), minlength=7).astype(np.float64)),
                ):
                    value = js_divergence(left, right)
                    js_results.append({"game": game, "metric": metric, "window_a": i + 1, "window_b": j + 1, "js_divergence_bits": value})
                    rows.append({
                        "game": game, "diagnostic_type": "jensen_shannon_between_thirds", "metric": metric,
                        "start_date": dates[thirds[i][0]], "end_date": dates[thirds[j][-1]],
                        "start_index_in_development_prefix": int(thirds[i][0]), "end_index_exclusive": int(thirds[j][-1] + 1),
                        "window_draws": f"{len(thirds[i])}:{len(thirds[j])}", "value": value,
                        "p_value": None, "bh_q_within_change_family": None,
                        "interpretation_limit": "descriptive divergence; not evidence of a physical mechanism",
                    })

    observed_series = series_summaries(y, game)
    test_names = list(observed_series)
    observed = [change_statistic(observed_series[name])[0] for name in test_names]
    observed_cuts = [change_statistic(observed_series[name])[1] for name in test_names]
    null = np.empty((PERMUTATIONS, len(test_names)), dtype=np.float64)
    for permutation_index in range(PERMUTATIONS):
        if permutation_index and permutation_index % 2500 == 0:
            print(f"[phase5r] {game} change-point permutations {permutation_index:,}/{PERMUTATIONS:,}", flush=True)
        shuffled = y[rng.permutation(n)]
        shuffled_series = series_summaries(shuffled, game)
        for i, name in enumerate(test_names):
            null[permutation_index, i] = change_statistic(shuffled_series[name])[0]
    p_values = (1 + np.sum(null >= np.asarray(observed)[None, :], axis=0)) / (PERMUTATIONS + 1)
    q_values = benjamini_hochberg(p_values)
    cp_results = []
    for i, name in enumerate(test_names):
        cp = {
            "game": game,
            "metric": name,
            "maximum_standardized_mean_shift": float(observed[i]),
            "cut_index_in_development_prefix": int(observed_cuts[i]),
            "cut_after_date": dates[min(observed_cuts[i] - 1, n - 1)],
            "p_value": float(p_values[i]),
            "bh_q_within_change_family": float(q_values[i]),
            "permutations": PERMUTATIONS,
            "minimum_segment_draws": CHANGE_MIN_SEGMENT,
            "candidate_cut_stride": CHANGE_STRIDE,
            "whole_draw_rows_permuted": True,
        }
        cp_results.append(cp)
        rows.append({
            "game": game, "diagnostic_type": "bounded_change_point", "metric": name,
            "start_date": dates[0], "end_date": dates[-1], "start_index_in_development_prefix": 0,
            "end_index_exclusive": n, "window_draws": n,
            "value": float(observed[i]), "p_value": float(p_values[i]),
            "bh_q_within_change_family": float(q_values[i]),
            "estimated_cut_after_date": cp["cut_after_date"],
            "permutations": PERMUTATIONS,
            "interpretation_limit": "screening statistic only; no physical cause is inferred",
        })
    summary = {
        "rolling_window_draws": ROLLING_WINDOW,
        "rolling_stride_draws": ROLLING_STRIDE,
        "jensen_shannon": js_results,
        "change_points": cp_results,
        "change_point_permutations": PERMUTATIONS,
        "chronological_windows": [
            {"third": i + 1, "row_count": len(part), "start_date": dates[part[0]], "end_date": dates[part[-1]]}
            for i, part in enumerate(thirds)
        ],
        "data_scope": "train plus validation rows only; validation is development evidence",
    }
    return rows, summary


def elementary_symmetric(weights: np.ndarray, k: int) -> float:
    weights = np.asarray(weights, dtype=np.float64)
    require(weights.ndim == 1 and np.all(np.isfinite(weights)) and np.all(weights > 0),
            "FAILED: fixed-cardinality weights must be positive and finite")
    require(0 <= k <= len(weights), "FAILED: elementary symmetric order outside support")
    dp = np.zeros(k + 1, dtype=np.float64)
    dp[0] = 1.0
    processed = 0
    for weight in weights:
        processed += 1
        for order in range(min(k, processed), 0, -1):
            dp[order] += weight * dp[order - 1]
    return float(dp[k])


def fixed_cardinality_parameters(probabilities: np.ndarray, selection: int = 6) -> dict[str, Any]:
    p = np.asarray(probabilities, dtype=np.float64)
    require(p.ndim == 1 and np.all(np.isfinite(p)) and np.all((p > 0) & (p < 1)),
            "FAILED: 6/42 marginal probabilities must lie strictly between zero and one")
    weights = p / (1.0 - p)
    scale = float(np.max(weights))
    scaled = weights / scale
    z_scaled = elementary_symmetric(scaled, selection)
    log_z = math.log(z_scaled) + selection * math.log(scale)
    marginal = np.empty(len(weights), dtype=np.float64)
    for i, weight in enumerate(scaled):
        marginal[i] = weight * elementary_symmetric(np.delete(scaled, i), selection - 1) / z_scaled
    require(abs(float(marginal.sum()) - selection) < 1e-9, "FAILED: 6/42 model marginal inclusion probabilities do not sum to six")
    return {"weights": weights, "scaled_weights": scaled, "z_scaled": z_scaled, "log_normalizer": log_z, "marginal_inclusion": marginal}


def multiset_catalog() -> tuple[list[tuple[int, ...]], np.ndarray, np.ndarray]:
    combinations = list(itertools.combinations_with_replacement(range(10), 3))
    counts = np.zeros((len(combinations), 10), dtype=np.int8)
    coefficients = np.empty(len(combinations), dtype=np.float64)
    for i, combo in enumerate(combinations):
        counts[i] = np.bincount(combo, minlength=10)
        denominator = math.prod(math.factorial(int(value)) for value in counts[i])
        coefficients[i] = math.factorial(3) / denominator
    require(len(combinations) == 220 and int(np.sum(np.count_nonzero(counts, axis=1) == 3)) == 120,
            "FAILED: 3D unordered multiset support is malformed")
    require(int(np.sum(np.count_nonzero(counts, axis=1) == 2)) == 90 and int(np.sum(np.count_nonzero(counts, axis=1) == 1)) == 10,
            "FAILED: 3D multiplicity classes are malformed")
    return combinations, counts, coefficients


def multiset_probabilities(p: np.ndarray, count_matrix: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=np.float64)
    require(p.shape == (10,) and np.all(np.isfinite(p)) and np.all(p >= 0) and abs(float(p.sum()) - 1.0) < 1e-10,
            "FAILED: 3D digit probabilities must form a distribution")
    log_p = np.full(10, -np.inf, dtype=np.float64)
    positive = p > 0
    log_p[positive] = np.log(p[positive])
    safe_log_p = np.where(positive, log_p, 0.0)
    log_probability = np.log(coefficients) + count_matrix @ safe_log_p
    log_probability[np.any((count_matrix > 0) & (~positive)[None, :], axis=1)] = -np.inf
    probabilities = np.exp(log_probability)
    return probabilities


def self_checks() -> dict[str, Any]:
    combinations, count_matrix, coefficients = multiset_catalog()
    fair3 = np.full(10, 0.1)
    fair_probs = multiset_probabilities(fair3, count_matrix, coefficients)
    require(len(fair_probs) == 220 and abs(float(fair_probs.sum()) - 1.0) < 1e-12,
            "FAILED: fair 3D multiset probabilities do not sum to one")
    synthetic_p = np.array([0.06, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.10, 0.11, 0.10])
    synthetic_p /= synthetic_p.sum()
    require(abs(float(multiset_probabilities(synthetic_p, count_matrix, coefficients).sum()) - 1.0) < 1e-12,
            "FAILED: conditional 3D multiset probabilities do not sum to one")

    synthetic_weights = np.array([0.5, 1.25, 2.0, 0.75, 1.5, 0.9])
    k = 3
    independent_z = sum(math.prod(synthetic_weights[i] for i in subset)
                         for subset in itertools.combinations(range(len(synthetic_weights)), k))
    dynamic_z = elementary_symmetric(synthetic_weights, k)
    require(math.isclose(dynamic_z, independent_z, rel_tol=1e-13, abs_tol=1e-13),
            "FAILED: fixed-cardinality DP disagrees with independent synthetic enumeration")
    subset_probabilities = [math.prod(synthetic_weights[i] for i in subset) / dynamic_z
                            for subset in itertools.combinations(range(len(synthetic_weights)), k)]
    require(abs(sum(subset_probabilities) - 1.0) < 1e-13
            and all(len(set(subset)) == k for subset in itertools.combinations(range(len(synthetic_weights)), k)),
            "FAILED: synthetic fixed-cardinality support includes invalid outcomes")
    fair_z = elementary_symmetric(np.ones(42), 6)
    require(math.isclose(fair_z, math.comb(42, 6), rel_tol=0.0, abs_tol=1e-8),
            "FAILED: fair 6/42 normalizer differs from C(42,6)")
    rng = np.random.default_rng(917)
    synthetic3 = np.zeros((125, 10), dtype=np.int16)
    synthetic642 = np.zeros((125, 42), dtype=np.int16)
    for t in range(125):
        synthetic3[t] = np.bincount(rng.integers(0, 10, size=3), minlength=10)
        synthetic642[t, rng.choice(42, size=6, replace=False)] = 1
    for game, source in (("3d_lotto", synthetic3), ("lotto_6_42", synthetic642)):
        base = family_arrays(source, game)
        future = source.copy()
        for t in range(110, len(source)):
            future[t] = 0
            if game == "3d_lotto":
                future[t] = np.bincount(rng.integers(0, 10, size=3), minlength=10)
            else:
                future[t, rng.choice(42, size=6, replace=False)] = 1
        changed = family_arrays(future, game)
        row = int(np.flatnonzero(base["times"] == 110)[0])
        for name in base:
            if name not in {"target", "times"}:
                left, right = base[name], changed[name]
                if isinstance(left, dict):
                    require(all(np.array_equal(left[key][row], right[key][row]) for key in left),
                            f"FAILED: {game} temporal features changed after future-target perturbation")
                else:
                    require(np.array_equal(left[row], right[row]),
                            f"FAILED: {game} temporal features changed after future-target perturbation")
    return {
        "3d_unordered_multisets": len(combinations),
        "3d_fair_probability_sum": float(fair_probs.sum()),
        "3d_synthetic_conditional_probability_sum": float(multiset_probabilities(synthetic_p, count_matrix, coefficients).sum()),
        "642_synthetic_dp_normalizer": dynamic_z,
        "642_synthetic_enumerated_normalizer": independent_z,
        "642_synthetic_subset_probability_sum": float(sum(subset_probabilities)),
        "642_fair_dp_normalizer": fair_z,
        "642_fair_expected_normalizer": math.comb(42, 6),
        "future_target_perturbation_audit": "PASS for both games; features at target index 110 unchanged when that and later outcomes change",
        "passed": True,
    }


def validation_probability_models(game: str, data: dict[str, Any], rng: np.random.Generator) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, np.ndarray]]:
    combinations, count_matrix, coefficients = multiset_catalog()
    fair_combo_count = math.comb(42, 6)
    train_n = data["train_n"]
    val_n = data["validation_n"]
    feature_index = data["feature_index"]
    feature_names = data["feature_names"]
    rows: list[dict[str, Any]] = []
    shrinkage_rows: list[dict[str, Any]] = []
    score_arrays: dict[str, dict[str, np.ndarray]] = {}
    date_rows = data["dates"][train_n:train_n + val_n]
    source_rows = data["source_rows"][train_n:train_n + val_n]
    y_validation = data["targets"][train_n:train_n + val_n]

    if game == "3d_lotto":
        count_columns = [feature_index[f"digit_{digit}_expanding_count"] for digit in range(10)]
        raw_frequency_columns = [feature_index[f"digit_{digit}_freq_expanding"] for digit in range(10)]
        prior_counts = data["features"][train_n:train_n + val_n, :][:, count_columns]
        history_exposure = prior_counts.sum(axis=1)
        require(np.all(history_exposure > 0) and np.allclose(prior_counts / history_exposure[:, None],
                data["features"][train_n:train_n + val_n, :][:, raw_frequency_columns], atol=2e-8),
                "BLOCKED: 3D expanding historical counts and frequencies disagree")
        model_names = ["fair_random", "raw_expanding_frequency", *[f"dirichlet_kappa_{int(kappa)}" for kappa in SHRINKAGE_STRENGTHS]]
        log_ratios: dict[str, np.ndarray] = {}
        actual_log_score: dict[str, np.ndarray] = {}
        fair_actual_logp = np.empty(val_n, dtype=np.float64)
        fair_marginal_pred = np.full((val_n, 10), 1.0 - 0.9 ** 3, dtype=np.float64)
        rank_rows: dict[str, list[int]] = {name: [] for name in model_names}
        top1_rows: dict[str, list[int]] = {name: [] for name in model_names}
        top5_rows: dict[str, list[int]] = {name: [] for name in model_names}
        top10_rows: dict[str, list[int]] = {name: [] for name in model_names}
        actual_probs: dict[str, list[float]] = {name: [] for name in model_names}
        nll_rows: dict[str, list[float]] = {name: [] for name in model_names}
        norm_errors: dict[str, list[float]] = {name: [] for name in model_names}
        p_predictions: dict[str, list[np.ndarray]] = {name: [] for name in model_names}

        for t in range(val_n):
            counts = prior_counts[t]
            raw = counts / history_exposure[t]
            probability_vectors = {"fair_random": np.full(10, 0.1), "raw_expanding_frequency": raw}
            for kappa in SHRINKAGE_STRENGTHS:
                probability_vectors[f"dirichlet_kappa_{int(kappa)}"] = (counts + kappa * 0.1) / (history_exposure[t] + kappa)
            actual = y_validation[t]
            actual_combo_index = next(i for i, combo_counts in enumerate(count_matrix) if np.array_equal(combo_counts, actual))
            for model in model_names:
                p = probability_vectors[model]
                combo_p = multiset_probabilities(p, count_matrix, coefficients)
                norm_error = abs(float(combo_p.sum()) - 1.0)
                require(norm_error < 2e-12 and np.all(combo_p >= 0), "FAILED: 3D validation multiset distribution is not normalized")
                logp = math.log(float(combo_p[actual_combo_index])) if combo_p[actual_combo_index] > 0 else -math.inf
                order = np.argsort(-combo_p, kind="stable")
                ranks = np.empty(len(order), dtype=np.int32)
                ranks[order] = np.arange(1, len(order) + 1)
                rank = int(ranks[actual_combo_index])
                rank_rows[model].append(rank)
                top1_rows[model].append(int(rank <= 1))
                top5_rows[model].append(int(rank <= 5))
                top10_rows[model].append(int(rank <= 10))
                actual_probs[model].append(float(combo_p[actual_combo_index]))
                nll_rows[model].append(float(-logp))
                norm_errors[model].append(norm_error)
                p_predictions[model].append(p.copy())
                rows.append({
                    "game": game, "model": model, "draw_date": date_rows[t], "source_row": source_rows[t],
                    "actual_combination_probability": float(combo_p[actual_combo_index]),
                    "actual_combination_nll_nats": float(-logp), "log_score_advantage_vs_fair": None,
                    "log_score_difference_vs_raw_expanding": None, "actual_combination_rank": rank,
                    "top_1_inclusion": int(rank <= 1), "top_5_inclusion": int(rank <= 5), "top_10_inclusion": int(rank <= 10),
                    "hits_at_6": None, "marginal_brier": None, "normalizer_log_e6": None,
                    "probability_sum_over_all_valid_outcomes": float(combo_p.sum()),
                    "marginal_inclusion_sum": float((1.0 - (1.0 - p) ** 3).sum()),
                    "validation_partition": "development_only",
                })
            fair_actual_logp[t] = math.log(float(multiset_probabilities(np.full(10, 0.1), count_matrix, coefficients)[actual_combo_index]))
            for model in model_names:
                p = probability_vectors[model]
                log_ratios.setdefault(model, np.empty((val_n, 10), dtype=np.float64))[t] = np.log(p / 0.1)
                actual_log_score.setdefault(model, np.empty(val_n, dtype=np.float64))[t] = float(np.dot(actual, np.log(p)))

            for model in model_names[1:]:
                p = probability_vectors[model]
                for digit in range(10):
                    shrinkage_rows.append({
                        "game": game, "draw_date": date_rows[t], "source_row": source_rows[t], "model": model,
                        "candidate": digit, "prior_count": float(counts[digit]), "history_exposure": float(history_exposure[t]),
                        "raw_historical_frequency": float(raw[digit]), "posterior_probability": float(p[digit]),
                        "difference_from_raw_frequency": float(p[digit] - raw[digit]),
                        "candidate_weight": float(p[digit]),
                        "prior_strength": int(model.rsplit("_", 1)[1]) if model.startswith("dirichlet") else None,
                    })

        fair_logp = -np.asarray(nll_rows["fair_random"], dtype=np.float64)
        raw_logp = -np.asarray(nll_rows["raw_expanding_frequency"], dtype=np.float64)
        scores = {}
        model_summary = {}
        for model in model_names:
            logp = -np.asarray(nll_rows[model], dtype=np.float64)
            adv_fair = logp - fair_logp
            adv_raw = logp - raw_logp
            presence_prediction = 1.0 - (1.0 - np.asarray(p_predictions[model])) ** 3
            presence_actual = (y_validation > 0).astype(np.float64)
            scores[model] = {
                "logp": logp,
                "advantage_vs_fair": adv_fair,
                "difference_vs_raw": adv_raw,
                "marginal_prediction": presence_prediction,
                "marginal_actual": presence_actual,
            }
            model_summary[model] = {
                "mean_combination_nll_nats": float(np.mean(nll_rows[model])),
                "median_actual_combination_rank": float(np.median(rank_rows[model])),
                "mean_actual_combination_rank": float(np.mean(rank_rows[model])),
                "mean_reciprocal_rank": float(np.mean(1.0 / np.asarray(rank_rows[model]))),
                "top_1_rate": float(np.mean(top1_rows[model])), "top_5_rate": float(np.mean(top5_rows[model])),
                "top_10_rate": float(np.mean(top10_rows[model])),
                "mean_log_score_advantage_vs_fair": float(np.mean(adv_fair)),
                "mean_log_score_difference_vs_raw": float(np.mean(adv_raw)),
                "maximum_probability_normalization_error": float(np.max(norm_errors[model])),
                "marginal_brier": float(np.mean((presence_prediction - presence_actual) ** 2)),
            }
        for row_index, row in enumerate(rows):
            model = row["model"]
            if model in scores:
                target_index = row_index // len(model_names)
                row["log_score_advantage_vs_fair"] = float(scores[model]["advantage_vs_fair"][target_index])
                row["log_score_difference_vs_raw_expanding"] = float(scores[model]["difference_vs_raw"][target_index])
                row["marginal_brier"] = float(np.mean((scores[model]["marginal_prediction"][target_index] - scores[model]["marginal_actual"][target_index]) ** 2))
        for model in model_names:
            scores[model]["digit_log_ratio"] = log_ratios[model]
        score_arrays = scores
        return rows, {"models": model_summary, "fair_log_score_nats": float(np.mean(fair_logp)), "catalog_size": 220}, shrinkage_rows, score_arrays

    # Lotto 6/42 uses a product-weight distribution restricted to exactly six distinct labels.
    stems = [f"num_{number:02d}" for number in range(1, 43)]
    count_columns = [feature_index[f"{stem}_expanding_count"] for stem in stems]
    prior_counts = data["features"][train_n:train_n + val_n, :][:, count_columns]
    prior_draws = prior_counts.sum(axis=1) / 6.0
    require(np.all(prior_draws > 0), "BLOCKED: 6/42 expanding history has no exposure")
    raw = prior_counts / prior_draws[:, None]
    require(np.all((raw > 0) & (raw < 1)), "BLOCKED: a 6/42 raw expansion candidate probability is outside (0,1)")
    model_names = ["fair_random", "raw_expanding_frequency", *[f"beta_kappa_{int(kappa)}" for kappa in SHRINKAGE_STRENGTHS]]
    score_logs = {name: np.empty(val_n, dtype=np.float64) for name in model_names}
    score_adv = {name: np.empty(val_n, dtype=np.float64) for name in model_names}
    score_adv_raw = {name: np.empty(val_n, dtype=np.float64) for name in model_names}
    marginal_pred = {name: np.empty((val_n, 42), dtype=np.float64) for name in model_names}
    hit_rows = {name: np.empty(val_n, dtype=np.int8) for name in model_names}
    log_weights_rows = {name: np.empty((val_n, 42), dtype=np.float64) for name in model_names}
    logz_rows = {name: np.empty(val_n, dtype=np.float64) for name in model_names}
    fair_nll = math.log(fair_combo_count)
    y_val = y_validation
    for t in range(val_n):
        probabilities = {"fair_random": np.full(42, 6.0 / 42.0), "raw_expanding_frequency": raw[t]}
        for kappa in SHRINKAGE_STRENGTHS:
            probabilities[f"beta_kappa_{int(kappa)}"] = (prior_counts[t] + kappa * (6.0 / 42.0)) / (prior_draws[t] + kappa)
        actual_numbers = np.flatnonzero(y_val[t])
        require(len(actual_numbers) == 6, "FAILED: validation outcome is not a six-number set")
        for model in model_names:
            p = probabilities[model]
            params = fixed_cardinality_parameters(p)
            weights = params["weights"]
            logw = np.log(weights)
            log_probability = float(np.sum(logw[actual_numbers]) - params["log_normalizer"])
            score_logs[model][t] = log_probability
            score_adv[model][t] = log_probability + fair_nll
            score_adv_raw[model][t] = log_probability
            marginal_pred[model][t] = params["marginal_inclusion"]
            order = np.argsort(-weights, kind="stable")[:6]
            hit_rows[model][t] = len(set(order.tolist()) & set(actual_numbers.tolist()))
            log_weights_rows[model][t] = logw
            logz_rows[model][t] = params["log_normalizer"]
            rows.append({
                "game": game, "model": model, "draw_date": date_rows[t], "source_row": source_rows[t],
                "actual_combination_probability": float(math.exp(log_probability)),
                "actual_combination_nll_nats": float(-log_probability),
                "log_score_advantage_vs_fair": float(log_probability + fair_nll),
                "log_score_difference_vs_raw_expanding": None,
                "actual_combination_rank": None, "top_1_inclusion": None, "top_5_inclusion": None, "top_10_inclusion": None,
                "hits_at_6": int(hit_rows[model][t]),
                "marginal_brier": float(np.mean((params["marginal_inclusion"] - y_val[t]) ** 2)),
                "normalizer_log_e6": float(params["log_normalizer"]),
                "probability_sum_over_all_valid_outcomes": 1.0,
                "marginal_inclusion_sum": float(params["marginal_inclusion"].sum()),
                "validation_partition": "development_only",
            })
            if model != "fair_random":
                for number in range(42):
                    shrinkage_rows.append({
                        "game": game, "draw_date": date_rows[t], "source_row": source_rows[t], "model": model,
                        "candidate": number + 1, "prior_count": float(prior_counts[t, number]),
                        "history_exposure": float(prior_draws[t]), "raw_historical_frequency": float(raw[t, number]),
                        "posterior_probability": float(p[number]),
                        "difference_from_raw_frequency": float(p[number] - raw[t, number]),
                        "candidate_weight": float(weights[number]),
                        "prior_strength": int(model.rsplit("_", 1)[1]) if model.startswith("beta") else None,
                    })

    fair_log = score_logs["fair_random"]
    raw_log = score_logs["raw_expanding_frequency"]
    model_summary = {}
    scores = {}
    for model in model_names:
        logp = score_logs[model]
        adv_fair = logp - fair_log
        adv_raw = logp - raw_log
        scores[model] = {
            "logp": logp,
            "advantage_vs_fair": adv_fair,
            "difference_vs_raw": adv_raw,
            "marginal_prediction": marginal_pred[model],
            "marginal_actual": y_val.astype(np.float64),
            "log_weights": log_weights_rows[model],
            "log_normalizers": logz_rows[model],
        }
        model_summary[model] = {
            "mean_combination_nll_nats": float(np.mean(-logp)),
            "mean_log_score_advantage_vs_fair": float(np.mean(adv_fair)),
            "mean_log_score_difference_vs_raw": float(np.mean(adv_raw)),
            "mean_hits_at_6": float(np.mean(hit_rows[model])),
            "hits_at_6_fair_expectation": 36.0 / 42.0,
            "marginal_brier": float(np.mean((marginal_pred[model] - y_val) ** 2)),
            "maximum_inclusion_sum_error": float(np.max(np.abs(marginal_pred[model].sum(axis=1) - 6.0))),
        }
    row_cursor = 0
    for model in model_names:
        for t in range(val_n):
            rows[row_cursor]["log_score_difference_vs_raw_expanding"] = float(scores[model]["difference_vs_raw"][t])
            row_cursor += 1
    score_arrays = scores
    return rows, {"models": model_summary, "fair_log_score_nats": -fair_nll, "valid_set_count": fair_combo_count}, shrinkage_rows, score_arrays


def bootstrap_score_comparisons(scores: dict[str, dict[str, np.ndarray]], rng: np.random.Generator) -> dict[str, Any]:
    model_names = list(scores)
    n = len(next(iter(scores.values()))["advantage_vs_fair"])
    matrix_fair = np.column_stack([scores[model]["advantage_vs_fair"] for model in model_names])
    matrix_raw = np.column_stack([scores[model]["difference_vs_raw"] for model in model_names])
    boots_fair = np.empty((BOOTSTRAPS, len(model_names)), dtype=np.float64)
    boots_raw = np.empty_like(boots_fair)
    batch_size = 128
    for start in range(0, BOOTSTRAPS, batch_size):
        end = min(start + batch_size, BOOTSTRAPS)
        idx = rng.integers(0, n, size=(end - start, n))
        boots_fair[start:end] = matrix_fair[idx].mean(axis=1)
        boots_raw[start:end] = matrix_raw[idx].mean(axis=1)
    summary: dict[str, Any] = {}
    for j, model in enumerate(model_names):
        fair_ci = np.quantile(boots_fair[:, j], [0.025, 0.975])
        raw_ci = np.quantile(boots_raw[:, j], [0.025, 0.975])
        segments = np.array_split(np.arange(n), 3)
        segment_fair = [float(np.mean(matrix_fair[index, j])) for index in segments]
        segment_raw = [float(np.mean(matrix_raw[index, j])) for index in segments]
        summary[model] = {
            "bootstrap_resamples": BOOTSTRAPS,
            "whole_validation_draw_rows_resampled": True,
            "mean_log_score_advantage_vs_fair": float(matrix_fair[:, j].mean()),
            "bootstrap_ci95_vs_fair": [float(fair_ci[0]), float(fair_ci[1])],
            "mean_log_score_difference_vs_raw_expanding": float(matrix_raw[:, j].mean()),
            "bootstrap_ci95_vs_raw_expanding": [float(raw_ci[0]), float(raw_ci[1])],
            "segment_log_score_advantage_vs_fair": segment_fair,
            "segment_log_score_difference_vs_raw_expanding": segment_raw,
            "segments_better_than_fair": int(sum(value > 0 for value in segment_fair)),
            "segments_better_than_raw_expanding": int(sum(value > 0 for value in segment_raw)),
        }
    return summary


def calibration_assessment(prediction: np.ndarray, actual: np.ndarray, rng: np.random.Generator) -> dict[str, Any]:
    p = np.asarray(prediction, dtype=np.float64)
    y = np.asarray(actual, dtype=np.float64)
    require(p.shape == y.shape and p.ndim == 2, "FAILED: calibration arrays are not draw-by-candidate matrices")
    n, candidates = p.shape
    bins = np.minimum((p * 10).astype(np.int32), 9)
    den = np.zeros((n, 10), dtype=np.float64)
    residual = np.zeros((n, 10), dtype=np.float64)
    observed = np.zeros((n, 10), dtype=np.float64)
    predicted = np.zeros((n, 10), dtype=np.float64)
    for b in range(10):
        mask = bins == b
        den[:, b] = mask.sum(axis=1)
        residual[:, b] = np.sum((y - p) * mask, axis=1)
        observed[:, b] = np.sum(y * mask, axis=1)
        predicted[:, b] = np.sum(p * mask, axis=1)
    boot_gaps = np.full((BOOTSTRAPS, 10), np.nan, dtype=np.float64)
    batch_size = 64
    for start in range(0, BOOTSTRAPS, batch_size):
        end = min(start + batch_size, BOOTSTRAPS)
        idx = rng.integers(0, n, size=(end - start, n))
        den_sum = np.take(den, idx, axis=0).sum(axis=1)
        residual_sum = np.take(residual, idx, axis=0).sum(axis=1)
        boot_gaps[start:end] = np.divide(residual_sum, den_sum, out=np.full_like(residual_sum, np.nan), where=den_sum > 0)
    table = []
    pass_bins = []
    ece = 0.0
    total = float(den.sum())
    for b in range(10):
        count = float(den[:, b].sum())
        if not count:
            continue
        gap = float(residual[:, b].sum() / count)
        ci = np.nanquantile(boot_gaps[:, b], [0.025, 0.975])
        calibrated_screen = bool(ci[0] <= 0 <= ci[1])
        pass_bins.append(calibrated_screen)
        ece += (count / total) * abs(gap)
        table.append({
            "bin": b,
            "count_candidate_draws": int(count),
            "mean_predicted_probability": float(predicted[:, b].sum() / count),
            "observed_rate": float(observed[:, b].sum() / count),
            "observed_minus_predicted": gap,
            "bootstrap_ci95_gap": [float(ci[0]), float(ci[1])],
            "calibration_screen_ci_contains_zero": calibrated_screen,
        })
    return {
        "ece": float(ece),
        "bins": table,
        "screen_passes": bool(pass_bins and all(pass_bins)),
        "screen": "all nonempty fixed-width probability bins have a 95% whole-draw bootstrap interval for observed-minus-predicted rate that contains zero",
        "bootstrap_resamples": BOOTSTRAPS,
        "whole_draw_rows_resampled": True,
    }


def fair_random_monte_carlo(game: str, scores: dict[str, dict[str, np.ndarray]], rng: np.random.Generator) -> dict[str, Any]:
    model_names = [name for name in scores if name != "fair_random"]
    n = len(scores[model_names[0]]["advantage_vs_fair"])
    observed = {name: float(np.mean(scores[name]["advantage_vs_fair"])) for name in model_names}
    simulations: dict[str, list[float]] = {name: [] for name in model_names}
    exceed: dict[str, int] = {name: 0 for name in model_names}

    def simulate(batch_count: int, names: list[str]) -> None:
        nonlocal simulations, exceed
        if game == "3d_lotto":
            digits = rng.integers(0, 10, size=(batch_count, n, 3), dtype=np.int8)
            for name in names:
                ratio = scores[name]["digit_log_ratio"]
                selected = np.take_along_axis(ratio[None, :, :], digits, axis=2).sum(axis=2)
                means = selected.mean(axis=1)
                simulations[name].extend(means.tolist())
                exceed[name] += int(np.count_nonzero(means >= observed[name]))
        else:
            random_values = rng.random((batch_count, n, 42))
            selected = np.argpartition(random_values, kth=5, axis=2)[:, :, :6]
            for name in names:
                logw = scores[name]["log_weights"]
                logz = scores[name]["log_normalizers"]
                gathered = np.take_along_axis(logw[None, :, :], selected, axis=2).sum(axis=2)
                means = (gathered - logz[None, :] + math.log(math.comb(42, 6))).mean(axis=1)
                simulations[name].extend(means.tolist())
                exceed[name] += int(np.count_nonzero(means >= observed[name]))

    batch_size = 64
    remaining = MC_INITIAL
    while remaining:
        batch = min(batch_size, remaining)
        simulate(batch, model_names)
        remaining -= batch
    initial_p = {name: (1 + exceed[name]) / (MC_INITIAL + 1) for name in model_names}
    escalated = [name for name, value in initial_p.items() if value < 0.01]
    if escalated:
        remaining = MC_CONFIRMATION - MC_INITIAL
        while remaining:
            batch = min(batch_size, remaining)
            simulate(batch, escalated)
            remaining -= batch
    result = {}
    for name in model_names:
        values = np.asarray(simulations[name], dtype=np.float64)
        count = len(values)
        result[name] = {
            "observed_mean_log_score_advantage_vs_fair": observed[name],
            "fair_null_simulation_mean": float(values.mean()),
            "fair_null_simulation_interval95": [float(v) for v in np.quantile(values, [0.025, 0.975])],
            "initial_simulations": MC_INITIAL,
            "initial_empirical_p_add_one": float(initial_p[name]),
            "simulations": count,
            "empirical_p_add_one": float((1 + exceed[name]) / (count + 1)),
            "confirmation_escalated": name in escalated,
            "complete_fair_random_validation_histories": True,
            "forecast_path_fixed_to_observed_history": True,
        }
    return {
        "models": result,
        "initial_simulations_per_model": MC_INITIAL,
        "confirmation_simulations": MC_CONFIRMATION,
        "escalated_models": escalated,
        "interpretation": "conditional fair-null comparison: model forecasts are frozen to the observed leakage-safe validation history; simulated complete fair validation outcomes are scored against those forecasts",
    }


def summarize_shrinkage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    by_game_model: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        by_game_model.setdefault((row["game"], row["model"]), []).append(row)
    for (game, model), items in by_game_model.items():
        posterior = np.asarray([item["posterior_probability"] for item in items], dtype=np.float64)
        raw = np.asarray([item["raw_historical_frequency"] for item in items], dtype=np.float64)
        summary.setdefault(game, {})[model] = {
            "prior_center": 0.1 if game == "3d_lotto" else 6.0 / 42.0,
            "prior_strength": int(items[0]["prior_strength"]) if items[0]["prior_strength"] is not None else None,
            "candidate_draw_estimates": len(items),
            "mean_absolute_difference_from_raw_frequency": float(np.mean(np.abs(posterior - raw))),
            "maximum_absolute_difference_from_raw_frequency": float(np.max(np.abs(posterior - raw))),
            "mean_posterior_probability_across_candidate_draws": float(np.mean(posterior)),
        }
    return summary


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(value) for key, value in row.items()})


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def decision_verdict(information: list[dict[str, Any]], comparisons: dict[str, Any], monte_carlo: dict[str, Any], calibration: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    information_detected = any(row["bh_q_within_game"] < ALPHA for row in information)
    qualifying_models: list[str] = []
    improvement = False
    stable = False
    calibrated = False
    for game, models in comparisons.items():
        for model, row in models.items():
            if model == "fair_random":
                continue
            fair_ci = row["bootstrap_ci95_vs_fair"]
            raw_ci = row["bootstrap_ci95_vs_raw_expanding"]
            this_improvement = fair_ci[0] > 0 and raw_ci[0] > 0
            this_stability = row["segments_better_than_fair"] == 3 and row["segments_better_than_raw_expanding"] == 3
            mc = monte_carlo.get(game, {}).get("models", {}).get(model, {})
            this_mc = mc.get("empirical_p_add_one", 1.0) <= ALPHA
            this_calibrated = calibration.get(game, {}).get(model, {}).get("screen_passes", False)
            if this_improvement and this_stability and this_mc and this_calibrated:
                qualifying_models.append(f"{game}/{model}")
            improvement = improvement or this_improvement
            stable = stable or this_stability
            calibrated = calibrated or this_calibrated
    evidence = {
        "bh_adjusted_information_detected": information_detected,
        "proper_score_bootstrap_improvement_vs_fair_and_raw_detected": improvement,
        "chronological_direction_stability_detected": stable,
        "conditional_monte_carlo_p_gate_detected": any(
            model.get("empirical_p_add_one", 1.0) <= ALPHA
            for game in monte_carlo.values() for model in game.get("models", {}).values()
        ),
        "marginal_calibration_screen_passed_by_any_candidate": calibrated,
        "qualifying_models": qualifying_models,
        "decision_gate": "BH q < 0.05 plus paired 95% bootstrap intervals above zero versus fair and raw expansion, positive direction in all three validation thirds, conditional fair-null Monte Carlo p <= 0.05, and no detected marginal miscalibration under the whole-draw bootstrap screen",
    }
    if qualifying_models and information_detected:
        return "PHASE5R_PREDICTIVE_INFORMATION_DETECTED", evidence
    any_signal = information_detected or improvement or stable or evidence["conditional_monte_carlo_p_gate_detected"]
    if any_signal:
        return "PHASE5R_INCONCLUSIVE", evidence
    return "PHASE5R_NO_REPRODUCIBLE_PREDICTIVE_INFORMATION", evidence


def short_number(value: Any, digits: int = 5) -> str:
    if value is None:
        return "n/a"
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(x):
        return "infinite" if x > 0 else "-infinite"
    return f"{x:.{digits}f}"


def render_report(evidence: dict[str, Any]) -> str:
    lines = [
        "# Phase 5R Predictive Information and Conditional Combination Modeling",
        "",
        f"- Verdict: **{evidence['verdict']}**",
        f"- Branch / HEAD: `{evidence['repository']['branch']}` / `{evidence['repository']['head']}`",
        f"- Seed: {SEED}; information and change-point permutations: {PERMUTATIONS:,}; whole-draw bootstrap resamples: {BOOTSTRAPS:,}",
        "- Locked test targets: not parsed, scored, visualized, tuned against, or used; only Phase 4 boundary metadata was read.",
        "- Phase 5A validation was already examined; all Phase 5R validation results below are development evidence, not pristine final confirmation.",
        "- Keys.env: ignored and untracked by Git metadata; contents not read. JEV and TypeSafe were not invoked.",
        "- Git stage, commit, push, and merge: not performed.",
        "",
        "## Scope and data boundaries",
        "",
        "The analysis reads only the Phase 4 train and validation prefixes. The feature and target CSV readers stop after those prefix rows. Training information diagnostics and conditional rates use training only; stationarity uses train plus validation; sequential combination forecasts use prior-history features at each validation draw. Validation is explicitly development evidence because Phase 5A already used it.",
        "",
        "| Game | Train | Validation | Locked test metadata only |",
        "|---|---:|---:|---|",
    ]
    for game, parts in evidence["data_boundaries"].items():
        lines.append(f"| {game} | {parts['train']['row_count']} ({parts['train']['start_date']}–{parts['train']['end_date']}) | {parts['validation']['row_count']} ({parts['validation']['start_date']}–{parts['validation']['end_date']}) | {parts['test']['row_count']} ({parts['test']['start_date']}–{parts['test']['end_date']}) |")
    lines.extend(["", "## Fair-random models", "", f"- 3D: all {evidence['fair_random_verification']['3d']['multiset_count']} unordered multisets were enumerated with multiplicity coefficients; fair probabilities sum to {short_number(evidence['fair_random_verification']['3d']['fair_probability_sum'], 12)}. Every validation forecast distribution was checked to sum to one.", f"- Lotto 6/42: the fair fixed-cardinality normalizer is {evidence['fair_random_verification']['642']['fair_normalizer']:,}, matching C(42,6); the weighted model uses the exact sixth elementary symmetric polynomial.", "- Independent synthetic enumeration matched the 6/42 dynamic-programming normalizer and valid-set probabilities.", "", "## Information-theoretic diagnostics", "", "Whole train draw rows were permuted 10,000 times; candidate features were rebuilt using only preceding shuffled rows for every permutation. 3D digit multiplicity and membership were assessed separately. Benjamini–Hochberg q-values are corrected within each game's full predefined diagnostic set.", "", "| Game | Diagnostic family | Target measure | MI (nats / candidate) | Empirical p | BH q |", "|---|---|---|---:|---:|---:|"])
    for row in evidence["information_tests"]:
        lines.append(f"| {row['game']} | {row['diagnostic_family']} | {row['target_measure']} | {short_number(row['observed_mutual_information_nats_per_candidate'])} | {short_number(row['empirical_p_add_one'])} | {short_number(row['bh_q_within_game'])} |")
    lines.extend(["", "These are training-period diagnostic associations, not evidence that a specific candidate is more likely in a future draw. A statistically small q-value alone does not establish useful full-combination prediction.", "", "## Temporal dependence and stationarity", "", "Temporal conditional rates, paired whole-draw bootstrap intervals, fair marginal references, and the corresponding information-permutation diagnostics are in `phase5r_temporal_dependence.csv`. The detailed stationarity file contains rolling entropy, marginal-deviation, draw-context, Jensen–Shannon, and bounded change-point rows.", ""])
    for game, stationarity in evidence["stationarity"].items():
        lines.append(f"### {game}")
        for item in stationarity["jensen_shannon"]:
            lines.append(f"- Jensen–Shannon {item['metric']} between thirds {item['window_a']} and {item['window_b']}: {short_number(item['js_divergence_bits'])} bits.")
        supported = [item for item in stationarity["change_points"] if item["bh_q_within_change_family"] < ALPHA]
        if supported:
            lines.append("- Bounded change-point screening flagged: " + ", ".join(f"{item['metric']} after {item['cut_after_date']} (q={short_number(item['bh_q_within_change_family'])})" for item in supported) + ". These are statistical screens and do not identify a physical cause.")
        else:
            lines.append("- No bounded mean-shift screen passed within-family BH q < 0.05; this does not prove strict stationarity.")
    lines.extend(["", "## Bayesian shrinkage and complete-combination scores", "", "3D forecasts use Dirichlet priors centered at 0.10 with total concentrations 10, 100, and 1,000. Lotto 6/42 uses Beta priors centered at 6/42; posterior marginal estimates become positive odds weights for the exact six-element product-weight model. Each estimate uses only Phase 4 prior-history counts for its target draw.", "", "| Game | Model | Mean combination NLL | Mean log-score advantage vs fair | 95% bootstrap CI vs fair | CI vs raw expansion | Positive validation thirds vs fair | MC p | Calibration screen |", "|---|---|---:|---:|---|---|---:|---:|---|"])
    for game, models in evidence["combination_validation"].items():
        for model, result in models["models"].items():
            boot = evidence["bootstrap"][game][model]
            mc = evidence["fair_random_monte_carlo"][game].get("models", {}).get(model, {})
            calibration = evidence["calibration"][game].get(model, {})
            fair_ci = boot["bootstrap_ci95_vs_fair"]
            raw_ci = boot["bootstrap_ci95_vs_raw_expanding"]
            lines.append(f"| {game} | {model} | {short_number(result['mean_combination_nll_nats'])} | {short_number(result['mean_log_score_advantage_vs_fair'])} | [{short_number(fair_ci[0])}, {short_number(fair_ci[1])}] | [{short_number(raw_ci[0])}, {short_number(raw_ci[1])}] | {boot['segments_better_than_fair']}/3 | {short_number(mc.get('empirical_p_add_one'))} | {calibration.get('screen_passes', 'n/a')} |")
    lines.extend(["", "Monte Carlo comparisons use 10,000 complete fair-random validation histories per model and escalate only an initial empirical p-value below 0.01 to 100,000. Forecasts are held fixed to the observed leakage-safe history, so these p-values are conditional comparisons and remain development evidence. Bootstrap intervals resample complete validation draw rows.", "", "The calibration screen uses 10 equal-width probability bins and 10,000 whole-draw bootstrap resamples. A screen pass means no nonempty bin's 95% interval for observed-minus-predicted marginal rate excluded zero; it is not a formal calibration guarantee. The ECE and bin details are in the evidence JSON.", "", "## Decision and limitations", "", evidence["decision_evidence"]["decision_gate"], ""])
    lines.append("The Phase 5A validation history has already been examined, so Phase 5R cannot provide pristine confirmation. No model may be described as finally predictive from these results alone. No draw recommendation is produced. Physical dynamics, quantum prediction, and player-choice optimization remain unsupported because the required measurements are absent.")
    lines.append("")
    lines.append(f"Safest next action: {evidence['safest_next_action']}")
    lines.append("")
    lines.append("## Validation and provenance")
    lines.append("")
    for name, result in evidence["validation"].items():
        lines.append(f"- `{name}`: {result}")
    lines.append("")
    return "\n".join(lines)


NOTEBOOK_SECTIONS = [
    ("1. Phase 5R Objective and Research Question", "Does history assign useful probability to a complete next draw? Proper scoring of complete outcomes answers this directly.", "Read the evidence summary and state the result without converting marginal frequency into a prediction claim."),
    ("2. Existing Evidence from Phases 1 through 5A", "Prior phase verdicts and saved audits establish the approved starting point.", "Phase 5A validation was already examined, so this remains development evidence."),
    ("3. Data and Chronological Boundary Verification", "Checking the recorded split metadata and parsed row counts makes the test boundary auditable.", "Locked test data appears as metadata only; no test target rows are loaded."),
    ("4. Fair-Random Combination Models", "The null must match each game's outcome space, including 3D multiplicity and fixed six-number cardinality.", "The fair 3D outcome probabilities differ by multiplicity class; 6/42 sets share one fair probability."),
    ("5. Information-Theoretic Framework", "Candidate-level mutual information estimates conditional dependence while complete-draw permutations provide the null.", "The association diagnostics are in-sample training evidence, not a utility claim."),
    ("6. Mutual Information and Permutation Tests", "Plotting a predeclared family against its full permutation null shows scale and uncertainty.", "All predefined families and adjusted values remain visible in the table."),
    ("7. Temporal-Dependence Analysis", "Conditional rates with paired whole-draw intervals avoid treating candidate rows as independent.", "Use the previous-draw state plot and full CSV for all other predeclared state groups."),
    ("8. Stationarity Diagnostics", "Rolling entropy and marginal deviations show how the development history varies over time.", "Variation alone does not demonstrate a change in the physical draw process."),
    ("9. Change-Point Investigation", "A bounded max-shift scan corrects for searching candidate cuts and uses complete-draw row permutations.", "Any flagged date is a statistical screen, not an explanation."),
    ("10. Bayesian Shrinkage Framework", "Dirichlet and Beta priors pull weak marginal estimates toward the fair reference.", "Prior strength sensitivity is reported; it was not selected on validation performance."),
    ("11. 3D Conditional Digit Probabilities", "The posterior digit vectors are the inputs to a valid unordered-multiset model.", "A marginal digit probability is not itself a multiset probability."),
    ("12. 3D 220-Multiset Probability Distribution", "The multinomial multiplicity coefficient yields an exact distribution over all valid multisets.", "Every validation forecast's full 220-outcome distribution was checked to sum to one."),
    ("13. 3D Combination-Level Validation", "Ranks and proper combination log scores compare full outcomes chronologically.", "Top-k rates are secondary and cannot establish useful predictive power alone."),
    ("14. Lotto 6/42 Candidate Weights", "Positive odds weights preserve the fixed-cardinality model's support.", "Marginal Beta posteriors are candidates for weights, not independent Bernoulli draw probabilities."),
    ("15. Fixed-Cardinality 6/42 Combination Model", "The sixth elementary symmetric polynomial exactly normalizes the product-weight distribution.", "A small independent enumeration validates the DP; no millions-of-sets loop is used per draw."),
    ("16. Lotto 6/42 Combination-Level Validation", "Complete-set NLL, marginal Brier, and hits@6 describe different aspects of the same forecast.", "Hits@6 is secondary to the exact complete-set probability score."),
    ("17. Proper-Scoring-Rule Comparison", "Bootstrap intervals and fair-null simulations compare log scores while preserving complete validation rows.", "The Monte Carlo comparison conditions on the observed forecast path and is not pristine confirmation."),
    ("18. Predictive Information Evidence Summary", "The gate requires corrected information, proper-score improvement, chronological stability, and calibration evidence.", "No individual p-value can bypass the combined evidence gate."),
    ("19. Limitations and Unsupported Theories", "Physical, quantum, and game-theoretic models require variables absent from these data.", "No unsupported model branch or draw recommendation is included."),
    ("20. Final Phase 5R Decision", "The verdict follows the recorded evidence gate and preserves the future test boundary.", "A later one-time test requires a separately authorized phase and a frozen model."),
]


def notebook_markdown(title: str, question: str, interpretation: str) -> str:
    return f"## {title}\n\n**Analytical question:** {question}\n\n**Why this method fits:** The analysis uses only Phase 4 train and validation prefixes and respects each game's complete-draw outcome structure.\n\n**Interpretation:** {interpretation}\n\n**Limitation:** Validation has already been examined in Phase 5A and is development evidence. Locked test targets are not read."


def build_notebook(evidence: dict[str, Any]) -> Any:
    import nbformat

    nb = nbformat.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": sys.version.split()[0]},
    }
    cells = [nbformat.v4.new_markdown_cell(
        "# Phase 5R Predictive Information and Conditional Combination Modeling\n\nThis executed notebook reads Phase 5R result artifacts only. It does not open the Phase 4 target matrix or any locked-test target row."
    )]
    setup = """from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

ROOT = Path.cwd()
EVIDENCE = json.loads((ROOT / 'reports/phase5r_evidence.json').read_text(encoding='utf-8'))
INFO = pd.read_csv(ROOT / 'reports/phase5r_information_tests.csv')
PERM = pd.read_csv(ROOT / 'reports/phase5r_information_permutations.csv')
TEMP = pd.read_csv(ROOT / 'reports/phase5r_temporal_dependence.csv')
STATION = pd.read_csv(ROOT / 'reports/phase5r_stationarity.csv')
BAYES = pd.read_csv(ROOT / 'reports/phase5r_bayesian_shrinkage.csv')
METRICS = pd.read_csv(ROOT / 'reports/phase5r_combination_probability_metrics.csv')
"""
    for i, (title, question, interpretation) in enumerate(NOTEBOOK_SECTIONS):
        cells.append(nbformat.v4.new_markdown_cell(notebook_markdown(title, question, interpretation)))
        if i == 0:
            code = "print(EVIDENCE['research_question'])\nprint('Verdict:', EVIDENCE['verdict'])"
        elif i == 1:
            code = "display(pd.DataFrame([{'phase': '3', 'verdict': EVIDENCE['preflight']['phase3_verdict']}, {'phase': '4', 'verdict': EVIDENCE['preflight']['phase4_verdict']}, {'phase': '5A', 'verdict': EVIDENCE['preflight']['phase5a_verdict']}]))"
        elif i == 2:
            code = "display(pd.DataFrame([{'game': game, **parts['test']} for game, parts in EVIDENCE['data_boundaries'].items()]))\nprint('Rows parsed:', {game: item['dev_rows_parsed'] for game, item in EVIDENCE['data_read_audit'].items()})"
        elif i == 3:
            code = "display(pd.DataFrame([{'game': '3d_lotto', **EVIDENCE['fair_random_verification']['3d']}, {'game': 'lotto_6_42', **EVIDENCE['fair_random_verification']['642']}]))"
        elif i == 4:
            code = "print(EVIDENCE['information_method'])"
        elif i == 5:
            code = "display(INFO.sort_values(['game', 'bh_q_within_game']))\nfamily = 'previous_draw_appearance'\nmeasure = 'multiplicity_count' if (INFO['game'] == '3d_lotto').any() else 'membership'\nrow = INFO[(INFO.game == '3d_lotto') & (INFO.diagnostic_family == family) & (INFO.target_measure == measure)].iloc[0]\nnull = PERM[(PERM.game == '3d_lotto') & (PERM.diagnostic_family == family) & (PERM.target_measure == measure)].mutual_information_nats_per_candidate\nplt.figure(figsize=(7, 3))\nplt.hist(null, bins=40, color='#6b8fb3')\nplt.axvline(row.observed_mutual_information_nats_per_candidate, color='#b54545', label='Observed')\nplt.title('Predeclared 3D previous-draw information diagnostic')\nplt.xlabel('Mutual information (nats per candidate)'); plt.ylabel('Permutation count'); plt.legend(); plt.tight_layout(); plt.show()"
        elif i == 6:
            code = "display(TEMP)\nprevious = TEMP[TEMP.feature_group == 'previous_draw_appearance'].copy()\nif len(previous):\n    plt.figure(figsize=(7, 3))\n    for game, block in previous.groupby('game'):\n        delta = block.rate_difference_from_empirical_baseline.to_numpy()\n        low = block.paired_draw_bootstrap_delta_ci95_low.to_numpy()\n        high = block.paired_draw_bootstrap_delta_ci95_high.to_numpy()\n        plt.errorbar(block.state, delta, yerr=[(delta-low).clip(min=0), (high-delta).clip(min=0)], marker='o', label=game)\n    plt.axhline(0, color='black', linewidth=.7)\n    plt.ylabel('Conditional rate minus empirical baseline'); plt.title('Appearance by previous-draw state'); plt.legend(); plt.tight_layout(); plt.show()"
        elif i == 7:
            code = "rolling = STATION[STATION.diagnostic_type == 'rolling_window']\nmetric = 'marginal_digit_entropy_nats' if (rolling.game == '3d_lotto').any() else 'marginal_number_entropy_nats'\nblock = rolling[rolling.metric == metric]\nfor game, values in block.groupby('game'):\n    plt.plot(values.end_date, values.value, marker='o', label=game)\nplt.xticks(rotation=30); plt.ylabel('Rolling entropy (nats)'); plt.title('Rolling marginal entropy'); plt.legend(); plt.tight_layout(); plt.show()\ndisplay(block[['game', 'start_date', 'end_date', 'value']])"
        elif i == 8:
            code = "change = STATION[STATION.diagnostic_type == 'bounded_change_point']\ndisplay(change[['game', 'metric', 'estimated_cut_after_date', 'value', 'p_value', 'bh_q_within_change_family']])"
        elif i == 9:
            code = "display(BAYES.groupby(['game', 'model']).agg(mean_posterior=('posterior_probability', 'mean'), mean_raw=('raw_historical_frequency', 'mean'), mean_abs_change=('difference_from_raw_frequency', lambda x: x.abs().mean())).reset_index())\nmeans = BAYES.groupby(['game', 'model', 'candidate'])[['posterior_probability', 'raw_historical_frequency']].mean().reset_index()\nfor game, block in means.groupby('game'):\n    plt.figure(figsize=(6, 3)); plt.scatter(block.raw_historical_frequency, block.posterior_probability, s=14, alpha=.6); plt.plot([0, block[['raw_historical_frequency','posterior_probability']].to_numpy().max()], [0, block[['raw_historical_frequency','posterior_probability']].to_numpy().max()], color='gray'); plt.title(f'{game}: posterior versus raw frequency'); plt.xlabel('Raw frequency'); plt.ylabel('Shrunk probability'); plt.tight_layout(); plt.show()"
        elif i == 10:
            code = "display(BAYES[BAYES.game == '3d_lotto'].groupby(['model', 'candidate']).posterior_probability.mean().unstack('model').head(10))"
        elif i == 11:
            code = "display(METRICS[METRICS.game == '3d_lotto'].groupby('model').agg(max_normalization_error=('probability_sum_over_all_valid_outcomes', lambda s: (s - 1).abs().max()), mean_nll=('actual_combination_nll_nats', 'mean'), mean_rank=('actual_combination_rank', 'mean')).reset_index())\nranked = METRICS[(METRICS.game == '3d_lotto') & METRICS.actual_combination_rank.notna()]\nplt.hist(ranked[ranked.model == 'dirichlet_kappa_100'].actual_combination_rank, bins=30, color='#758b5a'); plt.xlabel('Actual multiset rank'); plt.ylabel('Validation draws'); plt.title('3D actual-combination rank distribution'); plt.tight_layout(); plt.show()"
        elif i == 12:
            code = "display(METRICS[METRICS.game == '3d_lotto'].groupby('model').agg(mean_nll=('actual_combination_nll_nats', 'mean'), mean_log_advantage=('log_score_advantage_vs_fair', 'mean'), top5=('top_5_inclusion', 'mean')).reset_index())"
        elif i == 13:
            code = "display(BAYES[BAYES.game == 'lotto_6_42'].groupby('model').agg(mean_posterior=('posterior_probability', 'mean'), mean_raw=('raw_historical_frequency', 'mean'), min_weight=('candidate_weight', 'min')).reset_index())"
        elif i == 14:
            code = "print(EVIDENCE['fair_random_verification']['642']['synthetic_dp_normalizer'], EVIDENCE['fair_random_verification']['642']['synthetic_enumerated_normalizer'])\ndisplay(METRICS[METRICS.game == 'lotto_6_42'].groupby('model').agg(mean_nll=('actual_combination_nll_nats', 'mean'), max_marginal_sum_error=('marginal_inclusion_sum', lambda s: (s - 6).abs().max())).reset_index())"
        elif i == 15:
            code = "display(METRICS[METRICS.game == 'lotto_6_42'].groupby('model').agg(mean_nll=('actual_combination_nll_nats', 'mean'), mean_log_advantage=('log_score_advantage_vs_fair', 'mean'), mean_hits_at_6=('hits_at_6', 'mean'), marginal_brier=('marginal_brier', 'mean')).reset_index())"
        elif i == 16:
            code = "rows = []\nfor game, models in EVIDENCE['combination_validation'].items():\n    for model, stats in models['models'].items():\n        rows.append({'game': game, 'model': model, 'mean_log_score_advantage_vs_fair': stats['mean_log_score_advantage_vs_fair'], 'bootstrap_ci95': EVIDENCE['bootstrap'][game][model]['bootstrap_ci95_vs_fair'], 'mc_p': EVIDENCE['fair_random_monte_carlo'][game].get('models', {}).get(model, {}).get('empirical_p_add_one')})\ndisplay(pd.DataFrame(rows))\nfor game, group in METRICS.groupby('game'):\n    for model, sub in group.groupby('model'):\n        if model == 'fair_random': continue\n        sub = sub.sort_values(['draw_date', 'source_row'])\n        plt.plot(range(1, len(sub)+1), sub.log_score_advantage_vs_fair.cumsum(), label=f'{game}: {model}')\nplt.axhline(0, color='black', linewidth=.7); plt.title('Cumulative validation log-score advantage over fair'); plt.xlabel('Chronological validation draw'); plt.ylabel('Cumulative log-score difference'); plt.legend(fontsize=7); plt.tight_layout(); plt.show()"
        elif i == 17:
            code = "display(pd.DataFrame([EVIDENCE['decision_evidence']]))\nprint('Information diagnostics with BH q < .05:', int((INFO.bh_q_within_game < .05).sum()))"
        elif i == 18:
            code = "print('No physical machine-state variables, quantum observables, player-choice data, or payout-sharing data were used.')\nprint(EVIDENCE['limitations'])"
        else:
            code = "print('Verdict:', EVIDENCE['verdict'])\nprint('Safest next action:', EVIDENCE['safest_next_action'])"
        if i == 0:
            cells.append(nbformat.v4.new_code_cell(setup + "\n" + code))
        else:
            cells.append(nbformat.v4.new_code_cell(code))
    nb.cells = cells
    nbformat.validate(nb)
    return nb


def execute_notebook(notebook: Any) -> tuple[Any, dict[str, Any]]:
    import nbclient
    import nbformat

    notebook_path = ROOT / "notebooks/lotto_phase5r_predictive_information.ipynb"
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, notebook_path)
    client = nbclient.NotebookClient(notebook, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
    executed = client.execute()
    nbformat.validate(executed)
    code_cells = [cell for cell in executed.cells if cell.cell_type == "code"]
    errors = [output for cell in code_cells for output in cell.get("outputs", []) if output.get("output_type") == "error"]
    require(not errors, "FAILED: Phase 5R notebook contains an execution error")
    nbformat.write(executed, notebook_path)
    return executed, {
        "executed_top_to_bottom_in_clean_kernel": True,
        "kernel_name": "python3",
        "code_cell_count": len(code_cells),
        "nbformat_validation": "PASS",
        "execution_errors": 0,
    }


def validate_prior_phase_unchanged(prior_hashes: dict[str, str]) -> dict[str, Any]:
    after = {relative_path: sha256_file(ROOT / relative_path) for relative_path in prior_hashes}
    changed = sorted(path for path in prior_hashes if after[path] != prior_hashes[path])
    require(not changed, f"FAILED: canonical Phase 1 through Phase 5A artifacts changed: {changed}")
    return {"all_prior_phase_artifacts_unchanged": True, "artifact_count": len(after), "prior_artifact_hashes": after}


def validate_generated_whitespace() -> None:
    for relative_path in PHASE5R_PATHS:
        path = ROOT / relative_path
        if not path.is_file() or path.suffix.lower() == ".ipynb":
            continue
        text = path.read_text(encoding="utf-8")
        bad = [line_number for line_number, line in enumerate(text.splitlines(), 1) if line.rstrip(" \t") != line]
        require(not bad, f"FAILED: trailing whitespace in {relative_path} on lines {bad[:5]}")


def validate_final_git_state() -> dict[str, Any]:
    statuses, paths = status_paths()
    require(all(status == "??" for status in statuses), "FAILED: Phase 5R changed a tracked file or staged content")
    observed = set(paths)
    expected = EXPECTED_PREEXISTING_UNTRACKED | PHASE5R_PATHS
    require(observed == expected, f"FAILED: final untracked paths outside Phase 5R scope: {sorted(observed ^ expected)}")
    return {
        "tracked_worktree_clean": True,
        "index_clean": True,
        "preexisting_untracked_preserved": True,
        "new_phase5r_paths": sorted(PHASE5R_PATHS),
        "final_porcelain_paths": sorted(paths),
        "stage_commit_push_merge_performed": False,
    }


def information_method_summary() -> dict[str, Any]:
    return {
        "diagnostic_families": [
            "previous_10_frequency", "previous_30_frequency", "previous_100_frequency",
            "expanding_historical_frequency", "gap_since_seen", "previous_draw_appearance",
            "previous_100_frequency_deviation", "approved_draw_context",
        ],
        "feature_binning": "candidate-specific training quantile cutpoints at 20, 40, 60, and 80 percent; context family statistic is the maximum over predeclared context variables and is re-maximized for every permutation",
        "statistic": "mean candidate-level discrete mutual information in nats between prior-only feature bins and next-draw membership or 3D multiplicity count",
        "permutation_unit": "complete target draw rows, preserving each 3D multiset or 6/42 set; recompute the previous-only feature history after every permutation",
        "permutations": PERMUTATIONS,
        "multiple_testing": "Benjamini-Hochberg across every predefined family and response measure within each game",
        "training_only": True,
        "burn_in_draws_within_train_partition": TRAIN_ONLY_BURN_IN,
        "interpretation": "in-sample training diagnostics under a random-order null; validation is reserved for chronological development scoring",
    }


def run_analysis() -> dict[str, Any]:
    import nbformat

    require(sys.version_info >= (3, 10), "BLOCKED: Python 3.10 or newer is required")
    rng = np.random.Generator(np.random.PCG64(SEED))
    preflight, prior_hashes = verify_prior_phase_state()
    print(f"[phase5r] preflight passed on {preflight['branch']} {preflight['head']}", flush=True)
    self_check_result = self_checks()
    print("[phase5r] mathematical and future-perturbation self-checks passed", flush=True)
    data = load_development_data()
    print("[phase5r] train and validation prefixes loaded; locked test rows parsed: 0", flush=True)
    information_rows: list[dict[str, Any]] = []
    permutation_rows: list[dict[str, Any]] = []
    temporal_rows: list[dict[str, Any]] = []
    stationarity_rows: list[dict[str, Any]] = []
    stationarity_summaries: dict[str, Any] = {}
    combination_validation: dict[str, Any] = {}
    combination_csv_rows: list[dict[str, Any]] = []
    shrinkage_csv_rows: list[dict[str, Any]] = []
    bootstrap_results: dict[str, Any] = {}
    monte_carlo_results: dict[str, Any] = {}
    calibration_results: dict[str, Any] = {}

    for game, game_data in data.items():
        train_n = game_data["train_n"]
        y_train = game_data["targets"][:train_n].astype(np.int16)
        print(f"[phase5r] starting {game} information diagnostics", flush=True)
        information, permutation_stats = information_permutations(game, y_train, rng)
        information_rows.extend(information)
        permutation_rows.extend(permutation_stats)

        print(f"[phase5r] {game} information tests complete; bootstrapping temporal rates", flush=True)
        temporal_groups = phase4_temporal_groups(game, game_data, y_train)
        temporal_rows.extend(temporal_bootstrap(game, y_train, temporal_groups, rng))

        print(f"[phase5r] {game} temporal diagnostics complete; running stationarity checks", flush=True)
        station_rows, station_summary = stationarity_analysis(
            game, game_data["targets"], game_data["dates"], rng
        )
        stationarity_rows.extend(station_rows)
        stationarity_summaries[game] = station_summary

        print(f"[phase5r] {game} stationarity checks complete; scoring validation forecasts", flush=True)
        combo_rows, combo_summary, shrink_rows, scores = validation_probability_models(game, game_data, rng)
        combination_csv_rows.extend(combo_rows)
        shrinkage_csv_rows.extend(shrink_rows)
        bootstrap_results[game] = bootstrap_score_comparisons(scores, rng)
        calibration_results[game] = {
            model: calibration_assessment(score["marginal_prediction"], score["marginal_actual"], rng)
            for model, score in scores.items()
        }
        monte_carlo_results[game] = fair_random_monte_carlo(game, scores, rng)
        combination_validation[game] = combo_summary
        print(f"[phase5r] {game} validation scoring and fair-null simulation complete", flush=True)

    verdict, decision_evidence = decision_verdict(
        information_rows, bootstrap_results, monte_carlo_results, calibration_results
    )
    fair_probs = multiset_probabilities(np.full(10, 0.1), multiset_catalog()[1], multiset_catalog()[2])
    fair_random = {
        "3d": {
            "multiset_count": 220,
            "fair_probability_sum": float(fair_probs.sum()),
            "all_distinct_probability_each": 0.006,
            "one_pair_probability_each": 0.003,
            "triple_probability_each": 0.001,
            "ordered_outcomes": 1000,
            "fair_model_computed_from_multinomial_coefficients": True,
        },
        "642": {
            "valid_set_count": math.comb(42, 6),
            "fair_normalizer": elementary_symmetric(np.ones(42), 6),
            "fair_probability_each": 1.0 / math.comb(42, 6),
            "synthetic_dp_normalizer": self_check_result["642_synthetic_dp_normalizer"],
            "synthetic_enumerated_normalizer": self_check_result["642_synthetic_enumerated_normalizer"],
            "weighted_model_support": "all six-element subsets of 42 positive-weight candidates; all support outcomes contain six distinct numbers",
            "exact_normalizer_method": "sixth elementary symmetric polynomial computed by descending-order dynamic programming",
        },
    }
    split = read_json(ROOT / "data/features/chronological_splits.json")
    data_boundaries = {
        game: {
            name: {
                "row_count": split["games"][game]["partitions"][name]["row_count"],
                "start_date": split["games"][game]["partitions"][name]["start_date"],
                "end_date": split["games"][game]["partitions"][name]["end_date"],
            }
            for name in ("train", "validation", "test")
        }
        for game in data
    }
    data_read_audit = {
        game: {
            "train_rows_parsed": item["train_n"],
            "validation_rows_parsed": item["validation_n"],
            "dev_rows_parsed": item["dev_read_rows"],
            "locked_test_rows_parsed": item["locked_test_rows_parsed"],
            "read_method": "CSV prefix parser stops after the Phase 4 train plus validation row count",
            "feature_target_keys_aligned": True,
            "target_structure_validated_in_dev_prefix": True,
        }
        for game, item in data.items()
    }
    shrinkage_summary = summarize_shrinkage(shrinkage_csv_rows)
    info_significant = sum(row["bh_q_within_game"] < ALPHA for row in information_rows)
    limitations = [
        "Phase 5A already examined the validation partitions; Phase 5R validation is development evidence, not pristine confirmation.",
        "The Monte Carlo fair-null test holds the observed leakage-safe forecast path fixed and simulates complete fair validation outcomes conditionally.",
        "The information tests are finite-sample candidate-level diagnostics on the training sequence and do not imply full-combination utility.",
        "Stationarity and change-point tests can detect statistical variation but cannot identify a machine, ball, environmental, or physical cause.",
        "Physical dynamics require machine state, ball properties, airflow, timing, temperature, humidity, or video trajectory data.",
        "Quantum methods are not predictors supported by the available variables; player-choice and payout-sharing data are absent for game-theoretic expected-payout analysis.",
        "No probability calibration acceptance threshold was specified in the request; the reported 95% bootstrap screen is used descriptively and as a conservative promotion gate.",
    ]
    safest_next_action = (
        "Stop model expansion and keep the locked test untouched. The current evidence does not justify freezing a Phase 5R candidate for the one-time test evaluation; use any future confirmation only in a separately authorized phase after an explicit model freeze."
        if verdict != "PHASE5R_PREDICTIVE_INFORMATION_DETECTED" else
        "Preserve the current artifacts and review the candidate model specification. Any one-time test evaluation still requires a separately authorized phase after freezing the exact model and preprocessing."
    )

    info_method = information_method_summary()
    validation_results = {
        "assert_based_3d_and_642_mathematical_self_checks": "PASS",
        "phase3_phase4_phase5a_preflight_and_hashes": "PASS",
        "train_validation_only_prefix_parsing": "PASS",
        "target_structure_and_feature_key_alignment": "PASS",
        "phase4_split_boundaries_preserved": "PASS",
        "3d_all_220_probabilities_normalized_for_every_validation_forecast": "PASS",
        "642_exact_elementary_symmetric_normalizer_and_valid_six_set_support": "PASS",
        "temporal_features_use_only_information_before_target": "PASS by Phase 4 evidence and the Phase 5R recomputation audit",
        "information_and_change_point_permutations": "PASS",
        "bootstrap_and_monte_carlo_counts": "PASS",
        "locked_test_rows_parsed_or_scored": "NO",
        "jev_typesafe_or_keys_env_contents_accessed": "NO",
    }

    output_fields = {
        "information": list(information_rows[0]) if information_rows else [],
        "permutations": list(permutation_rows[0]) if permutation_rows else [],
        "temporal": list(temporal_rows[0]) if temporal_rows else [],
        "stationarity": list(dict.fromkeys(key for row in stationarity_rows for key in row)),
        "shrinkage": list(shrinkage_csv_rows[0]) if shrinkage_csv_rows else [],
        "combination": list(combination_csv_rows[0]) if combination_csv_rows else [],
    }
    outputs = {
        "reports/phase5r_information_tests.csv": information_rows,
        "reports/phase5r_information_permutations.csv": permutation_rows,
        "reports/phase5r_temporal_dependence.csv": temporal_rows,
        "reports/phase5r_stationarity.csv": stationarity_rows,
        "reports/phase5r_bayesian_shrinkage.csv": shrinkage_csv_rows,
        "reports/phase5r_combination_probability_metrics.csv": combination_csv_rows,
    }
    field_map = {
        "reports/phase5r_information_tests.csv": "information",
        "reports/phase5r_information_permutations.csv": "permutations",
        "reports/phase5r_temporal_dependence.csv": "temporal",
        "reports/phase5r_stationarity.csv": "stationarity",
        "reports/phase5r_bayesian_shrinkage.csv": "shrinkage",
        "reports/phase5r_combination_probability_metrics.csv": "combination",
    }
    for relative_path, rows in outputs.items():
        write_csv(ROOT / relative_path, rows, output_fields[field_map[relative_path]])

    base_evidence: dict[str, Any] = {
        "schema_version": 1,
        "phase": "PHASE_5R",
        "verdict": verdict,
        "research_question": "Given only information available before draw t, does the historical record contain enough information to assign a next-draw combination probability distribution that performs better than the appropriate fair-random baseline on chronological validation data?",
        "repository": {"path": str(ROOT.resolve()), "branch": preflight["branch"], "head": preflight["head"], "configured_remotes": preflight["configured_remotes"]},
        "preflight": preflight,
        "data_boundaries": data_boundaries,
        "data_read_audit": data_read_audit,
        "fair_random_verification": fair_random,
        "information_method": info_method,
        "information_tests": information_rows,
        "significant_information_diagnostics_bh_q_lt_0_05": info_significant,
        "temporal_summary": {
            game: {
                "rows": sum(1 for row in temporal_rows if row["game"] == game),
                "bootstrap_resamples": BOOTSTRAPS,
                "feature_groups": sorted({row["feature_group"] for row in temporal_rows if row["game"] == game}),
            }
            for game in data
        },
        "stationarity": stationarity_summaries,
        "shrinkage": shrinkage_summary,
        "combination_validation": combination_validation,
        "bootstrap": bootstrap_results,
        "fair_random_monte_carlo": monte_carlo_results,
        "calibration": calibration_results,
        "decision_evidence": decision_evidence,
        "limitations": limitations,
        "safest_next_action": safest_next_action,
        "security": {
            "keys_env_ignored": True,
            "keys_env_tracked": False,
            "keys_env_contents_read": False,
            "jev_invoked": False,
            "typesafe_invoked": False,
            "locked_test_targets_parsed": False,
        },
        "git_actions": {"stage": False, "commit": False, "push": False, "merge": False},
        "self_checks": self_check_result,
        "validation": validation_results,
        "random_seed": SEED,
        "bit_generator": "PCG64",
    }
    (ROOT / "reports/phase5r_evidence.json").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "reports/phase5r_evidence.json").write_text(
        json.dumps(json_safe(base_evidence), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    report = render_report(base_evidence)
    (ROOT / "reports/phase5r_predictive_information.md").write_text(report, encoding="utf-8")
    notebook = build_notebook(base_evidence)
    executed_notebook, nb_run = execute_notebook(notebook)
    nbformat.validate(executed_notebook)
    print("[phase5r] clean-kernel notebook execution passed", flush=True)

    prior_unchanged = validate_prior_phase_unchanged(prior_hashes)
    final_git = validate_final_git_state()
    diff_check = git("diff", "--check")
    require(diff_check.returncode == 0, f"FAILED: git diff --check failed: {diff_check.stdout}{diff_check.stderr}")
    validate_generated_whitespace()
    base_evidence["validation"].update({
        "clean_kernel_notebook_execution": "PASS",
        "nbformat_validation": "PASS",
        "git_diff_check": "PASS",
        "generated_text_whitespace_check": "PASS",
        "prior_phase_artifact_integrity": "PASS",
    })
    base_evidence["notebook_execution"] = nb_run
    base_evidence["prior_phase_integrity"] = prior_unchanged
    base_evidence["final_git_state"] = final_git
    base_evidence["output_sha256"] = {
        relative_path: sha256_file(ROOT / relative_path)
        for relative_path in sorted(PHASE5R_PATHS - {"reports/phase5r_evidence.json"})
    }
    (ROOT / "reports/phase5r_evidence.json").write_text(
        json.dumps(json_safe(base_evidence), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    report = render_report(base_evidence)
    (ROOT / "reports/phase5r_predictive_information.md").write_text(report, encoding="utf-8")
    # The notebook's opening cell reads the finalized machine-readable evidence, so execute it once more after the final evidence write.
    notebook = build_notebook(base_evidence)
    executed_notebook, nb_run = execute_notebook(notebook)
    nbformat.validate(executed_notebook)
    base_evidence["notebook_execution"] = nb_run
    base_evidence["output_sha256"]["notebooks/lotto_phase5r_predictive_information.ipynb"] = sha256_file(ROOT / "notebooks/lotto_phase5r_predictive_information.ipynb")
    base_evidence["output_sha256"]["reports/phase5r_predictive_information.md"] = sha256_file(ROOT / "reports/phase5r_predictive_information.md")
    (ROOT / "reports/phase5r_evidence.json").write_text(
        json.dumps(json_safe(base_evidence), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )

    final_git = validate_final_git_state()
    base_evidence["final_git_state"] = final_git
    (ROOT / "reports/phase5r_evidence.json").write_text(
        json.dumps(json_safe(base_evidence), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return base_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check-only", action="store_true", help="run analytical self-checks without reading project data or writing artifacts")
    args = parser.parse_args()
    if args.self_check_only:
        print(json.dumps(self_checks(), indent=2, sort_keys=True))
        return 0
    try:
        evidence = run_analysis()
    except Phase5RError as error:
        print(f"{error.__class__.__name__}: {error}", file=sys.stderr)
        return 2
    print(json.dumps({
        "verdict": evidence["verdict"],
        "branch": evidence["repository"]["branch"],
        "head": evidence["repository"]["head"],
        "significant_information_diagnostics": evidence["significant_information_diagnostics_bh_q_lt_0_05"],
        "outputs": sorted(PHASE5R_PATHS),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
