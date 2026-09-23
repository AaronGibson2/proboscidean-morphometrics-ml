# Conservative tooth crops on black backgrounds

Prepared 2026-09-23 after visual review found that the original masks removed real
occlusal surfaces. The second GrabCut pass in `04_standardize_images.py` retained only
31.61% of a marked enamel region in lower UF-38220 (source x=200:500, y=220:550).
The replacement retains 100% of those source pixels. Largest-component selection also
dropped detached Tyner pieces; the new workflow preserves them.

## Inputs and operations

`metadata/conservative_crops_v2.json` records all 37 source paths, SHA-256 hashes,
dimensions, pixel crop boundaries, background-only exclusion polygons, quarter turns,
left-tooth mirroring, and image-specific limitations. The upper 17 use original converted
16-bit TIFFs. The lower 20 use the earliest available JPEG crops in `data/segmented/lower_m3`.
Existing inclusion/exclusion decisions and catalog groupings are unchanged.

No foreground estimation, GrabCut, thresholding, erosion, largest-component selection,
learned segmentation, generative editing, or inpainting is used. Every pixel inside the
reviewed region is copied from its source. Exclusions zero only manually selected background
regions. Full-resolution crops retain the source bit depth in lossless compressed TIFFs
under `data/cropped_v2`. Original photographs and historical outputs remain available.

Model inputs use fixed uint16-to-uint8 conversion (`value // 257`), optional lossless
quarter turns and left mirroring, aspect-preserving Lanczos resizing to fit 90% of a
512px black canvas, and an RGB or grayscale derivative. DINOv3 then resizes the entire
square to 224px with bicubic interpolation. No center crop is applied. New runs explicitly
use black model padding and embed the crop provenance in `run.json` and the feature bundle.

## Reproduce and review

```powershell
.venv\Scripts\python.exe scripts/prepare_conservative_crops.py
.venv\Scripts\python.exe scripts/run_dinov3_pilot.py --local-files-only --revision 5931719e67bbdb9737e363e781fb0c67687896bc
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The builder refuses changed source hashes and existing outputs unless `--overwrite` is
explicit. Do not change recipes beneath a published run: use a new dataset version for
subsequent scientific revisions. The current run folders include `_crop_black_v2_224`;
the original pilot folders are preserved. `--preprocessing legacy` reproduces their input
selection but is not the default.

Open `outputs/qc/crop_black_v2/index.html` for all 37 comparisons. Left: source with crop
boundaries and exclusions. Middle: legacy input. Right: new black-background input.
Full-resolution crops and `provenance.json` support closer inspection. All ten comparison
sheets were visually checked, and remaining label corners were corrected before extraction.

## Remaining limitations

- Several lower sources already touch or cut through specimen margins. The available
  images cannot recover anything outside those original JPEG frames.
- Attached bone/matrix is retained where removing it could risk tooth structure. Small
  backing margins can remain along ambiguous boundaries; these are documented in recipes.
- Separate paper museum labels and scale cards are excluded. Numbers painted directly
  on teeth remain, because removing them would alter tooth pixels.
- Upper images are darker than the old percentile-stretched images. Brightness, background,
  orientation and crop geometry changed together, so the result difference is not a
  controlled test of segmentation alone.
- This is assistant visual QC, not anatomical certification. Advisor review of the gallery
  and collection-record confirmation of specimen grouping remain necessary for interpretation.

Regression tests cover the actual UF-38220 enamel region, the lower UF-217472 detached
fragment, paper-label locations, dark regions, uint16 preservation, and black padding
through the actual DINO image preprocessing function. Private-photo tests skip when their
sources are unavailable, while synthetic and recipe geometry tests run in CI.
