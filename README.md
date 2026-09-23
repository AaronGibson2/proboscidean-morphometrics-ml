# Proboscidean Morphometrics ML

A reproducible computer-vision pipeline for exploring morphological variation in Miocene
proboscidean third molars from Love Bone Bed, Mixson's Bone Bed, and Tyner Farm.

This is research software under active development. Embedding plots are hypothesis-generating
results, not taxonomic diagnoses or inferential evidence by themselves.

## Workflow

1. Convert NEF/TIFF photographs to consistent 16-bit RGB TIFFs.
2. Build an auditable image/specimen manifest with source hashes.
3. Apply reviewed conservative crops and remove separate museum labels without thresholding tooth pixels.
4. Preserve inclusion decisions; place whole crops on black canvases and generate comparison QC.
5. Extract frozen pretrained DINOv3 features, with no training or fine-tuning.
6. Compare independent specimens using cosine similarity, nearest neighbors, PCA, and label permutations.

Start with the [DINOv3 setup and run guide](docs/dinov3.md). Existing BioEncoder scripts and
outputs are retained for historical comparison; they are not used by the DINOv3 workflow.

The first frozen DINOv3 pilot is complete: [findings](docs/dinov3-pilot-results.md).
Open `outputs/dinov3/index.html` locally to view all four reports and plots.
The default now uses [conservative crops](docs/conservative-crops.md); the original masks
removed real tooth surface. Review all 37 before/after images in `outputs/qc/crop_black_v2/index.html`.

The `dinov3/crown-patch-experiment` branch adds a fixed, training-free comparison of whole-image
and crown-patch features at 224/512 pixels. See the [experiment protocol](docs/dinov3-crown-experiment.md)
and [results](docs/dinov3-crown-results.md). These separate experiments preserve all pilot outputs.

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_crown_experiment.py --prepare-only
# Inspect outputs/qc/crown_regions_v1/index.html before extraction.
.venv\Scripts\python.exe scripts/run_dinov3_crown_experiment.py
```

The experiment uses the already cached checkpoint offline. Its reports are in
`outputs/dinov3_crown_v1/index.html`. Completed experiments cannot be overwritten through
this runner; use a new version for later region revisions. Sources, model weights, and
generated outputs remain local; committed recipes, protocol, tests, and written results
are shared on GitHub.

Upper and lower M3s are processed and analyzed separately. All default paths resolve from
the repository root, so scripts may be launched from any working directory.

## Repository layout

```text
bioencoder_configs/       Legacy BioEncoder experiment configuration
docs/                    DINOv3 setup, methods, and research notes
data/
  raw/                    Immutable source photographs (ignored by Git)
  preprocessed/           Converted TIFFs and reports (ignored)
  segmented/              Tooth crops and segmentation QC (ignored)
  standardized/           Analysis-ready RGB and grayscale datasets (ignored)
metadata/                 QC decisions, crop overrides, and specimen schema
outputs/
  bioencoder/             Dataset splits, weights, logs, coordinates, and plots (ignored)
  dinov3/                 Frozen features, specimen comparisons, and reports (ignored)
  qc/                     Contact sheets, masks, and processing reports (ignored)
scripts/                  Numbered pipeline stages and shared utilities
tests/                    Fast metadata/unit tests
```

Within `data/raw`, preserve `tooth_position/site/image`, for example:

```text
data/raw/Upper/Love Bone Bed Upper M3/UF-38252-01-UM3.nef
data/raw/Lower/Tyner_Farm/UF-212304-RL_occlusal.tiff
```

Each standardized dataset contains one immediate directory per locality.

## Installation

Python 3.10 or 3.11 and CUDA-capable PyTorch are recommended for local inference.
On the configured workstation, use the existing `.venv` directly. For a fresh environment:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements-dinov3.txt
```

Install the PyTorch build appropriate for the computer's CUDA version if the default package
is unsuitable. `requirements.txt` retains the legacy/preprocessing dependencies, including
BioEncoder. SAM3 is optional; install its dependencies only when needed.

