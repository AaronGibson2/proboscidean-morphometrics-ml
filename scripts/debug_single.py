import os
os.environ["ROBOFLOW_API_KEY"] = "REVOKED_ROBOFLOW_KEY"

from autodistill_sam3 import SegmentAnything3
from autodistill.detection import CaptionOntology
import tifffile
import numpy as np
import cv2
import torch
import gc

# Try every possible prompt we can think of
PROMPTS = [
    "fossil tooth", "tooth", "molar", "fossil", "bone",
    "rock", "object", "specimen", "jaw", "mandible",
    "artifact", "stone", "brown object", "white object"
]

img = tifffile.imread("../converted_tiffs/LBB-UF-38215-LL_occlusal.tiff")
img_float = img.astype(np.float32)
img_out = np.zeros_like(img_float)
for c in range(3):
    channel = img_float[:,:,c]
    cmin, cmax = channel.min(), channel.max()
    if cmax > cmin:
        img_out[:,:,c] = ((channel - cmin) / (cmax - cmin) * 255)
img = img_out.astype(np.uint8)

# Try at multiple sizes
for width in [1280, 800, 640, 400]:
    scale = width / img.shape[1]
    small = cv2.resize(img, (width, int(img.shape[0] * scale)))
    cv2.imwrite("../temp_debug.jpg", cv2.cvtColor(small, cv2.COLOR_RGB2BGR))
    
    print(f"\n--- Testing at width {width}px ---")
    for prompt in PROMPTS:
        model = SegmentAnything3(ontology=CaptionOntology({prompt: "tooth"}))
        preds = model.predict("../temp_debug.jpg")
        del model
        torch.cuda.empty_cache()
        gc.collect()
        
        if len(preds) > 0:
            print(f"  ✅ FOUND with prompt '{prompt}': {len(preds)} detections")
        else:
            print(f"  ❌ '{prompt}': nothing")