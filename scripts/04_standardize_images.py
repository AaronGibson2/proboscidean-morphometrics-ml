"""Create geometry- and background-standardized images from curated tooth crops."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np

from pipeline_utils import OUTPUTS_DIR, image_files, infer_side, write_json


def read_rgb(path: Path) -> np.ndarray:
    encoded = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def largest_component(mask: np.ndarray) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if count <= 1:
        return mask.astype(bool)
    index = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    return labels == index


def estimate_foreground(image: np.ndarray, max_working_size: int = 640) -> np.ndarray:
    """Estimate foreground with GrabCut; this is a proposal that still requires human QC."""
    height, width = image.shape[:2]
    scale = min(1.0, max_working_size / max(height, width))
    working = cv2.resize(image, (round(width * scale), round(height * scale)),
                         interpolation=cv2.INTER_AREA)
    work_height, work_width = working.shape[:2]
    margin = max(2, round(min(work_height, work_width) * 0.015))
    rectangle = (margin, margin, work_width - 2 * margin, work_height - 2 * margin)
    labels = np.zeros((work_height, work_width), dtype=np.uint8)
    background_model = np.zeros((1, 65), dtype=np.float64)
    foreground_model = np.zeros((1, 65), dtype=np.float64)
    cv2.grabCut(working, labels, rectangle, background_model, foreground_model, 3,
                cv2.GC_INIT_WITH_RECT)
    mask = np.isin(labels, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)
    mask = largest_component(mask).astype(np.uint8)
    kernel_size = max(5, round(min(work_height, work_width) * 0.01) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        mask[:] = 0
        cv2.drawContours(mask, [max(contours, key=cv2.contourArea)], -1, 1, thickness=cv2.FILLED)
    return cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST).astype(bool)


def align_long_axis(image: np.ndarray, mask: np.ndarray, background: int) -> tuple[np.ndarray, np.ndarray]:
    rows, columns = np.where(mask)
    coordinates = np.column_stack((columns, rows)).astype(np.float64)
    covariance = np.cov(coordinates, rowvar=False)
    direction = np.linalg.eigh(covariance)[1][:, -1]
    angle = np.degrees(np.arctan2(direction[1], direction[0]))
    if angle > 90:
        angle -= 180
    if angle < -90:
        angle += 180

    height, width = image.shape[:2]
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    cosine, sine = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_width = int(height * sine + width * cosine)
    new_height = int(height * cosine + width * sine)
    matrix[0, 2] += new_width / 2 - center[0]
    matrix[1, 2] += new_height / 2 - center[1]
    aligned_image = cv2.warpAffine(image, matrix, (new_width, new_height),
                                   flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT,
                                   borderValue=(background,) * 3)
    aligned_mask = cv2.warpAffine(mask.astype(np.uint8), matrix, (new_width, new_height),
                                  flags=cv2.INTER_NEAREST,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(bool)
    return aligned_image, aligned_mask


def standardize(image: np.ndarray, mask: np.ndarray, canvas_size: int,
                occupancy: float, background: int, flip: bool) -> tuple[np.ndarray, np.ndarray]:
    rows, columns = np.where(mask)
    if not len(rows):
        raise ValueError("Foreground mask is empty")
    height, width = image.shape[:2]
    padding = round(max(rows.max() - rows.min(), columns.max() - columns.min()) * 0.03)
    x1, x2 = max(0, int(columns.min()) - padding), min(width, int(columns.max()) + padding + 1)
    y1, y2 = max(0, int(rows.min()) - padding), min(height, int(rows.max()) + padding + 1)
    image, mask = image[y1:y2, x1:x2], mask[y1:y2, x1:x2]

    masked = np.full_like(image, background)
    masked[mask] = image[mask]
    image, mask = align_long_axis(masked, mask, background)
    rows, columns = np.where(mask)
    image = image[rows.min():rows.max() + 1, columns.min():columns.max() + 1]
    mask = mask[rows.min():rows.max() + 1, columns.min():columns.max() + 1]
    if flip:
        image, mask = np.fliplr(image), np.fliplr(mask)

    target = round(canvas_size * occupancy)
    scale = min(target / image.shape[1], target / image.shape[0])
    resized_size = (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale)))
    resized_image = cv2.resize(image, resized_size, interpolation=cv2.INTER_AREA)
    resized_mask = cv2.resize(mask.astype(np.uint8), resized_size,
                              interpolation=cv2.INTER_NEAREST).astype(bool)

    canvas = np.full((canvas_size, canvas_size, 3), background, dtype=np.uint8)
    canvas_mask = np.zeros((canvas_size, canvas_size), dtype=bool)
    x = (canvas_size - resized_size[0]) // 2
    y = (canvas_size - resized_size[1]) // 2
    region = canvas[y:y + resized_size[1], x:x + resized_size[0]]
    region[resized_mask] = resized_image[resized_mask]
    canvas_mask[y:y + resized_size[1], x:x + resized_size[0]] = resized_mask
    return canvas, canvas_mask


def load_curation(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["image_path"]: row for row in csv.DictReader(handle)}


def save_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    success, encoded = cv2.imencode(path.suffix, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not success:
        raise ValueError(f"Could not encode {path}")
    encoded.tofile(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--curation", type=Path, default=Path("metadata/image_qc.csv"))
    parser.add_argument("--canvas-size", type=int, default=512)
    parser.add_argument("--occupancy", type=float, default=0.88)
    parser.add_argument("--background", type=int, default=127)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not 0 < args.occupancy <= 1 or not 0 <= args.background <= 255:
        raise SystemExit("Occupancy must be in (0, 1] and background in [0, 255]")
    curation = load_curation(args.curation)
    report = []
    for source in image_files(args.input):
        relative = source.relative_to(args.input).as_posix()
        decision = curation.get(relative)
        if decision is None:
            report.append({"image": relative, "status": "skipped", "reason": "not reviewed"})
            continue
        if decision["status"].strip().lower() != "include":
            report.append({"image": relative, "status": "excluded", "reason": decision["reason"]})
            continue
        try:
            image = read_rgb(source)
            mask = estimate_foreground(image)
            standardized, standardized_mask = standardize(
                image, mask, args.canvas_size, args.occupancy, args.background,
                flip=infer_side(source.name) == "left",
            )
            rgb_path = args.output / "rgb" / source.relative_to(args.input).with_suffix(".png")
            gray_path = args.output / "grayscale" / source.relative_to(args.input).with_suffix(".png")
            mask_path = OUTPUTS_DIR / "qc" / "masks" / args.output.name / source.relative_to(args.input).with_suffix(".png")
            save_image(rgb_path, standardized)
            gray = cv2.cvtColor(standardized, cv2.COLOR_RGB2GRAY)
            save_image(gray_path, np.repeat(gray[..., None], 3, axis=2))
            mask_preview = np.repeat(standardized_mask[..., None], 3, axis=2).astype(np.uint8) * 255
            save_image(mask_path, mask_preview)
            report.append({"image": relative, "status": "ok", "mask_fraction": float(mask.mean()),
                           "flipped": infer_side(source.name) == "left"})
            print(f"standardized: {relative}")
        except Exception as exc:
            report.append({"image": relative, "status": "failed", "error": str(exc)})
            print(f"failed: {relative}: {exc}")
    write_json(OUTPUTS_DIR / "qc" / f"{args.output.name}_standardization.json", report)
    counts = {status: sum(row["status"] == status for row in report)
              for status in ("ok", "excluded", "skipped", "failed")}
    print("Done:", counts)
