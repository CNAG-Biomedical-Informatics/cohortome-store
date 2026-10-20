# Synthetic access-control fixture

Package ID: `private-dataset`, matching the existing application registry.

Source: `private_dataset/` in the COHORTome repository. Despite the directory
name, this is a synthetic fixture, not a restricted research release.

Purpose: exercise restricted visibility, Summary access and model-context
policies. The package contains data; the test deployment configures the access
rules separately. An archive must never contain users, groups, passwords or
runtime state.

Status: existing source files; packaging and schema validation pending.
Intended primarily for developers. Review all included asset terms before any
public archive is released.
