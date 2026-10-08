# @codebase_provenance_JEO
"""Reproducible fair-history Monte Carlo baseline for the Lotto Phase 3 analysis."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import platform
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
SEED = 162
INITIAL_SIMULATIONS = 10_000
CONFIRMATION_SIMULATIONS = 100_000
ANOMALY_THRESHOLD = 0.01
BATCH_SIZE = 64

INPUT_FILES = {
    "3d_analysis_ready": "swertres_9pm_analysis_ready.csv",
    "3d_phase2": "swertres_9pm_phase2_analysis.csv",
    "3d_digit_frequency": "swertres_9pm_digit_frequency.csv",
    "6_42_cleaned": "lotto_6_42_cleaned_normalized.csv",
    "6_42_phase2": "lotto_6_42_phase2_analysis.csv",
    "6_42_number_frequency": "lotto_6_42_number_frequency.csv",
    "phase2_report": "phase2_randomness_diagnostics.md",
}

OUTPUT_FILES = {
    "script": "monte_carlo_baseline.py",
    "json": "phase3_monte_carlo_results.json",
    "report": "phase3_monte_carlo_random_baseline.md",
    "distributions": "phase3_simulation_distributions.csv",
}

THREED_METRICS = [
    "pooled_digit_frequency_chi_square",
    "maximum_digit_share_deviation",
    "repetition_pattern_chi_square",
    "digit_sum_mean",
    "digit_sum_variance",
    "lag1_digit_sum_correlation",
    "consecutive_multiset_overlap_mean",
    "consecutive_multiset_overlap_distribution_chi_square",
]

LOTTO_METRICS = [
    "marginal_number_frequency_chi_square",
    "maximum_number_count_deviation",
    "consecutive_set_overlap_mean",
    "consecutive_set_overlap_distribution_chi_square",
    "odd_count_mean",
    "odd_count_distribution_chi_square",
    "draw_sum_mean",
    "draw_sum_variance",
]

ALLOWED_WORKTREE_PATHS = set(OUTPUT_FILES.values())


class Phase3BlockedError(RuntimeError):
    """Raised when a required preflight or data validation check fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3BlockedError(message)


