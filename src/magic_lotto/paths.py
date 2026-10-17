"""Repository-root and compatibility path resolution."""

from __future__ import annotations

# @codebase_provenance_JEO
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LEGACY_REPOSITORY_PATHS = {
    "6-42.csv": "data/raw/6-42.csv",
    "swertres9pm.md": "data/raw/swertres9pm.md",
    "lotto_6_42_cleaned_normalized.csv": "data/processed/lotto_6_42_cleaned_normalized.csv",
    "swertres_9pm_cleaned_normalized.csv": "data/processed/swertres_9pm_cleaned_normalized.csv",
    "swertres_9pm_analysis_ready.csv": "data/processed/swertres_9pm_analysis_ready.csv",
    "lotto_6_42_number_frequency.csv": "data/analysis/phase2/lotto_6_42_number_frequency.csv",
    "lotto_6_42_phase2_analysis.csv": "data/analysis/phase2/lotto_6_42_phase2_analysis.csv",
    "swertres_9pm_digit_frequency.csv": "data/analysis/phase2/swertres_9pm_digit_frequency.csv",
    "swertres_9pm_phase2_analysis.csv": "data/analysis/phase2/swertres_9pm_phase2_analysis.csv",
    "lotto_data_cleaning_report.md": "docs/research/lotto_data_cleaning_report.md",
    "phase2_randomness_diagnostics.md": "docs/research/phase2_randomness_diagnostics.md",
    "monte_carlo_baseline.py": "research/legacy/scripts/monte_carlo_baseline.py",
    "phase3_monte_carlo_random_baseline.md": "docs/research/phase3_monte_carlo_random_baseline.md",
    "phase3_monte_carlo_results.json": "reports/phase3_monte_carlo_results.json",
    "phase3_simulation_distributions.csv": "reports/phase3_simulation_distributions.csv",
}


def repository_path(root: Path, relative_path: str | Path) -> Path:
    """Resolve a current or historical logical path without fallback searches."""
    path = Path(relative_path)
    if path.is_absolute():
        return path
    key = str(relative_path).replace("\\", "/")
    return Path(root) / LEGACY_REPOSITORY_PATHS.get(key, key)
