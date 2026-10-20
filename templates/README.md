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

The release contract must also specify provenance, licensing, checksums and
explicit linkage requirements. Contributor instructions will reference the
canonical versioned schemas and validator from COHORTome, not copied rules.
