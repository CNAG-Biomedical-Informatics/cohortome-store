"""Prepare a local GSE191328 package from the original public GEO inputs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote

import numpy as np

from build_synthetic import archive, write_json


def sha256(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def clinical_and_samples(metadata):
    """Keep source identity, relative timing and future outcome explicitly separate."""
    clinical, samples = [], []
    diagnoses = {'CD': 'Crohn disease', 'UC': 'Ulcerative colitis'}
    if metadata.sample_id.duplicated().any():
        raise ValueError('Duplicate GEO sample identifier')
    for field in ['treatment', 'remission at week 14', 'diagnosis']:
        if metadata.groupby('patient_id')[field].nunique().gt(1).any():
            raise ValueError('Inconsistent patient-level source metadata: ' + field)
    for row in metadata.to_dict('records'):
        if row['diagnosis'] not in diagnoses:
            raise ValueError('Unknown source diagnosis')
        # Escape each component: no collisions and no colon inside patient IDs.
        patient = 'GSE191328-' + quote(row['cohort'], safe='') + ':' + quote(row['patient'], safe='')
        patient = patient.replace(':', '~')
        sample = patient + ':' + row['sample_id']
        clinical.append({
            'id': sample, 'patient_id': patient, 'visit_id': row['time point'],
            'diseases': [{'diseaseCode': {'id': 'GSE191328:' + row['diagnosis'],
                                        'label': diagnoses[row['diagnosis']]}}],
            'treatments': [{'treatmentCode': {'label': row['treatment']},
                            '_info': {'interpretation': 'Study treatment group, not a dated administration'}}],
            'info': {'source_accession': row['sample_id'], 'source_patient_id': row['patient'],
                     'study_cohort': row['cohort'], 'timepoint': row['time point'],
                     'days_from_baseline': row['time'],
                     'remission_at_week_14': row['remission at week 14']}})
        samples.append({'sample_id': sample, 'patient_id': patient,
                        'source_sample_id': row['sample_id'], 'source_patient_id': row['patient'],
                        'study_cohort': row['cohort'], 'diagnosis': row['diagnosis'],
                        'treatment': row['treatment'], 'timepoint': row['time point'],
                        'days_from_baseline': row['time'],
                        'remission_at_week_14': row['remission at week 14']})
    if len({r['sample_id'] for r in samples}) != len(samples):
        raise ValueError('Mapped sample identity collision')
    if len({r['patient_id'] for r in samples}) != metadata.patient_id.nunique():
        raise ValueError('Mapped patient identity collision')
    return clinical, samples


def build(source, output, version, read_metadata, read_counts, validate):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', version):
        raise ValueError('Invalid resource version')
    destination = output / ('gse191328-' + version)
    if destination.exists():
        raise ValueError('Release already exists; use a new version or output directory')
    metadata_path = source / 'ed-GSE191328_series_matrix.txt.gz'
    count_source = source / 'counts'
    if not count_source.is_dir():
        count_source = source / 'GSE191328_RAW.tar'
    metadata = read_metadata(metadata_path)
    clinical, samples = clinical_and_samples(metadata)
    counts, genes = read_counts(count_source, metadata)
    if not all(re.fullmatch(r'ENSG[0-9]+(?:\.[0-9]+)?', str(gene)) for gene in genes):
        raise ValueError('Unexpected feature namespace; review source annotation')
    if (not np.isfinite(counts).all() or (counts < 0).any()
            or (counts >= 2**63).any() or (counts != np.floor(counts)).any()
            or (counts.sum(axis=1) <= 0).any()):
        raise ValueError('Raw counts must be finite nonnegative integers with nonempty libraries')
    if counts.shape != (len(samples), len(genes)):
        raise ValueError('Count dimensions do not match metadata')
    inputs = [metadata_path] + (sorted(count_source.glob('*.txt.gz'))
                              if count_source.is_dir() else [count_source])
    source_hashes = {p.relative_to(source).as_posix(): sha256(p) for p in inputs}
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gse191328-', dir=output) as temporary:
        work = Path(temporary)
        release = work / 'release'
        package = release / 'gse191328'
        (package / 'clinical').mkdir(parents=True)
        (package / 'assays').mkdir()
        write_json(package / 'manifest.json', {
            'schema_version': 1, 'name': 'GSE191328 longitudinal IBD blood RNA-seq',
            'study_design': 'longitudinal', 'clinical': {'representation': 'snapshot'}})
        write_json(package / 'clinical/records.json', clinical)
        with (package / 'assays/samples.tsv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(samples[0]), delimiter='\t', lineterminator='\n')
            writer.writeheader()
            writer.writerows(samples)
        with (package / 'assays/counts.csv').open('w', newline='') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(['gene_id'] + [s['sample_id'] for s in samples])
            for gene, values in zip(genes, counts.T):
                writer.writerow([gene] + values.astype(np.int64).tolist())
        write_json(package / 'assays/manifest.json', {'version': 1, 'assays': [{
            'assay_id': 'gse191328_transcriptomics', 'label': 'Whole-blood RNA-seq gene counts',
            'modality': 'transcriptomics', 'data_type': 'raw_counts', 'level': 'sample',
            'feature_namespace': 'ensembl_gene_id', 'feature_id_column': 'gene_id',
            'sample_id_column': 'matrix_columns', 'patient_id_column': 'patient_id',
            'patient_linkage': 'sample_metadata_file', 'sample_metadata_file': 'assays/samples.tsv',
            'file': 'assays/counts.csv', 'feature_count': len(genes)}]})
        validation = validate(package)
        resource = {
            'manifest_version': 1, 'dataset_id': 'gse191328', 'version': version,
            'schema_version': 1, 'synthetic': False, 'distribution_status': 'local-preview',
            'redistribution_review': 'pending',
            'sources': ['https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE191328',
                        'https://pmc.ncbi.nlm.nih.gov/articles/PMC9509553/'],
            'source_files_sha256': source_hashes, 'validation': validation,
            'preparation': 'Original featureCounts assembled without filtering or normalization.',
            'limitations': [
                'Repeated samples are not independent patients; model patient and visit explicitly.',
                'Week-14 remission is a future endpoint, not a measurement at every visit.',
                'No age, sex, calendar dates, or clinical measurements were inferred.',
                'Relative times are retained in metadata; calendar-date timeline support is not asserted.',
                'Treatment is a study grouping, not a dose or administration record.',
                'CD/UC identifiers use a source namespace, not an asserted ontology mapping.']}
        resource['files_sha256'] = {p.relative_to(package).as_posix(): sha256(p)
                                   for p in sorted(package.rglob('*')) if p.is_file()}
        write_json(package / 'resource.json', resource)
        filename = 'gse191328-' + version + '.zip'
        archive(package, release / filename)
        record = {'manifest_version': 1, 'dataset_id': 'gse191328', 'version': version,
                  'schema_version': 1, 'archive': filename, 'archive_sha256': sha256(release / filename),
                  'archive_bytes': (release / filename).stat().st_size,
                  'distribution_status': 'local-preview', 'redistribution_review': 'pending'}
        write_json(release / 'release.json', record)
        shutil.move(str(release), destination)
    return {'output': str(destination), 'validation': validation, **record}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ed-omics', required=True, type=Path)
    parser.add_argument('--cohortome', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'dist')
    args = parser.parse_args()
    sys.path[:0] = [str(args.cohortome.resolve()), str(args.ed_omics.resolve())]
    from ed_omics.public_data import ibd_metadata, read_counts
    from app.dataset_validation import validate_package
    print(json.dumps(build(args.source.resolve(), args.output.resolve(), args.version,
                           ibd_metadata, read_counts, validate_package), indent=2))


if __name__ == '__main__':
    main()
