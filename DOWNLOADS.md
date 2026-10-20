# Private preview downloads

These are individual dataset packages, not application installers. GitHub access
to this private repository is required. Public redistribution remains a separate
review. No GitHub Actions build is involved in uploading these archives.

| Dataset | Release tag | Archive size |
| --- | --- | --- |
| Default synthetic | `default-0.1.1-preview` | 0.87 MB |
| Synthetic autoimmune demo | `synthetic-autoimmune-demo-0.1.1-preview` | 1.28 MB |
| IBDMDB processed multi-omics | `ibdmdb-0.1.0-preview` | 87.88 MB |

From this repository, with GitHub CLI authenticated:

```bash
gh release download default-0.1.1-preview --repo CNAG-Biomedical-Informatics/cohortome-store --pattern '*.zip' --dir downloads/releases
python3 scripts/verify_resource.py catalog/default-0.1.1-preview.json downloads/releases/default-0.1.1-preview.zip
gh release download synthetic-autoimmune-demo-0.1.1-preview --repo CNAG-Biomedical-Informatics/cohortome-store --pattern '*.zip' --dir downloads/releases
python3 scripts/verify_resource.py catalog/synthetic-autoimmune-demo-0.1.1-preview.json downloads/releases/synthetic-autoimmune-demo-0.1.1-preview.zip
gh release download ibdmdb-0.1.0-preview --repo CNAG-Biomedical-Informatics/cohortome-store --pattern '*.zip' --dir downloads/releases
python3 scripts/verify_resource.py catalog/ibdmdb-0.1.0-preview.json downloads/releases/ibdmdb-0.1.0-preview.zip
```

Each ZIP contains one dataset root with clinical records, assay manifests and
matrices, plus resource metadata. It contains no DuckDB store, user state or
deployment permissions. The receiving app must validate and prepare its own
store and apply its own access and AI policies.

Downloading directly from the app is the next implementation step; these commands
do not register or activate a dataset. IBDMDB is the first real-data import-test
candidate. Its local app checks passed, but this does not validate a scientific
analysis or resolve the public redistribution review.

Never put tokens in catalogue URLs or commit downloaded archives. Do not replace
a release archive in place: changed content needs a new version and checksum.
