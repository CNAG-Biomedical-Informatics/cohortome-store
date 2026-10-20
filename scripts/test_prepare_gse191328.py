import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np
import pandas as pd

from app.dataset_validation import validate_package
from prepare_gse191328 import build, clinical_and_samples
from verify_resource import verify


def fixture():
    return pd.DataFrame([
        {'patient': '1', 'cohort': cohort, 'patient_id': cohort + ':1',
         'sample_id': 'GSM' + str(i), 'diagnosis': 'CD', 'time point': visit,
         'time': time, 'treatment': 'Infliximab', 'remission at week 14': 'Remission'}
        for i, (cohort, visit, time) in enumerate([
            ('Discovery', 'baseline', 0.), ('Discovery', '4h', 4/24),
            ('Replication', 'baseline', 0.)])])


class ResourceTests(unittest.TestCase):
    def test_identity_and_future_endpoint(self):
        clinical, samples = clinical_and_samples(fixture())
        self.assertEqual(len({s['patient_id'] for s in samples}), 2)
        self.assertEqual(samples[0]['patient_id'], samples[1]['patient_id'])
        self.assertNotEqual(samples[0]['patient_id'], samples[2]['patient_id'])
        for record, sample in zip(clinical, samples):
            self.assertEqual(sample['sample_id'].split(':')[0], record['patient_id'])
            self.assertNotIn('event_date', record['info'])
            self.assertNotIn('measures', record)
        self.assertEqual(samples[1]['days_from_baseline'], 4/24)

    def test_reject_inconsistent_metadata(self):
        metadata = fixture()
        metadata.loc[1, 'remission at week 14'] = 'Non-remission'
        with self.assertRaisesRegex(ValueError, 'Inconsistent'):
            clinical_and_samples(metadata)

    def test_roundtrip_reproducible_checksum_and_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            (source / 'counts').mkdir(parents=True)
            (source / 'ed-GSE191328_series_matrix.txt.gz').write_bytes(b'fixture')
            (source / 'counts/count.txt.gz').write_bytes(b'fixture counts')
            def counts(*args):
                return np.array([[1., 2.], [3., 4.], [5., 6.]]), np.array(['ENSG000001', 'ENSG000002'])
            def run(output):
                return build(source, output, '0.1.0', lambda p: fixture(), counts, validate_package)
            first, second = run(root / 'first'), run(root / 'second')
            self.assertEqual(first['archive_sha256'], second['archive_sha256'])
            release = Path(first['output'])
            archive = release / first['archive']
            verify(release / 'release.json', archive)
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(root / 'unpacked')
            result = validate_package(root / 'unpacked/gse191328')
            self.assertEqual(result['patients'], 2)
            self.assertEqual(result['assay_sample_columns'], 3)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                run(root / 'first')
            payload = bytearray(archive.read_bytes())
            payload[-1] ^= 1
            archive.write_bytes(payload)
            with self.assertRaisesRegex(ValueError, 'checksum'):
                verify(release / 'release.json', archive)

    def test_fractional_counts_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'integers'):
                build(root, root / 'out', '1', lambda p: fixture(),
                      lambda *args: (np.array([[0.5], [1.], [2.]]), np.array(['ENSG000001'])),
                      validate_package)


if __name__ == '__main__':
    unittest.main()
