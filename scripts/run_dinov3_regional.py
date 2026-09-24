"""Run the fixed regional experiment from audited cached 512px patch features."""

import argparse
import csv
import html
import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from threadpoolctl import threadpool_limits

from dinov3_crown import holm_adjust, patch_coverage
from dinov3_pipeline import aggregate_specimens, load_bundle, normalize, write_csv
from dinov3_regional import (compare_regions, exact_retrieval, mutual_matches,
                             regional_features, specimen_similarity)
from pipeline_utils import PROJECT_ROOT, infer_side, sha256, write_json

ROOT = PROJECT_ROOT
CACHE = ROOT / "outputs/dinov3_crown_v1"
OUT = ROOT / "outputs/dinov3_regional_v1"
PROTOCOL = ROOT / "docs/dinov3-regional-protocol-v1.md"
SPECIMENS = ROOT / "metadata/specimen_review_v1.csv"
IMAGES = ROOT / "metadata/image_review_v1.csv"
MANIFEST = ROOT / "metadata/regional_inputs_v1.json"
METHODS = ("cls", "regional_mean", "regional_patch")
COLORS = ("#ffbc42", "#4ed8b5", "#bc9bff")


def validate_inputs():
    prepared, hashes = {}, {}
    crops_path = ROOT / "metadata/conservative_crops_v2.json"
    regions_path = ROOT / "metadata/crown_regions_v1.json"
    crops = json.loads(crops_path.read_text())["images"]
    crop_lookup = {(r["position"], r["image_path"]): r for r in crops}
    for position in ("upper", "lower"):
        bundle = CACHE / f"{position}_cls_512/embeddings.npz"
        crown_bundle = CACHE / f"{position}_crown_512/embeddings.npz"
        features, records, provenance = load_bundle(bundle)
        crown_features, crown_records, crown_provenance = load_bundle(crown_bundle)
        if records != crown_records or provenance["trained"] is not False or crown_provenance["trained"] is not False:
            raise ValueError("Frozen CLS/crown inventories must agree")
        if (provenance["resolved_revision"] != "5931719e67bbdb9737e363e781fb0c67687896bc"
                or crown_provenance["resolved_revision"] != provenance["resolved_revision"]):
            raise ValueError("Unexpected checkpoint revision")
        audit = provenance["crop_provenance"]
        if (audit["crop_recipe_sha256"] != sha256(crops_path)
                or audit["region_recipe_sha256"] != sha256(regions_path)):
            raise ValueError("Crop/region recipe changed since extraction")
        audit_images = {r["image_path"]: r for r in audit["images"]
                        if r["position"] == position and r["size"] == 512}
        image_root = ROOT / f"data/standardized/crown_regions_v1/{position}/512/rgb"
        patch_root = CACHE / f"{position}_patch_tokens_512"
        expected_files = {f"{i:03d}.npz" for i in range(len(records))}
        if {p.name for p in patch_root.glob('*.npz')} != expected_files:
            raise ValueError("Patch inventory mismatch")
        regional, image_paths = [], []
        for i, record in enumerate(records):
            path = image_root / record["image_path"]
            mask_path = image_root.parent / "masks" / record["image_path"]
            audited = audit_images[record["image_path"]]
            if sha256(path) != record["sha256"] or sha256(mask_path) != audited["mask_sha256"]:
                raise ValueError("Input image/mask changed")
            crop = crop_lookup[position, record["image_path"]]
            if sha256(ROOT / crop["source"]) != crop["source_sha256"]:
                raise ValueError("Original source changed")
            token_path = patch_root / f"{i:03d}.npz"
            with np.load(token_path, allow_pickle=False) as cached:
                if str(cached["image_path"]) != record["image_path"]:
                    raise ValueError("Patch/image order mismatch")
                coverage = cached["coverage"]
                with Image.open(mask_path) as mask:
                    np.testing.assert_allclose(coverage, patch_coverage(mask), atol=1e-7)
                region = regional_features(cached["spatial_tokens"], coverage)
            pooled = normalize(np.average(region["vectors"], axis=0,
                                           weights=region["weights"])[None])[0]
            np.testing.assert_allclose(pooled, crown_features[i], atol=2e-6)
            regional.append(region)
            image_paths.append(path)
            hashes[token_path.relative_to(ROOT).as_posix()] = sha256(token_path)
        specimen_features, specimens = aggregate_specimens(features, records)
        if len(specimens) != 16 or len(records) != (17 if position == "upper" else 20):
            raise ValueError("This protocol requires the original full specimen inventory")
        prepared[position] = {"records": records, "specimens": specimens, "regional": regional,
                              "image_paths": image_paths, "cls": specimen_features @ specimen_features.T}
        for path in (bundle, crown_bundle):
            hashes[path.relative_to(ROOT).as_posix()] = sha256(path)
    for path in (PROTOCOL, crops_path, regions_path, ROOT / "metadata/locality_group_hypothesis_v1.json"):
        hashes[path.relative_to(ROOT).as_posix()] = sha256(path)
    return prepared, hashes, crop_lookup


