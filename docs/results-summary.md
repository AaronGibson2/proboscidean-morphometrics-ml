# Understanding and comparing the DINOv3 results

Results through September 23, 2026. This guide covers **24 analytical conditions in four experiment families**, all using frozen DINOv3 features. They reuse the same photographs; they are not 24 independent replications.

**The strongest exploratory result is upper teeth at 512px using whole-image features for Love versus Mixson + Tyner: 13/16 correct neighbors (81.2% overall agreement) and 79.2% balanced recall. However, no condition in either eight-condition experiment passes the multiple-comparison correction. We have not established reliable locality discrimination or species identification.** The lower teeth remain especially unpromising with these feature summaries.

## Where the results live

| Material | Available in this repository? | Location |
| --- | --- | --- |
| This explanation and all 24 comparison rows | Yes | `docs/results-summary.md` |
| Exact numerical results, original JSON snapshots and source-file hashes | Yes | [Numerical results](results/numerical-results.json) |
| Detailed pilot, crown and provisional-group findings | Yes | Linked in the experiment sections below |
| Code, crop recipes, crown regions and hypothesis mapping | Yes | `scripts/` and `metadata/` |
| Full HTML reports, tooth panels, PCA plots, neighbor tables and feature caches | Local only | `outputs/` (ignored by Git) |
| Complete source photographs and pretrained weights | No | Local dataset folders and model cache; an older lower-tooth JPEG subset is tracked |

The consolidated guide and numerical snapshots are on the `dinov3/provisional-group-comparison` branch. They appear on GitHub's default `main` page after that branch is merged. The earlier pilot and crown implementation already reached `main` through PR #1. Creating a pull request alone does not merge it.

For the full visual reports on this workstation, open:

- `outputs/dinov3/index_legacy.html`: original-mask pilot.
- `outputs/dinov3/index.html`: conservative-crop pilot.
- `outputs/dinov3_crown_v1/index.html`: crown and resolution experiment.
- `outputs/dinov3_group_hypothesis_v1/index.html`: provisional grouping experiment.
- `outputs/qc/crop_black_v2/index.html` and `outputs/qc/crown_regions_v1/index.html`: image and region quality checks.

These paths are files on this computer, not public website addresses. The numerical snapshot makes the results readable on GitHub without requiring the photographs, model download or a rerun.

## What was actually evaluated

DINOv3 converts each photograph into a numerical description of its visual appearance. Its pretrained weights stay fixed: no training or fine-tuning occurred. Photographs sharing a catalog ID are averaged into one specimen representation. For each specimen, we find the most similar **different catalog ID** and ask whether its locality or provisional group agrees. Another image of the same catalog ID cannot count as a successful independent match.

| Position | Love images / IDs | Mixson images / IDs | Tyner images / IDs | Total images / IDs |
| --- | ---: | ---: | ---: | ---: |
| Upper M3 | 12 / 12 | 3 / 3 | 2 / 1 | 17 / 16 |
| Lower M3 | 14 / 12 | 2 / 2 | 4 / 2 | 20 / 16 |

There are 37 photographs. Do not add the upper and lower ID counts to claim 32 different animals; catalog IDs can overlap across positions. IDs and localities were inferred from filenames and still need collection-record verification.

For the original three-locality question, upper Tyner has no second independent Tyner reference. It remains a possible neighbor but cannot be scored as a query: upper agreement uses **15 eligible specimens**, lower uses 16. For Love versus Mixson + Tyner, upper Tyner can match Mixson, so **all 16** upper specimens become eligible.

## How to read the numbers

**Recall for one site/group** is the fraction of its specimens whose nearest neighbor belongs to that same site/group. `3/4` means three specimens matched and one did not. With only two specimens at a site, changing one match moves its recall by 50 percentage points.

**Overall agreement**, also called ordinary accuracy, is correct matches divided by all eligible queries. It gives every specimen equal weight. Because Love dominates the dataset, a method that always returns Love can look good while completely failing the smaller sites.

**Macro recall**, or balanced recall here, averages site/group recalls, giving each eligible site/group equal weight. For upper 512px locality retrieval, `(10/12 + 2/3) / 2 = 75.0%`. For lower 512px, `(12/12 + 0/2 + 0/2) / 3 = 33.3%`, despite 75% overall agreement. The latter result recognizes only Love.

