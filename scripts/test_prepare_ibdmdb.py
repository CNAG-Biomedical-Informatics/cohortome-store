import gzip
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from app.dataset_validation import validate_package
from prepare_ibdmdb import FILES, SEROLOGY, biom_matrix, link_samples, prepare


class ConversionTests(unittest.TestCase):
    def payload(self):
        return {'rows': [{'id': 'f1'}, {'id': 'f2'}],
                'columns': [{'id': 'stool1'}], 'shape': [2, 1],
                'matrix_type': 'sparse', 'data': [[0, 0, 3.25]]}

    def test_sparse_zeros_and_invalid_coordinates(self):
        payload = self.payload()
        self.assertEqual(biom_matrix(payload).iloc[:, 0].tolist(), [3.25, 0])
        payload['data'].append([0, 0, 4])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            biom_matrix(payload)

    def test_shared_specimen_separate_serum_and_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = pd.DataFrame([
                {'External ID': sample, 'Participant ID': 'P1', 'data_type': modality,
                 'week_num': '2', 'visit_num': '1', 'diagnosis': 'CD'}
                for modality, sample in [('metabolomics', 'stool1'),
                                         ('proteomics', 'stool1'), ('serology', 'serum1')]])
            metadata.to_csv(root / FILES['metadata'], index=False)
            with gzip.open(root / FILES['metabolomics'], 'wt') as handle:
                json.dump(self.payload(), handle)
            pd.DataFrame({'stool1': [7]}, index=['protein1']).to_csv(
                root / FILES['proteomics'], sep='\t')
            pd.DataFrame({'serum1': range(5), '220948': range(5)}, index=SEROLOGY).to_csv(
                root / FILES['serology'], sep='\t')
            counts = prepare(root, root / 'package')
            report = validate_package(root / 'package')
            self.assertEqual(report['patients'], 1)
            self.assertEqual(report['clinical_records'], 2)
            self.assertEqual(counts['serology']['samples'], 1)
            records = json.loads((root / 'package/clinical/records.json').read_text())
            self.assertEqual(records[0]['info']['days_from_baseline'], 14)
            exclusions = json.loads((root / 'package/exclusions.json').read_text())
            self.assertEqual(exclusions[0]['source_sample_id'], '220948')
            with self.assertRaisesRegex(ValueError, 'Unexpected unlinked'):
                link_samples(metadata, 'serology', ['unreviewed'])
            clinical = root / 'enriched.json'
            clinical.write_text(json.dumps([{
                'id': 'IBDMDB-P1:visit_1_week_2', 'patient_id': 'IBDMDB-P1',
                'info': {'visit_id': 'visit_1_week_2',
                         'source_sample_ids': ['stool1', 'serum1'], 'days_from_baseline': 14},
                'measures': [{'assayCode': {'id': 'TEST:1', 'label': 'Test'},
                              'measurementValue': {'quantity': {'value': 0}}}],
            }]))
            prepare(root, root / 'enriched-package', clinical)
            enriched_report = validate_package(root / 'enriched-package')
            self.assertEqual(enriched_report['clinical_records'], 1)
            linked = pd.read_csv(root / 'enriched-package/assays/serology_samples.tsv', sep='\t')
            self.assertEqual(linked.iloc[0]['visit_id'], 'visit_1_week_2')
            enriched_records = json.loads((root / 'enriched-package/clinical/records.json').read_text())
            self.assertNotIn('visit_id', enriched_records[0])
            self.assertEqual(enriched_records[0]['info']['visit_id'], 'visit_1_week_2')
            self.assertEqual(enriched_records[0]['measures'][0]['measurementValue']['quantity']['value'], 0)


if __name__ == '__main__':
    unittest.main()
