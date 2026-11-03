"""Add matched GEUVADIS normalized expression to a local CINECA package."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

from build_synthetic import write_json
from prepare_cineca_uk1 import digest

SOURCE_URL = 'https://zenodo.org/records/15596289'
SOURCE_MD5 = '500bffeed8e0f770c157e0189e9e50ae'


def convert(expression, clinical, folder):
    """Stream rows, retaining source values and feature versions unchanged."""
    patients = {r['id'] for r in json.loads(clinical.read_text())}
    folder.mkdir(parents=True)
    with gzip.open(expression, 'rt') as source, (folder / 'expression.csv').open('w', newline='') as target, (folder / 'features.tsv').open('w', newline='') as annotations:
        reader = csv.reader(source, delimiter='\t')
        header = next(reader)
        if header[:4] != ['TargetID', 'Gene_Symbol', 'Chr', 'Coord']:
            raise ValueError('Unexpected GEUVADIS expression header')
        source_ids = header[4:]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError('Duplicate expression sample IDs')
        selected = [(i + 4, pid) for i, pid in enumerate(source_ids) if pid in patients]
        if not selected:
            raise ValueError('No clinical/expression overlap')
        writer = csv.writer(target)
        writer.writerow(['gene_id'] + [pid + ':geuvadis-rna' for _, pid in selected])
        feature_writer = csv.writer(annotations, delimiter='\t')
        feature_writer.writerow(['gene_id', 'source_gene_symbol', 'chromosome', 'coordinate'])
        genes, negative_values = set(), 0
        for row in reader:
            if len(row) != len(header) or not row[0] or row[0] in genes:
                raise ValueError('Invalid feature identity or expression row width')
            genes.add(row[0])
            values = [row[i] for i, _ in selected]
            for value in values:
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError('Nonfinite expression value')
                negative_values += number < 0
            writer.writerow([row[0]] + values)
            feature_writer.writerow(row[:4])
    if not genes:
        raise ValueError('No expression features')
    with (folder / 'samples.tsv').open('w', newline='') as handle:
        writer = csv.writer(handle, delimiter='\t')
        writer.writerow(['sample_id', 'patient_id', 'source_sample_id', 'material'])
        writer.writerows((pid + ':geuvadis-rna', pid, pid, 'lymphoblastoid cell line') for _, pid in selected)
    return dict(source_samples=len(source_ids), matched_patients=len(selected),
                excluded_sample_ids=[pid for pid in source_ids if pid not in patients],
                genes=len(genes), negative_values=negative_values)


def build(expression, source_readme, package, cohortome, output):
    expression, source_readme, package, cohortome, output = map(lambda p: Path(p).resolve(),
        (expression, source_readme, package, cohortome, output))
    if output.exists():
        raise ValueError('Output exists; choose a new directory')
    with expression.open('rb') as handle:
        if hashlib.file_digest(handle, 'md5').hexdigest() != SOURCE_MD5:
            raise ValueError('Expression download does not match the published Zenodo checksum')
    sys.path.insert(0, str(cohortome))
    from app.dataset_validation import validate_package
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cineca-rna-', dir=output.parent) as temp:
        work = Path(temp) / 'package'
        shutil.copytree(package, work)
        folder = work / 'assays/transcriptomics'
        if folder.exists() or (work / 'assays/manifest.json').exists():
            raise ValueError('Use the clinical-only CINECA package as input')
        report = convert(expression, work / 'clinical/individuals.json', folder)
        write_json(work / 'assays/manifest.json', {'version': 1, 'assays': [{
            'assay_id': 'geuvadis_normalized_expression',
            'label': 'GEUVADIS gene expression (PEER-normalized)',
            'modality': 'transcriptomics', 'data_type': 'normalized_expression',
            'level': 'sample', 'file': 'assays/transcriptomics/expression.csv',
            'sample_metadata_file': 'assays/transcriptomics/samples.tsv',
            'feature_metadata_file': 'assays/transcriptomics/features.tsv',
            'feature_namespace': 'ensembl_gene_id', 'feature_id_column': 'gene_id',
            'feature_count': report['genes'], 'sample_id_column': 'matrix_columns',
            'patient_linkage': 'sample_metadata_file', 'patient_id_column': 'patient_id',
            'value_kind': 'peer_normalized_expression',
            'supports_expression_summary': False, 'supports_differential_expression': False}]})
        shutil.copyfile(source_readme, work / 'provenance/GEUVADIS_README.txt')
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'datasets/cineca-uk1/README.md', work / 'README.md')
        write_json(work / 'provenance/expression-preparation.json', {
            'recipe_version': '0.1.0', 'source_url': SOURCE_URL, 'source_md5': SOURCE_MD5,
            'source_sha256': digest(expression), 'source_readme_sha256': digest(source_readme),
            'recipe_sha256': digest(Path(__file__)), 'counts': report,
            'source_license': 'Zenodo record declares CC-BY-4.0; Lappalainen et al., Nature 2013, doi:10.1038/nature12531',
            'processing': 'Exact individual-ID overlap; preserve source gene IDs and normalized expression values. No aggregation or imputation.',
            'normalization': 'Source filtered and PEER-normalized gene expression; not raw counts or unadjusted RPKM.',
            'sample_linkage': 'Individual-level only. RNA LCL material is not asserted to be the CINECA blood biosample.',
            'limitations': 'Synthetic clinical attributes must not be used for biological association claims.',
            'redistribution_review': 'pending'})
        validation = validate_package(work)
        write_json(work / 'provenance/validation.json', validation)
        write_json(work / 'resource.json', {
            'manifest_version': 1, 'schema_version': 1, 'dataset_id': 'cineca-uk1-demo',
            'version': '0.1.0', 'synthetic': False,
            'description': 'Synthetic clinical attributes linked to measured GEUVADIS expression',
            'files_sha256': {p.relative_to(work).as_posix(): digest(p)
                             for p in sorted(work.rglob('*')) if p.is_file() and p != work / 'resource.json'}})
        shutil.move(str(work), output)
    return dict(patients=validation['patients'], expression_patients=report['matched_patients'],
                excluded_samples=len(report['excluded_sample_ids']), genes=report['genes'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('expression', 'source-readme', 'package', 'cohortome', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.expression, args.source_readme, args.package, args.cohortome, args.output), indent=2))
