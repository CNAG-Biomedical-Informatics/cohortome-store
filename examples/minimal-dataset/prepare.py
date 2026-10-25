"""Build the fixed synthetic tutorial; not a general clinical-data converter."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

EXAMPLE = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE.parents[1] / 'scripts'))
from build_synthetic import archive, write_json


def sha256(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def build(cohortome, converter, output):
    sys.path.insert(0, str(cohortome))
    from app.dataset_validation import validate_package

    if output.exists():
        raise ValueError('Output already exists; choose a new directory')
    revision = subprocess.check_output(
        ['git', '-C', str(cohortome), 'rev-parse', 'HEAD'], text=True).strip()
    version_output = subprocess.check_output([str(converter), '--version'], text=True)
    version_match = re.search(r'Version\s+(\S+)', version_output)
    if not version_match:
        raise ValueError('Cannot identify Convert-Pheno version')
    converter_version = version_match.group(1)
    with (EXAMPLE / 'clinical.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    if len({r['snapshot_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate clinical snapshot')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tutorial-', dir=output.parent) as temp:
        work = Path(temp)
        release = work / 'release'
        package = release / 'tutorial-longitudinal'
        provenance = package / 'provenance'
        for folder in ('clinical', 'assays', 'provenance'):
            (package / folder).mkdir(parents=True)
        for name in ('clinical.csv', 'clinical.yaml', 'samples.tsv', 'counts.csv', 'prepare.py'):
            shutil.copyfile(EXAMPLE / name, provenance / name)
        with (work / 'converter.log').open('w') as log:
            try:
                subprocess.run([
                    str(converter), '-icsv', str(EXAMPLE / 'clinical.csv'), '--separator', ',',
                    '--mapping-file', str(EXAMPLE / 'clinical.yaml'), '--search', 'exact',
                    '--no-source-info', '--term-audit', str(provenance / 'terminology.tsv'),
                    '-obff', str(work / 'converted.json')], check=True, stdout=log, stderr=log)
            except subprocess.CalledProcessError:
                # Only the fixed invented tutorial is processed by this recipe.
                print((work / 'converter.log').read_text(), file=sys.stderr)
                raise
        converted = json.loads((work / 'converted.json').read_text())
        by_id = {r['id']: r for r in converted}
        if len(by_id) != len(converted) or set(by_id) != {r['snapshot_id'] for r in rows}:
            raise ValueError('Conversion changed snapshot identities')
        records = []
        for row in rows:
            mapped = by_id[row['snapshot_id']]
            disease = mapped.get('diseases', [])
            expected = {'CD': 'NCIT:C2965', 'UC': 'NCIT:C2952'}[row['diagnosis']]
            if len(disease) != 1 or disease[0]['diseaseCode']['id'] != expected:
                raise ValueError('Review the converted diagnosis against the mapping')
            if mapped['sex']['id'] != {'Female': 'NCIT:C16576', 'Male': 'NCIT:C20197'}[row['sex']]:
                raise ValueError('Review the converted sex term')
            # Unknown onset/age defaults are not observations.
            records.append({
                'id': row['snapshot_id'], 'patient_id': row['patient_id'],
                'sex': mapped['sex'], 'diseases': [{'diseaseCode': disease[0]['diseaseCode']}],
                'info': {'visit_id': row['visit_id'],
                         'days_from_baseline': int(row['days_from_baseline']),
                         'source_metadata': row}})
        write_json(package / 'clinical/records.json', records)
        write_json(package / 'manifest.json', {
            'schema_version': 1, 'name': 'Synthetic preparation tutorial',
            'study_design': 'longitudinal', 'clinical': {'representation': 'snapshot'}})
        for name in ('counts.csv', 'samples.tsv'):
            shutil.copyfile(EXAMPLE / name, package / 'assays' / name)
        write_json(package / 'assays/manifest.json', {'version': 1, 'assays': [{
            'assay_id': 'tutorial_rna', 'label': 'Invented counts for linkage testing',
            'modality': 'transcriptomics', 'data_type': 'raw_counts', 'level': 'sample',
            'file': 'assays/counts.csv', 'feature_namespace': 'synthetic_tutorial',
            'feature_id_column': 'gene_id', 'feature_count': 3,
            'sample_id_column': 'matrix_columns', 'patient_id_column': 'patient_id',
            'patient_linkage': 'sample_metadata_file', 'sample_metadata_file': 'assays/samples.tsv'}]})
        shutil.copyfile(EXAMPLE / 'README.md', package / 'README.md')
        write_json(provenance / 'preparation.json', {
            'recipe_version': '0.1.0', 'cohortome_revision': revision,
            'convert_pheno_version': converter_version,
            'source': 'Invented tutorial inputs; no study data or downloads',
            'source_files_sha256': {name: sha256(EXAMPLE / name) for name in
                                   ('clinical.csv', 'clinical.yaml', 'samples.tsv', 'counts.csv', 'prepare.py')},
            'clinical_fields': 'Mapped sex and diseaseCode; identity and visit context from CSV',
            'omitted': 'No ages, onset dates, treatment or clinical measurements supplied',
            'assay_processing': 'None; counts.csv and samples.tsv copied unchanged'})
        validation = validate_package(package)
        write_json(provenance / 'validation.json', validation)
        write_json(package / 'resource.json', {
            'manifest_version': 1, 'schema_version': 1,
            'dataset_id': 'tutorial-longitudinal', 'version': '0.1.0', 'synthetic': True,
            'files_sha256': {p.relative_to(package).as_posix(): sha256(p)
                             for p in sorted(package.rglob('*')) if p.is_file()}})
        filename = 'tutorial-longitudinal-0.1.0.zip'
        archive(package, release / filename)
        write_json(release / 'release.json', {
            'manifest_version': 1, 'schema_version': 1, 'dataset_id': 'tutorial-longitudinal',
            'version': '0.1.0', 'archive': filename, 'archive_sha256': sha256(release / filename),
            'archive_bytes': (release / filename).stat().st_size})
        shutil.move(str(release), output)
    return {'output': str(output), 'validation': validation}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohortome', type=Path, required=True)
    parser.add_argument('--convert-pheno', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.cohortome.resolve(), args.convert_pheno.resolve(),
                           args.output.resolve()), indent=2))
