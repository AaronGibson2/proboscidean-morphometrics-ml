# Regional matching v1: fixed exploratory protocol

Specified before evaluating the new regional results. Uses the existing frozen 512px
RGB DINOv3 ViT-B/16 features, checkpoint `5931719e67bbdb9737e363e781fb0c67687896bc`.
No training, new image editing, specimen exclusions, or selection by locality score.

## Question and limitation

Do spatially restricted comparisons retain information lost by whole-crown averaging?
This is a geometric precursor to anatomically reviewed matching. Existing crown polygons
are provisional, and no verified ridge/valley landmarks are available. Regions must not
be described as homologous cusps, lophs, or anterior/posterior structures.

## Fixed methods

Use all 37 photographs and the existing catalog-ID groups; keep upper/lower separate.
Select cached spatial patches with crown coverage >= 0.5; exclude all special tokens.
Derive a principal long axis from the coverage-weighted patch-center coordinates.
Divide its projected min-to-max extent into three equal-length bands. Label them
geometric region 1/2/3 only. Every band must contain at least one selected patch.
No silent exclusions or fallback if input validation fails.

Compare exactly three methods at 512px:

1. `cls`: unchanged original normalized specimen centroid cosine baseline.
2. `regional_mean`: normalize patch vectors, coverage-weighted mean within each band,
   normalize each regional vector, and average the three corresponding-region cosines.
3. `regional_patch`: within each corresponding band, find each patch's best cosine
   match in the other image; take coverage-weighted means in both directions, average
   the directions, then average the three bands equally. This permits many-to-one
   matches; it is not an anatomical correspondence guarantee or a one-to-one assignment.

For both regional methods take the larger score of forward band order and reversed
band order (1/2/3 versus 3/2/1). Orientation is selected without labels, separately
for each image pair and method; report the chosen order. It is not a verified anatomical
orientation. There is no additional rotation, scaling, feature threshold search, or
feature whitening. Features can still incorporate surrounding image context.

For each pair of different catalog IDs, average all cross-image pair scores, giving
each image pair equal weight. Every catalog ID is one query/reference regardless of
photo count. Never compare images sharing a catalog ID as independent specimens.
Regional score aggregation differs from CLS centroid aggregation and is part of the
method being assessed. It is not a controlled test of spatial information alone.
Nearest-neighbor ties use stable catalog-ID order, never the site label.

## Evaluation locked before results

Two positions x three methods x two targets = 12 reported conditions:

- Original three localities: upper singleton Tyner remains a reference but is excluded
  as a query; lower all 16 queries eligible.
- Provisional Love versus Mixson + Tyner: all 16 queries per position eligible; this
  is the same tentative grouping as the previous experiment, not verified taxa.

Primary metric: macro recall across groups with at least two independent catalog IDs.
Report per-group counts, ordinary agreement, and constant-Love baselines. Enumerate all
label assignments preserving counts: 7,280 upper-locality, 10,920 lower-locality and
1,820 binary assignments. Recompute eligible-query membership under each assignment.
One-sided exact p counts assignments scoring >= observed, including the observed
assignment. Apply Holm adjustment to all 12 conditions, including the reused baselines.
Differences from CLS are descriptive; no paired superiority claim is planned.
New exact p-values/correction scope can differ from earlier Monte Carlo/correction values.
Prior exploratory choices and reuse of previously inspected teeth remain uncorrected.

## Metadata and human review

Generate a separate draft specimen/position inventory and image inventory from cached
filenames. Preserve the original analysis labels; do not populate the authoritative
specimen table with unverified identifications. Taxon, wear, preservation, physical
scale, photography batch, and anatomical orientation remain unknown pending review.
Institution prefixes and sides, when parseable, are filename-inferred only.

For every distinct unordered nearest-neighbor specimen pair across all three methods,
show the first image of each specimen in a deterministic locality-label-hidden review
gallery. This fixed representative is not necessarily the strongest image pair, and
the scored specimen similarity still averages all image pairs. Include region overlays
and up to two highest-cosine mutual patch matches per region, with 48px spatial spacing
where available, using regional-patch orientation. These lines are illustrative, not
additional observations or proof of homology. Report the fraction of patches in mutual
matches. Pair and specimen display codes use a fixed random seed (42). Reviewers may
still recognize markings or specimens; this is not fully blinded acquisition.

Also produce a decoded neighbor table, similarity matrices, region-quality diagnostics,
and a blank review-rating table. Unknown metadata prevents adjusted wear/preservation
analysis in this version. A subsequent anatomically verified version must be separate.

## Reproducibility

Validate image/mask hashes and cached coverage against original audited masks;
verify patch pooling reproduces the original cached crown vectors. Save hashes of
all input bundles, patch files, protocol, recipes, code and draft inventories.
Refuse to overwrite completed output. Publish all results, including negative ones.
Frozen features and input labels remain unchanged.

General capability reference: [Meta's DINOv3 matching example](https://github.com/facebookresearch/dinov3/blob/main/notebooks/dense_sparse_matching.ipynb).
The regional scoring protocol above is a project-specific exploratory design, not a
validated fossil method or a claim to reproduce Meta's notebook evaluation.
