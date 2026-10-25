# Minimal dataset preparation example

Two invented patients, two visits each, four RNA samples and three invented
count features. This example tests conversion, identity and import, not biology
or differential expression. No real study records or source downloads are used.

Start with the [preparation guide](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/prepare-datasets)
and [package reference](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/dataset-packages).
The scripts/mappings in this repository prepare packages; the application's
fetch-and-build recipes are a separate, unchanged installation route.

## Requirements

- Python 3.11+ with COHORTome's dependencies installed.
- A COHORTome source checkout (tested with 0.1.0).
- Convert-Pheno 0.35 and its Perl dependencies, including its terminology data.
  Follow [Convert-Pheno installation](https://github.com/CNAG-Biomedical-Informatics/convert-pheno).

No LLM, R, Redis, ClarID-Tools or running application is needed for preparation.
In an existing COHORTome Python environment, use its Python executable. For a
new environment, from the Store root with sibling `../cohortome`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ../cohortome
```

## Run in order

From the Store repository root, replace the Convert-Pheno path below with the
installed executable. Its required Perl environment must be active.

```bash
.venv/bin/python examples/minimal-dataset/prepare.py \
  --cohortome ../cohortome \
  --convert-pheno /absolute/path/to/convert-pheno \
  --output build/tutorial

.venv/bin/python -m app.dataset_validation build/tutorial/tutorial-longitudinal

.venv/bin/python scripts/verify_resource.py \
  build/tutorial/release.json \
  build/tutorial/tutorial-longitudinal-0.1.0.zip
```

The output must not already exist. To repeat, choose another directory, such as
`build/tutorial-check`, and adjust the validation paths. The script does not
register datasets, alter a workspace or publish anything. `release.json` here
checks the locally built archive; it is not an independent review of that archive.

Open COHORTome → **Admin → Data → Add dataset → Import local package** and select
the ZIP. Once **Ready** appears, add it to the workspace selection and apply.
The app prepares DuckDB automatically. Expect 2 patients, 4 clinical snapshots,
4 linked RNA samples and 3 features. Inspect both visits in Patients/Timeline.
Do not interpret a statistical comparison from this tiny fixture.

## What each input means

| File/columns | Treatment |
| --- | --- |
| `clinical.csv`: `snapshot_id`, `patient_id` | Distinct visit record and stable patient; `T001:V1` resolves to `T001`. |
| `visit_id`, `days_from_baseline` | `info.visit_id` and relative time; no calendar dates inferred. |
| `sex`, `diagnosis` | Convert-Pheno maps to reviewed NCIT terms using `clinical.yaml`. Original values remain in source metadata. |
| `samples.tsv` | Explicit sample/patient/visit links. Assay sample IDs deliberately differ from clinical snapshot IDs. |
| `counts.csv` | Nonnegative integers; copied without normalization or filtering. Feature names are invented, not Ensembl identifiers. |

Repeated visits are not technical replicates or independent participants. The
raw-count importer currently also requires patient prefixes in sample IDs, so
this example uses `T001:RNA1` alongside explicit metadata.

The recipe retains only the converted sex and disease code; unknown-onset or
age defaults from the converter are not imported as observations. This small
allowlist is specific to this example, not a rule to discard mapped fields in
other studies. Additional clinical measurements need their own reviewed mapping.

## Output and provenance

```text
tutorial/
  tutorial-longitudinal/
    manifest.json
    resource.json
    clinical/records.json
    assays/{manifest.json,counts.csv,samples.tsv}
    provenance/                  Inputs, mapping, recipe, terminology audit,
                                 tool/revision metadata and validation report
    README.md
  tutorial-longitudinal-0.1.0.zip
  release.json                   Archive name, version, size and SHA-256
```

No DuckDB database, user state or credentials belong in the ZIP. Original
patient data, licences and access conditions must be reviewed separately when
adapting this example to a real study. Do not copy restricted data into this
repository, even into ignored folders. See the
[review checklist](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/dataset-review-checklist).

## Verification

Checked with COHORTome 0.1.0 and Convert-Pheno 0.35 on 25 October 2026:
conversion, package validation and archive checksums passed. A disposable
runtime completed the actual ZIP import and automatic DuckDB preparation,
retaining 2 patients and 4 visits without changing the active workspace.
This was an importer check, not a statistical evaluation or manual UI review.
