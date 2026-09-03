"""Convert raw NEF/TIFF images into consistent 16-bit RGB TIFF files."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import tifffile

from pipeline_utils import PREPROCESSED_DIR, RAW_DIR, RAW_SUFFIXES, image_files, sha256, write_json


def standardize_rgb(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image)
    if image.ndim == 2:
        image = np.repeat(image[..., None], 3, axis=2)
    if image.ndim != 3:
        raise ValueError(f"Expected a 2D or 3D image, received shape {image.shape}")
    if image.shape[0] in (3, 4) and image.shape[-1] not in (3, 4):
        image = np.moveaxis(image, 0, -1)
    if image.shape[-1] == 1:
        image = np.repeat(image, 3, axis=2)
    if image.shape[-1] == 4:
        image = image[..., :3]
    if image.shape[-1] != 3:
        raise ValueError(f"Expected 1, 3, or 4 channels, received shape {image.shape}")
    if image.dtype == np.uint16:
        return image
    if image.dtype == np.uint8:
        return image.astype(np.uint16) * 257

    values = image.astype(np.float64)
    finite = np.isfinite(values)
    if not finite.any():
        raise ValueError("Image contains no finite pixel values")
    low, high = float(values[finite].min()), float(values[finite].max())
    if high <= low:
        return np.zeros(values.shape, dtype=np.uint16)
    values = np.nan_to_num(values, nan=low, posinf=high, neginf=low)
    return np.clip((values - low) / (high - low) * 65535, 0, 65535).astype(np.uint16)


def read_raw(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".nef":
        try:
            import rawpy
        except ImportError as exc:
            raise RuntimeError("rawpy is required to convert NEF files") from exc
        with rawpy.imread(str(path)) as raw:
            return raw.postprocess(use_camera_wb=True, output_bps=16, no_auto_bright=True)
    return tifffile.imread(path)


def convert(input_dir: Path, output_dir: Path, overwrite: bool = False) -> dict[str, object]:
    files = list(image_files(input_dir, RAW_SUFFIXES))
    if not files:
        raise FileNotFoundError(f"No NEF/TIFF images found below {input_dir}")
    converted, skipped, failures = 0, 0, []
    for source in files:
        destination = output_dir / source.relative_to(input_dir).with_suffix(".tiff")
        if destination.exists() and not overwrite:
            skipped += 1
            continue
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            tifffile.imwrite(destination, standardize_rgb(read_raw(source)), photometric="rgb")
            converted += 1
            print(f"converted: {source.relative_to(input_dir)}")
        except Exception as exc:
            failures.append({"source": str(source), "error": str(exc)})
            print(f"failed: {source.name}: {exc}")
    report = {"input_dir": str(input_dir.resolve()), "output_dir": str(output_dir.resolve()),
              "discovered": len(files), "converted": converted, "skipped_existing": skipped,
              "failures": failures,
              "source_hashes": {str(p.relative_to(input_dir)): sha256(p) for p in files}}
    write_json(output_dir / "conversion_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path, default=PREPROCESSED_DIR)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = convert(args.input, args.output, args.overwrite)
    print(f"Done: {result['converted']} converted, {result['skipped_existing']} skipped, "
          f"{len(result['failures'])} failed")
