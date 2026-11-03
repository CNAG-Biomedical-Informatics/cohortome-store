# App catalogue

`catalogue.json` is the dataset list read by COHORTome's **Add dataset → Refresh**
action. It contains metadata, not patient records or executable preparation code.
The older per-dataset JSON files are preparation records, not the app feed.

## Updating the list

- Keep `catalogue_version: 1` for this catalogue structure and
  `dataset_schema_version: 1` for the current dataset contract.
- Use a unique `dataset_id`, a resource `version`, a name, description and source
  terms for every entry. Use HTTPS links for source documentation.
- For a prepared archive, include `archive_bytes` and `archive_sha256`. Publish
  it in this repository as release `DATASET_ID-VERSION`, asset
  `DATASET_ID-VERSION.zip`. Do not replace different bytes under the same version.
- For fetch-and-build, set `install_mode: source`, `recipe_version`, `source_bytes`,
  source and policy links, and the acknowledgement text. The installed app must
  already support that exact recipe and output version. Adding an entry does not
  install preparation code or change the app's pinned upstream downloads.
- An entry can declare a newer `dataset_schema_version`; older apps show it as
  requiring an update rather than allowing installation.

Review provenance and usage terms before listing a dataset. Public access alone
is not permission to redistribute its data. Do not include credentials, local
paths, access grants, AI permissions, arbitrary download URLs or shell commands.

COHORTome validates a refreshed list before caching it. Network failures or
invalid lists leave the previous cache intact; a bundled catalogue supports
offline first use. Installed datasets are unaffected by catalogue changes.

Dataset-list updates need only a Store commit/push. New input formats or
preparation recipes still require a COHORTome release. Released apps before this
feature continue using their bundled list.
