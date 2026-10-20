# GSE65391 — pediatric SLE microarrays

**On hold. The existing `0.1.0-preview` is not an approved analysis dataset.**

## Source and provenance

- [GEO GSE65391](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE65391)
- [Original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC5426482/)
- Input: `ed-GSE65391_series_matrix.txt.gz`, downloaded for ED-Omics.
- Reader: ED-Omics `ed_omics.public_data.series_metadata`.
- Adapter: `scripts/prepare_gse65391.py`.

The input contains 996 arrays: 924 labelled SLE and 72 labelled Healthy.
Published expression values are already processed. The adapter preserves their
decimal values and probe identifiers, without normalization or probe filtering.
Input and output-file checksums are in the preview's `resource.json`.

## Unresolved replicate issue

The first adapter selected SLE records with `batch_replicate=FALSE`. This retained
900 samples from 158 patients and excluded 24 flagged SLE records and all 72
Healthy records. That selection was premature.

GEO describes 24 healthy technical replicates used for batch adjustment. The
downloaded metadata flags 24 SLE records as well as 24 healthy records. A flag
alone does not establish which records represent the same biological specimen.
The source SLE records had no duplicate subject/visit pairs in the initial audit.

Before preparing a replacement, reconcile the metadata with the study methods
and actual sample relationships. Document whether samples are retained,
combined, or excluded, and why. Never treat technical replicates as independent
participants or combine distinct longitudinal visits.

The provisional archive contains 43,799 probe rows, SLEDAI as a clinical
measurement, and the other source metadata. Structural validation passed, but
this does not resolve the selection issue. No catalogue release is approved.

## Limits

These are microarray values, not RNA-seq counts. Calendar dates are unavailable;
relative days and age at visit are retained without inventing dates of birth.
The adapter does not map the other laboratory fields to clinical measurements
because their units and definitions still need review. No app ingestion or
analysis compatibility test has been completed.

## Access and redistribution

The GEO matrix was downloaded without an access application. Dataset-specific
redistribution terms have not been confirmed. Review date: 20 October 2026.
No data licence is assigned here. The original article's licence is not taken
as permission to redistribute the matrix. Do not publish this preview.