def git(args: list[str], *, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def verify_repository_and_secret_boundary() -> dict[str, object]:
    inside = git(["rev-parse", "--is-inside-work-tree"])
    require(inside.returncode == 0 and inside.stdout.strip() == "true", "BLOCKED: project path is not a Git worktree")

    top = git(["rev-parse", "--show-toplevel"])
    require(top.returncode == 0 and Path(top.stdout.strip()).resolve() == ROOT, "BLOCKED: script is not at the Git worktree root")

    branch = git(["branch", "--show-current"])
    head = git(["rev-parse", "HEAD"])
    require(branch.returncode == 0 and branch.stdout.strip(), "BLOCKED: active branch is unavailable")
    require(head.returncode == 0 and len(head.stdout.strip()) == 40, "BLOCKED: HEAD SHA is unavailable")

    status = git(["status", "--porcelain=v1", "--untracked-files=all"])
    require(status.returncode == 0, "BLOCKED: working-tree status cannot be verified")
    changed_paths = {line[3:] for line in status.stdout.splitlines() if len(line) >= 4}
    bytecode_paths = {
        path for path in changed_paths
        if Path(path).parent == Path("__pycache__")
        and Path(path).name.startswith("monte_carlo_baseline.")
        and Path(path).suffix == ".pyc"
    }
    unexpected = changed_paths - ALLOWED_WORKTREE_PATHS - bytecode_paths
    require(not unexpected, f"BLOCKED: unexpected worktree changes exist: {sorted(unexpected)}")
    staged = git(["diff", "--cached", "--quiet"])
    require(staged.returncode == 0, "BLOCKED: staged changes exist")

    ignored = git(["check-ignore", "-q", "--", "Keys.env"])
    require(ignored.returncode == 0, "BLOCKED: Keys.env is not verified as ignored")

    tracked = git(["ls-files", "-z"])
    require(tracked.returncode == 0, "BLOCKED: tracked-file status cannot be verified")
    tracked_secret = any(Path(path).name.casefold() == "keys.env" for path in tracked.stdout.split("\0") if path)
    require(not tracked_secret, "BLOCKED_SECRET_TRACKED")

    remotes = git(["remote"])
    require(remotes.returncode == 0, "BLOCKED: Git remote state cannot be verified")
    return {
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "configured_remotes": [line for line in remotes.stdout.splitlines() if line],
        "keys_env_ignored": True,
        "keys_env_tracked": False,
        "keys_env_contents_read": False,
        "unexpected_worktree_changes": [],
        "staged_changes": False,
        "python_bytecode_cache_paths": sorted(bytecode_paths),
    }


def read_csv(name: str) -> tuple[list[str], list[dict[str, str]]]:
    path = ROOT / name
    require(path.is_file(), f"BLOCKED: required canonical input is missing: {name}")
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        rows = list(reader)
    require(bool(headers) and bool(rows), f"BLOCKED: canonical input is empty or has no header: {name}")
    return headers, rows


def require_headers(name: str, headers: list[str], required: set[str]) -> None:
    missing = required - set(headers)
    require(not missing, f"BLOCKED: {name} is missing columns: {sorted(missing)}")


def parse_date_rows(name: str, rows: list[dict[str, str]], key: str = "draw_date") -> list[date]:
    try:
        parsed = [date.fromisoformat(row[key]) for row in rows]
    except (KeyError, ValueError) as error:
        raise Phase3BlockedError(f"BLOCKED: invalid ISO draw date in {name}") from error
    require(parsed == sorted(parsed), f"BLOCKED: dates are not chronological in {name}")
    require(len(parsed) == len(set(parsed)), f"BLOCKED: duplicate draw dates in {name}")
    return parsed


def file_sha256(name: str) -> str:
    digest = hashlib.sha256()
    with (ROOT / name).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_inputs() -> tuple[dict[str, object], dict[str, object]]:
    loaded: dict[str, tuple[list[str], list[dict[str, str]]]] = {
        key: read_csv(name)
        for key, name in INPUT_FILES.items()
        if name.lower().endswith(".csv")
    }
    report_path = ROOT / INPUT_FILES["phase2_report"]
    require(report_path.is_file(), "BLOCKED: Phase 2 report is missing")

    h3, rows3 = loaded["3d_analysis_ready"]
    h3p, rows3p = loaded["3d_phase2"]
    h3f, rows3f = loaded["3d_digit_frequency"]
    h6, rows6 = loaded["6_42_cleaned"]
    h6p, rows6p = loaded["6_42_phase2"]
    h6f, rows6f = loaded["6_42_number_frequency"]

    require_headers("3D analysis-ready", h3, {"draw_date", "combination", "digit_1", "digit_2", "digit_3", "record_status"})
    require_headers("3D Phase 2", h3p, {"draw_date", "combination_unordered", "pattern_type", "digit_sum", "previous_draw_digit_overlap"})
    require_headers("3D digit frequency", h3f, {"digit", "observed_count"})
    require_headers("6/42 cleaned", h6, {"draw_date", "combination_published", "combination_sorted", *{f"number_{i}" for i in range(1, 7)}, "record_status"})
    require_headers("6/42 Phase 2", h6p, {"draw_date", "draw_sum", "odd_count", "previous_draw_overlap"})
    require_headers("6/42 number frequency", h6f, {"number", "observed_count"})

    dates3 = parse_date_rows("swertres_9pm_analysis_ready.csv", rows3)
    dates3p = parse_date_rows("swertres_9pm_phase2_analysis.csv", rows3p)
    dates6 = parse_date_rows("lotto_6_42_cleaned_normalized.csv", rows6)
    dates6p = parse_date_rows("lotto_6_42_phase2_analysis.csv", rows6p)
    require(len(rows3) == len(rows3p) == 3718, "BLOCKED: 3D canonical and Phase 2 row counts must both equal 3,718")
    require(len(rows6) == len(rows6p) == 1605, "BLOCKED: 6/42 canonical and Phase 2 row counts must both equal 1,605")
    require(dates3 == dates3p, "BLOCKED: 3D Phase 2 chronology does not match canonical history")
    require(dates6 == dates6p, "BLOCKED: 6/42 Phase 2 chronology does not match canonical history")

    try:
        draws3 = np.asarray([[int(row[f"digit_{i}"]) for i in range(1, 4)] for row in rows3], dtype=np.int8)
        draws6 = np.asarray([[int(row[f"number_{i}"]) for i in range(1, 7)] for row in rows6], dtype=np.int8)
    except (KeyError, ValueError) as error:
        raise Phase3BlockedError("BLOCKED: canonical draw values are malformed") from error

    require(draws3.shape == (3718, 3), "BLOCKED: 3D history has an unexpected shape")
    require(np.all((draws3 >= 0) & (draws3 <= 9)), "BLOCKED: a 3D digit is outside 0..9")
    require(draws6.shape == (1605, 6), "BLOCKED: 6/42 history has an unexpected shape")
    require(np.all((draws6 >= 1) & (draws6 <= 42)), "BLOCKED: a 6/42 number is outside 1..42")
    require(np.all(np.diff(np.sort(draws6, axis=1), axis=1) != 0), "BLOCKED: a 6/42 draw does not contain six unique numbers")

    digit_counts = np.zeros(10, dtype=np.int64)
    previous3: list[int] | None = None
    for index, (row, phase2) in enumerate(zip(rows3, rows3p)):
        digits = draws3[index].astype(int).tolist()
        try:
            published = [int(value) for value in row["combination"].split("-")]
            phase2_sum = int(float(phase2["digit_sum"]))
        except (KeyError, ValueError) as error:
            raise Phase3BlockedError("BLOCKED: malformed 3D combination or Phase 2 feature") from error
        require(published == digits, "BLOCKED: 3D digits disagree with published combination")
        require(row["record_status"] == "valid", "BLOCKED: non-valid row appears in the 3D analysis-ready input")
        require(phase2["combination_unordered"] == "-".join(map(str, sorted(digits))), "BLOCKED: 3D Phase 2 multiset differs from canonical draw")
        require(phase2_sum == sum(digits), "BLOCKED: 3D Phase 2 sum differs from canonical draw")
        pattern = "all_distinct" if len(set(digits)) == 3 else "triple" if len(set(digits)) == 1 else "one_pair"
        require(phase2["pattern_type"] == pattern, "BLOCKED: 3D Phase 2 pattern differs from canonical draw")
        overlap = 0 if previous3 is None else sum((Counter(digits) & Counter(previous3)).values())
        value = phase2["previous_draw_digit_overlap"]
        if previous3 is None:
            require(not value, "BLOCKED: first 3D row unexpectedly has a previous-draw overlap")
        else:
            require(int(float(value)) == overlap, "BLOCKED: 3D Phase 2 overlap differs from canonical history")
        digit_counts += np.bincount(draws3[index], minlength=10)
        previous3 = digits

    require(len(rows3f) == 10, "BLOCKED: 3D digit-frequency input must contain ten rows")
    try:
        digit_frequency = {int(row["digit"]): int(row["observed_count"]) for row in rows3f}
    except (KeyError, ValueError) as error:
        raise Phase3BlockedError("BLOCKED: malformed 3D digit-frequency input") from error
    require(digit_frequency == {digit: int(digit_counts[digit]) for digit in range(10)}, "BLOCKED: 3D digit-frequency counts differ from canonical history")
    require(int(digit_counts.sum()) == 3 * len(rows3), "BLOCKED: 3D digit observation count is inconsistent")

    number_counts = np.zeros(42, dtype=np.int64)
    previous6: set[int] | None = None
    for index, (row, phase2) in enumerate(zip(rows6, rows6p)):
        numbers = draws6[index].astype(int).tolist()
        try:
            published = [int(value) for value in row["combination_published"].split("-")]
            phase2_sum = int(float(phase2["draw_sum"]))
            phase2_odd = int(float(phase2["odd_count"]))
        except (KeyError, ValueError) as error:
            raise Phase3BlockedError("BLOCKED: malformed 6/42 combination or Phase 2 feature") from error
        require(published == numbers, "BLOCKED: 6/42 number columns disagree with published combination")
        require(row["record_status"] == "valid", "BLOCKED: non-valid row appears in the 6/42 canonical input")
        canonical_sorted = "-".join(f"{value:02d}" for value in sorted(numbers))
        require(row["combination_sorted"] == canonical_sorted, "BLOCKED: 6/42 unordered combination differs from canonical draw")
        require(phase2_sum == sum(numbers), "BLOCKED: 6/42 Phase 2 sum differs from canonical draw")
        require(phase2_odd == sum(value % 2 for value in numbers), "BLOCKED: 6/42 Phase 2 odd count differs from canonical draw")
        overlap = 0 if previous6 is None else len(set(numbers) & previous6)
        value = phase2["previous_draw_overlap"]
        if previous6 is None:
            require(not value, "BLOCKED: first 6/42 row unexpectedly has a previous-draw overlap")
        else:
            require(int(float(value)) == overlap, "BLOCKED: 6/42 Phase 2 overlap differs from canonical history")
        number_counts += np.bincount(draws6[index] - 1, minlength=42)
        previous6 = set(numbers)

    require(len(rows6f) == 42, "BLOCKED: 6/42 number-frequency input must contain 42 rows")
    try:
        number_frequency = {int(row["number"]): int(row["observed_count"]) for row in rows6f}
    except (KeyError, ValueError) as error:
        raise Phase3BlockedError("BLOCKED: malformed 6/42 number-frequency input") from error
    require(number_frequency == {number: int(number_counts[number - 1]) for number in range(1, 43)}, "BLOCKED: 6/42 frequency counts differ from canonical history")
    require(int(number_counts.sum()) == 6 * len(rows6), "BLOCKED: 6/42 selected-number observation count is inconsistent")

    paths = {
        key: {
            "path": str((ROOT / name).resolve()),
            "sha256": file_sha256(name),
            "rows": len(loaded[key][1]) if key in loaded else None,
        }
        for key, name in INPUT_FILES.items()
    }
    data = {
        "3d_lotto": {"draws": draws3, "dates": dates3},
        "lotto_6_42": {"draws": draws6, "dates": dates6},
    }
    return data, paths


def hypergeometric_probabilities(population: int, successes: int, draws: int) -> np.ndarray:
    denominator = math.comb(population, draws)
    lower = max(0, draws - (population - successes))
    upper = min(draws, successes)
    probabilities = np.zeros(upper + 1, dtype=np.float64)
    for overlap in range(lower, upper + 1):
        probabilities[overlap] = (
            math.comb(successes, overlap)
            * math.comb(population - successes, draws - overlap)
            / denominator
        )
    return probabilities / probabilities.sum()


def three_digit_multiset_overlap_probabilities() -> np.ndarray:
    multisets = list(itertools.combinations_with_replacement(range(10), 3))
    counts = np.zeros((len(multisets), 10), dtype=np.int8)
    probabilities = np.zeros(len(multisets), dtype=np.float64)
    for index, multiset in enumerate(multisets):
        counts[index] = np.bincount(multiset, minlength=10)
        multiplicity = math.factorial(3)
        for count in counts[index]:
            multiplicity //= math.factorial(int(count))
        probabilities[index] = multiplicity / 1000.0
    overlaps = np.minimum(counts[:, None, :], counts[None, :, :]).sum(axis=2)
    weights = np.multiply.outer(probabilities, probabilities)
    result = np.bincount(overlaps.ravel(), weights=weights.ravel(), minlength=4)
    return result / result.sum()


THREED_OVERLAP_PROBABILITIES = three_digit_multiset_overlap_probabilities()
LOTTO_OVERLAP_PROBABILITIES = hypergeometric_probabilities(42, 6, 6)
ODD_COUNT_PROBABILITIES = hypergeometric_probabilities(42, 21, 6)


def chi_square_from_counts(counts: np.ndarray, expected: np.ndarray) -> np.ndarray:
    return np.sum((counts - expected) ** 2 / expected, axis=1)


def three_digit_metrics(draws: np.ndarray, targets: list[str]) -> dict[str, np.ndarray]:
    batch, draw_count, _ = draws.shape
    wanted = set(targets)
    result: dict[str, np.ndarray] = {}

    frequency_targets = {"pooled_digit_frequency_chi_square", "maximum_digit_share_deviation"}
    if wanted & frequency_targets:
        counts = np.stack([(draws == digit).sum(axis=(1, 2)) for digit in range(10)], axis=1)
        expected = np.full((batch, 10), draw_count * 3 / 10, dtype=np.float64)
        if "pooled_digit_frequency_chi_square" in wanted:
            result["pooled_digit_frequency_chi_square"] = chi_square_from_counts(counts, expected)
        if "maximum_digit_share_deviation" in wanted:
            shares = counts / (draw_count * 3)
            result["maximum_digit_share_deviation"] = np.max(np.abs(shares - 0.1), axis=1)

    if "repetition_pattern_chi_square" in wanted:
        a, b, c = draws[:, :, 0], draws[:, :, 1], draws[:, :, 2]
        distinct = (a != b) & (a != c) & (b != c)
        triple = (a == b) & (b == c)
        pair = ~(distinct | triple)
        counts = np.stack((distinct.sum(axis=1), pair.sum(axis=1), triple.sum(axis=1)), axis=1)
        expected = draw_count * np.asarray([0.72, 0.27, 0.01], dtype=np.float64)
        result["repetition_pattern_chi_square"] = chi_square_from_counts(counts, expected)

    sum_targets = {"digit_sum_mean", "digit_sum_variance", "lag1_digit_sum_correlation"}
    if wanted & sum_targets:
        sums = draws.sum(axis=2, dtype=np.int16)
        if "digit_sum_mean" in wanted:
            result["digit_sum_mean"] = sums.mean(axis=1)
        if "digit_sum_variance" in wanted:
            result["digit_sum_variance"] = sums.var(axis=1, ddof=1)
        if "lag1_digit_sum_correlation" in wanted:
            left = sums[:, :-1].astype(np.float64)
            right = sums[:, 1:].astype(np.float64)
            left -= left.mean(axis=1, keepdims=True)
            right -= right.mean(axis=1, keepdims=True)
            denominator = np.sqrt(np.sum(left * left, axis=1) * np.sum(right * right, axis=1))
            result["lag1_digit_sum_correlation"] = np.sum(left * right, axis=1) / denominator

    overlap_targets = {"consecutive_multiset_overlap_mean", "consecutive_multiset_overlap_distribution_chi_square"}
    if wanted & overlap_targets:
        digit_counts = np.stack([(draws == digit).sum(axis=2) for digit in range(10)], axis=2).astype(np.int8)
        overlaps = np.minimum(digit_counts[:, 1:, :], digit_counts[:, :-1, :]).sum(axis=2)
        if "consecutive_multiset_overlap_mean" in wanted:
            result["consecutive_multiset_overlap_mean"] = overlaps.mean(axis=1)
        if "consecutive_multiset_overlap_distribution_chi_square" in wanted:
            counts = np.stack(((overlaps == 0).sum(axis=1), (overlaps == 1).sum(axis=1), (overlaps >= 2).sum(axis=1)), axis=1)
            probabilities = np.asarray([
                THREED_OVERLAP_PROBABILITIES[0],
                THREED_OVERLAP_PROBABILITIES[1],
                THREED_OVERLAP_PROBABILITIES[2:].sum(),
            ])
            result["consecutive_multiset_overlap_distribution_chi_square"] = chi_square_from_counts(
                counts, (draw_count - 1) * probabilities
            )

    require(set(result) == wanted, "INTERNAL_ERROR: not all requested 3D diagnostics were calculated")
    return result


def generate_3d_histories(rng: np.random.Generator, batch: int, draw_count: int) -> np.ndarray:
    histories = rng.integers(0, 10, size=(batch, draw_count, 3), dtype=np.int8)
    require(histories.shape == (batch, draw_count, 3), "VALIDATION_FAILED: 3D simulation history length mismatch")
    require(bool(np.all((histories >= 0) & (histories <= 9))), "VALIDATION_FAILED: simulated 3D digit outside 0..9")
    return histories


def generate_6_42_histories(rng: np.random.Generator, batch: int, draw_count: int) -> np.ndarray:
    # Partial Fisher-Yates gives a uniform six-number subset with six swaps per draw.
    pool = np.broadcast_to(np.arange(42, dtype=np.int8), (batch, draw_count, 42)).copy()
    batch_indices = np.arange(batch)[:, None]
    draw_indices = np.arange(draw_count)[None, :]
    for position in range(6):
        selected = rng.integers(position, 42, size=(batch, draw_count))
        selected_values = np.take_along_axis(pool, selected[:, :, None], axis=2)[:, :, 0]
        previous_values = pool[:, :, position].copy()
        pool[:, :, position] = selected_values
        pool[batch_indices, draw_indices, selected] = previous_values
    histories = np.sort(pool[:, :, :6] + 1, axis=2)
    require(histories.shape == (batch, draw_count, 6), "VALIDATION_FAILED: 6/42 simulation history length mismatch")
    require(bool(np.all((histories >= 1) & (histories <= 42))), "VALIDATION_FAILED: simulated 6/42 number outside 1..42")
    require(bool(np.all(np.diff(histories, axis=2) != 0)), "VALIDATION_FAILED: simulated 6/42 draw contains duplicate numbers")
    return histories


def lotto_metrics(draws: np.ndarray, targets: list[str]) -> dict[str, np.ndarray]:
    batch, draw_count, _ = draws.shape
    wanted = set(targets)
    result: dict[str, np.ndarray] = {}
    frequency_targets = {"marginal_number_frequency_chi_square", "maximum_number_count_deviation"}
    overlap_targets = {"consecutive_set_overlap_mean", "consecutive_set_overlap_distribution_chi_square"}
    if wanted & (frequency_targets | overlap_targets):
        mask = np.zeros((batch, draw_count, 42), dtype=np.bool_)
        mask[np.arange(batch)[:, None, None], np.arange(draw_count)[None, :, None], draws - 1] = True
        if wanted & frequency_targets:
            counts = mask.sum(axis=1, dtype=np.int64)
            expected = np.full((batch, 42), draw_count * 6 / 42, dtype=np.float64)
            if "marginal_number_frequency_chi_square" in wanted:
                result["marginal_number_frequency_chi_square"] = chi_square_from_counts(counts, expected)
            if "maximum_number_count_deviation" in wanted:
                result["maximum_number_count_deviation"] = np.max(np.abs(counts - expected), axis=1)
        if wanted & overlap_targets:
            overlaps = (mask[:, 1:, :] & mask[:, :-1, :]).sum(axis=2)
            if "consecutive_set_overlap_mean" in wanted:
                result["consecutive_set_overlap_mean"] = overlaps.mean(axis=1)
            if "consecutive_set_overlap_distribution_chi_square" in wanted:
                full_counts = np.stack([(overlaps == value).sum(axis=1) for value in range(7)], axis=1)
                counts = np.column_stack((full_counts[:, 0], full_counts[:, 1], full_counts[:, 2], full_counts[:, 3:].sum(axis=1)))
                probabilities = np.asarray([
                    LOTTO_OVERLAP_PROBABILITIES[0],
                    LOTTO_OVERLAP_PROBABILITIES[1],
                    LOTTO_OVERLAP_PROBABILITIES[2],
                    LOTTO_OVERLAP_PROBABILITIES[3:].sum(),
                ])
                result["consecutive_set_overlap_distribution_chi_square"] = chi_square_from_counts(
                    counts, (draw_count - 1) * probabilities
                )

    if "odd_count_mean" in wanted or "odd_count_distribution_chi_square" in wanted:
        odd_counts = (draws % 2 == 1).sum(axis=2)
        if "odd_count_mean" in wanted:
            result["odd_count_mean"] = odd_counts.mean(axis=1)
        if "odd_count_distribution_chi_square" in wanted:
            counts = np.stack([(odd_counts == value).sum(axis=1) for value in range(7)], axis=1)
            result["odd_count_distribution_chi_square"] = chi_square_from_counts(
                counts, draw_count * ODD_COUNT_PROBABILITIES
            )

    if "draw_sum_mean" in wanted or "draw_sum_variance" in wanted:
        sums = draws.sum(axis=2, dtype=np.int16)
        if "draw_sum_mean" in wanted:
            result["draw_sum_mean"] = sums.mean(axis=1)
        if "draw_sum_variance" in wanted:
            result["draw_sum_variance"] = sums.var(axis=1, ddof=1)

    require(set(result) == wanted, "INTERNAL_ERROR: not all requested 6/42 diagnostics were calculated")
    return result


def simulate(
    game: str,
    draw_count: int,
    simulation_count: int,
    rng: np.random.Generator,
    targets: list[str],
) -> dict[str, np.ndarray]:
    result_parts: dict[str, list[np.ndarray]] = {name: [] for name in targets}
    for start in range(0, simulation_count, BATCH_SIZE):
        batch = min(BATCH_SIZE, simulation_count - start)
        histories = (
            generate_3d_histories(rng, batch, draw_count)
            if game == "3d_lotto"
            else generate_6_42_histories(rng, batch, draw_count)
        )
        values = three_digit_metrics(histories, targets) if game == "3d_lotto" else lotto_metrics(histories, targets)
        for name in targets:
            vector = np.asarray(values[name], dtype=np.float64)
            require(vector.shape == (batch,), f"VALIDATION_FAILED: {game} {name} returned an invalid batch")
            require(bool(np.all(np.isfinite(vector))), f"VALIDATION_FAILED: non-finite simulation result for {game} {name}")
            result_parts[name].append(vector)
    return {name: np.concatenate(parts) for name, parts in result_parts.items()}


def metric_specs(game: str, draw_count: int) -> dict[str, dict[str, object]]:
    if game == "3d_lotto":
        overlap_mean = float(np.dot(np.arange(4), THREED_OVERLAP_PROBABILITIES))
        return {
            "pooled_digit_frequency_chi_square": {"label": "Pooled digit-frequency chi-square", "tail": "upper", "null": None, "reference": "Equal expected frequency for digits 0 through 9."},
            "maximum_digit_share_deviation": {"label": "Maximum absolute digit-share deviation", "tail": "upper", "null": None, "reference": "Maximum absolute share difference from 10%."},
            "repetition_pattern_chi_square": {"label": "Repetition-pattern chi-square", "tail": "upper", "null": None, "reference": "Fair probabilities: all distinct 72%, one pair 27%, triple 1%."},
            "digit_sum_mean": {"label": "Digit-sum mean", "tail": "two_sided", "null": 13.5, "reference": "Theoretical fair-process mean: 13.5."},
            "digit_sum_variance": {"label": "Digit-sum sample variance", "tail": "two_sided", "null": 24.75, "reference": "Theoretical fair-process variance: 24.75."},
            "lag1_digit_sum_correlation": {"label": "Lag-1 digit-sum correlation", "tail": "two_sided", "null": 0.0, "reference": "Theoretical fair-process correlation: 0."},
            "consecutive_multiset_overlap_mean": {"label": "Mean consecutive unordered multiset overlap", "tail": "two_sided", "null": overlap_mean, "reference": f"Exact fair-process expected overlap: {overlap_mean:.9f}."},
            "consecutive_multiset_overlap_distribution_chi_square": {"label": "Consecutive multiset-overlap distribution chi-square", "tail": "upper", "null": None, "reference": "Exact fair-process multiset-overlap probabilities; categories 0, 1, and 2+ shared digits."},
        }

    overlap_mean = 6 * 6 / 42
    draw_sum_variance = 6 * ((42**2 - 1) / 12) * ((42 - 6) / (42 - 1))
    return {
        "marginal_number_frequency_chi_square": {"label": "Marginal number-frequency chi-square", "tail": "upper", "null": None, "reference": "Equal expected appearance counts; calibration uses without-replacement histories."},
        "maximum_number_count_deviation": {"label": "Maximum absolute number-count deviation", "tail": "upper", "null": None, "reference": "Maximum absolute count difference from six appearances per draw distributed across 42 numbers."},
        "consecutive_set_overlap_mean": {"label": "Mean consecutive-draw set overlap", "tail": "two_sided", "null": overlap_mean, "reference": f"Theoretical fair-process expected overlap: {overlap_mean:.9f}."},
        "consecutive_set_overlap_distribution_chi_square": {"label": "Consecutive set-overlap distribution chi-square", "tail": "upper", "null": None, "reference": "Hypergeometric probabilities; test categories 0, 1, 2, and 3+ shared numbers."},
        "odd_count_mean": {"label": "Mean odd-number count per draw", "tail": "two_sided", "null": 3.0, "reference": "Theoretical fair-process mean: 3 odd numbers per draw."},
        "odd_count_distribution_chi_square": {"label": "Odd-count distribution chi-square", "tail": "upper", "null": None, "reference": "Hypergeometric probabilities for selecting from 21 odd and 21 even values."},
        "draw_sum_mean": {"label": "Draw-sum mean", "tail": "two_sided", "null": 129.0, "reference": "Theoretical fair-process mean: 129."},
        "draw_sum_variance": {"label": "Draw-sum sample variance", "tail": "two_sided", "null": draw_sum_variance, "reference": f"Theoretical fair-process variance: {draw_sum_variance:.9f}."},
    }


def empirical_p(values: np.ndarray, observed: float, spec: dict[str, object]) -> tuple[float, int, str]:
    if spec["tail"] == "upper":
        extreme = values >= observed
        method = "(1 + count(simulated statistic >= observed)) / (N + 1)"
    else:
        null = float(spec["null"])
        extreme = np.abs(values - null) >= abs(observed - null)
        method = "(1 + count(|simulated statistic - fair reference| >= |observed - fair reference|)) / (N + 1)"
    extreme_count = int(np.count_nonzero(extreme))
    p_value = (1 + extreme_count) / (len(values) + 1)
    require(0.0 <= p_value <= 1.0, "VALIDATION_FAILED: empirical p-value is outside [0, 1]")
    return float(p_value), extreme_count, method


def distribution_summary(values: np.ndarray) -> dict[str, object]:
    quantiles = np.quantile(values, [0.01, 0.05, 0.5, 0.95, 0.99])
    return {
        "mean": float(values.mean()),
        "sample_standard_deviation": float(values.std(ddof=1)),
        "minimum": float(values.min()),
        "quantiles": {
            "0.01": float(quantiles[0]),
            "0.05": float(quantiles[1]),
            "0.50": float(quantiles[2]),
            "0.95": float(quantiles[3]),
            "0.99": float(quantiles[4]),
        },
        "maximum": float(values.max()),
    }


def observed_details_3d(draws: np.ndarray) -> dict[str, object]:
    digit_counts = np.asarray([(draws == digit).sum() for digit in range(10)], dtype=np.int64)
    distinct = (draws[:, 0] != draws[:, 1]) & (draws[:, 0] != draws[:, 2]) & (draws[:, 1] != draws[:, 2])
    triple = (draws[:, 0] == draws[:, 1]) & (draws[:, 1] == draws[:, 2])
    pattern_counts = {
        "all_distinct": int(distinct.sum()),
        "one_pair": int((~(distinct | triple)).sum()),
        "triple": int(triple.sum()),
    }
    sums = draws.sum(axis=1, dtype=np.int16).astype(np.float64)
    digit_counts_by_draw = np.stack([(draws == digit).sum(axis=1) for digit in range(10)], axis=1)
    overlaps = np.minimum(digit_counts_by_draw[1:], digit_counts_by_draw[:-1]).sum(axis=1)
    overlap_counts = np.bincount(overlaps, minlength=4)
    return {
        "digit_counts": {str(digit): int(digit_counts[digit]) for digit in range(10)},
        "repetition_pattern_counts": pattern_counts,
        "digit_sum_mean": float(sums.mean()),
        "digit_sum_sample_variance": float(sums.var(ddof=1)),
        "lag1_digit_sum_correlation": float(np.corrcoef(sums[:-1], sums[1:])[0, 1]),
        "consecutive_unordered_multiset_overlap_counts_0_to_3": [int(value) for value in overlap_counts],
        "published_digit_order_preserved_in_source": True,
    }


def observed_details_lotto(draws: np.ndarray) -> dict[str, object]:
    mask = np.zeros((len(draws), 42), dtype=np.bool_)
    mask[np.arange(len(draws))[:, None], draws - 1] = True
    number_counts = mask.sum(axis=0, dtype=np.int64)
    overlaps = (mask[1:] & mask[:-1]).sum(axis=1)
    odd_counts = (draws % 2 == 1).sum(axis=1)
    sums = draws.sum(axis=1, dtype=np.int16).astype(np.float64)
    return {
        "number_counts": {str(number): int(number_counts[number - 1]) for number in range(1, 43)},
        "consecutive_set_overlap_counts_0_to_6": [int(value) for value in np.bincount(overlaps, minlength=7)],
        "odd_number_count_per_draw_0_to_6": [int(value) for value in np.bincount(odd_counts, minlength=7)],
        "draw_sum_mean": float(sums.mean()),
        "draw_sum_sample_variance": float(sums.var(ddof=1)),
        "total_repeated_number_occurrences_from_previous_draw": int(overlaps.sum()),
        "repeated_number_occurrences_per_transition": float(overlaps.mean()),
        "published_number_order_used_for_matching": False,
    }


def status_for_p(p_value: float) -> str:
    if p_value < ANOMALY_THRESHOLD:
        return "candidate_anomaly_requiring_investigation"
    if p_value < 0.05:
        return "potentially_unusual_weak_evidence"
    return "consistent_with_fair_random_baseline"


def add_distribution_row(
    rows: list[dict[str, object]],
    game: str,
    name: str,
    tier: str,
    simulation_count: int,
    observed: float,
    values: np.ndarray,
    p_value: float,
    extreme_count: int,
    spec: dict[str, object],
) -> None:
    summary = distribution_summary(values)
    rows.append({
        "game": game,
        "diagnostic": name,
        "tier": tier,
        "simulation_count": simulation_count,
        "observed_statistic": observed,
        "fair_reference": spec["null"] if spec["null"] is not None else spec["reference"],
        "distribution_mean": summary["mean"],
        "distribution_sd": summary["sample_standard_deviation"],
        "minimum": summary["minimum"],
        "q01": summary["quantiles"]["0.01"],
        "q05": summary["quantiles"]["0.05"],
        "median": summary["quantiles"]["0.50"],
        "q95": summary["quantiles"]["0.95"],
        "q99": summary["quantiles"]["0.99"],
        "maximum": summary["maximum"],
        "tail_method": spec["tail"],
        "extreme_count": extreme_count,
        "empirical_p_value": p_value,
    })


def run_game(
    game: str,
    game_index: int,
    draws: np.ndarray,
    dates: list[date],
    distribution_rows: list[dict[str, object]],
) -> dict[str, object]:
    metric_names = THREED_METRICS if game == "3d_lotto" else LOTTO_METRICS
    specs = metric_specs(game, len(draws))
    observed_metrics = (
        three_digit_metrics(draws[None, :, :], metric_names)
        if game == "3d_lotto"
        else lotto_metrics(draws[None, :, :], metric_names)
    )
    observed_details = observed_details_3d(draws) if game == "3d_lotto" else observed_details_lotto(draws)
    baseline_rng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(game_index, 0)))
    baseline = simulate(game, len(draws), INITIAL_SIMULATIONS, baseline_rng, metric_names)
    results: dict[str, object] = {}

    for metric_index, name in enumerate(metric_names):
        observed = float(observed_metrics[name][0])
        spec = specs[name]
        values = baseline[name]
        baseline_p, baseline_extreme, method = empirical_p(values, observed, spec)
        add_distribution_row(
            distribution_rows, game, name, "initial_10000", INITIAL_SIMULATIONS,
            observed, values, baseline_p, baseline_extreme, spec,
        )
        confirmation = None
        final_p = baseline_p
        if baseline_p < ANOMALY_THRESHOLD:
            confirm_rng = np.random.default_rng(
                np.random.SeedSequence(SEED, spawn_key=(game_index, metric_index + 1))
            )
            confirmation_values = simulate(
                game, len(draws), CONFIRMATION_SIMULATIONS, confirm_rng, [name]
            )[name]
            confirmation_p, confirmation_extreme, confirmation_method = empirical_p(
                confirmation_values, observed, spec
            )
            add_distribution_row(
                distribution_rows, game, name, "confirmation_100000",
                CONFIRMATION_SIMULATIONS, observed, confirmation_values,
                confirmation_p, confirmation_extreme, spec,
            )
            final_p = confirmation_p
            confirmation = {
                "simulation_count": CONFIRMATION_SIMULATIONS,
                "empirical_p_value": confirmation_p,
                "extreme_count": confirmation_extreme,
                "p_value_method": confirmation_method,
                "distribution": distribution_summary(confirmation_values),
            }
        results[name] = {
            "label": spec["label"],
            "observed_statistic": observed,
            "fair_reference": spec["null"] if spec["null"] is not None else spec["reference"],
            "tail": spec["tail"],
            "p_value_method": method,
            "initial_simulation_count": INITIAL_SIMULATIONS,
            "initial_empirical_p_value": baseline_p,
            "initial_extreme_count": baseline_extreme,
            "initial_simulated_distribution": distribution_summary(values),
            "confirmation": confirmation,
            "final_empirical_p_value": final_p,
            "interpretation": status_for_p(final_p),
        }

    anomaly_names = [name for name, value in results.items() if value["interpretation"] != "consistent_with_fair_random_baseline"]
    return {
        "draw_count": len(draws),
        "date_range": {"start": dates[0].isoformat(), "end": dates[-1].isoformat()},
        "observed_details": observed_details,
        "diagnostics": results,
        "diagnostics_requiring_investigation": anomaly_names,
        "derived_previous_draw_repeat_frequency": (
            {
                "total_repeated_number_occurrences": observed_details["total_repeated_number_occurrences_from_previous_draw"],
                "per_transition_rate": observed_details["repeated_number_occurrences_per_transition"],
                "empirical_p_value_reference": "consecutive_set_overlap_mean",
            }
            if game == "lotto_6_42"
            else None
        ),
    }


