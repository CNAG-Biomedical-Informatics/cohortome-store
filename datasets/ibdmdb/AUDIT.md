# IBDMDB processed-data audit

20 October 2026. No raw sequence or instrument files were downloaded.
This records the source audit before conversion. No normalization, imputation
or replicate collapsing was done. See README.md for subsequent package decisions.

## Inputs and provenance

The official [download catalogue](https://ibdmdb.org/results) links these files.
All four downloads succeeded without login. The local copies are under ignored
`downloads/ibdmdb/`; SHA-256 values and aggregate results are in `audit.json`.

| Local filename | Published file |
| --- | --- |
| `ibdmdb-metadata.csv` | [hmp2_metadata_2018-08-20.csv](https://g-227ca.190ebd.75bc.data.globus.org/ibdmdb/metadata/hmp2_metadata_2018-08-20.csv) |
| `ibdmdb-metabolomics.biom.gz` | [HMP2_metabolomics_w_metadata.biom.gz](https://g-227ca.190ebd.75bc.data.globus.org/ibdmdb/products/HMP2/MBX/HMP2_metabolomics_w_metadata.biom.gz) |
| `ibdmdb-proteomics.tsv.gz` | [HMP2_proteomics_2pep-pro_1p_FDR_5ppm.tsv.gz](https://g-227ca.190ebd.75bc.data.globus.org/ibdmdb/products/HMP2/MPX/2017-03-20/HMP2_proteomics_2pep-pro_1p_FDR_5ppm.tsv.gz) |
| `ibdmdb-serology.tsv` | [hmp2_serology_Compiled_ELISA_Data.tsv](https://g-227ca.190ebd.75bc.data.globus.org/ibdmdb/products/HMP2/Serology/2017-10-05/hmp2_serology_Compiled_ELISA_Data.tsv) |

The proteomics file is one published processing variant, not a filter applied
by COHORTome. Its peptide/FDR criteria and measurement scale require method
review before use. The original study is
[Lloyd-Price et al., Nature, 2019](https://doi.org/10.1038/s41586-019-1237-9).

## Observed coverage

The metadata file has 5,533 rows and 131 distinct participant IDs. This is a
file-level count, not a claim about total study enrollment.

| Product | Matrix columns | Exact metadata matches | Linked participants | Rows |
| --- | ---: | ---: | ---: | ---: |
| Metabolomics | 546 | 546 | 106 | 81,867 features |
| Proteomics | 450 | 450 | 89 | 11,284 features |
| Serology | 211 | 210 | 67 | 14 assay or administrative rows |

Matching used `External ID` within each modality. No duplicate column IDs or
within-modality metadata IDs were found. Matched samples have participant IDs
and week labels. Diagnoses include Crohn disease, ulcerative colitis and non-IBD.

| Combination | Shared participants | Shared external specimen IDs | Shared participant/week labels |
| --- | ---: | ---: | ---: |
| Metabolomics + proteomics | 83 | 308 | 308 |
| Metabolomics + serology | 67 | 0 | 13 |
| Proteomics + serology | 57 | 0 | 12 |
| All three | 57 | 0 | 9 |

The 308 shared metabolomics/proteomics IDs have consistent participant, week and
diagnosis values. Serology is a different specimen type. A shared participant
or week does not establish that measurements came from the same specimen or
collection time. Do not create artificial three-assay matched samples.

## Preparation review at audit time

Subsequent decisions: retain all metabolite features with original annotations;
exclude the one unlinked serology column from linked matrices, retaining it in
the auxiliary source table; use the five numeric ELISA rows. Omitted sparse
BIOM entries are zero by format definition. No nearest-visit matching is applied.

1. **Metabolite features.** Only 592 rows have a nonempty metabolite annotation
   under the audit's explicit missing-label rules. These are not necessarily
   592 unique or confidently identified metabolites. The catalogue also links
   a 2021 annotation update, not yet downloaded or applied. Review it before
   choosing an annotated panel. Keep method-specific feature IDs distinct.
2. **Serology.** One populated sample column has no exact metadata match; it is
   not an empty spreadsheet column. Resolve it or document its exclusion.
   Separate numeric assays from site, plate, sample and categorical result rows.
3. **Missingness.** Inspect the meaning of sparse BIOM entries, zero values and
   detection limits before converting. This audit does not validate matrix values.
4. **Biological origin.** Retain specimen type and host/microbial origin.
   Do not describe stool metaproteomics as a human protein panel.
5. **Analysis scope.** Preserve separate assay samples and visits. Start with
   actual overlap; do not merge visits or apply nearest-time matching implicitly.

## Licensing and distribution

The subsequent use-terms review found unrestricted-use statements in the
[iHMP consortium report](https://pmc.ncbi.nlm.nih.gov/articles/PMC6784865/)
and [HMPDACC report](https://pmc.ncbi.nlm.nih.gov/articles/PMC7778886/).
These support preparation of the public processed products, without asserting
a named CC licence. A final exact-product scope check remains before publication.
Controlled sequence data and protected metadata are excluded. See README.md.

## Reproduce

From cohortome-store, with pandas installed:

```bash
python scripts/audit_ibdmdb.py downloads/ibdmdb --output /tmp/ibdmdb-audit-new.json
```

The script writes aggregate counts and checksums only and refuses to overwrite
an existing report. Full processed inputs stay outside Git.
