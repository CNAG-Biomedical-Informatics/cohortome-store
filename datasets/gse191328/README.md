# GSE191328 — longitudinal IBD blood RNA-seq

Local preview: `0.1.0-preview`. Not cleared for redistribution or published.

The package contains 201 sample-linked clinical records for 53 patients and an
unfiltered 58,051-gene integer-count matrix. It retains the original GEO sample
and patient identifiers alongside COHORTome-compatible identifiers. Validation
reports no missing count values or linkage warnings.

Sources: [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE191328)
and the [original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9509553/).
The ED-Omics `ed_omics.public_data` reader is reused; its transformed log-CPM
outputs and analysis-specific patient exclusions are not used.

## Prepare

Run from this repository with Python 3.11+ and the COHORTome and ED-Omics Python
dependencies installed. Inputs are the original GEO series matrix and 201
downloaded featureCounts files under `counts/` (or the complete RAW tar).

```bash
python scripts/prepare_gse191328.py \
  --cohortome ../cohortome \
  --ed-omics /path/to/ed-omics \
  --source /path/to/ed-omics/data/public/GSE191328 \
  --version 0.1.0-preview

python scripts/verify_resource.py \
  catalog/gse191328-0.1.0-preview.json \
  dist/gse191328-0.1.0-preview/gse191328-0.1.0-preview.zip
```

Existing output versions are never overwritten. The output directory includes
the unpacked `gse191328/` package, ZIP and `release.json`. The reviewed catalogue
manifest is the checksum reference; a checksum distributed beside an archive
alone is not the trust anchor. No particular application commit is required.
The script does not register datasets, build DuckDB stores or publish files.

## Interpretation and limitations

- Keep repeated samples linked to their patient. Do not run an unpaired
  comparison treating all visits as independent participants.
- Preserve treatment, study cohort, diagnosis, visit label and elapsed days.
  No normalization, expression filtering or batch correction is applied.
- Week-14 remission is retained as a named future endpoint, not a repeated
  clinical measurement at each RNA sampling visit.
- Age, sex, calendar dates and quantitative clinical measurements are not
  available in these input metadata and are not invented. Relative sampling
  times are present. COHORTome now supports a separate study-day timeline;
  this resource's display has not yet been checked in the app.
- Treatment labels describe study groups, not dated dosing records. Disease
  codes use a source namespace; ontology mapping remains a separate task.
- ClarIDs and clinical outcomes from paper supplements are not added in this
  first package. Original Ensembl gene IDs are preserved without annotation joins.

Before distribution, review source-specific reuse terms and attribution. Public
download availability and the article licence alone do not settle every input's
redistribution terms. The live GEO and PMC pages were blocked by browser checks
during this preparation; licence review therefore remains pending.

Before exposing this resource to users, test registration, count ingestion and
a patient-aware analysis in the app. Structural validation is not that test.

## Redistribution status

Review date: 20 October 2026. The public GEO metadata and count files are the
inputs, not restricted cohort data. Dataset-specific redistribution terms remain
unconfirmed; no data licence is assigned by this repository. Do not publish the
archive until the terms and required attribution are recorded.

The adapter makes no patient, visit or gene exclusions. Source-file checksums
are stored in `resource.json`; the reviewed archive checksum is in
`catalog/gse191328-0.1.0-preview.json`. Structural validation found no missing
count values. Unknown clinical fields remain absent rather than imputed.
