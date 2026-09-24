# Proboscidean Morphometrics ML

Exploring morphological variation in Miocene proboscidean third molars from **Love Bone Bed, Mixson's Bone Bed, and Tyner Farm** using pretrained DINOv3 features and specimen-level comparisons.

The research asks whether tooth photographs contain a reproducible signal that distinguishes localities. Locality differences may motivate taxonomic hypotheses, but they do not establish different species. Independent anatomical evidence and verified taxon labels are needed to evaluate taxonomic discrimination.

## Current status

- **No model training or fine-tuning.** DINOv3 ViT-B/16 is a frozen feature extractor.
- **37 photographs:** 17 upper M3 images representing 16 catalog IDs, and 20 lower M3 images representing 16 catalog IDs. Upper and lower teeth are analyzed separately; these counts should not be added to claim 32 distinct individuals across both datasets.
- Conservative crops preserve dark enamel and detached pieces. Separate paper labels and scale cards are excluded; attached matrix and writing on teeth can remain.
- Completed experiments compare whole-image features with crown-patch features at 224 and 512 pixels. Crown regions select output features without cutting pixels out of model inputs.
- **Results remain exploratory.** No condition in the eight-way crown experiment survives correction for multiple comparisons. The project has not demonstrated species discrimination.

## Code and findings

**New: [molar morphology and specimen identity review](docs/molar-morphology-assessment-v1.md).**
This connects the published anatomical comparisons to our photos and 27 UF catalog records.
It flags a tooth-position conflict for UF 212304, distinguishes catalog evidence from new
identifications, and includes a [GitHub photo gallery of all 37 photos](docs/morphology-gallery-v1/README.md)
plus a downloadable interactive HTML version. No new taxa were assigned.
The [primary-literature guide](docs/molar-taxonomy-primary-literature.md) explains the characters
and competing treatments of *floridanus*. These additions are on `morphology/literature-audit-v1`.

**Start with the [complete results guide](docs/results-summary.md): 36 reported condition rows (including reused baselines), plain-language explanations, counts, baselines, and comparisons.** Exact numbers are preserved in the [original snapshot](docs/results/numerical-results.json) and [regional snapshot](docs/results/regional-results-v1.json); visual reports remain local in `outputs/`.

The pilot and crown implementation was merged into `main` through PR #1. The latest regional experiment and updated guide are on `dinov3/regional-matching-v1`, which includes the preceding provisional-group analysis.

