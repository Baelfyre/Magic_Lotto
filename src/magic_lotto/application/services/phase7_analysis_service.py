"""Orchestrate the established train-only Phase 7 descriptive analysis."""

from __future__ import annotations

# @codebase_provenance_JEO
from magic_lotto.application.ports.training_draw_repository import TrainingDrawRepository
from magic_lotto.research.kmeans_642 import SEED, analyze


class Phase7AnalysisService:
    def __init__(self, repository: TrainingDrawRepository) -> None:
        self.repository = repository

    def run(self, null_replicates: int = 100, seed: int = SEED) -> dict:
        return analyze(self.repository.load_training_draws(), null_replicates, seed)
