"""Frozen DINOv3 features and specimen-level analysis (no model training)."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from pipeline_utils import PROJECT_ROOT, image_files, infer_specimen_id, sha256

DEFAULT_MODEL = "facebook/dinov3-vitb16-pretrain-lvd1689m"
DEFAULT_CACHE = PROJECT_ROOT / ".cache" / "huggingface" / "hub"


def project_path(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def inventory(root: Path, tooth_position: str, manifest: Path | None = None) -> list[dict]:
    """An optional reviewed CSV must cover the exact image set, without duplicates."""
    paths = list(image_files(root))
    if not paths:
        raise ValueError(f"No supported images found in {root}")
    overrides = {}
    if manifest:
        with manifest.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"image_path", "specimen_id", "site"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"Manifest must contain {sorted(required)}")
            for row in reader:
                key = row["image_path"].replace("\\", "/")
                if key in overrides:
                    raise ValueError(f"Duplicate manifest image: {key}")
                overrides[key] = row
        expected = {p.relative_to(root).as_posix() for p in paths}
        if set(overrides) != expected:
            raise ValueError("Manifest image paths must match the dataset exactly")
    records = []
    specimen_sites = {}
    hashes = {}
    for path in paths:
        relative = path.relative_to(root)
        if len(relative.parts) != 2:
            raise ValueError(f"Expected site/image layout: {relative}")
        row = overrides.get(relative.as_posix(), {})
        specimen_id = row.get("specimen_id", infer_specimen_id(path.name)).strip()
        site = row.get("site", relative.parts[0]).strip()
        if not specimen_id or not site:
            raise ValueError(f"Empty specimen ID or site: {relative}")
        if row.get("tooth_position", tooth_position) != tooth_position:
            raise ValueError(f"Mixed tooth positions in manifest: {relative}")
        if specimen_id in specimen_sites and specimen_sites[specimen_id] != site:
            raise ValueError(f"Specimen assigned to multiple sites: {specimen_id}")
        specimen_sites[specimen_id] = site
        digest = sha256(path)
        if digest in hashes and hashes[digest] != specimen_id:
            raise ValueError(f"Identical image assigned to different specimens: {relative}")
        hashes[digest] = specimen_id
        records.append({"image_path": relative.as_posix(), "specimen_id": specimen_id,
                        "site": site, "tooth_position": tooth_position, "sha256": digest,
                        "metadata_source": "manifest" if manifest else "filename_inference"})
    return records


def dataset_summary(records: list[dict]) -> dict:
    return {site: {"images": sum(r["site"] == site for r in records),
                   "specimens": len({r["specimen_id"] for r in records if r["site"] == site})}
            for site in sorted({r["site"] for r in records})}


def prepare_image(path: Path, size: int, padding_value: int = 127) -> Image.Image:
    """Preserve the whole crown and aspect ratio; never center-crop a tooth."""
    with Image.open(path) as source:
        rgb = ImageOps.exif_transpose(source).convert("RGB")
        contained = ImageOps.contain(rgb, (size, size), Image.Resampling.BICUBIC)
    if not 0 <= padding_value <= 255:
        raise ValueError("Padding value must be in [0, 255]")
    canvas = Image.new("RGB", (size, size), (padding_value,) * 3)
    canvas.paste(contained, ((size - contained.width) // 2, (size - contained.height) // 2))
    return canvas


def normalize(features: np.ndarray) -> np.ndarray:
    features = np.asarray(features, dtype=np.float32)
    if features.ndim != 2 or not features.shape[0] or not features.shape[1]:
        raise ValueError("Expected a nonempty matrix of features")
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    if not np.isfinite(features).all() or np.any(norms <= 1e-12):
        raise ValueError("Features contain nonfinite values or zero-length vectors")
    return features / norms


def extract_features(model, processor, paths: list[Path], *, size: int,
                     batch_size: int, device: str, padding_value: int = 127) -> np.ndarray:
    import torch

    model.requires_grad_(False)
    model.eval()
    model.to(device)
    features = []
    with torch.inference_mode():
        for start in range(0, len(paths), batch_size):
            images = [prepare_image(path, size, padding_value) for path in paths[start:start + batch_size]]
            inputs = processor(images=images, do_resize=False, do_center_crop=False, return_tensors="pt").to(device)
            result = model(**inputs)
            # The first token is CLS; registers and spatial patches are not pooled here.
            features.append(result.last_hidden_state[:, 0, :].float().cpu().numpy())
            print(f"Extracted {min(start + batch_size, len(paths))}/{len(paths)} images", flush=True)
    return normalize(np.concatenate(features))


def save_bundle(path: Path, features: np.ndarray, records: list[dict], provenance: dict) -> None:
    if len(features) != len(records):
        raise ValueError("Feature and image counts differ")
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, features=normalize(features),
                            records_json=json.dumps(records), provenance_json=json.dumps(provenance))
    temporary.replace(path)


def load_bundle(path: Path) -> tuple[np.ndarray, list[dict], dict]:
    with np.load(path, allow_pickle=False) as bundle:
        features = normalize(bundle["features"])
        records = json.loads(str(bundle["records_json"]))
        provenance = json.loads(str(bundle["provenance_json"]))
    if len(features) != len(records):
        raise ValueError("Feature and image counts differ")
    return features, records, provenance


def aggregate_specimens(features: np.ndarray, records: list[dict]) -> tuple[np.ndarray, list[dict]]:
    """Give each catalogued individual one observation, regardless of photo count."""
    if len(features) != len(records):
        raise ValueError("Feature and image counts differ")
    groups = defaultdict(list)
    for index, record in enumerate(records):
        groups[record["specimen_id"]].append(index)
    output, specimen_rows = [], []
    features = normalize(features)
    for specimen_id, indices in sorted(groups.items(), key=lambda item: (records[item[1][0]]["site"], item[0])):
        sites = {records[i]["site"] for i in indices}
        positions = {records[i]["tooth_position"] for i in indices}
        if len(sites) != 1 or len(positions) != 1:
            raise ValueError(f"Conflicting metadata for {specimen_id}")
        output.append(features[indices].mean(axis=0))
        specimen_rows.append({"specimen_id": specimen_id, "site": sites.pop(),
                              "tooth_position": positions.pop(), "image_count": len(indices),
                              "image_indices": indices})
    return normalize(np.stack(output)), specimen_rows


def nearest_specimens(features: np.ndarray, rows: list[dict], k: int = 3) -> list[dict]:
    """Query only distinct specimen centroids; ties use stable specimen order."""
    if len({r["specimen_id"] for r in rows}) != len(rows):
        raise ValueError("Nearest-neighbor analysis requires unique specimen IDs")
    similarities = np.clip(normalize(features) @ normalize(features).T, -1, 1)
    result = []
    counts = Counter(r["site"] for r in rows)
    for i, row in enumerate(rows):
        order = [int(j) for j in np.argsort(-similarities[i], kind="stable") if j != i][:k]
        for rank, j in enumerate(order, 1):
            result.append({"query_specimen": row["specimen_id"], "query_site": row["site"],
                           "rank": rank, "neighbor_specimen": rows[j]["specimen_id"],
                           "neighbor_site": rows[j]["site"], "cosine_similarity": float(similarities[i, j]),
                           "same_site": row["site"] == rows[j]["site"],
                           "same_site_reference_available": counts[row["site"]] > 1})
    return result


def separation_statistics(features: np.ndarray, rows: list[dict], *, permutations: int, seed: int) -> dict:
    """Permutation units are specimens, not correlated image pairs."""
    features = normalize(features)
    sites = np.array([r["site"] for r in rows])
    a, b = np.triu_indices(len(rows), 1)
    values = (features @ features.T)[a, b].astype(np.float64)

    def difference(labels):
        same = labels[a] == labels[b]
        if not same.any() or same.all():
            return None
        return float(values[same].mean() - values[~same].mean())

    observed = difference(sites)
    same = sites[a] == sites[b]
    result = {"within_site_mean_cosine": float(values[same].mean()) if same.any() else None,
              "between_site_mean_cosine": float(values[~same].mean()) if (~same).any() else None,
              "within_minus_between": observed, "permutations": permutations, "seed": seed,
              "permutation_p_one_sided": None,
              "permutation_assumption": "Specimen labels exchangeable across sites; confounding is not controlled."}
    if observed is not None and permutations > 0:
        rng = np.random.default_rng(seed)
        exceed = sum(difference(rng.permutation(sites)) >= observed - 1e-12 for _ in range(permutations))
        result["permutation_p_one_sided"] = float((exceed + 1) / (permutations + 1))
    neighbors = nearest_specimens(features, rows, k=1)
    supported = [r for r in neighbors if r["same_site_reference_available"]]
    result["nearest_neighbor"] = {
        "eligible_specimens": len(supported),
        "unsupported_specimens": [r["specimen_id"] for r in rows if Counter(sites)[r["site"]] == 1],
        "accuracy_eligible_only": float(np.mean([r["same_site"] for r in supported])) if supported else None,
        "per_site": {site: {"specimens": int(sum(sites == site)),
                            "accuracy": float(np.mean([r["same_site"] for r in supported if r["query_site"] == site]))
                            if any(r["query_site"] == site for r in supported) else None}
                     for site in sorted(set(sites))},
    }
    return result
