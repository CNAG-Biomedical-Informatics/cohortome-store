# IBDMDB processed multi-omics

## Subject ClarIDs

All 112 subjects have human and stub ClarIDs using clarid-tools/codebook 0.04.
Original patient identifiers remain `unique_id`. Numeric subject identifiers
are assigned once; supply the previous sidecar with `--previous` on later
generation runs to preserve those numbers. Age is `Not Available`: no age at
an observation is inferred from age at consent.

CD maps to K50.9, UC to K51.9, and non-IBD controls to Z00.00, following the
[ClarID FAQ convention](https://cnag-biomedical-informatics.github.io/clarid-tools/help/faq)
when no specific disease is available. This is an identifier convention,
not a claim that non-IBD participants are healthy. The original comparison
group is preserved; Z00.00 is not added to BFF clinical diagnoses.
The package includes the local IBDMDB codebook extension. Both identifier
formats are decoded and checked against their input fields before packaging.

Generate the sidecar after clinical conversion, then pass its directory to
`prepare_ibdmdb.py --clarid-directory PATH`:

```bash
python scripts/build_ibdmdb_clarids.py \
  --clinical PATH/individuals.json --output PATH/identifiers \
  --clarid-tools /path/to/clarid-tools/bin/clarid-tools \
  --codebook /path/to/clarid-tools/share/versions/0.04/clarid-codebook.yaml
```

## Clinical enrichment (unreleased 0.1)

This version uses Convert-Pheno 0.35 to map sex, CD/UC diagnoses, CRP and ESR.
The 1,206 metadata rows for the three included modalities form 898 snapshots
using exact participant, source visit and study week. No conflicting nonempty
values occurred for those mapped fields within these groups.
Separate stool and serum sample links remain explicit.
The COHORTome snapshot identifier is stored as `info.visit_id`, not a
top-level BFF field. Assay sample tables retain their `visit_id` linkage column.

There are 224 structured measurements (112 CRP and 112 ESR), supplied by the
serology metadata. Not every participant or timepoint has either measurement.
Other nonempty source columns, including disease activity scores and
calprotectin, are retained under `info.source_metadata`; they are not yet
harmonized BFF measurements. No baseline values are carried into later visits.

Converter-generated placeholder dates, age of onset, severity, stage and
reference ranges are omitted because the mapping supplied none.
BFF Tools 2.0.14.dev0 validated all 898 enriched clinical objects successfully.
The package retains the mapping and aggregate mapping audit under `provenance/`.
This is structural and conversion validation, not scientific validation.

Private preview prepared from public HMP2 processed products. Not publicly released.
Registration, clinical-store preparation, assay linkage, dashboard views,
relative-time display, cohort saving and exports have been checked in an isolated
COHORTome runtime. Scientific analysis has not yet been verified.

The 57-participant three-modality cohort exported 562 clinical records and
298 metabolomics, 295 metaproteomics and 173 serology sample columns. All exported
matrix values matched the selected source values. These are software checks,
not validation of a biological result.

The private 0.1 preview is refreshed during development. The current checksum
in `catalog/ibdmdb-0.1.0-preview.json` identifies the enriched package; older
downloads with the same filename should not be reused.

The [IBDMDB study](https://doi.org/10.1038/s41586-019-1237-9) followed participants
with Crohn disease, ulcerative colitis and a non-IBD comparison group.
This resource contains stool metabolomics, stool metaproteomics and serum
antibody assays. It does not contain raw sequencing or instrument files.

## Contents and conversion

- Metabolomics: 546 samples, 81,867 features. All features are retained, including
  those without metabolite names. Original BIOM annotations are included;
  the separate 2021 annotation update has not been applied.
- Metaproteomics: 450 samples, 11,284 features from the published
  `2pep-pro_1p_FDR_5ppm` table. This is not a human protein panel.
- Serology: 210 linked samples and five numeric ELISA assays: IgA ASCA,
  IgG ASCA, OmpC, Cbir1 and ANCA.

Values are not normalized, filtered by biological quality, or averaged.
Omitted sparse BIOM entries become zero, as specified by the
[BIOM 1.0 format](https://biom-format.org/documentation/format_versions/biom-1.0.html).
This is not evidence that a molecule is biologically absent.

Sample links use exact identifiers within each modality. Shared stool specimens
keep the same identifier. Serum and stool specimens remain separate, even when
collected from the same participant in the same week. Clinical snapshots record
source visits and relative weeks; they are not necessarily distinct clinic appointments.
Calendar dates and additional clinical measurements are not inferred.

One populated serology column (`220948`) has no match in the published serology
metadata. It is excluded from the linked matrix and listed in `exclusions.json`.
The complete source serology table, including categorical results and that
column, is retained as `assays/serology_source.tsv`. No participant was guessed.

At participant level, 57 people have all three modalities. There are no specimens
shared across all three. Metabolomics and metaproteomics share 308 specimens.
A participant-level overlap therefore does not establish matched measurements
at every visit.

## Sources and use terms

Inputs come from the [IBDMDB download catalogue](https://ibdmdb.org/results):
the 2018-08-20 metadata release, metabolomics BIOM, the 2017-03-20 proteomics
release and the 2017-10-05 serology release. The repository's `AUDIT.md` and
`audit.json` record the exact URLs and source checksums. The package's
`resource.json` records input and output checksums and conversion limitations.

The [iHMP consortium report](https://pmc.ncbi.nlm.nih.gov/articles/PMC6784865/)
and [HMPDACC report](https://pmc.ncbi.nlm.nih.gov/articles/PMC7778886/)
describe unrestricted use of DCC data. This is the reuse basis for these public
processed products; no CC0 or other named dataset-wide licence is asserted.
Controlled human sequence data and protected metadata are not included.
Before publishing the downloadable archive, check the scope of those statements
against these exact products. Cite the original study and retain provenance.
The software repository's licence does not replace source-data terms.

## Rebuild

From the COHORTome checkout, with its Python dependencies installed:

```bash
PYTHONPATH=.deps:. python3 ../cohortome-store/scripts/build_ibdmdb_clinical.py \
  --source ../cohortome-store/downloads/ibdmdb/ibdmdb-metadata.csv \
  --output /tmp/ibdmdb-clinical \
  --convert-pheno /path/to/convert-pheno/bin/convert-pheno \
  --mapping ../cohortome-store/datasets/ibdmdb/clinical.yaml
PYTHONPATH=.deps:. python3 ../cohortome-store/scripts/build_ibdmdb_clarids.py \
  --clinical /tmp/ibdmdb-clinical/individuals.json \
  --output /tmp/ibdmdb-identifiers \
  --clarid-tools /path/to/clarid-tools/bin/clarid-tools \
  --codebook /path/to/clarid-tools/share/versions/0.04/clarid-codebook.yaml
PYTHONPATH=.deps:. python3 ../cohortome-store/scripts/prepare_ibdmdb.py \
  --source ../cohortome-store/downloads/ibdmdb \
  --cohortome . --version 0.1.0-preview \
  --clinical-records /tmp/ibdmdb-clinical/individuals.json \
  --clarid-directory /tmp/ibdmdb-identifiers
```

The builder refuses to overwrite an existing version. It validates the package
with COHORTome's dataset validator before creating the archive. This structural
check does not validate biological conclusions or every analysis method.
