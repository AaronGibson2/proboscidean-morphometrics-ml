# BioEncoder configuration

All active configurations use `timm_resnet50`, 224-pixel inputs, and three site classes.
Stage one learns a supervised contrastive embedding. Stage two is retained for future
classification experiments, but should not be interpreted until specimen-grouped splits
and adequate per-site sample sizes are available.

Shape-changing augmentations such as optical and grid distortion are intentionally absent:
they can manufacture variation in the morphological signal under study. Any augmentation
change should be recorded as an experiment and justified biologically.

These files target BioEncoder 1.0.5, pinned in `requirements.txt`.
