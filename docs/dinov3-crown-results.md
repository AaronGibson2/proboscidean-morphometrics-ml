# Crown-patch experiment results

Completed 2026-09-23 using the fixed [experiment protocol](dinov3-crown-experiment.md),
37 photographs and the frozen pretrained ViT-B/16 checkpoint. No training or fine-tuning.
The crown-patch and CLS features were extracted from the same forward pass for each image.
Both resolutions were prepared directly from the full-resolution source crops.

## All eight conditions

Macro recall means the average nearest-neighbor recall across eligible localities, giving
each locality equal weight. Upper Tyner is excluded as a query because it has one catalog ID.
The constant Love Bone Bed baseline is 50% macro recall for upper and 33.3% for lower;
ordinary accuracy baselines are 80% and 75%, respectively.

| Position | Pixels | Features | Macro recall | Ordinary agreement | Raw macro permutation p | Holm p across 8 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Upper | 224 | CLS | 66.7% | 10/15 (66.7%) | 0.0720 | 0.4146 |
| Upper | 224 | Crown patches | 66.7% | 10/15 (66.7%) | 0.0691 | 0.4146 |
| Upper | 512 | CLS | 75.0% | 12/15 (80.0%) | 0.0363 | 0.2616 |
| Upper | 512 | Crown patches | 75.0% | 12/15 (80.0%) | 0.0327 | 0.2616 |
| Lower | 224 | CLS | 44.4% | 11/16 (68.8%) | 0.1088 | 0.4164 |
| Lower | 224 | Crown patches | 44.4% | 11/16 (68.8%) | 0.1041 | 0.4164 |
| Lower | 512 | CLS | 33.3% | 12/16 (75.0%) | 0.2614 | 0.5228 |
| Lower | 512 | Crown patches | 33.3% | 12/16 (75.0%) | 0.2619 | 0.5228 |

At 224px the upper recalls are Love 8/12 and Mixson 2/3. At 512px they are Love 10/12
and Mixson 2/3. Lower 224px recalls are Love 10/12, Mixson 0/2, and Tyner 1/2; lower
512px recalls are Love 12/12, Mixson 0/2, and Tyner 0/2. Crown pooling and CLS have the
same per-site recall at each resolution, although their vectors and permutation distributions
differ. Four lower Tyner photographs still count as two catalog IDs.

## Interpretation and next decision

Increasing resolution improved upper recall descriptively, but the macro permutation tests
are not significant after correction across the eight planned conditions. These tests assess
each condition against permuted locality labels; they do not test the 224-to-512 difference.
No condition beats the majority baseline on ordinary agreement. Balanced recall reveals
that the lower 512px result sacrifices both smaller localities despite higher overall accuracy.

Crown-patch averaging did not improve locality recall over CLS in this experiment.
This does not rule out local matching: averaging discards spatial arrangement, and the patch
vectors can still incorporate matrix, staining, or other context through model attention.
The next scientifically useful steps are advisor review of a small set of anatomical pairs,
wear/preservation metadata, and evaluating corresponding crown regions rather than another
unconstrained parameter search. Additional independent Mixson/Tyner specimens remain valuable.

Locality separation is not taxonomic identification. The taxa column remains unpopulated;
there are no independent taxon labels against which to validate species discrimination.
Locality differences could reflect morphology, wear, preservation, or photography. These
results can guide hypotheses and collection priorities but cannot establish different species.

## Review and reproduction

- `outputs/dinov3_crown_v1/index.html`: eight-condition overview and links to individual reports.
- `outputs/dinov3_crown_v1/comparison.csv` and `comparison.json`: all primary metrics.
- `outputs/qc/crown_regions_v1/index.html`: all 37 photographs and contributing 224/512px patches.
- Each run contains features, image hashes, crop/region/protocol provenance, secondary cosine
  statistics, and independent-specimen neighbor panels.
- `*_patch_tokens_*` folders preserve spatial tokens, coverage grids, and image identities.

```powershell
.venv\Scripts\python.exe scripts/run_dinov3_crown_experiment.py --prepare-only
# Review the crown-region gallery; then run once:
.venv\Scripts\python.exe scripts/run_dinov3_crown_experiment.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All 25 tests passed. New tests verify exclusion of CLS/register/background tokens, coverage
weighting, mask alignment under all quarter turns and mirroring at both resolutions, detached
regions, equal locality weighting, singleton handling, Holm adjustment, and a frozen forward
through the real DINOv3 architecture using synthetic weights only for that software test.
All ten real-image overlay sheets were inspected before extracting experimental features.
