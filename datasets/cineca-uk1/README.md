# CINECA UK1 + GEUVADIS demo

**Prepared package:** 2,504 clinical individuals, 2,504 supplied biosamples plus
445 GEUVADIS analytical sample records, GEUVADIS
expression for 445 individuals (23,722 genes), and a 44-variant chromosome 22
panel across 2,504 DNA samples. In COHORTome, select **Add dataset → Ready to
install**. Use the current source app with variant-browser support; the released
0.1.0 app does not include that interface.

Clinical attributes are synthetic; molecular measurements are not. See
[sources, attribution and reuse](TERMS.md).

Source: CINECA Synthetic Cohort EUROPE UK1,
[EGAD00001006673](https://ega-archive.org/datasets/EGAD00001006673), prepared as
Beacon BFF by beacon2-cbi-tools. Clinical attributes are synthetic and intended
for software testing, not biological association analysis.

| Input | Handling |
| --- | --- |
| `bff/individuals.json` | Copied unchanged to `clinical/individuals.json` |
| `bff/biosamples.json` | Copied unchanged, declared separately in the manifest |
| Source README | Preserved with its attribution and dataset description |

The supplied collection has 2,504 individuals and 2,504 biosamples. Their IDs
match, but the explicit `individualId` establishes the relationship. All
biosamples describe blood. This does not establish that a later RNA-seq assay
used the same specimen. No tissue, visit or age is inferred.

The basic package contains no molecular data. The optional preparation steps
below add measured GEUVADIS expression or prepare a separate variant panel.
The optional ClarID step below adds subject and biosample labels. Molecular
measurements are not synthetic.

## Prepare

From Store, with the COHORTome Python dependencies available:

```bash
PYTHONPATH=../cohortome/.deps:../cohortome python3 scripts/prepare_cineca_uk1.py \
  --source /path/to/CINECA_synthetic_cohort_EUROPE_UK1 \
  --cohortome ../cohortome \
  --output build/cineca-uk1-local
```

Choose a new output directory each time. The recipe validates identifiers and
links, records source/package checksums and creates a local ZIP. Existing BFF
needs no CSV conversion or VCF processing. Use COHORTome source with biosample
support; released 0.1.0 lacks that view.

## Prepare the chr22 panel

`scripts/prepare_cineca_variants.py` reads the annotated CINECA GRCh37/hs37d5
VCF once. It selects chr22 PASS variants with exact `CLINVAR_CLNSIG` values
`Pathogenic`, `Likely_pathogenic` or `Pathogenic/Likely_pathogenic`: **44 variants**
in this source. This is a demonstration panel, not a clinical diagnostic filter.

```bash
python3 scripts/prepare_cineca_variants.py \
  --vcf /path/to/annotated-chr22.vcf.gz \
  --package build/cineca-uk1-local/cineca-uk1-demo \
  --clinvar-version 20250312 \
  --output build/cineca-uk1-chr22-plp
```

| Output | Contents |
| --- | --- |
| `variants.tsv` | Assembly, 1-based VCF coordinates, alleles, original ClinVar classification/condition/review fields and SnpEff ANN |
| `genotypes.tsv.gz` | Compressed complete variant × sample grid, including reference and missing calls; original GT and phase retained |
| `samples.tsv` | Explicit patient and biosample links |
| `preparation.json` | Selection, annotation snapshot, checksums and aggregate counts |

Classifications and review status are kept as supplied, including punctuation.
No independent ACMG assessment is computed. Missing/partial calls have no dosage;
they are not coded as reference. VCF filter status is retained, but these inputs
have no sample DP/GQ to establish per-call confidence. Selected classifications
are retained verbatim; excluded classifications are counted in the preparation
report. No COSMIC/dbNSFP annotations are exported.

To keep the demo manageable, it includes 44 ClinVar pathogenic/likely pathogenic
variants across 2,504 samples.

These tables are imported through the optional variant-panel manifest, separately
from expression matrices. They must not be passed to an expression analysis or
interpreted as diagnoses for the synthetic patients.

## GEUVADIS expression

`scripts/prepare_cineca_expression.py` adds the processed GD462 gene-expression
matrix from [Zenodo record 15596289](https://zenodo.org/records/15596289), a copy
of the GEUVADIS product. Its published MD5 is checked before conversion.
The original [GEUVADIS README](http://ftp.ebi.ac.uk/pub/databases/microarray/data/experiment/GEUV/E-GEUV-1/analysis_results/GeuvadisRNASeqAnalysisFiles_README.txt)
describes filtering and PEER normalization. Values include negatives: **these
are not raw counts or unadjusted RPKM**. Do not use count-based differential
expression. No additional normalization or imputation is performed.

Of 462 unique individuals, **445 match CINECA UK1**. The other 17 are excluded
and recorded in provenance; no patients are invented to fill the gap. All
2,504 clinical patients remain in the package. RNA samples are lymphoblastoid
cell lines, linked by individual ID, not asserted to be the supplied blood
biosamples. Gene IDs retain their source versions.

```bash
PYTHONPATH=../cohortome/.deps:../cohortome python3 scripts/prepare_cineca_expression.py \
  --expression downloads/geuvadis/GD462.GeneQuantRPKM.50FN.samplename.resk10.txt.gz \
  --source-readme downloads/geuvadis/GeuvadisRNASeqAnalysisFiles_README.txt \
  --package build/cineca-uk1-local/cineca-uk1-demo \
  --cohortome ../cohortome \
  --output build/cineca-uk1-with-expression
```

This creates a new validated package directory without changing the clinical-only
input. It does not incorporate the variant intermediate or publish an archive.
Zenodo declares CC-BY-4.0. Cite Lappalainen et al., Nature (2013),
[doi:10.1038/nature12531](https://doi.org/10.1038/nature12531), and the archived
copy. Synthetic clinical attributes remain unsuitable for biological claims.

## Assemble and package

```bash
PYTHONPATH=../cohortome/.deps:../cohortome python3 scripts/assemble_cineca_panel.py \
  --package build/cineca-uk1-with-expression --panel build/cineca-uk1-chr22-plp \
  --cohortome ../cohortome --output build/cineca-uk1-browser
PYTHONPATH=../cohortome/.deps:../cohortome python3 scripts/package_cineca_release.py \
  --package build/cineca-uk1-browser --cohortome ../cohortome \
  --output dist/cineca-uk1-demo-0.1.0
```

The release includes original source notices, preparation provenance, file
checksums and [component-specific terms](TERMS.md). No raw VCF is included.
Annotations are supplied ClinVar/SnpEff results, not an independent ACMG assessment.

## Add ClarID labels

Use ClarID-Tools **0.05**, its GitHub checkout (for `utils/bff`), and a COHORTome
checkout with biosample ClarID support. Clinical JSON remains unchanged;
biosamples gain assay provenance and separate GEUVADIS analytical records.

```bash
PYTHONPATH=../cohortome/.deps:../cohortome python3 scripts/prepare_cineca_clarids.py \
  --package build/cineca-uk1-browser --output build/cineca-uk1-clarids \
  --cohortome ../cohortome --clarid-checkout /path/to/clarid-tools \
  --executable /path/to/clarid-tools/bin/clarid-tools
```

| Field | Mapping |
| --- | --- |
| Subject number | Original HG/NA numeric suffix, reused for biosamples (`HG00096` → `96`); collisions are rejected |
| Study/project | Local `CINECA-UK1` entry in the packaged codebook 0.04 |
| Condition | First listed synthetic ICD-10 code, **not** a primary diagnosis; `F3181` becomes `F31.81` |
| No recorded condition | `R69` placeholder, not a new diagnosis or a claim of health |
| Sex, species, tissue | Supplied sex, taxon 9606 and supplied blood term; RNA tissue stays unavailable |
| Assay | WGS for 2,504 DNA samples; RNA-seq for 445 GEUVADIS samples |
| Other fields | Not Available; missing duration is `P0N`, not zero |

All diagnoses remain in BFF. Case/control status, age and normal tissue
are not inferred. GEUVADIS RNA records represent analytical samples, not the
supplied blood specimens. WGS assignment follows prepared analytical links;
matching subject/sample IDs alone do not prove physical specimen identity.
Different specimens may share a ClarID; original IDs remain their identities.
Both label formats are decoded for verification. Mapping files, local codebook
and preparation provenance are included in the new package.

Pass `build/cineca-uk1-clarids` to `package_cineca_release.py --package` to make
a new archive. Uploading and updating the catalogue are separate steps.
