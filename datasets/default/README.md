# Default synthetic dataset

Package ID: `default`.

Source: `default_dataset/` in the COHORTome repository. The relevant generator
is `scripts/generate_synthetic_multimodal_fixture.py`; subject identifier
generation is handled by `scripts/generate_synthetic_clarids.py`.

Purpose: longitudinal clinical exploration and synthetic assay demonstrations.
It remains bundled with the application and should also be available as a
standalone package using the same validation and ingestion path.

Status: version 0.1.1-preview is packaged, schema-validated and uploaded as a
private GitHub prerelease. It includes shortened COH-SYN ClarIDs. Validation
warnings about existing sample-prefix linkage are recorded in release.json.
Review source and third-party asset terms before public distribution.
