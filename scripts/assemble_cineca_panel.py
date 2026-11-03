"""Combine a prepared CINECA clinical/RNA package and its compact variant panel."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile

from build_synthetic import write_json
from prepare_cineca_uk1 import digest


def build(package, panel, cohortome, output):
    package, panel, cohortome, output = [Path(p).resolve() for p in (package, panel, cohortome, output)]
    if output.exists():
        raise ValueError('Output exists; choose a new directory')
    report = json.loads((panel / 'preparation.json').read_text())
    for relative, expected in report['files_sha256'].items():
        path = (panel / relative).resolve()
        if not path.is_relative_to(panel) or digest(path) != expected:
            raise ValueError('Panel file checksum mismatch')
    sys.path.insert(0, str(cohortome))
    from app.dataset_validation import validate_package
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cineca-panel-', dir=output.parent) as temp:
        work = Path(temp) / 'package'
        shutil.copytree(package, work)
        manifest = json.loads((work / 'manifest.json').read_text())
        if 'variants' in manifest or (work / 'variants').exists():
            raise ValueError('Input package already has a variant panel')
        folder = work / 'variants'
        folder.mkdir()
        for name in ('variants.tsv', 'samples.tsv'):
            shutil.copyfile(panel / name, folder / name)
        if (panel / 'genotypes.tsv.gz').is_file():
            shutil.copyfile(panel / 'genotypes.tsv.gz', folder / 'genotypes.tsv.gz')
        else:
            with (panel / 'genotypes.tsv').open('rb') as source, (folder / 'genotypes.tsv.gz').open('wb') as raw:
                with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as target:
                    shutil.copyfileobj(source, target)
        manifest['variants'] = dict(schema_version=1, annotations_file='variants/variants.tsv',
            samples_file='variants/samples.tsv', genotypes_file='variants/genotypes.tsv.gz',
            provenance=dict(technology='dna_sequencing', method='Whole-genome sequencing',
                input_format='Annotated VCF', selection='44 selected chromosome 22 variants',
                annotation_tool=report.get('snpeff_version', ''),
                reference=report.get('reference', '')))
        write_json(work / 'manifest.json', manifest)
        shutil.copyfile(panel / 'preparation.json', work / 'provenance/variant-extraction.json')
        validation = validate_package(work)
        write_json(work / 'provenance/validation.json', validation)
        write_json(work / 'provenance/variant-assembly.json', {
            'recipe_sha256': digest(Path(__file__)), 'variant_schema_version': 1,
            'selection': report['selection'], 'redistribution_review': 'pending',
            'interpretation': 'ClinVar annotations are not diagnoses or an independent ACMG assessment. Synthetic clinical attributes do not support biological associations.'})
        resource = json.loads((work / 'resource.json').read_text())
        resource['description'] = 'Synthetic CINECA clinical attributes, GEUVADIS expression and a compact chr22 variant panel'
        resource['files_sha256'] = {p.relative_to(work).as_posix(): digest(p)
            for p in sorted(work.rglob('*')) if p.is_file() and p != work / 'resource.json'}
        write_json(work / 'resource.json', resource)
        shutil.move(str(work), output)
    return validation


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'panel', 'cohortome', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.package, args.panel, args.cohortome, args.output), indent=2))
