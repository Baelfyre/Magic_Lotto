"""Lightweight shape, reproducibility and partition-guard checks."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase7_kmeans_642 import encode_draws, fair_null_draws, load_train_only


class KMeansExplorationTests(unittest.TestCase):
    def test_binary_encoding_indifferent_to_ball_order(self):
        a = encode_draws(np.array([[1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1]]))
        self.assertEqual(a.shape, (2, 42))
        np.testing.assert_array_equal(a[0], a[1])
        self.assertEqual(a[0].sum(), 6)

    def test_invalid_combination_rejected(self):
        for values in ([1, 1, 2, 3, 4, 5], [0, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 43]):
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


if __name__ == "__main__":
    unittest.main()
