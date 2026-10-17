"""CSV reader enforcing the existing Phase 7 train-only boundary."""

from __future__ import annotations

# @codebase_provenance_JEO
from pathlib import Path

import numpy as np
import pandas as pd

from magic_lotto.domain.draw_642 import BALLS, DRAW_COLS, encode_draws


TRAIN_PREFIX_ROWS = 1003
TRAIN_COUNT = 902
TRAIN_START_SOURCE_ROW = 103
TRAIN_END_SOURCE_ROW = 1008
class CsvTrainingDrawDao:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def read_train_only(self) -> pd.DataFrame:
        """Read only the fixed prefix and validate the established train rows."""
        frame = pd.read_csv(self.path, nrows=TRAIN_PREFIX_ROWS)
        if len(frame) != TRAIN_PREFIX_ROWS:
            raise ValueError("Training prefix truncated; refusing to continue")
        needed = set(DRAW_COLS + ["draw_date", "source_row", "record_status"])
        if not needed.issubset(frame.columns):
            raise ValueError(f"Missing columns: {sorted(needed - set(frame.columns))}")
        if int(frame.iloc[-1]["source_row"]) != TRAIN_END_SOURCE_ROW:
            raise ValueError("Training boundary changed; refusing to continue")
        if frame["source_row"].duplicated().any():
            raise ValueError("Duplicate source_row")
        train = frame.loc[
            frame["source_row"].between(TRAIN_START_SOURCE_ROW, TRAIN_END_SOURCE_ROW)
        ].copy()
        if len(train) != TRAIN_COUNT or (train["record_status"] != "valid").any():
            raise ValueError("Training partition does not match Phase 4")
        if train["draw_date"].iloc[0] != "2016-08-30" or train["draw_date"].iloc[-1] != "2022-11-12":
            raise ValueError("Training date boundaries changed")
        if not train["draw_date"].is_monotonic_increasing:
            raise ValueError("Training dates not ordered")
        values = train[DRAW_COLS].to_numpy(dtype=float)
        if not np.isfinite(values).all() or np.any(values != np.floor(values)):
            raise ValueError("Invalid non-integer or nonfinite number")
        numbers = values.astype(int)
        if np.any((numbers < 1) | (numbers > BALLS)):
            raise ValueError("Draw with out-of-range balls")
        encode_draws(numbers)
        return train
