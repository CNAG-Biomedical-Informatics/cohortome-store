"""Convert public IBDMDB products without normalizing or joining distinct visits."""
import argparse
import gzip
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote
import zipfile

import numpy as np
import pandas as pd

from build_synthetic import write_json
from prepare_gse191328 import sha256

FILES = {'metadata': 'ibdmdb-metadata.csv', 'metabolomics': 'ibdmdb-metabolomics.biom.gz',
         'proteomics': 'ibdmdb-proteomics.tsv.gz', 'serology': 'ibdmdb-serology.tsv'}
SEROLOGY = ['IgA ASCA EU', 'IgG ASCA EU', 'OmpC. EU', 'Cbir1 EU', 'ANCA EU']
# Exact reviewed source column, not a general "drop unmatched" rule.
UNLINKED_SEROLOGY = {'220948'}
DIAGNOSES = {'CD': 'Crohn disease', 'UC': 'Ulcerative colitis', 'nonIBD': 'Non-IBD comparison group'}


def biom_matrix(payload):
    rows, cols = payload['rows'], payload['columns']
    shape = (len(rows), len(cols))
    if (list(shape) != payload['shape'] or payload['matrix_type'] != 'sparse'
            or len({r['id'] for r in rows}) != len(rows)
            or len({c['id'] for c in cols}) != len(cols)):
        raise ValueError('Invalid or unsupported BIOM dimensions/identifiers')
    matrix = np.zeros(shape, dtype=np.float64)
    seen = np.zeros(shape, dtype=bool)
    for r, c, value in payload['data']:
        if not isinstance(r, int) or not isinstance(c, int) or not (0 <= r < shape[0] and 0 <= c < shape[1]):
            raise ValueError('Invalid BIOM coordinate')
        if seen[r, c]:
            raise ValueError('Duplicate BIOM coordinate')
        seen[r, c] = True
        matrix[r, c] = np.nan if value is None else float(value)
    if np.isinf(matrix).any():
        raise ValueError('Infinite BIOM value')
    # BIOM 1.0 sparse entries omitted from data are zero, not missing.
    return pd.DataFrame(matrix, index=[r['id'] for r in rows], columns=[c['id'] for c in cols])


def link_samples(meta, modality, columns):
    rows = meta[meta.data_type == modality].copy()
    if rows['External ID'].duplicated().any() or len(set(columns)) != len(columns):
        raise ValueError('Duplicate sample identity')
    unknown = set(columns) - set(rows['External ID'])
    if unknown and (modality != 'serology' or unknown != UNLINKED_SEROLOGY):
        raise ValueError('Unexpected unlinked sample; review source metadata')
    rows = rows.set_index('External ID')
    samples = []
    for column in columns:
        if column in unknown:
            continue
        row = rows.loc[column]
        if not row['Participant ID'] or row['diagnosis'] not in DIAGNOSES:
            raise ValueError('Missing participant or unexpected diagnosis')
        week = float(row.week_num)
        if not np.isfinite(week):
            raise ValueError('Missing/nonfinite relative time')
        patient = 'IBDMDB-' + quote(row['Participant ID'], safe='')
        samples.append({'sample_id': patient + ':' + quote(column, safe=''),
            'patient_id': patient, 'source_sample_id': column,
            'source_participant_id': row['Participant ID'], 'diagnosis': row.diagnosis,
            'timepoint': 'week_' + format(week, 'g'), 'week_from_baseline': week,
            'days_from_baseline': week * 7, 'source_visit_num': row.visit_num,
            'specimen_type': 'serum' if modality == 'serology' else 'stool'})
    return samples, sorted(unknown)


