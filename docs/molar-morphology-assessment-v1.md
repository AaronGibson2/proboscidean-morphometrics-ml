# What our molars can tell us about identity

23 September 2026. Literature review, public collection-record crosswalk and visual screening of all 37 photographs. This is a preliminary assessment, not a specialist identification or a new DINOv3 experiment.

**The useful finding is that we already have candidate reference specimens in our dataset. The immediate priority is to verify those references and compare tooth anatomy, rather than treating locality as a species label.** Some teeth remain compatible with multiple groups; this review does not establish an additional species.

Open the **[GitHub photo gallery](morphology-gallery-v1/README.md)** for all 37 photographs and observations, or download its standalone HTML to use the interactive filters. The original **[local visual tooth review](../outputs/morphology_literature_v1/index.html)** remains available on this workstation. The [primary-literature guide](molar-taxonomy-primary-literature.md) contains the detailed character definitions, paper links and figure/table locations.

## What we should look for

*Gomphotherium* and *Amebelodon* are genera, not two species. Our specific comparison is with the Florida **floridanus** material and with **Gomphotherium of uncertain species**. The museum article supports that starting hypothesis, but it describes a wider study of jaws and teeth and does not identify each photograph in this project. [Florida Museum research update](https://www.floridamuseum.ufl.edu/nhdept/from-the-field/2026/amebelodon-or-not-that-is-the-question-a-reevaluation-of-amebelodontid-specimens-from-the-miocene-of-florida/).

Think of a molar as rows of large bumps, with smaller bumps between them. Wear joins some of those bumps into clover-like outlines. We need to compare the **arrangement**, not just the silhouette.

| Character | What we need to establish in each tooth | Why a simple rule fails |
| --- | --- | --- |
| Crosswise ridges, called lophs in upper teeth and lophids in lower teeth | Complete main rows, separately from a small terminal heel | Counts overlap; damage and the interpretation of the last structure change the count |
| Accessory cusps and trefoiling | Which half of each ridge has accessory structures or clover-like wear outlines | Wear can reveal or erase the pattern; anatomical sides must be verified |
| Serridentine structure | Actual subdivision into small cusps along crests | A crack, enamel wrinkle or stain is not an accessory cusp; subdivision is not exclusive to one genus |
| Crown proportions | Complete length, ridge widths and posterior taper | Broken crowns, perspective and unscaled photos can produce false differences |
| Associated anatomy | M2/m2, jaw and tusks securely associated with the catalog specimen | Some distinctions cannot be resolved from an isolated third molar |

These are a review checklist, not a validated identification key. The source-by-source evidence, exceptions and anatomical orientation definitions are in the [literature guide](molar-taxonomy-primary-literature.md#2-a-proposed-scoring-sheet-for-our-images). Upper **M3** and lower **m3** must be compared separately.

The practical comparison is a **combination of tendencies**, with substantial overlap:

| Feature | Conservative Gomphotherium comparison | floridanus comparison |
| --- | --- | --- |
| Clover-like pattern | Usually concentrated on the pretrite half; the opposite half is simpler | Look for weak additional complexity on the opposite, posttrite half, potentially only along part of the crown |
| Main rows and elongation | Variable; some lower third molars have five rows | Relatively elongated third molars are emphasized, but terminal-row interpretation is not uniform |
| Small cusp subdivisions | Can occur | Also described; their presence alone cannot separate the groups |

These tendencies synthesize the [Gomphotherium population study](https://doi.org/10.5252/g2014n1a2), [North American comparative material](https://doi.org/10.19615/j.cnki.1000-3118.200310), and the floridanus comparisons detailed in the literature guide. A tooth with a conservative pattern can remain compatible with multiple taxa. Tooth-side orientation and wear must be established before applying even this tentative comparison.

## What we can presently say about our specimens

I matched all **27 UF catalog numbers** to original UF Vertebrate Paleontology records distributed through iDigBio. These are exact institution/collection/catalog-number matches, not authenticated matches between a physical specimen and our photo. Provider names were retained separately from iDigBio's normalized search labels. Retrieval date, individual record links, provider modification dates and the raw-response checksum are preserved in [catalog evidence](../metadata/morphology_catalog_evidence_v1.json). Source: [UF Vertebrate Paleontology dataset](https://ipt.floridamuseum.ufl.edu/ipt/eml.do?r=ufvp).

| Evidence category | Catalog IDs in our data | Interpretation now |
| --- | --- | --- |
| Catalog says **Gomphotherium** | UF 38208, 38213, 38220, 38228, 38231, 38232, 38233, 38235, 38240, 38241, 38244, 38249 | Twelve Love candidates for a Gomphotherium comparison panel; no species assignment |
| Catalog says only **Amebelodontinae** | UF 276840, 38215, 38216, 38218, 38221, 38223, 38226, 38234, 38237, 38239, 38243, 38247 | Twelve Love specimens remain unresolved at genus level. This could reflect catalog history; it does not demonstrate a second Love taxon |
| **floridanus** catalog association, with third molars included in the published specimen description | UF 212305, UF 217472 | Tyner reference candidates; verify which associated tooth each photo shows and account for fragments |
| Exact **published reference molar** catalog numbers | USNM 3083, USNM 3084 | Strongest literature anchors in this dataset, subject to photo-identity verification |
| **Tooth-position conflict** | UF 212304 | Hold out of a confirmed M3/m3 reference set until resolved |
| No exact catalog/literature identification verified in this review | USNM 3080, USNM 3082, USNM 3085 | Keep unresolved; Mixson provenance alone does not establish identity |

These total **32 catalog/position rows, represented by 37 photos**, not 37 independent animals. The published-specimen links and the position conflict come from [Lambert 2023](https://doi.org/10.1080/02724634.2023.2252021); see the literature guide for locators. Paired teeth and associated skeletal material require collection confirmation.

### A concrete issue to resolve first

**UF 212304 is described with m1/m2 in the paper, while our two images are filed as m3.** The paper or our metadata could be wrong; the discrepancy alone cannot decide that. Obtain the specimen sheet or confirm the tooth's position in its mandible. Until then, do not interpret its apparent ridge count as a third-molar taxonomic difference.

This affects two of the four lower Tyner photographs and one of its two catalog IDs. Previously saved analyses still include those files under the original labels; their values are unchanged. The unresolved position adds a limitation to their biological interpretation.

### What was actually visible

- **UF 38213 and UF 38220:** clover-like worn outlines are conspicuous in one image half, with rounder outlines in the other. This makes them useful for inspecting asymmetric wear patterns. The observation alone does not diagnose a genus.
- **UF 38234 and UF 38243:** raised cusps and smaller knobs provide candidates for a detailed cusp-layout review. Their broad catalog labels should not be upgraded from appearance alone.
- **USNM 3083 and USNM 3084:** visible cusp structures can be compared directly with published plates carrying those catalog numbers. This is stronger than choosing a reference solely because it comes from Mixson.
- **UF 212305 right and UF 217472 right:** detached portions must be considered before a whole-tooth ridge count is attempted.
- Several other photos have strong wear, obscuring matrix, fractures or tight source-image margins. Absence of a visible cusp cannot safely be scored as anatomical absence.

The complete photo-by-photo notes are in [visual observations](../metadata/morphology_observations_v1.json) and the local gallery. These notes are assistant observations, not independent specialist scores. Formal ridge counts, anatomical orientation, cusp states and calibrated measurements remain unscored rather than guessed. Display-left/right is not anatomical left/right. The gallery uses recorded quarter turns but **does not mirror the teeth**; it preserves the existing crop exclusions and does not reconstruct missing edges.

## Could they be another species?

**Possibly, but this review has not established a morphological contradiction that requires that conclusion.** An unusual image, a distant DINOv3 neighbor or a mismatch to a single reference tooth is insufficient.

The literature guide includes **A. hicksi** and **A. fricki** for dental overlap and contrast, **Konobelodon britti** as a relevant Florida alternative, and other taxa as comparative examples. They are not equally supported identifications for our material. Expand the comparison when a clearly preserved combination disagrees with the initial reference set; check chronological plausibility and associated anatomy before assigning a name.

The name of floridanus itself is disputed: Jukar and colleagues retain **Amebelodon**, whereas Lambert favors **Stenobelodon**. That disagreement is not evidence that our photos contain two floridanus species. The full Jukar paper was not obtained; this review used its abstract and accessible primary texts for the other comparisons. [Jukar et al. 2025](https://doi.org/10.1080/02724634.2025.2453301); [Lambert 2025 response](https://www.researchgate.net/publication/396476723_THE_VALIDITY_OF_THE_GENUS_STENOBELODON_PROBOSCIDEA_GOMPHOTHERIIDAE_A_RESPONSE_TO_THE_REFERRAL_OF_THE_MIXSON%27S_BONE_BED_LATE_MIOCENE_FLORIDA_GOMPHOTHERE_TO_AMEBELODON).

## The next experiment should test anatomy

1. Verify UF 212304's tooth position and the identities of the reference photos. Obtain associated jaw/tusk records for Tyner and the full recent floridanus paper.
2. Mark orientation, main ridges, terminal structures and accessory cusps on a small reference panel; compare similar wear stages and upper/lower positions separately. Score visible traits with locality and existing proposed identity hidden where feasible, and reconcile independent specialist reviews.
3. Record each specimen as compatible with a reference group, compatible with several groups, contradictory, or insufficiently observable. Preserve reasons and annotated regions, rather than forcing a binary label.
4. Only then ask whether frozen DINOv3 features retrieve teeth with similar **verified anatomy**. Keep same-catalog photographs together, account for wear and damage, and retain an unresolved group. No training is required.

This would test whether DINOv3 follows anatomical evidence. The current screening does not provide verified taxon labels for measuring species accuracy.

## Rebuild the local review

```powershell
.venv\Scripts\python.exe scripts/build_morphology_review.py
```

The builder checks source-photo hashes, recreates previews from existing crop recipes and writes `outputs/morphology_literature_v1/index.html`, a specimen evidence CSV and an audit summary. It needs the local source images. To rebuild the committed shareable snapshot, run `.venv\Scripts\python.exe scripts/export_morphology_gallery.py`. That exports a GitHub-readable gallery, compressed viewing images and standalone HTML to `docs/morphology-gallery-v1/`, with provenance hashes. Generated working reports remain in ignored `outputs/`. Original metadata inventories, model features and historical results are unchanged.
