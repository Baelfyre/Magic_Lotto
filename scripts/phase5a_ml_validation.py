# @codebase_provenance_JEO
"""Run Phase 5A leakage-safe model selection and validation backtests."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "models" / "phase5a_model_config.json"
METRICS_PATH = ROOT / "reports" / "phase5a_metrics.json"
VALIDATION_PATH = ROOT / "reports" / "phase5a_validation.json"
REPORT_PATH = ROOT / "reports" / "phase5a_ml_validation.md"
PREDICTION_DIR = ROOT / "reports" / "phase5a_validation_predictions"
PREDICTION_3D = PREDICTION_DIR / "3d_validation_predictions.csv"
PREDICTION_642 = PREDICTION_DIR / "642_validation_predictions.csv"
SIMULATION_PATH = ROOT / "reports" / "phase5a_random_baseline_distributions.csv"
NOTEBOOK_PATH = ROOT / "notebooks" / "lotto_phase5a_ml_validation.ipynb"
PHASE4_REPORT_PATH = ROOT / "reports" / "phase4_validation.json"
SPLIT_PATH = ROOT / "data" / "features" / "chronological_splits.json"
DICTIONARY_PATH = ROOT / "data" / "features" / "feature_dictionary.json"
PHASE4_NOTEBOOK_PATH = ROOT / "notebooks" / "lotto_phase4_feature_engineering.ipynb"

PHASE1_TO3_HASHES = {
    "swertres9pm.md": "b8c1e1f762c8b3059956d96b344804498bc20bc9f174a358fc616ae115ecb1a3",
    "6-42.csv": "9d8bf396373cd20ac197f423ed245407fa701bbd28895b2bb55e1dca92e3e8a8",
    "swertres_9pm_cleaned_normalized.csv": "3118bc4972bbff55db6029342701c870ca3e4735e26ddcdf6bbe86ee018836cc",
    "swertres_9pm_analysis_ready.csv": "bed32547054a819e108f18d53af73db1f74db693202db066c64572846860959b",
    "swertres_9pm_phase2_analysis.csv": "3b207b356349c0bf4e1677979c1077bea434071508e3f835e4fc75e9997d7d72",
    "swertres_9pm_digit_frequency.csv": "4ad90a87cbaaca99a08001904b7bbef18e1561ed4b9c5a138f0253729b359681",
    "lotto_6_42_cleaned_normalized.csv": "980386a399077564d25de3a3a19aa3611969899895b9e3c06d7e9406599053a0",
    "lotto_6_42_phase2_analysis.csv": "a7ff6ac667ab9a4dd83c821ca6a7ad94b2866ab15299f5f0ad7e47818ac32958",
    "lotto_6_42_number_frequency.csv": "1284586aaccc86f43da2e9676f425842dbf171dde36d8d8da2b4027789252456",
    "lotto_data_cleaning_report.md": "5f3f0c99e9610781c64c2f5a1b8a2e057534a3202c781287ad00b37f38218850",
    "phase2_randomness_diagnostics.md": "c6318f74cc5685108f4bb278d6293b84771e0c29af7250888a789aec365cbce7",
    "monte_carlo_baseline.py": "31cd14b519af3457f2de5f55e836a1899d8751a8bb492faeb663b5ba10f7fe19",
    "phase3_monte_carlo_results.json": "79d131a68f913e43f3f8eabfac3f7ab557017216c623b893f283b72d8bbaa3b3",
    "phase3_monte_carlo_random_baseline.md": "f4105e6a40277c40e5374c9120e853050931b25b1dbb62a0b70fefee2c603f73",
    "phase3_simulation_distributions.csv": "c8dc4d390ae941bef8429f9d9c9564897b98f61e80eeb5738614e35ce161f43a",
    "notebooks/lotto_statistical_analysis.ipynb": "24d7e03e75d8c41a97ade1c826aae3a83e5b487de263d37b3165eac7b02dc1ae",
}

PHASE4_OUTPUT_PATHS = (
    "data/features/3d_features.csv",
    "data/features/3d_targets.csv",
    "data/features/642_features.csv",
    "data/features/642_targets.csv",
    "data/features/chronological_splits.json",
    "data/features/feature_dictionary.json",
    "reports/phase4_validation.json",
    "reports/phase4_feature_engineering.md",
    "scripts/phase4_feature_engineering.py",
    "notebooks/lotto_phase4_feature_engineering.ipynb",
)

PHASE5_OUTPUT_PATHS = (
    "scripts/phase5a_ml_validation.py",
    "models/phase5a_model_config.json",
    "reports/phase5a_validation_predictions/3d_validation_predictions.csv",
    "reports/phase5a_validation_predictions/642_validation_predictions.csv",
    "reports/phase5a_metrics.json",
    "reports/phase5a_random_baseline_distributions.csv",
    "reports/phase5a_validation.json",
    "reports/phase5a_ml_validation.md",
    "notebooks/lotto_phase5a_ml_validation.ipynb",
)

PHASE3_PRIOR_PATHS = (
    "__pycache__/monte_carlo_baseline.cpython-312.pyc",
    "monte_carlo_baseline.py",
    "phase3_monte_carlo_random_baseline.md",
    "phase3_monte_carlo_results.json",
    "phase3_simulation_distributions.csv",
    "notebooks/lotto_statistical_analysis.ipynb",
)

DATASET_FILES = {
    "3d_lotto": {
        "features": "data/features/3d_features.csv",
        "targets": "data/features/3d_targets.csv",
        "target_columns": [f"target_digit_{digit}" for digit in range(10)],
        "feature_key": "3d_lotto",
        "code": 3,
    },
    "lotto_6_42": {
        "features": "data/features/642_features.csv",
        "targets": "data/features/642_targets.csv",
        "target_columns": [f"target_{number:02d}" for number in range(1, 43)],
        "feature_key": "lotto_6_42",
        "code": 642,
    },
}

MODEL_NAMES = {
    "3d_lotto": "multinomial_logistic_regression",
    "lotto_6_42": {
        "logistic": "regularized_one_vs_rest_logistic_regression",
        "forest": "random_forest_multioutput_comparator",
    },
}


class Phase5AError(RuntimeError):
    """Raised when a Phase 5A gate fails closed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5AError(message)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(result.returncode == 0, f"Git command failed: git {' '.join(args)}")
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    require(path.is_file(), f"Required JSON file is missing: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def raw_csv_data_rows(path: Path) -> int:
    """Count physical data lines only; do not parse any target cell values."""
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return max(0, sum(1 for _ in stream) - 1)


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return next(csv.reader(stream), [])


def feature_group_names(columns: list[str]) -> dict[str, list[str]]:
    groups = {
        "frequency_and_deviation": [],
        "recency_and_gap": [],
        "draw_context": [],
        "all_features": list(columns),
    }
    for name in columns:
        if (
            ("_count_prev_" in name and not name.endswith("_count_prev_draw"))
            or name.endswith("_expanding_count")
            or name.endswith("_freq_expanding")
            or name.endswith("_freq_deviation_prev_100")
        ):
            groups["frequency_and_deviation"].append(name)
        elif (
            name.endswith("_gap_since_seen")
            or name.endswith("_never_seen")
            or name.endswith("_seen_prev_draw")
            or name.endswith("_count_prev_draw")
        ):
            groups["recency_and_gap"].append(name)
        else:
            groups["draw_context"].append(name)
    require(
        set(groups["frequency_and_deviation"])
        | set(groups["recency_and_gap"])
        | set(groups["draw_context"])
        == set(columns),
        "Feature groups do not cover all feature columns.",
    )
    require(
        sum(len(groups[name]) for name in ("frequency_and_deviation", "recency_and_gap", "draw_context"))
        == len(columns),
        "Feature groups overlap.",
    )
    return groups


def verify_initial_status(phase4: dict, run_mode: bool) -> dict:
    top = Path(git("rev-parse", "--show-toplevel")).resolve()
    require(top == ROOT.resolve(), "Unexpected Git worktree root.")
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    require(branch and len(head) == 40, "Branch or HEAD could not be verified.")
    require(
        branch == phase4["repository"]["branch"] and head == phase4["repository"]["head"],
        "Live branch or HEAD conflicts with the Phase 4 approved baseline.",
    )
    require(
        git("diff", "--quiet") == "",
        "Tracked worktree has changes; Phase 5A preflight blocked.",
    )
    require(
        git("diff", "--cached", "--quiet") == "",
        "Git index has staged changes; Phase 5A preflight blocked.",
    )
    remotes = [row for row in git("remote", "-v").splitlines() if row]
    require(
        remotes == phase4["repository"].get("configured_remotes", []),
        "Configured remotes changed since Phase 4.",
    )

    tracked = {name for name in git("ls-files").splitlines()}
    require(
        not any(Path(name).name.casefold() == "keys.env" for name in tracked),
        "BLOCKED_SECRET_TRACKED",
    )
    ignore = subprocess.run(
        ["git", "check-ignore", "-q", "--", "Keys.env"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    require(ignore.returncode == 0, "Keys.env is not ignored by Git.")

    status_lines = git("status", "--porcelain=v1", "--untracked-files=all").splitlines()
    changed = {
        line[3:].replace("\\", "/")
        for line in status_lines
        if len(line) >= 4
    }
    allowed = (
        set(PHASE1_TO3_HASHES)
        | set(PHASE4_OUTPUT_PATHS)
        | set(PHASE3_PRIOR_PATHS)
        | set(PHASE5_OUTPUT_PATHS)
    )
    unexpected = sorted(changed - allowed)
    require(not unexpected, f"Unexpected worktree paths: {unexpected}")
    if run_mode:
        if VALIDATION_PATH.is_file():
            existing_validation = read_json(VALIDATION_PATH)
            require(
                existing_validation.get("verdict")
                == "PHASE5A_IN_PROGRESS_AWAITING_NOTEBOOK_VALIDATION",
                "Completed Phase 5A outputs exist; refusing to overwrite them.",
            )
    return {
        "repository": str(ROOT.resolve()),
        "branch": branch,
        "head": head,
        "configured_remotes": remotes,
        "tracked_worktree_clean": True,
        "index_clean": True,
        "keys_env_ignored": True,
        "keys_env_tracked": False,
        "keys_env_contents_read": False,
        "pre_modification_status_snapshot": [
            "## main",
            "?? __pycache__/monte_carlo_baseline.cpython-312.pyc",
            "?? data/features/3d_features.csv",
            "?? data/features/3d_targets.csv",
            "?? data/features/642_features.csv",
            "?? data/features/642_targets.csv",
            "?? data/features/chronological_splits.json",
            "?? data/features/feature_dictionary.json",
            "?? monte_carlo_baseline.py",
            "?? notebooks/lotto_phase4_feature_engineering.ipynb",
            "?? notebooks/lotto_statistical_analysis.ipynb",
            "?? phase3_monte_carlo_random_baseline.md",
            "?? phase3_monte_carlo_results.json",
            "?? phase3_simulation_distributions.csv",
            "?? reports/phase4_feature_engineering.md",
            "?? reports/phase4_validation.json",
            "?? scripts/phase4_feature_engineering.py",
        ],
        "live_porcelain_status": status_lines,
    }


def validate_phase4_artifacts(np, pd, config: dict) -> dict:
    p4 = read_json(PHASE4_REPORT_PATH)
    require(
        p4.get("verdict") == "PHASE4_PASS_READY_FOR_ML_BASELINE",
        "Phase 4 validation verdict is not PASS_READY_FOR_ML_BASELINE.",
    )
    critical_checks = (
        "canonical_phase1_to_phase3_inputs",
        "chronological_splits",
        "deterministic_two_build_hashes",
        "feature_target_key_alignment",
        "notebook_execution_and_nbformat",
        "target_invariants_3d",
        "target_invariants_6_42",
        "temporal_leakage_audits",
    )
    require(
        all(p4["validation_checks"].get(name) == "PASS" for name in critical_checks),
        "One or more Phase 4 validation checks are not PASS.",
    )
    require(
        p4["validation_checks"].get("test_performance_calculated") is False
        and p4["validation_checks"].get("model_training_performed") is False
        and p4["validation_checks"].get("jev_or_typesafe_called") is False,
        "Phase 4 scope or test boundary is inconsistent.",
    )
    for name, expected in p4["canonical_input_hashes"].items():
        path = ROOT / name
        require(path.is_file(), f"Phase 2 canonical input missing: {name}")
        require(sha256_file(path) == expected, f"Phase 2 input hash mismatch: {name}")
    p3 = read_json(ROOT / "phase3_monte_carlo_results.json")
    require(p3.get("verdict") == "PHASE3_PASS_RANDOM_COMPATIBLE", "Phase 3 verdict is not PASS.")
    for entry in p3.get("inputs", {}).values():
        name = Path(entry.get("path", "")).name
        if name in p4["canonical_input_hashes"]:
            require(
                sha256_file(ROOT / name) == entry.get("sha256"),
                f"Phase 3 recorded input hash mismatch: {name}",
            )

    for name, expected in PHASE1_TO3_HASHES.items():
        path = ROOT / name
        require(path.is_file(), f"Phase 1 through Phase 3 artifact missing: {name}")
        require(sha256_file(path) == expected, f"Phase 1 through Phase 3 hash mismatch: {name}")
    p4_output_hashes = p4["reproducibility"]["artifact_hashes"]
    for name, expected in p4_output_hashes.items():
        path = ROOT / name
        require(path.is_file(), f"Phase 4 output missing: {name}")
        require(sha256_file(path) == expected, f"Phase 4 output hash mismatch: {name}")

    split = read_json(SPLIT_PATH)
    feature_dictionary = read_json(DICTIONARY_PATH)
    require(split.get("test_partition_locked") is True, "Phase 4 test partition is not locked.")
    require(split.get("shuffle") is False, "Phase 4 chronology was shuffled.")
    require(sha256_file(SPLIT_PATH) == p4_output_hashes["data/features/chronological_splits.json"],
            "Phase 4 split manifest hash changed.")
    notebook = read_json(PHASE4_NOTEBOOK_PATH)
    code_cells = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code"]
    require(len(code_cells) == p4["notebook_execution"]["code_cells"], "Phase 4 notebook cell count differs.")
    require(
        all(cell.get("execution_count") is not None for cell in code_cells)
        and not any(out.get("output_type") == "error" for cell in code_cells for out in cell.get("outputs", [])),
        "Phase 4 notebook is not fully executed without errors.",
    )

    data = {}
    partition_metadata = {}
    for game, spec in DATASET_FILES.items():
        game_manifest = split["games"][game]
        parts = game_manifest["partitions"]
        n_train = parts["train"]["row_count"]
        n_validation = parts["validation"]["row_count"]
        n_test = parts["test"]["row_count"]
        n_eligible = game_manifest["eligible_rows"]
        val_start = parts["validation"]["row_index_start_in_eligible_matrix"]
        val_end = parts["validation"]["row_index_end_exclusive"]
        test_start = parts["test"]["row_index_start_in_eligible_matrix"]
        test_end = parts["test"]["row_index_end_exclusive"]
        require(
            parts["train"]["row_index_start_in_eligible_matrix"] == 0
            and parts["train"]["row_index_end_exclusive"] == n_train
            and val_start == n_train
            and val_end == n_train + n_validation
            and test_start == val_end
            and test_end == n_eligible
            and n_train + n_validation + n_test == n_eligible,
            f"{game} split boundaries do not match the Phase 4 manifest.",
        )
        feature_path = ROOT / spec["features"]
        target_path = ROOT / spec["targets"]
        require(feature_path.is_file() and target_path.is_file(), f"{game} Phase 4 files are missing.")
        require(raw_csv_data_rows(feature_path) == n_eligible, f"{game} feature row count differs from manifest.")
        require(raw_csv_data_rows(target_path) == n_eligible, f"{game} target row count differs from manifest.")

        keys = ["draw_date", "source_row"]
        expected_features = list(p4["games"][game]["feature_columns"])
        require(
            set(expected_features) == set(feature_dictionary[spec["feature_key"]]["features"]),
            f"{game} feature dictionary columns differ from the Phase 4 validation report.",
        )
        feature_header = csv_header(feature_path)
        target_header = csv_header(target_path)
        require(feature_header == keys + expected_features, f"{game} feature header differs from dictionary.")
        require(target_header == keys + spec["target_columns"], f"{game} target header is invalid.")
        require(len(feature_header) == len(set(feature_header)), f"{game} feature headers are not unique.")
        require(len(target_header) == len(set(target_header)), f"{game} target headers are not unique.")
        require(
            len(expected_features) == feature_dictionary[spec["feature_key"]]["feature_count"],
            f"{game} feature dictionary count is invalid.",
        )

        # Explicitly load only the train-plus-validation prefix. No test feature or target rows are parsed.
        feature_frame = pd.read_csv(feature_path, nrows=val_end)
        target_frame = pd.read_csv(target_path, nrows=val_end)
        require(len(feature_frame) == val_end and len(target_frame) == val_end,
                f"{game} train/validation prefix has an unexpected row count.")
        require(
            feature_frame[keys].astype(str).equals(target_frame[keys].astype(str)),
            f"{game} feature/target keys are misaligned in train/validation rows.",
        )
        dates = feature_frame["draw_date"].astype(str).to_numpy()
        require(list(dates) == sorted(dates), f"{game} train/validation rows are not chronological.")
        feature_names = [name for name in feature_frame.columns if name not in keys]
        require(feature_names == expected_features, f"{game} feature columns changed.")
        x = feature_frame[feature_names].to_numpy(dtype=np.float64)
        y_float = target_frame[spec["target_columns"]].to_numpy(dtype=np.float64)
        require(np.isfinite(x).all(), f"{game} feature matrix has null or non-finite values.")
        require(np.isfinite(y_float).all(), f"{game} train/validation targets have non-finite values.")
        require(np.equal(y_float, np.floor(y_float)).all(), f"{game} targets are not integer valued.")
        y = y_float.astype(np.int16)
        if game == "3d_lotto":
            require((y >= 0).all() and (y.sum(axis=1) == 3).all(), "3D target multiset invariant failed.")
        else:
            require(
                ((y == 0) | (y == 1)).all() and (y.sum(axis=1) == 6).all(),
                "Lotto 6/42 target set invariant failed.",
            )
        groups = feature_group_names(feature_names)
        data[game] = {
            "feature_frame": feature_frame,
            "feature_names": feature_names,
            "groups": groups,
            "x_train": x[:n_train],
            "x_validation": x[n_train:val_end],
            "y_train": y[:n_train],
            "y_validation": y[n_train:val_end],
            "train_dates": dates[:n_train],
            "validation_dates": dates[n_train:val_end],
            "train_end": n_train,
            "validation_end": val_end,
            "manifest": game_manifest,
        }
        partition_metadata[game] = {
            "eligible_rows": n_eligible,
            "train": parts["train"],
            "validation": parts["validation"],
            "test": parts["test"],
            "target_rows_parsed": val_end,
            "test_target_rows_parsed": 0,
        }
    return {
        "phase4": p4,
        "phase3": p3,
        "split": split,
        "feature_dictionary": feature_dictionary,
        "data": data,
        "partition_metadata": partition_metadata,
    }


def get_runtime_versions() -> dict:
    from importlib.metadata import PackageNotFoundError, version

    packages = ("numpy", "pandas", "scikit-learn", "scipy", "joblib", "threadpoolctl")
    result = {"python": sys.version.split()[0], "executable": sys.executable}
    for package in packages:
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = None
    return result


def fit_3d_model(np, StandardScaler, LogisticRegression, Pipeline, x, y, c_value: float):
    expanded_x = np.repeat(x, 3, axis=0)
    expanded_y = np.concatenate([np.repeat(np.arange(10), row.astype(int)) for row in y])
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    C=float(c_value),
                    solver="lbfgs",
                    max_iter=2000,
                    random_state=162,
                ),
            ),
        ]
    )
    model.fit(expanded_x, expanded_y)
    return model


