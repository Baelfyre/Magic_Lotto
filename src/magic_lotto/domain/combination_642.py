"""Validated, immutable representations of Philippine Lotto 6/42 lines.

A combination is an unordered set. Canonical serialization uses ascending order.
This module performs no IO and does not reference historical result partitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


GAME_ID = "lotto-6-42"
BALL_COUNT = 42
LINE_SIZE = 6
LINE_SCHEMA_VERSION = "1.0"


def validate_combination(values: Sequence[int], *, game_id: str = GAME_ID) -> tuple[int, ...]:
    """Return a sorted Lotto 6/42 line; reject all invalid or coerced inputs.

    Exactly six built-in Python integers are required. Boolean, floats, text,
    duplicate/out-of-range values and other lottery games are rejected.
    """
    if game_id != GAME_ID:
        raise ValueError("Only Philippine Lotto 6/42 is supported")
    if not isinstance(values, (tuple, list)) or len(values) != LINE_SIZE:
        raise ValueError("A Lotto 6/42 line must contain exactly six integers")
    if any(type(value) is not int for value in values):
        raise ValueError("Ball values must be integers (not bool or floats)")
    if any(not 1 <= value <= BALL_COUNT for value in values):
        raise ValueError("Ball values must be between 1 and 42")
    if len(set(values)) != LINE_SIZE:
        raise ValueError("A Lotto 6/42 line may not repeat a ball")
    return tuple(sorted(values))


@dataclass(frozen=True, slots=True)
class Combination642:
    """Canonical six-ball value object (no source/draw provenance)."""

    numbers: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "numbers", validate_combination(self.numbers))
