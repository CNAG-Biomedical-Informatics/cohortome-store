"""Prepare non-replicate SLE samples from the public GSE65391 series matrix."""
import argparse
import csv
import gzip
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote

from build_synthetic import archive, write_json
from prepare_gse191328 import sha256


def select_samples(metadata):
    if not set(metadata['disease state']) <= {'SLE', 'Healthy'}:
        raise ValueError('Unexpected disease group')
    if not set(metadata.batch_replicate) <= {'TRUE', 'FALSE'}:
        raise ValueError('Unexpected replicate flag')
    selected = metadata[(metadata['disease state'] == 'SLE') &
                        (metadata.batch_replicate == 'FALSE')].copy()
    if selected.empty or selected.sample_id.duplicated().any():
        raise ValueError('Empty selection or duplicate samples')
    if selected.duplicated(['subject', 'visit']).any():
        raise ValueError('Duplicate patient visit')
    records, samples = [], []
    seen_times = set()
    for row in selected.to_dict('records'):
        patient = 'GSE65391-' + quote(row['subject'], safe='')
        sample = patient + ':' + row['sample_id']
        elapsed, age, score = (float(row[key]) for key in ['cumulative_time', 'age', 'sledai'])
        if not all(math.isfinite(value) and value >= 0 for value in (elapsed, age, score)):
            raise ValueError('Invalid time, age or SLEDAI value')
        if (patient, elapsed) in seen_times:
            raise ValueError('Duplicate patient sampling time')
        seen_times.add((patient, elapsed))
        if row['gender'] not in {'F', 'M'}:
            raise ValueError('Unmapped source sex value')
        records.append({
            'id': sample, 'patient_id': patient, 'visit_id': row['visit'],
            'sex': {'label': 'Female' if row['gender'] == 'F' else 'Male'},
            'diseases': [{'diseaseCode': {'id': 'GSE65391:SLE', 'label': 'Systemic Lupus Erythematosus'}}],
            'measures': [{'assayCode': {'id': 'GSE65391:SLEDAI', 'label': 'SLEDAI'},
                          'measurementValue': {'quantity': {'value': score}}}],
            'info': {'source_accession': row['sample_id'], 'source_subject': row['subject'],
                     'days_from_baseline': elapsed, 'age_at_visit_years': age,
                     'study_batch': row['batch'], 'source_metadata': row}})
        samples.append({'sample_id': sample, 'patient_id': patient,
                        'source_sample_id': row['sample_id'], 'timepoint': row['visit'],
                        'days_from_baseline': elapsed,
                        **{'source_' + key: value for key, value in row.items() if key != 'sample_id'}})
    return records, samples


def expression(source, target, samples):
    """Stream published values without normalization, annotation or probe filtering."""
    features, header, ended = set(), None, False
    with gzip.open(source, 'rt') as handle, target.open('w', newline='') as output:
        reader = csv.reader(handle, delimiter='\t')
        writer = csv.writer(output, lineterminator='\n')
        for row in reader:
            if row and row[0] == '!series_matrix_table_begin':
                header = next(reader)
                break
        if not header or header[0] != 'ID_REF' or len(header) != len(set(header)):
            raise ValueError('Missing or invalid expression matrix header')
        columns = [header.index(s['source_sample_id']) for s in samples]
        writer.writerow(['feature_id'] + [s['sample_id'] for s in samples])
        for row in reader:
            if row and row[0] == '!series_matrix_table_end':
                ended = True
                break
            if len(row) != len(header) or not row[0] or row[0] in features:
                raise ValueError('Invalid expression row or duplicate probe')
            if not re.fullmatch(r'ILMN_[0-9]+', row[0]):
                raise ValueError('Unexpected probe namespace')
            values = [row[i] for i in columns]
            if not all(math.isfinite(float(value)) for value in values):
                raise ValueError('Nonfinite expression value')
            writer.writerow([row[0]] + values)
            features.add(row[0])
    if not ended or not features:
        raise ValueError('Truncated or empty matrix')
    return len(features)