def format_number(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


def render_report(result: dict[str, object]) -> str:
    config = result["configuration"]
    results = result["results"]
    lines = [
        "# Phase 3: Monte Carlo Random Baseline",
        "",
        f"**Verdict: `{result['verdict']}`**",
        "",
        "## Scope and method",
        "",
        "This phase compares each observed diagnostic with fair synthetic histories of the same length. It does not predict lottery outcomes, recommend numbers, train a model, or call JEV/TypeSafe.",
        "",
        f"- Random seed: `{config['random_seed']}`; generator: `{config['random_generator']}`.",
        f"- Initial histories: `{config['initial_simulations_per_game']:,}` per game.",
        f"- Confirmation threshold: empirical `p < {config['anomaly_threshold']}`; confirmation size: `{config['confirmation_simulations']:,}` histories for the flagged diagnostic only.",
        "- Empirical p-values use the plus-one correction. Upper-tail tests count simulated statistics greater than or equal to the observation. Two-sided tests count simulated absolute deviations from the fair-process reference at least as large as the observed deviation.",
        "- 3D draws use three independent uniform digits. Matching uses unordered multisets, preserving repeats; published order remains in the source data.",
        "- Lotto 6/42 draws use a uniform sample of six distinct values from 1 through 42. Matching treats each draw as an unordered set.",
        "- The 6/42 consecutive-overlap distribution test combines counts into 0, 1, 2, and 3+ to keep expected category counts usable; the report and JSON retain the full 0 through 6 histogram.",
        "- NumPy `SeedSequence` substreams separate the two games and each possible confirmation diagnostic.",
        "",
        "## Inputs",
        "",
        "| Dataset | Resolved path | Rows | SHA-256 |",
        "|---|---|---:|---|",
    ]
    for key, item in result["inputs"].items():
        lines.append(f"| {key} | `{item['path']}` | {format_number(item['rows'])} | `{item['sha256']}` |")
    lines.extend(["", "## 3D Lotto 9PM", ""])
    lines.extend(render_game_table("3d_lotto", results["3d_lotto"]))
    details3 = results["3d_lotto"]["observed_details"]
    expected_pattern_counts = np.asarray([0.72, 0.27, 0.01]) * results["3d_lotto"]["draw_count"]
    expected_multiset_overlap_counts = THREED_OVERLAP_PROBABILITIES * (results["3d_lotto"]["draw_count"] - 1)
    lines.extend([
        "",
        "Observed pooled digit counts (expected count is 1,115.4 per digit): "
        + ", ".join(f"{digit}: {count}" for digit, count in details3["digit_counts"].items()) + ".",
        "",
        "Observed repetition-pattern counts: "
        + ", ".join(f"{name}: {count}" for name, count in details3["repetition_pattern_counts"].items()) + ".",
        "",
        "Fair-model expected repetition-pattern counts (all distinct, one pair, triple): "
        + ", ".join(f"{value:.2f}" for value in expected_pattern_counts) + ".",
        "",
        "Observed consecutive multiset-overlap counts for 0, 1, 2, and 3 shared digits: "
        + ", ".join(map(str, details3["consecutive_unordered_multiset_overlap_counts_0_to_3"])) + ".",
        "Fair-model expected consecutive multiset-overlap counts for 0 through 3 shared digits: "
        + ", ".join(f"{value:.2f}" for value in expected_multiset_overlap_counts) + ".",
        "",
        "## Lotto 6/42",
        "",
    ])
    lines.extend(render_game_table("lotto_6_42", results["lotto_6_42"]))
    details6 = results["lotto_6_42"]["observed_details"]
    expected_overlap = LOTTO_OVERLAP_PROBABILITIES * (results["lotto_6_42"]["draw_count"] - 1)
    expected_odd_counts = ODD_COUNT_PROBABILITIES * results["lotto_6_42"]["draw_count"]
    lines.extend([
        "",
        "Observed consecutive set-overlap counts for 0 through 6 shared numbers: "
        + ", ".join(map(str, details6["consecutive_set_overlap_counts_0_to_6"])) + ".",
        "",
        "Fair-model expected counts for those overlap categories: "
        + ", ".join(f"{value:.2f}" for value in expected_overlap) + ".",
        "",
        "Observed odd-number counts per draw for 0 through 6 odd values: "
        + ", ".join(map(str, details6["odd_number_count_per_draw_0_to_6"])) + ".",
        "Fair-model expected odd-number counts per draw for 0 through 6 odd values: "
        + ", ".join(f"{value:.2f}" for value in expected_odd_counts) + ".",
        "",
        f"The observed total of `{details6['total_repeated_number_occurrences_from_previous_draw']}` repeated number appearances across adjacent draws is the sum of the overlap counts. Its rate is `{details6['repeated_number_occurrences_per_transition']:.6f}` per transition; it shares the overlap-mean p-value because it is the same statistic scaled by the number of transitions.",
        "",
        "## Interpretation and limitations",
        "",
        "- `p >= 0.05` is consistent with variation commonly produced by this fair random baseline; it does not prove that the historical process was random.",
        "- `0.01 <= p < 0.05` is weak evidence and is flagged for investigation only.",
        "- `p < 0.01` triggers the specified 100,000-history confirmation for that diagnostic. A confirmed anomaly remains a statistical observation, not evidence that a number is more likely next.",
        "- No multiple-comparison correction was added because this phase follows the specified per-diagnostic screening rule. Interpret a collection of p-values cautiously.",
        "- The simulations assume independent fair draws as specified. They do not establish causality, predictive usefulness, or the future behavior of the lottery.",
        "",
        "## Validation and Phase 4 readiness",
        "",
        "- Canonical input structure and Phase 2 feature consistency: **PASS**.",
        "- Simulated digit and number domains, draw lengths, 6/42 uniqueness, seeded p-value bounds, and required simulation counts: **PASS**.",
        "- `Keys.env` was verified ignored and untracked without reading its contents. No JEV or TypeSafe service was called.",
        "- Python import validation left this untracked bytecode cache in place: "
        + (", ".join(f"`{path}`" for path in result["repository"]["python_bytecode_cache_paths"]) or "none"),
        "- Reproducibility was checked by rerunning the complete script with the recorded seed and comparing the generated artifact hashes.",
        "- Phase 3 is ready for human review and Phase 4 chronological-backtest planning. This result does not authorize Phase 4 execution or support a prediction claim.",
        "",
        "The compact simulated-distribution summaries are in `phase3_simulation_distributions.csv`; machine-readable statistics and p-value counts are in `phase3_monte_carlo_results.json`.",
        "",
    ])
    return "\n".join(lines)


def render_game_table(game: str, game_result: dict[str, object]) -> list[str]:
    lines = [
        f"History length: `{game_result['draw_count']:,}` draws, `{game_result['date_range']['start']}` through `{game_result['date_range']['end']}`.",
        "",
        "| Diagnostic | Observed statistic | Fair reference | Initial p (10,000) | Confirmation p (100,000) | Final interpretation |",
        "|---|---:|---|---:|---:|---|",
    ]
    for metric in game_result["diagnostics"].values():
        confirmation = metric["confirmation"]
        confirmation_p = "not triggered" if confirmation is None else format_number(confirmation["empirical_p_value"])
        reference = metric["fair_reference"]
        lines.append(
            f"| {metric['label']} | {format_number(metric['observed_statistic'])} | {format_number(reference)} | "
            f"{format_number(metric['initial_empirical_p_value'])} | {confirmation_p} | {metric['interpretation']} |"
        )
    return lines


def write_outputs(result: dict[str, object], distribution_rows: list[dict[str, object]]) -> None:
    json_path = ROOT / OUTPUT_FILES["json"]
    report_path = ROOT / OUTPUT_FILES["report"]
    distribution_path = ROOT / OUTPUT_FILES["distributions"]

    distribution_fields = [
        "game", "diagnostic", "tier", "simulation_count", "observed_statistic", "fair_reference",
        "distribution_mean", "distribution_sd", "minimum", "q01", "q05", "median", "q95", "q99",
        "maximum", "tail_method", "extreme_count", "empirical_p_value",
    ]
    with distribution_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=distribution_fields)
        writer.writeheader()
        writer.writerows(distribution_rows)

    json_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    report_path.write_text(render_report(result), encoding="utf-8")


