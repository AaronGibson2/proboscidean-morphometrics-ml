import os
os.environ["ROBOFLOW_API_KEY"] = "REVOKED_ROBOFLOW_KEY"

from autodistill_sam3 import SegmentAnything3
from autodistill.detection import CaptionOntology
import tifffile
import numpy as np
import cv2

TEST_IMAGE = "../converted_tiffs/LBB-UF-38208-RL_occlusal.tiff"

model = SegmentAnything3(ontology=CaptionOntology({"fossil tooth": "tooth"}))
predictions = model.predict(TEST_IMAGE)

print(f"Number of detections: {len(predictions)}")

# Merge all bounding boxes into one
x1 = int(predictions.xyxy[:, 0].min())
y1 = int(predictions.xyxy[:, 1].min())
x2 = int(predictions.xyxy[:, 2].max())
y2 = int(predictions.xyxy[:, 3].max())

print(f"Merged bounding box: {x1}, {y1}, {x2}, {y2}")

img = tifffile.imread(TEST_IMAGE)
if img.dtype != np.uint8:
    img = ((img - img.min()) / (img.max() - img.min()) * 255).astype(np.uint8)

# Add padding
pad = 80
h, w = img.shape[:2]
x1 = max(0, x1 - pad)
y1 = max(0, y1 - pad)
x2 = min(w, x2 + pad)
y2 = min(h, y2 + pad)

cropped = img[y1:y2, x1:x2]
cv2.imwrite("../test_crop.jpg", cropped)
print("Saved test_crop.jpg — open it to check the crop!")