"""Training-draw repository contract used by the Phase 7 analysis service."""

from __future__ import annotations

# @codebase_provenance_JEO
from typing import Protocol

import pandas as pd


class TrainingDrawRepository(Protocol):
    def load_training_draws(self) -> pd.DataFrame:
        """Return only the established Phase 7 training partition."""
