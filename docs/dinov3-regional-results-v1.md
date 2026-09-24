# DINOv3 regional matching v1 results

See the [visual guide](dinov3-visual-guide.md) for specimen-count diagrams and comparison
charts. They also appear above the tables in the local `index.html` report.

Frozen 512px features; geometric crown regions awaiting anatomical review. No training.

## What happened

Regional averages improved upper **three-locality** macro recall from 75.0% to 79.2%,
with 13/15 eligible specimens retrieving their locality instead of 12/15. Love improved
from 10/12 to 11/12; Mixson stayed at 2/3, and upper Tyner remained unsupported.
Two Love queries changed from wrong to right and one from right to wrong: a net gain
of one specimen. The raw exact p-value is 0.0242; the Holm value is 0.2901.

For **Love versus Mixson + Tyner**, regional averages reduced upper macro recall from
79.2% to 70.8%, even though overall agreement stayed at 13/16. Love gained one correct
query, but Tyner specimen `UF-212305` switched from a Mixson neighbor to Love, reducing
minority-group recall from 3/4 to 2/4. Regional patch matching performed worse still.

Neither regional method improved lower teeth. Both missed every Mixson and Tyner query,
and Love recall fell from 12/12 to 11/12. **No condition passed the Holm-adjusted 0.05
threshold.** The new methods are not validated replacements for CLS.

The practical outcome is a reviewable experiment: 43 distinct neighbor-pair panels,
three-region overlays, proposed patch correspondences, and draft metadata inventories.
It has not yet tested expert-verified homologous regions or established species separation.

## All 12 conditions

| Position | Target | Method | Macro recall | Correct / eligible | Raw exact p | Holm p (12) | Change from CLS |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| upper | locality | cls | 75.0% | 12/15 (80.0%) | 0.0390 | 0.3901 | +0.0 pp |
| upper | locality | regional_mean | 79.2% | 13/15 (86.7%) | 0.0242 | 0.2901 | +4.2 pp |
| upper | locality | regional_patch | 66.7% | 10/15 (66.7%) | 0.0791 | 0.6330 | -8.3 pp |
| upper | provisional_group | cls | 79.2% | 13/16 (81.2%) | 0.0291 | 0.3203 | +0.0 pp |
| upper | provisional_group | regional_mean | 70.8% | 13/16 (81.2%) | 0.0703 | 0.6330 | -8.3 pp |
| upper | provisional_group | regional_patch | 58.3% | 10/16 (62.5%) | 0.2275 | 1.0000 | -20.8 pp |
| lower | locality | cls | 33.3% | 12/16 (75.0%) | 0.2670 | 1.0000 | +0.0 pp |
| lower | locality | regional_mean | 30.6% | 11/16 (68.8%) | 0.2885 | 1.0000 | -2.8 pp |
| lower | locality | regional_patch | 30.6% | 11/16 (68.8%) | 0.3251 | 1.0000 | -2.8 pp |
| lower | provisional_group | cls | 50.0% | 12/16 (75.0%) | 0.3868 | 1.0000 | +0.0 pp |
| lower | provisional_group | regional_mean | 45.8% | 11/16 (68.8%) | 0.5181 | 1.0000 | -4.2 pp |
| lower | provisional_group | regional_patch | 45.8% | 11/16 (68.8%) | 0.5335 | 1.0000 | -4.2 pp |

## Recall by original locality or provisional group

| Position / target / method | Group | Correct / specimens | Recall |
| --- | --- | ---: | ---: |
| upper / locality / cls | Love Bone Bed Upper M3 | 10/12 | 83.3% |
| upper / locality / cls | Mixson's Bone Bed | 2/3 | 66.7% |
| upper / locality / cls | Tyner Farm | Unsupported (1 ID) | Not scored |
| upper / locality / regional_mean | Love Bone Bed Upper M3 | 11/12 | 91.7% |
| upper / locality / regional_mean | Mixson's Bone Bed | 2/3 | 66.7% |
| upper / locality / regional_mean | Tyner Farm | Unsupported (1 ID) | Not scored |
| upper / locality / regional_patch | Love Bone Bed Upper M3 | 8/12 | 66.7% |
| upper / locality / regional_patch | Mixson's Bone Bed | 2/3 | 66.7% |
| upper / locality / regional_patch | Tyner Farm | Unsupported (1 ID) | Not scored |
| upper / provisional_group / cls | Love | 10/12 | 83.3% |
| upper / provisional_group / cls | Mixson + Tyner | 3/4 | 75.0% |
| upper / provisional_group / regional_mean | Love | 11/12 | 91.7% |
| upper / provisional_group / regional_mean | Mixson + Tyner | 2/4 | 50.0% |
| upper / provisional_group / regional_patch | Love | 8/12 | 66.7% |
| upper / provisional_group / regional_patch | Mixson + Tyner | 2/4 | 50.0% |
| lower / locality / cls | Love_Bone_Bed | 12/12 | 100.0% |
| lower / locality / cls | Mixsons_Bone_Bed | 0/2 | 0.0% |
| lower / locality / cls | Tyner_Farm | 0/2 | 0.0% |
| lower / locality / regional_mean | Love_Bone_Bed | 11/12 | 91.7% |
| lower / locality / regional_mean | Mixsons_Bone_Bed | 0/2 | 0.0% |
| lower / locality / regional_mean | Tyner_Farm | 0/2 | 0.0% |
| lower / locality / regional_patch | Love_Bone_Bed | 11/12 | 91.7% |
| lower / locality / regional_patch | Mixsons_Bone_Bed | 0/2 | 0.0% |
| lower / locality / regional_patch | Tyner_Farm | 0/2 | 0.0% |
| lower / provisional_group / cls | Love | 12/12 | 100.0% |
| lower / provisional_group / cls | Mixson + Tyner | 0/4 | 0.0% |
| lower / provisional_group / regional_mean | Love | 11/12 | 91.7% |
| lower / provisional_group / regional_mean | Mixson + Tyner | 0/4 | 0.0% |
| lower / provisional_group / regional_patch | Love | 11/12 | 91.7% |
| lower / provisional_group / regional_patch | Mixson + Tyner | 0/4 | 0.0% |

