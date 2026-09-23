"""Fixed eight-condition frozen DINOv3 experiment; prepare and inspect regions first."""

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from dinov3_crown import crown_mask, crown_pool, holm_adjust, macro_locality, patch_coverage
from dinov3_pipeline import (DEFAULT_CACHE, DEFAULT_MODEL, aggregate_specimens, dataset_summary,
                             inventory, normalize, save_bundle, write_csv)
from pipeline_utils import PROJECT_ROOT, sha256, write_json
from prepare_conservative_crops import RECIPE, crop_source, data_uri, model_canvas, read_source

REGIONS = PROJECT_ROOT / "metadata/crown_regions_v1.json"
PROTOCOL = PROJECT_ROOT / "docs/dinov3-crown-experiment.md"
INPUTS = PROJECT_ROOT / "data/standardized/crown_regions_v1"
QC = PROJECT_ROOT / "outputs/qc/crown_regions_v1"
RUNS = PROJECT_ROOT / "outputs/dinov3_crown_v1"
REVISION = "5931719e67bbdb9737e363e781fb0c67687896bc"


def prepare(overwrite=False):
    if (QC / "provenance.json").exists() and not overwrite:
        raise FileExistsError("Prepared crown inputs exist; review them or explicitly use --overwrite")
    if any(RUNS.glob("*/embeddings.npz")):
        raise FileExistsError("Experiment already extracted; use a new dataset version before changing regions")
    crops = json.loads(RECIPE.read_text())["images"]
    regions = json.loads(REGIONS.read_text())["images"]
    keyed = {(r["position"], r["image_path"]): r for r in regions}
    if len(keyed) != len(regions) or set(keyed) != {(r["position"], r["image_path"]) for r in crops}:
        raise ValueError("Crown regions must cover the crop inventory exactly once")
    QC.mkdir(parents=True, exist_ok=True)
    records, panels, cards = [], [], []
    for crop in crops:
        source_path = PROJECT_ROOT / crop["source"]
        if sha256(source_path) != crop["source_sha256"]:
            raise ValueError(f"Source changed: {source_path}")
        pixels, retained = crop_source(read_source(source_path), crop)
        region = keyed[crop["position"], crop["image_path"]]
        previews = []
        for size in (224, 512):
            root = INPUTS / crop["position"] / str(size)
            path = root / "rgb" / crop["image_path"]
            mask_path = root / "masks" / crop["image_path"]
            image = model_canvas(pixels, crop, size=size)
            mask = crown_mask(pixels.shape, region["polygons"], retained, crop, size)
            coverage = patch_coverage(mask)
            if not (coverage >= .5).any():
                raise ValueError(f"Empty crown: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path)
            mask.save(mask_path)
            records.append({"position": crop["position"], "size": size, "image_path": crop["image_path"],
                            "image_sha256": sha256(path), "mask_sha256": sha256(mask_path),
                            "selected_patches": int((coverage >= .5).sum()), "source": crop["source"],
                            "source_sha256": crop["source_sha256"]})
            overlay = Image.new("RGBA", image.size)
            draw = ImageDraw.Draw(overlay)
            for y, x in np.argwhere(coverage >= .5):
                draw.rectangle((int(x*16), int(y*16), int(x*16+15), int(y*16+15)),
                               fill=(0, 220, 130, 75), outline=(0, 230, 150, 160))
            previews.append(Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB").resize((320, 320)))
        panel = Image.new("RGB", (1000, 360), "#eeeeee")
        ImageDraw.Draw(panel).text((10, 5), f'{crop["position"]} {crop["index"]:02d} {crop["image_path"]} | PHOTO / 224 PATCHES / 512 PATCHES', fill="black")
        panel.paste(model_canvas(pixels, crop).resize((320, 320)), (10, 30))
        for x, im in zip((340, 670), previews):
            panel.paste(im, (x, 30))
        panels.append(panel)
        cards.append(f'<img alt="Crown patch selection" src="{data_uri(panel)}">')
    for start in range(0, len(panels), 4):
        sheet = Image.new("RGB", (1000, 360*min(4, len(panels)-start)), "white")
        for offset, panel in enumerate(panels[start:start+4]):
            sheet.paste(panel, (0, offset*360))
        sheet.save(QC / f"regions_{start//4+1:02d}.jpg", quality=95)
    audit = {"crop_recipe_sha256": sha256(RECIPE), "region_recipe_sha256": sha256(REGIONS),
             "protocol_sha256": sha256(PROTOCOL), "images": records,
             "review": "Provisional assistant-drawn crown regions; anatomical review pending"}
    write_json(QC / "provenance.json", audit)
    (QC / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Crown patch review</title>'
        '<style>body{font:16px system-ui;margin:24px;background:#eee}img{display:block;max-width:100%;margin:18px 0}</style>'
        '<h1>Crown patches: provisional region review</h1><p>Left: unchanged input photograph. '
        'Middle/right: contributing patches at 224/512 pixels. Green patches have at least 50% crown coverage. '
        'Regions select features only; they do not remove pixels from the model input.</p>' + ''.join(cards), encoding="utf-8")
    print(f"Prepared {len(records)} inputs. Review {QC / 'index.html'}")


def run():
    import torch
    from transformers import AutoConfig, AutoImageProcessor, AutoModel

    names = [f"{position}_{feature}_{size}" for position in ("upper", "lower")
             for size in (224, 512) for feature in ("cls", "crown")]
    if any((RUNS / name / "embeddings.npz").exists() for name in names):
        raise FileExistsError("Experiment bundles already exist; preserve them and use a new version")
    audit = json.loads((QC / "provenance.json").read_text())
    for key, path in (("crop_recipe_sha256", RECIPE), ("region_recipe_sha256", REGIONS), ("protocol_sha256", PROTOCOL)):
        if audit[key] != sha256(path):
            raise ValueError("Recipes/protocol changed; prepare and review again before extraction")
    for r in audit["images"]:
        root = INPUTS / r["position"] / str(r["size"])
        for folder, key in (("rgb", "image_sha256"), ("masks", "mask_sha256")):
            if sha256(root / folder / r["image_path"]) != r[key]:
                raise ValueError("Prepared image or crown mask changed")
    options = {"cache_dir": str(DEFAULT_CACHE), "revision": REVISION, "local_files_only": True,
               "trust_remote_code": False}
    config = AutoConfig.from_pretrained(DEFAULT_MODEL, **options)
    if config.model_type != "dinov3_vit" or config.patch_size != 16:
        raise ValueError("Expected DINOv3 ViT with 16px patches")
    model, loading = AutoModel.from_pretrained(DEFAULT_MODEL, config=config, use_safetensors=True,
                                              output_loading_info=True, **options)
    if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
        raise ValueError("Checkpoint must load exactly")
    processor = AutoImageProcessor.from_pretrained(DEFAULT_MODEL, use_fast=True, **options)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.requires_grad_(False).eval().to(device)
    spec = importlib.util.spec_from_file_location("crown_analysis", Path(__file__).with_name("06_analyze_dinov3.py"))
    analysis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analysis)
    results = []
    for position in ("upper", "lower"):
        for size in (224, 512):
            root = INPUTS / position / str(size)
            records = inventory(root / "rgb", f"{position}_m3")
            expected = {r["image_path"]: r["image_sha256"] for r in audit["images"]
                        if r["position"] == position and r["size"] == size}
            if {r["image_path"]: r["sha256"] for r in records} != expected:
                raise ValueError("Input inventory differs from audited experiment")
            vectors = {"cls": [], "crown": []}
            token_dir = RUNS / f"{position}_patch_tokens_{size}"
            token_dir.mkdir(parents=True, exist_ok=True)
            for index, record in enumerate(records):
                with Image.open(root / "rgb" / record["image_path"]) as source:
                    image = source.convert("RGB")
                with Image.open(root / "masks" / record["image_path"]) as source:
                    coverage = patch_coverage(source)
                inputs = processor(images=[image], do_resize=False, do_center_crop=False, return_tensors="pt").to(device)
                with torch.inference_mode():
                    tokens = model(**inputs).last_hidden_state[0].float().cpu().numpy()
                vectors["cls"].append(normalize(tokens[:1])[0])
                vectors["crown"].append(crown_pool(tokens, coverage, config.num_register_tokens))
                np.savez_compressed(token_dir / f"{index:03d}.npz", spatial_tokens=tokens[1+config.num_register_tokens:],
                                    coverage=coverage, image_path=record["image_path"])
            for feature in ("cls", "crown"):
                name = f"{position}_{feature}_{size}"
                output = RUNS / name
                output.mkdir(parents=True, exist_ok=True)
                features = normalize(np.stack(vectors[feature]))
                specimen_features, specimens = aggregate_specimens(features, records)
                primary = macro_locality(specimen_features, specimens)
                provenance = {"model": DEFAULT_MODEL, "resolved_revision": getattr(config, "_commit_hash", None),
                              "requested_revision": REVISION, "trained": False, "device": device,
                              "images_root": str(root / "rgb"), "metadata_source": "filename_inference",
                              "feature": "CLS" if feature == "cls" else "coverage-weighted mean of normalized crown patch tokens",
                              "image_size": size, "padding_value": 0, "region_coverage_threshold": .5,
                              "num_register_tokens": config.num_register_tokens, "processor": processor.to_dict(),
                              "crop_provenance": audit, "dataset_summary": dataset_summary(records)}
                write_json(output / "run.json", provenance)
                write_csv(output / "image_index.csv", records)
                save_bundle(output / "embeddings.npz", features, records, provenance)
                summary = analysis.build_report(output)
                write_json(output / "analysis/locality_macro.json", primary)
                results.append({"run": name, "position": position, "feature": feature, "size": size,
                                **primary, "ordinary_accuracy": summary["nearest_neighbor"]["accuracy_eligible_only"],
                                "secondary_cosine_contrast": summary["within_minus_between"]})
                print(f'{name}: macro locality recall {primary["macro_recall"]:.3f}', flush=True)
    for result, adjusted in zip(results, holm_adjust([r["permutation_p"] for r in results])):
        result["holm_p_eight_conditions"] = adjusted
    write_json(RUNS / "comparison.json", results)
    write_csv(RUNS / "comparison.csv", [{k: v for k, v in r.items() if not isinstance(v, (dict, list))} for r in results])
    table = ''.join(f'<tr><td><a href="{r["run"]}/analysis/report.html">{r["run"]}</a></td>'
                    f'<td>{r["macro_recall"]:.1%}</td><td>{r["majority_macro_baseline"]:.1%}</td>'
                    f'<td>{r["ordinary_accuracy"]:.1%}</td><td>{r["permutation_p"]:.4f}</td>'
                    f'<td>{r["holm_p_eight_conditions"]:.4f}</td></tr>' for r in results)
    (RUNS / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>DINOv3 crown experiment</title>'
        '<style>body{font:16px/1.5 system-ui;max-width:1100px;margin:30px auto;padding:20px}th,td{padding:12px;border-bottom:1px solid #ccc}table{border-collapse:collapse}</style>'
        '<h1>Frozen DINOv3: crown patches and resolution</h1><p>Eight fixed RGB conditions; no training. '
        '<a href="../qc/crown_regions_v1/index.html">Review contributing crown patches</a>.</p>'
        '<p>Primary metric: mean of per-locality nearest-neighbor recall. Upper Tyner is unsupported as a query. '
        'Four lower Tyner photos represent two catalog IDs. Images of one individual cannot retrieve each other.</p>'
        '<table><tr><th>Run</th><th>Macro recall</th><th>Majority macro baseline</th><th>Ordinary agreement</th>'
        '<th>Raw permutation p</th><th>Holm p (8 tests)</th></tr>' + table + '</table>'
        '<p>Small exploratory sample, provisional crown regions, inferred specimen metadata; no held-out confirmation. '
        'Patch vectors still incorporate surrounding image context. Locality separation does not establish different species. '
        'Linked individual reports contain secondary cosine statistics and neighbor panels.</p>', encoding="utf-8")
    print(f"Completed: {RUNS / 'index.html'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="Rebuild preparation only, before feature extraction")
    args = parser.parse_args()
    if args.prepare_only:
        prepare(args.overwrite)
    else:
        if args.overwrite:
            parser.error("Completed experiments are immutable; --overwrite applies only to --prepare-only")
        run()
