"""Lightweight shape, reproducibility and partition-guard checks."""
# @codebase_provenance_JEO
from datetime import date, timedelta
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from threadpoolctl import threadpool_info, threadpool_limits
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase7_kmeans_642 import (
    DEFAULT_INPUT,
    TRAIN_COUNT,
    TRAIN_END_SOURCE_ROW,
    TRAIN_PREFIX_ROWS,
    TRAIN_START_SOURCE_ROW,
    encode_draws,
    fair_null_draws,
    load_train_only,
)
from magic_lotto.domain.draw_642 import BALLS, DRAW_COLS, DRAW_SIZE
from magic_lotto.research.kmeans_642 import fit_kmeans


def make_synthetic_training_prefix():
    preceding = list(range(2, 103))
    training = [row for row in range(TRAIN_START_SOURCE_ROW, TRAIN_END_SOURCE_ROW + 1)
                if row not in {200, 300, 400, 990}]
    source_rows = preceding + training
    source_rows[870], source_rows[871] = source_rows[871], source_rows[870]

    start = date(2016, 8, 30)
    end = date(2022, 11, 12)
    span = (end - start).days
    dates = [start - timedelta(days=101 - index) for index in range(len(preceding))]
    dates.extend(start + timedelta(days=(span * index) // (TRAIN_COUNT - 1))
                 for index in range(TRAIN_COUNT))

    rows = []
    for index, (source_row, draw_date) in enumerate(zip(source_rows, dates)):
        numbers = [(index + offset) % BALLS + 1 for offset in range(DRAW_SIZE)]
        rows.append({
            "draw_date": draw_date.isoformat(),
            "source_row": source_row,
            "record_status": "valid",
            **dict(zip(DRAW_COLS, numbers)),
        })
    return pd.DataFrame(rows)


class KMeansExplorationTests(unittest.TestCase):
    def test_default_input_tracks_repository_layout(self):
        self.assertEqual(DEFAULT_INPUT, Path(__file__).resolve().parents[1] / "data/processed/lotto_6_42_cleaned_normalized.csv")

    def test_binary_encoding_indifferent_to_ball_order(self):
        a = encode_draws(np.array([[1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1]]))
        self.assertEqual(a.shape, (2, 42))
        np.testing.assert_array_equal(a[0], a[1])
        self.assertEqual(a[0].sum(), 6)

    def test_invalid_combination_rejected(self):
        for values in ([1, 1, 2, 3, 4, 5], [0, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 43]):
            with self.assertRaises(ValueError):
                encode_draws(np.array([values]))

    def test_noninteger_and_nonfinite_numbers_rejected(self):
        for values in (
            [1.5, 2, 3, 4, 5, 6],
            [np.nan, 2, 3, 4, 5, 6],
            [np.inf, 2, 3, 4, 5, 6],
        ):
            with self.assertRaises(ValueError):
                encode_draws(np.array([values]))

    def test_fair_null_unique_and_deterministic(self):
        a = fair_null_draws(40, np.random.default_rng(162))
        np.testing.assert_array_equal(a, fair_null_draws(40, np.random.default_rng(162)))
        self.assertTrue(np.all(np.diff(np.sort(a, axis=1), axis=1) > 0))

    def test_seeded_kmeans_uses_single_native_thread_and_is_repeatable(self):
        # Synthetic draws only: no validation or locked-test data is read.
        rng = np.random.default_rng(53)
        draws = np.array(
            [rng.choice(np.arange(1, 43), size=6, replace=False) for _ in range(90)]
        )
        encoded = encode_draws(draws)
        observed_threads = []
        original_fit = KMeans.fit

        def observe_fit(estimator, values, *args, **kwargs):
            counts = [
                library["num_threads"]
                for library in threadpool_info()
                if library.get("user_api") in ("blas", "openmp")
            ]
            observed_threads.append(counts)
            return original_fit(estimator, values, *args, **kwargs)

        # Simulate a multi-threaded host; the fit must override it locally.
        with patch("magic_lotto.research.kmeans_642.KMeans.fit", new=observe_fit):
            with threadpool_limits(limits=4):
                first = fit_kmeans(encoded, k=4, seed=162)
                second = fit_kmeans(encoded, k=4, seed=162)

        self.assertTrue(observed_threads, "Native thread limit was not inspected")
        self.assertTrue(all(counts and all(n == 1 for n in counts)
                            for counts in observed_threads))
        self.assertEqual(first.inertia_, second.inertia_)
        np.testing.assert_array_equal(first.labels_, second.labels_)

    def test_rejects_synthetic_prefix_with_changed_boundary(self):
        prefix = make_synthetic_training_prefix()
        prefix.loc[prefix.index[-1], "source_row"] = TRAIN_END_SOURCE_ROW + 1
        with TemporaryDirectory() as p:
            csv = Path(p) / "synthetic.csv"
            prefix.to_csv(csv, index=False)
            with open(csv, "a", encoding="utf-8") as f:
                f.write("malformed synthetic suffix after the training prefix\n")
            with self.assertRaisesRegex(ValueError, "Training boundary changed"):
                load_train_only(csv)

    def test_synthetic_adjacent_source_row_inversion_is_provenance_only(self):
        prefix = make_synthetic_training_prefix()
        self.assertEqual(len(prefix), TRAIN_PREFIX_ROWS)
        self.assertEqual(prefix.loc[:100, "source_row"].tolist(), list(range(2, 103)))
        self.assertEqual(prefix.loc[870:871, "source_row"].tolist(), [876, 875])
        self.assertFalse(prefix["source_row"].is_monotonic_increasing)

        with TemporaryDirectory() as p:
            csv = Path(p) / "prefix.csv"
            prefix.to_csv(csv, index=False)
            with open(csv, "a", encoding="utf-8") as f:
                f.write("malformed validation and locked-test suffix\n")
            train = load_train_only(csv)

        self.assertEqual(len(train), TRAIN_COUNT)
        self.assertFalse(train["source_row"].duplicated().any())
        self.assertEqual(int(train["source_row"].min()), TRAIN_START_SOURCE_ROW)
        self.assertEqual(int(train["source_row"].max()), TRAIN_END_SOURCE_ROW)
        self.assertEqual(len(train), 902)
        self.assertEqual(
            sorted(train["source_row"].tolist()),
            [row for row in range(TRAIN_START_SOURCE_ROW, TRAIN_END_SOURCE_ROW + 1)
             if row not in {200, 300, 400, 990}],
        )
        self.assertTrue((train["record_status"] == "valid").all())
        self.assertTrue(train["draw_date"].is_monotonic_increasing)
        self.assertFalse(train["source_row"].is_monotonic_increasing)
        self.assertEqual(train["draw_date"].iloc[0], "2016-08-30")
        self.assertEqual(train["draw_date"].iloc[-1], "2022-11-12")

    def test_synthetic_duplicate_source_row_still_rejected(self):
        prefix = make_synthetic_training_prefix()
        prefix.loc[871, "source_row"] = prefix.loc[870, "source_row"]
        with TemporaryDirectory() as p:
            csv = Path(p) / "duplicate-source-row.csv"
            prefix.to_csv(csv, index=False)
            with self.assertRaisesRegex(ValueError, "Duplicate source_row"):
                load_train_only(csv)


if __name__ == "__main__":
    unittest.main()
