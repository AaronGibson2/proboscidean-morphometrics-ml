import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pipeline_utils import infer_side, infer_specimen_id, infer_tooth_position


class FilenameMetadataTests(unittest.TestCase):
    def test_uf_specimen_id(self):
        self.assertEqual(infer_specimen_id("LBB-UF-38249-RL_occlusal.jpg"), "UF-38249")

    def test_usnm_specimen_id(self):
        self.assertEqual(infer_specimen_id("Mixson_USNM-3083_occlusal.jpg"), "USNM-3083")

    def test_side(self):
        self.assertEqual(infer_side("UF-212305-01-LUM3.nef"), "left")
        self.assertEqual(infer_side("UF-38244-01-RUM3.nef"), "right")

    def test_tooth_position(self):
        self.assertEqual(infer_tooth_position("UF-38244-01-RUM3.nef"), "upper_m3")
        self.assertEqual(infer_tooth_position("UF-38249-RL_occlusal.jpg"), "lower_m3")


if __name__ == "__main__":
    unittest.main()
