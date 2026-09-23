# DINOv3 frozen-feature pilot

Checked against primary sources on 2026-09-23. This is a proposed analysis, not an implementation or a result.

## Verified capabilities

DINOv3 is already a self-supervised vision model family; using its pretrained checkpoint does not require self-supervised training on our teeth. The paper presents reusable global and dense features across downstream tasks. [DINOv3 paper](https://arxiv.org/abs/2508.10104)

Meta explicitly supports frozen-feature nearest-neighbor retrieval and k-NN classification. ViT-B/16 has approximately 86 million parameters and a 768-dimensional embedding; ViT-S/16 has 21 million parameters and 384 dimensions. The Hugging Face checkpoint is gated behind agreement to access conditions. Recommendation: start with `facebook/dinov3-vitb16-pretrain-lvd1689m`, using ViT-S if local inference resources require it. Benchmark actual memory and runtime before promising hardware requirements. [Meta model card](https://huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m)

The whole-image CLS token supports retrieval, while patch tokens represent local 16-by-16 input regions. Registers are separate from patch tokens and must be excluded from spatial pooling. Transformers supports `AutoImageProcessor` and `AutoModel`; extraction uses inference mode. Recommendation: explicitly set evaluation mode, freeze parameters, and cache embeddings plus checkpoint revision and preprocessing settings. [Transformers DINOv3 documentation](https://huggingface.co/docs/transformers/model_doc/dinov3)

The official web-image transform rescales pixels and uses ImageNet mean `(0.485, 0.456, 0.406)` and standard deviation `(0.229, 0.224, 0.225)`. The repo offers pretrained heads for specific downstream tasks, including a separate text-aligned `dino.txt` model. Base visual embeddings do not themselves provide text-prompt classification or fossil taxon labels. The foreground-segmentation example trains a linear model, so it does not meet this project's no-training constraint. [Official repository](https://github.com/facebookresearch/dinov3)

## Proposed project protocol

These are analysis recommendations based on the capabilities above and the current [project README](../README.md), not claims of validated fossil performance.

1. Reuse the curated standardized crops, masks, and QC decisions; analyze upper and lower M3s separately. Confirm biological specimen IDs before quantitative evaluation.
2. Extract frozen CLS embeddings for a simple first baseline. Preserve the full tooth and aspect ratio. Use the checkpoint's recorded preprocessing; test 512-pixel input as a predefined resolution check if needed for fine crown detail. Never choose preprocessing because it gives the most attractive locality separation.
3. L2-normalize features and compute cosine similarities. Produce nearest-neighbor image panels, a similarity matrix, and PCA colored by locality only after feature extraction. Treat projected clusters as exploratory.
4. Repeat the same protocol with existing grayscale images converted to three channels. Check whether similarities follow morphology, staining, wear, missing crown regions, background, or photography batch.
5. If the baseline is promising, pool foreground patch embeddings using aligned tooth masks and inspect patch similarity maps. This is a separate, predefined sensitivity analysis; patch similarity alone does not establish anatomical homology.
6. Evaluate at the specimen level. Exclude every image of the query specimen from its reference set. A fixed nearest-neighbor rule requires no learned classifier weights, but any site prediction still uses labeled reference specimens. Do not call that label-free zero-shot classification. Linear probes and logistic regression would introduce training and are out of scope.
7. The upper Tyner sample contains only one independent individual, so held-out Tyner recognition cannot be evaluated from these data: removing that individual leaves no Tyner reference. Report descriptive similarities and the limitation, rather than claiming three-site generalization. Small lower-site sample sizes also limit inference.

First deliverable: cached embeddings, specimen-linked nearest-neighbor panels, PCA, similarity matrices, and a brief RGB/grayscale comparison. No encoder retraining, fine-tuning, learned head, or optimizer is needed. The scientific question is whether pretrained features reveal reproducible morphological structure associated with locality; locality separation alone would not establish taxonomic differences.
