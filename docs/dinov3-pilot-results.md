# Frozen DINOv3 pilot: revised image preparation

## Current results: conservative crops on black, 2026-09-23

The original masks removed real tooth surface and detached pieces. Those runs are now
historical preprocessing diagnostics. The default pipeline bypasses automatic segmentation
and uses [reviewed conservative crops](conservative-crops.md). All 37 source/old/new comparisons
are in `outputs/qc/crop_black_v2/index.html`. Paper labels and scale cards are excluded;
attached matrix and writing directly on teeth remain. Some lower source frames already
cut through specimen margins and cannot be repaired from the available files.

The same frozen checkpoint, 224px input size, specimen grouping, and statistical procedure
were rerun on 17 upper and 20 lower images, with no training or tuning against site labels.

| Revised run | Within minus between-site cosine | Permutation p | Nearest-neighbor locality agreement | Always predict Love Bone Bed |
| --- | ---: | ---: | ---: | ---: |
| Upper RGB | -0.01127 | 0.5114 | 10/15 (66.7%) | 12/15 (80.0%) |
| Upper grayscale | -0.02019 | 0.6151 | 11/15 (73.3%) | 12/15 (80.0%) |
| Lower RGB | -0.00974 | 0.6885 | 11/16 (68.8%) | 12/16 (75.0%) |
| Lower grayscale | -0.03388 | 0.8347 | 11/16 (68.8%) | 12/16 (75.0%) |

These settings still provide no convincing evidence of locality separation, and none of
the four neighbor agreement rates exceeds the majority-locality baseline. Better anatomical
retention is a preprocessing correction, not evidence of improved biological discrimination.
Do not choose masks, contrast settings, or crops to optimize these exploratory scores.

Upper RGB retrieves the same locality for 8/12 Love and 2/3 Mixson specimens; upper grayscale
for 9/12 and 2/3. Upper Tyner remains unsupported as a query. Both lower variants retrieve
the same locality for 10/12 Love, 0/2 Mixson and 1/2 Tyner specimens. All four lower Tyner
photos remain included, grouped into two catalog IDs.

This revision changes brightness, orientation, background, and crop geometry together;
differences from the old scores cannot be attributed solely to mask quality. Metadata still
comes from filenames. Crown morphology, wear, preservation, matrix, and photography need
advisor review before interpretation.

Current reports are under `outputs/dinov3/{upper|lower}_{rgb|grayscale}_crop_black_v2_224/`.
Open `outputs/dinov3/index.html` for the current overview, or `index_legacy.html` for the
original overview. Original feature bundles and reports were preserved. All four new bundles
record the frozen pretrained revision, black padding, source hashes and crop audit.

Validation: 19 unit/integration tests passed, including exact source-pixel retention in the
marked UF-38220 enamel region (100% versus 31.61% retained by the original standardization
mask), the lower UF-217472 detached fragment, and representative label exclusions.

## Historical pilot with damaged masks

Completed 2026-09-23 on the local RTX 3070. The four runs used pretrained
`facebook/dinov3-vitb16-pretrain-lvd1689m`, revision
`5931719e67bbdb9737e363e781fb0c67687896bc`, with no training, fine-tuning, or learned classifier.
Weights were downloaded through the approved Hugging Face account and loaded from safetensors.
The direct Meta `.pth` checkpoint was not used for these results.

## Results

All inputs used whole-image 224px preprocessing, frozen 768-dimensional CLS features,
and specimen-level averaging followed by L2 normalization. Upper: 17 images / 16 catalog IDs;
lower: 20 images / 16 catalog IDs. RGB and grayscale are alternate versions of the same
images, not additional independent observations. Source images and checkpoint provenance are
recorded within each run. Methods are described in [the workflow guide](dinov3.md).

| Run | Within minus between-site cosine | Permutation p | Nearest-neighbor locality agreement | Always predict Love Bone Bed |
| --- | ---: | ---: | ---: | ---: |
| Upper RGB | -0.00238 | 0.4998 | 11/15 (73.3%) | 12/15 (80.0%) |
| Upper grayscale | -0.00347 | 0.5056 | 8/15 (53.3%) | 12/15 (80.0%) |
| Lower RGB | +0.00948 | 0.3089 | 12/16 (75.0%) | 12/16 (75.0%) |
| Lower grayscale | -0.02851 | 0.8078 | 10/16 (62.5%) | 12/16 (75.0%) |

Positive cosine contrasts mean pairs from the same locality were more similar on average.
The p-values use 9,999 specimen-label permutations, seed 42, and a one-sided test for a
positive contrast. They assume exchangeable specimen labels and are not corrected across
the four exploratory runs. The statistic averages pairs; larger sites contribute more pairs.

Upper nearest-neighbor agreement excludes the single Tyner individual as a query because
no other Tyner reference exists. It remains in the plots and reference pool. The constant
Love Bone Bed baseline uses the same eligible query sets; it requires no training.

## Interpretation

This pilot does not provide convincing evidence of locality separation under the chosen
global similarity test. None of the four nearest-neighbor agreement rates exceeds the
constant majority-locality baseline. This does not establish that the teeth are biologically
equivalent or that DINOv3 captures no morphological information.

Locality agreement by site:

| Run | Love Bone Bed | Mixson's Bone Bed | Tyner Farm |
| --- | ---: | ---: | ---: |
| Upper RGB | 9/12 | 2/3 | Unsupported |
| Upper grayscale | 8/12 | 0/3 | Unsupported |
| Lower RGB | 11/12 | 0/2 | 1/2 |
| Lower grayscale | 9/12 | 0/2 | 1/2 |

The four lower Tyner images are grouped into `UF-212304` and `UF-217472` according to their
filenames. Paired teeth cannot retrieve another image of the same individual as an independent
neighbor. Catalog grouping still needs verification against collection records;
`metadata/specimens.csv` is not yet populated. Wear, preservation, staining, orientation,
and photography may influence the features. Locality labels are not taxonomic labels.

Next scientific review: inspect the nearest-neighbor image panels with the advisor and record
whether matches follow crown morphology, wear, or preservation. Confirm specimen metadata
before stronger inference. A previously specified 512px sensitivity analysis remains available
but has not been run; settings should not be selected just to obtain locality clusters.

## Saved artifacts

Open `outputs/dinov3/index.html` for the comparison overview. Individual runs:

- `outputs/dinov3/upper_rgb_224/analysis/report.html`
- `outputs/dinov3/upper_grayscale_224/analysis/report.html`
- `outputs/dinov3/lower_rgb_224/analysis/report.html`
- `outputs/dinov3/lower_grayscale_224/analysis/report.html`

Each run contains the per-image feature cache, specimen embeddings, nearest-neighbor CSV,
cosine similarity matrix, PCA coordinates, PNG figures, and numerical summary JSON.
The output directory is ignored by Git; these notes retain the pilot's key numerical results.