def build(source, output, version, read_metadata, validate):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', version):
        raise ValueError('Invalid resource version')
    destination = output / ('gse65391-' + version)
    if destination.exists():
        raise ValueError('Release already exists; choose a new version or output directory')
    metadata = read_metadata(source)
    clinical, samples = select_samples(metadata)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gse65391-', dir=output) as temporary:
        release = Path(temporary) / 'release'
        package = release / 'gse65391'
        (package / 'clinical').mkdir(parents=True)
        (package / 'assays').mkdir()
        write_json(package / 'manifest.json', {'schema_version': 1,
            'name': 'GSE65391 longitudinal pediatric SLE microarray',
            'study_design': 'longitudinal', 'clinical': {'representation': 'snapshot'}})
        write_json(package / 'clinical/records.json', clinical)
        with (package / 'assays/samples.tsv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(samples[0]), delimiter='\t', lineterminator='\n')
            writer.writeheader()
            writer.writerows(samples)
        features = expression(source, package / 'assays/expression.csv', samples)
        write_json(package / 'assays/manifest.json', {'version': 1, 'assays': [{
            'assay_id': 'gse65391_microarray', 'label': 'Published whole-blood microarray expression',
            'modality': 'transcriptomics', 'data_type': 'microarray_expression', 'level': 'sample',
            'feature_namespace': 'illumina_probe_id', 'feature_id_column': 'feature_id',
            'sample_id_column': 'matrix_columns', 'patient_id_column': 'patient_id',
            'patient_linkage': 'sample_metadata_file', 'sample_metadata_file': 'assays/samples.tsv',
            'file': 'assays/expression.csv', 'feature_count': features}]})
        validation = validate(package)
        resource = {'manifest_version': 1, 'dataset_id': 'gse65391', 'version': version,
            'schema_version': 1, 'synthetic': False, 'distribution_status': 'local-preview',
            'redistribution_review': 'pending', 'source_sha256': sha256(source),
            'sources': ['https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE65391',
                        'https://pmc.ncbi.nlm.nih.gov/articles/PMC5426482/'],
            'validation': validation,
            'selection': {'source_samples': len(metadata), 'retained_samples': len(samples),
                'excluded_healthy_samples': int((metadata['disease state'] == 'Healthy').sum()),
                'excluded_sle_batch_replicates': int(((metadata['disease state'] == 'SLE') &
                                                     (metadata.batch_replicate == 'TRUE')).sum())},
            'preparation': 'Published probe values preserved; no renormalization, probe filtering or gene mapping.',
            'limitations': ['Microarray values are not counts: no voom/DESeq2/count-based analysis.',
                'Source expression is already processed; upstream preprocessing needs scientific review.',
                'Repeated visits require patient-aware analysis.',
                'No calendar dates or doses inferred. Relative times retained in metadata.',
                'Only SLEDAI is mapped to a clinical measurement; other source fields retained verbatim.',
                'Source namespaces used for disease and SLEDAI; no ontology mappings asserted.',
                'App ingestion and analysis compatibility remain to be tested.']}
        resource['files_sha256'] = {p.relative_to(package).as_posix(): sha256(p)
                                   for p in sorted(package.rglob('*')) if p.is_file()}
        write_json(package / 'resource.json', resource)
        filename = 'gse65391-' + version + '.zip'
        archive(package, release / filename)
        record = {key: resource[key] for key in ['manifest_version', 'dataset_id', 'version',
                  'schema_version', 'distribution_status', 'redistribution_review']}
        record.update(archive=filename, archive_sha256=sha256(release / filename),
                      archive_bytes=(release / filename).stat().st_size)
        write_json(release / 'release.json', record)
        shutil.move(str(release), destination)
    return {'output': str(destination), 'validation': validation, **record}


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohortome', type=Path, required=True)
    parser.add_argument('--ed-omics', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'dist')
    args = parser.parse_args()
    sys.path[:0] = [str(args.cohortome.resolve()), str(args.ed_omics.resolve())]
    from ed_omics.public_data import series_metadata
    from app.dataset_validation import validate_package
    print(json.dumps(build(args.source.resolve(), args.output.resolve(), args.version,
                           series_metadata, validate_package), indent=2))
