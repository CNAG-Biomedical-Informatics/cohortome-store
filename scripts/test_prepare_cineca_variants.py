import csv
import gzip
import json

import pytest

from prepare_cineca_variants import genotype, prepare


@pytest.mark.parametrize('gt,expected', [
    ('0/0', ('called', 0, 2, False)), ('0|1', ('called', 1, 2, True)),
    ('1', ('called', 1, 1, False)), ('1/1', ('called', 2, 2, False)),
    ('./.', ('missing', '', 2, False)), ('.', ('missing', '', '', False)),
    ('0/.', ('partial', '', 2, False)), ('1|.', ('partial', '', 2, True)),
])
def test_genotype(gt, expected):
    assert genotype(gt) == expected


@pytest.mark.parametrize('gt', ['0/2', '', '10', '0/1|1', 'NA'])
def test_invalid_genotype(gt):
    with pytest.raises(ValueError):
        genotype(gt)


def make_inputs(tmp_path, duplicate=False):
    package = tmp_path / 'package'
    (package / 'clinical').mkdir(parents=True)
    (package / 'clinical/individuals.json').write_text(json.dumps([{'id': 'P1'}, {'id': 'P2'}]))
    (package / 'biosamples.json').write_text(json.dumps([
        {'id': 'S1', 'individualId': 'P1'}, {'id': 'S2', 'individualId': 'P2'}]))
    path = tmp_path / 'input.vcf.gz'
    header = '##reference=hs37d5.fa.gz\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\tS2\n'
    info = 'CLINVAR_CLNSIG=Pathogenic;CLINVAR_CLNREVSTAT=criteria_provided,_single_submitter;CLINVAR_CLNDN=example;CLINVAR_CLNDISDB=MedGen:example;ANN=A|missense_variant|MODERATE|EXAMPLE;COSMIC_GENE=not_exported;dbNSFP_test=not_exported'
    row = f'22\t100\t.\tG\tA\t.\tPASS\t{info}\tGT\t0|1\t./.\n'
    other = '22\t200\t.\tG\tA\t.\tPASS\tCLINVAR_CLNSIG=Conflicting_classifications_of_pathogenicity;CLINVAR_CLNREVSTAT=criteria_provided,_conflicting_classifications\tGT\t0/0\t0/1\n'
    other += '22\t300\t.\tG\tA\t.\tPASS\tCLINVAR_CLNSIG=Benign;CLINVAR_CLNREVSTAT=criteria_provided,_single_submitter\tGT\t0/0\t0/0\n'
    other += '22\t400\t.\tG\tA\t.\tPASS\tCLINVAR_CLNSIG=Uncertain_significance;CLINVAR_CLNREVSTAT=criteria_provided,_single_submitter\tGT\t0/.\t0/1\n'
    other += '22\t500\t.\tG\tA\t.\tPASS\tCLINVAR_CLNSIG=.\tGT\t0/0\t0/1\n'
    with gzip.open(path, 'wt') as handle:
        handle.write(header + row + (row if duplicate else other))
    return path, package


def test_extract_and_preserve_annotations(tmp_path):
    vcf, package = make_inputs(tmp_path)
    output = tmp_path / 'panel'
    report = prepare(vcf, package, output, 'test-snapshot')
    assert report['selected_variants'] == 1 and report['samples'] == 2
    assert report['carrier_calls'] == 1
    assert report['genotype_call_states'] == {'called': 1, 'missing': 1}
    assert report['outside_classification_panel'] == 4
    with (output / 'variants.tsv').open() as handle:
        row = next(csv.DictReader(handle, delimiter='\t'))
    assert row['CLINVAR_CLNDISDB'] == 'MedGen:example'
    assert row['CLINVAR_CLNREVSTAT'] == 'criteria_provided,_single_submitter'
    assert 'COSMIC' not in (output / 'variants.tsv').read_text()
    assert 'dbNSFP' not in (output / 'variants.tsv').read_text()
    with gzip.open(output / 'genotypes.tsv.gz', 'rt') as handle:
        calls = list(csv.DictReader(handle, delimiter='\t'))
    assert calls[0]['GT'] == '0|1' and calls[1]['alt_dosage'] == ''
    with pytest.raises(ValueError, match='Output exists'):
        prepare(vcf, package, output, 'test-snapshot')


def test_duplicate_fails_without_publishing_partial_output(tmp_path):
    vcf, package = make_inputs(tmp_path, duplicate=True)
    output = tmp_path / 'panel'
    with pytest.raises(ValueError, match='Duplicate selected variant'):
        prepare(vcf, package, output, 'test-snapshot')
    assert not output.exists()
