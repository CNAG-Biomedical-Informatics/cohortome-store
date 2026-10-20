import csv
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from app.dataset_validation import validate_package
from prepare_gse42296 import prepare


class ConversionTests(unittest.TestCase):
    def fixture(self, root):
        rows = []
        for disease in ["Crohn's disease", 'Rheumatoid arthritis']:
            for day in [0, 2]:
                rows.append({'sample_id': 'GSM' + str(len(rows)), 'subject': '1',
                    'response': 'R - responder', 'treatment': 'Before treatment' if day == 0 else 'infliximab',
                    'time': 'week ' + str(day), 'disease state': disease, 'cell type': 'PBMC'})
        frame = pd.DataFrame(rows)
        frame.to_csv(root / 'metadata.tsv', sep='\t', index=False)
        np.savez(root / 'expression.npz', samples=frame.sample_id.to_numpy(dtype=str)[::-1],
                 probes=np.array(['123', '456']), expression=np.array([[4, 40], [3, 30], [2, 20], [1, 10]], dtype='float32'))
        return frame

    def test_alignment_disease_scoped_ids_and_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            prepare(root, root / 'package')
            report = validate_package(root / 'package')
            self.assertEqual(report['patients'], 2)
            self.assertEqual(report['clinical_records'], 4)
            with (root / 'package/assays/expression.csv').open() as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[1][1:], ['1.0', '2.0', '3.0', '4.0'])

    def test_duplicate_visit_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = self.fixture(root)
            frame.loc[1, 'time'] = 'week 0'
            frame.to_csv(root / 'metadata.tsv', sep='\t', index=False)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                prepare(root, root / 'package')

    def test_incomplete_pair_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = self.fixture(root)
            frame.iloc[1:].to_csv(root / 'metadata.tsv', sep='\t', index=False)
            with self.assertRaisesRegex(ValueError, 'complete paired'):
                prepare(root, root / 'package')


if __name__ == '__main__':
    unittest.main()
