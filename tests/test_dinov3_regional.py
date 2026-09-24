import itertools
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from dinov3_regional import (compare_regions, exact_retrieval, label_assignments,
                             mutual_matches, regional_features, specimen_similarity)


class RegionalTests(unittest.TestCase):
    def region(self, reverse=False):
        # Three separated anatomical surrogates along a horizontal geometric axis.
        tokens = np.repeat(np.eye(3), 2, axis=0)
        if reverse:
            tokens = tokens[::-1]
        return regional_features(tokens, np.ones((1, 6)))

    def test_orientation_reversal_and_symmetric_scores(self):
        a, b = self.region(), self.region(reverse=True)
        for method in ('regional_mean', 'regional_patch'):
            ab = compare_regions(a, b, method)
            ba = compare_regions(b, a, method)
            self.assertTrue(ab['reversed'])
            self.assertAlmostEqual(ab['score'], 1)
            self.assertAlmostEqual(ab['score'], ba['score'])
        self.assertEqual(len(mutual_matches(a, b, True)), 3)

    def test_middle_region_mismatch_cannot_be_hidden_by_axis_reversal(self):
        a, b = self.region(), self.region()
        b['vectors'][2:4] = [1, 0, 0]
        b['means'][1] = [1, 0, 0]
        for method in ('regional_mean', 'regional_patch'):
            self.assertAlmostEqual(compare_regions(a, b, method)['score'], 2/3)

    def test_background_and_special_token_shape(self):
        coverage = np.array([[0, .49, 1, 1, 1, 1, 1, 1]])
        tokens = np.vstack([[999, 999, 999], [-999, -999, -999], np.repeat(np.eye(3), 2, axis=0)])
        region = regional_features(tokens, coverage)
        self.assertEqual(region['indices'].tolist(), list(range(2, 8)))
        np.testing.assert_allclose(region['means'], np.eye(3))
        with self.assertRaises(ValueError):
            regional_features(np.vstack([tokens, [1, 1, 1]]), coverage)
        with self.assertRaises(ValueError):
            regional_features(tokens, np.zeros_like(coverage))

    def test_all_photo_pairs_average_without_self_leakage(self):
        records = [{'specimen_id': s} for s in ['A', 'A', 'B', 'C']]
        specimens = [{'specimen_id': s} for s in ['A', 'B', 'C']]
        image_scores = np.array([[99, 99, .2, .8], [99, 99, .6, .4], [.2, .6, 99, .1], [.8, .4, .1, 99]])
        scores = specimen_similarity(image_scores, records, specimens)
        np.testing.assert_allclose(scores, [[0, .4, .6], [.4, 0, .1], [.6, .1, 0]])
        stats = exact_retrieval(np.array([[10, 1, 0, 0], [1, 10, 0, 0], [0, 0, 10, 1], [0, 0, 1, 10]]),
                                [{'specimen_id': str(i)} for i in range(4)], ['A', 'A', 'B', 'B'])
        self.assertEqual(stats['nearest_indices'], [1, 0, 3, 2])
        self.assertAlmostEqual(stats['exact_p'], 2/6)

    def test_exact_multiclass_matches_brute_force_and_excludes_singleton_query(self):
        labels = ['A', 'A', 'B', 'B', 'C']
        scores = np.array([[0, 1, .1, .2, .3], [1, 0, .2, .3, .1],
                           [.1, .2, 0, 1, .3], [.2, .3, 1, 0, .1], [.3, .1, .3, .1, 0]])
        rows = [{'specimen_id': str(i)} for i in range(5)]
        result = exact_retrieval(scores, rows, labels)
        nearest = np.array(result['nearest_indices'])
        values = []
        assignments = set(itertools.permutations(labels))
        for assignment in assignments:
            current = np.array(assignment)
            correct = current == current[nearest]
            values.append(np.mean([correct[current == name].mean() for name in ['A', 'B']]))
        self.assertEqual(result['assignments'], 30)
        self.assertEqual(result['eligible_specimens'], 4)
        self.assertFalse(result['per_group']['C']['eligible'])
        self.assertEqual(result['exact_p'], np.mean(np.array(values) >= result['macro_recall']))
        self.assertEqual(len({tuple(x) for x in label_assignments([2, 2, 1])}), 30)

    def test_ties_use_catalog_id_not_locality_order(self):
        rows = [{'specimen_id': s} for s in ['Z', 'Y', 'A', 'B']]
        scores = np.ones((4, 4))
        result = exact_retrieval(scores, rows, ['X', 'X', 'Y', 'Y'])
        self.assertEqual(result['nearest_indices'], [2, 2, 3, 2])

    def test_invalid_scores_and_duplicate_specimens_rejected(self):
        rows = [{'specimen_id': str(i)} for i in range(4)]
        for scores in [np.full((4, 4), np.nan), np.arange(16).reshape(4, 4)]:
            with self.assertRaises(ValueError):
                exact_retrieval(scores, rows, ['A', 'A', 'B', 'B'])
        with self.assertRaises(ValueError):
            exact_retrieval(np.eye(4), [rows[0]]*4, ['A', 'A', 'B', 'B'])


if __name__ == '__main__':
    unittest.main()
