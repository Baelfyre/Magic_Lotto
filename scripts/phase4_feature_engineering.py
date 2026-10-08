# @codebase_provenance_JEO
"""Build leakage-safe Phase 4 feature, target, and split artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MIN_HISTORY = 101
WINDOWS = (10, 30, 100)
EXPECTED_ROWS = {"3d_lotto": 3718, "lotto_6_42": 1605}
PHASE4_FILES = {
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
}
PRIOR_PHASE_ARTIFACTS = {
    "__pycache__/monte_carlo_baseline.cpython-312.pyc",
    "monte_carlo_baseline.py",
    "notebooks/lotto_statistical_analysis.ipynb",
    "phase3_monte_carlo_random_baseline.md",
    "phase3_monte_carlo_results.json",
    "phase3_simulation_distributions.csv",
}
CANONICAL_INPUTS = {
    "3d_analysis_ready": "swertres_9pm_analysis_ready.csv",
    "3d_cleaned": "swertres_9pm_cleaned_normalized.csv",
    "3d_frequency": "swertres_9pm_digit_frequency.csv",
    "3d_phase2": "swertres_9pm_phase2_analysis.csv",
    "6_42_cleaned": "lotto_6_42_cleaned_normalized.csv",
    "6_42_frequency": "lotto_6_42_number_frequency.csv",
    "6_42_phase2": "lotto_6_42_phase2_analysis.csv",
    "phase2_report": "phase2_randomness_diagnostics.md",
}


class Phase4Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4Error(message)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def preflight(root: Path) -> dict[str, object]:
    top = git(root, "rev-parse", "--show-toplevel")
    require(top.returncode == 0, "BLOCKED: repository is not a Git worktree")
    require(Path(top.stdout.strip()).resolve() == root.resolve(), "BLOCKED: unexpected repository root")
    branch = git(root, "branch", "--show-current")
    head = git(root, "rev-parse", "HEAD")
    remotes = git(root, "remote")
    require(branch.returncode == head.returncode == remotes.returncode == 0, "BLOCKED: Git state is unavailable")
    require(bool(branch.stdout.strip()) and len(head.stdout.strip()) == 40, "BLOCKED: branch or HEAD is unavailable")
    require(git(root, "diff", "--quiet").returncode == 0, "BLOCKED: tracked worktree changes exist")
    require(git(root, "diff", "--cached", "--quiet").returncode == 0, "BLOCKED: staged changes exist")

    tracked = git(root, "ls-files", "-z")
    ignored = git(root, "check-ignore", "-q", "--", "Keys.env")
    require(tracked.returncode == ignored.returncode == 0, "BLOCKED: Keys.env Git metadata cannot be verified")
    tracked_keys = [p for p in tracked.stdout.split("\0") if Path(p).name.casefold() == "keys.env"]
    require(not tracked_keys, "BLOCKED_SECRET_TRACKED")

    status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    require(status.returncode == 0, "BLOCKED: working-tree status is unavailable")
    allowed = PHASE4_FILES | PRIOR_PHASE_ARTIFACTS
    changed = {line[3:].replace("\\", "/") for line in status.stdout.splitlines() if len(line) >= 4}
    require(changed <= allowed, f"BLOCKED: unexpected worktree paths: {sorted(changed - allowed)}")
    return {
        "repository": str(root.resolve()),
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "configured_remotes": [value for value in remotes.stdout.splitlines() if value],
        "tracked_worktree_clean": True,
        "index_clean": True,
        "initial_or_existing_untracked_paths": sorted(changed),
        "keys_env_ignored": True,
        "keys_env_tracked": False,
        "keys_env_contents_read": False,
    }


def read_csv(root: Path, name: str) -> tuple[list[str], list[dict[str, str]]]:
    path = root / name
    require(path.is_file(), f"BLOCKED: required canonical input is missing: {name}")
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        rows = list(reader)
    require(bool(headers) and bool(rows), f"BLOCKED: empty canonical input: {name}")
    return headers, rows


def check_headers(name: str, headers: list[str], required: set[str]) -> None:
    missing = required - set(headers)
    require(not missing, f"BLOCKED: {name} is missing columns {sorted(missing)}")


def parse3(value: str) -> np.ndarray:
    try:
        digits = [int(part) for part in value.split("-")]
    except ValueError as error:
        raise Phase4Error("BLOCKED: malformed 3D combination") from error
    require(len(digits) == 3 and all(0 <= digit <= 9 for digit in digits), "BLOCKED: invalid 3D multiset")
    return np.bincount(digits, minlength=10).astype(np.int16)


def parse642(value: str) -> np.ndarray:
    try:
        numbers = [int(part) for part in value.split("-")]
    except ValueError as error:
        raise Phase4Error("BLOCKED: malformed Lotto 6/42 unordered combination") from error
    require(
        len(numbers) == 6 and len(set(numbers)) == 6 and all(1 <= n <= 42 for n in numbers),
        "BLOCKED: invalid Lotto 6/42 set",
    )
    return np.bincount(numbers, minlength=43)[1:].astype(np.int16)


def record_keys(rows: list[dict[str, str]], game: str) -> list[tuple[str, str]]:
    result = [(row["draw_date"], row["source_row"]) for row in rows]
    require(all(date for date, _ in result), f"BLOCKED: {game} has an empty date key")
    require(len(result) == len(set(result)), f"BLOCKED: {game} has duplicate stable keys")
    require(
        result == sorted(result, key=lambda item: (item[0], int(item[1]))),
        f"BLOCKED: {game} rows are not chronologically ordered by date and source row",
    )
    require(len({date for date, _ in result}) == len(result), f"BLOCKED: {game} has duplicate draw dates")
    return result


def phase3_and_input_validation(root: Path) -> tuple[dict[str, object], dict[str, object]]:
    for name in [*CANONICAL_INPUTS.values(), "phase3_monte_carlo_results.json",
                 "phase3_monte_carlo_random_baseline.md", "phase3_simulation_distributions.csv",
                 "monte_carlo_baseline.py", "notebooks/lotto_statistical_analysis.ipynb"]:
        require((root / name).is_file(), f"BLOCKED: required Phase 1 through Phase 3 artifact is missing: {name}")

    phase3 = json.loads((root / "phase3_monte_carlo_results.json").read_text(encoding="utf-8"))
    require(phase3.get("verdict") == "PHASE3_PASS_RANDOM_COMPATIBLE", "BLOCKED: Phase 3 verdict is not validated")
    p3v = phase3.get("validation", {})
    require(
        p3v.get("canonical_input_structure") == "PASS"
        and p3v.get("phase2_feature_consistency") == "PASS"
        and p3v.get("seeded_full_rerun_artifact_hash_check", "").startswith("PASS:")
        and p3v.get("jev_or_typesafe_called") is False
        and p3v.get("keys_env_contents_read") is False,
        "BLOCKED: Phase 3 validation status cannot be established",
    )
    for key, entry in phase3.get("inputs", {}).items():
        name = Path(entry.get("path", "")).name
        expected = next((v for v in CANONICAL_INPUTS.values() if v == name), None)
        if expected:
            require(sha256_file(root / expected) == entry.get("sha256"), f"BLOCKED: Phase 3 input hash mismatch: {expected}")

    nb = json.loads((root / "notebooks/lotto_statistical_analysis.ipynb").read_text(encoding="utf-8"))
    code_cells = [cell for cell in nb.get("cells", []) if cell.get("cell_type") == "code"]
    require(bool(code_cells) and all(cell.get("execution_count") is not None for cell in code_cells),
            "BLOCKED: canonical Phase 3 notebook is not fully executed")
    require(not any(out.get("output_type") == "error" for cell in code_cells for out in cell.get("outputs", [])),
            "BLOCKED: canonical Phase 3 notebook contains execution errors")

    h3, rows3 = read_csv(root, CANONICAL_INPUTS["3d_analysis_ready"])
    h3p, rows3p = read_csv(root, CANONICAL_INPUTS["3d_phase2"])
    h6, rows6 = read_csv(root, CANONICAL_INPUTS["6_42_cleaned"])
    h6p, rows6p = read_csv(root, CANONICAL_INPUTS["6_42_phase2"])
    check_headers("3D canonical input", h3, {"draw_date", "source_row", "combination", "record_status"})
    check_headers("3D Phase 2 input", h3p, {"draw_date", "combination_unordered", "pattern_type", "digit_sum", "previous_draw_digit_overlap"})
    check_headers("6/42 canonical input", h6, {"draw_date", "source_row", "combination_sorted", "record_status"})
    check_headers("6/42 Phase 2 input", h6p, {"draw_date", "draw_sum", "odd_count", "previous_draw_overlap"})
    require(len(rows3) == len(rows3p) == EXPECTED_ROWS["3d_lotto"], "BLOCKED: 3D canonical and Phase 2 row counts differ")
    require(len(rows6) == len(rows6p) == EXPECTED_ROWS["lotto_6_42"], "BLOCKED: 6/42 canonical and Phase 2 row counts differ")
    keys3 = record_keys(rows3, "3D Lotto")
    keys6 = record_keys(rows6, "Lotto 6/42")
    require(keys3 == [(r["draw_date"], r["source_row"]) for r in rows3p], "BLOCKED: 3D Phase 2 rows do not align")
    require([k[0] for k in keys6] == [r["draw_date"] for r in rows6p], "BLOCKED: 6/42 Phase 2 chronology does not align")

    draws3 = np.stack([parse3(row["combination"]) for row in rows3])
    draws6 = np.stack([parse642(row["combination_sorted"]) for row in rows6])
    require(all(row["record_status"] == "valid" for row in rows3 + rows6), "BLOCKED: invalid record status in canonical draws")

    prior3 = np.zeros(10, dtype=np.int64)
    prior6 = np.zeros(42, dtype=np.int64)
    for index, (draw, p2) in enumerate(zip(draws3, rows3p)):
        unordered = "-".join(map(str, np.repeat(np.arange(10), draw)))
        require(unordered == p2["combination_unordered"],
                "BLOCKED: Phase 2 3D multiset differs from canonical")
        pattern = "all_distinct" if np.count_nonzero(draw) == 3 else "triple" if draw.max() == 3 else "one_pair"
        require(pattern == p2["pattern_type"] and int(p2["digit_sum"]) == int(np.dot(draw, np.arange(10))),
                "BLOCKED: Phase 2 3D pattern or sum differs from canonical")
        overlap = int(np.minimum(draw, prior3).sum())
        if index:
            require(int(float(p2["previous_draw_digit_overlap"])) == overlap, "BLOCKED: Phase 2 3D overlap differs")
        else:
            require(not p2["previous_draw_digit_overlap"], "BLOCKED: first Phase 2 3D overlap is not empty")
        prior3 = draw
    for index, (draw, p2) in enumerate(zip(draws6, rows6p)):
        numbers = (np.flatnonzero(draw) + 1).tolist()
        require(sum(draw) == 6, "BLOCKED: 6/42 set representation is malformed")
        require(int(p2["draw_sum"]) == sum(numbers) and int(p2["odd_count"]) == sum(n % 2 for n in numbers),
                "BLOCKED: Phase 2 6/42 sum or odd count differs from canonical")
        overlap = int(np.minimum(draw, prior6).sum())
        if index:
            require(int(float(p2["previous_draw_overlap"])) == overlap, "BLOCKED: Phase 2 6/42 overlap differs")
        else:
            require(not p2["previous_draw_overlap"], "BLOCKED: first Phase 2 6/42 overlap is not empty")
        prior6 = draw
    return phase3, {
        "3d_rows": rows3, "6_42_rows": rows6, "3d_draws": draws3, "6_42_draws": draws6,
        "input_hashes": {name: sha256_file(root / name) for name in CANONICAL_INPUTS.values()},
        "phase3_verdict": phase3["verdict"],
        "phase3_notebook_code_cells": len(code_cells),
    }


def feature_names3() -> list[str]:
    names: list[str] = []
    for digit in range(10):
        names += [f"digit_{digit}_count_prev_{w}" for w in WINDOWS]
        names += [
            f"digit_{digit}_expanding_count",
            f"digit_{digit}_freq_expanding",
            f"digit_{digit}_gap_since_seen",
            f"digit_{digit}_never_seen",
            f"digit_{digit}_count_prev_draw",
            f"digit_{digit}_freq_deviation_prev_100",
        ]
    names += ["previous_draw_digit_sum"]
    names += [f"digit_sum_mean_prev_{w}" for w in WINDOWS]
    names += [f"digit_sum_variance_prev_{w}" for w in WINDOWS]
    names += ["prev_pattern_all_distinct", "prev_pattern_one_pair", "prev_pattern_triple"]
    names += [f"one_pair_rate_prev_{w}" for w in (30, 100)]
    names += [f"triple_rate_prev_{w}" for w in (30, 100)]
    names += ["previous_multiset_overlap"]
    names += [f"multiset_overlap_mean_prev_{w}" for w in (30, 100)]
    return names


def feature_names642() -> list[str]:
    names: list[str] = []
    for number in range(1, 43):
        entity = f"num_{number:02d}"
        names += [f"{entity}_count_prev_{w}" for w in WINDOWS]
        names += [
            f"{entity}_expanding_count",
            f"{entity}_freq_expanding",
            f"{entity}_gap_since_seen",
            f"{entity}_never_seen",
            f"{entity}_seen_prev_draw",
            f"{entity}_freq_deviation_prev_100",
        ]
    names += ["previous_draw_sum"]
    names += [f"draw_sum_mean_prev_{w}" for w in WINDOWS]
    names += [f"draw_sum_variance_prev_{w}" for w in WINDOWS]
    names += ["previous_draw_odd_count"]
    names += [f"odd_count_mean_prev_{w}" for w in (30, 100)]
    names += ["previous_set_overlap"]
    names += [f"set_overlap_mean_prev_{w}" for w in (30, 100)]
    return names


def pattern_ids(draws: np.ndarray) -> np.ndarray:
    distinct = np.count_nonzero(draws, axis=1)
    maximum = draws.max(axis=1)
    return np.where(distinct == 3, 0, np.where(maximum == 3, 2, 1)).astype(np.int8)


def feature_row3(draws: np.ndarray, t: int) -> list[float | int | None]:
    hist = draws[:t]
    sums = hist @ np.arange(10)
    patterns = pattern_ids(hist)
    overlaps = np.minimum(hist[1:], hist[:-1]).sum(axis=1)
    prior_overlap = int(overlaps[-1])
    out: list[float | int | None] = []
    last_draw = hist[-1]
    for digit in range(10):
        for w in WINDOWS:
            out.append(int(hist[-w:, digit].sum()))
        count = int(hist[:, digit].sum())
        out += [count, count / (3 * t)]
        seen = np.flatnonzero(hist[:, digit])
        out += [None if not len(seen) else t - 1 - int(seen[-1]), int(not len(seen))]
        out += [int(last_draw[digit]), int(hist[-100:, digit].sum()) / 300 - 0.1]
    out.append(int(sums[-1]))
    for w in WINDOWS:
        out.append(float(sums[-w:].mean()))
    for w in WINDOWS:
        out.append(float(sums[-w:].var(ddof=0)))
    prev_pattern = int(patterns[-1])
    out += [int(prev_pattern == i) for i in range(3)]
    for category in (1, 2):
        out += [float(np.mean(patterns[-w:] == category)) for w in (30, 100)]
    out.append(prior_overlap)
    for w in (30, 100):
        out.append(float(overlaps[-w:].mean()))
    return out


def feature_row642(draws: np.ndarray, t: int) -> list[float | int | None]:
    hist = draws[:t]
    sums = hist @ np.arange(1, 43)
    odd = (hist @ (np.arange(1, 43) % 2)).astype(np.int16)
    overlaps = np.minimum(hist[1:], hist[:-1]).sum(axis=1)
    out: list[float | int | None] = []
    last_draw = hist[-1]
    for entity in range(42):
        for w in WINDOWS:
            out.append(int(hist[-w:, entity].sum()))
        count = int(hist[:, entity].sum())
        out += [count, count / t]
        seen = np.flatnonzero(hist[:, entity])
        out += [None if not len(seen) else t - 1 - int(seen[-1]), int(not len(seen))]
        out += [int(last_draw[entity]), int(hist[-100:, entity].sum()) / 100 - 6 / 42]
    out.append(int(sums[-1]))
    for w in WINDOWS:
        out.append(float(sums[-w:].mean()))
    for w in WINDOWS:
        out.append(float(sums[-w:].var(ddof=0)))
    out.append(int(odd[-1]))
    for w in (30, 100):
        out.append(float(odd[-w:].mean()))
    out.append(int(overlaps[-1]))
    for w in (30, 100):
        out.append(float(overlaps[-w:].mean()))
    return out


def csv_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_game(
    game: str,
    rows: list[dict[str, str]],
    draws: np.ndarray,
    feature_names: list[str],
) -> tuple[bytes, bytes, dict[str, object], list[list[object]], list[list[object]]]:
    require(len(draws) == EXPECTED_ROWS[game], f"BLOCKED: unexpected {game} draw count")
    feat_header = ["draw_date", "source_row", *feature_names]
    if game == "3d_lotto":
        target_names = [f"target_digit_{d}" for d in range(10)]
        target_values = draws
    else:
        target_names = [f"target_{n:02d}" for n in range(1, 43)]
        target_values = draws
    target_header = ["draw_date", "source_row", *target_names]

    feature_rows: list[list[object]] = []
    target_rows: list[list[object]] = []
    if game == "3d_lotto":
        for t in range(MIN_HISTORY, len(rows)):
            feature_rows.append([rows[t]["draw_date"], rows[t]["source_row"], *feature_row3(draws, t)])
    else:
        for t in range(MIN_HISTORY, len(rows)):
            feature_rows.append([rows[t]["draw_date"], rows[t]["source_row"], *feature_row642(draws, t)])
    for t in range(MIN_HISTORY, len(rows)):
        target_rows.append([rows[t]["draw_date"], rows[t]["source_row"], *target_values[t].tolist()])

    require(len(feature_rows) == len(target_rows) == len(rows) - MIN_HISTORY, f"FAILED: {game} row count mismatch")
    require(
        [(r[0], r[1]) for r in feature_rows] == [(r[0], r[1]) for r in target_rows],
        f"FAILED: {game} feature/target stable-key alignment",
    )
    require(not set(feat_header) & set(target_header[2:]), f"FAILED: {game} target-like feature column detected")
    gap_indices = [i for i, name in enumerate(feat_header) if name.endswith("_gap_since_seen")]
    never_indices = [i for i, name in enumerate(feat_header) if name.endswith("_never_seen")]
    for row in feature_rows:
        for gap_i, never_i in zip(gap_indices, never_indices):
            gap, never_seen = row[gap_i], int(row[never_i])
            require((gap is None) == bool(never_seen), f"FAILED: {game} never-seen gap encoding")
            if gap is not None:
                require(int(gap) >= 0, f"FAILED: {game} negative gap")
    if game == "3d_lotto":
        targets = np.asarray([row[2:] for row in target_rows], dtype=np.int64)
        require(targets.shape[1] == 10 and np.all((targets >= 0) & (targets <= 3)), "FAILED: 3D target domain")
        require(np.all(targets.sum(axis=1) == 3), "FAILED: 3D target multiplicity")
    else:
        targets = np.asarray([row[2:] for row in target_rows], dtype=np.int64)
        require(targets.shape[1] == 42 and np.all((targets == 0) | (targets == 1)), "FAILED: 6/42 target domain")
        require(np.all(targets.sum(axis=1) == 6), "FAILED: 6/42 target cardinality")

    details = {
        "feature_count": len(feature_names),
        "feature_columns": feature_names,
        "target_count": len(target_names),
        "target_columns": target_names,
        "input_rows": len(rows),
        "rows_excluded_insufficient_history": MIN_HISTORY,
        "eligible_rows": len(feature_rows),
        "first_eligible_date": feature_rows[0][0],
        "last_eligible_date": feature_rows[-1][0],
        "gap_null_cells": sum(row[i] is None for row in feature_rows for i in gap_indices),
        "never_seen_cells": sum(int(row[i]) for row in feature_rows for i in never_indices),
    }
    return (
        csv_bytes(feat_header, feature_rows),
        csv_bytes(target_header, target_rows),
        details,
        feature_rows,
        target_rows,
    )


def partition(n: int) -> dict[str, tuple[int, int]]:
    train_end = math.floor(0.60 * n)
    validation_end = train_end + math.floor(0.20 * n)
    return {"train": (0, train_end), "validation": (train_end, validation_end), "test": (validation_end, n)}


def split_entry(rows: list[list[object]], bounds: tuple[int, int]) -> dict[str, object]:
    start, end = bounds
    selected = rows[start:end]
    return {
        "row_count": len(selected),
        "start_date": selected[0][0],
        "end_date": selected[-1][0],
        "first_record_key": {"draw_date": selected[0][0], "source_row": selected[0][1]},
        "last_record_key": {"draw_date": selected[-1][0], "source_row": selected[-1][1]},
        "row_index_start_in_eligible_matrix": start,
        "row_index_end_exclusive": end,
    }


def feature_dictionary(names3: list[str], names6: list[str]) -> dict[str, object]:
    def definition(name: str, game: str) -> dict[str, object]:
        window_match = re.search(r"_prev_(10|30|100)$", name)
        window = int(window_match.group(1)) if window_match else None
        is3 = game == "3d_lotto"
        if "_gap_since_seen" in name:
            metric, formula = "gap_since_seen", "target_index - 1 - last_prior_appearance_index; null if never seen"
        elif "_never_seen" in name:
            metric, formula = "never_seen", "1 if no appearance exists in draws strictly before the target; otherwise 0"
        elif "_freq_deviation_prev_100" in name:
            metric = "rolling_frequency_deviation"
            formula = "empirical marginal frequency in previous 100 draws minus fair marginal frequency"
        elif "_freq_expanding" in name:
            metric = "expanding_frequency"
            formula = "historical appearance count divided by prior digit slots or prior draws, excluding target"
        elif "_expanding_count" in name:
            metric, formula = "expanding_count", "appearance count across all draws strictly before target"
        elif "_count_prev_" in name:
            metric, formula = "rolling_count", "appearance multiplicity in exactly the prior W draws"
        elif "_seen_prev_draw" in name:
            metric, formula = "previous_draw_presence", "binary membership in draw t-1"
        elif "_count_prev_draw" in name:
            metric, formula = "previous_draw_multiplicity", "digit multiplicity in draw t-1"
        elif "_mean_prev_" in name:
            metric, formula = "rolling_mean", "population mean over the named completed prior draws or transitions"
        elif "_variance_prev_" in name:
            metric, formula = "rolling_population_variance", "population variance over the named completed prior draws"
        elif "_rate_prev_" in name:
            metric, formula = "rolling_pattern_rate", "fraction of the named prior draws in the pattern"
        elif name.startswith("prev_pattern_"):
            metric, formula = "previous_pattern_one_hot", "one-hot type of draw t-1, treated as an unordered multiset"
        elif "overlap" in name and name.startswith("previous_"):
            metric, formula = "previous_draw_overlap", "multiset intersection size for 3D or set intersection size for 6/42 at t-2,t-1"
        elif "overlap" in name:
            metric, formula = "rolling_overlap_mean", "mean overlap over the named latest completed transitions"
        elif name in {"previous_draw_digit_sum", "previous_draw_sum"}:
            metric, formula = "previous_draw_sum", "sum of values in draw t-1"
        elif name == "previous_draw_odd_count":
            metric, formula = "previous_draw_odd_count", "count of odd numbers in draw t-1"
        else:
            metric, formula = "unspecified_context", "See metric name; all values use draws strictly before target"
        entity = None
        match = re.match(r"(digit_\d+|num_\d+)", name)
        if match:
            entity = match.group(1)
        fair = 0.1 if is3 else 6 / 42
        return {
            "entity": entity,
            "metric": metric,
            "window_draws_or_transitions": window,
            "definition": formula,
            "fair_reference": fair if "deviation" in name else None,
            "missing_history": "only gap_since_seen may be null; paired never_seen flag is 1",
            "temporal_rule": "uses strictly prior draws; target draw and later draws are excluded",
        }

    return {
        "schema_version": 1,
        "row_key_columns": ["draw_date", "source_row"],
        "global_temporal_rule": "Every feature for target draw t uses only draws with chronological index less than t.",
        "history_policy": {
            "fixed_windows_draws": list(WINDOWS),
            "required_prior_draws": MIN_HISTORY,
            "reason": "100 prior draws provide 100 completed transitions for overlap windows",
            "excluded_early_rows_per_game": MIN_HISTORY,
            "gap_for_never_seen": "CSV empty cell / null plus never_seen=1",
        },
        "3d_lotto": {
            "draw_representation": "unordered three-digit multiset with multiplicity",
            "target_representation": "ten integer digit counts summing to 3",
            "feature_count": len(names3),
            "features": {name: definition(name, "3d_lotto") for name in names3},
        },
        "lotto_6_42": {
            "draw_representation": "unordered set of six distinct numbers",
            "target_representation": "42 binary membership values summing to 6",
            "feature_count": len(names6),
            "features": {name: definition(name, "lotto_6_42") for name in names6},
        },
    }


def audit_temporal(
    game: str,
    draws: np.ndarray,
    feature_rows: list[list[object]],
    feature_names: list[str],
) -> dict[str, object]:
    index = {name: i + 2 for i, name in enumerate(feature_names)}
    sample_t = sorted(set([MIN_HISTORY, MIN_HISTORY + 1, len(draws) // 2, len(draws) - 1]))
    checks = {
        "rolling_features_match_direct_prior_slices": True,
        "expanding_features_exclude_target": True,
        "gap_features_use_prior_appearances": True,
        "previous_draw_features_reference_t_minus_1": True,
        "no_future_draw_influences_features": True,
        "unordered_draw_permutation_invariance": True,
        "no_target_columns_in_features": True,
    }
    for t in sample_t:
        row = feature_rows[t - MIN_HISTORY]
        history = draws[:t]
        last = history[-1]
        if game == "3d_lotto":
            draw_sums = history @ np.arange(10)
            patterns = pattern_ids(history)
            transition_overlaps = np.minimum(history[1:], history[:-1]).sum(axis=1)
            require(int(row[index["previous_draw_digit_sum"]]) == int(draw_sums[-1]),
                    "FAILED: 3D previous-draw sum provenance")
            require(int(row[index["previous_multiset_overlap"]]) == int(transition_overlaps[-1]),
                    "FAILED: 3D previous overlap provenance")
            for w in WINDOWS:
                require(math.isclose(float(row[index[f"digit_sum_mean_prev_{w}"]]), float(draw_sums[-w:].mean())),
                        "FAILED: 3D rolling sum mean provenance")
                require(math.isclose(float(row[index[f"digit_sum_variance_prev_{w}"]]), float(draw_sums[-w:].var(ddof=0))),
                        "FAILED: 3D rolling sum variance provenance")
            previous_pattern = int(patterns[-1])
            for category, name in enumerate(("prev_pattern_all_distinct", "prev_pattern_one_pair", "prev_pattern_triple")):
                require(int(row[index[name]]) == int(previous_pattern == category), "FAILED: 3D previous pattern lag")
            for w in (30, 100):
                require(math.isclose(float(row[index[f"one_pair_rate_prev_{w}"]]), float(np.mean(patterns[-w:] == 1))),
                        "FAILED: 3D one-pair rolling rate")
                require(math.isclose(float(row[index[f"triple_rate_prev_{w}"]]), float(np.mean(patterns[-w:] == 2))),
                        "FAILED: 3D triple rolling rate")
                require(math.isclose(float(row[index[f"multiset_overlap_mean_prev_{w}"]]),
                                     float(transition_overlaps[-w:].mean())),
                        "FAILED: 3D rolling multiset overlap")
            for digit in range(10):
                for w in WINDOWS:
                    actual = int(row[index[f"digit_{digit}_count_prev_{w}"]])
                    require(actual == int(history[-w:, digit].sum()), f"FAILED: 3D rolling provenance {digit}/{w}")
                actual_count = int(row[index[f"digit_{digit}_expanding_count"]])
                require(actual_count == int(history[:, digit].sum()), "FAILED: 3D expanding provenance")
                require(math.isclose(float(row[index[f"digit_{digit}_freq_expanding"]]), actual_count / (3 * t)),
                        "FAILED: 3D expanding frequency denominator")
                seen = np.flatnonzero(history[:, digit])
                gap = row[index[f"digit_{digit}_gap_since_seen"]]
                never = int(row[index[f"digit_{digit}_never_seen"]])
                require((gap is None) == (not len(seen)) and never == int(not len(seen)), "FAILED: 3D gap provenance")
                if len(seen):
                    require(int(gap) == t - 1 - int(seen[-1]), "FAILED: 3D gap offset")
                require(int(row[index[f"digit_{digit}_count_prev_draw"]]) == int(last[digit]),
                        "FAILED: 3D t-1 lag")
                fair_dev = int(history[-100:, digit].sum()) / 300 - 0.1
                require(math.isclose(float(row[index[f"digit_{digit}_freq_deviation_prev_100"]]), fair_dev),
                        "FAILED: 3D rolling fair deviation")
            permuted = np.stack([
                np.bincount(np.repeat(np.arange(10), draw)[::-1], minlength=10)
                for draw in history
            ])
            require(np.array_equal(permuted, history), "FAILED: 3D positional invariance")
        else:
            draw_sums = history @ np.arange(1, 43)
            odd_counts = history @ (np.arange(1, 43) % 2)
            transition_overlaps = np.minimum(history[1:], history[:-1]).sum(axis=1)
            require(int(row[index["previous_draw_sum"]]) == int(draw_sums[-1]),
                    "FAILED: 6/42 previous-draw sum provenance")
            require(int(row[index["previous_draw_odd_count"]]) == int(odd_counts[-1]),
                    "FAILED: 6/42 previous odd-count provenance")
            require(int(row[index["previous_set_overlap"]]) == int(transition_overlaps[-1]),
                    "FAILED: 6/42 previous overlap provenance")
            for w in WINDOWS:
                require(math.isclose(float(row[index[f"draw_sum_mean_prev_{w}"]]), float(draw_sums[-w:].mean())),
                        "FAILED: 6/42 rolling sum mean provenance")
                require(math.isclose(float(row[index[f"draw_sum_variance_prev_{w}"]]), float(draw_sums[-w:].var(ddof=0))),
                        "FAILED: 6/42 rolling sum variance provenance")
            for w in (30, 100):
                require(math.isclose(float(row[index[f"odd_count_mean_prev_{w}"]]), float(odd_counts[-w:].mean())),
                        "FAILED: 6/42 rolling odd-count mean")
                require(math.isclose(float(row[index[f"set_overlap_mean_prev_{w}"]]),
                                     float(transition_overlaps[-w:].mean())),
                        "FAILED: 6/42 rolling set overlap")
            for entity in range(42):
                name = f"num_{entity + 1:02d}"
                for w in WINDOWS:
                    require(int(row[index[f"{name}_count_prev_{w}"]]) == int(history[-w:, entity].sum()),
                            "FAILED: 6/42 rolling provenance")
                count = int(history[:, entity].sum())
                require(int(row[index[f"{name}_expanding_count"]]) == count, "FAILED: 6/42 expanding provenance")
                require(math.isclose(float(row[index[f"{name}_freq_expanding"]]), count / t),
                        "FAILED: 6/42 expanding frequency")
                seen = np.flatnonzero(history[:, entity])
                gap = row[index[f"{name}_gap_since_seen"]]
                never = int(row[index[f"{name}_never_seen"]])
                require((gap is None) == (not len(seen)) and never == int(not len(seen)), "FAILED: 6/42 gap provenance")
                if len(seen):
                    require(int(gap) == t - 1 - int(seen[-1]), "FAILED: 6/42 gap offset")
                require(int(row[index[f"{name}_seen_prev_draw"]]) == int(last[entity]), "FAILED: 6/42 t-1 lag")
                fair_dev = int(history[-100:, entity].sum()) / 100 - 6 / 42
                require(math.isclose(float(row[index[f"{name}_freq_deviation_prev_100"]]), fair_dev),
                        "FAILED: 6/42 rolling fair deviation")
            permuted = np.stack([
                np.bincount((np.flatnonzero(draw) + 1)[::-1], minlength=43)[1:]
                for draw in history
            ])
            require(np.array_equal(permuted, history), "FAILED: 6/42 positional invariance")
        altered = draws.copy()
        if game == "3d_lotto":
            altered[t:] = altered[t:, ::-1]
            perturbed = feature_row3(altered, t)
        else:
            # Rebuild each future draw by complementing the selected set.
            future_sets = [43 - (np.flatnonzero(draw) + 1) for draw in draws[t:]]
            altered = draws.copy()
            for offset, numbers in enumerate(future_sets, start=t):
                altered[offset] = np.bincount(numbers, minlength=43)[1:]
            perturbed = feature_row642(altered, t)
        expected = feature_row3(draws, t) if game == "3d_lotto" else feature_row642(draws, t)
        require(perturbed == expected, f"FAILED: {game} current/future perturbation changed features")
    return {"checks": checks, "sampled_target_indices": sample_t, "status": "PASS"}


def build_core(root: Path) -> tuple[dict[str, bytes], dict[str, object]]:
    _, data = phase3_and_input_validation(root)
    rows3, rows6 = data["3d_rows"], data["6_42_rows"]
    draws3, draws6 = data["3d_draws"], data["6_42_draws"]
    names3, names6 = feature_names3(), feature_names642()
    f3, t3, d3, fr3, tr3 = build_game("3d_lotto", rows3, draws3, names3)
    f6, t6, d6, fr6, tr6 = build_game("lotto_6_42", rows6, draws6, names6)

    split_games: dict[str, object] = {}
    for game, feature_rows, details in (
        ("3d_lotto", fr3, d3),
        ("lotto_6_42", fr6, d6),
    ):
        bounds = partition(len(feature_rows))
        parts = {name: split_entry(feature_rows, span) for name, span in bounds.items()}
        require(parts["train"]["end_date"] < parts["validation"]["start_date"], f"FAILED: {game} split overlap")
        require(parts["validation"]["end_date"] < parts["test"]["start_date"], f"FAILED: {game} split overlap")
        split_games[game] = {
            "eligible_rows": len(feature_rows),
            "excluded_insufficient_history": details["rows_excluded_insufficient_history"],
            "partitions": parts,
        }
    splits = {
        "schema_version": 1,
        "ordering": "ascending draw_date; source_row is stable tie-breaker",
        "shuffle": False,
        "fractions": {"train": 0.60, "validation": 0.20, "test": 0.20},
        "rounding": "floor train and validation counts; remainder assigned to test",
        "test_partition_locked": True,
        "row_key_columns": ["draw_date", "source_row"],
        "games": split_games,
    }
    dictionary = feature_dictionary(names3, names6)
    audit3 = audit_temporal("3d_lotto", draws3, fr3, names3)
    audit6 = audit_temporal("lotto_6_42", draws6, fr6, names6)
    payloads = {
        "data/features/3d_features.csv": f3,
        "data/features/3d_targets.csv": t3,
        "data/features/642_features.csv": f6,
        "data/features/642_targets.csv": t6,
        "data/features/chronological_splits.json": json_bytes(splits),
        "data/features/feature_dictionary.json": json_bytes(dictionary),
    }
    hashes = {name: sha256_bytes(value) for name, value in payloads.items()}
    details = {
        "phase3_verdict": data["phase3_verdict"],
        "phase3_notebook_code_cells": data["phase3_notebook_code_cells"],
        "canonical_input_hashes": data["input_hashes"],
        "games": {"3d_lotto": d3, "lotto_6_42": d6},
        "splits": splits,
        "leakage_audit": {"3d_lotto": audit3, "lotto_6_42": audit6},
        "artifact_hashes": hashes,
        "feature_counts": {"3d_lotto": len(names3), "lotto_6_42": len(names6)},
    }
    return payloads, details


def notebook_cells() -> list[dict[str, object]]:
    import nbformat as nbf

    sections = [
        ("1. Phase 4 Objective and Scope", "Question: What does Phase 4 deliver? Method: construct historical features, unordered targets, fixed chronological splits, and audits only. Interpretation: these are inputs for a later backtest, not predictions. Limitation: no model is trained and no test performance is measured.", None),
        ("2. Canonical Inputs and Provenance", "Question: Which canonical data and prior-phase evidence are used? Method: verify Phase 1 through Phase 3 artifacts and compare source hashes. Interpretation: each row is keyed by draw_date and source_row. Limitation: hashes establish byte identity, not upstream correctness beyond the recorded validation.", "provenance"),
        ("3. Temporal Leakage Rule", "Question: Can row t see its own or later draw? Method: every feature uses indices less than t, followed by sampled future-perturbation checks. Interpretation: target t is excluded from rolling, expanding, lag, gap, and overlap calculations. Limitation: the audit samples representative indices and also checks the shared construction rules.", "leakage"),
        ("4. Target Representation: 3D Lotto", "Question: How are repeated digits retained? Method: encode each draw as ten digit counts from an unordered multiset. Interpretation: each row contains values 0 through 3 summing to 3. Limitation: the output intentionally discards published digit position.", "targets"),
        ("5. Target Representation: Lotto 6/42", "Question: How is each draw represented? Method: parse the canonical sorted combination into a set and emit binary membership for 1 through 42. Interpretation: each row has six positive labels. Limitation: published draw order is not retained in the target matrix.", "targets"),
        ("6. Historical Feature Definitions", "Question: What features are available to the later backtest? Method: use the machine-readable feature dictionary and the fixed 10, 30, and 100 draw windows. Interpretation: feature names identify entity, metric, and history window. Limitation: no extra windows or data sources are introduced.", "dictionary"),
        ("7. Rolling and Expanding Feature Construction", "Question: How are historical frequencies calculated? Method: count exact prior windows and cumulative prior history; digit frequencies divide by prior digit slots, Lotto frequencies by prior draws. Interpretation: deviations use fair marginal references 0.1 and 6/42. Limitation: these are descriptive rates and imply no predictive value.", "rolling"),
        ("8. Gap and Recency Features", "Question: How is recency defined when an entity has never appeared? Method: count completed draws since the last prior appearance, and pair null gap with never_seen=1 when absent. Interpretation: a gap of zero means appearance in t-1. Limitation: early rows are excluded until the longest required history is available.", "gaps"),
        ("9. Draw-Level Context Features", "Question: Which properties of prior draws are summarized? Method: summarize sums, population variances, patterns, odd counts, and completed transition overlaps. Interpretation: all summaries end at t-1. Limitation: they are descriptive context only.", "context"),
        ("10. Missing-History Treatment", "Question: How are incomplete histories handled? Method: exclude the first 101 target rows to provide 100 prior draws and 100 prior transitions. Interpretation: only never-seen gap cells can remain null thereafter. Limitation: this reduces the available sample.", "missing"),
        ("11. Feature-Matrix Verification", "Question: Do features and targets align by draw? Method: compare stable keys and check target invariants and missingness rules. Interpretation: row order is identical within each game. Limitation: keys establish row identity, not causal meaning.", "alignment"),
        ("12. Chronological Train Validation Test Split", "Question: How are partitions frozen? Method: floor 60 percent for train, floor 20 percent for validation, and assign the remainder to the newest test partition. Interpretation: boundaries are non-overlapping and persisted. Limitation: Phase 4 does not inspect test-label performance.", "splits"),
        ("13. Leakage Audit", "Question: Have temporal and positional leakage checks passed? Method: direct prior-slice checks, lag/gap verification, permutation invariance, and future perturbation. Interpretation: all recorded checks must pass. Limitation: this validates construction, not future model design.", "leakage"),
        ("14. Feature Distribution Diagnostics", "Question: What do selected feature histories look like? Method: chart rolling frequency deviations, gap distributions, and missingness. Interpretation: charts describe feature variation only. Limitation: no chart is evidence of predictive usefulness.", "diagnostics"),
        ("15. Phase 4 Validation Summary", "Question: Did the required engineering checks pass? Method: read the machine-readable validation summary and verify saved artifact hashes. Interpretation: only a fully passing status supports readiness. Limitation: later model evaluation remains out of scope.", "validation"),
        ("16. Phase 5 Readiness", "Question: What can Phase 5 safely consume? Method: use exact persisted keys, matrices, feature definitions, and split boundaries. Interpretation: a future baseline comparison can begin from the locked chronology. Limitation: no Phase 5 model or performance claim is created here.", "readiness"),
        ("17. Limitations", "Question: What should readers avoid concluding? Method: interpret all outputs as historical feature engineering only. Interpretation: no numbers are recommended and no hot, cold, due, or lucky claim is made. Limitation: lottery outcomes remain uncertain and feature variation alone is not evidence of an edge.", None),
    ]
    code = {
        "provenance": """print('Repository:', ROOT)\nprint('Source input hashes:')\nfor name, digest in sorted(validation['canonical_input_hashes'].items()):\n    print(name, digest)\nprint('Phase 3 verdict:', validation['preflight']['phase3_verdict'])""",
        "leakage": """print(pd.DataFrame([{'game': game, 'status': item['status'], 'checks': len(item['checks']), 'sampled target indices': item['sampled_target_indices']} for game, item in validation['leakage_audit'].items()]))""",
        "targets": """target_checks = []\nfor game, name, total in [('3d_lotto', '3d_targets.csv', 3), ('lotto_6_42', '642_targets.csv', 6)]:\n    frame = pd.read_csv(ROOT / 'data/features' / name)\n    values = frame.iloc[:, 2:].to_numpy()\n    target_checks.append({'game': game, 'rows': len(frame), 'target_columns': values.shape[1], 'min': int(values.min()), 'max': int(values.max()), 'row_sum_min': int(values.sum(axis=1).min()), 'row_sum_max': int(values.sum(axis=1).max()), 'required_row_sum': total})\nprint(pd.DataFrame(target_checks))""",
        "dictionary": """print(pd.DataFrame([{'game': game, 'feature_count': spec['feature_count'], 'feature_groups': len(spec['features'])} for game, spec in dictionary.items() if isinstance(spec, dict) and 'features' in spec]))""",
        "rolling": """sample3 = features3[['draw_date', 'digit_7_freq_deviation_prev_100']].copy()\nsample6 = features6[['draw_date', 'num_21_freq_deviation_prev_100']].copy()\nsample3['draw_date'] = pd.to_datetime(sample3['draw_date'])\nsample6['draw_date'] = pd.to_datetime(sample6['draw_date'])\nfig, ax = plt.subplots(figsize=(10, 3.5))\nax.plot(sample3['draw_date'], sample3['digit_7_freq_deviation_prev_100'], linewidth=0.8, label='3D digit 7')\nax.plot(sample6['draw_date'], sample6['num_21_freq_deviation_prev_100'], linewidth=0.8, label='6/42 number 21')\nax.axhline(0, color='black', linewidth=0.8)\nax.legend()\nax.set(title='Selected prior-100-draw frequency deviations', xlabel='Target draw date', ylabel='Observed frequency minus fair marginal frequency')\nfig.tight_layout()""",
        "gaps": """fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))\nfor ax, frame, column, title in [(axes[0], features3, 'digit_7_gap_since_seen', '3D digit 7'), (axes[1], features6, 'num_21_gap_since_seen', '6/42 number 21')]:\n    values = frame[column].dropna()\n    ax.hist(values, bins=20, color='#466a8a', edgecolor='white')\n    ax.set(title=title, xlabel='Draws since prior appearance', ylabel='Feature rows')\nfig.suptitle('Selected prior-history gap distributions')\nfig.tight_layout()""",
        "context": """context = [name for name in features3.columns if name.startswith(('previous_', 'digit_sum_', 'one_pair_', 'triple_', 'multiset_'))]\ncontext6 = [name for name in features6.columns if name.startswith(('previous_', 'draw_sum_', 'odd_count_', 'set_overlap_'))]\nprint('3D context columns:', len(context))\nprint('6/42 context columns:', len(context6))\nprint('Variance convention: population variance (ddof=0). Overlap windows count completed transitions.')""",
        "missing": """missing = []\nfor game, frame in [('3d_lotto', features3), ('lotto_6_42', features6)]:\n    gaps = [name for name in frame.columns if name.endswith('_gap_since_seen')]\n    missing.append({'game': game, 'feature_rows': len(frame), 'gap_columns': len(gaps), 'null_gap_cells': int(frame[gaps].isna().sum().sum()), 'never_seen_flags': int(frame[[n for n in frame if n.endswith('_never_seen')]].sum().sum())})\nprint(pd.DataFrame(missing))""",
        "alignment": """alignment = []\nfor game, feature, target in [('3d_lotto', features3, targets3), ('lotto_6_42', features6, targets6)]:\n    alignment.append({'game': game, 'same_rows': len(feature) == len(target), 'same_keys': feature[['draw_date', 'source_row']].equals(target[['draw_date', 'source_row']]), 'feature_columns': feature.shape[1]-2, 'target_columns': target.shape[1]-2})\nprint(pd.DataFrame(alignment))""",
        "splits": """fig, axes = plt.subplots(2, 1, figsize=(10, 3.6), sharex=True)\nfor ax, game in zip(axes, ['3d_lotto', 'lotto_6_42']):\n    parts = split_manifest['games'][game]['partitions']\n    for y, (name, color) in enumerate([('train', '#4c78a8'), ('validation', '#f2a541'), ('test', '#c44e52')]):\n        span = parts[name]\n        ax.plot([pd.Timestamp(span['start_date']), pd.Timestamp(span['end_date'])], [0, 0], linewidth=9, solid_capstyle='butt', color=color, label=f\"{name}: {span['row_count']}\")\n    ax.set_yticks([])\n    ax.set_ylabel(game)\n    ax.legend(ncol=3, loc='upper center', fontsize=8)\naxes[-1].set_xlabel('Draw date; partitions remain chronological')\nfig.suptitle('Locked chronological split timelines')\nfig.tight_layout()""",
        "validation": """print('Verdict:', validation['verdict'])\nprint('Notebook execution:', validation['notebook_execution'])\nprint(pd.DataFrame([{'artifact': name, 'sha256': digest} for name, digest in validation['reproducibility']['artifact_hashes'].items()]))""",
        "readiness": """print(pd.DataFrame([{'game': game, 'features': details['feature_count'], 'targets': details['target_count'], 'eligible_rows': details['eligible_rows'], 'excluded_early_rows': details['rows_excluded_insufficient_history']} for game, details in validation['games'].items()]))\nprint('Test partition locked:', split_manifest['test_partition_locked'])\nprint('Model training:', 'not performed')\nprint('Test performance:', 'not calculated')""",
        "diagnostics": """fig, ax = plt.subplots(figsize=(8, 3.2))\nax.bar(['3D gap nulls', '6/42 gap nulls'], [validation['games']['3d_lotto']['gap_null_cells'], validation['games']['lotto_6_42']['gap_null_cells']], color=['#466a8a', '#8a6da8'])\nax.set(title='Never-seen gap values after required-history filtering', ylabel='Nullable gap cells', xlabel='Game')\nfig.tight_layout()""",
    }
    cells: list[dict[str, object]] = []
    setup = """from pathlib import Path\nimport json, sys\nimport pandas as pd\nimport matplotlib.pyplot as plt\nsys.dont_write_bytecode = True\nROOT = next((candidate for candidate in [Path.cwd().resolve(), *Path.cwd().resolve().parents] if (candidate / 'scripts/phase4_feature_engineering.py').is_file()), None)\nassert ROOT is not None, 'Open this notebook from within the magic_Lotto repository.'\nsys.path.insert(0, str(ROOT))\nfrom scripts.phase4_feature_engineering import build_core\npayloads, validation = build_core(ROOT)\nfor relative, content in payloads.items():\n    assert (ROOT / relative).read_bytes() == content, f'Saved artifact differs: {relative}'\nfeatures3 = pd.read_csv(ROOT / 'data/features/3d_features.csv')\ntargets3 = pd.read_csv(ROOT / 'data/features/3d_targets.csv')\nfeatures6 = pd.read_csv(ROOT / 'data/features/642_features.csv')\ntargets6 = pd.read_csv(ROOT / 'data/features/642_targets.csv')\ndictionary = json.loads((ROOT / 'data/features/feature_dictionary.json').read_text(encoding='utf-8'))\nsplit_manifest = json.loads((ROOT / 'data/features/chronological_splits.json').read_text(encoding='utf-8'))\nvalidation = json.loads((ROOT / 'reports/phase4_validation.json').read_text(encoding='utf-8'))\nprint('Saved core artifacts match a fresh deterministic build.')"""
    cells.append(nbf.v4.new_code_cell(setup))
    for heading, text, code_key in sections:
        cells.append(nbf.v4.new_markdown_cell(f"## {heading}\n\n{text}"))
        if code_key:
            cells.append(nbf.v4.new_code_cell(code[code_key]))
    return cells


