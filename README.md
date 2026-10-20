# COHORTome Store

A curated collection of datasets ready to use in COHORTome.

Preparation recipes and catalogue metadata for installable COHORTome dataset
packages. The COHORTome application and its dataset schemas/validator remain in
the separate `cohortome` repository.

Private GitHub prereleases now provide the two bundled synthetic datasets
(0.1.1-preview) and processed IBDMDB data (0.1.0-preview).
COHORTome supports catalogue downloads and local ZIP imports. No Zenodo record
has been created yet.
See [download instructions](DOWNLOADS.md) and the versioned catalogue.

Repository: `CNAG-Biomedical-Informatics/cohortome-store` (private during
development). Git contains recipes, documentation and versioned checksum
manifests, not dataset archives. Reviewed archives can be attached to versioned
GitHub releases for initial download testing; private assets require GitHub
access. Public distribution and Zenodo deposits remain separate steps, subject
to each dataset's terms. Never put access tokens in catalogue URLs.

See [dataset status and documentation](DATASETS.md) for provenance, preparation
decisions, unresolved issues and redistribution status.

## Layout

```text
cohortome-store/
  catalog/                         Dataset catalogue and release metadata
  datasets/
    default/                       Bundled synthetic longitudinal example
    synthetic-autoimmune-demo/     Bundled synthetic multimodal example
    private-dataset/               Synthetic access-control fixture
    dataset-large/                 Synthetic transcriptomics timing fixture
    gse191328/                     Candidate public IBD study
  templates/                       Contributor package guidance
  scripts/                         Shared validation/packaging commands
```

Each dataset directory holds its preparation recipe and documentation, not a
second manually maintained copy of the data. The existing synthetic files and
generators remain in COHORTome. Resource versions are independent of app commits.
The synthetic packager reads committed fixtures (HEAD by default) to avoid
including untracked runtime files; this is not an installation requirement.
The explicit `--worktree` option packages current contents of those same tracked,
allowlisted files. The synthetic 0.1.1 previews use this option to include the
shortened ClarIDs. Each package records file checksums and its source mode.

Generated public downloads, prepared packages and archives will use ignored
`downloads/`, `build/` and `dist/` directories. Create these when needed.
Restricted source data and derivatives must never be placed in this repository,
including its ignored directories.

## Package policy

- Bundled examples and optional downloads must follow the same versioned package
  contract and pass the same validator. Bundling changes delivery, not format.
- Validate portable source files before registration and DuckDB preparation.
  DuckDB databases, user state, credentials and deployment access policies are
  not distributed in dataset packages.
- Declare the package schema version supported by COHORTome. Do not maintain a
  separate schema implementation here.
- Keep a reproducible recipe, source citations, preprocessing description,
  redistribution terms and checksums for each released package.
- Validation checks structure and linkage, not scientific validity. A valid
  package does not imply that every analysis is suitable for its measurements.
- Publish reviewed archives separately from Git, with versioned Zenodo records
  as the intended distribution location. The catalogue will reference exact
  versions and checksums, not mutable "latest" downloads.

## Next steps

1. Validate packages with the existing COHORTome schema and validator.
2. Review the prepared GSE191328 preview and its redistribution terms.
3. Complete the synthetic resource catalogue.
4. Check each refreshed package in COHORTome before wider distribution.

No blanket data licence is assigned by this scaffold. Redistribution terms must
be established per package, including third-party annotations or imaging assets.
