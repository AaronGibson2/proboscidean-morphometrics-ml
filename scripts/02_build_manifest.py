"""Create a specimen-aware CSV inventory for a pipeline image directory."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from pipeline_utils import OUTPUTS_DIR, PREPROCESSED_DIR, records_for_directory, write_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=PREPROCESSED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output = args.output or OUTPUTS_DIR / "manifests" / f"{args.images.name}_manifest.csv"
    records = records_for_directory(args.images)
    if not records:
        raise SystemExit(f"No images found below {args.images}")
    write_manifest(output, records)
    specimens = {record.specimen_id for record in records}
    print(f"Wrote {len(records)} images representing {len(specimens)} specimens to {output}")
    print("Sites:", dict(Counter(record.site for record in records)))
