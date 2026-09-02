import os
import rawpy
import tifffile
import numpy as np
from pathlib import Path

RAW_DIR = "../raw_tiffs"
OUT_DIR = "../converted_tiffs"
os.makedirs(OUT_DIR, exist_ok=True)

# Get all file types
nef_files = list(Path(RAW_DIR).glob("*.nef")) + list(Path(RAW_DIR).glob("*.NEF"))
tif_files = list(Path(RAW_DIR).glob("*.tif")) + list(Path(RAW_DIR).glob("*.tiff")) + list(Path(RAW_DIR).glob("*.TIF")) + list(Path(RAW_DIR).glob("*.TIFF"))

print(f"Found {len(nef_files)} NEF files")
print(f"Found {len(tif_files)} TIFF files")

# Convert NEFs to TIFF
for nef_path in nef_files:
    print(f"Converting {nef_path.name}...")
    with rawpy.imread(str(nef_path)) as raw:
        rgb = raw.postprocess(use_camera_wb=True, output_bps=16)
    out_name = nef_path.stem + ".tiff"
    tifffile.imwrite(os.path.join(OUT_DIR, out_name), rgb)
    print(f"  ✅ Saved {out_name}")

# Copy TIFFs as-is
from shutil import copy2
for tif_path in tif_files:
    print(f"Copying {tif_path.name}...")
    copy2(str(tif_path), os.path.join(OUT_DIR, tif_path.name))
    print(f"  ✅ Copied {tif_path.name}")

print(f"\nDone! All files saved to {OUT_DIR}")
