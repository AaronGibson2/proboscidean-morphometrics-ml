"""Run BioEncoder stage-one training after validating the image dataset."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from pipeline_utils import BIOENCODER_DIR, CONFIG_DIR, image_files, infer_specimen_id, set_reproducible_seed


def validate_dataset(image_dir: Path) -> dict[str, dict[str, int]]:
    if not image_dir.is_dir():
        raise FileNotFoundError(f"Dataset directory does not exist: {image_dir}")
    non_directories = [path.name for path in image_dir.iterdir() if not path.is_dir()]
    if non_directories:
        raise ValueError(
            f"BioEncoder requires only class directories inside {image_dir}; move these files: {non_directories}"
        )
    summary = {}
    for class_dir in sorted(path for path in image_dir.iterdir() if path.is_dir()):
        files = list(image_files(class_dir))
        specimens = {infer_specimen_id(path.name) for path in files}
        if files:
            summary[class_dir.name] = {"images": len(files), "specimens": len(specimens)}
    if len(summary) != 3:
        raise ValueError(f"Expected exactly three non-empty site classes below {image_dir}; found {list(summary)}")
    too_small = {name: values for name, values in summary.items() if values["specimens"] < 2}
    if too_small:
        raise ValueError(f"Every class needs at least two specimens; too small: {too_small}")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True,
                        help="Tooth-position directory containing one folder per site")
    parser.add_argument("--work-dir", type=Path, default=BIOENCODER_DIR)
    parser.add_argument("--run-name", default="proboscidean_stage1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validation-percent", type=float, default=0.2)
    parser.add_argument("--minimum-training-images", type=int, default=1,
                        help="Post-split minimum; use 1 only for tiny exploratory datasets")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-image-level-split", action="store_true",
                        help="Acknowledge possible specimen leakage in BioEncoder's splitter")
    parser.add_argument("--allow-single-specimen-class", action="store_true",
                        help="Allow an exploratory run when a site has fewer than two specimens")
    return parser.parse_args()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        summary = validate_dataset(args.images)
    except ValueError as exc:
        if not args.allow_single_specimen_class or "Every class needs at least two specimens" not in str(exc):
            raise
        # Recompute the summary without relaxing validate_dataset's default scientific safeguard.
        summary = {}
        for class_dir in sorted(path for path in args.images.iterdir() if path.is_dir()):
            files = list(image_files(class_dir))
            if files:
                summary[class_dir.name] = {
                    "images": len(files),
                    "specimens": len({infer_specimen_id(path.name) for path in files}),
                }
        print("WARNING: a class has only one independent specimen; this run is exploratory only.")
    print("Dataset:", summary)
    repeated = Counter(infer_specimen_id(path.name) for path in image_files(args.images))
    repeated = {name: count for name, count in repeated.items() if count > 1}
    if repeated and not args.allow_image_level_split:
        raise SystemExit(
            "Repeated specimen IDs detected. BioEncoder's split can leak views across sets. "
            "Remove duplicate views or explicitly pass --allow-image-level-split for exploratory training."
        )
    if repeated:
        print("WARNING: image-level split acknowledged; do not report its validation metric as final.")
    set_reproducible_seed(args.seed)

    import bioencoder
    bioencoder.configure(root_dir=str(args.work_dir), run_name=args.run_name, create=True)
    bioencoder.split_dataset(
        image_dir=str(args.images), max_ratio=6, random_seed=args.seed,
        val_percent=args.validation_percent, min_per_class=args.minimum_training_images,
        overwrite=args.overwrite,
    )
    bioencoder.train(config_path=str(CONFIG_DIR / "train_stage1.yml"), overwrite=args.overwrite)
    bioencoder.swa(config_path=str(CONFIG_DIR / "swa_stage1.yml"), overwrite=args.overwrite)
    print(f"Stage-one run complete: {args.work_dir} / {args.run_name}")
