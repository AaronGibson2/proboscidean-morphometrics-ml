import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dinov3_crown import crown_mask, crown_pool, holm_adjust, macro_locality, patch_coverage
from prepare_conservative_crops import model_canvas


class CrownFeatureTests(unittest.TestCase):
    def test_registers_and_background_cannot_contribute_to_pool(self):
        # CLS and four registers point in a deliberately unrelated direction.
        tokens = np.array([[0, 0, 99]]*5 + [[2, 0, 0], [0, 100, 0], [0, 0, 90], [1, 1, 0]], dtype=float)
        coverage = np.array([[1, 0], [.49, .5]], dtype=float)
        expected = np.array([1 + .5/np.sqrt(2), .5/np.sqrt(2), 0])
        expected /= np.linalg.norm(expected)
        np.testing.assert_allclose(crown_pool(tokens, coverage, 4), expected, atol=1e-7)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            crown_pool(tokens, coverage, 0)
        with self.assertRaisesRegex(ValueError, "No crown"):
            crown_pool(tokens, np.zeros((2, 2)), 4)

    def test_mask_orientation_matches_image_for_all_quarter_turns_and_mirroring(self):
        pixels = np.zeros((100, 200, 3), dtype=np.uint8)
        pixels[10:40, 20:80] = 255
        polygon = [[20/199, 10/99], [79/199, 10/99], [79/199, 39/99], [20/199, 39/99]]
        for size in (224, 512):
            for turns in range(4):
                for mirror in (True, False):
                    recipe = {"quarter_turns_ccw": turns, "mirror_left": mirror}
                    mask = crown_mask(pixels.shape, [polygon], np.ones((100, 200), bool), recipe, size)
                    image = np.asarray(model_canvas(pixels, recipe, size))[:, :, 0] > 127
                    selected = np.asarray(mask) > 127
                    intersection = (image & selected).sum()
                    self.assertGreater(intersection / (image | selected).sum(), .95)
                    self.assertEqual(patch_coverage(mask).shape, (size//16, size//16))

    def test_detached_regions_are_united_and_background_exclusions_apply(self):
        polygons = [[[0, 0], [.3, 0], [.3, 1], [0, 1]], [[.8, 0], [1, 0], [1, 1], [.8, 1]]]
        retained = np.ones((100, 200), bool)
        retained[:30, :30] = False
        mask = np.asarray(crown_mask((100, 200, 3), polygons, retained, {}, 224))
        self.assertTrue(mask[110, 30] > 0)
        self.assertTrue(mask[110, 200] > 0)
        self.assertEqual(mask[110, 110], 0)
        self.assertEqual(mask[65, 20], 0)

    def test_macro_recall_weights_sites_equally_and_excludes_singleton_query(self):
        rows = [{"specimen_id": str(i), "site": site} for i, site in enumerate(["A"]*4 + ["B"]*2 + ["C"])]
        features = np.array([[1, 0], [1, .01], [1, .02], [1, .03], [1, -.03], [1, .10], [-1, 0]])
        result = macro_locality(features, rows, permutations=39, seed=42)
        self.assertEqual(result["supported_sites"], ["A", "B"])
        self.assertEqual(result["per_site"], {"A": 1., "B": 0.})
        self.assertEqual(result["macro_recall"], .5)
        self.assertEqual(result["majority_macro_baseline"], .5)
        self.assertEqual(result, macro_locality(features, rows, permutations=39, seed=42))

    def test_holm_correction_preserves_order_and_is_monotone_in_sorted_p(self):
        np.testing.assert_allclose(holm_adjust([.04, .001, .03]), [.06, .003, .06])

    @unittest.skipUnless(importlib.util.find_spec("transformers") and importlib.util.find_spec("torch"),
                         "Optional frozen architecture test requires torch/transformers")
    def test_real_architecture_spatial_token_layout_and_frozen_forward(self):
        import torch
        from transformers import DINOv3ViTConfig, DINOv3ViTModel
        model = DINOv3ViTModel(DINOv3ViTConfig(hidden_size=32, intermediate_size=64,
                             num_hidden_layers=1, num_attention_heads=2, num_register_tokens=4)).eval()
        model.requires_grad_(False)
        with torch.inference_mode():
            tokens = model(pixel_values=torch.zeros(1, 3, 32, 32)).last_hidden_state[0].numpy()
        self.assertEqual(tokens.shape, (9, 32))
        pooled = crown_pool(tokens, np.ones((2, 2)), 4)
        self.assertAlmostEqual(float(np.linalg.norm(pooled)), 1., places=6)
        self.assertTrue(all(not p.requires_grad and p.grad is None for p in model.parameters()))


if __name__ == "__main__":
    unittest.main()
