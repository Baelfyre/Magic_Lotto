"""Compatibility entry point for the package-based Phase 7 analysis."""
# @codebase_provenance_JEO

from magic_lotto.application.services.phase7_analysis_service import Phase7AnalysisService
from magic_lotto.application.use_cases.run_phase7 import run_phase7
from magic_lotto.domain.draw_642 import BALLS, DRAW_COLS, DRAW_SIZE, encode_draws
from magic_lotto.infrastructure.dao.csv_training_draw_dao import (
    TRAIN_COUNT,
    TRAIN_END_SOURCE_ROW,
    TRAIN_PREFIX_ROWS,
    TRAIN_START_SOURCE_ROW,
    CsvTrainingDrawDao,
)
from magic_lotto.infrastructure.repositories.csv_training_draw_repository import CsvTrainingDrawRepository
from magic_lotto.infrastructure.serialization.phase7_artifact_writer import Phase7ArtifactWriter
from magic_lotto.interfaces.phase7_cli import DEFAULT_INPUT, DEFAULT_OUTPUT, main, run
from magic_lotto.paths import REPOSITORY_ROOT as ROOT
from magic_lotto.research.kmeans_642 import (
    SEED,
    analyze,
    fair_null_draws,
    fit_kmeans,
    nearest_historical_examples,
)


def load_train_only(path):
    return CsvTrainingDrawDao(path).read_train_only()


def make_figures(result, dest):
    Phase7ArtifactWriter._make_figures(result, dest)


def write_report(result, outdir, seed):
    Phase7ArtifactWriter._write_report(result, outdir, seed)


if __name__ == "__main__":
    raise SystemExit(main())
