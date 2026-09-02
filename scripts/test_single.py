import os
os.environ["ROBOFLOW_API_KEY"] = "REVOKED_ROBOFLOW_KEY"

from autodistill_sam3 import SegmentAnything3
from autodistill.detection import CaptionOntology
import tifffile
import numpy as np
import cv2

img = tifffile.imread("../converted_tiffs/LBB-UF-38215-LL_occlusal.tiff")
print(f"Shape: {img.shape}, dtype: {img.dtype}")

# Normalize
img_float = img.astype(np.float32)
img_out = np.zeros_like(img_float)
for c in range(3):
    channel = img_float[:,:,c]
    cmin, cmax = channel.min(), channel.max()
    if cmax > cmin:
        img_out[:,:,c] = ((channel - cmin) / (cmax - cmin) * 255)
img = img_out.astype(np.uint8)

# Save temp and check it looks right
cv2.imwrite("../debug_temp.jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
print("Saved debug_temp.jpg — check if it looks correct")

# Now try SAM3
model = SegmentAnything3(ontology=CaptionOntology({"tooth": "tooth"}))
preds = model.predict("../debug_temp.jpg")
print(f"Detections: {len(preds)}")
print(f"Boxes: {preds.xyxy}")