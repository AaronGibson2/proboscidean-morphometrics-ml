"""Scientific grouping, provenance, and frozen-forward regression checks."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dinov3_pipeline import (aggregate_specimens, extract_features, inventory, load_bundle,
                             nearest_specimens, normalize, prepare_image, save_bundle,
                             separation_statistics, write_csv)


def record(specimen, site, image="example.png"):
    return {"specimen_id": specimen, "site": site, "tooth_position": "lower_m3", "image_path": image}


class SpecimenAnalysisTests(unittest.TestCase):
    def test_paired_teeth_cannot_be_their_own_neighbors(self):
        records = [record("UF-1", "A"), record("UF-1", "A"), record("UF-2", "A"), record("UF-3", "B")]
        vectors = np.array([[1, 0], [1, 0], [0.9, 0.1], [0, 1]])
        features, rows = aggregate_specimens(vectors, records)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["image_count"], 2)
        neighbors = nearest_specimens(features, rows)
        self.assertTrue(all(r["query_specimen"] != r["neighbor_specimen"] for r in neighbors))
        self.assertEqual(next(r for r in neighbors if r["query_specimen"] == "UF-1")["neighbor_specimen"], "UF-2")
        stats = separation_statistics(features, rows, permutations=99, seed=42)
        self.assertEqual(stats["nearest_neighbor"]["unsupported_specimens"], ["UF-3"])
        self.assertIsNone(stats["nearest_neighbor"]["per_site"]["B"]["accuracy"])
        self.assertEqual(stats["nearest_neighbor"]["eligible_specimens"], 2)

    def test_label_permutation_is_reproducible_and_detects_clear_separation(self):
        rows = [record(f"UF-{i}", "A" if i < 3 else "B") for i in range(6)]
        vectors = np.array([[1, 0]] * 3 + [[0, 1]] * 3)
        first = separation_statistics(vectors, rows, permutations=999, seed=2)
        second = separation_statistics(vectors, rows, permutations=999, seed=2)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["within_minus_between"], 1)
        # Only two of the 20 possible 3/3 label assignments give perfect separation.
        self.assertTrue(0.06 < first["permutation_p_one_sided"] < 0.15)

    def test_undefined_separation_is_reported_as_null(self):
        stats = separation_statistics(np.eye(2), [record("a", "A"), record("b", "B")], permutations=9, seed=1)
        self.assertIsNone(stats["within_minus_between"])
        self.assertIsNone(stats["permutation_p_one_sided"])

    def test_conflicting_specimen_labels_and_invalid_vectors_are_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_specimens(np.eye(2), [record("same", "A"), record("same", "B")])
        for vectors in (np.zeros((2, 3)), np.array([[np.nan, 1]])):
            with self.assertRaises(ValueError):
                normalize(vectors)


class ImageAndCacheTests(unittest.TestCase):
    def test_whole_image_resize_preserves_both_ends(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wide.png"
            pixels = np.zeros((16, 64, 3), dtype=np.uint8)
            pixels[:, :16] = [255, 0, 0]
            pixels[:, -16:] = [0, 0, 255]
            Image.fromarray(pixels).save(path)
            prepared = np.asarray(prepare_image(path, 64))
            np.testing.assert_array_equal(prepared[32, 0], [255, 0, 0])
            np.testing.assert_array_equal(prepared[32, -1], [0, 0, 255])
            np.testing.assert_array_equal(prepared[0, 0], [127, 127, 127])

    def test_reviewed_manifest_overrides_catalog_grouping_and_requires_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A").mkdir()
            Image.new("RGB", (16, 16), "red").save(root / "A" / "UF-1-LL.png")
            Image.new("RGB", (16, 16), "blue").save(root / "A" / "UF-2-RL.png")
            manifest = root / "review.csv"
            write_csv(manifest, [{"image_path": "A/UF-1-LL.png", "specimen_id": "one-individual", "site": "A"},
                                 {"image_path": "A/UF-2-RL.png", "specimen_id": "one-individual", "site": "A"}])
            rows = inventory(root, "lower_m3", manifest)
            self.assertEqual({r["specimen_id"] for r in rows}, {"one-individual"})
            write_csv(manifest, [{"image_path": "A/UF-1-LL.png", "specimen_id": "one-individual", "site": "A"}])
            with self.assertRaisesRegex(ValueError, "exactly"):
                inventory(root, "lower_m3", manifest)

    def test_cache_round_trip_preserves_order_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "embeddings.npz"
            rows = [record("b", "B"), record("a", "A")]
            save_bundle(path, np.eye(2), rows, {"resolved_revision": "fixed-commit"})
            features, actual, provenance = load_bundle(path)
            np.testing.assert_array_equal(features, np.eye(2))
            self.assertEqual(actual, rows)
            self.assertEqual(provenance["resolved_revision"], "fixed-commit")

    def test_report_builds_from_cached_features_and_rejects_changed_images(self):
        module_path = Path(__file__).resolve().parents[1] / "scripts" / "06_analyze_dinov3.py"
        spec = importlib.util.spec_from_file_location("analyze_dinov3", module_path)
        analysis = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analysis)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for site in ["A", "B"]:
                (root / "images" / site).mkdir(parents=True)
                for index in range(2):
                    Image.new("RGB", (32, 32), (200 * (site == "A"), index * 50, 200 * (site == "B"))).save(
                        root / "images" / site / f"{site}-{index}.png")
            rows = inventory(root / "images", "lower_m3")
            vectors = np.array([[1, 0], [0.99, 0.01], [0, 1], [0.01, 0.99]])
            save_bundle(root / "embeddings.npz", vectors, rows,
                        {"images_root": str(root / "images"), "metadata_source": "filename_inference", "model": "synthetic-test"})
            stats = analysis.build_report(root, permutations=19)
            self.assertEqual(stats["specimens"], 4)
            self.assertIn("data:image/png;base64", (root / "analysis" / "report.html").read_text())
            self.assertTrue((root / "analysis" / "nearest_neighbors.csv").exists())
            Image.new("RGB", (32, 32), "green").save(root / "images" / rows[0]["image_path"])
            with self.assertRaisesRegex(ValueError, "changed"):
                analysis.build_report(root, overwrite=True)


@unittest.skipUnless(importlib.util.find_spec("transformers") and importlib.util.find_spec("torch"),
                     "Optional local DINOv3 forward smoke test requires torch/transformers")
class FrozenForwardTests(unittest.TestCase):
    def test_local_checkpoint_cli_records_provenance_on_available_device(self):
        import torch
        from transformers import DINOv3ViTConfig, DINOv3ViTModel, DINOv3ViTImageProcessorFast
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = DINOv3ViTConfig(hidden_size=32, intermediate_size=64, num_hidden_layers=1,
                                     num_attention_heads=2, num_register_tokens=4, image_size=32)
            # Synthetic software fixture only. Never used with fossil images or kept as a result.
            DINOv3ViTModel(config).save_pretrained(root / "synthetic_model")
            DINOv3ViTImageProcessorFast().save_pretrained(root / "synthetic_model")
            (root / "images" / "synthetic_site").mkdir(parents=True)
            Image.new("RGB", (32, 32), "red").save(root / "images" / "synthetic_site" / "fixture.png")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "05_extract_dinov3.py"),
                       "--images", str(root / "images"), "--tooth-position", "lower_m3",
                       "--output", str(root / "run"), "--model", str(root / "synthetic_model"),
                       "--image-size", "32", "--device", device, "--local-files-only"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            features, records, provenance = load_bundle(root / "run" / "embeddings.npz")
            self.assertEqual(features.shape, (1, 32))
            self.assertEqual(provenance["device"], device)
            self.assertFalse(provenance["trained"])
            self.assertIn("model.safetensors", provenance["local_checkpoint_sha256"])
            self.assertEqual(records[0]["specimen_id"], "fixture")
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("Run already exists", repeated.stderr)

    def test_real_dinov3_architecture_forward_is_frozen_and_deterministic(self):
        # Tiny random weights are used ONLY on synthetic test images, never as pretrained results.
        import torch
        from transformers import DINOv3ViTConfig, DINOv3ViTModel, DINOv3ViTImageProcessorFast
        config = DINOv3ViTConfig(hidden_size=32, intermediate_size=64, num_hidden_layers=1,
                                 num_attention_heads=2, num_register_tokens=4, image_size=32)
        model = DINOv3ViTModel(config)
        processor = DINOv3ViTImageProcessorFast()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.png"
            Image.new("RGB", (32, 32), "red").save(path)
            first = extract_features(model, processor, [path], size=32, batch_size=1, device="cpu")
            second = extract_features(model, processor, [path], size=32, batch_size=1, device="cpu")
            self.assertEqual(first.shape, (1, 32))
            np.testing.assert_allclose(first, second, rtol=0, atol=1e-7)
            self.assertFalse(model.training)
            self.assertTrue(all(not p.requires_grad and p.grad is None for p in model.parameters()))
            self.assertTrue(torch.isfinite(torch.from_numpy(first)).all())


if __name__ == "__main__":
    unittest.main()