**The constant-majority baseline** is what always predicting Love would achieve. It is a reference score, not the permutation-test null distribution or a fitted model:

| Evaluation | Overall baseline | Macro baseline |
| --- | ---: | ---: |
| Upper, original localities | 12/15 = 80% | 50% (two eligible localities) |
| Lower, original localities | 12/16 = 75% | 33.3% (three localities) |
| Either position, Love vs Mixson + Tyner | 12/16 = 75% | 50% (two groups) |

**Cosine similarity** measures how closely two feature vectors point in the same direction. Larger values mean more similar model representations; a cosine of 0.9 does not mean a 90% probability of the same species. The pilot's **cosine contrast** is mean similarity within a locality minus mean similarity between localities. Positive is the expected direction for locality separation; zero indicates no average difference, and negative means cross-locality pairs are more similar on average. It weights specimen pairs, so Love contributes many more within-site pairs. It can disagree with nearest-neighbor recall, which uses only one neighbor per query.

**Raw permutation p** asks how often shuffled labels produce a statistic at least as large as the observed one, assuming specimen labels are exchangeable. The pilot tests cosine contrast; the later experiments test macro recall. Their p-values therefore answer different questions. The pilot and crown analyses use 9,999 random permutations; the provisional grouping enumerates all 1,820 assignments with group sizes 12 and 4. A p-value is not the probability that the species hypothesis is true or false, and it is not prediction accuracy.

**Holm p (8)** adjusts for examining eight conditions within that experiment family. We compare it with 0.05. Every adjusted value is above 0.05, so none meets that threshold. The two eight-condition families are corrected separately; this does not correct for all earlier exploration or the later choice of a grouping hypothesis. Failure to pass the threshold does not prove that biological differences are absent. Photography, preservation and other confounding are not controlled by shuffling labels.

**PCA plots** compress the 768-dimensional specimen features into two display axes. An axis's explained-variance percentage describes how much feature variation it displays, not classification accuracy. Apparent clusters and overlap are visual clues; distances in two dimensions need not reproduce the full-feature nearest-neighbor results. No verified species clusters were discovered by these plots.

**CLS** is the model's whole-image summary. **Crown** averages selected patch features inside provisional crown regions. Both still come from a model that saw the entire crop, so crown pooling does not guarantee the removal of background or preservation effects. **224/512** denotes square model-input size in pixels. **RGB/grayscale** compares color with grayscale inputs.

## 1. Original-mask pilot: historical diagnostic

Question: do the original prepared images show locality separation with whole-image features at 224px? The primary test is cosine contrast; p-values below are unadjusted. Counts in the three site columns show correct neighbors / eligible specimens at that site.

| Condition (224px CLS) | Love | Mixson | Tyner | Overall agreement | Cosine contrast | Raw cosine p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Upper RGB | 9/12 | 2/3 | Unsupported | 11/15 (73.3%) | -0.0024 | 0.4998 |
| Upper grayscale | 8/12 | 0/3 | Unsupported | 8/15 (53.3%) | -0.0035 | 0.5056 |
| Lower RGB | 11/12 | 0/2 | 1/2 | 12/16 (75.0%) | +0.0095 | 0.3089 |
| Lower grayscale | 9/12 | 0/2 | 1/2 | 10/16 (62.5%) | -0.0285 | 0.8078 |

The original masks were later found to remove real tooth surface. These scores are retained for transparency, but this image preparation is not a suitable basis for biological conclusions. All cosine tests are unconvincing, and overall agreement never beats its majority baseline.

## 2. Conservative-crop pilot: better preservation of anatomy

Question: does preserving more tooth material, excluding separate labels and using black backgrounds reveal clearer locality structure? Same 224px CLS approach; cosine contrast remains the primary statistic.

