from build_ibdmdb_clarids import subjects
import pytest


def record(pid, group='Non-IBD comparison group'):
    return {'patient_id': pid, 'sex': {'label': 'Female'},
            'info': {'study_group': group}, 'diseases': []}


def test_control_convention_and_stable_numbers():
    data = [record('b'), record('b'), record('a', 'Crohn disease')]
    rows = subjects(data, [{'unique_id': 'b', 'subject_id': '42'}])
    assert len(rows) == 2
    assert rows[0]['subject_id'] == 43
    assert rows[0]['condition'] == 'K50.9'
    assert rows[1]['subject_id'] == 42
    assert rows[1]['condition'] == 'Z00.00'
    assert rows[1]['type'] == 'Control'
    assert all(r['age_group'] == 'Not Available' for r in rows)
    assert all(r['diseases'] == [] for r in data)


def test_conflicting_snapshots_rejected():
    with pytest.raises(ValueError, match='Conflicting'):
        subjects([record('a'), record('a', 'Crohn disease')])
