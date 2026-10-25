# COHORTome Store

A curated collection of datasets ready to use in COHORTome.

Preparation recipes and catalogue metadata for installable COHORTome dataset
packages. The COHORTome application and its dataset schemas/validator remain in
the separate `cohortome` repository.

## Start here

- **Prepare your own data:** [preparation guide](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/prepare-datasets),
  [package reference](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/dataset-packages)
  and [review checklist](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/dataset-review-checklist).
- **Try the complete process:** [minimal worked example](examples/minimal-dataset/README.md),
  from invented clinical CSVs through Convert-Pheno to a validated importable ZIP.
- **Reproduce a study:** [dataset index](DATASETS.md), then its README, mapping,
  preparation script and source-specific licensing notes.
- **Install data:** [application instructions](https://cnag-biomedical-informatics.github.io/cohortome/docs/user-guide/install-datasets).
  Reviewed studies can be fetched and prepared locally by recipes shipped in
  COHORTome. Adding a Store script does not enable a new in-app recipe.

There is one documentation site, maintained in COHORTome. Store holds the
dataset-specific inputs, mappings and recipes. Coding agents should follow the
same reading order; do not guess units, clinical meanings, linkage or replicate
handling. Record unresolved decisions before preparing a study.

The private preview catalogue also contains early synthetic and IBDMDB ZIPs.
See [preview downloads](DOWNLOADS.md) for their status and legacy identifiers;
these are not the source of every dataset in the current app catalogue.

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
  examples/minimal-dataset/         Runnable CSV-to-package tutorial
  templates/                       Links to the canonical package guidance
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

The `default` and `synthetic-autoimmune-demo` folders/catalogue entries are
historical preview names. The app now calls its included examples **Synthetic
longitudinal demo** and **Synthetic cross-sectional demo**. Older preparation
scripts may refer to pre-release source layouts; check the chosen source revision
before rerunning them. The new tutorial does not depend on those fixture paths.

No blanket data licence is assigned by this collection. Redistribution terms must
be established per package, including third-party annotations or imaging assets.
