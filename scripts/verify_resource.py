"""Verify an archive against a reviewed repository resource manifest."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(manifest, archive):
    entry = json.loads(manifest.read_text())
    if entry.get('manifest_version') != 1 or not entry.get('version'):
        raise ValueError('Unsupported or unversioned resource manifest')
    if archive.name != entry['archive'] or archive.stat().st_size != entry['archive_bytes']:
        raise ValueError('Archive filename or size mismatch')
    with archive.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    if digest != entry['archive_sha256']:
        raise ValueError('Archive checksum mismatch')
    return digest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    print('Verified SHA-256:', verify(args.manifest, args.archive))