def draft_metadata(prepared, crop_lookup):
    image_rows, specimen_rows = [], []
    for position, data in prepared.items():
        for record in data["records"]:
            image_rows.append({"tooth_position": record["tooth_position"],
                               "specimen_id": record["specimen_id"], "site": record["site"],
                               "image_path": record["image_path"],
                               "source_path": crop_lookup[position, record["image_path"]]["source"],
                               "side_inferred": infer_side(record["image_path"]),
                               "metadata_status": "filename_inferred_unverified",
                               "anatomical_orientation": "unknown", "wear": "unknown",
                               "preservation": "unknown", "photography_batch": "unknown",
                               "scale_mm_per_pixel": "unknown", "reviewer": "", "notes": ""})
        for specimen in data["specimens"]:
            records = [data["records"][i] for i in specimen["image_indices"]]
            specimen_rows.append({"specimen_id": specimen["specimen_id"],
                "tooth_position": specimen["tooth_position"], "site": specimen["site"],
                "institution_prefix_inferred": specimen["specimen_id"].split('-')[0],
                "sides_inferred": ';'.join(sorted({infer_side(r['image_path']) for r in records})),
                "image_count": len(records), "taxon": "unknown", "taxon_evidence": "",
                "catalog_id_verified": "no", "locality_verified": "no",
                "metadata_status": "filename_inferred_unverified", "reviewer": "", "notes": ""})
    for path, rows, keys in ((SPECIMENS, specimen_rows, ("tooth_position", "specimen_id")),
                             (IMAGES, image_rows, ("tooth_position", "image_path"))):
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as handle:
                existing = list(csv.DictReader(handle))
            if len(existing) != len(rows) or {tuple(r[k] for k in keys) for r in existing} != {tuple(r[k] for k in keys) for r in rows}:
                raise ValueError("Existing review inventory differs; do not overwrite user annotations")
        else:
            write_csv(path, rows)


def prepare():
    prepared, hashes, crop_lookup = validate_inputs()
    draft_metadata(prepared, crop_lookup)
    manifest = {"protocol": PROTOCOL.relative_to(ROOT).as_posix(), "input_hashes": hashes,
                "metadata_use": "Drafts are for review only; analysis labels remain the original cached labels."}
    if MANIFEST.exists():
        if json.loads(MANIFEST.read_text()) != manifest:
            raise ValueError("Prepared inputs/protocol changed; use a new experiment version")
    else:
        write_json(MANIFEST, manifest)
    return prepared, manifest


