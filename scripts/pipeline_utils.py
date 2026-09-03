"""Shared utilities for the proboscidean image-analysis pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PREPROCESSED_DIR = DATA_DIR / "preprocessed"
SEGMENTED_DIR = DATA_DIR / "segmented"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
BIOENCODER_DIR = OUTPUTS_DIR / "bioencoder"
CONFIG_DIR = PROJECT_ROOT / "bioencoder_configs"
RAW_SUFFIXES = {".nef", ".tif", ".tiff"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def image_files(root: Path, suffixes: set[str] = IMAGE_SUFFIXES) -> Iterator[Path]:
    """Yield supported images recursively in a stable order."""
    if root.exists():
        yield from sorted(
            (p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in suffixes),
            key=lambda p: p.as_posix().casefold(),
        )


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def set_reproducible_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def infer_specimen_id(filename: str) -> str:
    match = re.search(r"(?i)(UF|USNM)[-_ ]?(\d+)", Path(filename).stem)
    return f"{match.group(1).upper()}-{match.group(2)}" if match else Path(filename).stem


def infer_side(filename: str) -> str:
    stem = Path(filename).stem.upper()
    if re.search(r"(?:^|[-_])(?:RL|RUM3|RLM3)(?:[-_]|$)", stem):
        return "right"
    if re.search(r"(?:^|[-_])(?:LL|LUM3|LLM3)(?:[-_]|$)", stem):
        return "left"
    return "unknown"


def infer_tooth_position(filename: str) -> str:
    stem = Path(filename).stem.upper()
    if "UM3" in stem:
        return "upper_m3"
    if "LM3" in stem or "-LL" in stem or "-RL" in stem:
        return "lower_m3"
    return "unknown"


@dataclass(frozen=True)
class ImageRecord:
    image_path: str
    specimen_id: str
    site: str
    tooth_position: str
    side: str
    sha256: str


def records_for_directory(root: Path) -> list[ImageRecord]:
    records = []
    for path in image_files(root):
        relative = path.relative_to(root)
        site = relative.parent.name if relative.parent != Path(".") else "unknown"
        records.append(ImageRecord(relative.as_posix(), infer_specimen_id(path.name), site,
                                   infer_tooth_position(path.name), infer_side(path.name), sha256(path)))
    return records


def write_manifest(path: Path, records: Iterable[ImageRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(ImageRecord.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)