def predict_3d_probabilities(np, model, x):
    raw = model.predict_proba(x)
    classifier = model.named_steps["logistic"]
    probabilities = np.zeros((len(x), 10), dtype=np.float64)
    probabilities[:, classifier.classes_.astype(int)] = raw
    return probabilities


def fit_642_logistic(np, StandardScaler, LogisticRegression, OneVsRestClassifier, Pipeline, x, y, c_value):
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "ovr",
                OneVsRestClassifier(
                    LogisticRegression(
                        C=float(c_value),
                        solver="liblinear",
                        penalty="l2",
                        max_iter=2000,
                        random_state=162,
                    ),
                    n_jobs=1,
                ),
            ),
        ]
    )
    model.fit(x, y)
    return model


def fit_642_forest(RandomForestClassifier, x, y, config):
    return RandomForestClassifier(
        n_estimators=config["n_estimators"],
        max_depth=config["max_depth"],
        min_samples_leaf=config["min_samples_leaf"],
        max_features=config["max_features"],
        bootstrap=True,
        random_state=162,
        n_jobs=1,
    ).fit(x, y)


def predict_642_probabilities(np, model, x, forest: bool):
    if forest:
        outputs = model.predict_proba(x)
        probabilities = np.zeros((len(x), len(outputs)), dtype=np.float64)
        for index, (classes, output) in enumerate(zip(model.classes_, outputs)):
            positive = np.flatnonzero(np.asarray(classes) == 1)
            if len(positive):
                probabilities[:, index] = output[:, positive[0]]
        return probabilities
    probabilities = model.predict_proba(x)
    if probabilities.ndim == 1:
        probabilities = probabilities.reshape(-1, 1)
    return probabilities


def normalize_rows(np, probabilities):
    probabilities = np.asarray(probabilities, dtype=np.float64)
    probabilities = np.clip(probabilities, 1e-15, 1.0)
    totals = probabilities.sum(axis=1, keepdims=True)
    return probabilities / totals


def multinomial_nll_per_draw(np, counts, probabilities):
    logp = np.log(np.clip(probabilities, 1e-15, 1.0))
    coefficient = np.array(
        [
            math.lgamma(4.0) - sum(math.lgamma(float(value) + 1.0) for value in row)
            for row in counts
        ],
        dtype=np.float64,
    )
    log_likelihood = coefficient + (counts * logp).sum(axis=1)
    return -log_likelihood / 3.0


def deterministic_multiset_counts(np, probabilities):
    counts = np.zeros_like(probabilities, dtype=np.int16)
    digits = np.arange(probabilities.shape[1])
    for row_index, row in enumerate(probabilities):
        scaled = row * 3.0
        base = np.floor(scaled).astype(int)
        remainder = int(3 - base.sum())
        if remainder:
            order = np.lexsort((digits, -(scaled - base)))
            base[order[:remainder]] += 1
        require(base.sum() == 3 and (base >= 0).all(), "Hamilton allocation failed.")
        counts[row_index] = base
    return counts


def multiset_overlap(np, actual, predicted):
    return np.minimum(actual, predicted).sum(axis=1).astype(np.int16)


def digit_brier_per_draw(np, counts, probabilities):
    label_mean = counts / 3.0
    return (
        (probabilities**2).sum(axis=1)
        - 2.0 * (probabilities * label_mean).sum(axis=1)
        + 1.0
    )


def expand_multiset_labels(np, counts, probabilities):
    labels = np.concatenate(
        [np.repeat(np.arange(counts.shape[1]), row.astype(int)) for row in counts]
    )
    expanded_probabilities = np.repeat(probabilities, 3, axis=0)
    one_hot = (labels[:, None] == np.arange(counts.shape[1])[None, :]).astype(np.uint8)
    return expanded_probabilities, one_hot


def top_k_indices(np, probabilities, k: int):
    return np.argsort(-probabilities, axis=1, kind="stable")[:, :k]


def six_set_metrics(np, y, probabilities):
    probabilities = np.clip(probabilities, 1e-12, 1.0 - 1e-12)
    predicted = np.zeros_like(y, dtype=np.uint8)
    top = top_k_indices(np, probabilities, 6)
    predicted[np.arange(len(y))[:, None], top] = 1
    hits = (predicted * y).sum(axis=1).astype(np.int16)
    recall = hits / 6.0
    jaccard = hits / np.maximum(12 - hits, 1)
    brier = ((probabilities - y) ** 2).mean(axis=1)
    logloss = -(
        y * np.log(probabilities) + (1 - y) * np.log(1 - probabilities)
    ).mean(axis=1)
    return {
        "prediction_matrix": predicted,
        "hits": hits,
        "recall": recall,
        "precision": recall.copy(),
        "jaccard": jaccard,
        "brier": brier,
        "marginal_log_loss": logloss,
        "match_distribution": {
            str(value): int((hits == value).sum()) for value in range(7)
        },
    }


def calibration_summary(np, probabilities, labels, bins=10):
    probabilities = np.asarray(probabilities, dtype=np.float64).ravel()
    labels = np.asarray(labels, dtype=np.float64).ravel()
    edges = np.linspace(0.0, 1.0, bins + 1)
    records = []
    weighted_error = 0.0
    total = len(probabilities)
    for index in range(bins):
        if index == bins - 1:
            mask = (probabilities >= edges[index]) & (probabilities <= edges[index + 1])
        else:
            mask = (probabilities >= edges[index]) & (probabilities < edges[index + 1])
        count = int(mask.sum())
        if count:
            mean_probability = float(probabilities[mask].mean())
            observed_rate = float(labels[mask].mean())
            weighted_error += count * abs(mean_probability - observed_rate)
        else:
            mean_probability = None
            observed_rate = None
        records.append(
            {
                "bin": index,
                "lower": float(edges[index]),
                "upper": float(edges[index + 1]),
                "count": count,
                "mean_probability": mean_probability,
                "observed_rate": observed_rate,
            }
        )
    return {
        "expected_calibration_error": float(weighted_error / max(total, 1)),
        "bins": records,
        "sample_count": total,
        "bin_count": bins,
    }


def metric_summary_3d(np, counts, probabilities):
    probabilities = normalize_rows(np, probabilities)
    predicted = deterministic_multiset_counts(np, probabilities)
    overlap = multiset_overlap(np, counts, predicted)
    expanded_probabilities, one_hot = expand_multiset_labels(np, counts, probabilities)
    calibration = calibration_summary(np, expanded_probabilities, one_hot)
    return {
        "mean_multinomial_negative_log_likelihood_per_digit": float(
            multinomial_nll_per_draw(np, counts, probabilities).mean()
        ),
        "mean_multiset_overlap": float(overlap.mean()),
        "digit_level_multiclass_brier": float(digit_brier_per_draw(np, counts, probabilities).mean()),
        "deterministic_overlap_distribution": {
            str(value): int((overlap == value).sum()) for value in range(4)
        },
        "deterministic_prediction_counts": predicted,
        "per_draw_nll": multinomial_nll_per_draw(np, counts, probabilities),
        "per_draw_overlap": overlap,
        "per_draw_brier": digit_brier_per_draw(np, counts, probabilities),
        "calibration": calibration,
        "probabilities": probabilities,
    }


def metric_summary_642(np, y, probabilities):
    summary = six_set_metrics(np, y, probabilities)
    calibration = calibration_summary(np, probabilities, y)
    return {
        "mean_hits_at_6": float(summary["hits"].mean()),
        "mean_recall_at_6": float(summary["recall"].mean()),
        "mean_precision_at_6": float(summary["precision"].mean()),
        "mean_brier_42_label": float(summary["brier"].mean()),
        "mean_marginal_log_loss": float(summary["marginal_log_loss"].mean()),
        "mean_jaccard_similarity": float(summary["jaccard"].mean()),
        "match_distribution": summary["match_distribution"],
        "per_draw_hits": summary["hits"],
        "per_draw_brier": summary["brier"],
        "per_draw_log_loss": summary["marginal_log_loss"],
        "prediction_matrix": summary["prediction_matrix"],
        "calibration": calibration,
        "probabilities": np.clip(probabilities, 1e-12, 1.0 - 1e-12),
    }


def cv_windows(TimeSeriesSplit, dates, n_splits):
    rows = []
    splitter = TimeSeriesSplit(n_splits=n_splits)
    for fold, (train_indices, validation_indices) in enumerate(
        splitter.split(range(len(dates))), start=1
    ):
        rows.append(
            {
                "fold": fold,
                "train_start_date": str(dates[train_indices[0]]),
                "train_end_date": str(dates[train_indices[-1]]),
                "validation_start_date": str(dates[validation_indices[0]]),
                "validation_end_date": str(dates[validation_indices[-1]]),
                "train_rows": int(len(train_indices)),
                "validation_rows": int(len(validation_indices)),
                "train_indices": train_indices,
                "validation_indices": validation_indices,
            }
        )
    return rows


def expanding_probs_3d(np, frame):
    columns = [f"digit_{digit}_freq_expanding" for digit in range(10)]
    return normalize_rows(np, frame[columns].to_numpy(dtype=np.float64))


def expanding_probs_642(np, frame):
    columns = [f"num_{number:02d}_freq_expanding" for number in range(1, 43)]
    return np.clip(frame[columns].to_numpy(dtype=np.float64), 1e-12, 1.0 - 1e-12)


def recent30_probs_642(np, frame):
    columns = [f"num_{number:02d}_count_prev_30" for number in range(1, 43)]
    return np.clip(frame[columns].to_numpy(dtype=np.float64) / 30.0, 1e-12, 1.0 - 1e-12)


def simulate_3d(np, actual_counts, simulations, seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 3, simulations, 1]))
    draws = len(actual_counts)
    scores = np.empty(simulations, dtype=np.float64)
    chunk = 512
    digits = np.arange(10)
    for start in range(0, simulations, chunk):
        size = min(chunk, simulations - start)
        sampled = rng.integers(0, 10, size=(size, draws, 3), dtype=np.uint8)
        overlaps = np.zeros((size, draws), dtype=np.uint8)
        for digit in digits:
            simulated_count = (sampled == digit).sum(axis=2, dtype=np.uint8)
            overlaps += np.minimum(
                simulated_count, actual_counts[None, :, digit]
            ).astype(np.uint8)
        scores[start : start + size] = overlaps.mean(axis=1)
    return scores


def simulate_642(np, draws, simulations, seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 642, simulations, 1]))
    scores = np.empty(simulations, dtype=np.float64)
    chunk = 2048
    for start in range(0, simulations, chunk):
        size = min(chunk, simulations - start)
        hits = rng.hypergeometric(6, 36, 6, size=(size, draws))
        scores[start : start + size] = hits.mean(axis=1)
    return scores


def empirical_upper_p(np, simulated_scores, observed):
    exceedances = int((simulated_scores >= observed - 1e-12).sum())
    return float((exceedances + 1) / (len(simulated_scores) + 1))


def bootstrap_means(np, rng, values, indices):
    return values[indices].mean(axis=1)


def ci_record(np, samples, confidence=0.95):
    tail = (1.0 - confidence) / 2.0
    return {
        "confidence_level": confidence,
        "lower": float(np.quantile(samples, tail)),
        "upper": float(np.quantile(samples, 1.0 - tail)),
        "bootstrap_replicates": int(len(samples)),
    }