def draw_pair(data, i, j, destination, title):
    a, b = data["regional"][i], data["regional"][j]
    comparison = compare_regions(a, b, "regional_patch")
    matches = mutual_matches(a, b, comparison["reversed"])
    panel = Image.new("RGB", (1104, 600), "#111827")
    draw = ImageDraw.Draw(panel)
    draw.text((24, 14), title, fill="white")
    for region, path, offset in ((a, data["image_paths"][i], 24), (b, data["image_paths"][j], 568)):
        with Image.open(path) as im:
            panel.paste(im.convert("RGB"), (offset, 48))
        for (x, y), band in zip(region["xy"], region["bands"]):
            display_band = 2-int(band) if region is b and comparison["reversed"] else int(band)
            draw.rectangle((offset+x-7, 48+y-7, offset+x+7, 48+y+7), outline=COLORS[display_band])
    chosen = []
    for band in range(3):
        band_chosen = []
        for match in matches:
            ai, bi, _, k = match
            if k != band:
                continue
            if all(np.linalg.norm(a["xy"][ai]-a["xy"][old[0]]) >= 48
                   and np.linalg.norm(b["xy"][bi]-b["xy"][old[1]]) >= 48 for old in band_chosen):
                band_chosen.append(match)
            if len(band_chosen) == 2:
                break
        chosen.extend(band_chosen)
    for number, (ai, bi, score, band) in enumerate(chosen, 1):
        x1, y1 = a["xy"][ai] + [24, 48]
        x2, y2 = b["xy"][bi] + [568, 48]
        draw.line((x1, y1, x2, y2), fill=COLORS[band], width=2)
        for x, y in ((x1, y1), (x2, y2)):
            draw.ellipse((x-6, y-6, x+6, y+6), fill=COLORS[band], outline="white")
            draw.text((x+8, y-10), str(number), fill="white", stroke_width=1, stroke_fill="black")
    mutual_fraction = 2*len(matches)/(len(a["vectors"])+len(b["vectors"]))
    draw.text((24, 574), f'Geometric regions only | band order reversed: {comparison["reversed"]} | mutual-patch fraction: {mutual_fraction:.1%}', fill="white")
    panel.save(destination)
    return {"representative_patch_score": comparison["score"],
            "band_order_reversed": comparison["reversed"], "mutual_patch_fraction": mutual_fraction,
            "displayed_matches": len(chosen), "region_scores": comparison["region_scores"]}


