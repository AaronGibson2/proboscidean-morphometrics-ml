# Provisional Love versus Mixson + Tyner comparison

See the [complete results guide](results-summary.md) for metric explanations, all 24 conditions,
and a numerical snapshot available without the local HTML reports.

Exploratory locality grouping; specimen-level taxon identifications are unconfirmed.

No images, original locality labels, taxon metadata, or feature vectors were changed. No training.

| Condition | Love recall | Mixson + Tyner recall | Macro recall | Ordinary agreement | Exact p | Holm p (8) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| upper_cls_224 | 66.7% | 75.0% | 70.8% | 68.8% | 0.0648 | 0.4538 |
| upper_crown_224 | 66.7% | 50.0% | 58.3% | 62.5% | 0.2088 | 1.0000 |
| upper_cls_512 | 83.3% | 75.0% | 79.2% | 81.2% | 0.0291 | 0.2330 |
| upper_crown_512 | 83.3% | 50.0% | 66.7% | 75.0% | 0.0907 | 0.5440 |
| lower_cls_224 | 83.3% | 25.0% | 54.2% | 68.8% | 0.2841 | 1.0000 |
| lower_crown_224 | 83.3% | 25.0% | 54.2% | 68.8% | 0.2879 | 1.0000 |
| lower_cls_512 | 100.0% | 0.0% | 50.0% | 75.0% | 0.3868 | 1.0000 |
| lower_crown_512 | 100.0% | 0.0% | 50.0% | 75.0% | 0.4330 | 1.0000 |

Each position has 12 Love and 4 Mixson + Tyner catalog IDs. All 16 queries are now eligible; upper Tyner can retrieve Mixson under the provisional grouping. Majority baselines: 50% macro recall and 75% ordinary agreement. Exact tests enumerate all 1,820 assignments of four specimens to the smaller group, assuming exchangeable specimen labels. Locality/photography confounding is not controlled. Holm correction covers these eight conditions only, not earlier exploratory choices. These are the same previously inspected specimens, with no independent validation set. Scores cannot be compared directly with three-locality scores because the question and eligible query set changed. This analysis does not validate taxon identification, species boundaries, or anatomical homology.

## Interpretation

Completed 2026-09-23. The grouping was proposed after inspecting the earlier locality results,
and was motivated by the Florida Museum research update and the user's tentative belief that
it applies to these photographs. It is not a preregistered or independently validated taxonomic test.
The museum update summarizes ongoing research; catalog-ID correspondence still needs confirmation.

The strongest condition is upper CLS at 512 pixels: 10/12 Love specimens and 3/4 specimens
from Mixson plus Tyner retrieve their provisional group (13/16 overall; 79.2% macro recall).
Its raw exact p-value is 0.0291, but the Holm-adjusted value is 0.2330. No condition survives
correction at 0.05. This condition exceeds the 75% ordinary majority baseline by one specimen;
that difference alone does not establish a reliable improvement.

Crown averaging underperforms CLS for the upper proposed grouping. Lower 512px features
retrieve Love for all 16 specimens, yielding 75% ordinary agreement but only 50% macro recall.
The minority group is not recognized. Consequently this reanalysis does not rescue the lower
results or demonstrate separation between taxa.

Next: verify the catalog IDs and proposed identifications, review wear and preservation,
and define corresponding anatomical regions before another feature comparison. Keep the
original three-locality analysis available as a different question. Do not interpret a new
binary label scheme as an improvement to the same three-locality prediction task.

## Reproduce

Run `python scripts/analyze_dinov3_group_hypothesis.py` from the project environment after
preparing the eight crown-experiment feature bundles. No model download, forward pass,
training, or image editing is required. Existing hypothesis outputs are protected against
overwrite; subsequent changes require a new hypothesis version.

The mapping and analysis protocol are recorded in `metadata/locality_group_hypothesis_v1.json`.
Original site fields, specimen metadata, and all prior feature bundles remain untouched.
Output: `outputs/dinov3_group_hypothesis_v1/index.html`, with per-specimen predictions,
comparison tables, hypothesis hash and input-bundle hashes.

Source: [Florida Museum research update](https://www.floridamuseum.ufl.edu/nhdept/from-the-field/2026/amebelodon-or-not-that-is-the-question-a-reevaluation-of-amebelodontid-specimens-from-the-miocene-of-florida/).
