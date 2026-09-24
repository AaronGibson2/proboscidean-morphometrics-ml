"""Build a local, image-based literature audit; no model inference or taxon prediction."""

from __future__ import annotations

import csv
import html
import json
from collections import Counter
from pathlib import Path

from PIL import Image

from pipeline_utils import PROJECT_ROOT, sha256
from prepare_conservative_crops import crop_source, read_source, to_rgb8

OUTPUT = PROJECT_ROOT / "outputs/morphology_literature_v1"
LAMBERT = "https://doi.org/10.1080/02724634.2023.2252021"


def read_json(relative):
    return json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))


def comparison_evidence(specimen_id, catalogs):
    """These are evidence categories, never new anatomical identifications."""
    record = catalogs.get(specimen_id)
    if specimen_id == "UF-212304":
        return "position_hold", "Resolve tooth position", "Catalog: floridanus; paper lists m1/m2, filenames claim m3.", LAMBERT
    if specimen_id in {"USNM-3083", "USNM-3084"}:
        return "published_reference", "Published floridanus reference", "Exact catalog number and third-molar position occur in Lambert (2023). Photo identity still needs verification.", LAMBERT
    if record:
        name = record["catalog_scientific_name"]
        if name == "Gomphotherium":
            return "catalog_gomphotherium", "Catalog: Gomphotherium", "Genus-level catalog label; species and photo identity are unverified.", record["record_url"]
        if "floridanus" in name:
            return "catalog_floridanus", "Catalog: floridanus", "Amebelodon/Stenobelodon placement is disputed; this is a catalog association.", record["record_url"]
        return "broad_catalog", "Catalog: Amebelodontinae", "Broad catalog identification; not a verified genus or species, and not proof of a second Love taxon.", record["record_url"]
    return "unresolved", "No exact reference verified", "Locality alone does not identify this tooth. Seek its collection record and associated material.", ""


