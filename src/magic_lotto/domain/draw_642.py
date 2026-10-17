"""Lotto 6/42 combination invariants and unordered binary encoding."""

from __future__ import annotations

# @codebase_provenance_JEO
import numpy as np


BALLS = 42
DRAW_SIZE = 6
DRAW_COLS = [f"number_{index}" for index in range(1, DRAW_SIZE + 1)]


def encode_draws(numbers: np.ndarray) -> np.ndarray:
    """Represent valid unordered six-number combinations as 42 indicators."""
    try:
        values = np.asarray(numbers, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError("Expected numeric six-number combinations") from error
    if values.ndim != 2 or values.shape[1] != DRAW_SIZE:
        raise ValueError("Expected a matrix with six columns")
    if not np.isfinite(values).all() or np.any(values != np.floor(values)):
        raise ValueError("Draw values must be finite integers")
    if np.any((values < 1) | (values > BALLS)) or np.any(np.diff(np.sort(values, axis=1), axis=1) == 0):
        raise ValueError("Invalid six-number combination")
    integer_values = values.astype(int)
    encoded = np.zeros((len(integer_values), BALLS), dtype=np.float64)
    encoded[np.arange(len(integer_values))[:, None], integer_values - 1] = 1.0
    if not np.all(encoded.sum(axis=1) == DRAW_SIZE):
        raise AssertionError("One-hot representation must have exactly six ones")
    return encoded
