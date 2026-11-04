import pytest

from prepare_cineca_clarids import clinical_condition, mappings, assay_records, subject_numbers


@pytest.mark.parametrize('source, expected', [
    ('ICD10:E10', 'E10'), ('ICD10:F3181', 'F31.81'), ('ICD10:M06.9', 'M06.9')])
def test_condition_preserves_meaning(source, expected):
    assert clinical_condition({'diseases': [{'diseaseCode': {'id': source}}]}) == expected


def test_no_diagnosis_is_not_called_healthy():
    assert clinical_condition({}) == 'R69'
    assert clinical_condition({'diseases': []}) == 'R69'


def test_first_listed_is_not_reordered():
    record = {'diseases': [{'diseaseCode': {'id': 'ICD10:J45'}}, {'diseaseCode': {'id': 'ICD10:E10'}}]}
    assert clinical_condition(record) == 'J45'
    assert len(record['diseases']) == 2


def test_no_specimen_status_inference():
    subject, specimen = mappings()
    assert subject['static_fields']['type'] == 'Not Available'
    assert subject['static_fields']['age_group'] == 'Not Available'
    assert specimen['static_fields']['sample_type'] == 'Not Available'
    assert specimen['static_fields']['assay'] == 'Not Available'
    assert specimen['static_fields']['duration'] == 'P0N'
    assert 'biosampleStatus' not in str(specimen)


def test_other_ontology_not_relabelled_icd():
    with pytest.raises(ValueError, match='ICD10'):
        clinical_condition({'diseases': [{'diseaseCode': {'id': 'MONDO:0000001'}}]})


def test_subject_numbers_retain_source_suffix():
    assert subject_numbers([{'id': 'HG00096'}, {'id': 'NA06984'}]) == {'HG00096': 96, 'NA06984': 6984}


@pytest.mark.parametrize('ids', [['HG00096', 'NA00096'], ['HG00096', 'HG00096'], ['other96']])
def test_subject_number_conflicts_fail(ids):
    with pytest.raises(ValueError):
        subject_numbers([{'id': identifier} for identifier in ids])


def test_assays_use_distinct_records_and_keep_source_ids():
    source = [{'id': 'HG00096', 'individualId': 'HG00096', 'info': {'taxId': 9606}}]
    dna = [{'sample_id': 'HG00096', 'patient_id': 'HG00096', 'biosample_id': 'HG00096'}]
    rna = [{'sample_id': 'HG00096:geuvadis-rna', 'patient_id': 'HG00096', 'source_sample_id': 'HG00096'}]
    records, links = assay_records(source, dna, rna)
    assert len(records) == 2
    assert records[0]['info']['clarid_assay'] == 'WGS'
    assert records[1]['info']['clarid_assay'] == 'RNA_seq'
    assert records[1]['individualId'] == records[0]['individualId']
    assert links[0]['biosample_id'] == 'HG00096:geuvadis-rna'
    assert 'sampleOriginType' not in records[1]
    assert 'biosample_id' not in rna[0]
    assert 'clarid_assay' not in source[0]['info']


def test_assay_identity_conflicts_fail():
    source = [{'id': 'P1', 'individualId': 'P1'}]
    with pytest.raises(ValueError, match='DNA'):
        assay_records(source, [{'patient_id': 'P2', 'biosample_id': 'P1'}], [])
    with pytest.raises(ValueError, match='collision'):
        assay_records(source, [], [{'sample_id': 'P1', 'patient_id': 'P1'}])
