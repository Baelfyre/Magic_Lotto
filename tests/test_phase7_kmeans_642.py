"""Lightweight shape, reproducibility and partition-guard checks."""
# @codebase_provenance_JEO
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import numpy as np
import pandas as pd
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

    def test_refuses_bad_training_prefix_without_touching_suffix(self):
        with TemporaryDirectory() as p:
            csv = Path(p) / "synthetic.csv"
            cols = ["draw_date", "source_row", "record_status"] + [f"number_{i}" for i in range(1, 7)]
            data = [["2016-01-01", i, "valid", 1, 2, 3, 4, 5, 6] for i in range(2, 1005)]
            pd.DataFrame(data, columns=cols).to_csv(csv, index=False)
            with open(csv, "a", encoding="utf-8") as f:
                f.write("not,a,valid,row,with,broken,columns,after,limit\n")
            with self.assertRaisesRegex(ValueError, "Training boundary changed"):
                load_train_only(csv)

    def test_adjacent_source_row_inversion_is_provenance_only(self):
        source = Path(__file__).resolve().parents[1] / "data/processed/lotto_6_42_cleaned_normalized.csv"
        prefix = pd.read_csv(source, nrows=TRAIN_PREFIX_ROWS)
        self.assertEqual(prefix.loc[870:871, "source_row"].tolist(), [876, 875])

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
        self.assertTrue(train["draw_date"].is_monotonic_increasing)
        self.assertEqual(train["draw_date"].iloc[0], "2016-08-30")
        self.assertEqual(train["draw_date"].iloc[-1], "2022-11-12")

    def test_duplicate_source_row_still_rejected(self):
        source = Path(__file__).resolve().parents[1] / "data/processed/lotto_6_42_cleaned_normalized.csv"
        prefix = pd.read_csv(source, nrows=TRAIN_PREFIX_ROWS)
        prefix.loc[871, "source_row"] = prefix.loc[870, "source_row"]
        with TemporaryDirectory() as p:
            csv = Path(p) / "duplicate-source-row.csv"
            prefix.to_csv(csv, index=False)
            with self.assertRaisesRegex(ValueError, "Duplicate source_row"):
                load_train_only(csv)


if __name__ == "__main__":
    unittest.main()
