# Dataset status and documentation

Last checked: 20 October 2026.

| Dataset | Prepared contents | Status |
| --- | --- | --- |
| [GSE191328](datasets/gse191328/README.md) | 53 IBD patients, 201 RNA-seq samples, 58,051 genes | Validated local preview; redistribution review pending |
| [GSE42296](datasets/gse42296/README.md) | 39 Crohn/RA patients, 78 microarrays, 33,297 probes | Validated local preview; redistribution review pending |
| [GSE65391](datasets/gse65391/README.md) | Provisional SLE subset: 158 patients, 900 microarrays | On hold: replicate handling unresolved |
| [IBDMDB](datasets/ibdmdb/README.md) | 112 participants, 898 clinical snapshots, 224 CRP/ESR measurements, subject ClarIDs; three assay modalities | Private import-tested preview; final product-scope review before public distribution |

IBDMDB is available through a private GitHub prerelease and has been imported
and browsed in COHORTome. The other real-study packages remain local previews,
not app-tested releases. IBDMDB includes subject ClarIDs; the other studies
still need clinical mapping and subject identifiers reviewed. Sample ClarIDs
are deferred.
Validation checks file structure and linkage. It does not establish that the
clinical interpretation, preprocessing or analysis is correct.

## What each dataset README must record

- Source accession, original study and exact input files.
- Whether inputs came directly from the source or through an intermediate export.
- Available patients, samples, visits and measurements.
- Conversion steps, numerical transformations, exclusions and missing data.
- Known limits, including repeated measurements and technical replicates.
- Data access conditions and redistribution evidence, with links and review date.
- Preparation and validation commands; resource version and checksum manifest.

Do not assign the repository's software licence to third-party data. Do not
infer a data licence from a paper's open-access licence or an accessible download.
When the applicable terms have not been established, record **pending** and do
not publish the archive. Obtain clarification from the source if necessary.

## Version and checksum

A resource version identifies a prepared dataset, independently of app commits.
`manifest_version` describes the resource manifest; `schema_version` describes
the COHORTome dataset contract. Reviewed entries in `catalog/` record the exact
archive name, byte size and SHA-256. Check the downloaded archive against that
repository entry with `scripts/verify_resource.py`.

During private development, unreleased 0.1 previews may be replaced under the
same version. Their checksums and catalogue entries must be updated together.
After public release, changes to data or metadata require a new resource version.
Keep the preparation recipe and reason for each change.

## Next app checks

1. GSE191328: map the recorded diagnoses to ontology terms, preserve treatment
   groups and the future remission endpoint without inventing visit observations,
   add subject ClarIDs, and check all 201 sample links and clinical timepoints.
2. GSE42296: apply the same mapping/identifier checks to both diseases and visits;
   retain its processed microarray scale, not RNA-seq counts.
3. GSE65391: keep on hold until replicate handling is reviewed. Do not silently
   collapse or exclude replicates.

The two GEO previews are not yet cleared for distribution. Review and record
their source terms before uploading archives.
