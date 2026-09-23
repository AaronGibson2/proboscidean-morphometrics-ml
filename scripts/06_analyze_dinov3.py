"""Analyze cached DINOv3 features at specimen level without training a classifier."""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
from importlib.metadata import version
from pathlib import Path

import numpy as np

from dinov3_pipeline import (aggregate_specimens, load_bundle, nearest_specimens,
                             project_path, separation_statistics, write_csv)
from pipeline_utils import PROJECT_ROOT, sha256, write_json


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--images", type=Path, help="Relocated image root; hashes must match the cached inputs")
    parser.add_argument("--permutations", type=int, default=9999)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--neighbors", type=int, default=3)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def build_report(run_dir: Path, *, images: Path | None = None, permutations: int = 9999,
                 seed: int = 42, neighbors: int = 3, overwrite: bool = False) -> dict:
    if permutations < 0 or neighbors < 1:
        raise ValueError("Permutations must be nonnegative; neighbors must be positive")
    output = run_dir / "analysis"
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise FileExistsError(f"Analysis exists: {output}; use --overwrite to regenerate")
    features, records, provenance = load_bundle(run_dir / "embeddings.npz")
    if len({r["tooth_position"] for r in records}) != 1:
        raise ValueError("Analyze upper and lower teeth separately")
    root = images or Path(provenance["images_root"])
    for record in records:
        path = (root / record["image_path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Image path escapes the dataset directory")
        if not path.is_file() or sha256(path) != record["sha256"]:
            raise ValueError(f"Image missing or changed since extraction: {path}")
    specimen_features, specimens = aggregate_specimens(features, records)
    if len(specimens) < 2:
        raise ValueError("Need at least two independent specimens to compare")
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".cache" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image, ImageOps
    from sklearn.decomposition import PCA

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "#faf9f6", "axes.facecolor": "#faf9f6"})
    stats = separation_statistics(specimen_features, specimens, permutations=permutations, seed=seed)
    stats.update({"images": len(records), "specimens": len(specimens),
                  "metadata_source": provenance["metadata_source"],
                  "model": provenance["model"], "resolved_revision": provenance.get("resolved_revision"),
                  "input_bundle_sha256": sha256(run_dir / "embeddings.npz"),
                  "specimen_aggregation": "Mean of normalized image feature vectors, then L2 normalization",
                  "feature": provenance.get("feature", "CLS"),
                  "analysis_packages": {name: version(name)
                                        for name in ("numpy", "scikit-learn", "matplotlib")}})
    nearest = nearest_specimens(specimen_features, specimens, k=neighbors)
    write_csv(output / "nearest_neighbors.csv", nearest)
    np.save(output / "specimen_embeddings.npy", specimen_features)
    pca = PCA(n_components=min(2, *specimen_features.shape), svd_solver="full")
    coordinates = pca.fit_transform(specimen_features)
    if coordinates.shape[1] < 2:
        coordinates = np.pad(coordinates, ((0, 0), (0, 1)))
    stats["pca_explained_variance_ratio"] = [float(v) if np.isfinite(v) else None
                                           for v in pca.explained_variance_ratio_]
    coordinate_rows = [{"specimen_id": r["specimen_id"], "site": r["site"],
                        "image_count": r["image_count"], "PC1": float(coordinates[i, 0]),
                        "PC2": float(coordinates[i, 1])} for i, r in enumerate(specimens)]
    write_csv(output / "specimen_coordinates.csv", coordinate_rows)
    similarities = np.clip(specimen_features @ specimen_features.T, -1, 1)
    labels = [r["specimen_id"] for r in specimens]
    write_csv(output / "cosine_similarity.csv",
              [{"specimen_id": label, **{other: float(similarities[i, j]) for j, other in enumerate(labels)}}
               for i, label in enumerate(labels)])
    sites = sorted({r["site"] for r in specimens})
    colors = {site: plt.get_cmap("tab10")(i % 10) for i, site in enumerate(sites)}
    title = run_dir.name.replace("_", " ")
    figure, axis = plt.subplots(figsize=(10, 7), layout="constrained")
    for site in sites:
        indices = [i for i, r in enumerate(specimens) if r["site"] == site]
        axis.scatter(coordinates[indices, 0], coordinates[indices, 1], color=colors[site],
                     s=75, edgecolors="white", label=f"{site.replace('_', ' ')} (n={len(indices)})")
    for i, row in enumerate(specimens):
        axis.annotate(row["specimen_id"], coordinates[i], xytext=(5, 5), textcoords="offset points", fontsize=8)
    axis.set(title=f"{title}\nFrozen DINOv3: one point per specimen", xlabel="PC1", ylabel="PC2")
    axis.legend(loc="best", fontsize=9)
    figure.savefig(output / "pca.png", dpi=160, bbox_inches="tight")
    plt.close(figure)

    display_labels = [f"{r['specimen_id']} | {r['site'].replace('_', ' ')}" for r in specimens]
    figure, axis = plt.subplots(figsize=(12, 10), layout="constrained")
    off_diagonal = similarities[np.triu_indices(len(specimens), 1)]
    # Mask self-similarity so the color range describes comparisons between specimens.
    shown = np.ma.array(similarities, mask=np.eye(len(specimens), dtype=bool))
    plot = axis.imshow(shown, vmin=float(off_diagonal.min()), vmax=float(off_diagonal.max()) + 1e-7,
                       cmap="viridis")
    axis.set_xticks(range(len(labels)), labels=labels, rotation=90, fontsize=8)
    axis.set_yticks(range(len(labels)), labels=display_labels, fontsize=8)
    axis.set_title(f"{title}\nCosine similarity between specimens (self-comparisons hidden)")
    figure.colorbar(plot, ax=axis, shrink=0.7, label="Cosine similarity")
    figure.savefig(output / "similarity.png", dpi=150, bbox_inches="tight")
    plt.close(figure)

    # All query images are represented by a fixed first image; ranking uses every image in the centroid.
    image_paths = {r["specimen_id"]: root / records[r["image_indices"][0]]["image_path"] for r in specimens}
    panel_names = []
    columns = min(neighbors, len(specimens) - 1) + 1
    for start in range(0, len(specimens), 5):
        page = specimens[start:start + 5]
        figure, axes = plt.subplots(len(page), columns, figsize=(3.3 * columns, 3.0 * len(page)),
                                    squeeze=False, layout="constrained")
        for row_index, query in enumerate(page):
            matches = [r for r in nearest if r["query_specimen"] == query["specimen_id"]]
            cells = [(query["specimen_id"], query["site"], "Query")]
            cells.extend((r["neighbor_specimen"], r["neighbor_site"],
                          f"#{r['rank']} | cosine {r['cosine_similarity']:.3f}") for r in matches)
            for column, (specimen_id, site, caption) in enumerate(cells):
                with Image.open(image_paths[specimen_id]) as source:
                    axes[row_index, column].imshow(ImageOps.exif_transpose(source).convert("RGB"))
                axes[row_index, column].set_title(f"{caption}\n{specimen_id}\n{site.replace('_', ' ')}",
                                                  fontsize=9, color=colors[site])
                axes[row_index, column].axis("off")
        figure.suptitle("Nearest independent specimens\nOne representative image shown; all images contribute to each specimen vector")
        name = f"neighbors_{start // 5 + 1:02d}.png"
        figure.savefig(output / name, dpi=120, bbox_inches="tight")
        plt.close(figure)
        panel_names.append(name)
    write_json(output / "summary.json", stats)
    limitations = ["Exploratory visual similarity does not establish taxonomic identity or anatomical homology.",
                   "Locality, wear, staining, preservation, and photography may be confounded.",
                   "PCA is a display only; statistics use the original feature space.",
                   "Permutation results assume exchangeable specimen labels and are not corrected across runs.",
                   "Nearest-neighbor accuracy excludes queries with no same-site reference; it is not three-site accuracy."]
    if provenance["metadata_source"] == "filename_inference":
        limitations.insert(0, "Specimen IDs were inferred from filenames and require confirmation against collection records.")
    unsupported = stats["nearest_neighbor"]["unsupported_specimens"]
    if unsupported:
        limitations.append("No same-site reference for: " + ", ".join(unsupported))
    lines = [f"# {title}", "", f"{len(records)} images; {len(specimens)} independent catalog IDs.", "",
             f"Frozen pretrained DINOv3 features ({provenance.get('feature', 'CLS')}); no training or fine-tuning.", "",
             f"Within minus between-site mean cosine: {stats['within_minus_between']}",
             f"One-sided specimen-label permutation p: {stats['permutation_p_one_sided']}",
             f"Nearest-neighbor results: {json.dumps(stats['nearest_neighbor'])}", "",
             *[f"- {item}" for item in limitations], ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    cards = []
    for name in ["pca.png", "similarity.png", *panel_names]:
        encoded = base64.b64encode((output / name).read_bytes()).decode("ascii")
        cards.append(f'<img alt="{html.escape(name)}" src="data:image/png;base64,{encoded}">')
    document = ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
                f"<title>{html.escape(title)}</title><style>body{{max-width:1200px;margin:40px auto;padding:0 24px;"
                "font:16px/1.6 system-ui;background:#faf9f6;color:#24312e}}img{width:100%;margin:18px 0}"
                "pre{white-space:pre-wrap;background:#efeee9;padding:20px;border-radius:12px}</style>"
                f"<h1>{html.escape(title)}</h1><pre>{html.escape(chr(10).join(lines[2:]))}</pre>"
                + "".join(cards) + "</html>")
    (output / "report.html").write_text(document, encoding="utf-8")
    print(f"Report: {output / 'report.html'}", flush=True)
    return stats


if __name__ == "__main__":
    args = parse_args()
    build_report(project_path(args.run_dir), images=project_path(args.images) if args.images else None,
                 permutations=args.permutations, seed=args.seed, neighbors=args.neighbors, overwrite=args.overwrite)
