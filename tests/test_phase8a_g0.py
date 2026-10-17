"""Phase 8A: no historical, validation, or locked-test data are opened."""

from __future__ import annotations

import itertools
import json
import unittest
from collections import Counter
from fractions import Fraction
from math import comb
from pathlib import Path
from unittest.mock import patch

from magic_lotto.application.use_cases.generate_g0 import generate_g0_lines
from magic_lotto.domain.combination_642 import Combination642, validate_combination
from magic_lotto.research.fair_probability import (
    TOTAL_COMBINATIONS, expected_match_count, fair_exact_match_probability,
    jackpot_probability_for_batch, jaccard_distance, jaccard_distance_from_overlap,
    match_count_numerator, match_count_pmf,
)
from magic_lotto.research.g0_uniform import (
    DISTINCT_SETS, INDEPENDENT_WITH_REPLACEMENT, G0GenerationResult,
    bounded_integer, distinct_uniform_ranks, generate_g0, uniform_subset,
    unrank_subset, validate_batch_size,
)


class SequenceRng:
    def __init__(self, values):
        self.it = iter(values)

    def __call__(self, upper):
        return next(self.it)


class Phase8AMathTests(unittest.TestCase):
    def test_combination_count_and_exact_match_probability(self):
        self.assertEqual(TOTAL_COMBINATIONS, 5_245_786)
        self.assertEqual(fair_exact_match_probability(), Fraction(1, 5_245_786))

    def test_exact_pmf_and_expectation(self):
        numerators = [1947792, 2261952, 883575, 142800, 9450, 216, 1]
        self.assertEqual([match_count_numerator(i) for i in range(7)], numerators)
        self.assertEqual(sum(numerators), TOTAL_COMBINATIONS)
        self.assertEqual(sum((match_count_pmf(i) for i in range(7)), Fraction()), Fraction(1))
        self.assertEqual(expected_match_count(), Fraction(6, 7))
        for bad in (-1, 7, True, 1.0, "3"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                match_count_pmf(bad)

    def test_jaccard_distance_formula_and_input_validation(self):
        expected = [Fraction(1), Fraction(10, 11), Fraction(4, 5),
                    Fraction(2, 3), Fraction(1, 2), Fraction(2, 7), Fraction(0)]
        self.assertEqual([jaccard_distance_from_overlap(i) for i in range(7)], expected)
        self.assertEqual(jaccard_distance((6, 4, 2, 1, 5, 3), (1, 2, 3, 4, 5, 6)), 0)
        self.assertEqual(jaccard_distance((1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12)), 1)
        for bad in (-1, 7, 0.5, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                jaccard_distance_from_overlap(bad)

    def test_batch_jackpot_probabilities_have_distinct_semantics(self):
        self.assertEqual(jackpot_probability_for_batch(0), 0)
        self.assertEqual(jackpot_probability_for_batch(1), Fraction(1, TOTAL_COMBINATIONS))
        self.assertEqual(jackpot_probability_for_batch(2, distinct_sets=True), Fraction(2, TOTAL_COMBINATIONS))
        self.assertEqual(jackpot_probability_for_batch(2),
                         Fraction(1) - Fraction(TOTAL_COMBINATIONS - 1, TOTAL_COMBINATIONS) ** 2)
        self.assertEqual(jackpot_probability_for_batch(TOTAL_COMBINATIONS, distinct_sets=True), 1)
        for bad in (True, -1, TOTAL_COMBINATIONS + 1, 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                jackpot_probability_for_batch(bad)


class Phase8ADomainTests(unittest.TestCase):
    def test_line_is_sorted_and_immutable(self):
        combo = Combination642((42, 6, 25, 1, 11, 19))
        self.assertEqual(combo.numbers, (1, 6, 11, 19, 25, 42))
        with self.assertRaises(Exception):
            combo.numbers = (1, 2, 3, 4, 5, 6)

    def test_invalid_inputs_and_other_games_fail_closed(self):
        for invalid in (
            (), (1, 2, 3, 4, 5), (1, 2, 3, 4, 5, 5),
            (0, 2, 3, 4, 5, 6), (1, 2, 3, 4, 5, 43),
            (1, 2, 3, 4, 5, 6.0), (True, 2, 3, 4, 5, 6),
            (1, 2, 3, 4, 5, "6"), "123456", None,
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_combination(invalid)
        with self.assertRaises(ValueError):
            validate_combination((1, 2, 3, 4, 5, 6), game_id="3d-lotto")


class Phase8ASamplingTests(unittest.TestCase):
    def test_toy_universe_all_rng_paths_are_exactly_uniform(self):
        # Draws 2 of 4. Each of the 12 index paths is equally likely.
        counts = Counter()
        for first in range(4):
            for second in range(3):
                counts[uniform_subset(4, 2, SequenceRng([first, second]))] += 1
        self.assertEqual(len(counts), comb(4, 2))
        self.assertEqual(set(counts.values()), {2})

    def test_unrank_bijection_toy_universes(self):
        for population, count in ((4, 2), (6, 3), (7, 0), (7, 7)):
            all_subsets = list(itertools.combinations(range(1, population + 1), count))
            self.assertEqual([unrank_subset(rank, population, count)
                              for rank in range(len(all_subsets))], all_subsets)

    def test_distinct_uniform_rank_paths_are_exactly_uniform(self):
        # Select 2 of 4 ranks. All 12 ordered rank pairs are equally likely.
        counts = Counter()
        for first in range(4):
            for second in range(3):
                ranks = distinct_uniform_ranks(4, 2, SequenceRng([first, second]))
                self.assertEqual(len(set(ranks)), 2)
                counts[ranks] += 1
        self.assertEqual(len(counts), 12)
        self.assertEqual(set(counts.values()), {1})

    def test_rng_bounded_integer_validation(self):
        for value in (-1, 3, True, 0.1, "0"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bounded_integer(3, lambda upper: value)
        self.assertEqual(bounded_integer(3, lambda upper: 2), 2)

    def test_independent_mode_allows_repeated_lines(self):
        # Selecting index 0 at each partial swap generates (1..6).
        result = generate_g0(3, random_source=lambda upper: 0)
        self.assertEqual(result.sampling_mode, INDEPENDENT_WITH_REPLACEMENT)
        self.assertEqual(result.lines, ((1, 2, 3, 4, 5, 6),) * 3)

    def test_distinct_mode_yields_distinct_complete_lines(self):
        result = generate_g0(100, sampling_mode=DISTINCT_SETS)
        self.assertEqual(len(result.lines), 100)
        self.assertEqual(len(set(result.lines)), 100)
        self.assertEqual(result.algorithm_id, "G0")
        for line in result.lines:
            self.assertEqual(line, validate_combination(line))

    def test_default_crypto_source_and_schema_label(self):
        result = generate_g0_lines(3)
        self.assertIsInstance(result, G0GenerationResult)
        self.assertEqual(result.game_id, "lotto-6-42")
        self.assertEqual(result.schema_version, "1.0")
        body = result.to_dict()
        self.assertEqual(body["line_count"], 3)
        self.assertEqual(body["algorithm_id"], "G0")
        self.assertEqual(len(body["ticket_lines"]), 3)
        self.assertEqual(json.loads(json.dumps(body)), body)

    def test_batch_size_and_invalid_modes_rejected(self):
        for bad in (0, -1, 101, True, 1.0, "3", None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_batch_size(bad)
        for args in ({"sampling_mode": "G1"}, {"sampling_mode": "G2"},
                     {"sampling_mode": "biased"}, {"game_id": "3d-lotto"}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                generate_g0(1, **args)

    def test_no_filesystem_or_network_needed_for_generation(self):
        # No training dataset or locked suffix should be opened by Phase 8A.
        with patch("builtins.open", side_effect=AssertionError("unexpected file IO")), \
                patch.object(Path, "open", side_effect=AssertionError("unexpected Path IO")):
            result = generate_g0(2)
            self.assertEqual(len(result.lines), 2)
            self.assertEqual(match_count_numerator(6), 1)


if __name__ == "__main__":
    unittest.main()
