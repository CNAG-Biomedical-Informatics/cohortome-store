# Resource preparation and packaging

New contributors: read the
[preparation guide](https://cnag-biomedical-informatics.github.io/cohortome/docs/admin-guide/prepare-datasets)
and run the [minimal example](../examples/minimal-dataset/README.md) first.

Implemented commands:

- `build_synthetic.py`: package older bundled synthetic fixtures; its source paths
  predate the current app layout. Use a compatible historical revision for those
  previews, not this script as the current onboarding example.
- `prepare_gse191328.py`: assemble original public IBD count files and metadata.
- `prepare_gse42296.py`: convert the ED-Omics Crohn/RA microarray export.
- `prepare_gse65391.py`: provisional SLE adapter; on hold pending replicate review.
- `audit_ibdmdb.py`: audit public processed sample linkage and report aggregates.
- `prepare_ibdmdb.py`: package processed IBDMDB matrices and linked clinical records.
- `verify_resource.py MANIFEST ARCHIVE`: verify against a repository catalogue entry.

See each dataset README for inputs, commands, limitations and redistribution status.
These scripts are not dynamically downloaded or executed by COHORTome. The app
has its own shipped, reviewed fetch-and-build recipes; this documentation does
not change them.

The intended workflow is:

1. Identify reviewed inputs and record their checksums.
2. Prepare portable clinical/assay files in `build/`.
3. Validate using COHORTome's package validator, without creating a live
   application registration or modifying its runtime.
4. Build a reproducible archive in `dist/` and calculate its checksum.
5. Review the archive contents before publishing and updating the catalogue.

Packaging must exclude credentials, user state, DuckDB caches and unrelated
files. Source conversion belongs in the relevant dataset recipe; shared scripts
should not accumulate study-specific interpretation rules.
