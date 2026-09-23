"""Build auditable crop-only DINOv3 inputs; never infer foreground from tooth color."""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from pipeline_utils import PROJECT_ROOT, sha256, write_json

RECIPE = PROJECT_ROOT / "metadata/conservative_crops_v2.json"
OUTPUT = PROJECT_ROOT / "data/standardized/crop_black_v2"
QC = PROJECT_ROOT / "outputs/qc/crop_black_v2"


def read_source(path):
    if path.suffix.lower() in {".tif", ".tiff"}:
        import tifffile
        pixels = tifffile.imread(path)
    else:
        with Image.open(path) as image:
            pixels = np.asarray(image.convert("RGB"))
    if pixels.ndim != 3 or pixels.shape[2] != 3 or pixels.dtype not in (np.uint8, np.uint16):
        raise ValueError(f"Expected uint8/uint16 RGB source: {path}")
    return pixels


def to_rgb8(pixels):
    # Fixed full-range conversion, no per-image contrast stretch or inpainting.
    return Image.fromarray((pixels // 257).astype(np.uint8) if pixels.dtype == np.uint16 else pixels)


def crop_source(pixels, recipe):
    """Keep every source pixel in the reviewed region, including disconnected pieces."""
    height, width = pixels.shape[:2]
    if recipe["source_size"] != [width, height]:
        raise ValueError("Source dimensions changed; review the crop again")
    left, top, right, bottom = recipe["bbox"]
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("Crop is outside source bounds")
    mask_image = Image.new("L", (right - left, bottom - top), 255)
    draw = ImageDraw.Draw(mask_image)
    for polygon in recipe.get("exclude_polygons", []):
        if len(polygon) < 3 or any(not (0 <= x <= width and 0 <= y <= height) for x, y in polygon):
            raise ValueError("Invalid exclusion polygon")
        draw.polygon([(x - left, y - top) for x, y in polygon], fill=0)
    mask = np.asarray(mask_image) > 0
    cropped = pixels[top:bottom, left:right].copy()
    cropped[~mask] = 0
    return cropped, mask


def model_canvas(cropped, recipe, size=512):
    image = to_rgb8(cropped)
    turns = recipe.get("quarter_turns_ccw", 0)
    if turns not in (0, 1, 2, 3):
        raise ValueError("Rotation must be a whole quarter turn")
    if turns:
        image = image.transpose({1: Image.Transpose.ROTATE_90, 2: Image.Transpose.ROTATE_180,
                                 3: Image.Transpose.ROTATE_270}[turns])
    if recipe.get("mirror_left", False):
        image = ImageOps.mirror(image)
    contained = ImageOps.contain(image, (round(size * .90), round(size * .90)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), "black")
    canvas.paste(contained, ((size - contained.width) // 2, (size - contained.height) // 2))
    return canvas


def data_uri(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def build(recipe_path=RECIPE, *, overwrite=False):
    import tifffile
    document = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipes = document["images"]
    expected = {f'{r["position"]}/{color}/{r["image_path"]}' for r in recipes for color in ("rgb", "grayscale")}
    if len(expected) != 2 * len(recipes):
        raise ValueError("Duplicate output images in crop recipes")
    existing = {p.relative_to(OUTPUT).as_posix() for p in OUTPUT.rglob("*.png")}
    if existing - expected:
        raise ValueError("Unexpected existing inputs; use a new dataset version")
    if existing and not overwrite:
        raise FileExistsError("Prepared inputs already exist; use --overwrite to rebuild")
    # Validate every source before writing any outputs.
    for recipe in recipes:
        if sha256(PROJECT_ROOT / recipe["source"]) != recipe["source_sha256"]:
            raise ValueError(f'Source changed; review again: {recipe["source"]}')
    QC.mkdir(parents=True, exist_ok=True)
    provenance, panels, cards = [], [], []
    for recipe in recipes:
        source = read_source(PROJECT_ROOT / recipe["source"])
        cropped, mask = crop_source(source, recipe)
        prepared = model_canvas(cropped, recipe)
        relative = Path(recipe["image_path"])
        fullres = PROJECT_ROOT / "data/cropped_v2" / recipe["position"] / relative.with_suffix(".tiff")
        fullres.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imwrite(fullres, cropped, photometric="rgb", compression="deflate")
        outputs = {}
        for color in ("rgb", "grayscale"):
            path = OUTPUT / recipe["position"] / color / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            (prepared if color == "rgb" else ImageOps.grayscale(prepared).convert("RGB")).save(path)
            outputs[color] = {"path": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256(path)}
        provenance.append({**recipe, "retained_crop_pixels": int(mask.sum()),
                           "source_dtype": str(source.dtype), "outputs": outputs,
                           "full_resolution_crop": fullres.relative_to(PROJECT_ROOT).as_posix()})
        annotated = to_rgb8(source)
        draw = ImageDraw.Draw(annotated)
        draw.rectangle(recipe["bbox"], outline="#00ff80", width=max(3, source.shape[1] // 250))
        for polygon in recipe.get("exclude_polygons", []):
            draw.line([tuple(p) for p in polygon + polygon[:1]], fill="#ff5577", width=max(3, source.shape[1] // 250))
        annotated.thumbnail((600, 420))
        old_root = "upper_m3_strict" if recipe["position"] == "upper" else "lower_m3"
        old_path = PROJECT_ROOT / "data/standardized" / old_root / "rgb" / relative
        if old_path.exists():
            with Image.open(old_path) as old_source:
                old = old_source.convert("RGB")
        else:
            old = Image.new("RGB", (400, 400), "#dddddd")
            ImageDraw.Draw(old).text((20, 180), "Legacy input unavailable", fill="black")
        old.thumbnail((400, 400))
        new = prepared.resize((400, 400))
        label = f'{recipe["position"]} {recipe["index"]:02d}: {relative.name}'
        panel = Image.new("RGB", (1430, 470), "#eeeeee")
        d = ImageDraw.Draw(panel)
        d.text((10, 5), label + " | SOURCE + CROP / OLD / NEW", fill="black")
        for x, im in ((10, annotated), (620, old), (1025, new)):
            panel.paste(im, (x, 35))
        panels.append(panel)
        cards.append(f'<article><h2>{html.escape(label)}</h2><p>{html.escape(recipe["notes"])}</p>'
                     f'<img alt="Source with crop boundaries, old input, new black input" src="{data_uri(panel)}"></article>')
        print(label, flush=True)
    for start in range(0, len(panels), 4):
        sheet = Image.new("RGB", (1430, 470 * min(4, len(panels) - start)), "white")
        for j, panel in enumerate(panels[start:start + 4]):
            sheet.paste(panel, (0, j * 470))
        sheet.save(QC / f"comparison_{start // 4 + 1:02d}.jpg", quality=93)
    write_json(QC / "provenance.json", {"version": document["version"], "recipe_sha256": sha256(recipe_path),
               "method": "Reviewed rectangles plus background-only exclusion polygons; no automatic segmentation",
               "canvas": "512px RGB, black padding, 90% occupancy, aspect preserved; fixed uint16 / 257 conversion",
               "images": provenance})
    (QC / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Conservative crop review</title>'
        '<style>body{font:16px system-ui;margin:24px;background:#eee}article{background:white;padding:16px;margin:20px 0}'
        f'img{{width:100%;height:auto}}h2{{font-size:18px}}</style><h1>Conservative black-background crops: {len(recipes)} images</h1>'
        '<p>Left: earliest available source, green crop and pink background exclusions. Middle: old input. Right: new input.</p>'
        '<p>No intensity masking or connected-component selection. Attached matrix and painted catalog marks are preserved; '
        'lower source frames sometimes already touch the tooth. Small backing margins may remain to avoid cutting anatomy.</p>'
        + "".join(cards) + '</html>', encoding="utf-8")
    print(f"Review: {QC / 'index.html'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipes", type=Path, default=RECIPE)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    build(args.recipes, overwrite=args.overwrite)
