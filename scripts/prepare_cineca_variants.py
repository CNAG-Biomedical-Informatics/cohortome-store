"""Extract a compact ClinVar P/LP chr22 panel from the annotated CINECA VCF."""
import argparse
from collections import Counter
import csv
import gzip
import io
from contextlib import contextmanager
from functools import lru_cache
import json
from pathlib import Path
import re
import shutil
import tempfile

from build_synthetic import write_json
from prepare_cineca_uk1 import digest

SELECTED = {'Pathogenic', 'Likely_pathogenic', 'Pathogenic/Likely_pathogenic'}
CLINVAR = ['ALLELEID', 'CLNSIG', 'CLNSIGCONF', 'CLNREVSTAT', 'CLNDN', 'CLNDISDB', 'CLNHGVS']
VARIANT_COLUMNS = ['variant_id', 'assembly', 'chromosome', 'position', 'ref', 'alt',
                   'vcf_id', 'filter', 'classification_source', 'classification_version'] + [
                       'CLINVAR_' + key for key in CLINVAR] + ['snpeff_ann']


@lru_cache(maxsize=128)
def genotype(gt):
    """Keep raw GT; partial calls have unknown dosage, not reference dosage."""
    if not re.fullmatch(r'[01.]+(?:[/|][01.]+)*', gt):
        raise ValueError('Selected biallelic record has an unsupported genotype')
    alleles = re.split(r'[/|]', gt)
    if any(a not in {'0', '1', '.'} for a in alleles) or ('/' in gt and '|' in gt):
        raise ValueError('Selected biallelic record has an unsupported genotype')
    state = 'missing' if all(a == '.' for a in alleles) else 'partial' if '.' in alleles else 'called'
    dosage = sum(a == '1' for a in alleles) if state == 'called' else ''
    return state, dosage, '' if gt == '.' else len(alleles), '|' in gt


@contextmanager
def compressed_table(path):
    # Stable gzip header; compress the complete grid rather than omitting calls.
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', compresslevel=1, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding='utf-8', newline='') as text:
                yield text


