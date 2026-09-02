# Proboscidean Morphometrics ML

Machine learning pipeline for morphological analysis and taxonomic 
classification of proboscidean fossil teeth using BioEncoder and SAM3.

## Project Overview

This project develops an automated image analysis pipeline to compare 
and classify Miocene gomphothere molars (M3) from three Florida fossil 
sites. The goal is to determine whether specimens from different sites 
represent the same or distinct taxa based on tooth morphology.

## Study Taxa & Sites

| Site | Taxon | Specimens |
|------|-------|-----------|
| Love Bone Bed (LBB) | *Amebelodon floridanus* | UF-38208 to UF-38249 |
| Mixson's Bone Bed | Referred *A. floridanus* | USNM-3082, USNM-3083 |
| Tyner Farm | Unknown gomphothere | UF-212304, UF-217472 |

## Pipeline

1. `01_convert_nefs.py` — Convert NEF/TIFF images to standardized TIFFs
2. `03_segment_all.py` — Segment fossil teeth using SAM3
3. `04_run_bioencoder.py` — Train BioEncoder metric learning model
4. `05_plot_embeddings.py` — Generate interactive t-SNE/PCA plots

## Dependencies

- Python 3.10
- PyTorch (CUDA)
- BioEncoder
- autodistill-sam3
- rawpy, tifffile, opencv

## Installation

```bash
conda create -n fossil_teeth python=3.10 -y
conda activate fossil_teeth
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install autodistill autodistill-sam3 bioencoder roboflow inference
pip install sam3 triton rawpy tifffile pillow opencv-python numpy
pip install imagecodecs supervision bokeh scikit-learn
```

## Current Status

- [x] Lower M3 segmentation and embedding pipeline
- [x] Preliminary t-SNE clustering of lower M3s
- [ ] Upper M3 integration
- [ ] Fine-tuning on fossil tooth data
- [ ] Stage 2 BioEncoder classification

## Authors

Aaron Gibson  
Advisors: Arthur Porto, Advait Jukar 
University of Florida

## Acknowledgements

Specimens from the Florida Museum of Natural History and 
Smithsonian National Museum of Natural History.

## Data Availability

Raw specimen images are property of the Florida Museum of Natural 
History and are not included in this repository. Contact the respective institutions 
for data access.
