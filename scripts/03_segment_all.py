"""Isolate tooth foregrounds and write cropped PNGs plus visual QC images."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import tifffile

from pipeline_utils import PREPROCESSED_DIR, SEGMENTED_DIR, image_files, write_json


def load_crop_overrides(path: Path | None) -> dict[str, tuple[int, int, int, int]]:
    """Read auditable manual crop boxes keyed by input-relative POSIX path."""
    if path is None or not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        required = {"image_path", "x1", "y1", "x2", "y2"}
        if not required.issubset(rows.fieldnames or ()):
            raise ValueError(f"{path} must contain columns: {sorted(required)}")
        return {
            row["image_path"].replace("\\", "/"): tuple(
                int(row[name]) for name in ("x1", "y1", "x2", "y2")
            )
            for row in rows
        }


def to_uint8(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image)
    if image.ndim == 2:
        image = np.repeat(image[..., None], 3, axis=2)
    if image.shape[-1] == 4:
        image = image[..., :3]
    values = image.astype(np.float32)
    finite = np.isfinite(values)
    if not finite.any():
        raise ValueError("Image contains no finite values")
    low, high = np.percentile(values[finite], (0.5, 99.5))
    if high <= low:
        return np.zeros(values.shape, dtype=np.uint8)
    return np.clip((values - low) / (high - low) * 255, 0, 255).astype(np.uint8)


def contour_mask(image: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    masks = []
    for polarity in (cv2.THRESH_BINARY, cv2.THRESH_BINARY_INV):
        _, threshold = cv2.threshold(blurred, 0, 255, polarity + cv2.THRESH_OTSU)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(threshold, connectivity=8)
        height, width = gray.shape
        for index in range(1, count):
            x, y, box_width, box_height, area = stats[index]
            fraction = area / (height * width)
            if not 0.01 <= fraction <= 0.85:
                continue
            borders = sum((x == 0, y == 0, x + box_width >= width, y + box_height >= height))
            masks.append((area / (1 + 4 * borders), labels == index))
    if not masks:
        return None
    _, mask = max(masks, key=lambda candidate: candidate[0])
    kernel = np.ones((11, 11), np.uint8)
    return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel).astype(bool)


def sam_mask(model: object, image: np.ndarray, temp_dir: Path, width: int) -> np.ndarray | None:
    height, original_width = image.shape[:2]
    scale = min(1.0, width / original_width)
    resized = cv2.resize(image, (round(original_width * scale), round(height * scale)))
    temp_path = temp_dir / "sam_input.jpg"
    cv2.imwrite(str(temp_path), cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))
    predictions = model.predict(str(temp_path))
    masks = getattr(predictions, "mask", None)
    if masks is None or len(masks) == 0:
        return None
    masks = np.asarray(masks, dtype=bool)
    largest = masks[np.argmax(masks.sum(axis=(1, 2)))].astype(np.uint8)
    return cv2.resize(largest, (original_width, height), interpolation=cv2.INTER_NEAREST).astype(bool)


def crop_to_mask(image: np.ndarray, mask: np.ndarray, padding: int) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    rows, columns = np.where(mask)
    if not len(rows):
        raise ValueError("Empty foreground mask")
    height, width = image.shape[:2]
    x1, x2 = max(0, int(columns.min()) - padding), min(width, int(columns.max()) + padding + 1)
    y1, y2 = max(0, int(rows.min()) - padding), min(height, int(rows.max()) + padding + 1)
    masked = image.copy()
    masked[~mask] = 0
    return masked[y1:y2, x1:x2], (x1, y1, x2, y2)


def build_sam_model(prompt: str) -> object:
    if not os.environ.get("ROBOFLOW_API_KEY"):
        raise RuntimeError("Set ROBOFLOW_API_KEY in the environment before using SAM3")
    from autodistill.detection import CaptionOntology
    from autodistill_sam3 import SegmentAnything3
    return SegmentAnything3(ontology=CaptionOntology({prompt: "tooth"}))


def segment(input_dir: Path, output_dir: Path, method: str, prompt: str, padding: int,
            sam_width: int, overwrite: bool,
            overrides_path: Path | None = None) -> dict[str, object]:
    files = list(image_files(input_dir, {".tif", ".tiff"}))
    if not files:
        raise FileNotFoundError(f"No TIFF images found below {input_dir}")
    model = None
    if method in {"sam3", "auto"} and os.environ.get("ROBOFLOW_API_KEY"):
        try:
            model = build_sam_model(prompt)
        except Exception:
            if method == "sam3":
                raise
            print("SAM3 could not initialize; continuing with contour segmentation")
    if method == "sam3" and model is None:
        raise RuntimeError("SAM3 requested but ROBOFLOW_API_KEY is not set")

    overrides = load_crop_overrides(overrides_path)
    qc_dir = output_dir.parent / "qc" / output_dir.name
    results = []
    with tempfile.TemporaryDirectory(prefix="proboscidean_sam_") as temp:
        for source in files:
            relative = source.relative_to(input_dir).with_suffix(".png")
            destination = output_dir / relative
            if destination.exists() and not overwrite:
                results.append({"source": str(source), "output": str(destination), "status": "skipped"})
                continue
            try:
                image = to_uint8(tifffile.imread(source))
                mask, used = None, None
                override = overrides.get(source.relative_to(input_dir).as_posix())
                if override is not None:
                    x1, y1, x2, y2 = override
                    height, width = image.shape[:2]
                    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                        raise ValueError(f"Invalid crop override {override} for {width}x{height} image")
                    mask = np.zeros((height, width), dtype=bool)
                    mask[y1:y2, x1:x2] = True
                    used = "manual_override"
                elif model is not None:
                    mask = sam_mask(model, image, Path(temp), sam_width)
                    used = "sam3" if mask is not None else None
                if mask is None and method in {"contour", "auto"}:
                    mask, used = contour_mask(image), "contour"
                if mask is None:
                    raise RuntimeError("No foreground detected")
                cropped, box = crop_to_mask(image, mask, 0 if override is not None else padding)
                destination.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(destination), cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
                qc = image.copy()
                cv2.rectangle(qc, box[:2], box[2:], (255, 0, 255), max(2, image.shape[1] // 500))
                qc_path = (qc_dir / relative).with_suffix(".jpg")
                qc_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(qc_path), cv2.cvtColor(qc, cv2.COLOR_RGB2BGR))
                results.append({"source": str(source), "output": str(destination), "status": "ok",
                                "method": used, "box": box, "foreground_fraction": float(mask.mean())})
                print(f"segmented ({used}): {source.relative_to(input_dir)}")
            except Exception as exc:
                results.append({"source": str(source), "status": "failed", "error": str(exc)})
                print(f"failed: {source.name}: {exc}")
    report = {"method": method, "prompt": prompt, "padding": padding, "images": results}
    write_json(output_dir / "segmentation_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PREPROCESSED_DIR)
    parser.add_argument("--output", type=Path, default=SEGMENTED_DIR)
    parser.add_argument("--method", choices=("contour", "sam3", "auto"), default="contour")
    parser.add_argument("--prompt", default="fossil molar tooth")
    parser.add_argument("--padding", type=int, default=200)
    parser.add_argument("--sam-width", type=int, default=1280)
    parser.add_argument("--overrides", type=Path,
                        default=Path("metadata/segmentation_overrides.csv"))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    report = segment(args.input, args.output, args.method, args.prompt, args.padding,
                     args.sam_width, args.overwrite, args.overrides)
    counts = {status: sum(item["status"] == status for item in report["images"])
              for status in ("ok", "skipped", "failed")}
    print("Done:", counts)