| Condition (224px CLS) | Love | Mixson | Tyner | Overall agreement | Cosine contrast | Raw cosine p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Upper RGB | 8/12 | 2/3 | Unsupported | 10/15 (66.7%) | -0.0113 | 0.5114 |
| Upper grayscale | 9/12 | 2/3 | Unsupported | 11/15 (73.3%) | -0.0202 | 0.6151 |
| Lower RGB | 10/12 | 0/2 | 1/2 | 11/16 (68.8%) | -0.0097 | 0.6885 |
| Lower grayscale | 10/12 | 0/2 | 1/2 | 11/16 (68.8%) | -0.0339 | 0.8347 |

The crops improved anatomical preservation, but did not produce better evidence of locality separation. Every cosine contrast is negative, and grayscale does not consistently improve retrieval. This does not imply that destroying tooth surface was beneficial: the previous masks were unsuitable even where their scores happened to be higher. Several input details changed together, including crop geometry, background, orientation and intensity handling, so this is not an isolated test of segmentation alone.

Details: [pilot findings](dinov3-pilot-results.md) and [conservative crops](conservative-crops.md).

## 3. Crown and resolution experiment: eight conditions

Question: do crown-patch features or higher input resolution help distinguish the original localities? All conditions use RGB conservative crops, with each resolution prepared directly from source crops. Macro recall is the primary statistic; the numerical snapshot also retains the secondary cosine summaries. The pilot's 224px preparation used an intermediate resized image, so it is not an exactly identical baseline.

| Condition | Recall by site/group | Macro recall | Overall agreement | Raw macro p | Holm p (8) |
| --- | --- | ---: | ---: | ---: | ---: |
| upper_cls_224 | Love 8/12; Mixson 2/3; Tyner unsupported | 66.7% | 10/15 (66.7%) | 0.0720 | 0.4146 |
| upper_crown_224 | Love 8/12; Mixson 2/3; Tyner unsupported | 66.7% | 10/15 (66.7%) | 0.0691 | 0.4146 |
| upper_cls_512 | Love 10/12; Mixson 2/3; Tyner unsupported | 75.0% | 12/15 (80.0%) | 0.0363 | 0.2616 |
| upper_crown_512 | Love 10/12; Mixson 2/3; Tyner unsupported | 75.0% | 12/15 (80.0%) | 0.0327 | 0.2616 |
| lower_cls_224 | Love 10/12; Mixson 0/2; Tyner 1/2 | 44.4% | 11/16 (68.8%) | 0.1088 | 0.4164 |
| lower_crown_224 | Love 10/12; Mixson 0/2; Tyner 1/2 | 44.4% | 11/16 (68.8%) | 0.1041 | 0.4164 |
| lower_cls_512 | Love 12/12; Mixson 0/2; Tyner 0/2 | 33.3% | 12/16 (75.0%) | 0.2614 | 0.5228 |
| lower_crown_512 | Love 12/12; Mixson 0/2; Tyner 0/2 | 33.3% | 12/16 (75.0%) | 0.2619 | 0.5228 |

The upper 512px conditions improve balanced recall from 66.7% to 75.0%, but the improvement is descriptive: we did not perform a separate paired test of the resolution difference. The best raw p-values become 0.2616 after correction. Crown pooling and CLS achieve the same observed recall at each resolution; their p-values can differ because their neighbor relationships under shuffled labels differ.

For lower teeth, 512px raises overall agreement from 68.8% to 75.0% while **reducing** macro recall from 44.4% to 33.3%. Every Mixson and Tyner query retrieves Love. Higher overall agreement therefore does not mean better locality discrimination.

Details: [crown results](dinov3-crown-results.md) and [fixed experiment protocol](dinov3-crown-experiment.md).

## 4. Provisional Love versus Mixson + Tyner: eight conditions

Question: do the existing features support this proposed grouping? This reuses the eight cached feature sets without changing images or original locality labels. `M+T` below means Mixson + Tyner. The grouping is exploratory and does not assign verified species labels.

