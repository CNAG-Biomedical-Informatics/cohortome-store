"""Package the reviewed compact CINECA demo for Store distribution."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

from build_synthetic import write_json
from prepare_cineca_uk1 import digest


def build(package, output, cohortome):
    package, output, cohortome = [Path(p).resolve() for p in (package, output, cohortome)]
    if output.exists():
        raise ValueError('Output exists; do not overwrite a published package')
    sys.path.insert(0, str(cohortome))
    from app.dataset_validation import validate_package
    store = Path(__file__).resolve().parents[1]
    resource = json.loads((package / 'resource.json').read_text())
    for name, expected in resource['files_sha256'].items():
        path = (package / name).resolve()
        if not path.is_relative_to(package) or digest(path) != expected:
            raise ValueError('Input checksum mismatch')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cineca-release-', dir=output.parent) as temp:
        release = Path(temp) / 'release'
        work = release / 'cineca-uk1-demo'
        shutil.copytree(package, work)
        for name in ('README.md', 'TERMS.md'):
            shutil.copyfile(store / 'datasets/cineca-uk1' / name, work / name)
        write_json(work / 'provenance/distribution-review.json', {
            'review_date': '2026-11-03', 'terms_file': 'TERMS.md',
            'decision': 'Distribute this prepared demonstration with source attribution and notices.',
            'scope': 'Synthetic clinical BFF, biosamples, matched GEUVADIS expression, 44 selected chr22 variants.',
            'recipe_sha256': digest(Path(__file__)),
            'historical_notes': 'Pending review in earlier preparation-stage records is superseded by this distribution review.'})
        validation = validate_package(work)
        write_json(work / 'provenance/validation.json', validation)
        resource['files_sha256'] = {p.relative_to(work).as_posix(): digest(p)
            for p in sorted(work.rglob('*')) if p.is_file() and p != work / 'resource.json'}
        write_json(work / 'resource.json', resource)
        filename = resource['dataset_id'] + '-' + resource['version'] + '.zip'
        archive = release / filename
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as target:
            for path in sorted(work.rglob('*')):
                if path.is_symlink():
                    raise ValueError('No symlinks in published packages')
                if path.is_file():
                    info = zipfile.ZipInfo(work.name + '/' + path.relative_to(work).as_posix(), (1980, 1, 1, 0, 0, 0))
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    target.writestr(info, path.read_bytes(), compresslevel=6)
        metadata = dict(dataset_id=resource['dataset_id'], version=resource['version'],
                        archive=filename, archive_bytes=archive.stat().st_size, archive_sha256=digest(archive))
        write_json(release / 'release.json', metadata)
        shutil.move(str(release), output)
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'output', 'cohortome'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.package, args.output, args.cohortome), indent=2))
