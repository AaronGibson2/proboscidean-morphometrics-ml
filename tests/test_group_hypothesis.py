import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_dinov3_group_hypothesis import exact_group_test


class GroupHypothesisTests(unittest.TestCase):
    def test_exact_enumeration_counts_observed_and_complement(self):
        features = np.array([[1, 0], [1, .01], [0, 1], [.01, 1]])
        result = exact_group_test(features, ["A", "A", "B", "B"])
        self.assertEqual(result["assignments"], 6)
        self.assertEqual(result["macro_recall"], 1)
        self.assertAlmostEqual(result["exact_p"], 2/6)
        self.assertTrue(all(i != j for i, j in enumerate(result["nearest_indices"])))

    def test_imbalanced_groups_have_equal_weight(self):
        features = np.array([[1, 0], [1, .01], [1, .02], [1, .03], [1, -.03], [1, .10]])
        result = exact_group_test(features, ["A"]*4 + ["B"]*2)
        self.assertEqual(result["macro_recall"], .5)
        self.assertAlmostEqual(result["accuracy"], 4/6)
        self.assertEqual(result["assignments"], 15)

    def test_unsupported_groups_are_rejected(self):
        with self.assertRaises(ValueError):
            exact_group_test(np.eye(3), ["A", "A", "B"])


if __name__ == "__main__":
    unittest.main()
