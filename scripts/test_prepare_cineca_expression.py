import csv
import gzip
import json

import pytest

from prepare_cineca_expression import convert


def inputs(tmp_path, rows):
    expression = tmp_path / 'expression.gz'
    with gzip.open(expression, 'wt') as handle:
        handle.write('TargetID\tGene_Symbol\tChr\tCoord\tP2\tOTHER\tP1\n' + rows)
    clinical = tmp_path / 'clinical.json'
    clinical.write_text(json.dumps([{'id': 'P1'}, {'id': 'P2'}, {'id': 'P3'}]))
    return expression, clinical


def test_exact_overlap_and_signed_values(tmp_path):
    expression, clinical = inputs(tmp_path, 'ENSG1.2\tENSG1\t22\t10\t-0.50\t99\t1.25\n')
    target = tmp_path / 'assay'
    result = convert(expression, clinical, target)
    assert result == dict(source_samples=3, matched_patients=2,
                          excluded_sample_ids=['OTHER'], genes=1, negative_values=1)
    with (target / 'expression.csv').open() as handle:
        rows = list(csv.reader(handle))
    assert rows == [['gene_id', 'P2:geuvadis-rna', 'P1:geuvadis-rna'], ['ENSG1.2', '-0.50', '1.25']]
    with (target / 'samples.tsv').open() as handle:
        samples = list(csv.DictReader(handle, delimiter='\t'))
    assert [r['patient_id'] for r in samples] == ['P2', 'P1']
    assert all('biosample_id' not in r for r in samples)


@pytest.mark.parametrize('rows', [
    'ENSG1\tA\t22\t10\tnan\t1\t2\n',
    'ENSG1\tA\t22\t10\t1\t2\n',
    'ENSG1\tA\t22\t10\t1\t2\t3\nENSG1\tA\t22\t10\t1\t2\t3\n',
])
def test_bad_expression_rejected(tmp_path, rows):
    expression, clinical = inputs(tmp_path, rows)
    with pytest.raises(ValueError):
        convert(expression, clinical, tmp_path / 'assay')
