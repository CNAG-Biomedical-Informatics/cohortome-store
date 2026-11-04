"""Add prepared subject/specimen labels to a copy of the CINECA demo package."""
import argparse
import csv
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

from build_synthetic import write_json
from prepare_cineca_uk1 import digest


def mappings():
    subject = dict(fields={
        'condition': {'source': 'info.clarid_condition'},
        'sex': {'source': 'sex.label', 'operations': ['normalize_sex']}},
        static_fields=dict(study='CINECA-UK1', type='Not Available',
                           sex='Not Available', age_group='Not Available'))
    specimen = dict(fields={
        'assay': {'source': 'info.clarid_assay'},
        'condition': {'source': 'info.clarid_condition'},
        'species': {'source': 'info.taxId', 'operations': [{'map_values': {'9606': 'Human'}}]},
        'tissue': {'source': 'sampleOriginType.id', 'operations': [
            {'map_values': {'UBERON:0000178': 'Blood'}}]}},
        static_fields=dict(project='CINECA-UK1', species='Not Available', tissue='Not Available',
                           sample_type='Not Available', assay='Not Available',
                           timepoint='Not Available', duration='P0N'))
    return subject, specimen


def clinical_condition(record):
    diseases = record.get('diseases') or []
    if not diseases:
        return 'R69'
    code = diseases[0]['diseaseCode']['id']
    if not code.startswith('ICD10:'):
        raise ValueError('Expected an ICD10 source condition')
    code = code[6:]
    # Source F3181 is ICD-10-CM F31.81; restore punctuation, not meaning.
    if re.fullmatch(r'[A-Z][0-9]{3,4}', code):
        code = code[:3] + '.' + code[3:]
    if not re.fullmatch(r'[A-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?', code):
        raise ValueError('Unsupported source condition syntax')
    return code


def subject_numbers(records):
    numbers, owners = {}, {}
    for record in records:
        identifier = record['id']
        match = re.fullmatch(r'(HG|NA)([0-9]+)', identifier)
        if not match or identifier in numbers:
            raise ValueError('Expected unique HG/NA individual IDs')
        number = int(match[2])
        if number in owners:
            raise ValueError('HG/NA numeric suffix collision')
        numbers[identifier], owners[number] = number, identifier
    return numbers


def write_csv(path, rows, delimiter=','):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=delimiter, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def assay_records(specimens, dna, rna):
    """Preserve supplied specimens; add explicit analytical records for RNA."""
    specimens, rna = deepcopy(specimens), deepcopy(rna)
    by_id = {r['id']: r for r in specimens}
    if len(by_id) != len(specimens):
        raise ValueError('Duplicate specimen IDs')
    assigned = set()
    for sample in dna:
        bid = sample.get('biosample_id')
        if bid not in by_id or by_id[bid]['individualId'] != sample['patient_id'] or bid in assigned:
            raise ValueError('Invalid or ambiguous DNA specimen linkage')
        assigned.add(bid)
        by_id[bid].setdefault('info', {}).update(
            clarid_assay='WGS', assay_source='variants/samples.tsv',
            assay_link_note='WGS analytical sample linked by the prepared dataset. Matching individual/sample IDs do not independently establish physical specimen identity.')
    for sample in rna:
        bid = sample['sample_id']
        if bid in by_id or sample.get('biosample_id'):
            raise ValueError('RNA specimen identity collision or pre-existing link')
        record = dict(id=bid, individualId=sample['patient_id'], info=dict(
            taxId=9606, clarid_assay='RNA_seq', record_kind='analytical_sample',
            source_sample_id=sample['source_sample_id'], material=sample.get('material', ''),
            assay_source='assays/transcriptomics/samples.tsv',
            specimen_note='GEUVADIS RNA-seq analytical sample, not asserted to be the supplied CINECA blood specimen.'))
        specimens.append(record)
        by_id[bid] = record
        sample['biosample_id'] = bid
    return specimens, rna


def encode(rows, entity, executable, codebook, directory):
    source = directory / (entity + '-input.csv')
    write_csv(source, rows)
    for fmt, column in [('human', 'clar_id'), ('stub', 'stub_id')]:
        target = directory / f'{entity}-{fmt}.csv'
        subprocess.run([str(executable), 'code', '--entity', entity, '--action', 'encode',
            '--format', fmt, '--codebook', str(codebook), '--sep', ',',
            '--infile', str(source), '--outfile', str(target)], check=True, capture_output=True)
        with target.open() as handle:
            encoded = {r['unique_id']: r[column] for r in csv.DictReader(handle)}
        for row in rows:
            row[column] = encoded[row['unique_id']]
    for fmt, column in [('human', 'clar_id'), ('stub', 'stub_id')]:
        target = directory / f'{entity}-{fmt}-decoded.csv'
        subprocess.run([str(executable), 'code', '--entity', entity, '--action', 'decode',
            '--format', fmt, '--codebook', str(codebook), '--sep', ',', '--with-condition-name',
            '--infile', str(directory / f'{entity}-{fmt}.csv'), '--outfile', str(target)],
            check=True, capture_output=True)
        with target.open() as handle:
            decoded = {r['unique_id']: r for r in csv.DictReader(handle)}
        for row in rows:
            item = decoded[row['unique_id']]
            if int(item['subject_id']) != int(row['subject_id']) or item['condition'] != row['condition']:
                raise ValueError('ClarID round-trip mismatch')
            if entity == 'biosample' and item['assay'] != row['assay']:
                raise ValueError('Assay round-trip mismatch')
            row['condition_name'] = item.get('condition_name', '')
    return rows


