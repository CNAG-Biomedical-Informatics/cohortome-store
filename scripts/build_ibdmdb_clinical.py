"""Prepare IBDMDB clinical snapshots using reviewed Convert-Pheno mappings."""
import argparse
from collections import defaultdict
import csv
import json
import hashlib
from pathlib import Path
import subprocess
from urllib.parse import quote

MAPPED = ['sex', 'diagnosis', 'CRP (mg/L)', 'ESR (mm/hr)']


def prepare(source, output, converter, mapping):
    output.mkdir(parents=True, exist_ok=False)
    with source.open() as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        rows = [r for r in reader if r['data_type'] in {'metabolomics', 'proteomics', 'serology'}]
    groups = defaultdict(list)
    for row in rows:
        key = (row['Participant ID'], row['visit_num'], row['week_num'])
        if not all(key):
            raise ValueError('Imported modality row lacks patient/visit/week identity')
        groups[key].append(row)
    snapshots, input_rows = {}, []
    for (patient, visit, week), source_rows in sorted(groups.items()):
        patient_id = 'IBDMDB-' + quote(patient, safe='')
        visit_id = 'visit_' + quote(visit, safe='') + '_week_' + quote(week, safe='')
        record_id = patient_id + ':' + visit_id
        mapped = {}
        for field in MAPPED:
            values = {r[field] for r in source_rows if r[field].strip()}
            if len(values) > 1:
                raise ValueError(f'Conflicting values within patient/visit/week: {field}')
            mapped[field] = next(iter(values), '')
        input_rows.append({'snapshot_id': record_id, 'Participant ID': patient, **mapped})
        snapshots[record_id] = dict(
            patient_id=patient_id,
            info=dict(visit_id=visit_id, source_participant_id=patient, source_visit_num=visit,
                      week_from_baseline=float(week), days_from_baseline=float(week) * 7,
                      source_sample_ids=sorted({r['External ID'] for r in source_rows}),
                      study_group={'CD': 'Crohn disease', 'UC': 'Ulcerative colitis',
                                   'nonIBD': 'Non-IBD comparison group'}[mapped['diagnosis']],
                      source_metadata=[{k: v for k, v in r.items() if v.strip()} for r in source_rows]))
    input_path = output / 'clinical.csv'
    with input_path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['snapshot_id', 'Participant ID', *MAPPED])
        writer.writeheader()
        writer.writerows(input_rows)
    # Keep logs on disk: converter diagnostics may contain source values.
    with (output / 'converter.log').open('w') as log:
        subprocess.run([str(converter), '-icsv', str(input_path), '--separator', ',',
                        '--mapping-file', str(mapping), '--search', 'exact', '--no-source-info',
                        '--term-audit', str(output / 'terminology.tsv'),
                        '-obff', str(output / 'converted.json')], stdout=log, stderr=log, check=True)
    converted = json.loads((output / 'converted.json').read_text())
    if len(converted) != len(snapshots) or {r['id'] for r in converted} != set(snapshots):
        raise ValueError('Conversion dropped or duplicated snapshot identities')
    expected = {r['snapshot_id']: r for r in input_rows}
    concepts = {'NCIT:C64548': 'CRP (mg/L)', 'NCIT:C74611': 'ESR (mm/hr)'}
    records = []
    for record in converted:
        # Only these fields were mapped. Do not carry converter default onset,
        # severity, stage, date or reference range into clinical observations.
        diseases = [{'diseaseCode': d['diseaseCode']} for d in record.get('diseases', [])]
        measures = []
        for measure in record.get('measures', []):
            code = measure['assayCode']['id']
            quantity = measure['measurementValue']['quantity']
            if code not in concepts or float(quantity['value']) != float(expected[record['id']][concepts[code]]):
                raise ValueError('Converted measurement differs from its source')
            measures.append(dict(assayCode=measure['assayCode'],
                                 measurementValue={'quantity': {k: quantity[k] for k in ['value', 'unit']}}))
        expected_count = sum(bool(expected[record['id']][field]) for field in concepts.values())
        if len(measures) != expected_count:
            raise ValueError('Missing converted measurements')
        records.append(dict(id=record['id'], sex=record['sex'], diseases=diseases,
                            measures=measures, **snapshots[record['id']]))
    (output / 'individuals.json').write_text(json.dumps(records, indent=2))
    (output / 'clinical.yaml').write_bytes(mapping.read_bytes())
    audit = dict(source_rows=len(rows), snapshots=len(records), source_columns=columns,
                 mapping_sha256=hashlib.sha256(mapping.read_bytes()).hexdigest(),
                 metadata_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                 converter_version=subprocess.check_output([str(converter), '--version'], text=True).strip().split('Version')[-1].strip(),
                 measures=sum(len(r['measures']) for r in records),
                 structured_fields=MAPPED,
                 other_fields='Retained under info.source_metadata, not yet structurally mapped',
                 grouping=['Participant ID', 'visit_num', 'week_num'],
                 missing='Empty source cells omitted; no imputation or baseline propagation')
    (output / 'mapping-audit.json').write_text(json.dumps(audit, indent=2))
    print(json.dumps({k: audit[k] for k in ['source_rows', 'snapshots', 'measures']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--convert-pheno', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.output, args.convert_pheno, args.mapping)
