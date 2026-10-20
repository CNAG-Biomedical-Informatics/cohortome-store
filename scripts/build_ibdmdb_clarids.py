"""Generate subject ClarIDs from enriched IBDMDB snapshots; never edit BFF."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import tempfile
import yaml

FIELDS = ['unique_id', 'subject_id', 'study', 'type', 'condition', 'sex', 'age_group']
CONDITIONS = {'Crohn disease': 'K50.9', 'Ulcerative colitis': 'K51.9',
              'Non-IBD comparison group': 'Z00.00'}


def subjects(records, previous=()):
    numbers = {r['unique_id']: int(r['subject_id']) for r in previous}
    if len(set(numbers.values())) != len(numbers) or any(n < 1 for n in numbers.values()):
        raise ValueError('Invalid previous subject-number mapping')
    patients = {}
    for record in records:
        value = (record['info']['study_group'], record['sex']['label'])
        pid = record['patient_id']
        if pid in patients and patients[pid] != value:
            raise ValueError('Conflicting subject group or sex across snapshots')
        patients[pid] = value
    next_id = max(numbers.values(), default=0) + 1
    rows = []
    for pid, (group, sex) in sorted(patients.items()):
        if pid not in numbers:
            numbers[pid] = next_id
            next_id += 1
        rows.append(dict(zip(FIELDS, [pid, numbers[pid], 'IBDMDB',
                    'Control' if group == 'Non-IBD comparison group' else 'Case',
                    CONDITIONS[group], sex, 'Not Available'])))
    return rows


def write_csv(path, rows, fields):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def build(clinical, output, executable, codebook, previous=None):
    vocabulary = yaml.safe_load(codebook.read_text())
    version = subprocess.check_output([str(executable), '--version'], text=True).strip()
    if str(vocabulary['metadata']['version']) != '0.04' or version.split()[-1] != '0.04':
        raise ValueError('Requires clarid-tools and codebook 0.04')
    prior = []
    if previous:
        with previous.open() as handle:
            prior = list(csv.DictReader(handle))
    rows = subjects(json.loads(clinical.read_text()), prior)
    output.mkdir(parents=True, exist_ok=False)
    vocabulary['entities']['subject']['study']['IBDMDB'] = dict(
        code='IBDMDB', stub_code='IBD', label='IBDMDB', id='NCIT:C17998')
    vocabulary['metadata']['local_version'] = 'IBDMDB-1'
    book = output / 'clarid-codebook.yaml'
    book.write_text(yaml.safe_dump(vocabulary, sort_keys=False))
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        source = directory / 'subjects.csv'
        write_csv(source, rows, FIELDS)
        for fmt, column in [('human', 'clar_id'), ('stub', 'stub_id')]:
            target = directory / f'{fmt}.csv'
            base = [str(executable), 'code', '--entity', 'subject', '--format', fmt,
                    '--codebook', str(book), '--sep', ',']
            subprocess.run(base + ['--action', 'encode', '--infile', str(source),
                                  '--outfile', str(target)], check=True, capture_output=True)
            with target.open() as handle:
                encoded = {r['unique_id']: r[column] for r in csv.DictReader(handle)}
            for row in rows:
                row[column] = encoded[row['unique_id']]
            decoded = directory / f'{fmt}-decoded.csv'
            # Decode only IDs: original fields cannot mask decoding failures.
            ids = directory / f'{fmt}-ids.csv'
            write_csv(ids, rows, ['unique_id', column])
            subprocess.run(base + ['--action', 'decode', '--infile', str(ids),
                                  '--outfile', str(decoded), '--with-condition-name'],
                           check=True, capture_output=True)
            with decoded.open() as handle:
                result = {r['unique_id']: r for r in csv.DictReader(handle)}
            for row in rows:
                recovered = result[row['unique_id']]
                for field in ['condition', 'type', 'sex', 'age_group', 'study']:
                    expected = 'IBD' if fmt == 'stub' and field == 'study' else row[field]
                    if recovered[field] != expected:
                        raise ValueError(f'{fmt} round-trip mismatch: {field}')
                if int(recovered['subject_id']) != row['subject_id']:
                    raise ValueError('Subject-number round-trip mismatch')
                row['condition_name'] = recovered['condition_name']
    write_csv(output / 'clarid_subjects.csv', rows, FIELDS + ['clar_id', 'stub_id', 'condition_name'])
    print(f'Validated {len(rows)} subject ClarIDs in human and stub formats')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ['clinical', 'output', 'clarid-tools', 'codebook']:
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--previous', type=Path, help='Previous release sidecar; preserves subject numbers')
    args = parser.parse_args()
    build(args.clinical, args.output, args.clarid_tools.resolve(), args.codebook, args.previous)