def build(package, output, cohortome, clarid_checkout, executable):
    package, output, cohortome, clarid_checkout, executable = [Path(p).resolve()
        for p in (package, output, cohortome, clarid_checkout, executable)]
    if output.exists():
        raise ValueError('Output exists; choose a new directory')
    version = subprocess.run([str(executable), '--version'], check=True, capture_output=True, text=True).stdout
    if version.strip().split()[-1] != '0.05':
        raise ValueError('Use ClarID-Tools 0.05')
    utility = clarid_checkout / 'utils/bff/bff2_clarid_in.py'
    spec = importlib.util.spec_from_file_location('bff_clarid', utility)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    resource = json.loads((package / 'resource.json').read_text())
    for name, expected in resource['files_sha256'].items():
        path = (package / name).resolve()
        if not path.is_relative_to(package) or digest(path) != expected:
            raise ValueError('Input checksum mismatch')
    sys.path.insert(0, str(cohortome))
    from app.dataset_validation import validate_package
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cineca-clarids-', dir=output.parent) as temp:
        work = Path(temp) / 'package'
        shutil.copytree(package, work)
        manifest = json.loads((work / 'manifest.json').read_text())
        if manifest.get('identifiers') or (work / 'identifiers').exists():
            raise ValueError('Package already has identifiers; preserve and reuse its subject map')
        folder = work / 'identifiers'
        folder.mkdir()
        codebook = yaml.safe_load((clarid_checkout / 'share/versions/0.04/clarid-codebook.yaml').read_text())
        if str(codebook['metadata']['version']) != '0.04':
            raise ValueError('Expected codebook 0.04')
        entry = dict(code='CINECA_UK1', stub_code='CUK', label='CINECA UK1', id='NCIT:C17998')
        for entity, field in [('subject', 'study'), ('biosample', 'project')]:
            codebook['entities'][entity][field]['CINECA-UK1'] = entry
        codebook['metadata']['local_version'] = 'CINECA-UK1-1'
        book = folder / 'clarid-codebook.yaml'
        book.write_text(yaml.safe_dump(codebook, sort_keys=False))
        subjects = json.loads((work / 'clinical/individuals.json').read_text())
        specimens = json.loads((work / 'biosamples.json').read_text())
        with (work / 'variants/samples.tsv').open() as handle:
            dna = list(csv.DictReader(handle, delimiter='\t'))
        with (work / 'assays/transcriptomics/samples.tsv').open() as handle:
            rna = list(csv.DictReader(handle, delimiter='\t'))
        specimens, rna = assay_records(specimens, dna, rna)
        write_json(work / 'biosamples.json', specimens)
        write_csv(work / 'assays/transcriptomics/samples.tsv', rna, delimiter='\t')
        conditions = {r['id']: clinical_condition(r) for r in subjects}
        for row in subjects:
            row.setdefault('info', {})['clarid_condition'] = conditions[row['id']]
        for row in specimens:
            row.setdefault('info', {})['clarid_condition'] = conditions[row['individualId']]
        subject_map, specimen_map = mappings()
        subject_rows = converter.prepare(subjects, subject_map, previous=subject_numbers(subjects), entity='subject')
        numbers = {r['unique_id']: r['subject_id'] for r in subject_rows}
        specimen_rows = converter.prepare(specimens, specimen_map, previous=numbers, entity='biosample')
        for entity, rows, mapping in [('subject', subject_rows, subject_map), ('biosample', specimen_rows, specimen_map)]:
            encode(rows, entity, executable, book, Path(temp))
            relative = f'identifiers/clarid_{entity}s.csv'
            write_csv(work / relative, rows)
            (folder / f'{entity}-mapping.yaml').write_text(yaml.safe_dump(mapping, sort_keys=False))
            manifest.setdefault('identifiers', {})[f'clarid_{entity}s'] = dict(
                entity=entity, file=relative, codebook_version='0.04', tools_version='0.05')
        write_json(work / 'manifest.json', manifest)
        validation = validate_package(work)
        write_json(work / 'provenance/validation.json', validation)
        write_json(work / 'provenance/clarid-preparation.json', dict(
            tools_version='0.05', codebook_version='0.04', local_codebook='CINECA-UK1-1',
            recipe_sha256=digest(Path(__file__)), converter_sha256=digest(utility),
            transforms_sha256=digest(clarid_checkout / 'utils/clarid_preprocessing/transforms.py'),
            source_resource_sha256=digest(package / 'resource.json'),
            subjects=len(subject_rows), biosamples=len(specimen_rows),
            condition_policy='First listed synthetic ICD10 code, not a primary diagnosis. R69 is a placeholder when absent, not an added BFF diagnosis. F3181 punctuation restored to F31.81.',
            missing_condition_count=sum(not r.get('diseases') for r in subjects),
            numbering='Original HG/NA numeric suffix; collisions rejected. The same map is reused for specimens.',
            assays=dict(WGS=len(dna), RNA_seq=len(rna)),
            limitations='Reference sample does not imply normal tissue. Age, case/control status, tissue status, timepoint and duration are not inferred. RNA records represent analytical samples, not the supplied blood specimens. WGS assignment follows prepared analytical links, not proof of physical specimen identity. Clinical BFF is unchanged; biosamples are augmented with assay provenance and RNA analytical records.'))
        resource['files_sha256'] = {p.relative_to(work).as_posix(): digest(p)
            for p in sorted(work.rglob('*')) if p.is_file() and p != work / 'resource.json'}
        write_json(work / 'resource.json', resource)
        shutil.move(str(work), output)
    return dict(subjects=len(subject_rows), biosamples=len(specimen_rows), valid=validation['valid'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'output', 'cohortome', 'clarid-checkout', 'executable'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.package, args.output, args.cohortome, args.clarid_checkout, args.executable)))
