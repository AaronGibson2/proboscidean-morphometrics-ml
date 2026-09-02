import os
os.environ["ROBOFLOW_API_KEY"] = "REVOKED_ROBOFLOW_KEY"

from pathlib import Path
from autodistill_sam3 import SegmentAnything3
from autodistill.detection import CaptionOntology
import tifffile
import numpy as np
import cv2
import torch
import gc

INPUT_DIR = "../converted_tiffs"
OUTPUT_DIR = "../segmented_teeth"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PROMPTS = ["fossil tooth", "tooth", "molar", "fossil"]
SAM_WIDTHS = [1280, 800, 640]

def normalize_image(img):
    if img.dtype == np.uint8:
        return img
    img_float = img.astype(np.float32)
    img_out = np.zeros_like(img_float)
    for c in range(img.shape[2] if len(img.shape) == 3 else 1):
        channel = img_float[:,:,c]
        cmin, cmax = channel.min(), channel.max()
        if cmax > cmin:
            img_out[:,:,c] = ((channel - cmin) / (cmax - cmin) * 255)
        else:
            img_out[:,:,c] = 0
    return img_out.astype(np.uint8)

def try_predict(temp_path, prompt):
    model = SegmentAnything3(ontology=CaptionOntology({prompt: "tooth"}))
    preds = model.predict(temp_path)
    del model
    torch.cuda.empty_cache()
    gc.collect()
    return preds

def contour_crop(img, pad=200):
    """Fallback: find largest bright object on black background"""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Blur to ignore small specks
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    # Threshold — tooth is bright, background is black
    _, thresh = cv2.threshold(blur, 30, 255, cv2.THRESH_BINARY)
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, 
                                    cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    # Get bounding box of largest contour
    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    orig_h, orig_w = img.shape[:2]
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(orig_w, x + w + pad)
    y2 = min(orig_h, y + h + pad)
    return img[y1:y2, x1:x2]

files = list(Path(INPUT_DIR).glob("*.tiff")) + list(Path(INPUT_DIR).glob("*.TIF"))
print(f"Found {len(files)} images\n")

skipped = []

for img_path in sorted(files):
    print(f"Processing {img_path.name}...")
    
    try:
        img = tifffile.imread(str(img_path))
        img = normalize_image(img)
        orig_h, orig_w = img.shape[:2]
        
        # --- Try SAM3 first ---
        predictions = None
        used_prompt = None
        used_scale = None

        for sam_width in SAM_WIDTHS:
            scale = sam_width / orig_w
            small_h = int(orig_h * scale)
            img_small = cv2.resize(img, (sam_width, small_h))
            temp_path = "../temp_input.jpg"
            cv2.imwrite(temp_path, cv2.cvtColor(img_small, cv2.COLOR_RGB2BGR))
            
            for prompt in PROMPTS:
                preds = try_predict(temp_path, prompt)
                if len(preds) > 0:
                    predictions = preds
                    used_prompt = prompt
                    used_scale = scale
                    break
            if predictions is not None:
                break
        
        if predictions is not None:
            # SAM3 worked — use mask or xyxy
            if predictions.mask is not None and len(predictions.mask) > 0:
                combined_mask = np.zeros((int(orig_h * used_scale),
                                          int(orig_w * used_scale)), dtype=bool)
                for mask in predictions.mask:
                    combined_mask = combined_mask | mask
                rows = np.any(combined_mask, axis=1)
                cols = np.any(combined_mask, axis=0)
                y1, y2 = np.where(rows)[0][[0, -1]]
                x1, x2 = np.where(cols)[0][[0, -1]]
                x1 = int(x1 / used_scale)
                y1 = int(y1 / used_scale)
                x2 = int(x2 / used_scale)
                y2 = int(y2 / used_scale)
            else:
                x1 = int(predictions.xyxy[:, 0].min() / used_scale)
                y1 = int(predictions.xyxy[:, 1].min() / used_scale)
                x2 = int(predictions.xyxy[:, 2].max() / used_scale)
                y2 = int(predictions.xyxy[:, 3].max() / used_scale)
            
            pad = 200
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(orig_w, x2 + pad)
            y2 = min(orig_h, y2 + pad)
            cropped = img[y1:y2, x1:x2]
            method = f"SAM3 ('{used_prompt}')"
        
        else:
            # SAM3 failed — fallback to contour detection
            print(f"  SAM3 failed — trying contour fallback...")
            cropped = contour_crop(img)
            if cropped is None:
                print(f"  ⚠️  Both methods failed — skipping")
                skipped.append(img_path.name)
                continue
            method = "contour fallback"
        
        out_path = os.path.join(OUTPUT_DIR, img_path.stem + ".jpg")
        cv2.imwrite(out_path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
        print(f"  ✅ Saved ({cropped.shape[1]}x{cropped.shape[0]}px) via {method}")
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        torch.cuda.empty_cache()
        gc.collect()
        skipped.append(img_path.name)
        continue

if os.path.exists("../temp_input.jpg"):
    os.remove("../temp_input.jpg")

print(f"\nDone!")
print(f"Skipped {len(skipped)}: {skipped}")