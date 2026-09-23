# Frozen DINOv3 workflow

This workflow uses Meta's pretrained DINOv3 ViT-B/16 as a frozen visual feature extractor.
There is no encoder training, fine-tuning, optimizer, learned classification head, or
BioEncoder dependency. Site labels are used only after extraction for exploratory comparison.
The original pilot used masks that removed visible tooth surfaces. The default now uses
reviewed conservative crops on black backgrounds; see [image preparation](conservative-crops.md).
The pretrained runs completed on 2026-09-23. See the
[pilot findings](dinov3-pilot-results.md) and local `outputs/dinov3/index.html` overview.
Tiny randomly initialized models in tests are software checks only.

## Local installation

On this workstation, `.venv` reuses CUDA PyTorch from the existing `fossil_teeth` Conda
environment and has its own Transformers installation. The Conda environment was not modified.
Use `.venv\Scripts\python.exe` directly; PowerShell activation is unnecessary.
The installed/tested inference versions are PyTorch 2.5.1+cu121, torchvision 0.20.1+cu121,
Transformers 4.57.6, and huggingface-hub 0.36.2. The GPU is an RTX 3070 with 8 GB VRAM.
The inherited environment contains unrelated optional inference packages; use this venv for
the DINOv3 scripts, and the original Conda environment for legacy tools.

For a fresh machine, create a Python 3.10/3.11 venv:

```powershell
python -m venv .venv
```

