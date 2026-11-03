"""Package existing CINECA UK1 clinical/biosample BFF for local testing."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from build_synthetic import archive, write_json

DATASET_ID = 'cineca-uk1-demo'


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def build(source, cohortome, output):
    source, cohortome, output = map(lambda p: Path(p).resolve(), (source, cohortome, output))
    if output.exists():
        raise ValueError('Output exists; choose a new directory')
    sys.path.insert(0, str(cohortome))
    from app.dataset_validation import validate_package
    inputs = {'individuals.json': source / 'bff/individuals.json',
              'biosamples.json': source / 'bff/biosamples.json',
              'source-README.md': source / 'README.md'}
    hashes = {name: digest(path) for name, path in inputs.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cineca-', dir=output.parent) as temp:
        release = Path(temp) / 'release'
        package = release / DATASET_ID
        (package / 'clinical').mkdir(parents=True)
        (package / 'provenance').mkdir()
        shutil.copyfile(inputs['individuals.json'], package / 'clinical/individuals.json')
        shutil.copyfile(inputs['biosamples.json'], package / 'biosamples.json')
        shutil.copyfile(inputs['source-README.md'], package / 'provenance/source-README.md')
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'datasets/cineca-uk1/README.md', package / 'README.md')
        write_json(package / 'manifest.json', {
            'schema_version': 1, 'name': 'CINECA UK1 demo',
            'study_design': 'cross_sectional', 'clinical': {'representation': 'person'},
            'biosamples': {'file': 'biosamples.json'}})
        validation = validate_package(package)
        if 'biosamples' not in validation:
            raise ValueError('Use a COHORTome checkout with biosample support')
        write_json(package / 'provenance/preparation.json', {
            'recipe_version': '0.1.0', 'source_dataset': 'EGAD00001006673',
            'source_files_sha256': hashes, 'recipe_sha256': digest(Path(__file__)),
            'processing': 'Clinical and biosample BFF copied unchanged. No new conversion or inference.',
            'included': ['clinical', 'biosamples'],
            'not_included': ['variants', 'RNA expression', 'ClarIDs'],
            'redistribution_review': 'pending',
            'limitations': 'Synthetic clinical attributes are for software testing, not biological association analysis.'})
        write_json(package / 'provenance/validation.json', validation)
        write_json(package / 'resource.json', {
            'manifest_version': 1, 'schema_version': 1, 'dataset_id': DATASET_ID,
            'version': '0.1.0', 'synthetic': True,
            'files_sha256': {p.relative_to(package).as_posix(): digest(p)
                             for p in sorted(package.rglob('*')) if p.is_file()}})
        filename = DATASET_ID + '-0.1.0-local.zip'
        archive(package, release / filename)
        write_json(release / 'release.json', {
            'manifest_version': 1, 'schema_version': 1, 'dataset_id': DATASET_ID,
            'version': '0.1.0', 'archive': filename, 'archive_sha256': digest(release / filename),
            'archive_bytes': (release / filename).stat().st_size,
            'redistribution_review': 'pending'})
        shutil.move(str(release), output)
    return validation


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='CINECA root containing bff/ and README.md')
    parser.add_argument('--cohortome', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.cohortome, args.output), indent=2))