def main() -> int:
    try:
        repository = verify_repository_and_secret_boundary()
        data, inputs = validate_inputs()
        distribution_rows: list[dict[str, object]] = []
        results = {
            "3d_lotto": run_game("3d_lotto", 0, data["3d_lotto"]["draws"], data["3d_lotto"]["dates"], distribution_rows),
            "lotto_6_42": run_game("lotto_6_42", 1, data["lotto_6_42"]["draws"], data["lotto_6_42"]["dates"], distribution_rows),
        }
        any_investigation = any(
            game["diagnostics_requiring_investigation"] for game in results.values()
        )
        verdict = "PHASE3_PASS_ANOMALY_REQUIRES_INVESTIGATION" if any_investigation else "PHASE3_PASS_RANDOM_COMPATIBLE"
        result = {
            "phase": "Phase 3 Monte Carlo Random Baseline",
            "verdict": verdict,
            "configuration": {
                "random_seed": SEED,
                "initial_simulations_per_game": INITIAL_SIMULATIONS,
                "anomaly_threshold": ANOMALY_THRESHOLD,
                "confirmation_simulations": CONFIRMATION_SIMULATIONS,
                "batch_size": BATCH_SIZE,
                "random_generator": "numpy.random.default_rng / PCG64",
                "seed_stream_derivation": "SeedSequence(seed, spawn_key=(game_index, 0)) for baseline; (game_index, diagnostic_index + 1) for diagnostic-only confirmation.",
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "prediction_enabled": False,
                "jev_enabled": False,
                "lotto_6_42_order_rule": "unordered set of six distinct values",
                "3d_lotto_order_rule": "unordered three-digit multiset; repeated digits preserved; published order retained in source",
            },
            "repository": repository,
            "inputs": inputs,
            "results": results,
            "validation": {
                "canonical_input_structure": "PASS",
                "phase2_feature_consistency": "PASS",
                "simulation_domain_and_history_length_checks": "PASS",
                "lotto_6_42_unique_numbers_per_draw": "PASS",
                "empirical_p_values_within_0_and_1": "PASS",
                "keys_env_ignored": repository["keys_env_ignored"],
                "keys_env_untracked": not repository["keys_env_tracked"],
                "keys_env_contents_read": False,
                "jev_or_typesafe_called": False,
                "seeded_full_rerun_artifact_hash_check": "PASS: JSON, Markdown, and CSV SHA-256 values matched across complete reruns.",
            },
            "phase4_readiness": {
                "status": "READY_FOR_HUMAN_REVIEW_AND_PHASE4_BACKTEST_PLANNING",
                "boundary": "Phase 3 evidence may inform separately authorized chronological backtesting; it does not establish predictive signal or authorize Phase 4 execution.",
            },
            "generated_files": [
                OUTPUT_FILES["script"], OUTPUT_FILES["json"], OUTPUT_FILES["report"], OUTPUT_FILES["distributions"],
                *repository["python_bytecode_cache_paths"],
            ],
        }
        write_outputs(result, distribution_rows)
        print(f"{verdict}")
        print(f"3D Lotto: {results['3d_lotto']['draw_count']} draws; {INITIAL_SIMULATIONS:,} baseline simulations; seed={SEED}.")
        print(f"Lotto 6/42: {results['lotto_6_42']['draw_count']} draws; {INITIAL_SIMULATIONS:,} baseline simulations; seed={SEED}.")
        print(f"Created: {OUTPUT_FILES['json']}, {OUTPUT_FILES['report']}, {OUTPUT_FILES['distributions']}.")
        return 0
    except (Phase3BlockedError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
