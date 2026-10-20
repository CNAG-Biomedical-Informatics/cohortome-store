"""Package both GSE42296 disease groups from the ED-Omics public-data export."""
import argparse
import csv
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote

import numpy as np
import pandas as pd

from build_synthetic import archive, write_json
from prepare_gse191328 import sha256


def prepare(source, package):
    metadata_path, expression_path = source / 'metadata.tsv', source / 'expression.npz'
    m = pd.read_csv(metadata_path, sep='\t', dtype=str, keep_default_na=False)
    required = {'sample_id', 'subject', 'response', 'treatment', 'time', 'disease state', 'cell type'}
    if not required <= set(m.columns) or m.empty or m.sample_id.duplicated().any():
        raise ValueError('Incomplete metadata or duplicate sample IDs')
    diseases = {"Crohn's disease": 'CD', 'Rheumatoid arthritis': 'RA'}
    if set(m['disease state']) != set(diseases):
        raise ValueError('Expected both Crohn and rheumatoid arthritis source groups')
    if not set(m.response) <= {'R - responder', 'NR - non-responder'}:
        raise ValueError('Unexpected response label')
    if m.duplicated(['disease state', 'subject', 'time']).any():
        raise ValueError('Duplicate disease/patient/visit; review rather than discard')
    for _, group in m.groupby(['disease state', 'subject']):
        if set(group.time) != {'week 0', 'week 2'} or group.response.nunique() != 1:
            raise ValueError('Expected complete paired visits with consistent response labels')
    with np.load(expression_path, allow_pickle=False) as data:
        values, probes, source_samples = data['expression'], data['probes'], data['samples']
    if (values.shape != (len(source_samples), len(probes)) or
            len(set(source_samples)) != len(source_samples) or len(set(probes)) != len(probes) or
            not len(probes) or not np.isfinite(values).all() or
            set(m.sample_id) != set(source_samples)):
        raise ValueError('Expression shape, identifiers, coverage or values are invalid')
    # Align explicitly by original sample ID, never by source row position.
    index = {sample: i for i, sample in enumerate(source_samples)}
    values = values[[index[s] for s in m.sample_id]]
    samples, records = [], []
    for row in m.to_dict('records'):
        patient = 'GSE42296-' + diseases[row['disease state']] + '-' + quote(row['subject'], safe='')
        sample = patient + ':' + row['sample_id']
        day = {'week 0': 0, 'week 2': 14}[row['time']]
        expected_treatment = 'Before treatment' if day == 0 else 'infliximab'
        if row['treatment'] != expected_treatment or row['cell type'] != 'PBMC':
            raise ValueError('Unexpected treatment timing or tissue')
        records.append({'id': sample, 'patient_id': patient, 'visit_id': row['time'],
            'diseases': [{'diseaseCode': {'id': 'GSE42296:' + diseases[row['disease state']],
                                        'label': row['disease state']}}],
            'treatments': [] if day == 0 else [{'treatmentCode': {'label': 'Infliximab'}}],
            'info': {'source_accession': row['sample_id'], 'source_subject': row['subject'],
                     'days_from_baseline': day, 'treatment_response': row['response'],
                     'source_metadata': row}})
        samples.append({'sample_id': sample, 'patient_id': patient,
            'source_sample_id': row['sample_id'], 'source_patient_id': row['subject'],
            'diagnosis': row['disease state'], 'timepoint': row['time'],
            'days_from_baseline': day, 'treatment': row['treatment'], 'response': row['response'],
            'tissue': row['cell type']})
    (package / 'clinical').mkdir(parents=True)
    (package / 'assays').mkdir()
    write_json(package / 'manifest.json', {'schema_version': 1,
        'name': 'GSE42296 Crohn disease and rheumatoid arthritis infliximab study',
        'study_design': 'longitudinal', 'clinical': {'representation': 'snapshot'}})
    write_json(package / 'clinical/records.json', records)
    with (package / 'assays/samples.tsv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(samples[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(samples)
    with (package / 'assays/expression.csv').open('w', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['feature_id'] + [s['sample_id'] for s in samples])
        for probe, expression in zip(probes, values.T):
            writer.writerow([probe] + expression.astype(float).tolist())
    write_json(package / 'assays/manifest.json', {'version': 1, 'assays': [{
        'assay_id': 'gse42296_microarray', 'label': 'Published PBMC microarray expression',
        'modality': 'transcriptomics', 'data_type': 'microarray_expression', 'level': 'sample',
        'feature_namespace': 'affymetrix_transcript_cluster_id', 'feature_id_column': 'feature_id',
        'sample_id_column': 'matrix_columns', 'patient_id_column': 'patient_id',
        'patient_linkage': 'sample_metadata_file', 'sample_metadata_file': 'assays/samples.tsv',
        'file': 'assays/expression.csv', 'feature_count': len(probes)}]})
    return {'metadata.tsv': sha256(metadata_path), 'expression.npz': sha256(expression_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohortome', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'dist')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.version):
        parser.error('Invalid resource version')
    sys.path.insert(0, str(args.cohortome.resolve()))
    from app.dataset_validation import validate_package
    output = args.output.resolve()
    destination = output / ('gse42296-' + args.version)
    if destination.exists():
        parser.error('Release exists; choose a new version or output directory')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gse42296-', dir=output) as temporary:
        release = Path(temporary) / 'release'
        package = release / 'gse42296'
        sources = prepare(args.source.resolve(), package)
        validation = validate_package(package)
        resource = {'manifest_version': 1, 'dataset_id': 'gse42296', 'version': args.version,
            'schema_version': 1, 'distribution_status': 'local-preview', 'redistribution_review': 'pending',
            'synthetic': False, 'source_files_sha256': sources, 'validation': validation,
            'sources': ['https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE42296'],
            'preparation': 'ED-Omics export of original GEO SOFT expression, previously stored as float32; no further normalization or filtering.',
            'limitations': ['Microarray values are not counts; count-based workflows are inappropriate.',
                'Paired visits must be modelled by patient.',
                'Response labels are outcomes, not visit-specific measurements; endpoint definitions require source review.',
                'No calendar dates, demographics, doses or clinical scores inferred.',
                'Original probe IDs preserved; no gene-annotation mapping or probe collapsing.',
                'Source-specific disease identifiers are not ontology mappings.',
                'In-app ingestion and analysis compatibility have not yet been verified.']}
        resource['files_sha256'] = {p.relative_to(package).as_posix(): sha256(p)
                                   for p in sorted(package.rglob('*')) if p.is_file()}
        write_json(package / 'resource.json', resource)
        filename = destination.name + '.zip'
        archive(package, release / filename)
        entry = {key: resource[key] for key in ['manifest_version', 'dataset_id', 'version',
                 'schema_version', 'distribution_status', 'redistribution_review']}
        entry.update(archive=filename, archive_sha256=sha256(release / filename),
                     archive_bytes=(release / filename).stat().st_size)
        write_json(release / 'release.json', entry)
        shutil.move(str(release), destination)
    print(json.dumps({'validation': validation, **entry}, indent=2))


if __name__ == '__main__':
    main()
