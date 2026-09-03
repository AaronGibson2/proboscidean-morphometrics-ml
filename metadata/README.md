# Specimen metadata

`specimens.csv` is the curated, specimen-level source of truth. Keep one row per museum
catalog number; do not create separate biological specimens for multiple photographs,
sides, or views.

Required before inferential analysis:

- `specimen_id`: stable museum prefix and catalog number, such as `UF-38249`
- `institution`: repository holding the specimen
- `site`: fossil locality, using one spelling consistently
- `taxon`: identification and qualifier (`cf.`, `?`, etc.); do not infer this from site
- `tooth_position`: controlled value such as `upper_m3` or `lower_m3`
- `side`: `left`, `right`, `both`, or `unknown`
- `scale_mm_per_pixel`: calibrated image scale, when available
- `photography_batch`: camera/setup/batch identifier for confounding checks
- `notes`: preservation, reconstruction, occlusion, or exclusion rationale

The automatically generated image manifest links files to inferred specimen IDs. Review it
against this table; filenames are not authoritative metadata.