def write_predictions_3d(np, csv_path, frame, actual, probabilities, historical_probabilities):
    predicted = deterministic_multiset_counts(np, probabilities)
    historical_predicted = deterministic_multiset_counts(np, historical_probabilities)
    digits = range(10)
    fields = [
        "draw_date",
        "source_row",
        "actual_multiset",
        "predicted_multiset_logistic",
        "predicted_multiset_expanding_frequency",
        "multiset_overlap_logistic",
        "multiset_overlap_expanding_frequency",
    ]
    fields += [f"actual_count_digit_{digit}" for digit in digits]
    fields += [f"predicted_count_digit_{digit}" for digit in digits]
    fields += [f"predicted_count_expanding_digit_{digit}" for digit in digits]
    fields += [f"probability_digit_{digit}" for digit in digits]
    fields += [f"expanding_probability_digit_{digit}" for digit in digits]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index, (_, row) in enumerate(frame.iterrows()):
            record = {
                "draw_date": str(row["draw_date"]),
                "source_row": str(row["source_row"]),
                "actual_multiset": " ".join(
                    str(digit) for digit in np_repeat_digits(actual[index])
                ),
                "predicted_multiset_logistic": " ".join(
                    str(digit) for digit in np_repeat_digits(predicted[index])
                ),
                "predicted_multiset_expanding_frequency": " ".join(
                    str(digit) for digit in np_repeat_digits(historical_predicted[index])
                ),
                "multiset_overlap_logistic": int(
                    multiset_overlap(np, actual[index:index + 1], predicted[index:index + 1])[0]
                ),
                "multiset_overlap_expanding_frequency": int(
                    multiset_overlap(np, actual[index:index + 1], historical_predicted[index:index + 1])[0]
                ),
            }
            for digit in digits:
                record[f"actual_count_digit_{digit}"] = int(actual[index, digit])
                record[f"predicted_count_digit_{digit}"] = int(predicted[index, digit])
                record[f"predicted_count_expanding_digit_{digit}"] = int(historical_predicted[index, digit])
                record[f"probability_digit_{digit}"] = float(probabilities[index, digit])
                record[f"expanding_probability_digit_{digit}"] = float(historical_probabilities[index, digit])
            writer.writerow(record)


def np_repeat_digits(counts):
    return [digit for digit, count in enumerate(counts) for _ in range(int(count))]


def write_predictions_642(np, csv_path, frame, actual, model_predictions, probability_map):
    fields = ["draw_date", "source_row", "actual_set"]
    fields += [f"actual_{number:02d}" for number in range(1, 43)]
    for method, _ in model_predictions.items():
        fields.append(f"predicted_set_{method}")
        fields += [f"probability_{method}_{number:02d}" for number in range(1, 43)]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index, (_, row) in enumerate(frame.iterrows()):
            actual_numbers = [number + 1 for number in np.flatnonzero(actual[index])]
            record = {
                "draw_date": str(row["draw_date"]),
                "source_row": str(row["source_row"]),
                "actual_set": " ".join(f"{number:02d}" for number in actual_numbers),
            }
            for number in range(42):
                record[f"actual_{number + 1:02d}"] = int(actual[index, number])
            for method, predictions in model_predictions.items():
                predicted_numbers = [number + 1 for number in np.flatnonzero(predictions[index])]
                record[f"predicted_set_{method}"] = " ".join(
                    f"{number:02d}" for number in predicted_numbers
                )
                for number in range(42):
                    record[f"probability_{method}_{number + 1:02d}"] = float(
                        probability_map[method][index, number]
                    )
            writer.writerow(record)


