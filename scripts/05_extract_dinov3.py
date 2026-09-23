"""Extract frozen pretrained DINOv3 CLS features; no training or fine-tuning."""

from __future__ import annotations

import argparse
import json
import os
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from dinov3_pipeline import (DEFAULT_CACHE, DEFAULT_MODEL, dataset_summary, extract_features,
                             inventory, project_path, save_bundle, write_csv)
from pipeline_utils import sha256, write_json


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True, help="Standardized site/image directory")
    parser.add_argument("--tooth-position", choices=["upper_m3", "lower_m3"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, help="Reviewed image_path/specimen_id/site CSV")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face ID or local pretrained model directory")
    parser.add_argument("--revision", default="main", help="HF branch, tag, or commit; resolved commit is recorded")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--image-size", type=int, default=224, help="Whole-image square input, multiple of 16")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--padding-value", type=int, choices=range(256), default=127, metavar="0..255")
    parser.add_argument("--crop-provenance", type=Path, help="Crop audit whose output hashes must match these inputs")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--inventory-only", action="store_true", help="Audit images without loading/downloading weights")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.image_size < 16 or args.image_size % 16 or args.batch_size < 1:
        raise ValueError("Image size must be a positive multiple of 16; batch size must be positive")
    root, output = project_path(args.images), project_path(args.output)
    manifest = project_path(args.manifest) if args.manifest else None
    if (output / "embeddings.npz").exists() and not args.overwrite:
        raise FileExistsError(f"Run already exists: {output}. Use a new output or --overwrite.")
    records = inventory(root, args.tooth_position, manifest)
    crop_audit = None
    if args.crop_provenance:
        audit_path = project_path(args.crop_provenance)
        crop_audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audited = {str(project_path(Path(output["path"]))): output["sha256"]
                   for row in crop_audit["images"] for output in row["outputs"].values()}
        if any(audited.get(str(root / r["image_path"])) != r["sha256"] for r in records):
            raise ValueError("Prepared input does not match the crop audit; rebuild before extraction")
    summary = dataset_summary(records)
    print(json.dumps(summary, indent=2), flush=True)
    if not manifest:
        print("Specimen IDs are inferred from filenames. Review the exported inventory before scientific interpretation.", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    if args.inventory_only:
        # Never change metadata beside an existing bundle during an inventory-only audit.
        write_csv(output / "inventory.csv", records)
        write_json(output / "inventory_summary.json", summary)
        return

    import torch
    from transformers import AutoConfig, AutoImageProcessor, AutoModel

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device == "auto":
        device = "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA requested but unavailable; use --device cpu")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    options = {"cache_dir": str(project_path(args.cache_dir)), "revision": args.revision,
               "local_files_only": args.local_files_only, "trust_remote_code": False}
    model_name = str(project_path(Path(args.model))) if project_path(Path(args.model)).is_dir() else args.model
    try:
        config = AutoConfig.from_pretrained(model_name, **options)
        if config.model_type != "dinov3_vit":
            raise ValueError("This workflow requires a pretrained DINOv3 ViT checkpoint")
        resolved_revision = getattr(config, "_commit_hash", None)
        if resolved_revision:
            options["revision"] = resolved_revision
        processor = AutoImageProcessor.from_pretrained(model_name, use_fast=True, **options)
        model, loading = AutoModel.from_pretrained(model_name, config=config, use_safetensors=True,
                                                  output_loading_info=True, **options)
        if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise ValueError("Checkpoint did not load exactly; refusing partial/randomly initialized features")
    except OSError as exc:
        raise SystemExit(
            "Could not load the pretrained DINOv3 checkpoint. Accept access at "
            f"https://huggingface.co/{DEFAULT_MODEL}, then run .venv\\Scripts\\hf.exe auth login "
            "locally with a read token (never put a token in source or chat). "
            "For an approved offline download use --model <local-directory> --local-files-only. "
            f"Underlying error: {type(exc).__name__}"
        ) from None
    print(f"Frozen {model_name} on {device}; input {args.image_size}px", flush=True)
    features = extract_features(model, processor, [root / r["image_path"] for r in records],
                                size=args.image_size, batch_size=args.batch_size, device=device,
                                padding_value=args.padding_value)
    # Detect edits during the run rather than associating features with the wrong source hashes.
    if any(sha256(root / r["image_path"]) != r["sha256"] for r in records):
        raise ValueError("An input image changed during extraction; rerun in a new output directory")
    local_checkpoint_hashes = {}
    if Path(model_name).is_dir():
        local_checkpoint_hashes = {p.name: sha256(p) for p in sorted(Path(model_name).glob("*.safetensors"))}
    provenance = {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "images_root": str(root), "model": model_name, "requested_revision": args.revision,
        "resolved_revision": resolved_revision, "local_checkpoint_sha256": local_checkpoint_hashes,
        "feature": "last_hidden_state[:, 0, :] (CLS), L2 normalized", "trained": False,
        "device": device, "dtype": "float32", "image_size": args.image_size,
        "resize": f"PIL bicubic contain; centered padding value {args.padding_value}; no crop",
        "padding_value": args.padding_value, "crop_provenance": crop_audit,
        "processor": processor.to_dict(), "model_config": config.to_dict(),
        "batch_size": args.batch_size, "dataset_summary": summary,
        "metadata_source": "manifest" if manifest else "filename_inference",
        "manifest_sha256": sha256(manifest) if manifest else None,
        "python": platform.python_version(),
        "packages": {name: version(name) for name in ["torch", "torchvision", "transformers", "numpy", "Pillow"]},
    }
    write_csv(output / "image_index.csv", records)
    write_json(output / "run.json", provenance)
    save_bundle(output / "embeddings.npz", features, records, provenance)
    print(f"Saved {features.shape} frozen features to {output / 'embeddings.npz'}")


if __name__ == "__main__":
    main()
