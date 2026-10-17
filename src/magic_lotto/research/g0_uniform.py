"""Unbiased G0 uniform generation, with cryptographic runtime randomness.

The default source is secrets.randbelow (rejection-sampled bounded integers).
Tests may inject a deterministic callable, but runtime generation does not
claim replayability. No historical data, model fitting, or IO is used.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import comb
from secrets import randbelow as crypto_randbelow

from magic_lotto.domain.combination_642 import (
    BALL_COUNT, GAME_ID, LINE_SCHEMA_VERSION, LINE_SIZE, validate_combination,
)
from magic_lotto.research.fair_probability import TOTAL_COMBINATIONS


INDEPENDENT_WITH_REPLACEMENT = "independent_with_replacement"
DISTINCT_SETS = "distinct_sets"
MAX_BATCH_SIZE = 100  # Phase 8A bounded API policy; revisit before Phase 8C UX approval.
RandBelow = Callable[[int], int]


def bounded_integer(upper: int, randbelow: RandBelow) -> int:
    """Reject an incorrect injected RNG instead of silently biasing output."""
    if type(upper) is not int or upper <= 0:
        raise ValueError("Upper bound must be a positive integer")
    value = randbelow(upper)
    if type(value) is not int or not 0 <= value < upper:
        raise ValueError("Random source returned an invalid bounded integer")
    return value


def uniform_subset(population: int, count: int, randbelow: RandBelow) -> tuple[int, ...]:
    """Uniformly sample an unordered k-subset via partial Fisher-Yates.

    General form is exposed for exhaustive small-universe correctness tests.
    G0 itself always calls this with population=42 and count=6.
    """
    if (type(population) is not int or type(count) is not int
            or population <= 0 or not 0 <= count <= population):
        raise ValueError("Invalid population or subset size")
    values = list(range(1, population + 1))
    for i in range(count):
        j = i + bounded_integer(population - i, randbelow)
        values[i], values[j] = values[j], values[i]
    return tuple(sorted(values[:count]))


def unrank_subset(rank: int, population: int = BALL_COUNT, count: int = LINE_SIZE) -> tuple[int, ...]:
    """Unrank an unordered subset in ascending lexicographic order."""
    if (type(population) is not int or type(count) is not int
            or population < 0 or count < 0 or count > population):
        raise ValueError("Invalid subset universe")
    if type(rank) is not int or not 0 <= rank < comb(population, count):
        raise ValueError("Combination rank outside universe")
    result: list[int] = []
    minimum = 1
    for remaining in range(count, 0, -1):
        for ball in range(minimum, population - remaining + 2):
            block = comb(population - ball, remaining - 1)
            if rank < block:
                result.append(ball)
                minimum = ball + 1
                break
            rank -= block
        else:
            raise AssertionError("Combination unranking invariant violated")
    return tuple(result)


def distinct_uniform_ranks(universe_size: int, count: int, randbelow: RandBelow) -> tuple[int, ...]:
    """Select uniformly distributed ordered distinct ranks using sparse swaps.

    This is a partial Fisher-Yates permutation over rank indices. It does not
    need to allocate a list of all 5,245,786 possible lines.
    """
    if (type(universe_size) is not int or type(count) is not int
            or universe_size < 1 or not 0 <= count <= universe_size):
        raise ValueError("Invalid universe size or distinct rank count")
    swaps: dict[int, int] = {}
    selected: list[int] = []
    for i in range(count):
        remaining = universe_size - i
        picked = bounded_integer(remaining, randbelow)
        selected.append(swaps.get(picked, picked))
        swaps[picked] = swaps.get(remaining - 1, remaining - 1)
    if len(set(selected)) != count:
        raise AssertionError("Distinct rank sampler repeated a rank")
    return tuple(selected)


def validate_batch_size(batch_size: int) -> int:
    if type(batch_size) is not int or not 1 <= batch_size <= MAX_BATCH_SIZE:
        raise ValueError(f"Batch size must be an integer from 1 to {MAX_BATCH_SIZE}")
    return batch_size


@dataclass(frozen=True, slots=True)
class G0GenerationResult:
    """Transient G0 result, NOT a registered or persisted research batch."""

    lines: tuple[tuple[int, ...], ...]
    sampling_mode: str
    schema_version: str = LINE_SCHEMA_VERSION
    game_id: str = GAME_ID
    algorithm_id: str = "G0"
    sampler_contract_version: str = "g0-uniform-v1"

    def __post_init__(self) -> None:
        if self.sampling_mode not in (INDEPENDENT_WITH_REPLACEMENT, DISTINCT_SETS):
            raise ValueError("Unsupported sampling mode")
        if self.game_id != GAME_ID or self.algorithm_id != "G0":
            raise ValueError("Only G0 Lotto 6/42 is supported")
        validate_batch_size(len(self.lines))
        for line in self.lines:
            if validate_combination(line) != line:
                raise ValueError("Result lines must be sorted")
        if self.sampling_mode == DISTINCT_SETS and len(set(self.lines)) != len(self.lines):
            raise ValueError("Distinct mode produced duplicate lines")

    def to_dict(self) -> dict:
        """Schema-labelled transient value; callers must not persist visitor lines."""
        return {
            "schema_version": self.schema_version,
            "game_id": self.game_id,
            "algorithm_id": self.algorithm_id,
            "sampler_contract_version": self.sampler_contract_version,
            "sampling_mode": self.sampling_mode,
            "line_count": len(self.lines),
            "ticket_lines": [list(line) for line in self.lines],
        }


def generate_g0(
    batch_size: int = 1,
    *,
    sampling_mode: str = INDEPENDENT_WITH_REPLACEMENT,
    random_source: RandBelow | None = None,
    game_id: str = GAME_ID,
) -> G0GenerationResult:
    """Generate valid 6/42 lines uniformly, using secrets by default.

    Independent mode samples each line iid and permits repeated full lines.
    Distinct mode selects unique ranks, then un-ranks their combinations;
    those lines are not independently sampled.
    """
    if game_id != GAME_ID:
        raise ValueError("Only Philippine Lotto 6/42 is supported")
    size = validate_batch_size(batch_size)
    if sampling_mode not in (INDEPENDENT_WITH_REPLACEMENT, DISTINCT_SETS):
        raise ValueError("Unsupported sampling mode")
    source = crypto_randbelow if random_source is None else random_source
    if not callable(source):
        raise TypeError("Random source must implement randbelow(upper)")
    if sampling_mode == INDEPENDENT_WITH_REPLACEMENT:
        lines = tuple(uniform_subset(BALL_COUNT, LINE_SIZE, source) for _ in range(size))
    else:
        ranks = distinct_uniform_ranks(TOTAL_COMBINATIONS, size, source)
        lines = tuple(unrank_subset(rank) for rank in ranks)
    return G0GenerationResult(lines, sampling_mode)