## Interpretation limits

The CLS features and observed baseline scores are unchanged. Locality raw p-values differ
slightly from the previous crown report because this run enumerates all assignments rather
than sampling 9,999 permutations. Adjusted values also differ because Holm now covers 12
conditions instead of eight. Binary CLS raw exact p-values reproduce the previous run.

## Files, review and reproduction

- Full local report: `outputs/dinov3_regional_v1/index.html`.
- Locality-label-hidden review: `outputs/dinov3_regional_v1/review.html` (43 pairs).
- Blank ratings: `outputs/dinov3_regional_v1/review_ratings.csv`; decode identities with
  `review_key.csv` after rating. Original markings may still reveal specimen identity.
- [Specimen review draft](../metadata/specimen_review_v1.csv): 32 specimen/position rows,
  not 32 confirmed distinct individuals. IDs, localities and institution prefixes are
  inferred; all taxa remain unknown.
- [Image review draft](../metadata/image_review_v1.csv): 37 photos with inferred sides
  and source paths. Wear, preservation, orientation, photography batch and scale remain
  unknown. Do not infer physical scale from the resized display image.
- [Exact results and provenance](results/regional-results-v1.json) are tracked for GitHub;
  visual reports and feature caches remain local.
- [Fixed protocol](dinov3-regional-protocol-v1.md) and
  [input manifest](../metadata/regional_inputs_v1.json).

Review a saved copy of the rating CSV, recording `yes`, `no`, `uncertain`, or `unknown`
for corresponding anatomy, similar wear, similar preservation and validity of marked
patch matches. Record the reviewer and evidence in notes. Some inspected illustrative
matches lie near tooth margins; their anatomical relevance requires review. This gallery
contains model-selected neighbors, not a representative blinded benchmark of all pairs.

Fill draft metadata from collection records or expert assessment, preserving unknowns
when evidence is absent. The drafts do not override cached labels or retroactively change
this result. Reviewed landmarks or corrected metadata should define a separate version.

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_regional.py --prepare-only
.venv\Scripts\python.exe scripts/run_dinov3_regional.py
```

The run requires audited crown caches, masks and source images. No model download or
forward pass is needed. Completed outputs cannot be overwritten. Preparation preserves
existing review annotations. The historical manifest pins the original cache bytes;
byte-different regenerated caches need a separately recorded reproduction manifest.

Validation: 35 software tests passed, including exact enumeration against brute force,
reversal handling, regional mismatch, background exclusion, specimen aggregation and
label-independent ties. All source/code hashes were checked after the run; all 192
predictions exclude self-specimens. All 43 panel images and report links were verified,
with visual inspection of representative upper/lower panels. Software checks do not
validate anatomical correspondence or species separation.

### Statistical and biological limits

Regional methods use three geometric bands, not verified anatomical landmarks. Regional patch scoring allows many-to-one matches and maximizes over forward/reversed band order. All cross-image pairs are averaged per catalog-ID pair; queries exclude the entire catalog ID. Locality upper Tyner is unsupported as a query. Exact tests enumerate 7,280 upper-locality, 10,920 lower-locality or 1,820 provisional-group label assignments. Holm correction covers all 12 conditions in this experiment, not earlier exploratory choices. Baselines: upper locality 80% ordinary / 50% macro, lower locality 75% / 33.3%, provisional groups 75% / 50%. Differences from CLS are descriptive, not paired significance tests. Exchangeable labels are assumed; photography/wear confounding is uncontrolled. This reuses previously inspected specimens and has no independent confirmation set or verified species identifications. Metadata inventories remain draft; no wear/preservation-adjusted analysis was performed.
