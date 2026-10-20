# GSE42296 — infliximab in Crohn disease and rheumatoid arthritis

Local preview `0.1.0-preview`; not published or cleared for redistribution.
The full ED-Omics source export contains 20 Crohn disease and 19 rheumatoid
arthritis patients, each sampled at weeks 0 and 2: 78 samples, 33,297 probes.

[GEO source](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE42296).
Unlike the Crohn-only ED benchmark, this resource retains both disease groups.
The adapter rejects duplicate or incomplete patient/visit pairs rather than
silently removing them. It aligns matrix rows by GEO accession, not position.

## Prepare and verify

With COHORTome dependencies installed, from this repository:

```bash
python scripts/prepare_gse42296.py --cohortome ../cohortome \
  --source /path/to/ed-omics/data/public/GSE42296 --version 0.1.0-preview
python scripts/verify_resource.py catalog/gse42296-0.1.0-preview.json \
  dist/gse42296-0.1.0-preview/gse42296-0.1.0-preview.zip
```

Inputs are `metadata.tsv` and `expression.npz`, created by ED-Omics'
`ed_omics.remission_data.prepare_gse42296` from the full GEO SOFT record.
Their SHA-256 checksums are recorded inside `resource.json`. The original
SOFT is not required at packaging time. The existing intermediate stores
expression as float32; exported values preserve that precision, not the
original textual decimal representation. No further filtering or normalization
is applied. Gene-annotation files and ED-derived coordinates are not included.

## Analysis limits

These are processed microarray measurements, not RNA-seq counts. Do not use
voom or DESeq2. Paired analyses must account for the same patient at both visits.
Response labels are retained with their source wording; do not assume identical
clinical response definitions between diseases. Calendar dates, demographics,
dosages and clinical scores are not inferred. Only relative visit timing is
available. Probe IDs are retained; no probe-to-gene collapsing is performed.

Disease namespaces are source-specific, not curated ontology mappings.
Registration, app analysis compatibility and redistribution review remain
pending. Structural validation is not a biological or end-to-end app validation.

## Provenance and redistribution review

Review date: 20 October 2026. The GEO record provides public processed data and
describes the study's two disease groups. No dataset-specific redistribution
licence has been established for this package. No blanket data licence is
assigned here; publication is on hold until the applicable terms are recorded.

ED-Omics recorded upstream SOFT SHA-256
`0d66d7ecbfcf0b398c3f7e4a207d3ca64d4e002a433726074bbab38cb2a68985`.
That checksum is historical provenance: the original SOFT was not present during
this conversion and was not independently rehashed. The intermediate metadata
and expression checksums were computed directly and are in `resource.json`.

The adapter applies no sample exclusions to these inputs. Both visits from both
disease groups are retained. Validation found 39 patients, 78 sample columns,
33,297 probe rows, no missing expression values and no linkage warnings.
Three synthetic tests cover matrix alignment, disease-scoped patient IDs,
duplicate visits and incomplete pairs.
