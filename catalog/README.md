# Dataset catalogue

This inventory includes local previews and private GitHub release downloads.
Versioned JSON entries record archive checksums and exact download URLs where
available. Private downloads require repository access; see [instructions](../DOWNLOADS.md).

| Package ID | Kind | Current source | Intended delivery |
| --- | --- | --- | --- |
| `default` | Synthetic longitudinal example | COHORTome `default_dataset/` | Bundled and separately downloadable |
| `synthetic-autoimmune-demo` | Synthetic multimodal example | COHORTome `synthetic_autoimmune_demo/` | Bundled and separately downloadable |
| `private-dataset` | Synthetic permission-testing fixture | COHORTome `private_dataset/` | Developer/test resource |
| `dataset-large` | Synthetic transcriptomics timing fixture | COHORTome `dataset-large/` | Developer/optional resource |
| `gse191328` | Public IBD research study | GEO metadata and featureCounts; local preview prepared | Optional download after review |
| `gse42296` | Crohn/RA treatment study | ED-Omics export of GEO SOFT; local preview prepared | Optional download after review |
| `gse65391` | SLE study | Provisional preview; replicate handling unresolved | On hold |
| `ibdmdb` | Public IBD multi-omics | Processed metabolomics, metaproteomics and serology | Local preview; final product-scope review before publication |

The first four IDs match the existing application registry. `gse191328` is a
proposed resource ID and does not register a dataset in the application.

Manifest version 1 records dataset ID/version, schema version, archive name,
byte size, SHA-256 and review status. Source citations, preparation and access
terms are documented in each dataset README and the archive's resource.json.
Add exact archive URLs only after publication. Do not invent licences or
compatibility claims before review. See [dataset status](../DATASETS.md).

Installation must not copy access grants or AI-provider permissions from this
catalogue. Those are controlled by the receiving deployment.
