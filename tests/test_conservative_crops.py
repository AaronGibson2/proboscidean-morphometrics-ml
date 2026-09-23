"""Lock down tooth retention, disconnected pieces, and background-only cleanup."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_conservative_crops import RECIPE, crop_source, model_canvas, read_source
from dinov3_pipeline import prepare_image
from pipeline_utils import PROJECT_ROOT


class ConservativeCropTests(unittest.TestCase):
    def test_dark_surface_and_disconnected_fragment_survive(self):
        pixels = np.zeros((100, 200, 3), dtype=np.uint16)
        pixels[20:80, 10:130] = 33000
        pixels[30:70, 40:100] = 257  # dark enamel must not become a hole
        pixels[35:65, 160:190] = 44000  # detached piece
        pixels[85:95, 5:35] = 65535  # separate paper label
        recipe = {"source_size": [200, 100], "bbox": [0, 0, 200, 100],
                  "exclude_polygons": [[[0, 82], [40, 82], [40, 100], [0, 100]]]}
        cropped, mask = crop_source(pixels, recipe)
        np.testing.assert_array_equal(cropped[20:80], pixels[20:80])
        self.assertTrue(mask[30:70, 40:100].all())
        self.assertTrue(mask[35:65, 160:190].all())
        self.assertFalse(cropped[85:95, 5:35].any())
        self.assertEqual(cropped.dtype, np.uint16)

    def test_black_padding_survives_the_actual_model_preprocessor(self):
        pixels = np.full((80, 200, 3), 120, dtype=np.uint8)
        canvas = model_canvas(pixels, {"quarter_turns_ccw": 1, "mirror_left": True})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.png"
            canvas.save(path)
            prepared = np.asarray(prepare_image(path, 224, padding_value=0))
        self.assertFalse(prepared[:8].any())
        self.assertFalse(prepared[-8:].any())
        self.assertFalse(prepared[:, :8].any())
        self.assertTrue((prepared[100:120, 100:120] == 120).all())

    def test_changed_source_dimensions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "dimensions"):
            crop_source(np.zeros((10, 20, 3), dtype=np.uint8),
                        {"source_size": [21, 10], "bbox": [0, 0, 20, 10]})

    def test_real_crown_region_and_tyner_fragment_are_pixel_identical(self):
        recipes = json.loads(RECIPE.read_text())["images"]
        cases = [("lower", 6, (200, 220, 500, 550)),
                 ("lower", 19, (2470, 300, 2600, 650))]
        for position, index, (left, top, right, bottom) in cases:
            recipe = next(r for r in recipes if r["position"] == position and r["index"] == index)
            path = PROJECT_ROOT / recipe["source"]
            if not path.exists():
                self.skipTest("Private source photographs are not present")
            source = read_source(path)
            cropped, mask = crop_source(source, recipe)
            x, y = recipe["bbox"][:2]
            region = (slice(top-y, bottom-y), slice(left-x, right-x))
            self.assertTrue(mask[region].all(), path.name)
            np.testing.assert_array_equal(cropped[region], source[top:bottom, left:right])

    def test_real_paper_label_corners_are_black(self):
        recipes = json.loads(RECIPE.read_text())["images"]
        # Manually located paper pixels in 630px-wide source previews.
        for position, index, tx, ty in [("upper", 10, 148, 258), ("lower", 7, 50, 220),
                                        ("lower", 8, 25, 237), ("lower", 17, 20, 269)]:
            recipe = next(r for r in recipes if r["position"] == position and r["index"] == index)
            width, height = recipe["source_size"]
            cropped, mask = crop_source(np.full((height, width, 3), 255, dtype=np.uint8), recipe)
            x = round(tx * width / 630) - recipe["bbox"][0]
            y = round(ty * width / 630) - recipe["bbox"][1]
            self.assertFalse(mask[y, x], f"{position} {index}")
            self.assertFalse(cropped[y, x].any())


if __name__ == "__main__":
    unittest.main()