Install a compatible PyTorch/torchvision pair into that venv using the
[official installer](https://pytorch.org/get-started/locally/), then install the remaining dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dinov3.txt
```

The above installs conservative cropping and extraction/analysis dependencies. Existing conversion and segmentation
tools have additional dependencies listed in `requirements.txt`.

## One-time checkpoint access

1. Create and verify a [Hugging Face account](https://huggingface.co/join).
2. Open [Meta's ViT-B/16 model page](https://huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m),
   complete its access form, and wait for approval if required.
3. Create a read token in [Hugging Face token settings](https://huggingface.co/settings/tokens).
   A fine-grained token must permit reading the gated model your account can access.
4. From the project directory, run this locally and paste the token at the hidden prompt:

```powershell
.venv\Scripts\hf.exe auth login
```

Do not add it as a Git credential when asked; that is unnecessary for this workflow.
Never put a token in chat, source, a command-line argument, or a committed file.
The login is stored by Hugging Face's credential mechanism. Downloads are cached under
the ignored `.cache/huggingface/hub` directory. Extraction uses `safetensors` weights and
does not execute remote model code. It fails on missing/mismatched checkpoint weights.

## Run the pilot

Prepare the reviewed images from the existing source photographs first (only once):

```powershell
.venv\Scripts\python.exe scripts/prepare_conservative_crops.py
```

Inspect `outputs/qc/crop_black_v2/index.html`. This bypasses stages 03 and 04 entirely.
The committed recipes cover the current 17 upper and 20 lower images, preserving the
previous inclusion decisions. New photographs need new reviewed recipes.

Audit all four datasets without downloading a model:

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py --inventory-only
```

Once checkpoint access and login are ready, run all upper/lower and RGB/grayscale analyses:

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py
```

Start with lower RGB alone if preferred:

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py --dataset lower --color rgb
```

Existing completed runs are protected; use a new `--output` with the extraction command
below, or explicitly pass `--overwrite`. The default is whole-image 224px input with a
batch size of four. A predefined 512px sensitivity run uses `--image-size 512 --batch-size 1`
and receives a separate output directory. Do not select settings by the prettiest separation.

Run stages independently, including a reviewed metadata manifest when available:

```powershell
.venv\Scripts\python.exe scripts/05_extract_dinov3.py --images data/standardized/crop_black_v2/lower/rgb --tooth-position lower_m3 --output outputs/dinov3/lower_rgb_crop_black_v2_224 --padding-value 0 --crop-provenance outputs/qc/crop_black_v2/provenance.json
.venv\Scripts\python.exe scripts/06_analyze_dinov3.py --run-dir outputs/dinov3/lower_rgb_crop_black_v2_224
```

Extraction options include `--device cpu`, `--revision <commit>`, `--local-files-only`,
and `--model <local-Hugging-Face-model-directory>`. A local model directory must contain
the pretrained safetensors weights, config, and image processor config. For a relative
local model path, use the extraction script directly; paths resolve from the project root.
Analysis can be regenerated from cached features without loading DINOv3:

```powershell
.venv\Scripts\python.exe scripts/06_analyze_dinov3.py --run-dir outputs/dinov3/lower_rgb_crop_black_v2_224 --overwrite
```

## Metadata and independence

The current filename-derived inventory is:

| Dataset | Locality | Images | Catalog IDs |
| --- | --- | ---: | ---: |
| Upper strict | Love Bone Bed | 12 | 12 |
| Upper strict | Mixson's Bone Bed | 3 | 3 |
| Upper strict | Tyner Farm | 2 | 1 |
| Lower | Love Bone Bed | 14 | 12 |
| Lower | Mixson's Bone Bed | 2 | 2 |
| Lower | Tyner Farm | 4 | 2 |

The four lower Tyner images are left/right teeth of `UF-212304` and `UF-217472` according
to their filenames. Confirm biological independence against collection records; catalog
numbers are a working grouping, not proof of independence. `metadata/specimens.csv` currently
contains only a header, so reports explicitly label the metadata as inferred.

To override filename grouping, copy the exported `inventory.csv` to a reviewed metadata CSV.
It must cover every included image exactly once, with `image_path` relative to the selected
RGB/grayscale dataset, `specimen_id`, and `site` columns. Optional `tooth_position` must match
the run. Pass it to extraction as `--manifest metadata/your_reviewed_manifest.csv`.
The same manifest may be reused for RGB and grayscale when their relative image paths match.

## Outputs and method

Default runs are saved under `outputs/dinov3/<position>_<color>_crop_black_v2_<size>/`.
`--preprocessing legacy` selects the historical inputs and original directory names:

- `embeddings.npz`: normalized per-image CLS features, ordered image records, and provenance.
- `image_index.csv`, `run.json`: source hashes, model revision, preprocessing, versions, and counts.
- `analysis/report.html`: self-contained local report with PCA, similarity heatmap, and neighbor panels.
- `analysis/report.md`, `summary.json`: numerical results and limitations.
- `analysis/specimen_embeddings.npy`, `specimen_coordinates.csv`, `cosine_similarity.csv`,
  `nearest_neighbors.csv`: reusable specimen-level data in consistent specimen order.
- `analysis/pca.png`, `similarity.png`, `neighbors_*.png`: figures.

Images retain their aspect ratio, with bicubic resizing and black padding for v2
(gray-127 padding for legacy). The 512px source canvas is already square and black. The checkpoint's
pixel rescaling/normalization follows; center-cropping is disabled. Extraction uses
`eval()`, frozen parameters, and `torch.inference_mode()` in float32. The first final-layer
token (CLS) is L2-normalized. The resolved Hugging Face commit is shared by config, processor,
and model within each extraction; local checkpoints instead have their weight hashes recorded.

For quantitative analysis, image vectors are averaged within each specimen and normalized
again. Each specimen has equal weight as an observation. Similarity is cosine similarity;
neighbors exclude the query specimen. A panel shows the first image of each specimen, while
ranking uses all its images. Upper and lower analyses are kept separate.

The separation statistic is mean within-site cosine minus mean between-site cosine over
distinct specimen pairs. Its one-sided Monte Carlo test permutes site labels at the specimen
level (9,999 permutations, seed 42), preserving site sizes. This is a pair-weighted descriptive
contrast; it does not treat pairs as independent observations. Its exchangeability assumption
may fail with photography or preservation confounding. Multiple runs are exploratory, without
multiple-testing correction. Undefined statistics are reported as null.

Nearest-neighbor locality agreement is reported only for queries with a same-site reference;
singleton localities remain visible in plots/retrieval and are explicitly unsupported for
recognition. Thus upper Tyner cannot be validated for locality recognition. This is a fixed
reference-matching rule, not a trained classifier or label-free taxonomic prediction.
PCA is centered without per-dimension scaling and is only a visualization; statistics use
the full feature vectors. No images are uploaded by the pipeline.

## Validation

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover paired-tooth exclusion, singleton handling, specimen-label permutations,
reviewed metadata, full-image preservation, cache provenance, report generation, and changed
input detection. When torch/Transformers are available, a tiny DINOv3 forward on synthetic
images checks frozen parameters and determinism without downloading any weights.

Primary sources: [Meta repository](https://github.com/facebookresearch/dinov3),
[checkpoint](https://huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m),
[Transformers documentation](https://huggingface.co/docs/transformers/model_doc/dinov3).
