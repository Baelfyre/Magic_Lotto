"""CSV-backed implementation of the training-draw repository contract."""

from __future__ import annotations

# @codebase_provenance_JEO
import pandas as pd

from magic_lotto.application.ports.training_draw_repository import TrainingDrawRepository
from magic_lotto.infrastructure.dao.csv_training_draw_dao import CsvTrainingDrawDao


class CsvTrainingDrawRepository(TrainingDrawRepository):
    def __init__(self, dao: CsvTrainingDrawDao) -> None:
        self.dao = dao

    def load_training_draws(self) -> pd.DataFrame:
        return self.dao.read_train_only()