def write_reports(results, gallery_cards):
    lines = ["# DINOv3 regional matching v1 results", "",
             "Frozen 512px features; geometric crown regions awaiting anatomical review. No training.", "",
             "| Position | Target | Method | Macro recall | Correct / eligible | Raw exact p | Holm p (12) | Change from CLS |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in results:
        lines.append(f'| {r["position"]} | {r["target"]} | {r["method"]} | {r["macro_recall"]:.1%} | '
                     f'{r["correct"]}/{r["eligible_specimens"]} ({r["ordinary_accuracy"]:.1%}) | '
                     f'{r["exact_p"]:.4f} | {r["holm_p_twelve_conditions"]:.4f} | {r["macro_delta_from_cls"]*100:+.1f} pp |')
    lines.extend(["", "## Recall by original locality or provisional group", "",
                  "| Position / target / method | Group | Correct / specimens | Recall |",
                  "| --- | --- | ---: | ---: |"])
    for r in results:
        for name, v in r["per_group"].items():
            count = f'{v["correct"]}/{v["specimens"]}' if v["eligible"] else f'Unsupported ({v["specimens"]} ID)'
            recall = f'{v["recall"]:.1%}' if v["eligible"] else "Not scored"
            lines.append(f'| {r["position"]} / {r["target"]} / {r["method"]} | {name} | {count} | {recall} |')
    notes = ("Regional methods use three geometric bands, not verified anatomical landmarks. "
             "Regional patch scoring allows many-to-one matches and maximizes over forward/reversed band order. "
             "All cross-image pairs are averaged per catalog-ID pair; queries exclude the entire catalog ID. "
             "Locality upper Tyner is unsupported as a query. Exact tests enumerate 7,280 upper-locality, "
             "10,920 lower-locality or 1,820 provisional-group label assignments. Holm correction covers "
             "all 12 conditions in this experiment, not earlier exploratory choices. Baselines: upper locality "
             "80% ordinary / 50% macro, lower locality 75% / 33.3%, provisional groups 75% / 50%. "
             "Differences from CLS are descriptive, not paired significance tests. Exchangeable labels are "
             "assumed; photography/wear confounding is uncontrolled. This reuses previously inspected specimens "
             "and has no independent confirmation set or verified species identifications. Metadata inventories "
             "remain draft; no wear/preservation-adjusted analysis was performed.")
    lines.extend(["", "## Interpretation limits", "", notes, ""])
    (OUT / "report.md").write_text('\n'.join(lines), encoding="utf-8")
    style = ('<style>body{font:16px/1.6 system-ui;max-width:1250px;margin:30px auto;padding:0 20px;background:#f8fafc;color:#172033}'
             'table{border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #ccd3dd}'
             '.scroll{overflow:auto}img{width:100%;height:auto}article{margin:30px 0;background:white;padding:16px}'
             'a{color:#1255aa}</style>')
    head = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    headers = ["Position", "Target", "Method", "Macro", "Correct", "Raw p", "Holm p (12)", "Change from CLS"]
    rows = []
    for r in results:
        cells = [r['position'], r['target'], r['method'], f'{r["macro_recall"]:.1%}',
                 f'{r["correct"]}/{r["eligible_specimens"]}', f'{r["exact_p"]:.4f}',
                 f'{r["holm_p_twelve_conditions"]:.4f}', f'{r["macro_delta_from_cls"]*100:+.1f} pp']
        rows.append('<tr>'+''.join('<td>'+html.escape(c)+'</td>' for c in cells)+'</tr>')
    (OUT / "index.html").write_text(head+'<title>Regional DINOv3 comparison</title>'+style+
        '<h1>Regional crown matching</h1><p>Three fixed methods, two positions, two questions. No training.</p>'
        '<p><a href="review.html">Review proposed patch correspondences (locality labels hidden)</a> | '
        '<a href="report.md">Detailed results and per-group recall</a> | <a href="predictions.csv">All specimen predictions</a> | '
        '<a href="comparison.json">Exact numerical results</a></p><div class="scroll"><table><tr>'+
        ''.join('<th>'+h+'</th>' for h in headers)+'</tr>'+''.join(rows)+'</table></div><p>'+html.escape(notes)+
        '</p><p><a href="../dinov3_group_hypothesis_v1/index.html">Previous provisional-group report</a></p></html>', encoding="utf-8")
    (OUT / "review.html").write_text(head+'<title>Tooth correspondence review</title>'+style+
        '<h1>Proposed crown correspondences</h1><p>Locality labels and catalog IDs are hidden here. '
        'Specimen markings can still reveal identity. Each card shows a distinct nearest-neighbor specimen pair '
        'from at least one method, using its first photograph. Lines show up to two reciprocal patch matches '
        'per geometric region; colors do not identify anatomical structures. Unshown photographs also contribute '
        'to specimen scores. Record whether matches follow corresponding anatomy, wear, or preservation.</p>'
        '<p><a href="review_ratings.csv">Blank ratings table</a> | <a href="region_diagnostics.csv">Region diagnostics</a> | '
        '<a href="review_key.csv">Reveal specimen identities</a> | <a href="index.html">Quantitative results</a></p>'+
        ''.join(gallery_cards)+'</html>', encoding="utf-8")


def run():
    if OUT.exists():
        raise FileExistsError("Regional output exists; preserve it and use a new version")
    prepared, manifest = prepare()
    OUT.mkdir(parents=True)
    (OUT / "pairs").mkdir()
    mapping = json.loads((ROOT / "metadata/locality_group_hypothesis_v1.json").read_text())["groups"]
    results, predictions, diagnostics, pair_rows, ratings, cards = [], [], [], [], [], []
    for position, data in prepared.items():
        records, specimens, regions = data['records'], data['specimens'], data['regional']
        for record, region in zip(records, regions):
            diagnostics.append({"position": position, "image_path": record['image_path'],
                "specimen_id": record['specimen_id'], "patches": len(region['vectors']),
                **{f"region_{k+1}_patches": n for k, n in enumerate(region['region_patch_counts'])},
                "axis_eigenvalue_ratio": region['axis_eigenvalue_ratio'], "anatomy_verified": False})
        matrices = {'cls': data['cls']}
        for method in METHODS[1:]:
            image_scores = np.full((len(records), len(records)), np.nan)
            for i, j in itertools.combinations(range(len(records)), 2):
                if records[i]['specimen_id'] != records[j]['specimen_id']:
                    image_scores[i, j] = image_scores[j, i] = compare_regions(regions[i], regions[j], method)['score']
            matrices[method] = specimen_similarity(image_scores, records, specimens)
        np.savez_compressed(OUT / f'{position}_similarities.npz', **matrices,
                            specimen_ids=np.array([s['specimen_id'] for s in specimens]))
        neighbors = {}
        for target in ('locality', 'provisional_group'):
            labels = [s['site'] if target == 'locality' else mapping[s['site']] for s in specimens]
            baseline = None
            for method in METHODS:
                stats = exact_retrieval(matrices[method], specimens, labels)
                nearest = stats.pop('nearest_indices')
                neighbors[method] = nearest
                if baseline is None:
                    baseline = stats['macro_recall']
                result = {'position': position, 'target': target, 'method': method, **stats,
                          'macro_delta_from_cls': stats['macro_recall']-baseline}
                results.append(result)
                for i, j in enumerate(nearest):
                    predictions.append({'position': position, 'target': target, 'method': method,
                        'specimen_id': specimens[i]['specimen_id'], 'original_site': specimens[i]['site'],
                        'label': labels[i], 'neighbor_specimen': specimens[j]['specimen_id'],
                        'neighbor_original_site': specimens[j]['site'], 'neighbor_label': labels[j],
                        'eligible': stats['per_group'][labels[i]]['eligible'], 'correct': labels[i] == labels[j],
                        'similarity': float(matrices[method][i, j])})
                print(f'{position} {target} {method}: macro={stats["macro_recall"]:.3f} exact_p={stats["exact_p"]:.4f}', flush=True)
        unique_pairs = sorted({tuple(sorted((i, j))) for nearest in neighbors.values() for i, j in enumerate(nearest)})
        rng = np.random.default_rng(42)
        codes = rng.permutation(np.arange(1, len(specimens)+1))
        for pair_index in rng.permutation(len(unique_pairs)):
            si, sj = unique_pairs[pair_index]
            i, j = specimens[si]['image_indices'][0], specimens[sj]['image_indices'][0]
            pair_id = f'{position[0].upper()}P{len(pair_rows)+1:03d}'
            code_a, code_b = f'{position[0].upper()}{codes[si]:02d}', f'{position[0].upper()}{codes[sj]:02d}'
            picture = Path('pairs') / f'{pair_id}.png'
            info = draw_pair(data, i, j, OUT / picture, f'{pair_id} | {position} M3 | {code_a} / {code_b}')
            pair_rows.append({'pair_id': pair_id, 'position': position, 'code_a': code_a, 'code_b': code_b,
                'specimen_a': specimens[si]['specimen_id'], 'specimen_b': specimens[sj]['specimen_id'],
                'site_a': specimens[si]['site'], 'site_b': specimens[sj]['site'],
                'image_a': records[i]['image_path'], 'image_b': records[j]['image_path'],
                **{k: v for k, v in info.items() if k != 'region_scores'},
                **{f'region_{k+1}_score': score for k, score in enumerate(info['region_scores'])}})
            ratings.append({'pair_id': pair_id, 'corresponding_anatomy': 'unknown', 'similar_wear': 'unknown',
                            'similar_preservation': 'unknown', 'patch_matches_anatomically_valid': 'unknown',
                            'reviewer': '', 'notes': ''})
            cards.append(f'<article><h2>{pair_id}: {code_a} / {code_b} ({position} M3)</h2>'
                         f'<img loading="lazy" src="{picture.as_posix()}" alt="{pair_id} geometric crown regions and proposed patch matches">'
                         '<p>Review: corresponding anatomy? Similar wear? Similar preservation? Are the marked patches anatomically comparable?</p></article>')
    for r, adjusted in zip(results, holm_adjust([r['exact_p'] for r in results])):
        r['holm_p_twelve_conditions'] = adjusted
    sources = dict(manifest['input_hashes'])
    for path in (SPECIMENS, IMAGES, MANIFEST, Path(__file__), ROOT / 'scripts/dinov3_regional.py',
                 ROOT / 'scripts/dinov3_pipeline.py', ROOT / 'scripts/dinov3_crown.py', ROOT / 'scripts/pipeline_utils.py'):
        sources[path.relative_to(ROOT).as_posix()] = sha256(path)
    write_json(OUT / 'comparison.json', {'experiment': 'dinov3_regional_v1', 'trained': False,
               'anatomical_regions_verified': False, 'taxon_assignments_verified': False,
               'input_and_code_hashes': sources, 'results': results})
    write_csv(OUT / 'comparison.csv', [{k: v for k, v in r.items() if k != 'per_group'} for r in results])
    for name, rows in [('predictions', predictions), ('region_diagnostics', diagnostics),
                       ('review_key', pair_rows), ('review_ratings', ratings)]:
        write_csv(OUT / f'{name}.csv', rows)
    write_reports(results, cards)
    print(f'Completed {len(results)} conditions and {len(cards)} review pairs: {OUT / "index.html"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true', help='Validate caches and create draft review inventories')
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        if args.prepare_only:
            prepare()
            print(f'Draft review inventories: {SPECIMENS}, {IMAGES}')
        else:
            run()