def prepare(vcf, package, output, clinvar_version):
    vcf, package, output = map(lambda p: Path(p).resolve(), (vcf, package, output))
    if output.exists():
        raise ValueError('Output exists; choose a new directory')
    if not clinvar_version.strip():
        raise ValueError('Declare the ClinVar annotation snapshot')
    biosamples = json.loads((package / 'biosamples.json').read_text())
    links = {row['id']: row['individualId'] for row in biosamples}
    if len(links) != len(biosamples):
        raise ValueError('Duplicate biosample identifiers')
    patients = {r['id'] for r in json.loads((package / 'clinical/individuals.json').read_text())}
    if not set(links.values()) <= patients:
        raise ValueError('Unresolved biosample patient links')
    stats, classifications, states = Counter(), Counter(), Counter()
    seen, samples, reference, snpeff = set(), None, '', ''
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cineca-variants-', dir=output.parent) as temp:
        work = Path(temp) / 'panel'
        work.mkdir()
        with (work / 'variants.tsv').open('w', newline='') as variants, compressed_table(work / 'genotypes.tsv.gz') as calls:
            vw, gw = csv.writer(variants, delimiter='\t'), csv.writer(calls, delimiter='\t')
            vw.writerow(VARIANT_COLUMNS)
            gw.writerow(['variant_id', 'sample_id', 'GT', 'call_status', 'alt_dosage', 'ploidy', 'phased'])
            with gzip.open(vcf, 'rt') as source:
                for line in source:
                    if line.startswith('##reference='):
                        reference = line.strip().split('=', 1)[1]
                    if line.startswith('##SnpEffVersion='):
                        snpeff = line.strip().split('=', 1)[1]
                    if line.startswith('#CHROM\t'):
                        samples = line.rstrip('\r\n').split('\t')[9:]
                        if not samples or len(set(samples)) != len(samples) or set(samples) != set(links):
                            raise ValueError('VCF samples must match the declared CINECA biosamples exactly')
                        if 'hs37d5' not in reference:
                            raise ValueError('This recipe expects the CINECA GRCh37/hs37d5 reference')
                        continue
                    if line.startswith('#'):
                        continue
                    if samples is None:
                        raise ValueError('VCF sample header is missing')
                    stats['source_records'] += 1
                    fields = line.rstrip('\r\n').split('\t', 9)
                    if len(fields) != 10:
                        raise ValueError('Malformed VCF row')
                    chrom, pos, vid, ref, alt, qual, filt, info, fmt, values = fields
                    if chrom.removeprefix('chr') != '22':
                        stats['outside_chr22'] += 1
                        continue
                    annotation = dict(part.split('=', 1) for part in info.split(';') if '=' in part)
                    classification = annotation.get('CLINVAR_CLNSIG', '')
                    if classification and classification != '.':
                        classifications[classification] += 1
                    if classification not in SELECTED:
                        stats['outside_classification_panel'] += 1
                        continue
                    if filt != 'PASS':
                        stats['nonpass_selected_classification'] += 1
                        continue
                    if not re.fullmatch('[ACGTN]+', ref) or not re.fullmatch('[ACGTN]+', alt) or not pos.isdigit() or int(pos) < 1:
                        raise ValueError('Normalize selected variants to biallelic sequence alleles first')
                    key = f'GRCh37:22:{int(pos)}:{ref}:{alt}'
                    if key in seen:
                        raise ValueError('Duplicate selected variant')
                    seen.add(key)
                    if not annotation.get('CLINVAR_CLNREVSTAT'):
                        raise ValueError('Selected variant lacks ClinVar review status')
                    formats = fmt.split(':')
                    if formats.count('GT') != 1:
                        raise ValueError('Selected variant requires a GT field')
                    gt_index = formats.index('GT')
                    sample_values = values.split('\t')
                    if len(sample_values) != len(samples):
                        raise ValueError('Selected variant sample count differs from header')
                    vw.writerow([key, 'GRCh37', '22', pos, ref, alt, vid, filt, 'ClinVar', clinvar_version] +
                                [annotation.get('CLINVAR_' + k, '') for k in CLINVAR] + [annotation.get('ANN', '')])
                    for sid, value in zip(samples, sample_values):
                        parts = value.split(':')
                        if len(parts) <= gt_index:
                            raise ValueError('Selected variant is missing a sample GT field')
                        gt = parts[gt_index]
                        state, dosage, ploidy, phased = genotype(gt)
                        states[state] += 1
                        if state == 'called' and dosage > 0:
                            stats['carrier_calls'] += 1
                        gw.writerow([key, sid, gt, state, dosage, ploidy, str(phased).lower()])
            if not seen:
                raise ValueError('No variants matched the panel')
        with (work / 'samples.tsv').open('w', newline='') as handle:
            writer = csv.writer(handle, delimiter='\t')
            writer.writerow(['sample_id', 'patient_id', 'biosample_id'])
            writer.writerows((sid, links[sid], sid) for sid in samples)
        report = dict(stats, selected_variants=len(seen), samples=len(samples),
                      classification_counts=dict(classifications), genotype_call_states=dict(states))
        write_json(work / 'preparation.json', {
            'recipe_version': '0.1.0', 'format_version': 2,
            'status': 'offline intermediate; not an app import format yet',
            'source_vcf_sha256': digest(vcf), 'biosamples_sha256': digest(package / 'biosamples.json'),
            'recipe_sha256': digest(Path(__file__)), 'assembly': 'GRCh37', 'reference': reference,
            'snpeff_version': snpeff, 'clinvar_version': clinvar_version,
            'selection': {'chromosome': '22', 'filter': 'PASS', 'CLINVAR_CLNSIG_exact': sorted(SELECTED)},
            'interpretation': 'ClinVar germline classifications, not independently computed ACMG classifications or patient diagnoses.',
            'missing_calls': 'Raw GT retained. Missing or partial calls have empty dosage; they are not reference calls.',
            'annotations': 'ClinVar fields and SnpEff ANN retained verbatim; no COSMIC or dbNSFP output.',
            'redistribution_review': 'pending', 'counts': report,
            'genotype_storage': 'gzip-compressed TSV; complete selected variant-by-sample grid',
            'files_sha256': {p.name: digest(p) for p in sorted(work.iterdir()) if p.is_file()}})
        shutil.move(str(work), output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vcf', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clinvar-version', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.vcf, args.package, args.output, args.clinvar_version), indent=2))
