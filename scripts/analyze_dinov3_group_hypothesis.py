"""Explore a provisional locality grouping without changing specimen taxon labels."""

import html
import itertools
import json
import math
from pathlib import Path

import numpy as np

from dinov3_crown import holm_adjust
from dinov3_pipeline import aggregate_specimens, load_bundle, normalize, write_csv
from pipeline_utils import PROJECT_ROOT, sha256, write_json

HYPOTHESIS = PROJECT_ROOT / "metadata/locality_group_hypothesis_v1.json"
RUNS = PROJECT_ROOT / "outputs/dinov3_crown_v1"
OUTPUT = PROJECT_ROOT / "outputs/dinov3_group_hypothesis_v1"


def exact_group_test(features, groups):
    """Enumerate the complete binary assignment space, including the observed assignment."""
    labels = np.asarray(groups)
    names, counts = np.unique(labels, return_counts=True)
    if len(names) != 2 or min(counts) < 2 or len(labels) != len(features):
        raise ValueError("Require two groups, each with at least two specimens, matching the features")
    assignments = math.comb(len(labels), int(counts[1]))
    if assignments > 100000:
        raise ValueError("Too many assignments for this exact-test workflow")
    vectors = normalize(features)
    similarities = vectors @ vectors.T
    np.fill_diagonal(similarities, -np.inf)
    nearest = similarities.argmax(axis=1)
    observed_labels = labels == names[1]

    def score(current):
        correct = current == current[nearest]
        return float((correct[current].mean() + correct[~current].mean()) / 2)

    observed = score(observed_labels)
    exceed = 0
    for selected in itertools.combinations(range(len(labels)), int(counts[1])):
        permuted = np.zeros(len(labels), dtype=bool)
        permuted[list(selected)] = True
        exceed += score(permuted) >= observed - 1e-12
    correct = labels == labels[nearest]
    return {"macro_recall": observed, "accuracy": float(correct.mean()),
            "group_counts": dict(zip(names.tolist(), counts.tolist())),
            "group_recall": {name: float(correct[labels == name].mean()) for name in names},
            "majority_accuracy": float(max(counts) / len(labels)), "majority_macro_recall": .5,
            "exact_p": exceed / assignments, "assignments": assignments,
            "nearest_indices": nearest.tolist()}