| Branch | Purpose |
| --- | --- |
| [`dinov3/conservative-crop-pilot`](https://github.com/AaronGibson2/proboscidean-morphometrics-ml/tree/dinov3/conservative-crop-pilot) | Frozen baseline, audited crop recipes, and pilot results |
| [`dinov3/crown-patch-experiment`](https://github.com/AaronGibson2/proboscidean-morphometrics-ml/tree/dinov3/crown-patch-experiment) | Includes the pilot plus crown-patch pooling, resolution comparisons, and locality-balanced evaluation |
| [`dinov3/provisional-group-comparison`](https://github.com/AaronGibson2/proboscidean-morphometrics-ml/tree/dinov3/provisional-group-comparison) | Adds exploratory Love versus Mixson + Tyner comparisons and the consolidated results guide |
| [`dinov3/regional-matching-v1`](https://github.com/AaronGibson2/proboscidean-morphometrics-ml/tree/dinov3/regional-matching-v1) | Adds geometric regional matching, 43 review pairs, and draft specimen/image metadata inventories |
| [`morphology/literature-audit-v1`](https://github.com/AaronGibson2/proboscidean-morphometrics-ml/tree/morphology/literature-audit-v1) | Adds primary literature, catalog evidence, a tooth-position discrepancy and a visual morphology review |

Documentation for the current checkout:

- [DINOv3 setup and pilot workflow](docs/dinov3.md)
- [Conservative image preparation](docs/conservative-crops.md)
- [Pilot findings](docs/dinov3-pilot-results.md)
- [Crown experiment protocol](docs/dinov3-crown-experiment.md)
- [All eight crown experiment results](docs/dinov3-crown-results.md)

## Latest results

**Prefer pictures? Start with the [visual explanation](docs/dinov3-visual-guide.md): one
symbol per specimen, simple method-comparison charts, and an explanation of why 75%
overall agreement can still fail to distinguish the sites.** These charts also appear
above the tables in the local regional report. To regenerate them from saved results,
run `.venv\Scripts\python.exe scripts/visualize_dinov3_regional.py`.

The [regional experiment](docs/dinov3-regional-results-v1.md) compares CLS, three-region
averages and within-region patch matching at 512px. Upper three-locality macro recall
increases from 75.0% to 79.2% with regional averages (13/15 versus 12/15 correct), but
the provisional grouping and lower results do not improve. None of its 12 conditions
passes Holm correction. Regions are geometric, not verified anatomical landmarks.

Draft [specimen](metadata/specimen_review_v1.csv) and [image](metadata/image_review_v1.csv)
inventories are ready for collection-record and anatomical review. Unverified fields
remain unknown; these drafts do not overwrite original labels or assign taxa.

### Previous crown and provisional-group comparisons

An additional [provisional Love versus Mixson + Tyner comparison](docs/dinov3-group-hypothesis-results.md)
uses the same cached features to explore a literature-motivated grouping. Specimen-level taxon
assignments remain unconfirmed. No condition survives correction across its eight comparisons;
this is a separate exploratory question, not verified species identification.

The primary metric is **macro locality recall**: average nearest-neighbor recall across localities with an independent same-site reference, giving each eligible locality equal weight.

| Dataset | 224px macro recall | 512px macro recall | Constant-majority macro baseline |
| --- | ---: | ---: | ---: |
| Upper M3 | 66.7% | 75.0% | 50.0% |
| Lower M3 | 44.4% | 33.3% | 33.3% |

Whole-image and crown-patch features achieved the same recall within each resolution. Higher resolution improved the upper result descriptively, but worsened balanced retrieval for the lower teeth. No condition exceeded the majority baseline on ordinary accuracy. All eight Holm-adjusted permutation p-values were above 0.05; the apparent improvements are not confirmed effects.

## Dataset and independence

| Tooth position | Locality | Images | Catalog IDs |
| --- | --- | ---: | ---: |
| Upper M3 | Love Bone Bed | 12 | 12 |
| Upper M3 | Mixson's Bone Bed | 3 | 3 |
| Upper M3 | Tyner Farm | 2 | 1 |
| Lower M3 | Love Bone Bed | 14 | 12 |
| Lower M3 | Mixson's Bone Bed | 2 | 2 |
| Lower M3 | Tyner Farm | 4 | 2 |

The four lower Tyner photographs are paired teeth labeled `UF-212304` and `UF-217472`. Grouping is inferred from filenames and still requires collection-record confirmation. Features from photographs of one catalog ID are averaged before comparison, and a specimen cannot retrieve another photograph of itself as an independent neighbor.

**Position check pending:** a published description lists UF 212304 with m1/m2,
conflicting with our m3 filenames. The saved experiments retain the original labels;
see the [morphology assessment](docs/molar-morphology-assessment-v1.md) before interpreting
the lower Tyner comparison as confirmed third-molar anatomy.

For three-locality evaluation, upper Tyner remains in the reference pool but cannot be evaluated as a locality query because it has no second independent reference. For the provisional grouping, it becomes eligible because Mixson provides same-group references.

## Run locally

The repository contains code, recipes, tests, written findings, and an older set of lower-tooth JPEG crops. **The complete source dataset, pretrained weights, generated HTML reports, and feature caches are not included.** Reproduction requires matching source photographs at the paths and hashes recorded in the recipes.

On Windows PowerShell, select the branch containing all experiments:

```powershell
git fetch origin
git switch dinov3/regional-matching-v1
```

For a fresh environment, use Python 3.10 or 3.11 and install a compatible PyTorch/torchvision build for your hardware. On the configured workstation, use the existing `.venv` instead of creating it again.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dinov3.txt
```

Follow the linked setup guide to obtain approved access to the pretrained weights and log in locally. Do not put access tokens in source code or commit them.

Prepare and inspect the conservative crops, then run the baseline:

```powershell
.venv\Scripts\python.exe scripts/prepare_conservative_crops.py
# Review outputs/qc/crop_black_v2/index.html.
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py --inventory-only
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py
```

Prepare and inspect the crown regions, then run the fixed eight-condition experiment:

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_crown_experiment.py --prepare-only
# Review outputs/qc/crown_regions_v1/index.html.
.venv\Scripts\python.exe scripts/run_dinov3_crown_experiment.py
```

The crown experiment uses the cached checkpoint offline. Skip preparation when matching inputs already exist. Completed experiments are protected against overwrite; use a new version for later changes to crown regions or methods.

## Local reports and validation

After the crown caches exist, run the new regional experiment with no further model inference:

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_regional.py --prepare-only
.venv\Scripts\python.exe scripts/run_dinov3_regional.py
```

The first command validates inputs and creates draft review inventories. Completed outputs
are protected against overwrite. See the [regional results](docs/dinov3-regional-results-v1.md)
for review instructions and the exact-cache reproduction requirements.

| Local file | Contents |
| --- | --- |
| `outputs/qc/crop_black_v2/index.html` | Source / old / revised image comparisons |
| `outputs/dinov3/index.html` | Conservative-crop pilot overview |
| `outputs/qc/crown_regions_v1/index.html` | Contributing crown patches at both resolutions |
| `outputs/dinov3_crown_v1/index.html` | All eight experimental conditions and individual reports |
| `outputs/dinov3_group_hypothesis_v1/index.html` | Eight provisional-group comparisons using the cached crown-experiment features |
| `outputs/dinov3_regional_v1/index.html` | Twelve regional/baseline evaluations with exact permutation tests |
| `outputs/dinov3_regional_v1/review.html` | Forty-three neighbor-pair panels with proposed patch correspondences and locality labels hidden |
| `outputs/morphology_literature_v1/index.html` | All 37 photos with visibility notes and catalog/literature evidence; build with `scripts/build_morphology_review.py` |

These paths refer to generated local files, not hosted GitHub pages. Individual runs record input hashes, checkpoint revision, crop/region provenance, and specimen-level results.

The morphology review also has a committed [shareable gallery](docs/morphology-gallery-v1/README.md).
Its standalone `index.html` embeds the viewing images and works after download.
Rebuild that snapshot with `.venv\Scripts\python.exe scripts/export_morphology_gallery.py`.
Other generated reports remain local.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The regional implementation passed 35 local software tests. These check code behavior; they are separate from the 36 reported analytical rows and do not establish scientific validity. Tests involving private photographs or optional model dependencies can skip when those resources are absent.

## Limitations and next steps

The sample is small and uneven across localities. Wear, staining, preservation, attached matrix, and photography may influence similarities. Some lower source photographs already cut through specimen margins; cropping cannot recover missing anatomy. Crown regions are provisional assistant-drawn annotations awaiting anatomical review.

Next priorities are verifying specimen metadata, recording wear/preservation and reliable morphometric measurements, evaluating anatomically comparable tooth regions, and obtaining additional independent specimens from the smaller locality samples. PCA and neighbor panels support inspection; attractive clusters alone do not establish biological or taxonomic groups.

## Image preparation and credits

Automatic masks were found to remove real tooth structure, which motivated the conservative-crop revision. The current workflow uses reviewed crops and frozen DINOv3 features throughout.

Source specimens and photographs are controlled by their institutions; repository inclusion does not grant redistribution rights. Specimens derive from the Florida Museum of Natural History and Smithsonian National Museum of Natural History collections.

**Author:** Aaron Gibson

**Advisors:** Arthur Porto and Advait Jukar

**Institution:** University of Florida

Use the [DINOv3 authors' citation](https://github.com/facebookresearch/dinov3#citation) when reporting the current method.