Meta's pretrained weights require account access and a local Hugging Face login. After
following the [access instructions](docs/dinov3.md#one-time-checkpoint-access):

```powershell
.venv\Scripts\python.exe scripts/prepare_conservative_crops.py
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py --inventory-only
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py
```

The second command runs upper/lower RGB/grayscale separately and writes local HTML reports
under `outputs/dinov3/`. No model is trained.

## Upper-M3 workflow

Convert the upper originals if needed. The conservative crop builder uses these TIFFs
directly and also prepares the existing lower JPEGs. If the v2 images already exist,
skip directly to DINOv3:

```powershell
python scripts/01_convert_nefs.py --input data/raw/Upper --output data/preprocessed/upper_m3
python scripts/02_build_manifest.py --images data/preprocessed/upper_m3 --output outputs/manifests/upper_m3.csv
.venv\Scripts\python.exe scripts/prepare_conservative_crops.py
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py --dataset upper --color rgb
```

The current Tyner upper sample is one individual represented by left and right teeth.
DINOv3 analysis combines those images into one specimen and marks its locality recognition
as unsupported because no independent same-site reference remains.

For the grayscale control, use the same standardized dataset:

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py --dataset upper --color grayscale
```

Add `--overwrite` to stages 01, 03, 05, or 06 only when intentionally replacing existing
derived outputs or runs. Stage 04 regenerates its included outputs when invoked.

## Lower-M3 workflow

The curated lower crops already live at `data/segmented/lower_m3`:

```powershell
python scripts/02_build_manifest.py --images data/segmented/lower_m3 --output outputs/manifests/lower_m3.csv
.venv\Scripts\python.exe scripts/prepare_conservative_crops.py
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py --dataset lower --color rgb
```

## Legacy segmentation and quality control

The following segmentation tools remain for historical experiments; the default DINOv3
workflow bypasses them. Their masks were observed to remove enamel and detached pieces.
Conservative v2 crops use recorded rectangles and background exclusions instead.
Contour segmentation is local and deterministic and fills the selected external silhouette.
Recorded exceptions in `metadata/segmentation_overrides.csv` correct frames where a bright
scale card is selected instead of the darker fossil.

To try SAM3, put the credential in the process environment—never in source code:

```powershell
$env:ROBOFLOW_API_KEY = "your_key"
python scripts/03_segment_all.py --input data/preprocessed/upper_m3 --output data/segmented/upper_m3 --method auto --overwrite
```

`auto` attempts SAM3 and falls back to contours. Inspect the segmentation QC under
`data/segmented/qc` and standardization masks/contact sheets under `outputs/qc`. Record every
inclusion or exclusion in the appropriate metadata QC file. Successful processing does not
guarantee a biologically valid crop.

Use `--help` on any numbered script for all options.

## Historical BioEncoder pilot results

These scores are from the previous trained BioEncoder workflow, not DINOv3.

### Lower M3

After QC, the lower dataset contains 20 images representing 16 independent specimens:
12 Love Bone Bed, two Mixson's Bone Bed, and two Tyner Farm. Tyner has four images: left/right
teeth for catalog IDs UF-212304 and UF-217472. Background/pose standardization
changed the two-dimensional PCA silhouette score from -0.146 to -0.062; grayscale produced
-0.310. All are negative, so these runs do not show convincing locality separation.

### Upper M3

Strict QC retained 17 images: 12 independent Love Bone Bed specimens, three independent
Mixson's Bone Bed specimens, and two contralateral teeth from one Tyner Farm individual.
After fixing destructive thresholding so internal crown detail was preserved, RGB embeddings
produced silhouette scores of 0.024 in PCA and 0.077 in t-SNE; grayscale produced -0.045 and
0.048. The mildly positive t-SNE values are driven mainly by the close Tyner pair, which is
not an independent sample. Mixson's pattern changes with projection and preprocessing.

## Scientific validity

- Keep raw photographs immutable.
- Treat specimens—not photographs or contralateral teeth—as independent observations.
- Do not place views from one specimen in both training and validation for final evaluation.
- Verify filename-derived metadata against museum records.
- Record site, catalog number, tooth position, side, scale, wear, preservation, photography
  batch, and every processing decision.
- Compare neural embeddings with conventional morphometric baselines.
- Use specimen-grouped repeated validation, confidence intervals, and permutation tests.
- Do not interpret t-SNE axes, distances, or apparent clusters as inferential statistics.
- Account for confounding among site, taxon, preservation, collection, and photography.

Legacy BioEncoder 1.0.5 uses an image-level splitter. Its training script blocks repeated
specimens and single-specimen classes by default; overrides were for pilot experiments.
The DINOv3 workflow uses frozen features and specimen-level comparisons without training splits.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Data and credits

Source specimens and photographs are controlled by their institutions and are not distributed
through this repository. Confirm permissions before sharing derived imagery.

Author: Aaron Gibson<br>
Advisors: Arthur Porto and Advait Jukar<br>
University of Florida

Use the [DINOv3 authors' citation](https://github.com/facebookresearch/dinov3#citation)
for the current workflow, and BioEncoder's citation when reporting historical results. Specimens derive from the
Florida Museum of Natural History and Smithsonian National Museum of Natural History collections.
