"""Generate BioEncoder's interactive PCA/t-SNE views for a completed run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline_utils import BIOENCODER_DIR, CONFIG_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=BIOENCODER_DIR)
    parser.add_argument("--run-name", default="proboscidean_stage1")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    import numpy as np
    import bioencoder
    from sklearn import decomposition, manifold
    from bioencoder.vis import helpers

    # BioEncoder 1.0.5 divides every embedding dimension by its standard
    # deviation. Constant dimensions therefore become NaN on small datasets.
    # Keep constant dimensions centered at zero instead.
    def safe_dimension_reductions(data_table, perplexity, seed):
        values = np.asarray(data_table, dtype=np.float64)
        mean = np.mean(values, axis=0)
        std = np.std(values, axis=0)
        std[std < np.finfo(np.float64).eps] = 1.0
        normalized = np.nan_to_num((values - mean) / std)
        pca_object = decomposition.PCA(n_components=2)
        pca = pca_object.fit_transform(normalized)
        tsne = manifold.TSNE(
            n_components=2, perplexity=perplexity, random_state=seed,
            learning_rate="auto", method="exact", init=pca,
        ).fit_transform(normalized)
        return np.hstack((pca, tsne)), ["PC1", "PC2", "tSNE-0", "tSNE-1"], pca_object

    helpers.embbedings_dimension_reductions = safe_dimension_reductions
    bioencoder.configure(root_dir=str(args.work_dir), run_name=args.run_name)
    result = bioencoder.interactive_plots(
        config_path=str(CONFIG_DIR / "plot_stage1.yml"), overwrite=args.overwrite
    )
    if result is not None:
        _, coordinates = result
        plot_dir = args.work_dir / "plots" / args.run_name
        plot_dir.mkdir(parents=True, exist_ok=True)
        coordinates.to_csv(plot_dir / "embedding_coordinates.csv", index=False)

        import matplotlib.pyplot as plt
        palette = {"Love_Bone_Bed": "#d62728", "Mixsons_Bone_Bed": "#ff7f0e",
                   "Tyner_Farm": "#4c78a8"}
        figure, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
        for axis, x_name, y_name, title in (
            (axes[0], "PC1", "PC2", "PCA"),
            (axes[1], "tSNE-0", "tSNE-1", "t-SNE"),
        ):
            for class_name, group in coordinates.groupby("class_str"):
                axis.scatter(group[x_name], group[y_name], s=55, alpha=0.85,
                             color=palette.get(class_name), label=class_name.replace("_", " "))
            validation = coordinates[coordinates["dataset"] == "val"]
            axis.scatter(validation[x_name], validation[y_name], s=120, facecolors="none",
                         edgecolors="black", linewidths=1.5, label="validation")
            axis.set(title=title, xlabel=x_name, ylabel=y_name)
            axis.axhline(0, color="#dddddd", linewidth=0.7, zorder=0)
            axis.axvline(0, color="#dddddd", linewidth=0.7, zorder=0)
        handles, labels = axes[1].get_legend_handles_labels()
        figure.legend(handles, labels, loc="outside lower center", ncol=4, frameon=False)
        figure.suptitle(f"Proboscidean lower M3 embeddings — {args.run_name}")
        figure.savefig(plot_dir / "embedding_plot.png", dpi=180)
        plt.close(figure)
    print(f"Plots written below {args.work_dir}")
