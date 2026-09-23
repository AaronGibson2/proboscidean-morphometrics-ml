"""Auditable crown regions and training-free patch/locality evaluation."""

from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from dinov3_pipeline import normalize


def crown_mask(shape, polygons, retained, recipe, size):
    height, width = shape[:2]
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    for polygon in polygons:
        if len(polygon) < 3 or any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in polygon):
            raise ValueError("Crown coordinates must be normalized to [0, 1]")
        draw.polygon([(round(x * (width - 1)), round(y * (height - 1))) for x, y in polygon], fill=255)
    image = Image.fromarray(np.where(retained, np.asarray(image), 0).astype(np.uint8))
    turns = recipe.get("quarter_turns_ccw", 0)
    if turns:
        image = image.transpose({1: Image.Transpose.ROTATE_90, 2: Image.Transpose.ROTATE_180,
                                 3: Image.Transpose.ROTATE_270}[turns])
    if recipe.get("mirror_left", False):
        image = ImageOps.mirror(image)
    limit = round(size * .90)
    contained = ImageOps.contain(image, (limit, limit), Image.Resampling.NEAREST)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(contained, ((size - contained.width) // 2, (size - contained.height) // 2))
    return canvas


def patch_coverage(mask, patch_size=16):
    pixels = np.asarray(mask, dtype=np.float32) / 255
    height, width = pixels.shape
    if height % patch_size or width % patch_size:
        raise ValueError("Canvas must be divisible by patch size")
    return pixels.reshape(height // patch_size, patch_size, width // patch_size, patch_size).mean(axis=(1, 3))


def crown_pool(tokens, coverage, register_tokens, minimum_coverage=.5):
    """Exclude all special tokens; spatial flattening is row-major, matching DINOv3."""
    tokens = np.asarray(tokens, dtype=np.float32)
    spatial = tokens[1 + register_tokens:]
    if spatial.shape[0] != coverage.size:
        raise ValueError("Patch grid/token mismatch; check register count and patch size")
    weights = np.where(coverage.ravel() >= minimum_coverage, coverage.ravel(), 0)
    if not weights.sum():
        raise ValueError("No crown patches selected")
    spatial = normalize(spatial)
    return normalize(((spatial * weights[:, None]).sum(axis=0) / weights.sum())[None])[0]


def macro_locality(features, rows, permutations=9999, seed=42):
    """Equal locality weight; independently permute specimen labels, not image labels."""
    if len(rows) < 2 or len({r["specimen_id"] for r in rows}) != len(rows):
        raise ValueError("Need distinct specimen observations")
    similarity = normalize(features) @ normalize(features).T
    np.fill_diagonal(similarity, -np.inf)
    nearest = similarity.argmax(axis=1)
    labels = np.array([r["site"] for r in rows])
    supported = sorted(site for site, count in Counter(labels).items() if count > 1)
    if not supported:
        return {"macro_recall": None, "permutation_p": None, "supported_sites": []}

    def recalls(current):
        correct = current[nearest] == current
        return {site: float(correct[current == site].mean()) for site in supported}

    per_site = recalls(labels)
    observed = float(np.mean(list(per_site.values())))
    rng = np.random.default_rng(seed)
    exceed = sum(np.mean(list(recalls(rng.permutation(labels)).values())) >= observed - 1e-12
                 for _ in range(permutations))
    return {"macro_recall": observed, "per_site": per_site, "supported_sites": supported,
            "majority_macro_baseline": 1 / len(supported),
            "permutation_p": (exceed + 1) / (permutations + 1) if permutations else None,
            "permutations": permutations, "seed": seed,
            "assumption": "Specimen labels exchangeable; locality/photography confounding is not controlled."}


def holm_adjust(pvalues):
    pvalues = np.asarray(pvalues, dtype=float)
    if not np.isfinite(pvalues).all() or np.any((pvalues < 0) | (pvalues > 1)):
        raise ValueError("Expected finite p-values in [0, 1]")
    order = np.argsort(pvalues, kind="stable")
    adjusted = np.empty_like(pvalues)
    adjusted[order] = np.minimum(1, np.maximum.accumulate(pvalues[order] * np.arange(len(pvalues), 0, -1)))
    return adjusted.tolist()
