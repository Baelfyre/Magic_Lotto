"""Existing descriptive K-means calculations for Lotto 6/42 training draws."""

from __future__ import annotations

# @codebase_provenance_JEO
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from magic_lotto.domain.draw_642 import BALLS, DRAW_COLS, DRAW_SIZE, encode_draws


SEED = 162
def fair_null_draws(n: int, rng: np.random.Generator) -> np.ndarray:
    """Uniformly sample independent 6-of-42 sets without replacement."""
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
    model = fit_kmeans(x, k=6, seed=seed)
    counts = np.bincount(model.labels_, minlength=6)
    rng = np.random.default_rng(seed)
    null_inertia = np.empty(null_replicates)
    for index in range(null_replicates):
        null_x = encode_draws(fair_null_draws(len(x), rng))
        null_inertia[index] = fit_kmeans(null_x, k=6, seed=seed + index + 1).inertia_
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
