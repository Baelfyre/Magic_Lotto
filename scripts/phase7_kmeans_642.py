"""Descriptive 6/42 K-means exploration on the sealed-safe Phase 4 train partition.

No validation or test rows are loaded. Clusters describe past draws, not
probabilities of future winning combinations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

SEED = 162
BALLS = 42
DRAW_SIZE = 6
TRAIN_PREFIX_ROWS = 1003  # First 101 clean records plus 902 Phase 4 training records
TRAIN_COUNT = 902
TRAIN_START_SOURCE_ROW = 103
TRAIN_END_SOURCE_ROW = 1008
DRAW_COLS = [f"number_{i}" for i in range(1, DRAW_SIZE + 1)]


def load_train_only(path: Path) -> pd.DataFrame:
    """Read exactly the pre-established training prefix, never validation/test."""
    df = pd.read_csv(path, nrows=TRAIN_PREFIX_ROWS)
    if len(df) != TRAIN_PREFIX_ROWS:
        raise ValueError("Training prefix truncated; refusing to continue")
    needed = set(DRAW_COLS + ["draw_date", "source_row", "record_status"])
    if not needed.issubset(df.columns):
        raise ValueError(f"Missing columns: {sorted(needed - set(df.columns))}")
    if int(df.iloc[-1]["source_row"]) != TRAIN_END_SOURCE_ROW:
        raise ValueError("Training boundary changed; refusing to continue")
    if df["source_row"].duplicated().any() or not df["source_row"].is_monotonic_increasing:
        raise ValueError("Duplicate or unordered source_row")
    train = df.loc[df["source_row"].between(TRAIN_START_SOURCE_ROW, TRAIN_END_SOURCE_ROW)].copy()
    if len(train) != TRAIN_COUNT or (train["record_status"] != "valid").any():
        raise ValueError("Training partition does not match Phase 4")
    if train["draw_date"].iloc[0] != "2016-08-30" or train["draw_date"].iloc[-1] != "2022-11-12":
        raise ValueError("Training date boundaries changed")
    if not train["draw_date"].is_monotonic_increasing:
        raise ValueError("Training dates not ordered")
    vals = train[DRAW_COLS].to_numpy(dtype=float)
    if not np.isfinite(vals).all() or np.any(vals != np.floor(vals)):
        raise ValueError("Invalid non-integer or nonfinite number")
    nums = vals.astype(int)
    if np.any((nums < 1) | (nums > BALLS)) or np.any(np.diff(np.sort(nums, axis=1), axis=1) == 0):
        raise ValueError("Draw with out-of-range or duplicated balls")
    return train


def encode_draws(numbers: np.ndarray) -> np.ndarray:
    """Represent unordered six-number combinations as 42-dimensional indicators."""
    numbers = np.asarray(numbers)
    if numbers.ndim != 2 or numbers.shape[1] != DRAW_SIZE:
        raise ValueError("Expected a matrix with six columns")
    if np.any((numbers < 1) | (numbers > BALLS)) or np.any(np.diff(np.sort(numbers, axis=1), axis=1) == 0):
        raise ValueError("Invalid six-number combination")
    x = np.zeros((len(numbers), BALLS), dtype=np.float64)
    x[np.arange(len(numbers))[:, None], numbers.astype(int) - 1] = 1.0
    if not np.all(x.sum(axis=1) == DRAW_SIZE):
        raise AssertionError("One-hot representation must have exactly six ones")
    return x


def fair_null_draws(n: int, rng: np.random.Generator) -> np.ndarray:
    """Uniformly sample independent 6-of-42 sets without replacement."""
    # Ranks of iid continuous uniforms are equiprobable permutations.
    return np.argsort(rng.random((n, BALLS)), axis=1)[:, :DRAW_SIZE] + 1


def fit_kmeans(x: np.ndarray, k: int, seed: int = SEED) -> KMeans:
    if k < 2 or k >= len(x):
        raise ValueError("k outside supported range")
    return KMeans(n_clusters=k, n_init=5, random_state=seed, max_iter=200).fit(x)


def nearest_historical_examples(x: np.ndarray, model: KMeans) -> list[list[int]]:
    """Actual training combinations closest to centroids, not forecasts."""
    examples = []
    for cluster, centroid in enumerate(model.cluster_centers_):
        positions = np.flatnonzero(model.labels_ == cluster)
        idx = positions[np.argmin(((x[positions] - centroid) ** 2).sum(axis=1))]
        examples.append((np.flatnonzero(x[idx] == 1) + 1).astype(int).tolist())
    return examples


def analyze(train: pd.DataFrame, null_replicates: int = 100, seed: int = SEED) -> dict:
    if null_replicates < 20:
        raise ValueError("Use >=20 null replications for a meaningful descriptive reference")
    x = encode_draws(train[DRAW_COLS].to_numpy(dtype=int))
    model = fit_kmeans(x, k=6, seed=seed)  # fixed a priori, not selected by validation
    counts = np.bincount(model.labels_, minlength=6)
    rng = np.random.default_rng(seed)
    null_inertia = np.empty(null_replicates)
    for i in range(null_replicates):
        null_x = encode_draws(fair_null_draws(len(x), rng))
        null_inertia[i] = fit_kmeans(null_x, k=6, seed=seed + i + 1).inertia_
    freqs = x.sum(axis=0).astype(int)
    cooccur = x.T @ x
    expectation_pair = len(x) * DRAW_SIZE * (DRAW_SIZE - 1) / (BALLS * (BALLS - 1))
    np.fill_diagonal(cooccur, np.nan)
    p_lower = (1 + int(np.sum(null_inertia <= model.inertia_))) / (null_replicates + 1)
    elbow = {str(k): float(fit_kmeans(x, k, seed).inertia_) for k in range(2, 9)}
    pca = PCA(n_components=2, random_state=seed)
    points = pca.fit_transform(x)
    return {
        "x": x, "model": model, "freqs": freqs, "cooccur": cooccur,
        "cluster_counts": counts, "null_inertia": null_inertia, "elbow": elbow,
        "points": points, "pca_explained": pca.explained_variance_ratio_,
        "pair_expected": float(expectation_pair), "p_lower": p_lower,
        "medoids": nearest_historical_examples(x, model),
    }


def make_figures(result: dict, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    x, model = result["x"], result["model"]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(np.arange(1, BALLS + 1), result["freqs"], width=0.8)
    ax.axhline(len(x) * DRAW_SIZE / BALLS, linestyle="--", color="black", label="Fair-model expected frequency")
    ax.set(xlabel="Ball (1 to 42)", ylabel="Training-draw appearances", title="6/42 training-prefix frequency (descriptive)")
    ax.legend()
    fig.tight_layout(); fig.savefig(dest / "01_frequency.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 7))
    residual = result["cooccur"] - result["pair_expected"]
    m = float(np.nanmax(np.abs(residual)))
    im = ax.imshow(np.ma.masked_invalid(residual), cmap="coolwarm", vmin=-m, vmax=m)
    ax.set(xlabel="Ball index (1 to 42)", ylabel="Ball index (1 to 42)", title="Pair counts minus fair-model expectation (training)")
    fig.colorbar(im, ax=ax, label="Observed minus expected appearances")
    fig.tight_layout(); fig.savefig(dest / "02_pair_residuals.png", dpi=150); plt.close(fig)

    order = np.argsort(-result["cluster_counts"])
    fig, ax = plt.subplots(figsize=(11, 4))
    c = ax.imshow(model.cluster_centers_[order], aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set(yticks=range(6), yticklabels=[f"Cluster {i + 1} (n={result['cluster_counts'][i]})" for i in order],
           xlabel="Ball index (1 to 42)", title="Cluster membership rates among historical training draws")
    fig.colorbar(c, ax=ax, label="Within-cluster share containing ball")
    fig.tight_layout(); fig.savefig(dest / "03_cluster_profiles.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(result["points"][:, 0], result["points"][:, 1], c=model.labels_, cmap="tab10", s=16, alpha=0.68)
    ax.set(xlabel="PCA component 1", ylabel="PCA component 2", title="K-means clusters projected to 2D PCA (illustrative)")
    fig.tight_layout(); fig.savefig(dest / "04_cluster_pca.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([int(k) for k in result["elbow"]], list(result["elbow"].values()), marker="o")
    ax.axvline(6, linestyle="--", color="black", label="Preselected k=6")
    ax.set(xlabel="k", ylabel="Within-cluster sum of squares (inertia)", title="Descriptive elbow plot (training only)")
    ax.legend(); fig.tight_layout(); fig.savefig(dest / "05_elbow.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(result["null_inertia"], bins=18, edgecolor="black")
    ax.axvline(model.inertia_, color="red", linestyle="--", label="Actual historical training draws")
    ax.set(xlabel="K-means inertia, fixed k=6", ylabel="Simulated fair histories", title="Fair-random reference: same number of draws")
    ax.legend(); fig.tight_layout(); fig.savefig(dest / "06_null_inertia.png", dpi=150); plt.close(fig)


def write_report(result: dict, outdir: Path, seed: int) -> None:
    model = result["model"]
    obj = {
        "status": "EXPLORATORY_ONLY_NO_PREDICTION_CLAIM", "game": "Lotto 6/42",
        "train_draws": int(len(result["x"])), "train_date_start": "2016-08-30", "train_date_end": "2022-11-12",
        "validation_rows_read": 0, "locked_test_rows_read": 0, "seed": seed, "k_preselected": 6,
        "representation": "unordered binary 42 indicators, six ones per draw",
        "null_model": "iid fair 6-of-42 sets, KMeans refit to each equal-length history",
        "null_replicates": int(len(result["null_inertia"])),
        "inertia_observed": float(model.inertia_),
        "inertia_null_mean": float(result["null_inertia"].mean()),
        "inertia_null_interval_95_percentile": [float(v) for v in np.quantile(result["null_inertia"], [0.025, 0.975])],
        "empirical_lower_tail_p": float(result["p_lower"]),
        "cluster_sizes": result["cluster_counts"].astype(int).tolist(),
        "descriptive_cluster_medoids_not_predictions": result["medoids"],
        "expected_pair_frequency": result["pair_expected"],
        "observed_number_counts": result["freqs"].tolist(),
        "pca_explained_variance_ratio": result["pca_explained"].tolist(),
        "elbow_inertia": result["elbow"],
    }
    outdir.joinpath("summary.json").write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    interpretation = (
        "The clustering inertia was lower than most fair simulations. This is an "
        "exploratory, model-specific deviation only; it does not establish "
        "future-draw predictability or justify overriding the prior STOP decision."
        if result["p_lower"] <= 0.05 else
        "The clustering inertia was not unusually low relative to fair-draw "
        "simulations in this descriptive screen. The observed clusters should not "
        "be interpreted as predictive patterns."
    )
    text = (
        "# Phase 7: K-means descriptive exploration, Lotto 6/42\n\n"
        "**Status: EXPLORATORY ONLY.** Previous STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL unchanged.\n\n"
        "Dataset: 902 training draws (2016-08-30 through 2022-11-12). "
        "The program reads exactly the first 1003 cleaned records; validation and locked test are not loaded.\n\n"
        f"Fixed k=6, seed={seed}, n_init=5, {len(result['null_inertia'])} fair synthetic histories. "
        f"Actual inertia: {model.inertia_:.3f}; fair-reference mean: {result['null_inertia'].mean():.3f}; "
        f"lower-tail simulation p={(result['p_lower']):.4f}.\n\n"
        f"Interpretation: {interpretation}\n\n"
        "Cluster medoids are historical examples, **not forecasts, probabilities, or suggested wagers**. "
        "PCA projections, frequency deviations, and co-occurrence differences are descriptive. "
        "K-means will form clusters in completely random data as well. The fixed-k inertia comparison "
        "is a single exploratory diagnostic and does not correct for trying multiple representations "
        "or methods. Earlier validation was reused in other project phases, so no new independent "
        "prediction evidence is claimed.\n\n"
        "## Generated charts\n\n"
        "- 01_frequency.png: observed ball counts versus fair expectation\n"
        "- 02_pair_residuals.png: pair co-occurrence count deviations\n"
        "- 03_cluster_profiles.png: per-cluster ball frequencies\n"
        "- 04_cluster_pca.png: PCA view of cluster labels\n"
        "- 05_elbow.png: k=2..8 within-cluster inertia (not model-selection evidence)\n"
        "- 06_null_inertia.png: fixed k=6 against fair-random null\n\n"
        "The locked test is sealed; no inference about next week's draw is warranted.\n"
    )
    outdir.joinpath("README.md").write_text(text, encoding="utf-8")


def run(input_path: Path = Path("lotto_6_42_cleaned_normalized.csv"),
        output_dir: Path = Path("reports/phase7_kmeans_642"),
        null_replicates: int = 100, seed: int = SEED) -> dict:
    train = load_train_only(input_path)
    result = analyze(train, null_replicates=null_replicates, seed=seed)
    make_figures(result, output_dir)
    write_report(result, output_dir, seed)
    return {"summary_path": str(output_dir / "summary.json"),
            "observed_inertia": float(result["model"].inertia_),
            "null_mean_inertia": float(result["null_inertia"].mean()),
            "lower_tail_p": float(result["p_lower"])}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=Path("lotto_6_42_cleaned_normalized.csv"))
    p.add_argument("--output", type=Path, default=Path("reports/phase7_kmeans_642"))
    p.add_argument("--null-replicates", type=int, default=100)
    p.add_argument("--seed", type=int, default=SEED)
    a = p.parse_args()
    print(json.dumps(run(a.input, a.output, a.null_replicates, a.seed), indent=2))
