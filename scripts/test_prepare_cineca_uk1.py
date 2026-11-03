import json
from pathlib import Path
import zipfile

import pytest

from prepare_cineca_uk1 import build, digest


def test_package_preserves_sources_and_rejects_overwrite(tmp_path):
    source = tmp_path / 'source'
    (source / 'bff').mkdir(parents=True)
    (source / 'README.md').write_text('Invented test data; not CINECA source records.\n')
    (source / 'bff/individuals.json').write_text(json.dumps([{'id': 'P1'}]))
    (source / 'bff/biosamples.json').write_text(json.dumps([
        {'id': 'B1', 'individualId': 'P1',
         'sampleOriginType': {'id': 'UBERON:0000178', 'label': 'blood'}}]))
    cohortome = Path(__file__).resolve().parents[2] / 'cohortome'
    output = tmp_path / 'output'
    result = build(source, cohortome, output)
    assert result['patients'] == result['biosamples'] == 1
    package = output / 'cineca-uk1-demo'
    assert digest(source / 'bff/individuals.json') == digest(package / 'clinical/individuals.json')
    assert digest(source / 'bff/biosamples.json') == digest(package / 'biosamples.json')
    resource = json.loads((package / 'resource.json').read_text())
    assert all(digest(package / name) == expected for name, expected in resource['files_sha256'].items())
    with zipfile.ZipFile(next(output.glob('*.zip'))) as archive:
        assert 'cineca-uk1-demo/biosamples.json' in archive.namelist()
    with pytest.raises(ValueError, match='Output exists'):
        build(source, cohortome, output)
    second = tmp_path / 'second'
    build(source, cohortome, second)
    assert digest(next(output.glob('*.zip'))) == digest(next(second.glob('*.zip')))