def notebook_execution_status(root: Path) -> dict[str, object]:
    path = root / "notebooks/lotto_phase4_feature_engineering.ipynb"
    if not path.is_file():
        return {"status": "PENDING", "code_cells": 0}
    try:
        import nbformat

        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        executed = bool(code_cells) and all(cell.execution_count is not None for cell in code_cells)
        errors = sum(
            output.output_type == "error"
            for cell in code_cells
            for output in cell.get("outputs", [])
        )
        return {
            "status": "PASS" if executed and errors == 0 else "PENDING",
            "code_cells": len(code_cells),
            "executed_code_cells": sum(cell.execution_count is not None for cell in code_cells),
            "error_outputs": errors,
            "nbformat_validation": "PASS",
        }
    except Exception as error:
        return {"status": "FAILED", "detail": f"{type(error).__name__}: {error}"}


def make_notebook(root: Path) -> bytes:
    import nbformat as nbf

    notebook = nbf.v4.new_notebook(
        cells=notebook_cells(),
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"},
        },
    )
    nbf.validate(notebook)
    return nbf.writes(notebook, version=4).encode("utf-8")


def validation_report(
    root: Path,
    context: dict[str, object],
    details: dict[str, object],
    deterministic: bool,
) -> tuple[bytes, bytes]:
    execution = notebook_execution_status(root)
    status = "PHASE4_PASS_READY_FOR_ML_BASELINE" if deterministic and execution["status"] == "PASS" else "PHASE4_BLOCKED"
    validation = {
        "schema_version": 1,
        "verdict": status,
        "repository": {k: context[k] for k in ("repository", "branch", "head", "configured_remotes")},
        "preflight": {
            "tracked_worktree_clean": context["tracked_worktree_clean"],
            "index_clean": context["index_clean"],
            "keys_env_ignored": True,
            "keys_env_tracked": False,
            "keys_env_contents_read": False,
            "phase3_verdict": details["phase3_verdict"],
            "phase3_notebook_code_cells": details["phase3_notebook_code_cells"],
        },
        "canonical_input_paths": {key: str((root / name).resolve()) for key, name in CANONICAL_INPUTS.items()},
        "canonical_input_hashes": details["canonical_input_hashes"],
        "games": details["games"],
        "split_manifest_path": str((root / "data/features/chronological_splits.json").resolve()),
        "feature_dictionary_path": str((root / "data/features/feature_dictionary.json").resolve()),
        "leakage_audit": details["leakage_audit"],
        "reproducibility": {
            "two_in_memory_builds_match": deterministic,
            "artifact_hashes": details["artifact_hashes"],
            "fixed_windows_draws": list(WINDOWS),
            "random_seed": None,
            "note": "No randomness is used in Phase 4.",
        },
        "notebook_execution": execution,
        "validation_checks": {
            "canonical_phase1_to_phase3_inputs": "PASS",
            "phase3_verdict": "PASS",
            "target_invariants_3d": "PASS",
            "target_invariants_6_42": "PASS",
            "feature_target_key_alignment": "PASS",
            "temporal_leakage_audits": "PASS",
            "chronological_splits": "PASS",
            "deterministic_two_build_hashes": "PASS" if deterministic else "FAIL",
            "notebook_execution_and_nbformat": execution["status"],
            "jev_or_typesafe_called": False,
            "model_training_performed": False,
            "test_performance_calculated": False,
        },
        "git_actions": {"stage": False, "commit": False, "push": False, "merge": False},
    }
    md = [
        "# Phase 4 Feature Engineering and Experimental Design",
        "",
        f"- Verdict: {status}",
        f"- Branch and HEAD: {context['branch']} / {context['head']}",
        "- Phase 3 prerequisite: PHASE3_PASS_RANDOM_COMPATIBLE",
        "- Canonical inputs are unchanged; SHA-256 values are recorded in phase4_validation.json.",
        "- Leakage rule: every feature for target t uses only earlier draws.",
        "- Early history: first 101 rows per game excluded to provide 100 prior draws and 100 completed transitions.",
        "- Chronology: floor 60% train, floor 20% validation, remainder test; test partition locked.",
        "- No model training, hyperparameter search, test-performance calculation, number recommendations, JEV, or TypeSafe.",
        "",
        "## Dataset summary",
        "",
        "| Game | Features | Targets | Input draws | Excluded | Eligible | Gap null cells |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for game, entry in details["games"].items():
        md.append(
            f"| {game} | {entry['feature_count']} | {entry['target_count']} | {entry['input_rows']} | "
            f"{entry['rows_excluded_insufficient_history']} | {entry['eligible_rows']} | {entry['gap_null_cells']} |"
        )
    md += ["", "## Chronological partitions", ""]
    for game, spec in details["splits"]["games"].items():
        md += [f"### {game}", "", "| Partition | Rows | Start | End |", "|---|---:|---|---|"]
        for part, p in spec["partitions"].items():
            md.append(f"| {part} | {p['row_count']} | {p['start_date']} | {p['end_date']} |")
        md.append("")
    md += [
        "## Validation",
        "",
        "- Target domains and row sums: PASS.",
        "- Feature and target stable keys: PASS.",
        "- Rolling, expanding, lag, gap, overlap, fair-deviation, permutation, and future-perturbation audits: PASS.",
        "- Two in-memory builds produced identical hashes: " + ("PASS." if deterministic else "FAIL."),
        "- Phase 4 notebook execution and nbformat: " + str(execution["status"]) + ".",
        "- Machine-readable evidence: data/features/chronological_splits.json, data/features/feature_dictionary.json, reports/phase4_validation.json.",
        "",
        "## Interpretation limits",
        "",
        "These matrices are descriptive historical inputs for a later chronological backtest. Feature variation does not establish predictive value. Phase 4 did not train models, select features using test labels, calculate test performance, or recommend numbers.",
        "",
    ]
    return json_bytes(validation), ("\n".join(md)).encode("utf-8")


def main() -> int:
    root = ROOT.resolve()
    context = preflight(root)
    payloads1, details1 = build_core(root)
    payloads2, details2 = build_core(root)
    hashes1 = {name: sha256_bytes(value) for name, value in payloads1.items()}
    hashes2 = {name: sha256_bytes(value) for name, value in payloads2.items()}
    require(hashes1 == hashes2, "FAILED: two deterministic Phase 4 builds differ")
    require(details1["artifact_hashes"] == details2["artifact_hashes"], "FAILED: artifact hash records differ")
    (root / "data/features").mkdir(parents=True, exist_ok=True)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    for name, content in payloads1.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    notebook_path = root / "notebooks/lotto_phase4_feature_engineering.ipynb"
    if not notebook_path.exists():
        notebook_path.parent.mkdir(parents=True, exist_ok=True)
        notebook_path.write_bytes(make_notebook(root))
    validation, report = validation_report(root, context, details1, True)
    (root / "reports/phase4_validation.json").write_bytes(validation)
    (root / "reports/phase4_feature_engineering.md").write_bytes(report)
    print(json.dumps({
        "verdict": json.loads(validation)["verdict"],
        "branch": context["branch"],
        "head": context["head"],
        "deterministic_build_hashes": hashes1,
        "notebook_execution": json.loads(validation)["notebook_execution"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Phase4Error as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
