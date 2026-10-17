"""Command-line entry point for the existing Phase 7 descriptive analysis."""

from __future__ import annotations

# @codebase_provenance_JEO
import argparse
import json
from pathlib import Path

from magic_lotto.application.services.phase7_analysis_service import Phase7AnalysisService
from magic_lotto.application.use_cases.run_phase7 import run_phase7
from magic_lotto.infrastructure.dao.csv_training_draw_dao import CsvTrainingDrawDao
from magic_lotto.infrastructure.repositories.csv_training_draw_repository import CsvTrainingDrawRepository
from magic_lotto.infrastructure.serialization.phase7_artifact_writer import Phase7ArtifactWriter
from magic_lotto.paths import REPOSITORY_ROOT
from magic_lotto.research.kmeans_642 import SEED


DEFAULT_INPUT = REPOSITORY_ROOT / "data/processed/lotto_6_42_cleaned_normalized.csv"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "reports/phase7_kmeans_642"


def run(input_path: Path = DEFAULT_INPUT, output_dir: Path = DEFAULT_OUTPUT,
        null_replicates: int = 100, seed: int = SEED) -> dict:
    repository = CsvTrainingDrawRepository(CsvTrainingDrawDao(input_path))
    return run_phase7(
        Phase7AnalysisService(repository), Phase7ArtifactWriter(), output_dir,
        null_replicates=null_replicates, seed=seed,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--null-replicates", type=int, default=100)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.input, args.output, args.null_replicates, args.seed), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
