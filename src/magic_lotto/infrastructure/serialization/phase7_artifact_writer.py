"""Write the existing Phase 7 charts, JSON summary and Markdown report."""

from __future__ import annotations

# @codebase_provenance_JEO
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from magic_lotto.application.ports.phase7_artifact_writer import Phase7ArtifactWriter as Phase7ArtifactWriterPort
from magic_lotto.domain.draw_642 import BALLS, DRAW_SIZE


class Phase7ArtifactWriter(Phase7ArtifactWriterPort):
    def write(self, result: dict, output_dir: Path, seed: int) -> None:
        self._make_figures(result, output_dir)
        self._write_report(result, output_dir, seed)

    @staticmethod
    def _make_figures(result: dict, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        x, model = result["x"], result["model"]
        ball_ticks = np.array([1, 6, 11, 16, 21, 26, 31, 36, 42])
        matrix_ticks = ball_ticks - 1
        fig, ax = plt.subplots(figsize=(11, 4))
        ax.bar(np.arange(1, BALLS + 1), result["freqs"], width=0.8)
        ax.axhline(len(x) * DRAW_SIZE / BALLS, linestyle="--", color="black", label="Fair-model expected frequency")
        ax.set(xlim=(0.5, BALLS + 0.5), xticks=ball_ticks, xlabel="Ball (1 to 42)", ylabel="Training-draw appearances", title="6/42 training-prefix frequency (descriptive)")
        ax.legend()
        fig.tight_layout(); fig.savefig(dest / "01_frequency.png", dpi=150); plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 7))
        residual = result["cooccur"] - result["pair_expected"]
        magnitude = float(np.nanmax(np.abs(residual)))
        image = ax.imshow(np.ma.masked_invalid(residual), cmap="coolwarm", vmin=-magnitude, vmax=magnitude)
        ax.set(xticks=matrix_ticks, xticklabels=ball_ticks, yticks=matrix_ticks, yticklabels=ball_ticks,
               xlabel="Ball (1 to 42)", ylabel="Ball (1 to 42)", title="Pair counts minus fair-model expectation (training)")
        fig.colorbar(image, ax=ax, label="Observed minus expected appearances")
        fig.tight_layout(); fig.savefig(dest / "02_pair_residuals.png", dpi=150); plt.close(fig)

        order = np.argsort(-result["cluster_counts"])
        fig, ax = plt.subplots(figsize=(11, 4))
        image = ax.imshow(model.cluster_centers_[order], aspect="auto", cmap="viridis", vmin=0, vmax=1)
        ax.set(yticks=range(6), yticklabels=[f"Cluster {i + 1} (n={result['cluster_counts'][i]})" for i in order],
               xticks=matrix_ticks, xticklabels=ball_ticks,
               xlabel="Ball (1 to 42)", title="Cluster membership rates among historical training draws")
        fig.colorbar(image, ax=ax, label="Within-cluster share containing ball")
        fig.tight_layout(); fig.savefig(dest / "03_cluster_profiles.png", dpi=150); plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 6))
        scatter = ax.scatter(result["points"][:, 0], result["points"][:, 1], c=model.labels_, cmap="tab10", s=16, alpha=0.68)
        ax.set(xlabel="PCA component 1", ylabel="PCA component 2", title="K-means clusters projected to 2D PCA (illustrative)")
        handles, _ = scatter.legend_elements()
        ax.legend(handles, [f"Cluster {i + 1}" for i in range(len(handles))], title="Cluster")
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

    @staticmethod
    def _write_report(result: dict, outdir: Path, seed: int) -> None:
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
            "inertia_null_interval_95_percentile": [float(value) for value in np.quantile(result["null_inertia"], [0.025, 0.975])],
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
