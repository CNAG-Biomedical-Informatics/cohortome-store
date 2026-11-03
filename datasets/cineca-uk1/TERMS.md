# Sources, attribution and reuse

This package combines sources with separate terms. It is not a new blanket
licence for those sources. Reviewed 3 November 2026.

| Component | Source and terms |
| --- | --- |
| Synthetic clinical records and biosamples | [CINECA UK1, EGAD00001006673](https://ega-archive.org/datasets/EGAD00001006673). The source declares CC-BY without specifying its version. Preserve the source preamble and acknowledge CINECA, EC H2020 grant 825775. |
| Chromosome 22 genotypes | 1000 Genomes Phase 3, as supplied with CINECA. [IGSR terms](https://www.internationalgenome.org/IGSR_disclaimer/) state the project data are available without embargo; retain attribution and applicable source terms. Cite the 1000 Genomes Project Consortium, Nature 526, 68–74 (2015), doi:10.1038/nature15393. |
| GEUVADIS expression | [David Laub's archived copy](https://doi.org/10.5281/zenodo.15596289), licensed [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cite Laub (2025) and Lappalainen et al., Nature 501, 506–511 (2013), doi:10.1038/nature12531. |
| ClinVar annotations | ClinVar snapshot 20250312, supplied in the annotated VCF. [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) is a public archive. Retain ClinVar attribution and consult its [data-use policy](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/); no endorsement or independent ACMG assessment is implied. |
| Consequence annotations | Supplied SnpEff ANN output. Cite Cingolani et al., Fly 6, 80–92 (2012), doi:10.4161/fly.19695. Tool version and reference are retained in provenance. |

Changes made: linked records by explicit identifiers, retained 445 matching
GEUVADIS individuals, selected 44 chromosome 22 variants, and converted tables
into the COHORTome package format. Expression values were not renormalized.
The supplied clinical BFF and biosamples were copied unchanged.

The EGA description covers 2,521 source samples; this supplied BFF/Phase 3
subset contains 2,504 individuals. We do not imply that these are the complete
EGA collection. The original preamble is retained in provenance/source-README.md.

Clinical attributes are synthetic. Genotypes and expression are measured data;
their combination with fictional clinical traits must not be used for biological
association claims. ClinVar annotations are not patient diagnoses. This is a
software demonstration, not a diagnostic resource. No COSMIC/dbNSFP annotations,
raw sequencing reads or whole-genome VCFs are redistributed.