| Condition | Recall by site/group | Macro recall | Overall agreement | Raw macro p | Holm p (8) |
| --- | --- | ---: | ---: | ---: | ---: |
| upper_cls_224 | Love 8/12; M+T 3/4 | 70.8% | 11/16 (68.8%) | 0.0648 | 0.4538 |
| upper_crown_224 | Love 8/12; M+T 2/4 | 58.3% | 10/16 (62.5%) | 0.2088 | 1.0000 |
| upper_cls_512 | Love 10/12; M+T 3/4 | 79.2% | 13/16 (81.2%) | 0.0291 | 0.2330 |
| upper_crown_512 | Love 10/12; M+T 2/4 | 66.7% | 12/16 (75.0%) | 0.0907 | 0.5440 |
| lower_cls_224 | Love 10/12; M+T 1/4 | 54.2% | 11/16 (68.8%) | 0.2841 | 1.0000 |
| lower_crown_224 | Love 10/12; M+T 1/4 | 54.2% | 11/16 (68.8%) | 0.2879 | 1.0000 |
| lower_cls_512 | Love 12/12; M+T 0/4 | 50.0% | 12/16 (75.0%) | 0.3868 | 1.0000 |
| lower_crown_512 | Love 12/12; M+T 0/4 | 50.0% | 12/16 (75.0%) | 0.4330 | 1.0000 |

Upper CLS at 512px is the strongest condition: `(10/12 + 3/4) / 2 = 79.2%` macro recall and `13/16 = 81.2%` overall agreement. Always predicting Love gets 12/16, so this result is only **one additional correct specimen** above that overall baseline. Its raw p of 0.0291 becomes 0.2330 after correction. Crown pooling performs worse for this upper grouping. Lower 512px still retrieves Love for every query and recognizes none of the four minority-group specimens.

This does not show that upper teeth can be identified to species with 79.2% accuracy. The proposed grouping was considered after inspecting earlier results, uses the same specimens, and has no independent validation set. Individual taxon assignments remain unconfirmed. It also changes the question: a Mixson-to-Tyner match was wrong under three-locality evaluation and is now correct, and upper Tyner becomes an eligible query. Consequently the 75.0% locality macro score and the 79.2% provisional-group score cannot be treated as a measured improvement on the same task.

Details and the source motivating the hypothesis: [provisional-group findings](dinov3-group-hypothesis-results.md).

## What changed across experiments

| Experiment | Change being explored | What the results support |
| --- | --- | --- |
| Original masks, 4 conditions | Color versus grayscale on old prepared images | No convincing locality separation; image review exposed loss of tooth structure |
| Conservative crops, 4 conditions | Better-preserved tooth images and black backgrounds | Better inputs for anatomical review, but no clearer statistical separation |
| Crown / resolution, 8 conditions | CLS versus crown features; 224 versus 512px | Upper 512px has better descriptive balanced recall; crown pooling adds no recall benefit; lower 512px fails the smaller sites |
| Provisional groups, 8 conditions | Love versus combined Mixson + Tyner, using unchanged features | Upper 512px CLS is worth investigating; lower failure persists; no corrected evidence or verified taxonomic result |

We should preserve the more faithful crops even though they did not raise the scores. Among the feature comparisons, higher-resolution upper CLS deserves further anatomical inspection; it is a candidate for follow-up, not a validated winning model. The present data do not support announcing distinct species or reliable site grouping.

The next useful work is to verify the catalog IDs and proposed taxon assignments with collection records/advisor input, record wear and preservation, and inspect whether successful neighbors share corresponding crown anatomy. Additional independent Mixson and Tyner specimens would make minority-site recall less dependent on single teeth. Any further comparison should specify its metric and conditions before looking at outcomes and, where feasible, reserve independent specimens for confirmation. A new hypothesis can be explored, but repeatedly choosing features or groupings on these same teeth is not independent validation, even without training the neural network.

## Scientific conditions versus software tests

The implementation passed **28 local software tests** at the analysis revision. Those tests check behavior such as specimen aggregation, region pooling and permutation calculations. Passing them does not mean the teeth separate biologically. This guide's **24 conditions** are scientific analyses of the same small dataset; they are separate from the software-test count.

This document summarizes existing outputs; it does not rerun inference or change any labels, crops, features or frozen protocols. The [numerical snapshot](results/numerical-results.json) records the source-code revision and SHA-256 hashes of the 18 original JSON files used for these tables, including all 24 conditions. Pilot p-values refer to cosine contrast; the crown/group comparison p-values refer to macro recall. The crown per-run summaries also contain secondary cosine p-values, which must not be substituted for the primary macro tests.
