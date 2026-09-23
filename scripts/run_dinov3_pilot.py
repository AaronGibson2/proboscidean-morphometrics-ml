"""Run the frozen DINOv3 pilot for upper/lower and RGB/grayscale datasets."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from dinov3_pipeline import DEFAULT_MODEL
from pipeline_utils import PROJECT_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["all", "upper", "lower"], default="all")
    parser.add_argument("--color", choices=["both", "rgb", "grayscale"], default="both")
    parser.add_argument("--preprocessing", choices=["crop_black_v2", "legacy"], default="crop_black_v2",
                        help="Reviewed conservative crops (default), or the original damaged-mask pilot")
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--permutations", type=int, default=9999)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default="main")
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.permutations < 0:
        parser.error("--permutations must be nonnegative")
    datasets = ["upper", "lower"] if args.dataset == "all" else [args.dataset]
    colors = ["rgb", "grayscale"] if args.color == "both" else [args.color]
    for position in datasets:
        source = "upper_m3_strict" if position == "upper" else "lower_m3"
        for color in colors:
            suffix = "_crop_black_v2" if args.preprocessing == "crop_black_v2" else ""
            run = f"outputs/dinov3/{position}_{color}{suffix}_{args.image_size}"
            images = (f"data/standardized/crop_black_v2/{position}/{color}"
                      if suffix else f"data/standardized/{source}/{color}")
            extract = [sys.executable, str(Path(__file__).with_name("05_extract_dinov3.py")),
                       "--images", images, "--tooth-position", f"{position}_m3",
                       "--output", run, "--image-size", str(args.image_size), "--batch-size", str(args.batch_size),
                       "--model", args.model, "--revision", args.revision]
            if suffix:
                extract += ["--padding-value", "0", "--crop-provenance", "outputs/qc/crop_black_v2/provenance.json"]
            for flag in ("inventory_only", "local_files_only", "overwrite"):
                if getattr(args, flag):
                    extract.append("--" + flag.replace("_", "-"))
            subprocess.run(extract, cwd=PROJECT_ROOT, check=True)
            if not args.inventory_only:
                analyze = [sys.executable, str(Path(__file__).with_name("06_analyze_dinov3.py")),
                           "--run-dir", run, "--permutations", str(args.permutations)]
                if args.overwrite:
                    analyze.append("--overwrite")
                subprocess.run(analyze, cwd=PROJECT_ROOT, check=True)
    print("Completed. Outputs are in outputs/dinov3.")


if __name__ == "__main__":
    main()