def build():
    recipes = read_json("metadata/conservative_crops_v2.json")["images"]
    observations = read_json("metadata/morphology_observations_v1.json")["images"]
    catalog_doc = read_json("metadata/morphology_catalog_evidence_v1.json")
    catalogs = {r["specimen_id"]: r for r in catalog_doc["records"]}
    notes = {(r["position"], r["image_path"]): r for r in observations}
    expected = {(r["position"], r["image_path"]) for r in recipes}
    if len(notes) != len(observations) or expected != set(notes):
        raise ValueError("Observations must match crop recipes one-to-one")
    if len(catalogs) != len(catalog_doc["records"]):
        raise ValueError("Duplicate catalog evidence")
    # Check source identities before generating any new report content.
    for recipe in recipes:
        if sha256(PROJECT_ROOT / recipe["source"]) != recipe["source_sha256"]:
            raise ValueError(f'Source changed: {recipe["source"]}')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "images").mkdir(exist_ok=True)
    cards, rows, previews = [], {}, {}
    esc = html.escape
    for recipe in recipes:
        position = recipe["position"]
        note = notes[(position, recipe["image_path"])]
        specimen = note["specimen_id"]
        category, label, explanation, url = comparison_evidence(specimen, catalogs)
        pixels, _ = crop_source(read_source(PROJECT_ROOT / recipe["source"]), recipe)
        image = to_rgb8(pixels)
        turns = recipe.get("quarter_turns_ccw", 0)
        if turns not in (0, 1, 2, 3):
            raise ValueError("Invalid quarter turn")
        if turns:
            image = image.transpose({1: Image.Transpose.ROTATE_90, 2: Image.Transpose.ROTATE_180, 3: Image.Transpose.ROTATE_270}[turns])
        # No reflection, contrast stretching, retouching or anatomical segmentation.
        image.thumbnail((1600, 1000), Image.Resampling.LANCZOS)
        preview = f'images/{position}_{recipe["index"]:02d}.png'
        image.save(OUTPUT / preview)
        previews[(position, specimen)] = preview
        key = (position, specimen)
        if key not in rows:
            rows[key] = {"specimen_id": specimen, "filename_position": position + "_m3", "image_count": 0,
                         "evidence_category": category, "catalog_name": catalogs.get(specimen, {}).get("catalog_scientific_name", ""),
                         "evidence_note": explanation, "source_url": url,
                         "photo_identity_verified": "no", "new_morphological_assignment": "none"}
        rows[key]["image_count"] += 1
        source_link = f'<a href="{esc(url)}">Evidence source</a>' if url else "Collection record needed"
        cards.append(f'''<article data-position="{position}" data-category="{category}">
<h3>{esc(specimen)} <small>{position}; filename side: {esc(note['side_from_filename'])}</small></h3>
<a href="{preview}"><img loading="lazy" src="{preview}" alt="Occlusal photograph of {esc(specimen)}; {position}"></a>
<p class="badge {category}">{esc(label)}</p><p><b>Visible in this photo:</b> {esc(note['observation'])}</p>
<p><b>Identification evidence:</b> {esc(explanation)} {source_link}</p>
<details><summary>Photo and scoring status</summary><p>{esc(recipe['image_path'])}</p>
<p>Orientation unverified; anatomical character scores pending. Unknown does not mean absent.
Applied {turns} quarter turns counterclockwise; no reflection. Display size is not a physical scale.</p></details></article>''')
    with (OUTPUT / "specimen_evidence.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(next(iter(rows.values()))))
        writer.writeheader()
        writer.writerows(rows.values())
    counts = Counter(r["evidence_category"] for r in rows.values())
    summary = {"photos": len(recipes), "catalog_position_rows": len(rows), "evidence_counts": dict(counts),
               "new_taxonomic_assignments": 0, "source_hashes_verified": True,
               "warning": "Catalog associations are not verified photo identifications; historical analyses are unchanged."}
    (OUTPUT / "audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    examples = []
    for position, specimen, caption in [
        ("lower", "UF-38220", "Look for clover-like wear outlines versus rounder outlines on the other half. This is a visible pattern, not a diagnosis."),
        ("lower", "USNM-3083", "A published floridanus reference number already in our dataset. Raised cusps need different interpretation from worn loops.")]:
        examples.append(f'<figure><img src="{previews[(position, specimen)]}" alt="{specimen}"><figcaption><b>{specimen}</b>: {caption}</figcaption></figure>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tooth morphology: evidence and photo review</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f2ed;color:#202c32;font:17px/1.55 system-ui,sans-serif}main{max-width:1320px;margin:auto;padding:32px}
h1{font-size:clamp(30px,4vw,49px);line-height:1.12;max-width:900px}h2{margin-top:36px}a{color:#145c7a}small{display:block;font-size:14px;font-weight:400}
.intro{font-size:20px;max-width:960px}.callout{background:#fff0cb;border-left:5px solid #b97800;padding:18px 22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr));gap:22px}
article,figure{background:white;border:1px solid #d3d9d8;border-radius:12px;padding:20px;margin:0;overflow-wrap:anywhere}img{width:100%;height:285px;object-fit:contain;background:#000;border-radius:6px}figure img{height:235px}
.badge{display:inline-block;background:#e2edf1;padding:4px 10px;border-radius:6px;font-size:14px}.position_hold{background:#ffe1b1}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:12px;border-bottom:1px solid #d3d9d8}select{font:inherit;padding:8px;max-width:100%}.filters{display:flex;gap:20px;flex-wrap:wrap;margin:24px 0}article[hidden]{display:none}details{font-size:14px;color:#4e5e67}figcaption{margin-top:12px}.muted{color:#4e5e67}
</style><main><p class="muted">Literature + collection records + 37 photographs | 23 September 2026</p>
<h1>What do the teeth themselves tell us?</h1>
<p class="intro">We now have reference candidates and a checklist of anatomical features to examine. We have <b>not</b> established two species from these photos. Catalog labels, visible anatomy and DINOv3 similarity are different kinds of evidence.</p>
<p><a href="../../docs/molar-morphology-assessment-v1.md">Written assessment</a> &middot; <a href="../../docs/molar-taxonomy-primary-literature.md">Papers and character definitions</a> &middot; <a href="specimen_evidence.csv">Specimen evidence table</a></p>
<div class="callout"><b>Check UF-212304 first.</b> Its filenames say lower third molar, but a published description lists first and second molars for that catalog number. This is a conflict to resolve, not proof of which label is wrong. Do not use it as a confirmed m3 reference yet.</div>
<h2>The four things to compare</h2>
<table><tr><th>Look at</th><th>Plain-language question</th></tr>
<tr><td>Ridges and the back end</td><td>How many complete crosswise rows remain? Is the last piece a full row or a smaller heel?</td></tr>
<tr><td>Accessory cusps and wear outlines</td><td>Where are the small bumps? When worn, do they form clover-like outlines on one side or both?</td></tr>
<tr><td>Cusp subdivision</td><td>Are there real little cusps along a crest, or just cracks, wrinkles and staining?</td></tr>
<tr><td>Proportions and preservation</td><td>How long and wide is the complete crown? Are wear, breakage or camera angle changing its appearance?</td></tr></table>
<p>No single row count or clover-like outline is a reliable two-genus test. Use the <a href="../../docs/molar-taxonomy-primary-literature.md">sourced character guide</a> for overlap, terminology and alternatives.</p>
<h2>Start by looking, not by reading a score</h2><div class="grid">EXAMPLES</div>
<p class="muted">These examples differ in wear. They are teaching examples, not a matched diagnostic pair. Images are resized independently; tooth lengths cannot be compared on screen.</p>
<h2>Our current evidence</h2>
<p>Of 32 catalog/position rows: 12 have a Gomphotherium catalog label, 12 have only Amebelodontinae, 2 have floridanus catalog labels with a third molar included in the published specimen description, 2 match published floridanus reference molars, 1 has a tooth-position conflict, and 3 lack an exact verified reference. These are evidence categories, not predicted species.</p>
<h2>Review every photograph</h2><p>Notes are an assistant visual screening. Formal ridge, cusp, wear and orientation scores remain unverified. The original crop masks still apply; missing edges cannot be recovered here.</p>
<div class="filters"><label>Position <select id="position"><option value="all">Both</option><option value="upper">Upper</option><option value="lower">Lower</option></select></label>
<label>Evidence <select id="category"><option value="all">All evidence</option><option value="catalog_gomphotherium">Catalog: Gomphotherium</option><option value="broad_catalog">Broad Amebelodontinae</option><option value="catalog_floridanus">Catalog: floridanus</option><option value="published_reference">Published reference</option><option value="position_hold">Position conflict</option><option value="unresolved">No exact reference</option></select></label><span id="count" aria-live="polite"></span></div>
<div class="grid" id="cards">CARDS</div>
<p class="muted">Museum record data: University of Florida Vertebrate Paleontology via iDigBio; provider rights field CC4 BY-NC. Exact catalog-number matches do not authenticate photographs. No original analysis labels or results were changed.</p>
<script>const cards=[...document.querySelectorAll('article')];function filter(){const p=document.querySelector('#position').value,c=document.querySelector('#category').value;let n=0;cards.forEach(x=>{x.hidden=!((p==='all'||x.dataset.position===p)&&(c==='all'||x.dataset.category===c));if(!x.hidden)n++});document.querySelector('#count').textContent=n+' of '+cards.length+' photos'}document.querySelectorAll('select').forEach(x=>x.addEventListener('change',filter));filter();</script></main></html>'''
    (OUTPUT / "index.html").write_text(page.replace("EXAMPLES", "".join(examples)).replace("CARDS", "".join(cards)), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(OUTPUT / "index.html")


if __name__ == "__main__":
    build()
