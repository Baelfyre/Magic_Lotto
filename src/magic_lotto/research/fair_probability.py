"""Exact fair-draw mathematics for unordered six-of-42 combinations.

These are mathematical baselines under fair, independent draws, never
predictions or model-based estimates of winning chances.
"""

from __future__ import annotations

# @codebase_provenance_JEO

from fractions import Fraction
from math import comb

from magic_lotto.domain.combination_642 import BALL_COUNT, LINE_SIZE, validate_combination


TOTAL_COMBINATIONS = comb(BALL_COUNT, LINE_SIZE)


def fair_exact_match_probability() -> Fraction:
    """Chance a specified valid line exactly matches one fair draw."""
    return Fraction(1, TOTAL_COMBINATIONS)


def match_count_numerator(matches: int) -> int:
    """Number of combinations sharing exactly ``matches`` balls with a line."""
    if type(matches) is not int or not 0 <= matches <= LINE_SIZE:
        raise ValueError("Match count must be an integer from 0 to 6")
    return comb(LINE_SIZE, matches) * comb(BALL_COUNT - LINE_SIZE, LINE_SIZE - matches)


def match_count_pmf(matches: int) -> Fraction:
    return Fraction(match_count_numerator(matches), TOTAL_COMBINATIONS)


def expected_match_count() -> Fraction:
    return sum((matches * match_count_pmf(matches) for matches in range(7)), Fraction())


def jackpot_probability_for_batch(size: int, *, distinct_sets: bool = False) -> Fraction:
    """At-least-one exact match for fixed lines vs one independent fair draw.

    ``distinct_sets=False`` assumes iid uniform lines drawn *with* replacement.
    ``distinct_sets=True`` assumes a uniform batch of distinct lines. The batch
    distribution differs; neither option changes any one line's fair-draw odds.
    """
    if type(size) is not int or not 0 <= size <= TOTAL_COMBINATIONS:
        raise ValueError("Line count must be between 0 and C(42,6)")
    if distinct_sets:
        return Fraction(size, TOTAL_COMBINATIONS)
    return Fraction(1) - Fraction(TOTAL_COMBINATIONS - 1, TOTAL_COMBINATIONS) ** size


def jaccard_distance_from_overlap(overlap: int) -> Fraction:
    """Exact Jaccard distance for two valid six-ball sets."""
    if type(overlap) is not int or not 0 <= overlap <= LINE_SIZE:
        raise ValueError("Overlap must be an integer from 0 to 6")
    return Fraction(12 - 2 * overlap, 12 - overlap)


def jaccard_distance(first: tuple[int, ...], second: tuple[int, ...]) -> Fraction:
    a, b = validate_combination(first), validate_combination(second)
    return jaccard_distance_from_overlap(len(set(a).intersection(b)))