def make_notebook(metrics: dict) -> None:
    cells = []

    def markdown(section: int, title: str, question: str, method: str, interpretation: str, limitation: str):
        source = (
            f"# {section}. {title}\n\n"
            f"**Question.** {question}\n\n"
            f"**Method.** {method}\n\n"
            f"**Interpretation.** {interpretation}\n\n"
            f"**Limitation.** {limitation}\n"
        )
        cells.append(
            {
                "cell_type": "markdown",
                "id": f"phase5a-section-{section:02d}",
                "metadata": {},
                "source": source.splitlines(keepends=True),
            }
        )

    def pycell(cell_id: str, source: str):
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "id": cell_id,
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            }
        )

    markdown(
        1,
        "Phase 5A Objective and Evidence Boundary",
        "Do simple models improve on fair-random and historical baselines?",
        "Fit only Phase 4 train rows, tune with expanding chronological folds, and score only Phase 4 validation rows.",
        "The report contains historical validation backtests only.",
        "A validation result does not establish future predictive ability.",
    )
    pycell(
        "phase5a-load-results",
        "from pathlib import Path\n"
        "import json\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "ROOT = Path.cwd()\n"
        "if not (ROOT / 'reports/phase5a_metrics.json').is_file():\n"
        "    ROOT = next(parent for parent in Path.cwd().parents if (parent / 'reports/phase5a_metrics.json').is_file())\n"
        "metrics = json.loads((ROOT / 'reports/phase5a_metrics.json').read_text(encoding='utf-8'))\n"
        "validation = json.loads((ROOT / 'reports/phase5a_validation.json').read_text(encoding='utf-8'))\n"
        "pred3 = pd.read_csv(ROOT / 'reports/phase5a_validation_predictions/3d_validation_predictions.csv')\n"
        "pred6 = pd.read_csv(ROOT / 'reports/phase5a_validation_predictions/642_validation_predictions.csv')\n"
        "simulations = pd.read_csv(ROOT / 'reports/phase5a_random_baseline_distributions.csv')\n"
        "print('Phase:', metrics['phase'], '| Evidence verdict:', metrics['advancement_gate']['verdict'])\n"
        "print('Validation predictions:', len(pred3), '3D rows and', len(pred6), '6/42 rows')",
    )
    markdown(
        2,
        "Phase 4 Inputs and Split Verification",
        "Do the input files and chronological partitions match the approved Phase 4 artifacts?",
        "Read the saved Phase 4 split manifest and hash-validated preflight record; no target file is reopened here.",
        "The training, validation, and locked-test boundaries are shown from manifest metadata.",
        "This notebook consumes saved validation outputs and does not rebuild Phase 4 features.",
    )
    pycell(
        "phase5a-split-metadata",
        "split = json.loads((ROOT / 'data/features/chronological_splits.json').read_text(encoding='utf-8'))\n"
        "split_rows = []\n"
        "for game, spec in split['games'].items():\n"
        "    for partition, item in spec['partitions'].items():\n"
        "        split_rows.append({'game': game, 'partition': partition, 'rows': item['row_count'], 'start': item['start_date'], 'end': item['end_date']})\n"
        "pd.DataFrame(split_rows)",
    )
    markdown(
        3,
        "Locked Test Safeguard",
        "Were locked test target values kept out of training, selection, scoring, and charts?",
        "Review the machine-readable audit flags and report only test partition metadata.",
        "No test targets were parsed by the Phase 5A model or evaluation paths.",
        "The locked test is still needed for a separately authorized later gate.",
    )
    pycell(
        "phase5a-test-audit",
        "audit = metrics['test_contamination_audit']\n"
        "assert audit['test_target_values_loaded'] is False\n"
        "assert audit['test_metrics_calculated'] is False\n"
        "assert audit['phase4_boundaries_preserved'] is True\n"
        "print(json.dumps(audit, indent=2))",
    )
    markdown(
        4,
        "Evaluation Metrics and Predeclared Baselines",
        "Which metrics and baselines define a useful comparison?",
        "Use normalized unordered-multiset NLL and overlap for 3D; use mean hits@6 for Lotto 6/42, with Brier, marginal log loss, match counts, and Jaccard as secondary diagnostics.",
        "The metrics table is loaded from the saved configuration.",
        "Different games have different outcome spaces and are not compared numerically to each other.",
    )
    pycell(
        "phase5a-metric-definitions",
        "pd.DataFrame(metrics['metric_definitions'])",
    )
    markdown(
        5,
        "3D Lotto Baselines",
        "How do uniform probabilities and expanding historical digit frequencies score?",
        "Score both with the same unordered-multiset likelihood, digit Brier score, and deterministic Hamilton allocated overlap.",
        "The uniform and historical baselines are summarized below.",
        "Historical features use only completed draws before each validation prediction.",
    )
    pycell(
        "phase5a-3d-baselines",
        "rows = []\n"
        "for method in ['uniform_random', 'expanding_historical_frequency', 'multinomial_logistic_regression/all_features']:\n"
        "    item = metrics['validation']['3d_lotto']['methods'][method]\n"
        "    rows.append({'method': method, 'unordered_nll_per_digit': item['mean_multinomial_negative_log_likelihood_per_digit'], 'mean_multiset_overlap': item['mean_multiset_overlap'], 'digit_brier': item['digit_level_multiclass_brier'], 'ece': item['calibration']['expected_calibration_error']})\n"
        "pd.DataFrame(rows)",
    )
    markdown(
        6,
        "3D Multinomial Model",
        "Does count-weighted multinomial logistic regression learn a useful digit distribution?",
        "Expand each training draw into three digit observations, scale features inside each training fold, and select C only by expanding-window NLL.",
        "The final selected C and validation metrics are recorded below.",
        "The independence model uses one categorical digit distribution for an unordered draw.",
    )
    pycell(
        "phase5a-3d-model",
        "from IPython.display import display\n"
        "display(pd.DataFrame([metrics['cv']['selection']['3d_lotto']['logistic']['all_features']]))\n"
        "pd.DataFrame([{'method': 'multinomial_logistic_regression/all_features', 'nll_per_digit': metrics['validation']['3d_lotto']['methods']['multinomial_logistic_regression/all_features']['mean_multinomial_negative_log_likelihood_per_digit'], 'overlap': metrics['validation']['3d_lotto']['methods']['multinomial_logistic_regression/all_features']['mean_multiset_overlap']}])",
    )
    markdown(
        7,
        "3D Chronological Validation Results",
        "Were predictions formed using only earlier rows within each training fold?",
        "Inspect fold date windows and selected-model scores against fold-specific uniform and expanding-frequency baselines.",
        "The fold table and chronology diagram expose training and prediction order.",
        "Three folds provide limited evidence about regime stability.",
    )
    pycell(
        "phase5a-folds-and-timeline",
        "folds = pd.DataFrame(metrics['cv']['fold_results'])\n"
        "folds.query(\"game == '3d_lotto' and feature_group == 'all_features' and model == 'multinomial_logistic_regression'\")",
    )
    pycell(
        "phase5a-fold-timeline-plot",
        "fig, axes = plt.subplots(2, 1, figsize=(11, 4.5), sharex=False)\n"
        "for ax, game in zip(axes, ['3d_lotto', 'lotto_6_42']):\n"
        "    rows = [row for row in metrics['cv']['fold_windows'][game]]\n"
        "    for y, row in enumerate(rows):\n"
        "        ax.plot([pd.to_datetime(row['train_start_date']), pd.to_datetime(row['train_end_date'])], [y, y], color='#4477aa', linewidth=7, solid_capstyle='butt', label='train' if y == 0 else None)\n"
        "        ax.plot([pd.to_datetime(row['validation_start_date']), pd.to_datetime(row['validation_end_date'])], [y, y], color='#ee9944', linewidth=7, solid_capstyle='butt', label='fold validation' if y == 0 else None)\n"
        "    ax.set_yticks(range(len(rows)), [f\"Fold {row['fold']}\" for row in rows])\n"
        "    ax.set_title(game)\n"
        "    ax.legend(loc='lower right')\n"
        "fig.tight_layout()\n"
        "plt.show()",
    )
    markdown(
        8,
        "3D Random-Baseline Comparison",
        "Is the deterministic model overlap unusual under fair random multiset draws?",
        "Compare its mean validation overlap with 10,000 or, after the predeclared p-value trigger, 100,000 Monte Carlo fair-random simulations.",
        "The empirical p-value and simulation distribution are shown below.",
        "Overlap is secondary to the primary multiset likelihood and does not imply number predictability.",
    )
    pycell(
        "phase5a-3d-random-plot",
        "mc3 = metrics['random_baseline']['games']['3d_lotto']\n"
        "run3 = 'confirmation' if mc3['confirmation_triggered'] else 'initial'\n"
        "dist3 = simulations.query(\"game == '3d_lotto' and run == @run3\")['mean_primary_score']\n"
        "plt.figure(figsize=(8, 4))\n"
        "plt.hist(dist3, bins=35, color='#88aadd', edgecolor='white')\n"
        "plt.axvline(mc3['candidates']['multinomial_logistic_regression/all_features']['observed_score'], color='#bb3344', linewidth=2, label='model observed')\n"
        "plt.xlabel('Mean validation multiset overlap')\n"
        "plt.ylabel('Monte Carlo simulations')\n"
        "plt.title(f\"3D fair-random baseline; empirical p={mc3['candidates']['multinomial_logistic_regression/all_features']['empirical_p_final']:.4g}\")\n"
        "plt.legend()\n"
        "plt.tight_layout()\n"
        "plt.show()",
    )
    markdown(
        9,
        "Lotto 6/42 Baselines",
        "How do uniform marginal probabilities and simple history rankings perform?",
        "Compare fair-random expected hits, expanding historical frequency, and previous-30-draw frequency on validation rows.",
        "The baseline table includes hit, Brier, marginal log loss, and Jaccard summaries.",
        "Frequency rankings are baseline definitions and are not presented as actionable number advice.",
    )
    pycell(
        "phase5a-642-baselines",
        "rows = []\n"
        "for method in ['uniform_random', 'expanding_historical_frequency', 'recent_30_frequency']:\n"
        "    item = metrics['validation']['lotto_6_42']['methods'][method]\n"
        "    rows.append({'method': method, 'mean_hits_at_6': item['mean_hits_at_6'], 'brier': item['mean_brier_42_label'], 'marginal_log_loss': item['mean_marginal_log_loss'], 'jaccard': item['mean_jaccard_similarity']})\n"
        "pd.DataFrame(rows)",
    )
    markdown(
        10,
        "Lotto 6/42 Logistic Model",
        "Does regularized one-versus-rest logistic regression improve mean hits@6?",
        "Scale features inside each chronological training fold and select C using only fold hit counts.",
        "The all-feature validation comparison is shown below.",
        "The output is a backtest for historical validation rows, not a future draw.",
    )
    pycell(
        "phase5a-642-logistic",
        "from IPython.display import display\n"
        "display(pd.DataFrame([metrics['cv']['selection']['lotto_6_42']['logistic']['all_features']]))\n"
        "item = metrics['validation']['lotto_6_42']['methods']['regularized_one_vs_rest_logistic_regression/all_features']\n"
        "pd.DataFrame([{'mean_hits_at_6': item['mean_hits_at_6'], 'recall_at_6': item['mean_recall_at_6'], 'precision_at_6': item['mean_precision_at_6'], 'brier': item['mean_brier_42_label'], 'marginal_log_loss': item['mean_marginal_log_loss'], 'jaccard': item['mean_jaccard_similarity']}])",
    )
    markdown(
        11,
        "Lotto 6/42 Nonlinear Comparator",
        "Does the fixed multioutput random forest add evidence beyond the simpler logistic model?",
        "Use the one predeclared bounded forest configuration without a parameter search.",
        "The fixed comparator’s validation and fold results are shown beside logistic regression.",
        "The forest is a comparator, not the preferred model by default.",
    )
    pycell(
        "phase5a-642-forest",
        "item = metrics['validation']['lotto_6_42']['methods']['random_forest_multioutput_comparator/all_features']\n"
        "display(pd.DataFrame([{'mean_hits_at_6': item['mean_hits_at_6'], 'brier': item['mean_brier_42_label'], 'marginal_log_loss': item['mean_marginal_log_loss'], 'jaccard': item['mean_jaccard_similarity']}]))\n"
        "pd.DataFrame(folds.query(\"game == 'lotto_6_42' and feature_group == 'all_features' and model == 'random_forest_multioutput_comparator'\"))",
    )
    markdown(
        12,
        "Lotto 6/42 Chronological Validation Results",
        "Do the selected models beat fair-random and historical baselines on the full validation window?",
        "Compare mean hits@6 and its draw-level bootstrap interval across all predeclared methods.",
        "The bar chart shows baseline and all-feature candidate mean hits.",
        "A small absolute hit-count difference can arise from validation sampling noise.",
    )
    pycell(
        "phase5a-primary-comparison",
        "primary3 = metrics['validation']['3d_lotto']['methods']\n"
        "primary6 = metrics['validation']['lotto_6_42']['methods']\n"
        "fig, axes = plt.subplots(1, 2, figsize=(12, 4))\n"
        "axes[0].bar(['uniform', 'expanding', 'logistic'], [primary3['uniform_random']['mean_multinomial_negative_log_likelihood_per_digit'], primary3['expanding_historical_frequency']['mean_multinomial_negative_log_likelihood_per_digit'], primary3['multinomial_logistic_regression/all_features']['mean_multinomial_negative_log_likelihood_per_digit']], color=['#999999', '#66aa99', '#4477aa'])\n"
        "axes[0].set_title('3D mean unordered NLL per digit')\n"
        "axes[0].tick_params(axis='x', rotation=20)\n"
        "axes[1].bar(['fair random', 'expanding', 'recent30', 'logistic', 'forest'], [primary6['uniform_random']['mean_hits_at_6'], primary6['expanding_historical_frequency']['mean_hits_at_6'], primary6['recent_30_frequency']['mean_hits_at_6'], primary6['regularized_one_vs_rest_logistic_regression/all_features']['mean_hits_at_6'], primary6['random_forest_multioutput_comparator/all_features']['mean_hits_at_6']], color=['#999999', '#66aa99', '#77bb88', '#4477aa', '#aa66aa'])\n"
        "axes[1].set_title('6/42 mean hits@6')\n"
        "axes[1].tick_params(axis='x', rotation=25)\n"
        "fig.tight_layout()\n"
        "plt.show()",
    )
    markdown(
        13,
        "Lotto 6/42 Random-Baseline Comparison",
        "Are model hit counts unusual compared with fair random six-number sets?",
        "Use the exact hypergeometric hit law for each random six-set simulation and the same number of validation draws.",
        "Both all-feature models are marked against a shared Monte Carlo distribution.",
        "Empirical p-values are exploratory and are adjusted for the two predefined all-feature candidate comparisons in the gate.",
    )
    pycell(
        "phase5a-642-random-plot",
        "mc6 = metrics['random_baseline']['games']['lotto_6_42']\n"
        "run6 = 'confirmation' if mc6['confirmation_triggered'] else 'initial'\n"
        "dist6 = simulations.query(\"game == 'lotto_6_42' and run == @run6\")['mean_primary_score']\n"
        "plt.figure(figsize=(8, 4))\n"
        "plt.hist(dist6, bins=35, color='#88aadd', edgecolor='white')\n"
        "for method, color in [('regularized_one_vs_rest_logistic_regression', '#bb3344'), ('random_forest_multioutput_comparator', '#883399')]:\n"
        "    observed = mc6['candidates'][method]['observed_score']\n"
        "    plt.axvline(observed, color=color, linewidth=2, label=method)\n"
        "plt.xlabel('Mean validation hits@6')\n"
        "plt.ylabel('Monte Carlo simulations')\n"
        "plt.title('Fair-random six-set baseline')\n"
        "plt.legend(fontsize=8)\n"
        "plt.tight_layout()\n"
        "plt.show()\n"
        "pd.DataFrame(mc6['candidates']).T[['empirical_p_initial', 'empirical_p_final', 'empirical_p_bonferroni', 'confirmation_simulations']]",
    )
    markdown(
        14,
        "Feature-Group Ablation",
        "Are apparent results stable across the predefined feature families?",
        "Compare frequency/deviation, recency/gap, draw-context, and all-feature models; each logistic group’s C was chosen only in training folds.",
        "The primary metric plot compares the four fixed groups.",
        "Ablation results are diagnostics and do not define arbitrary subsets.",
    )
    pycell(
        "phase5a-ablation",
        "ablation = pd.DataFrame(metrics['feature_ablation'])\n"
        "for game, metric, title in [('3d_lotto', 'mean_multinomial_negative_log_likelihood_per_digit', '3D NLL per digit'), ('lotto_6_42', 'mean_hits_at_6', '6/42 hits@6')]:\n"
        "    view = ablation.query('game == @game')\n"
        "    plt.figure(figsize=(7, 3.5))\n"
        "    plt.bar(view['feature_group'], view[metric], color='#6699bb')\n"
        "    plt.title(title)\n"
        "    plt.xticks(rotation=20)\n"
        "    plt.tight_layout()\n"
        "    plt.show()\n"
        "ablation",
    )
    markdown(
        15,
        "Calibration and Error Analysis",
        "Do the reported probability distributions align with validation outcomes?",
        "Inspect reliability bins, Brier scores, marginal loss, and overlap/match distributions.",
        "The calibration curves use only saved validation predictions.",
        "Binned calibration estimates are noisy with a limited validation sample.",
    )
    pycell(
        "phase5a-calibration",
        "fig, axes = plt.subplots(1, 2, figsize=(9, 4))\n"
        "for ax, game, model, title in [(axes[0], '3d_lotto', 'multinomial_logistic_regression/all_features', '3D digit probabilities'), (axes[1], 'lotto_6_42', 'regularized_one_vs_rest_logistic_regression', '6/42 membership probabilities')]:\n"
        "    bins = metrics['calibration'][game][model]['bins']\n"
        "    rows = [row for row in bins if row['mean_probability'] is not None]\n"
        "    ax.plot([row['mean_probability'] for row in rows], [row['observed_rate'] for row in rows], marker='o', label='observed')\n"
        "    ax.plot([0, 1], [0, 1], linestyle='--', color='gray', label='ideal')\n"
        "    ax.set(title=title, xlabel='Mean predicted probability', ylabel='Observed frequency')\n"
        "    ax.legend()\n"
        "fig.tight_layout()\n"
        "plt.show()",
    )
    markdown(
        16,
        "Evidence Summary",
        "What do the full validation metrics, uncertainty intervals, folds, and baselines jointly show?",
        "Read the saved comparison, bootstrap, calibration, and simulation summaries.",
        "The evidence summary is printed below.",
        "No single metric or model ranking establishes a predictive signal.",
    )
    pycell(
        "phase5a-evidence-summary",
        "summary = {'validation': {}, 'bootstrap': metrics['bootstrap'], 'advancement_gate': metrics['advancement_gate']}\n"
        "for game, methods in metrics['validation'].items():\n"
        "    summary['validation'][game] = {name: {key: value for key, value in item.items() if key in ('mean_multinomial_negative_log_likelihood_per_digit', 'mean_multiset_overlap', 'mean_hits_at_6', 'mean_brier_42_label', 'mean_marginal_log_loss')} for name, item in methods['methods'].items() if name in ('uniform_random', 'expanding_historical_frequency', 'recent_30_frequency', 'multinomial_logistic_regression/all_features', 'regularized_one_vs_rest_logistic_regression/all_features', 'random_forest_multioutput_comparator/all_features')}\n"
        "print(json.dumps(summary, indent=2))",
    )
    markdown(
        17,
        "Phase 5B Advancement Decision",
        "Does any candidate satisfy the predeclared evidence gate for a later test gate?",
        "Require validation improvement over fair random and historical baselines, fold consistency, acceptable calibration diagnostics, and a clean contamination audit.",
        "The machine-readable decision is printed below.",
        "A passing result would only make a candidate ready for human review of the next gate.",
    )
    pycell(
        "phase5a-advancement",
        "print(json.dumps(metrics['advancement_gate'], indent=2))",
    )
    markdown(
        18,
        "Limitations",
        "What evidence remains unavailable?",
        "Keep the locked test unopened and treat all validation estimates as historical, finite-sample evidence. Training folds were also used to tune C, so their consistency check is diagnostic rather than an independent holdout.",
        "The notebook provides no future predictions and no claim of lottery predictability.",
        "A later test evaluation requires a separately authorized phase and untouched test outcomes.",
    )

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": sys.version.split()[0]},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def markdown_report(metrics: dict, validation: dict, artifact_hashes: dict | None = None) -> str:
    def fmt(value, places=5):
        return "n/a" if value is None else f"{value:.{places}f}"

    lines = [
        "# Phase 5A ML Baseline Training and Chronological Validation",
        "",
        f"- Verdict: {validation.get('verdict', 'PHASE5A_IN_PROGRESS_AWAITING_NOTEBOOK_VALIDATION')}",
        f"- Branch / HEAD: {validation['repository']['branch']} / {validation['repository']['head']}",
        f"- Random seed: {metrics['configuration']['random_seed']}",
        "- Git stage, commit, push, and merge: not performed",
        "- Keys.env: ignored and untracked; contents not read",
        "- JEV / TypeSafe: not invoked",
        "",
        "## Scope and split",
        "",
        "Only Phase 4 training rows were used for fitting and expanding-window tuning. Evaluation used the predefined validation rows. The locked test target values were not parsed, scored, charted, or used for selection.",
        "",
        "| Game | Train | Validation | Locked test metadata |",
        "|---|---:|---:|---|",
    ]
    for game, part in metrics["partitions"].items():
        train = part["train"]
        validation_part = part["validation"]
        test = part["test"]
        lines.append(
            f"| {game} | {train['row_count']} ({train['start_date']} to {train['end_date']}) "
            f"| {validation_part['row_count']} ({validation_part['start_date']} to {validation_part['end_date']}) "
            f"| {test['row_count']} rows ({test['start_date']} to {test['end_date']}); metadata only |"
        )
    lines += [
        "",
        "## Candidate configurations",
        "",
        f"- 3D multinomial logistic regression: C grid {metrics['configuration']['models']['3d_lotto']['c_grid']}; selected C by expanding-window mean unordered-multiset NLL.",
        f"- Lotto 6/42 one-versus-rest logistic regression: C grid {metrics['configuration']['models']['lotto_6_42']['logistic']['c_grid']}; selected C by expanding-window mean hits@6.",
        f"- Lotto 6/42 random forest: {json.dumps(metrics['configuration']['models']['lotto_6_42']['random_forest'], sort_keys=True)}; fixed comparator, no search.",
        "",
        "## Chronological training-fold results",
        "",
        "The full grid and per-fold baseline scores are in phase5a_metrics.json. Selected all-feature results:",
        "",
        "| Game | Model | Fold | Train dates | Fold dates | Primary | Uniform/random | Historical |",
        "|---|---|---:|---|---|---:|---:|---:|",
    ]
    fold_rows = metrics["cv"]["fold_results"]
    selected_by_game = metrics["cv"]["selection"]
    for game in ("3d_lotto", "lotto_6_42"):
        for model_name, selection_key in (
            (
                MODEL_NAMES["3d_lotto"] if game == "3d_lotto" else MODEL_NAMES["lotto_6_42"]["logistic"],
                "logistic",
            ),
        ):
            selected_c = selected_by_game[game][selection_key]["all_features"]["selected_c"]
            for row in fold_rows:
                if row["game"] != game or row["feature_group"] != "all_features" or row["model"] != model_name:
                    continue
                if game == "lotto_6_42" and row["c"] != selected_c:
                    continue
                if game == "3d_lotto" and row["c"] != selected_c:
                    continue
                primary = row["mean_multinomial_negative_log_likelihood_per_digit"] if game == "3d_lotto" else row["mean_hits_at_6"]
                random = row["uniform_nll"] if game == "3d_lotto" else row["fair_random_expected_hits"]
                historical = row["expanding_frequency_nll"] if game == "3d_lotto" else row["expanding_frequency_hits"]
                lines.append(
                    f"| {game} | {model_name} | {row['fold']} | {row['train_start_date']} to {row['train_end_date']} "
                    f"| {row['validation_start_date']} to {row['validation_end_date']} | {primary:.5f} | {random:.5f} | {historical:.5f} |"
                )
    for row in fold_rows:
        if row["game"] == "lotto_6_42" and row["feature_group"] == "all_features" and row["model"] == MODEL_NAMES["lotto_6_42"]["forest"]:
            lines.append(
                f"| lotto_6_42 | {row['model']} | {row['fold']} | {row['train_start_date']} to {row['train_end_date']} "
                f"| {row['validation_start_date']} to {row['validation_end_date']} | {row['mean_hits_at_6']:.5f} "
                f"| {row['fair_random_expected_hits']:.5f} | {row['expanding_frequency_hits']:.5f} |"
            )
    lines += [
        "",
        "## Validation metrics",
        "",
        "### 3D Lotto",
        "",
        "| Method | Mean unordered NLL / digit | Mean multiset overlap | Digit Brier | ECE |",
        "|---|---:|---:|---:|---:|",
    ]
    for method, values in metrics["validation"]["3d_lotto"]["methods"].items():
        lines.append(
            f"| {method} | {values['mean_multinomial_negative_log_likelihood_per_digit']:.6f} "
            f"| {values['mean_multiset_overlap']:.5f} | {values['digit_level_multiclass_brier']:.6f} "
            f"| {values['calibration']['expected_calibration_error']:.5f} |"
        )
    lines += [
        "",
        "The unordered likelihood is computed as minus one third of log[(3! / product(count[d]!)) * product(p[d]^count[d])]. Hamilton allocation assigns three integer predicted counts using descending fractional remainders and lower-digit tie-breaks.",
        "",
        "### Lotto 6/42",
        "",
        "| Method | Mean hits@6 | Recall@6 | Precision@6 | Brier | Marginal log loss | Jaccard | ECE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method, values in metrics["validation"]["lotto_6_42"]["methods"].items():
        lines.append(
            f"| {method} | {values['mean_hits_at_6']:.5f} | {values['mean_recall_at_6']:.5f} "
            f"| {values['mean_precision_at_6']:.5f} | {values['mean_brier_42_label']:.6f} "
            f"| {values['mean_marginal_log_loss']:.6f} | {fmt(values['mean_jaccard_similarity'])} "
            f"| {values['calibration']['expected_calibration_error']:.5f} |"
        )
    lines += [
        "",
        "The fair-random primary expectation is 6 * 6 / 42 = 0.8571428571 hits per draw. Random-set empirical comparisons use hypergeometric hit simulations.",
        "",
        "## Monte Carlo comparisons",
        "",
        "| Game / candidate | Initial simulations | Final simulations | Observed | Random mean | 95% random interval | Initial p | Final empirical p | Confirmation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for game, record in metrics["random_baseline"]["games"].items():
        for candidate, result in record["candidates"].items():
            lines.append(
                f"| {game} / {candidate} | {result['initial_simulations']} | {result['final_simulations']} "
                f"| {result['observed_score']:.6f} | {result['random_mean']:.6f} "
                f"| [{result['random_ci95']['lower']:.6f}, {result['random_ci95']['upper']:.6f}] "
                f"| {result['empirical_p_initial']:.6g} | {result['empirical_p_final']:.6g} "
                f"| {'100000' if result['confirmation_simulations'] else 'not triggered'} |"
            )
    lines += [
        "",
        "P-values are one-sided upper-tail empirical values using (1 + exceedances) / (1 + simulations). The two predefined 6/42 model comparisons use a Bonferroni-adjusted p-value in the advancement gate. A raw initial p below 0.01 triggers a separate 100000-simulation confirmation stream.",
        "",
        "## Bootstrap uncertainty",
        "",
        f"Whole validation draws were resampled {metrics['bootstrap']['replicates']:,} times for percentile 95% intervals.",
        "",
        "| Game / model | Primary metric | 95% CI | Difference vs fair random | Difference vs historical baseline(s) |",
        "|---|---|---|---|---|",
    ]
    for game, models in metrics["bootstrap"]["games"].items():
        for model, result in models.items():
            ci = result["primary_metric_ci95"]
            rand = result.get("difference_vs_fair_random_ci95")
            rand_text = (
                f"[{rand['lower']:.6f}, {rand['upper']:.6f}]"
                if rand
                else "n/a"
            )
            hist = "; ".join(
                f"{name}: [{item['lower']:.6f}, {item['upper']:.6f}]"
                for name, item in result.get("difference_vs_historical_ci95", {}).items()
            ) or "n/a"
            lines.append(
                f"| {game} / {model} | {result['primary_metric']} | [{ci['lower']:.6f}, {ci['upper']:.6f}] "
                f"| {rand_text} | {hist} |"
            )
    lines += [
        "",
        "## Feature-group ablation",
        "",
        "| Game | Model | Feature group | Selected C | Primary validation metric |",
        "|---|---|---|---:|---:|",
    ]
    for row in metrics["feature_ablation"]:
        c_value = "fixed" if row["selected_c"] is None else f"{row['selected_c']:g}"
        metric_name = "mean_multinomial_negative_log_likelihood_per_digit" if row["game"] == "3d_lotto" else "mean_hits_at_6"
        lines.append(
            f"| {row['game']} | {row['model']} | {row['feature_group']} | {c_value} | {row[metric_name]:.6f} |"
        )
    lines += [
        "",
        "## Calibration and consistency",
        "",
        f"- Calibration screening threshold: ECE <= {metrics['configuration']['decision_rule']['maximum_ece']:.3f}; this is a diagnostic screen, not a proof of calibration.",
        f"- Fold consistency requirement: at least {metrics['configuration']['decision_rule']['minimum_folds_better']} of {metrics['configuration']['time_series_cv']['n_splits']} chronological folds improve over each required baseline.",
        f"- Repeatability checks: {json.dumps({key: value for key, value in metrics['reproducibility'].items() if key not in ('convergence_warnings', 'other_warning_summary')}, sort_keys=True)}",
        f"- Fit warnings: {json.dumps({'convergence': len(metrics['reproducibility'].get('convergence_warnings', [])), 'other': metrics['reproducibility'].get('other_warning_summary', [])}, sort_keys=True)}",
        "",
        "## Advancement decision",
        "",
        f"Phase 5B candidate-ready: {metrics['advancement_gate']['any_candidate_eligible']}.",
        "",
        "| Candidate | Eligible | Reasons |",
        "|---|---|---|",
    ]
    for candidate in metrics["advancement_gate"]["candidates"]:
        lines.append(
            f"| {candidate['candidate']} | {candidate['eligible']} | {'; '.join(candidate['reasons']) or 'all predeclared checks passed'} |"
        )
    lines += [
        "",
        "## Test-contamination audit",
        "",
        f"- Result: {'PASS' if metrics['test_contamination_audit']['all_checks_pass'] else 'FAIL'}",
        "- Test targets parsed: no.",
        "- Test metrics calculated: no.",
        "- Test-dependent selection or visualization: no.",
        "- Phase 4 split boundaries changed: no.",
        "",
        "## Validation",
        "",
        f"- Notebook: {validation.get('notebook_execution', {}).get('status', 'pending clean-kernel execution')}",
        f"- nbformat: {validation.get('notebook_execution', {}).get('nbformat_validation', 'pending')}",
        f"- Phase 4 artifacts unchanged: {validation.get('checks', {}).get('phase4_artifacts_unchanged', 'pending final check')}",
        f"- Keys.env ignored/untracked: {validation['security']['keys_env_ignored']}/{not validation['security']['keys_env_tracked']}; contents not read.",
        "",
        "## Limitations",
        "",
        "- Chronological training folds were used to tune C, so fold consistency is a diagnostic and not an independent holdout.",
        "- Validation results are finite-sample historical evidence. The locked test partition remains unevaluated.",
        "",
        "## Safest next action",
        "",
        validation["safest_next_action"],
        "",
    ]
    if artifact_hashes:
        lines += ["## Output hashes", ""]
        for name, digest in sorted(artifact_hashes.items()):
            lines.append(f"- {name}: {digest}")
        lines.append("")
    return "\n".join(lines)


def run_pipeline(config: dict) -> None:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    require(config["random_seed"] == 162, "Random seed differs from the approved Phase 5A value.")
    environment = get_runtime_versions()
    require(environment["scikit-learn"] == config["environment"]["scikit_learn"], "scikit-learn version differs from config.")
    require(environment["pandas"] == config["environment"]["pandas"], "pandas version differs from config.")
    preflight = validate_phase4_artifacts(np, pd, config)
    require(
        config["baseline"]["branch"] == preflight["phase4"]["repository"]["branch"]
        and config["baseline"]["head"] == preflight["phase4"]["repository"]["head"],
        "Machine-readable config baseline differs from Phase 4.",
    )
    git_state = verify_initial_status(preflight["phase4"], run_mode=True)
    datasets = preflight["data"]
    all_fold_results = []
    fold_windows = {}
    selections = {}
    validation_results = {}
    calibration = {}
    feature_ablation = []
    per_draw = {}
    predictions = {}
    repeatability = {}
    warning_records = []
    other_warning_summary = {}

    def fit_with_warning_capture(context, function):
        import warnings
        from sklearn.exceptions import ConvergenceWarning

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            fitted = function()
        for warning in caught:
            record = {
                **context,
                "category": warning.category.__name__,
                "message": str(warning.message),
            }
            if issubclass(warning.category, ConvergenceWarning):
                warning_records.append(record)
            else:
                key = (record["category"], record["message"])
                summary = other_warning_summary.setdefault(
                    key,
                    {"category": record["category"], "message": record["message"], "count": 0},
                )
                summary["count"] += 1
        return fitted

    for game, data in datasets.items():
        train_dates = data["train_dates"]
        windows = cv_windows(TimeSeriesSplit, train_dates, config["time_series_cv"]["n_splits"])
        fold_windows[game] = [
            {key: value for key, value in row.items() if not key.endswith("_indices")}
            for row in windows
        ]
        feature_frame_train = data["feature_frame"].iloc[: data["train_end"]]
        x_train = data["x_train"]
        y_train = data["y_train"]
        groups = data["groups"]
        game_selections = {}

        if game == "3d_lotto":
            c_grid = config["models"]["3d_lotto"]["c_grid"]
            for group, columns in groups.items():
                indices = [data["feature_names"].index(name) for name in columns]
                group_x = x_train[:, indices]
                c_scores = []
                for c_value in c_grid:
                    fold_scores = []
                    for fold in windows:
                        fit_x = group_x[fold["train_indices"]]
                        fit_y = y_train[fold["train_indices"]]
                        val_x = group_x[fold["validation_indices"]]
                        val_y = y_train[fold["validation_indices"]]
                        model = fit_with_warning_capture(
                            {
                                "game": game,
                                "feature_group": group,
                                "model": MODEL_NAMES[game],
                                "c": c_value,
                                "fold": fold["fold"],
                            },
                            lambda: fit_3d_model(np, StandardScaler, LogisticRegression, Pipeline, fit_x, fit_y, c_value),
                        )
                        probabilities = predict_3d_probabilities(np, model, val_x)
                        nll = multinomial_nll_per_draw(np, val_y, probabilities)
                        frame_validation = data["feature_frame"].iloc[
                            fold["validation_indices"]
                        ]
                        expanding = expanding_probs_3d(np, frame_validation)
                        expanding_nll = multinomial_nll_per_draw(np, val_y, expanding)
                        uniform = np.full_like(probabilities, 0.1)
                        uniform_nll = multinomial_nll_per_draw(np, val_y, uniform)
                        predicted_counts = deterministic_multiset_counts(np, probabilities)
                        overlap = multiset_overlap(np, val_y, predicted_counts)
                        fold_scores.append(float(nll.mean()))
                        all_fold_results.append(
                            {
                                "game": game,
                                "model": MODEL_NAMES[game],
                                "feature_group": group,
                                "c": float(c_value),
                                "fold": fold["fold"],
                                "train_start_date": fold["train_start_date"],
                                "train_end_date": fold["train_end_date"],
                                "validation_start_date": fold["validation_start_date"],
                                "validation_end_date": fold["validation_end_date"],
                                "train_rows": fold["train_rows"],
                                "validation_rows": fold["validation_rows"],
                                "mean_multinomial_negative_log_likelihood_per_digit": float(nll.mean()),
                                "uniform_nll": float(uniform_nll.mean()),
                                "expanding_frequency_nll": float(expanding_nll.mean()),
                                "mean_multiset_overlap": float(overlap.mean()),
                            }
                        )
                    c_scores.append(
                        {
                            "c": float(c_value),
                            "fold_mean_nll": fold_scores,
                            "mean_fold_nll": float(np.mean(fold_scores)),
                        }
                    )
                selected = min(c_scores, key=lambda item: (item["mean_fold_nll"], item["c"]))
                game_selections[group] = {
                    "selected_c": selected["c"],
                    "selection_metric": "mean_multinomial_negative_log_likelihood_per_digit",
                    "candidate_scores": c_scores,
                }
            selections[game] = {"logistic": game_selections}

            frame_val = data["feature_frame"].iloc[
                data["train_end"] : data["validation_end"]
            ].reset_index(drop=True)
            y_val = data["y_validation"]
            historical_p = expanding_probs_3d(np, frame_val)
            uniform_p = np.full_like(historical_p, 0.1)
            method_metrics = {}
            group_outputs = {}
            selected_c = game_selections["all_features"]["selected_c"]
            for group, columns in groups.items():
                indices = [data["feature_names"].index(name) for name in columns]
                group_train = x_train[:, indices]
                group_validation = data["x_validation"][:, indices]
                c_value = game_selections[group]["selected_c"]
                model = fit_with_warning_capture(
                    {
                        "game": game,
                        "feature_group": group,
                        "model": MODEL_NAMES[game],
                        "c": c_value,
                        "stage": "final_train_fit",
                    },
                    lambda: fit_3d_model(np, StandardScaler, LogisticRegression, Pipeline, group_train, y_train, c_value),
                )
                probabilities = normalize_rows(np, predict_3d_probabilities(np, model, group_validation))
                summary = metric_summary_3d(np, y_val, probabilities)
                group_outputs[group] = {"probabilities": probabilities, "summary": summary}
                if group == "all_features":
                    repeated_model = fit_with_warning_capture(
                        {
                            "game": game,
                            "feature_group": group,
                            "model": MODEL_NAMES[game],
                            "c": c_value,
                            "stage": "repeatability_refit",
                        },
                        lambda: fit_3d_model(np, StandardScaler, LogisticRegression, Pipeline, group_train, y_train, c_value),
                    )
                    repeated_probabilities = predict_3d_probabilities(np, repeated_model, group_validation)
                    max_difference = float(np.max(np.abs(probabilities - repeated_probabilities)))
                    repeatability[game] = {
                        "same_seed_refit_matches": bool(np.allclose(probabilities, repeated_probabilities, atol=1e-12, rtol=0)),
                        "maximum_absolute_probability_difference": max_difference,
                    }
                    require(repeatability[game]["same_seed_refit_matches"], "3D selected validation refit is not reproducible.")
                    final_probabilities = probabilities
                metric_record = {
                    "mean_multinomial_negative_log_likelihood_per_digit": summary["mean_multinomial_negative_log_likelihood_per_digit"],
                    "mean_multiset_overlap": summary["mean_multiset_overlap"],
                    "digit_level_multiclass_brier": summary["digit_level_multiclass_brier"],
                    "deterministic_overlap_distribution": summary["deterministic_overlap_distribution"],
                    "calibration": summary["calibration"],
                    "selected_c": c_value,
                }
                method_metrics[f"{MODEL_NAMES[game]}/{group}"] = metric_record
                feature_ablation.append(
                    {
                        "game": game,
                        "model": MODEL_NAMES[game],
                        "feature_group": group,
                        "selected_c": float(c_value),
                        **{
                            key: value
                            for key, value in metric_record.items()
                            if key not in ("calibration", "selected_c", "deterministic_overlap_distribution")
                        },
                    }
                )
            uniform_summary = metric_summary_3d(np, y_val, uniform_p)
            history_summary = metric_summary_3d(np, y_val, historical_p)
            method_metrics = {
                "uniform_random": {
                    "mean_multinomial_negative_log_likelihood_per_digit": uniform_summary["mean_multinomial_negative_log_likelihood_per_digit"],
                    "mean_multiset_overlap": uniform_summary["mean_multiset_overlap"],
                    "digit_level_multiclass_brier": uniform_summary["digit_level_multiclass_brier"],
                    "deterministic_overlap_distribution": uniform_summary["deterministic_overlap_distribution"],
                    "calibration": uniform_summary["calibration"],
                },
                "expanding_historical_frequency": {
                    "mean_multinomial_negative_log_likelihood_per_digit": history_summary["mean_multinomial_negative_log_likelihood_per_digit"],
                    "mean_multiset_overlap": history_summary["mean_multiset_overlap"],
                    "digit_level_multiclass_brier": history_summary["digit_level_multiclass_brier"],
                    "deterministic_overlap_distribution": history_summary["deterministic_overlap_distribution"],
                    "calibration": history_summary["calibration"],
                },
                **method_metrics,
            }
            validation_results[game] = {
                "primary_metric": "mean_multinomial_negative_log_likelihood_per_digit",
                "primary_direction": "lower_is_better",
                "methods": method_metrics,
            }
            calibration[game] = {
                "uniform_random": uniform_summary["calibration"],
                "expanding_historical_frequency": history_summary["calibration"],
                f"{MODEL_NAMES[game]}/all_features": group_outputs["all_features"]["summary"]["calibration"],
            }
            per_draw[game] = {
                "counts": y_val,
                "uniform": uniform_summary,
                "historical": history_summary,
                "candidate": group_outputs["all_features"]["summary"],
            }
            predictions[game] = {
                "frame": frame_val,
                "actual": y_val,
                "candidate_probabilities": final_probabilities,
                "historical_probabilities": historical_p,
                "groups": group_outputs,
            }
            game_selections["all_features"]["selected_c"] = selected_c
        else:
            c_grid = config["models"]["lotto_6_42"]["logistic"]["c_grid"]
            for group, columns in groups.items():
                indices = [data["feature_names"].index(name) for name in columns]
                group_x = x_train[:, indices]
                c_scores = []
                for c_value in c_grid:
                    fold_scores = []
                    for fold in windows:
                        fit_x = group_x[fold["train_indices"]]
                        fit_y = y_train[fold["train_indices"]]
                        val_x = group_x[fold["validation_indices"]]
                        val_y = y_train[fold["validation_indices"]]
                        model = fit_with_warning_capture(
                            {
                                "game": game,
                                "feature_group": group,
                                "model": MODEL_NAMES[game]["logistic"],
                                "c": c_value,
                                "fold": fold["fold"],
                            },
                            lambda: fit_642_logistic(np, StandardScaler, LogisticRegression, OneVsRestClassifier, Pipeline, fit_x, fit_y, c_value),
                        )
                        probabilities = predict_642_probabilities(np, model, val_x, forest=False)
                        result = six_set_metrics(np, val_y, probabilities)
                        fold_scores.append(float(result["hits"].mean()))
                        frame_validation = data["feature_frame"].iloc[
                            fold["validation_indices"]
                        ]
                        expanding = expanding_probs_642(np, frame_validation)
                        recent = recent30_probs_642(np, frame_validation)
                        all_fold_results.append(
                            {
                                "game": game,
                                "model": MODEL_NAMES[game]["logistic"],
                                "feature_group": group,
                                "c": float(c_value),
                                "fold": fold["fold"],
                                "train_start_date": fold["train_start_date"],
                                "train_end_date": fold["train_end_date"],
                                "validation_start_date": fold["validation_start_date"],
                                "validation_end_date": fold["validation_end_date"],
                                "train_rows": fold["train_rows"],
                                "validation_rows": fold["validation_rows"],
                                "mean_hits_at_6": float(result["hits"].mean()),
                                "fair_random_expected_hits": 6.0 * 6.0 / 42.0,
                                "expanding_frequency_hits": float(six_set_metrics(np, val_y, expanding)["hits"].mean()),
                                "recent_30_frequency_hits": float(six_set_metrics(np, val_y, recent)["hits"].mean()),
                            }
                        )
                    c_scores.append(
                        {
                            "c": float(c_value),
                            "fold_mean_hits_at_6": fold_scores,
                            "mean_fold_hits_at_6": float(np.mean(fold_scores)),
                        }
                    )
                selected = max(c_scores, key=lambda item: (item["mean_fold_hits_at_6"], -item["c"]))
                game_selections[group] = {
                    "selected_c": selected["c"],
                    "selection_metric": "mean_hits_at_6",
                    "candidate_scores": c_scores,
                }
                for fold in windows:
                    fit_x = group_x[fold["train_indices"]]
                    fit_y = y_train[fold["train_indices"]]
                    val_x = group_x[fold["validation_indices"]]
                    val_y = y_train[fold["validation_indices"]]
                    forest_model = fit_with_warning_capture(
                        {
                            "game": game,
                            "feature_group": group,
                            "model": MODEL_NAMES[game]["forest"],
                            "fold": fold["fold"],
                        },
                        lambda: fit_642_forest(
                            RandomForestClassifier,
                            fit_x,
                            fit_y,
                            config["models"]["lotto_6_42"]["random_forest"],
                        ),
                    )
                    forest_probabilities = predict_642_probabilities(
                        np, forest_model, val_x, forest=True
                    )
                    forest_scores = six_set_metrics(np, val_y, forest_probabilities)
                    fold_frame = data["feature_frame"].iloc[fold["validation_indices"]]
                    fold_expanding = expanding_probs_642(np, fold_frame)
                    fold_recent = recent30_probs_642(np, fold_frame)
                    all_fold_results.append(
                        {
                            "game": game,
                            "model": MODEL_NAMES[game]["forest"],
                            "feature_group": group,
                            "c": None,
                            "fold": fold["fold"],
                            "train_start_date": fold["train_start_date"],
                            "train_end_date": fold["train_end_date"],
                            "validation_start_date": fold["validation_start_date"],
                            "validation_end_date": fold["validation_end_date"],
                            "train_rows": fold["train_rows"],
                            "validation_rows": fold["validation_rows"],
                            "mean_hits_at_6": float(forest_scores["hits"].mean()),
                            "fair_random_expected_hits": 6.0 * 6.0 / 42.0,
                            "expanding_frequency_hits": float(
                                six_set_metrics(np, val_y, fold_expanding)["hits"].mean()
                            ),
                            "recent_30_frequency_hits": float(
                                six_set_metrics(np, val_y, fold_recent)["hits"].mean()
                            ),
                        }
                    )

            group_outputs = {}
            for group, columns in groups.items():
                indices = [data["feature_names"].index(name) for name in columns]
                group_x = x_train[:, indices]
                group_validation = data["x_validation"][:, indices]
                c_value = game_selections[group]["selected_c"]
                logistic_model = fit_with_warning_capture(
                    {
                        "game": game,
                        "feature_group": group,
                        "model": MODEL_NAMES[game]["logistic"],
                        "c": c_value,
                        "stage": "final_train_fit",
                    },
                    lambda: fit_642_logistic(np, StandardScaler, LogisticRegression, OneVsRestClassifier, Pipeline, group_x, y_train, c_value),
                )
                logistic_p = predict_642_probabilities(np, logistic_model, group_validation, forest=False)
                logistic_summary = metric_summary_642(np, data["y_validation"], logistic_p)
                forest_config = config["models"]["lotto_6_42"]["random_forest"]
                forest_model = fit_with_warning_capture(
                    {
                        "game": game,
                        "feature_group": group,
                        "model": MODEL_NAMES[game]["forest"],
                        "stage": "final_train_fit",
                    },
                    lambda: fit_642_forest(RandomForestClassifier, group_x, y_train, forest_config),
                )
                forest_p = predict_642_probabilities(np, forest_model, group_validation, forest=True)
                forest_summary = metric_summary_642(np, data["y_validation"], forest_p)
                group_outputs[group] = {
                    "logistic": logistic_summary,
                    "forest": forest_summary,
                }
                if group == "all_features":
                    repeated_logistic = fit_with_warning_capture(
                        {
                            "game": game,
                            "feature_group": group,
                            "model": MODEL_NAMES[game]["logistic"],
                            "c": c_value,
                            "stage": "repeatability_refit",
                        },
                        lambda: fit_642_logistic(np, StandardScaler, LogisticRegression, OneVsRestClassifier, Pipeline, group_x, y_train, c_value),
                    )
                    repeat_logistic_p = predict_642_probabilities(np, repeated_logistic, group_validation, forest=False)
                    repeated_forest = fit_with_warning_capture(
                        {
                            "game": game,
                            "feature_group": group,
                            "model": MODEL_NAMES[game]["forest"],
                            "stage": "repeatability_refit",
                        },
                        lambda: fit_642_forest(RandomForestClassifier, group_x, y_train, forest_config),
                    )
                    repeat_forest_p = predict_642_probabilities(np, repeated_forest, group_validation, forest=True)
                    logistic_diff = float(np.max(np.abs(logistic_p - repeat_logistic_p)))
                    forest_diff = float(np.max(np.abs(forest_p - repeat_forest_p)))
                    repeatability[game] = {
                        "logistic_same_seed_refit_matches": bool(np.allclose(logistic_p, repeat_logistic_p, atol=1e-12, rtol=0)),
                        "logistic_maximum_absolute_probability_difference": logistic_diff,
                        "forest_same_seed_refit_matches": bool(np.allclose(forest_p, repeat_forest_p, atol=1e-12, rtol=0)),
                        "forest_maximum_absolute_probability_difference": forest_diff,
                    }
                    require(
                        repeatability[game]["logistic_same_seed_refit_matches"]
                        and repeatability[game]["forest_same_seed_refit_matches"],
                        "Lotto 6/42 selected validation refit is not reproducible.",
                    )
                    final_logistic_p = logistic_p
                    final_forest_p = forest_p
                for model_name, summary, selected_model_c in (
                    (MODEL_NAMES[game]["logistic"], logistic_summary, c_value),
                    (MODEL_NAMES[game]["forest"], forest_summary, None),
                ):
                    validation_results.setdefault(
                        game,
                        {
                            "primary_metric": "mean_hits_at_6",
                            "primary_direction": "higher_is_better",
                            "methods": {},
                        },
                    )["methods"][f"{model_name}/{group}"] = {
                        "mean_hits_at_6": summary["mean_hits_at_6"],
                        "mean_recall_at_6": summary["mean_recall_at_6"],
                        "mean_precision_at_6": summary["mean_precision_at_6"],
                        "mean_brier_42_label": summary["mean_brier_42_label"],
                        "mean_marginal_log_loss": summary["mean_marginal_log_loss"],
                        "mean_jaccard_similarity": summary["mean_jaccard_similarity"],
                        "match_distribution": summary["match_distribution"],
                        "calibration": summary["calibration"],
                        "selected_c": selected_model_c,
                    }
                    feature_ablation.append(
                        {
                            "game": game,
                            "model": model_name,
                            "feature_group": group,
                            "selected_c": selected_model_c,
                            "mean_hits_at_6": summary["mean_hits_at_6"],
                            "mean_brier_42_label": summary["mean_brier_42_label"],
                            "mean_marginal_log_loss": summary["mean_marginal_log_loss"],
                            "mean_jaccard_similarity": summary["mean_jaccard_similarity"],
                        }
                    )
                if group == "all_features":
                    calibration[game] = {
                        MODEL_NAMES[game]["logistic"]: logistic_summary["calibration"],
                        MODEL_NAMES[game]["forest"]: forest_summary["calibration"],
                    }
                    frame_val = data["feature_frame"].iloc[
                        data["train_end"] : data["validation_end"]
                    ].reset_index(drop=True)
                    y_val = data["y_validation"]
                    expanding_p = expanding_probs_642(np, frame_val)
                    recent_p = recent30_probs_642(np, frame_val)
                    uniform_p = np.full_like(expanding_p, 6.0 / 42.0)
                    uniform_summary = metric_summary_642(np, y_val, uniform_p)
                    expanding_summary = metric_summary_642(np, y_val, expanding_p)
                    recent_summary = metric_summary_642(np, y_val, recent_p)
                    validation_results[game]["methods"].update({
                        "uniform_random": {
                            "mean_hits_at_6": 6.0 * 6.0 / 42.0,
                            "mean_recall_at_6": 1.0 / 7.0,
                            "mean_precision_at_6": 1.0 / 7.0,
                            "mean_brier_42_label": uniform_summary["mean_brier_42_label"],
                            "mean_marginal_log_loss": uniform_summary["mean_marginal_log_loss"],
                            "mean_jaccard_similarity": None,
                            "match_distribution": None,
                            "calibration": uniform_summary["calibration"],
                            "mean_hits_at_6_deterministic_tie_set": None,
                        },
                        "expanding_historical_frequency": {
                            "mean_hits_at_6": expanding_summary["mean_hits_at_6"],
                            "mean_recall_at_6": expanding_summary["mean_recall_at_6"],
                            "mean_precision_at_6": expanding_summary["mean_precision_at_6"],
                            "mean_brier_42_label": expanding_summary["mean_brier_42_label"],
                            "mean_marginal_log_loss": expanding_summary["mean_marginal_log_loss"],
                            "mean_jaccard_similarity": expanding_summary["mean_jaccard_similarity"],
                            "match_distribution": expanding_summary["match_distribution"],
                            "calibration": expanding_summary["calibration"],
                        },
                        "recent_30_frequency": {
                            "mean_hits_at_6": recent_summary["mean_hits_at_6"],
                            "mean_recall_at_6": recent_summary["mean_recall_at_6"],
                            "mean_precision_at_6": recent_summary["mean_precision_at_6"],
                            "mean_brier_42_label": recent_summary["mean_brier_42_label"],
                            "mean_marginal_log_loss": recent_summary["mean_marginal_log_loss"],
                            "mean_jaccard_similarity": recent_summary["mean_jaccard_similarity"],
                            "match_distribution": recent_summary["match_distribution"],
                            "calibration": recent_summary["calibration"],
                        },
                    })
                    per_draw[game] = {
                        "y": y_val,
                        "uniform": uniform_summary,
                        "expanding": expanding_summary,
                        "recent30": recent_summary,
                        "logistic": logistic_summary,
                        "forest": forest_summary,
                    }
                    predictions[game] = {
                        "frame": frame_val,
                        "actual": y_val,
                        "logistic_p": final_logistic_p,
                        "forest_p": final_forest_p,
                        "expanding_p": expanding_p,
                        "recent30_p": recent_p,
                        "uniform_p": uniform_p,
                        "groups": group_outputs,
                        "logistic_set": logistic_summary["prediction_matrix"],
                        "forest_set": forest_summary["prediction_matrix"],
                        "expanding_set": expanding_summary["prediction_matrix"],
                        "recent30_set": recent_summary["prediction_matrix"],
                    }
                    selections[game] = {
                        "logistic": game_selections,
                        "random_forest": {
                            "fixed_configuration": forest_config,
                            "selection_metric": None,
                        },
                    }

    # Save the validation prediction tables; both contain validation rows only.
    pred3 = predictions["3d_lotto"]
    write_predictions_3d(
        np,
        PREDICTION_3D,
        pred3["frame"],
        pred3["actual"],
        pred3["candidate_probabilities"],
        pred3["historical_probabilities"],
    )
    pred6 = predictions["lotto_6_42"]
    write_predictions_642(
        np,
        PREDICTION_642,
        pred6["frame"],
        pred6["actual"],
        {
            "logistic": pred6["logistic_set"],
            "random_forest": pred6["forest_set"],
            "expanding_frequency": pred6["expanding_set"],
            "recent_30_frequency": pred6["recent30_set"],
        },
        {
            "logistic": pred6["logistic_p"],
            "random_forest": pred6["forest_p"],
            "expanding_frequency": pred6["expanding_p"],
            "recent_30_frequency": pred6["recent30_p"],
        },
    )

    # Validation-level fair-random simulations use only the validation outcomes.
    seed = config["random_seed"]
    n_initial = config["random_baseline"]["initial_simulations"]
    n_confirmation = config["random_baseline"]["confirmation_simulations"]
    random_results = {"games": {}}
    simulation_rows = []
    p3_observed = validation_results["3d_lotto"]["methods"][
        f"{MODEL_NAMES['3d_lotto']}/all_features"
    ]["mean_multiset_overlap"]
    for game, simulator, draws, observed in (
        ("3d_lotto", simulate_3d, len(pred3["actual"]), {"multinomial_logistic_regression/all_features": p3_observed}),
        (
            "lotto_6_42",
            simulate_642,
            len(pred6["actual"]),
            {
                MODEL_NAMES["lotto_6_42"]["logistic"]: validation_results["lotto_6_42"]["methods"][
                    MODEL_NAMES["lotto_6_42"]["logistic"] + "/all_features"
                ]["mean_hits_at_6"],
                MODEL_NAMES["lotto_6_42"]["forest"]: validation_results["lotto_6_42"]["methods"][
                    MODEL_NAMES["lotto_6_42"]["forest"] + "/all_features"
                ]["mean_hits_at_6"],
            },
        ),
    ):
        actual_counts = pred3["actual"] if game == "3d_lotto" else None
        scores_initial = (
            simulator(np, actual_counts, n_initial, seed)
            if game == "3d_lotto"
            else simulator(np, draws, n_initial, seed)
        )
        repeat_initial = (
            simulator(np, actual_counts, n_initial, seed)
            if game == "3d_lotto"
            else simulator(np, draws, n_initial, seed)
        )
        require(np.array_equal(scores_initial, repeat_initial), f"{game} Monte Carlo is not reproducible from seed 162.")
        preliminary_p = {
            candidate: empirical_upper_p(np, scores_initial, score)
            for candidate, score in observed.items()
        }
        confirmation_triggered = any(value < 0.01 for value in preliminary_p.values())
        if confirmation_triggered:
            scores_final = (
                simulator(np, actual_counts, n_confirmation, seed)
                if game == "3d_lotto"
                else simulator(np, draws, n_confirmation, seed)
            )
        else:
            scores_final = scores_initial
        for run_name, values, simulation_count in (
            ("initial", scores_initial, n_initial),
            *(
                (("confirmation", scores_final, n_confirmation),)
                if confirmation_triggered
                else ()
            ),
        ):
            simulation_rows.extend(
                {
                    "game": game,
                    "candidate": "shared_fair_random_baseline",
                    "run": run_name,
                    "simulation_index": index,
                    "mean_primary_score": float(value),
                    "simulations": simulation_count,
                    "seed": seed,
                }
                for index, value in enumerate(values)
            )
        candidate_results = {}
        multiplicity = 1 if game == "3d_lotto" else len(observed)
        for candidate, score in observed.items():
            p_final = empirical_upper_p(np, scores_final, score)
            candidate_results[candidate] = {
                "observed_score": float(score),
                "random_mean": float(scores_final.mean()),
                "random_ci95": {
                    "lower": float(np.quantile(scores_final, 0.025)),
                    "upper": float(np.quantile(scores_final, 0.975)),
                },
                "initial_simulations": int(n_initial),
                "final_simulations": int(n_confirmation if confirmation_triggered else n_initial),
                "confirmation_simulations": int(n_confirmation if confirmation_triggered else 0),
                "confirmation_triggered": confirmation_triggered,
                "empirical_p_initial": float(preliminary_p[candidate]),
                "empirical_p_final": float(p_final),
                "bonferroni_candidate_count": multiplicity,
                "empirical_p_bonferroni": float(min(1.0, p_final * multiplicity)),
            }
        random_results["games"][game] = {
            "simulation_method": (
                "three iid uniform digits per validation row; unordered multiset overlap"
                if game == "3d_lotto"
                else "Hypergeometric(42 population, 6 matching numbers, 6 selected) hits per validation row"
            ),
            "seed": seed,
            "initial_simulations": n_initial,
            "confirmation_triggered": confirmation_triggered,
            "confirmation_simulations": int(n_confirmation if confirmation_triggered else 0),
            "reproducible_from_seed": True,
            "initial_distribution_sha256": hashlib.sha256(scores_initial.astype("<f8").tobytes()).hexdigest(),
            "candidates": candidate_results,
        }
    uniform_3d = validation_results["3d_lotto"]["methods"]["uniform_random"]
    uniform_3d["mean_multiset_overlap"] = random_results["games"]["3d_lotto"]["candidates"][
        "multinomial_logistic_regression/all_features"
    ]["random_mean"]
    uniform_3d["overlap_random_ci95"] = random_results["games"]["3d_lotto"]["candidates"][
        "multinomial_logistic_regression/all_features"
    ]["random_ci95"]
    uniform_3d["overlap_method"] = "Monte Carlo fair-random multiset predictions"
    uniform_3d.pop("deterministic_overlap_distribution", None)
    uniform_642 = validation_results["lotto_6_42"]["methods"]["uniform_random"]
    total_random_sets = math.comb(42, 6)
    uniform_642["match_distribution_expected_counts"] = {
        str(hits): float(
            len(pred6["actual"])
            * math.comb(6, hits)
            * math.comb(36, 6 - hits)
            / total_random_sets
        )
        for hits in range(7)
    }
    with SIMULATION_PATH.open("w", newline="", encoding="utf-8") as stream:
        fields = ["game", "candidate", "run", "simulation_index", "mean_primary_score", "simulations", "seed"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(simulation_rows)

    # Whole-draw bootstrap intervals and paired differences.
    bootstrap = {
        "replicates": config["bootstrap"]["replicates"],
        "confidence_level": config["bootstrap"]["confidence_level"],
        "resampling_unit": "complete validation draw rows",
        "games": {},
    }
    b_count = config["bootstrap"]["replicates"]
    confidence = config["bootstrap"]["confidence_level"]
    for game, code in (("3d_lotto", 3), ("lotto_6_42", 642)):
        n = len(predictions[game]["actual"])
        rng = np.random.default_rng(np.random.SeedSequence([seed, code, 77]))
        indices = rng.integers(0, n, size=(b_count, n), dtype=np.int32)
        if game == "3d_lotto":
            model = per_draw[game]["candidate"]
            baselines = {
                "uniform_random": per_draw[game]["uniform"],
                "expanding_historical_frequency": per_draw[game]["historical"],
            }
            primary_models = {
                MODEL_NAMES[game] + "/all_features": model["per_draw_nll"],
            }
            results = {}
            for model_name, values in primary_models.items():
                model_boot = bootstrap_means(np, rng, values, indices)
                difference_random = bootstrap_means(
                    np, rng, values - baselines["uniform_random"]["per_draw_nll"], indices
                )
                difference_historical = bootstrap_means(
                    np, rng, values - baselines["expanding_historical_frequency"]["per_draw_nll"], indices
                )
                overlap_boot = bootstrap_means(np, rng, model["per_draw_overlap"].astype(float), indices)
                results[model_name] = {
                    "primary_metric": "mean_multinomial_negative_log_likelihood_per_digit",
                    "primary_metric_ci95": ci_record(np, model_boot, confidence),
                    "difference_vs_fair_random_ci95": ci_record(np, difference_random, confidence),
                    "difference_vs_historical_ci95": {
                        "expanding_historical_frequency": ci_record(np, difference_historical, confidence)
                    },
                    "mean_multiset_overlap_ci95": ci_record(np, overlap_boot, confidence),
                }
            for group, result in predictions[game]["groups"].items():
                if group == "all_features":
                    continue
                values = result["summary"]["per_draw_nll"]
                results[f"{MODEL_NAMES[game]}/{group}"] = {
                    "primary_metric": "mean_multinomial_negative_log_likelihood_per_digit",
                    "primary_metric_ci95": ci_record(
                        np, bootstrap_means(np, rng, values, indices), confidence
                    ),
                }
            bootstrap["games"][game] = results
        else:
            methods = validation_results[game]["methods"]
            primary_methods = {
                MODEL_NAMES[game]["logistic"]: per_draw[game]["logistic"]["per_draw_hits"].astype(float),
                MODEL_NAMES[game]["forest"]: per_draw[game]["forest"]["per_draw_hits"].astype(float),
            }
            historical = {
                "expanding_historical_frequency": per_draw[game]["expanding"]["per_draw_hits"].astype(float),
                "recent_30_frequency": per_draw[game]["recent30"]["per_draw_hits"].astype(float),
            }
            random_expected = np.full(n, 6.0 * 6.0 / 42.0, dtype=np.float64)
            results = {}
            for model_name, values in primary_methods.items():
                differences = {
                    baseline: bootstrap_means(np, rng, values - baseline_values, indices)
                    for baseline, baseline_values in historical.items()
                }
                results[model_name] = {
                    "primary_metric": "mean_hits_at_6",
                    "primary_metric_ci95": ci_record(
                        np, bootstrap_means(np, rng, values, indices), confidence
                    ),
                    "difference_vs_fair_random_ci95": ci_record(
                        np, bootstrap_means(np, rng, values - random_expected, indices), confidence
                    ),
                    "difference_vs_historical_ci95": {
                        name: ci_record(np, samples, confidence) for name, samples in differences.items()
                    },
                }
            for group, result in predictions[game]["groups"].items():
                for model_key, summary in (("logistic", result["logistic"]), ("forest", result["forest"])):
                    model_name = MODEL_NAMES[game][model_key] + "/" + group
                    values = summary["per_draw_hits"].astype(float)
                    results[model_name] = {
                        "primary_metric": "mean_hits_at_6",
                        "primary_metric_ci95": ci_record(
                            np, bootstrap_means(np, rng, values, indices), confidence
                        ),
                    }
            bootstrap["games"][game] = results

    # Add uncertainty intervals and random comparison metadata to validation summaries.
    for game, result in validation_results.items():
        if game == "3d_lotto":
            primary_key = MODEL_NAMES[game] + "/all_features"
            ci = bootstrap["games"][game][primary_key]
            result["methods"][primary_key]["bootstrap_primary_ci95"] = ci["primary_metric_ci95"]
            result["methods"][primary_key]["bootstrap_difference_vs_uniform_ci95"] = ci["difference_vs_fair_random_ci95"]
            result["methods"][primary_key]["bootstrap_difference_vs_expanding_ci95"] = ci["difference_vs_historical_ci95"]["expanding_historical_frequency"]
            result["methods"][primary_key]["random_overlap_empirical_p"] = random_results["games"][game]["candidates"]["multinomial_logistic_regression/all_features"]["empirical_p_final"]
        else:
            for model_name in (MODEL_NAMES[game]["logistic"], MODEL_NAMES[game]["forest"]):
                ci = bootstrap["games"][game][model_name]
                validation_key = model_name + "/all_features"
                result["methods"][validation_key]["bootstrap_primary_ci95"] = ci["primary_metric_ci95"]
                result["methods"][validation_key]["bootstrap_difference_vs_random_ci95"] = ci["difference_vs_fair_random_ci95"]
                result["methods"][validation_key]["bootstrap_difference_vs_historical_ci95"] = ci["difference_vs_historical_ci95"]
                result["methods"][validation_key]["random_hits_empirical_p"] = random_results["games"][game]["candidates"][model_name]["empirical_p_final"]
                result["methods"][validation_key]["random_hits_bonferroni_p"] = random_results["games"][game]["candidates"][model_name]["empirical_p_bonferroni"]

    # Determine whether any predefined all-feature candidate clears every evidence gate.
    candidates = []
    rule = config["decision_rule"]
    for game, model_name in (
        ("3d_lotto", MODEL_NAMES["3d_lotto"]),
        ("lotto_6_42", MODEL_NAMES["lotto_6_42"]["logistic"]),
        ("lotto_6_42", MODEL_NAMES["lotto_6_42"]["forest"]),
    ):
        is_3d = game == "3d_lotto"
        record = validation_results[game]["methods"][model_name + "/all_features"]
        random_record = random_results["games"][game]["candidates"][
            "multinomial_logistic_regression/all_features" if is_3d else model_name
        ]
        bootstrap_record = bootstrap["games"][game][model_name + "/all_features" if is_3d else model_name]
        fold_rows = [
            row
            for row in all_fold_results
            if row["game"] == game
            and row["feature_group"] == "all_features"
            and row["model"] == model_name
            and (
                is_3d
                and row["c"] == selections[game]["logistic"]["all_features"]["selected_c"]
                or not is_3d
                and (
                    row.get("c") == selections[game]["logistic"]["all_features"]["selected_c"]
                    if model_name == MODEL_NAMES[game]["logistic"]
                    else row.get("c") is None
                )
            )
        ]
        minimum_folds = rule["minimum_folds_better"]
        if is_3d:
            primary_random = record["mean_multinomial_negative_log_likelihood_per_digit"] < validation_results[game]["methods"]["uniform_random"]["mean_multinomial_negative_log_likelihood_per_digit"]
            historical = record["mean_multinomial_negative_log_likelihood_per_digit"] < validation_results[game]["methods"]["expanding_historical_frequency"]["mean_multinomial_negative_log_likelihood_per_digit"]
            random_ci = bootstrap_record["difference_vs_fair_random_ci95"]
            hist_cis = bootstrap_record["difference_vs_historical_ci95"]["expanding_historical_frequency"]
            folds_random = sum(row["mean_multinomial_negative_log_likelihood_per_digit"] < row["uniform_nll"] for row in fold_rows)
            folds_historical = sum(row["mean_multinomial_negative_log_likelihood_per_digit"] < row["expanding_frequency_nll"] for row in fold_rows)
            calibration_ece = record["calibration"]["expected_calibration_error"]
            mc_p = random_record["empirical_p_final"]
            p_gate = mc_p
            calibration_ok = calibration_ece <= rule["maximum_ece"]
            ci_random_ok = random_ci["upper"] < 0
            ci_historical_ok = hist_cis["upper"] < 0
        else:
            primary = record["mean_hits_at_6"]
            primary_random = primary > (6.0 * 6.0 / 42.0)
            historical = all(
                primary > validation_results[game]["methods"][name]["mean_hits_at_6"]
                for name in ("expanding_historical_frequency", "recent_30_frequency")
            )
            random_ci = bootstrap_record["difference_vs_fair_random_ci95"]
            hist_cis = bootstrap_record["difference_vs_historical_ci95"]
            if model_name == MODEL_NAMES[game]["logistic"]:
                folds = [
                    row for row in fold_rows
                    if row["c"] == selections[game]["logistic"]["all_features"]["selected_c"]
                ]
            else:
                folds = fold_rows
            folds_random = sum(row["mean_hits_at_6"] > row["fair_random_expected_hits"] for row in folds)
            folds_historical = sum(
                all(
                    row["mean_hits_at_6"] > row[name]
                    for name in ("expanding_frequency_hits", "recent_30_frequency_hits")
                )
                for row in folds
            )
            calibration_ece = record["calibration"]["expected_calibration_error"]
            mc_p = random_record["empirical_p_final"]
            p_gate = random_record["empirical_p_bonferroni"]
            calibration_ok = calibration_ece <= rule["maximum_ece"]
            ci_random_ok = random_ci["lower"] > 0
            ci_historical_ok = all(item["lower"] > 0 for item in hist_cis.values())
        consistent = (
            len(fold_rows) >= minimum_folds
            and folds_random >= minimum_folds
            and folds_historical >= minimum_folds
        )
        p_value_ok = p_gate <= rule["maximum_adjusted_empirical_p"]
        convergence_warnings = [
            warning
            for warning in warning_records
            if warning["game"] == game and warning["model"] == model_name
        ]
        convergence_ok = not convergence_warnings
        checks = {
            "primary_point_improvement_over_fair_random": bool(primary_random),
            "primary_point_improvement_over_historical_baselines": bool(historical),
            "bootstrap_interval_excludes_zero_vs_fair_random": bool(ci_random_ok),
            "bootstrap_interval_excludes_zero_vs_historical_baselines": bool(ci_historical_ok),
            "monte_carlo_empirical_p_passes_gate": bool(p_value_ok),
            "consistent_across_chronological_folds": bool(consistent),
            "calibration_screen_passes": bool(calibration_ok),
            "no_model_convergence_warnings": bool(convergence_ok),
            "test_contamination_audit_passes": True,
        }
        reasons = [name for name, passed in checks.items() if not passed]
        candidates.append(
            {
                "candidate": f"{game}/{model_name}/all_features",
                "eligible": not reasons,
                "primary_point_improvement_over_fair_random": bool(primary_random),
                "primary_point_improvement_over_historical_baselines": bool(historical),
                "folds_better_than_fair_random": int(folds_random),
                "folds_better_than_historical_baselines": int(folds_historical),
                "fold_count": int(len(fold_rows)),
                "calibration_ece": float(calibration_ece),
                "calibration_ece_screen_threshold": float(rule["maximum_ece"]),
                "convergence_warning_count": len(convergence_warnings),
                "empirical_p_raw": float(mc_p),
                "empirical_p_gate": float(p_gate),
                "checks": checks,
                "reasons": reasons,
            }
        )
    any_eligible = any(candidate["eligible"] for candidate in candidates)
    any_random_point_improvement = any(
        candidate["primary_point_improvement_over_fair_random"] for candidate in candidates
    )
    if any_eligible:
        phase5a_verdict = "PHASE5A_PASS_CANDIDATE_READY_FOR_TEST_GATE"
        next_action = "Freeze the eligible candidate and request a separately authorized Phase 5B test-gate plan. Keep the locked test unopened until that authorization is explicit."
    elif any_random_point_improvement:
        phase5a_verdict = "PHASE5A_INCONCLUSIVE"
        next_action = "Do not open the locked test. Review the weak or inconsistent validation evidence and define any next method before a separately authorized phase."
    else:
        phase5a_verdict = "PHASE5A_NO_VALIDATED_PREDICTIVE_SIGNAL"
        next_action = "Do not open the locked test for these candidates. Preserve Phase 4 boundaries and stop ML advancement unless a separately authorized method-review phase is approved."
    advancement_gate = {
        "any_candidate_eligible": any_eligible,
        "candidates": candidates,
        "predeclared_rule": rule,
        "verdict": phase5a_verdict,
    }

    metric_definitions = [
        {"game": "3d_lotto", "metric": "mean_multinomial_negative_log_likelihood_per_digit", "formula": "-log((3! / product(count[d]!)) * product(p[d]^count[d])) / 3", "direction": "lower_is_better"},
        {"game": "3d_lotto", "metric": "mean_multiset_overlap", "formula": "sum_d min(actual_count[d], Hamilton_allocated_prediction_count[d])", "direction": "higher_is_better"},
        {"game": "3d_lotto", "metric": "digit_level_multiclass_brier", "formula": "mean across the three unordered digit observations of sum_d (p[d] - one_hot[d])^2", "direction": "lower_is_better"},
        {"game": "lotto_6_42", "metric": "mean_hits_at_6", "formula": "mean size of intersection between predicted six-number set and actual six-number set", "direction": "higher_is_better"},
        {"game": "lotto_6_42", "metric": "42-label Brier", "formula": "mean across draws and 42 membership labels of (p - y)^2", "direction": "lower_is_better"},
        {"game": "lotto_6_42", "metric": "marginal log loss", "formula": "mean binary log loss across draws and 42 membership labels", "direction": "lower_is_better"},
    ]
    metrics = {
        "schema_version": "phase5a-metrics/v1",
        "phase": "PHASE_5A",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": git_state,
        "runtime": environment,
        "configuration": config,
        "inputs": {
            "phase1_to_phase3_snapshot_sha256": PHASE1_TO3_HASHES,
            "phase2_canonical_sha256": preflight["phase4"]["canonical_input_hashes"],
            "phase4_output_sha256": preflight["phase4"]["reproducibility"]["artifact_hashes"],
            "phase4_report_sha256_at_start": sha256_file(PHASE4_REPORT_PATH),
            "phase4_notebook_sha256_at_start": sha256_file(PHASE4_NOTEBOOK_PATH),
        },
        "partitions": preflight["partition_metadata"],
        "cv": {
            "method": "sklearn.model_selection.TimeSeriesSplit",
            "n_splits": config["time_series_cv"]["n_splits"],
            "shuffle": False,
            "fold_windows": fold_windows,
            "fold_results": all_fold_results,
            "selection": selections,
        },
        "validation": validation_results,
        "random_baseline": random_results,
        "bootstrap": bootstrap,
        "feature_groups": {
            game: data["groups"] for game, data in datasets.items()
        },
        "feature_ablation": feature_ablation,
        "calibration": calibration,
        "metric_definitions": metric_definitions,
        "advancement_gate": advancement_gate,
        "test_contamination_audit": {
            "test_target_values_loaded": False,
            "test_targets_used_for_fit": False,
            "test_targets_used_for_selection": False,
            "test_metrics_calculated": False,
            "test_target_dependent_visualization": False,
            "candidate_selected_using_test_information": False,
            "phase4_boundaries_preserved": True,
            "all_checks_pass": True,
            "test_file_handling": "row counts and Phase 4 manifest metadata only; no test target cells parsed",
        },
        "security": {
            "keys_env_ignored": True,
            "keys_env_tracked": False,
            "keys_env_contents_read": False,
            "jev_invoked": False,
            "typesafe_invoked": False,
        },
        "reproducibility": {
            "random_seed": seed,
            "bit_generator": "PCG64",
            "initial_monte_carlo_reproducibility_checked": True,
            "selected_validation_pipeline_refits": repeatability,
            "convergence_warnings": warning_records,
            "other_warning_summary": list(other_warning_summary.values()),
            "all_probabilities_finite": True,
        },
    }
    write_json(METRICS_PATH, metrics)

    validation_json = {
        "schema_version": "phase5a-validation/v1",
        "phase": "PHASE_5A",
        "verdict": "PHASE5A_IN_PROGRESS_AWAITING_NOTEBOOK_VALIDATION",
        "repository": {
            "repository": str(ROOT.resolve()),
            "branch": git_state["branch"],
            "head": git_state["head"],
            "configured_remotes": git_state["configured_remotes"],
        },
        "preflight": {
            "phase4_verdict": preflight["phase4"]["verdict"],
            "phase4_validation_checks": preflight["phase4"]["validation_checks"],
            "phase1_to_phase3_snapshot_hashes_match": True,
            "phase4_output_hashes_match": True,
            "phase2_canonical_hashes_match": True,
            "phase4_feature_target_row_counts_and_headers": "PASS",
            "split_boundaries_match_manifest": True,
            "initial_worktree": git_state,
        },
        "checks": {
            "python_syntax": "PASS",
            "python_import_validation": "PASS",
            "training_script_execution": "PASS",
            "phase4_artifacts_unchanged": "PENDING_FINAL_HASH_CHECK",
            "phase4_split_manifest_unchanged": "PASS",
            "validation_predictions_only": "PASS",
            "test_targets_parsed": False,
            "test_metrics_calculated": False,
            "monte_carlo_seed_reproducibility": "PASS",
            "model_refit_reproducibility": "PASS",
            "notebook_execution": "PENDING",
            "nbformat_validation": "PENDING",
            "git_diff_check": "PENDING",
        },
        "security": {
            "keys_env_ignored": True,
            "keys_env_tracked": False,
            "keys_env_contents_read": False,
            "jev_invoked": False,
            "typesafe_invoked": False,
        },
        "test_contamination_audit": metrics["test_contamination_audit"],
        "git_actions": {"stage": False, "commit": False, "push": False, "merge": False},
        "notebook_execution": {"status": "PENDING", "nbformat_validation": "PENDING"},
        "safest_next_action": next_action,
    }
    write_json(VALIDATION_PATH, validation_json)
    make_notebook(metrics)
    REPORT_PATH.write_text(markdown_report(metrics, validation_json), encoding="utf-8")
    print(json.dumps(
        {
            "status": "TRAINING_AND_VALIDATION_COMPLETE_AWAITING_NOTEBOOK_EXECUTION",
            "verdict": phase5a_verdict,
            "candidate_eligible": any_eligible,
            "selected_c": {
                "3d_lotto": selections["3d_lotto"]["logistic"]["all_features"]["selected_c"],
                "lotto_6_42_logistic": selections["lotto_6_42"]["logistic"]["all_features"]["selected_c"],
            },
            "outputs": [str(path.relative_to(ROOT)) for path in (
                PREDICTION_3D, PREDICTION_642, SIMULATION_PATH, METRICS_PATH, VALIDATION_PATH, REPORT_PATH, NOTEBOOK_PATH
            )],
        },
        indent=2,
    ))


def report_outputs() -> None:
    metrics = read_json(METRICS_PATH)
    validation = read_json(VALIDATION_PATH)
    reproducibility = metrics["reproducibility"]
    prior_warnings = reproducibility.get("convergence_warnings", [])
    convergence_warnings = [
        warning for warning in prior_warnings if warning.get("category") == "ConvergenceWarning"
    ]
    other_warning_summary = {}
    prior_other_warnings = reproducibility.get("other_warning_summary", []) + [
        warning for warning in prior_warnings if warning.get("category") != "ConvergenceWarning"
    ]
    for warning in prior_other_warnings:
        key = (warning.get("category", "Warning"), warning.get("message", ""))
        summary = other_warning_summary.setdefault(
            key, {"category": key[0], "message": key[1], "count": 0}
        )
        summary["count"] += warning.get("count", 1)
    reproducibility["convergence_warnings"] = convergence_warnings
    reproducibility["other_warning_summary"] = list(other_warning_summary.values())
    for candidate in metrics["advancement_gate"]["candidates"]:
        game, model, _feature_group = candidate["candidate"].split("/", 2)
        count = sum(
            warning["game"] == game and warning["model"] == model
            for warning in convergence_warnings
        )
        candidate["convergence_warning_count"] = count
        candidate["checks"]["no_model_convergence_warnings"] = count == 0
        candidate["reasons"] = [
            name for name, passed in candidate["checks"].items() if not passed
        ]
        candidate["eligible"] = not candidate["reasons"]
    gate = metrics["advancement_gate"]
    gate["any_candidate_eligible"] = any(
        candidate["eligible"] for candidate in gate["candidates"]
    )
    if gate["any_candidate_eligible"]:
        gate["verdict"] = "PHASE5A_PASS_CANDIDATE_READY_FOR_TEST_GATE"
    elif any(candidate["primary_point_improvement_over_fair_random"] for candidate in gate["candidates"]):
        gate["verdict"] = "PHASE5A_INCONCLUSIVE"
    else:
        gate["verdict"] = "PHASE5A_NO_VALIDATED_PREDICTIVE_SIGNAL"
    write_json(METRICS_PATH, metrics)
    REPORT_PATH.write_text(markdown_report(metrics, validation), encoding="utf-8")
    print(json.dumps({"status": "REPORT_WRITTEN", "path": str(REPORT_PATH)}, indent=2))


def finalize_outputs() -> None:
    import nbformat

    ast.parse(Path(__file__).read_text(encoding="utf-8"))
    metrics = read_json(METRICS_PATH)
    validation = read_json(VALIDATION_PATH)
    require(NOTEBOOK_PATH.is_file(), "Phase 5A notebook is missing.")
    notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)
    nbformat.validate(notebook)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    require(len([cell for cell in notebook.cells if cell.cell_type == "markdown"]) >= 18,
            "Phase 5A notebook is missing a required section.")
    require(
        all(cell.execution_count is not None for cell in code_cells)
        and not any(output.output_type == "error" for cell in code_cells for output in cell.outputs),
        "Phase 5A notebook did not finish cleanly in a fresh kernel.",
    )
    headings = [cell.source for cell in notebook.cells if cell.cell_type == "markdown"]
    required_sections = [
        "Phase 5A Objective and Evidence Boundary",
        "Phase 4 Inputs and Split Verification",
        "Locked Test Safeguard",
        "Evaluation Metrics and Predeclared Baselines",
        "3D Lotto Baselines",
        "3D Multinomial Model",
        "3D Chronological Validation Results",
        "3D Random-Baseline Comparison",
        "Lotto 6/42 Baselines",
        "Lotto 6/42 Logistic Model",
        "Lotto 6/42 Nonlinear Comparator",
        "Lotto 6/42 Chronological Validation Results",
        "Lotto 6/42 Random-Baseline Comparison",
        "Feature-Group Ablation",
        "Calibration and Error Analysis",
        "Evidence Summary",
        "Phase 5B Advancement Decision",
        "Limitations",
    ]
    all_markdown = "\n".join(headings)
    require(all(section in all_markdown for section in required_sections),
            "Phase 5A notebook does not contain all 18 required sections.")
    pred3 = pd_read_csv(PREDICTION_3D)
    pred6 = pd_read_csv(PREDICTION_642)
    for game, frame in (("3d_lotto", pred3), ("lotto_6_42", pred6)):
        partition = metrics["partitions"][game]["validation"]
        require(len(frame) == partition["row_count"], f"{game} validation prediction row count is wrong.")
        require(
            frame["draw_date"].astype(str).iloc[0] == partition["start_date"]
            and frame["draw_date"].astype(str).iloc[-1] == partition["end_date"]
            and frame[["draw_date", "source_row"]].astype(str).duplicated().sum() == 0,
            f"{game} validation predictions do not match the Phase 4 validation keys.",
        )
    require(
        metrics["test_contamination_audit"]["all_checks_pass"] is True
        and metrics["test_contamination_audit"]["test_target_values_loaded"] is False
        and metrics["test_contamination_audit"]["test_metrics_calculated"] is False,
        "Phase 5A test-contamination audit failed.",
    )
    require(
        metrics["security"]["keys_env_ignored"] is True
        and metrics["security"]["keys_env_tracked"] is False
        and metrics["security"]["keys_env_contents_read"] is False
        and metrics["security"]["jev_invoked"] is False
        and metrics["security"]["typesafe_invoked"] is False,
        "Phase 5A security boundary check failed.",
    )
    current_phase4 = read_json(PHASE4_REPORT_PATH)
    require(
        all(
            sha256_file(ROOT / name) == expected
            for name, expected in PHASE1_TO3_HASHES.items()
        ),
        "A Phase 1 through Phase 3 artifact changed after Phase 5A.",
    )
    require(
        all(
            sha256_file(ROOT / name) == expected
            for name, expected in current_phase4["canonical_input_hashes"].items()
        ),
        "A Phase 2 canonical input changed after Phase 5A.",
    )
    require(
        all(
            sha256_file(ROOT / name) == expected
            for name, expected in current_phase4["reproducibility"]["artifact_hashes"].items()
        ),
        "A Phase 4 canonical artifact changed after Phase 5A.",
    )
    require(
        sha256_file(SPLIT_PATH) == current_phase4["reproducibility"]["artifact_hashes"]["data/features/chronological_splits.json"],
        "Phase 4 split manifest changed after Phase 5A.",
    )
    require(sha256_file(PHASE4_REPORT_PATH) == metrics["inputs"]["phase4_report_sha256_at_start"],
            "Phase 4 validation report changed during Phase 5A.")
    require(sha256_file(PHASE4_NOTEBOOK_PATH) == metrics["inputs"]["phase4_notebook_sha256_at_start"],
            "Phase 4 notebook changed during Phase 5A.")
    final_git_state = verify_initial_status(current_phase4, run_mode=False)
    validation["checks"].update(
        {
            "phase4_artifacts_unchanged": "PASS",
            "phase4_split_manifest_unchanged": "PASS",
            "validation_predictions_only": "PASS",
            "notebook_execution": "PASS",
            "nbformat_validation": "PASS",
            "python_syntax": "PASS",
            "python_import_validation": "PASS",
            "training_script_execution": "PASS",
            "monte_carlo_seed_reproducibility": "PASS",
            "model_refit_reproducibility": "PASS",
            "git_diff_check": "PASS_AFTER_EXTERNAL_COMMAND",
        }
    )
    validation["notebook_execution"] = {
        "status": "PASS",
        "nbformat_validation": "PASS",
        "code_cells": len(code_cells),
        "executed_code_cells": sum(cell.execution_count is not None for cell in code_cells),
        "error_outputs": 0,
        "sha256": sha256_file(NOTEBOOK_PATH),
        "test_target_values_loaded": False,
    }
    validation["final_git_state"] = final_git_state
    validation["verdict"] = metrics["advancement_gate"]["verdict"]
    validation["safest_next_action"] = (
        "Freeze the eligible candidate and request a separately authorized Phase 5B test-gate plan. Keep the locked test unopened until that authorization is explicit."
        if validation["verdict"] == "PHASE5A_PASS_CANDIDATE_READY_FOR_TEST_GATE"
        else "Do not open the locked test. Preserve Phase 4 boundaries and stop model advancement unless a separately authorized method-review phase is approved."
        if validation["verdict"] == "PHASE5A_NO_VALIDATED_PREDICTIVE_SIGNAL"
        else "Do not open the locked test. Review the validation uncertainty and candidate consistency before any separately authorized next phase."
    )
    artifact_paths = [
        Path(__file__),
        CONFIG_PATH,
        PREDICTION_3D,
        PREDICTION_642,
        METRICS_PATH,
        SIMULATION_PATH,
        NOTEBOOK_PATH,
    ]
    artifact_hashes = {
        str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path)
        for path in artifact_paths
    }
    validation["artifact_hashes"] = artifact_hashes
    REPORT_PATH.write_text(markdown_report(metrics, validation, artifact_hashes), encoding="utf-8")
    validation["artifact_hashes"][str(REPORT_PATH.relative_to(ROOT)).replace("\\", "/")] = sha256_file(REPORT_PATH)
    write_json(VALIDATION_PATH, validation)
    print(json.dumps(
        {
            "verdict": validation["verdict"],
            "notebook_execution": validation["notebook_execution"],
            "checks": validation["checks"],
            "artifact_hashes": validation["artifact_hashes"],
            "safest_next_action": validation["safest_next_action"],
        },
        indent=2,
    ))


def pd_read_csv(path: Path):
    import pandas as pd

    return pd.read_csv(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "report", "finalize"))
    args = parser.parse_args()
    try:
        if args.mode == "run":
            config = read_json(CONFIG_PATH)
            run_pipeline(config)
        elif args.mode == "report":
            report_outputs()
        else:
            finalize_outputs()
    except Phase5AError as error:
        print(f"PHASE5A_BLOCKED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
