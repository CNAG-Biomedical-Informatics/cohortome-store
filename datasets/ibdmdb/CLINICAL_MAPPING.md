# IBDMDB clinical mapping

## Integrated private 0.1 preview

20 October 2026. The package now uses `clinical.yaml` and
`scripts/build_ibdmdb_clinical.py`: 1,206 source modality rows form 898 snapshots
by exact participant, source visit and relative week. Sex, diagnoses and 224
CRP/ESR measurements are mapped; other source fields remain in
`info.source_metadata`. Snapshot linkage is `info.visit_id`. Placeholder dates,
onset, severity and reference ranges are removed. BFF validation passed for all
898 objects. Subject ClarIDs are separate from clinical diagnoses.

The findings below describe the earlier all-row pilot. Its 5,533 records and
placeholder warnings are not the contents of the refreshed import package.

## Result

Convert-Pheno 0.35 converted all 5,533 source rows with 490 source columns.
The pilot maps sex, CD/UC diagnoses, CRP and ESR. Original columns remain under
`info.CSV_columns`; preserving a column there does not make it a structured
clinical variable or an appropriate Pheno-Ranker input.

- 5,533 distinct output IDs and retained source rows.
- 4,188 records with CD or UC; non-IBD is not mapped as a disease.
- 1,338 measurements: 669 CRP and 669 ESR values.
- Terminology audit: 11,728 matched decisions, 669 configured UCUM unit
  decisions, no fallbacks.
- NCIT labels checked against Convert-Pheno's bundled SQLite database:
  Female C16576, Male C20197, Crohn Disease C2965, Ulcerative Colitis C2952,
  C-Reactive Protein Measurement C64548, Erythrocyte Sedimentation Rate
  Measurement C74611 and Millimeter per Hour C67419.
- CRP uses UCUM mg/L, explicitly stated in the source column.

## Pilot issues resolved during integration

The pilot intentionally preserves one record per source row. Those rows are
assay/specimen metadata, not distinct clinical visits. There are 2,049
participant/week groups, but week alone is not a safe snapshot key: 203 groups
have different nonempty visit numbers, 30 have different CRP values, 35 different
ESR values, 64 different HBI values and 29 different SCCAI values.
Do not choose the first row, average values or silently merge these groups.
Review source visit semantics and retain explicit specimen links.

The mapping uses `records: {}`: no `_visit` annotations or baseline propagation.
The final resource must use stable patient IDs and distinct patient/timepoint
records, not the pilot's sequential row IDs.

Convert-Pheno adds a default measurement date of `1900-01-01` and unknown
age-of-onset `P999Y` where this pilot supplies neither. These are converter
placeholders, not observations; remove them before COHORTome ingestion.
Do not infer calendar dates from receipt dates or relative weeks.

BFF Tools 2.0.14.dev0 checked all 5,533 records and reported 4,188
`diseases.0.ageOfOnset` issues (the documented overlapping `oneOf` alternatives).
This was not a clean validation pass. Correct placeholder handling, rerun the
validator and retain its report before release.

Next mapping pass: disease activity, fecal calprotectin, symptoms, medication
status and other clinical fields. Review all 490 columns and document each
structured mapping, source-only preservation or exclusion. Medication history
must not be interpreted as current treatment; age at consent is not visit age.

## Reproduce

From the resources repository, with Convert-Pheno installed:

```bash
python3 scripts/pilot_ibdmdb_clinical.py \
  --source downloads/ibdmdb/ibdmdb-metadata.csv \
  --output /tmp/ibdmdb-clinical-review

convert-pheno \
  -icsv /tmp/ibdmdb-clinical-review/input.csv --separator ',' \
  --mapping-file datasets/ibdmdb/clinical-pilot.yaml --search exact \
  --term-audit /tmp/ibdmdb-clinical-review/terminology.tsv \
  -obff /tmp/ibdmdb-clinical-review/individuals.json

bff-tools validate -i /tmp/ibdmdb-clinical-review/individuals.json -nc -ne
```

Use a new output directory. Do not commit source rows, output BFF or row-level
terminology logs. This pilot does not alter the existing package builder.
