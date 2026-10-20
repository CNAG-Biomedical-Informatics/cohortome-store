"""Audit processed IBDMDB sample linkage; report aggregates, not source records."""
import argparse
import gzip
import itertools
import json
from pathlib import Path

import pandas as pd

from prepare_gse191328 import sha256


def audit(root):
    paths = {name: root / filename for name, filename in {
        'metadata': 'ibdmdb-metadata.csv', 'metabolomics': 'ibdmdb-metabolomics.biom.gz',
        'proteomics': 'ibdmdb-proteomics.tsv.gz', 'serology': 'ibdmdb-serology.tsv'}.items()}
    meta = pd.read_csv(paths['metadata'], dtype=str, keep_default_na=False)
    protein = pd.read_csv(paths['proteomics'], sep='\t', index_col=0)
    serum = pd.read_csv(paths['serology'], sep='\t', index_col=0)
    with gzip.open(paths['metabolomics'], 'rt') as handle:
        metabolites = json.load(handle)
    if metabolites['shape'] != [len(metabolites['rows']), len(metabolites['columns'])]:
        raise ValueError('BIOM dimensions do not match row/column definitions')
    identifiers = {
        'metabolomics': [str(c['id']) for c in metabolites['columns']],
        'proteomics': list(protein.columns), 'serology': list(serum.columns)}
    features = {'metabolomics': len(metabolites['rows']),
                'proteomics': len(protein), 'serology': len(serum)}
    summary, people, specimens, visits = {}, {}, {}, {}
    for modality, columns in identifiers.items():
        rows = meta[meta.data_type == modality]
        duplicate = rows['External ID'].duplicated().sum()
        if duplicate:
            raise ValueError('Ambiguous within-modality metadata identifiers: ' + modality)
        matched = rows[rows['External ID'].isin(columns)]
        unmatched = set(columns) - set(rows['External ID'])
        people[modality] = set(matched['Participant ID']) - {''}
        specimens[modality] = set(matched['External ID'])
        visits[modality] = set(zip(matched['Participant ID'], matched['week_num'])) - {('', '')}
        # Missing weeks cannot establish matched time points.
        visits[modality] = {(p, w) for p, w in visits[modality] if p and w}
        summary[modality] = {
            'matrix_columns': len(columns), 'feature_or_metadata_rows': features[modality],
            'duplicate_matrix_columns': len(columns) - len(set(columns)),
            'exact_metadata_matches': len(matched), 'unmatched_columns': len(unmatched),
            'participants': len(people[modality]),
            'missing_participant_links': int(matched['Participant ID'].eq('').sum()),
            'missing_week': int(matched.week_num.eq('').sum()),
            'diagnosis_sample_counts': matched.diagnosis.value_counts().to_dict()}
        if modality == 'serology':
            summary[modality]['unmatched_all_empty_columns'] = sum(
                bool(serum[c].isna().all()) for c in unmatched)
            summary[modality]['unmatched_unnamed_columns'] = sum(
                c.startswith('Unnamed:') for c in unmatched)
    named = [r for r in metabolites['rows'] if str((r.get('metadata') or {}).get('Metabolite', '')).strip()
             not in {'', 'None', 'NA', 'nan', 'Unknown', 'unknown'}]
    summary['metabolomics']['rows_with_nonempty_metabolite_annotation'] = len(named)
    overlaps = []
    for size in (2, 3):
        for group in itertools.combinations(identifiers, size):
            overlaps.append({'modalities': list(group),
                'participants': len(set.intersection(*(people[g] for g in group))),
                'exact_external_ids': len(set.intersection(*(specimens[g] for g in group))),
                'participant_week_labels': len(set.intersection(*(visits[g] for g in group)))})
    return {'audit_version': 1, 'metadata_rows': len(meta),
        'metadata_participants': meta.loc[meta['Participant ID'].ne(''), 'Participant ID'].nunique(),
        'source_files_sha256': {p.name: sha256(p) for p in paths.values()},
        'modalities': summary, 'overlaps': overlaps,
        'limitations': [
            'Metadata matching is exact by External ID within modality.',
            'Participant/week overlap is not proof of contemporaneous specimen collection.',
            'Serology contains administrative and categorical rows as well as numeric assays.',
            'Metabolite annotation presence does not establish chemical identification confidence.',
            'No matrix conversion, normalization, imputation or replicate collapsing performed.',
            'Redistribution review remains pending.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.source)
    payload = json.dumps(report, indent=2)
    with args.output.open('x') as handle:
        handle.write(payload + '\n')
    print(payload)
