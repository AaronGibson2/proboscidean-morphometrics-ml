# Experiment 1: frozen crown-patch features and resolution

Protocol fixed before extracting these results, 2026-09-23. Branch:
`dinov3/crown-patch-experiment`, based on `dinov3/conservative-crop-pilot` (57335bc).

## Question and fixed comparisons

Does crown-restricted patch pooling retrieve locality more consistently than whole-image
CLS features, and does increased input resolution help? Locality is the exploratory target.
Locality separation would not establish distinct species: taxonomic conclusions require
independent anatomical/collection evidence, and photography may confound locality.

Run exactly eight RGB conditions: upper/lower separately, 224/512 pixels, CLS/crown-patch
mean. Same included photographs, catalog grouping, checkpoint revision
`5931719e67bbdb9737e363e781fb0c67687896bc`, and source crop recipes throughout. No training,
fine-tuning, classifier fitting, selecting images by locality score, or parameter search.
Grayscale and additional models are deferred. Both resolutions are rendered directly from
full-resolution conservative crops using the same fixed scaling and orientation rules.
Consequently the 224px CLS control is fresh; it is not exactly the old two-stage resize.

## Crown regions and feature extraction

Record assistant-drawn broad crown polygons before inspecting results. Coordinates in
`metadata/crown_regions_v1.json` are normalized to the unrotated conservative crop.
Multiple polygons preserve detached pieces. These are provisional feature-selection regions,
not anatomically certified segmentations. Review overlays in `outputs/qc/crown_regions_v1`.
Full images enter DINOv3 unchanged; masks only determine which output patch vectors are pooled.
Attention still permits those vectors to incorporate surrounding context.

Exclude CLS and all register tokens before pooling. Normalize each spatial patch vector,
select patches with at least 50% crown coverage, weight their mean by coverage, and
L2-normalize the result. Coverage uses a mask transformed with the exact image placement,
orientation, and padding geometry. CLS and crown features come from the same frozen forward
pass. Save spatial tokens and coverage maps so comparisons can be inspected without reruns.

## Evaluation and interpretation

Average normalized image features within catalog ID, then normalize, as in the pilot.
Nearest neighbors exclude the complete query individual. Primary descriptive metric:
macro recall across localities with at least two catalog IDs (mean of per-site nearest-neighbor
agreement). Report per-site recall, ordinary agreement, and the constant-majority baseline.
The baseline macro recall is 1/2 for upper and 1/3 for lower; upper Tyner has no independent
reference and remains in the reference pool but is excluded as a query.

Use 9,999 specimen-label permutations, seed 42, for a one-sided macro-recall test, recomputing
eligible query groups under each permutation. Report raw p-values and Holm-adjusted values
across all eight conditions. Pair-weighted cosine contrast is retained as a secondary metric.
All results are exploratory on this small, previously inspected dataset; there is no held-out
confirmation set. Low power, inferred independence, and locality/photography confounding remain.

Report every condition. Do not redraw regions or choose preprocessing based on locality
scores. Inspect patch overlays and future advisor-rated anatomical pairs to assess what the
representation captures. A negative result is still useful for choosing the next data collection.
