# Proboscidean Morphometrics ML

A reproducible computer-vision pipeline for exploring morphological variation in Miocene
proboscidean third molars from Love Bone Bed, Mixson's Bone Bed, and Tyner Farm.

This is research software under active development. Embedding plots are hypothesis-generating
results, not taxonomic diagnoses or inferential evidence by themselves.

## Workflow

1. Convert NEF/TIFF photographs to consistent 16-bit RGB TIFFs.
2. Build an auditable image/specimen manifest with source hashes.
3. Propose tooth silhouettes, apply recorded crop overrides, and generate segmentation QC.
4. Apply human inclusion decisions; standardize orientation, scale, and background.
5. Train BioEncoder stage-one morphology embeddings.
6. export interactive and static PCA/t-SNE plots plus their coordinates.

Upper and lower M3s are processed and analyzed separately. All default paths resolve from
the repository root, so scripts may be launched from any working directory.

## Repository layout

```text
bioencoder_configs/       BioEncoder experiment configuration
data/
  raw/                    Immutable source photographs (ignored by Git)
  preprocessed/           Converted TIFFs and reports (ignored)
  segmented/              Tooth crops and segmentation QC (ignored)
  standardized/           Analysis-ready RGB and grayscale datasets (ignored)
metadata/                 QC decisions, crop overrides, and specimen schema
outputs/
  bioencoder/             Dataset splits, weights, logs, coordinates, and plots (ignored)
  qc/                     Contact sheets, masks, and processing reports (ignored)
scripts/                  Numbered pipeline stages and shared utilities
tests/                    Fast metadata/unit tests
```

Within `data/raw`, preserve `tooth_position/site/image`, for example:

```text
data/raw/Upper/Love Bone Bed Upper M3/UF-38252-01-UM3.nef
data/raw/Lower/Tyner_Farm/UF-212304-RL_occlusal.tiff
```

The directory supplied to BioEncoder must contain exactly one immediate directory per site.

## Installation

Python 3.10 or 3.11 and CUDA-capable PyTorch are recommended for training.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install the PyTorch build appropriate for the computer's CUDA version if the default package
is unsuitable. SAM3 is optional; install `autodistill` and `autodistill-sam3` only when needed.

## Upper-M3 workflow

The commands below reproduce the current strict upper-M3 RGB experiment:

```powershell
python scripts/01_convert_nefs.py --input data/raw/Upper --output data/preprocessed/upper_m3
python scripts/02_build_manifest.py --images data/preprocessed/upper_m3 --output outputs/manifests/upper_m3.csv
python scripts/03_segment_all.py --input data/preprocessed/upper_m3 --output data/segmented/upper_m3 --method contour
python scripts/04_standardize_images.py --input data/segmented/upper_m3 --output data/standardized/upper_m3_strict --curation metadata/upper_m3_image_qc.csv
python scripts/05_train_bioencoder.py --images data/standardized/upper_m3_strict/rgb --allow-image-level-split --allow-single-specimen-class --run-name proboscidean_upper_standardized_rgb_v1
python scripts/06_plot_embeddings.py --run-name proboscidean_upper_standardized_rgb_v1 --title "Proboscidean upper M3 embeddings — strict RGB dataset"
```

The two `--allow-*` switches explicitly acknowledge that the current Tyner upper sample is
one individual represented by left and right teeth. The resulting validation metric is not
an estimate of generalization to new Tyner specimens.

For the grayscale control, use the same standardized dataset:

```powershell
python scripts/05_train_bioencoder.py --images data/standardized/upper_m3_strict/grayscale --allow-image-level-split --allow-single-specimen-class --run-name proboscidean_upper_standardized_gray_v1
python scripts/06_plot_embeddings.py --run-name proboscidean_upper_standardized_gray_v1 --title "Proboscidean upper M3 embeddings — strict grayscale dataset"
```

Add `--overwrite` to stages 01, 03, 05, or 06 only when intentionally replacing existing
derived outputs or runs. Stage 04 regenerates its included outputs when invoked.

## Lower-M3 workflow

The curated lower crops already live at `data/segmented/lower_m3`:

```powershell
python scripts/02_build_manifest.py --images data/segmented/lower_m3 --output outputs/manifests/lower_m3.csv
python scripts/04_standardize_images.py --input data/segmented/lower_m3 --output data/standardized/lower_m3 --curation metadata/image_qc.csv
python scripts/05_train_bioencoder.py --images data/standardized/lower_m3/rgb --allow-image-level-split --run-name proboscidean_lower_standardized_rgb_v1
python scripts/06_plot_embeddings.py --run-name proboscidean_lower_standardized_rgb_v1 --title "Proboscidean lower M3 embeddings — standardized RGB dataset"
```

## Segmentation and quality control

Contour segmentation is local and deterministic. It fills the detected external silhouette
while preserving original crown pixels, including dark enamel valleys and genuine breaks.
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

## Current pilot results

### Lower M3

After QC, the lower dataset contains 20 images representing 16 independent specimens:
12 Love Bone Bed, two Mixson's Bone Bed, and two Tyner Farm. Background/pose standardization
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

BioEncoder 1.0.5 uses an image-level splitter. Stage 05 blocks repeated specimens and
single-specimen classes by default; its override flags exist only for clearly labeled pilot
experiments. Specimen-grouped evaluation is the next analytical milestone.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Data and credits

Source specimens and photographs are controlled by their institutions and are not distributed
through this repository. Confirm permissions before sharing derived imagery.

Author: Aaron Gibson<br>
Advisors: Arthur Porto and Advait Jukar<br>
University of Florida

BioEncoder should be cited using its authors' recommended citation. Specimens derive from the
Florida Museum of Natural History and Smithsonian National Museum of Natural History collections.