def main():
    if OUTPUT.exists():
        raise FileExistsError("Hypothesis output exists; preserve it and use a new hypothesis version")
    hypothesis = json.loads(HYPOTHESIS.read_text())
    prepared = []
    inventories = {}
    # Validate all inputs before producing any new results.
    for name in hypothesis["protocol"]["runs"]:
        bundle = RUNS / name / "embeddings.npz"
        features, records, provenance = load_bundle(bundle)
        if provenance["trained"] is not False:
            raise ValueError("Expected frozen-model features")
        for record in records:
            if sha256(Path(provenance["images_root"]) / record["image_path"]) != record["sha256"]:
                raise ValueError("An image changed since the original feature extraction")
        features, specimens = aggregate_specimens(features, records)
        if len({r["tooth_position"] for r in specimens}) != 1:
            raise ValueError("Do not pool upper and lower teeth")
        position = specimens[0]["tooth_position"]
        identity = [(r["specimen_id"], r["site"], r["image_count"]) for r in specimens]
        if position in inventories and identity != inventories[position]:
            raise ValueError("Conditions must contain identical specimen inventories")
        inventories[position] = identity
        groups = [hypothesis["groups"][r["site"]] for r in specimens]
        if groups.count("Love") != 12 or groups.count("Mixson + Tyner") != 4:
            raise ValueError("This hypothesis version requires the original 12/4 specimen inventory")
        prepared.append((name, bundle, features, specimens, groups, provenance))
    OUTPUT.mkdir(parents=True)
    results, predictions = [], []
    for name, bundle, features, specimens, groups, provenance in prepared:
        stats = exact_group_test(features, groups)
        nearest = stats.pop("nearest_indices")
        for i, j in enumerate(nearest):
            predictions.append({"run": name, "specimen_id": specimens[i]["specimen_id"],
                                "original_site": specimens[i]["site"], "provisional_group": groups[i],
                                "neighbor_specimen": specimens[j]["specimen_id"],
                                "neighbor_original_site": specimens[j]["site"],
                                "predicted_group": groups[j], "correct": groups[i] == groups[j]})
        results.append({"run": name, **stats, "input_bundle_sha256": sha256(bundle),
                        "model_revision": provenance["resolved_revision"]})
    for row, adjusted in zip(results, holm_adjust([r["exact_p"] for r in results])):
        row["holm_p_eight_conditions"] = adjusted
    write_json(OUTPUT / "comparison.json", {"hypothesis": hypothesis, "hypothesis_sha256": sha256(HYPOTHESIS),
                                            "results": results})
    write_csv(OUTPUT / "predictions.csv", predictions)
    write_csv(OUTPUT / "comparison.csv", [{k: v for k, v in r.items() if not isinstance(v, dict)} for r in results])
    lines = ["# Provisional Love versus Mixson + Tyner comparison", "",
             "Exploratory locality grouping; specimen-level taxon identifications are unconfirmed.", "",
             "No images, original locality labels, taxon metadata, or feature vectors were changed. No training.", "",
             "| Condition | Love recall | Mixson + Tyner recall | Macro recall | Ordinary agreement | Exact p | Holm p (8) |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    table_rows = []
    for r in results:
        cells = [r["run"], f'{r["group_recall"]["Love"]:.1%}', f'{r["group_recall"]["Mixson + Tyner"]:.1%}',
                 f'{r["macro_recall"]:.1%}', f'{r["accuracy"]:.1%}', f'{r["exact_p"]:.4f}',
                 f'{r["holm_p_eight_conditions"]:.4f}']
        lines.append("| " + " | ".join(cells) + " |")
        table_rows.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in cells) + "</tr>")
    notes = ("Each position has 12 Love and 4 Mixson + Tyner catalog IDs. All 16 queries are now eligible; "
             "upper Tyner can retrieve Mixson under the provisional grouping. Majority baselines: 50% macro recall "
             "and 75% ordinary agreement. Exact tests enumerate all 1,820 assignments of four specimens to the "
             "smaller group, assuming exchangeable specimen labels. Locality/photography confounding is not controlled. "
             "Holm correction covers these eight conditions only, not earlier exploratory choices. These are the "
             "same previously inspected specimens, with no independent validation set. Scores cannot be compared "
             "directly with three-locality scores because the question and eligible query set changed. This "
             "analysis does not validate taxon identification, species boundaries, or anatomical homology.")
    lines.extend(["", notes, ""])
    (OUTPUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (OUTPUT / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Provisional group comparison</title>'
        '<style>body{font:16px/1.6 system-ui;max-width:1200px;margin:32px auto;padding:0 20px}'
        'th,td{padding:10px;text-align:left;border-bottom:1px solid #ccc}table{border-collapse:collapse}.scroll{overflow:auto}</style>'
        '<h1>Love versus Mixson + Tyner</h1><p><strong>Provisional locality grouping, not verified taxon labels.</strong> '
        'Existing frozen features; no training or changes to the photographs.</p><div class="scroll"><table><tr>'
        '<th>Condition</th><th>Love recall</th><th>Mixson + Tyner recall</th><th>Macro recall</th>'
        '<th>Ordinary agreement</th><th>Exact p</th><th>Holm p (8)</th></tr>' + ''.join(table_rows) +
        '</table></div><p>' + html.escape(notes) + '</p><p><a href="predictions.csv">Individual predictions</a> · '
        '<a href="../dinov3_crown_v1/index.html">Original three-locality analysis</a></p></html>', encoding="utf-8")
    print("\n".join(lines))
    print(f"Report: {OUTPUT / 'index.html'}")


if __name__ == "__main__":
    main()