def prepare(source, package, clinical_records=None):
    meta = pd.read_csv(source / FILES['metadata'], dtype=str, keep_default_na=False)
    records, assays, counts, exclusions = {}, [], {}, []
    enriched = json.loads(clinical_records.read_text()) if clinical_records else None
    snapshot_links = {}
    if enriched is not None:
        for record in enriched:
            for source_sample in record['info']['source_sample_ids']:
                key = (record['patient_id'], source_sample)
                if key in snapshot_links:
                    raise ValueError('Source sample links to multiple clinical snapshots')
                snapshot_links[key] = record['info']['visit_id']
    (package / 'clinical').mkdir(parents=True)
    (package / 'assays').mkdir()
    for modality in ('metabolomics', 'proteomics', 'serology'):
        annotation = None
        if modality == 'metabolomics':
            with gzip.open(source / FILES[modality], 'rt') as handle:
                payload = json.load(handle)
            frame = biom_matrix(payload)
            annotation = [{'feature_id': r['id'], **(r.get('metadata') or {})} for r in payload['rows']]
            del payload
        else:
            frame = pd.read_csv(source / FILES[modality], sep='\t', index_col=0)
            if modality == 'serology':
                # Preserve administrative/categorical annotations separately.
                frame.to_csv(package / 'assays/serology_source.tsv', sep='\t', index_label='source_row')
                frame = frame.loc[SEROLOGY].apply(pd.to_numeric, errors='raise')
        if frame.index.has_duplicates or frame.empty:
            raise ValueError('Duplicate/empty feature table')
        numeric = frame.to_numpy(dtype=float)
        if np.isinf(numeric).any():
            raise ValueError('Infinite matrix value')
        samples, unknown = link_samples(meta, modality, list(frame.columns))
        if enriched is not None:
            for sample in samples:
                sample['visit_id'] = snapshot_links[(sample['patient_id'], sample['source_sample_id'])]
        exclusions.extend({'modality': modality, 'source_sample_id': sample,
                           'reason': 'No exact match in published modality metadata'} for sample in unknown)
        frame = frame.loc[:, [s['source_sample_id'] for s in samples]]
        frame.columns = [s['sample_id'] for s in samples]
        frame.index = frame.index.map(str)
        frame.to_csv(package / f'assays/{modality}.csv', index_label='feature_id', na_rep='NA')
        pd.DataFrame(samples).to_csv(package / f'assays/{modality}_samples.tsv', sep='\t', index=False)
        if annotation:
            pd.DataFrame(annotation).to_csv(package / 'assays/metabolomics_features.tsv', sep='\t', index=False)
        for sample in samples:
            key = sample['sample_id']
            info = {k: sample[k] for k in ['source_sample_id', 'source_participant_id',
                'week_from_baseline', 'days_from_baseline', 'source_visit_num', 'specimen_type']}
            record = {'id': key, 'patient_id': sample['patient_id'],
                'diseases': [] if sample['diagnosis'] == 'nonIBD' else [
                    {'diseaseCode': {'id': 'IBDMDB:' + sample['diagnosis'],
                                     'label': DIAGNOSES[sample['diagnosis']]}}],
                'info': {**info, 'visit_id': sample['source_sample_id'],
                         'study_group': DIAGNOSES[sample['diagnosis']]}}
            if key in records and records[key] != record:
                raise ValueError('Conflicting metadata for shared specimen')
            records[key] = record
        assays.append({'assay_id': 'ibdmdb_' + modality, 'label': {
            'metabolomics': 'Stool metabolite features (published values)',
            'proteomics': 'Stool metaproteomics (published values)',
            'serology': 'Serum antibody assays (ELISA units)'}[modality],
            'modality': modality, 'data_type': 'elisa_units' if modality == 'serology' else 'published_abundance',
            'level': 'sample', 'feature_namespace': 'ibdmdb_' + modality + '_feature',
            'feature_id_column': 'feature_id', 'sample_id_column': 'matrix_columns',
            'patient_id_column': 'patient_id', 'patient_linkage': 'sample_metadata_file',
            'sample_metadata_file': f'assays/{modality}_samples.tsv',
            'file': f'assays/{modality}.csv', 'feature_count': len(frame)})
        counts[modality] = {'samples': len(samples), 'features': len(frame),
                           'missing_values': int(frame.isna().sum().sum())}
        del frame, numeric
    patients = {}
    for record in records.values():
        group = record['info']['study_group']
        if record['patient_id'] in patients and patients[record['patient_id']] != group:
            raise ValueError('Conflicting patient diagnosis across specimens')
        patients[record['patient_id']] = group
    if enriched is not None:
        linked = {(record['patient_id'], record['info']['source_sample_id']) for record in records.values()}
        if set(snapshot_links) != linked:
            raise ValueError('Enriched clinical sample links differ from packaged assay samples')
        records = {record['id']: record for record in enriched}
        if len(records) != len(enriched):
            raise ValueError('Duplicate enriched clinical record IDs')
    write_json(package / 'clinical/records.json', list(records.values()))
    write_json(package / 'manifest.json', {'schema_version': 1,
        'name': 'IBDMDB processed stool and serum multi-omics', 'study_design': 'longitudinal',
        'clinical': {'representation': 'snapshot'}})
    write_json(package / 'assays/manifest.json', {'version': 1, 'assays': assays})
    write_json(package / 'exclusions.json', exclusions)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cohortome', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--clinical-records', type=Path,
                        help='Validated Convert-Pheno clinical snapshots from build_ibdmdb_clinical.py')
    parser.add_argument('--clarid-directory', type=Path,
                        help='Validated subject sidecar and local codebook from build_ibdmdb_clarids.py')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'dist')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.version):
        parser.error('Invalid version')
    destination = args.output.resolve() / ('ibdmdb-' + args.version)
    if destination.exists():
        parser.error('Output exists; use a new version or output directory')
    sys.path.insert(0, str(args.cohortome.resolve()))
    from app.dataset_validation import validate_package
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ibdmdb-', dir=destination.parent) as temporary:
        release = Path(temporary) / 'release'
        package = release / 'ibdmdb'
        counts = prepare(args.source, package, args.clinical_records)
        if args.clarid_directory:
            identifiers = package / 'identifiers'
            identifiers.mkdir()
            for name in ('clarid_subjects.csv', 'clarid-codebook.yaml'):
                shutil.copyfile(args.clarid_directory / name, identifiers / name)
            manifest = json.loads((package / 'manifest.json').read_text())
            manifest['identifiers'] = {'clarid_subjects': {
                'entity': 'subject', 'file': 'identifiers/clarid_subjects.csv',
                'delimiter': ',', 'codebook_version': '0.04', 'tools_version': '0.04'}}
            write_json(package / 'manifest.json', manifest)
        if args.clinical_records:
            provenance = package / 'provenance'
            provenance.mkdir()
            for name in ('clinical.yaml', 'mapping-audit.json'):
                shutil.copyfile(args.clinical_records.parent / name, provenance / name)
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'datasets/ibdmdb/README.md',
                        package / 'README.md')
        validation = validate_package(package)
        resource = {'manifest_version': 1, 'dataset_id': 'ibdmdb', 'version': args.version,
            'schema_version': 1, 'distribution_status': 'local-preview', 'synthetic': False,
            'data_use_basis': 'Public HMP/iHMP products; consortium unrestricted-use statements',
            'redistribution_review': 'Final exact-product scope check before publication',
            'rights_sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6784865/',
                              'https://pmc.ncbi.nlm.nih.gov/articles/PMC7778886/'],
            'source_catalogue': 'https://ibdmdb.org/results',
            'source_files_sha256': {f: sha256(args.source / f) for f in FILES.values()},
            'counts': counts, 'validation': validation,
            'preparation': 'Published values preserved; full metabolomics/proteomics and five numeric serology rows.',
            'limitations': ['No normalization, biological QC, replicate collapse or nearest-visit matching.',
                'Sparse BIOM omitted entries become zero by format definition; zero is not proof of biological absence.',
                'Metabolite annotations are original BIOM annotations, not the 2021 update; unannotated features retained.',
                'One unlinked serology sample excluded from linked matrices, retained in auxiliary source table.',
                ('Clinical snapshots group exact patient, source visit and relative week; separate specimen links are retained.'
                 if args.clinical_records else 'Clinical snapshots represent specimens, not counts of distinct clinic visits.'),
                ('Sex, diagnoses, CRP and ESR are structurally mapped; other source fields remain in info.source_metadata.'
                 if args.clinical_records else 'Clinical mapping is limited to study group and linkage.'),
                'Relative weeks retained; calendar dates, doses and clinical measurements not inferred.',
                'Do not treat stool metaproteomics as a human protein panel.',
                'In-app registration and scientific analysis have not been verified.']}
        resource['files_sha256'] = {p.relative_to(package).as_posix(): sha256(p)
                                   for p in sorted(package.rglob('*')) if p.is_file()}
        if args.clinical_records:
            resource['clinical_mapping'] = {
                'input_sha256': sha256(args.clinical_records),
                'audit': 'provenance/mapping-audit.json',
                'mapping': 'provenance/clinical.yaml'}
        write_json(package / 'resource.json', resource)
        filename = destination.name + '.zip'
        with zipfile.ZipFile(release / filename, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            for path in sorted(package.rglob('*')):
                if path.is_file():
                    info = zipfile.ZipInfo('ibdmdb/' + path.relative_to(package).as_posix(), (1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with path.open('rb') as src, bundle.open(info, 'w') as dst:
                        shutil.copyfileobj(src, dst)
        entry = {k: resource[k] for k in ['manifest_version', 'dataset_id', 'version', 'schema_version',
                 'distribution_status', 'data_use_basis', 'redistribution_review']}
        entry.update(archive=filename, archive_sha256=sha256(release / filename),
                     archive_bytes=(release / filename).stat().st_size)
        write_json(release / 'release.json', entry)
        shutil.move(str(release), destination)
    print(json.dumps({'validation': validation, **entry}, indent=2))


if __name__ == '__main__':
    main()
