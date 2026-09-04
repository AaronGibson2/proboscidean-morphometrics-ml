# Proboscidean Morphometrics ML

A reproducible image-analysis pipeline for exploring morphological variation in Miocene
proboscidean third molars. The immediate study compares material from Love Bone Bed,
Mixson's Bone Bed, and Tyner Farm.

This repository is research software under active development. Embedding clusters are
hypothesis-generating results; they are not, by themselves, taxonomic diagnoses.

## Pipeline

1. Convert NEF/TIFF source photographs to consistent 16-bit RGB TIFFs.
2. Build an auditable specimen manifest with source hashes.
3. Isolate each tooth and generate visual quality-control images.
4. Standardize orientation, scale, and background; export RGB and grayscale controls.
5. Learn morphology embeddings with BioEncoder.
6. Explore the learned space with PCA and t-SNE.

All scripts resolve default paths from the repository root, so they can be launched from
any working directory.

## Repository layout

```text
bioencoder_configs/       BioEncoder experiment configuration
data/
  raw/                    Original photographs (ignored by Git)
  preprocessed/           Standardized TIFFs and conversion report (ignored)
  segmented/              Cropped, masked teeth (ignored)
  standardized/           Analysis-ready RGB and grayscale controls (ignored)
outputs/
  bioencoder/             Weights, logs, and plots (ignored)
scripts/                  Numbered pipeline stages and shared utilities
tests/                    Fast metadata/unit tests
```

Within `raw`, preserve the hierarchy `tooth_position/site/image`, for example:

```text
data/raw/Upper/Love_Bone_Bed/UF-38252-01-UM3.nef
data/raw/Lower/Tyner_Farm/UF-212304-RL_occlusal.tiff
```

The directory passed to BioEncoder must contain one immediate subdirectory per class.
For an upper-M3 site comparison, use `data/segmented/Upper`, whose immediate children
should be the three site directories.

The curated lower-M3 dataset currently lives at `data/segmented/lower_m3` and contains
the three site directories expected by BioEncoder.

## Installation

Python 3.10 or 3.11 and a CUDA-capable PyTorch installation are recommended for training.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install PyTorch using the command recommended for the local CUDA version if the default
package is unsuitable. SAM3 is optional; install `autodistill` and `autodistill-sam3` only
when it will be used.

## Usage

Run these commands from the repository root:

```powershell
python scripts/01_convert_nefs.py
python scripts/02_build_manifest.py
python scripts/03_segment_all.py --method contour
python scripts/02_build_manifest.py --images data/segmented
python scripts/04_standardize_images.py --input data/segmented/upper_m3 --output data/standardized/upper_m3 --curation metadata/upper_m3_image_qc.csv
python scripts/05_train_bioencoder.py --images data/standardized/upper_m3/rgb --run-name upper_m3_rgb_v1
python scripts/06_plot_embeddings.py --run-name upper_m3_rgb_v1
```

To rerun the existing lower-M3 experiment without reconverting or resegmenting images:

```powershell
python scripts/04_standardize_images.py --input data/segmented/lower_m3 --output data/standardized/lower_m3
python scripts/05_train_bioencoder.py --images data/standardized/lower_m3/rgb --allow-image-level-split --run-name lower_m3_rgb_v1
python scripts/06_plot_embeddings.py --run-name lower_m3_rgb_v1
```

The contour method is local, deterministic, and the default. To try SAM3, set the
credential in the process environment—never in a source file—and run:

```powershell
$env:ROBOFLOW_API_KEY = "your_key"
python scripts/03_segment_all.py --method auto --overwrite
```

`auto` tries SAM3 and falls back to contour segmentation. Inspect every image under
`data/qc/segmented` before training. A successful script run does not imply a biologically
valid crop.

Use `--help` on any numbered script for all path and overwrite options.

## Reproducibility and scientific validity

- Keep raw images immutable. Conversion and segmentation reports record what happened.
- Treat the specimen—not the photograph or left/right view—as the independent unit.
- Never place views from one specimen in both training and validation data.
- Record site, catalog number, tooth position, side, camera/setup, scale, and processing
  decisions in the manifest; verify all filename-derived fields manually.
- Analyze upper and lower M3s separately unless a preregistered design says otherwise.
- Compare learned embeddings against simple image and morphometric baselines.
- Report grouped cross-validation, uncertainty, and permutation tests. Do not interpret
  t-SNE distance or apparent clusters as inferential statistics.
- Site and taxon are currently confounded. Claims must account for acquisition background,
  collection, preservation, and sample-size effects.

BioEncoder's built-in splitter is image-level. Stage 05 warns when repeated specimen IDs
are present; its validation metrics must not be reported as final results in that case.
A specimen-grouped evaluation is the next required analytical milestone.

## Current lower-M3 pilot result

The present lower-M3 collection is a pipeline pilot, not a significance-ready dataset.
After quality-control exclusion it contains 20 images but only 16 independent specimens:
12 from Love Bone Bed, 2 from Mixson's Bone Bed, and 2 from Tyner Farm. A three-image
BioEncoder validation score is therefore unstable and must not be interpreted as accuracy.

Standardizing the background and pose modestly improved the two-dimensional PCA silhouette
score compared with the original photographs (-0.062 versus -0.146), while grayscale was
worse (-0.310). All values remain negative, so none of these runs shows convincing site
separation. The next defensible step is to add substantially more independent specimens per
site, process upper and lower molars separately, and then use specimen-grouped repeated
cross-validation with permutation testing and confidence intervals.

## Current upper-M3 pilot result

Strict quality control retained 17 images: 12 Love Bone Bed specimens, three Mixson's Bone
Bed specimens, and two contralateral teeth belonging to one Tyner Farm specimen. Standardized
RGB embeddings produced silhouette scores of 0.193 in PCA and 0.070 in t-SNE; grayscale
produced 0.150 and 0.107, respectively. The positive overall scores are driven primarily by
the close Tyner pair. Because those points are two teeth from one individual rather than two
independent specimens, this is an exploratory observation rather than evidence for locality
classification. Mixson's specimens remain dispersed in both controls.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Data and credits

Raw specimen images are controlled by their source institutions and are intentionally
excluded from Git. Confirm permissions before distributing derived images.

Author: Aaron Gibson<br>
Advisors: Arthur Porto and Advait Jukar<br>
University of Florida

BioEncoder should be cited using the citation provided by its authors. Specimens derive
from the Florida Museum of Natural History and Smithsonian National Museum of Natural
History collections.
