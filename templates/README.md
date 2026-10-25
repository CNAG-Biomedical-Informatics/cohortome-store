# Contributor templates

The canonical package schemas and validator are maintained in COHORTome under
`app/dataset_schemas/` and `app/dataset_validation.py`. This layout is guidance,
not a separate format specification.

The existing application layout provides the starting point:

```text
dataset/
  manifest.json
  clinical/
    records.json
  assays/                          Optional for clinical-only packages
    manifest.json
    transcriptomics/
      counts.csv
      sample_metadata.tsv
  identifiers/                     Optional
    clarid_subjects.csv
```

For a complete runnable starting point, use the
[minimal dataset example](../examples/minimal-dataset/README.md). Follow the
[preparation guide](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/prepare-datasets)
and [review checklist](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/dataset-review-checklist).
ZIP import also requires `resource.json` inside the dataset root. Document
provenance, licensing, checksums and explicit linkage; do not copy or extend the
canonical schemas here.
