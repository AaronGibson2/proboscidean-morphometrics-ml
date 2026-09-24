"""Export the morphology review as a GitHub gallery and standalone HTML snapshot."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from PIL import Image

from build_morphology_review import OUTPUT, build, comparison_evidence, read_json
from pipeline_utils import PROJECT_ROOT, sha256

DESTINATION = PROJECT_ROOT / "docs/morphology-gallery-v1"
GITHUB = "https://github.com/AaronGibson2/proboscidean-morphometrics-ml/blob/morphology/literature-audit-v1"


def export():
    build()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    (DESTINATION / "images").mkdir(exist_ok=True)
    page = (OUTPUT / "index.html").read_text(encoding="utf-8")
    observations = read_json("metadata/morphology_observations_v1.json")["images"]
    catalogs = {r["specimen_id"]: r for r in read_json("metadata/morphology_catalog_evidence_v1.json")["records"]}
    introduction = """# Tooth morphology photo gallery

This preserves the 23 September 2026 literature and photo review, including all **37 photographs**, observations, catalog evidence and unresolved identifications. No new species assignments were made.

**Scroll down to view the teeth directly on GitHub.** For the original interactive layout and filters, open [index.html](index.html), select **Download raw file**, and open the downloaded file in your browser. All photographs and the evidence CSV are embedded in that HTML file; no Python, model weights or additional image downloads are needed. Links to papers and written guides require internet access.

[Written assessment](../molar-morphology-assessment-v1.md) | [Primary-literature guide](../molar-taxonomy-primary-literature.md) | [Specimen evidence CSV](specimen_evidence.csv)

## How to read the photographs

Look for complete crosswise ridges, smaller accessory cusps, clover-like wear outlines and the terminal crown structure. Use combinations of features; ridge counts and cusp patterns overlap between taxa. Images are independently resized, so on-screen lengths are not comparable physical measurements.

These JPEGs are compressed viewing copies of the reviewed crops, with the recorded quarter turns and no reflection. They retain the existing crop exclusions. They are not measurement inputs or replacements for the original photographs. Assistant observations are preliminary; anatomical orientation and formal character scores remain unverified.

**Priority discrepancy:** UF 212304's filenames indicate m3, while a published specimen description lists m1/m2. Resolve the position before using those two photos as confirmed third-molar references.

## Evidence overview

The 32 catalog/position rows comprise 12 Gomphotherium catalog associations, 12 broad Amebelodontinae associations, 2 floridanus catalog candidates, 2 published floridanus reference numbers, 1 tooth-position conflict and 3 unresolved reference identities. These are evidence categories, not predicted species. Exact catalog-number matches do not authenticate the photographs.

Museum catalog data: University of Florida Vertebrate Paleontology via iDigBio; provider rights field CC4 BY-NC. That attribution concerns catalog data, not a new license for the specimen photographs.

"""
    sections = [introduction]
    for position, title in [("upper", "Upper teeth"), ("lower", "Lower teeth")]:
        sections.append(f"## {title}\n\n")
        for note in observations:
            if note["position"] != position:
                continue
            stem = f"{position}_{note['recipe_index']:02d}"
            original = f"images/{stem}.png"
            relative = f"images/{stem}.jpg"
            destination = DESTINATION / relative
            with Image.open(OUTPUT / original) as image:
                # No geometric changes, contrast processing or removal of image content.
                image.convert("RGB").save(destination, quality=85, subsampling=0, optimize=True)
            uri = "data:image/jpeg;base64," + base64.b64encode(destination.read_bytes()).decode("ascii")
            page = page.replace(f'src="{original}"', f'src="{uri}"')
            # Embedded previews can be saved without depending on a remote image path.
            page = page.replace(f'href="{original}"', f'download="{stem}.jpg" href="#" onclick="this.href=this.querySelector(\'img\').src"')
            _, label, explanation, source = comparison_evidence(note["specimen_id"], catalogs)
            evidence_link = f" [Evidence source]({source})." if source else ""
            sections.append(
                f"### {note['specimen_id']} - filename side: {note['side_from_filename']}\n\n"
                f"![{note['specimen_id']}, {position}, {note['side_from_filename']}](images/{stem}.jpg)\n\n"
                f"**Visible in this photo:** {note['observation']}\n\n"
                f"**{label}:** {explanation}{evidence_link}\n\n"
                f"Photo: `{note['image_path']}`\n\n"
            )
    for name in ("molar-morphology-assessment-v1.md", "molar-taxonomy-primary-literature.md"):
        page = page.replace(f'../../docs/{name}', f'{GITHUB}/docs/{name}')
    csv_bytes = (OUTPUT / "specimen_evidence.csv").read_text(encoding="utf-8").encode("utf-8")
    (DESTINATION / "specimen_evidence.csv").write_bytes(csv_bytes)
    csv_uri = "data:text/csv;base64," + base64.b64encode(csv_bytes).decode("ascii")
    page = page.replace('href="specimen_evidence.csv"', f'download="specimen_evidence.csv" href="{csv_uri}"')
    page = page.replace('<h2>Review every photograph</h2>', '<h2>Review every photograph</h2><p>Shareable snapshot: compressed viewing copies. Click a photo to save its JPEG. The original analysis images are unchanged.</p>')
    (DESTINATION / "index.html").write_text(page, encoding="utf-8")
    (DESTINATION / "README.md").write_text("".join(sections), encoding="utf-8")
    inputs = ["metadata/conservative_crops_v2.json", "metadata/morphology_observations_v1.json", "metadata/morphology_catalog_evidence_v1.json"]
    artifacts = [DESTINATION / "index.html", DESTINATION / "README.md", DESTINATION / "specimen_evidence.csv", *sorted((DESTINATION / "images").glob("*.jpg"))]
    provenance = {"review_date": "2026-09-23", "photograph_count": len(observations),
                  "image_encoding": "JPEG quality 85, no chroma subsampling; viewing derivatives of hash-verified source crops",
                  "input_sha256": {p: sha256(PROJECT_ROOT / p) for p in inputs},
                  "artifact_sha256": {p.relative_to(DESTINATION).as_posix(): sha256(p) for p in artifacts}}
    (DESTINATION / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(observations)} photographs to {DESTINATION}")
    print(f"Standalone HTML: {(DESTINATION / 'index.html').stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    export()
