#!/usr/bin/env python3
"""Join and verify every downloaded artifact; no dependencies beyond Python 3."""
import hashlib
import json
from pathlib import Path
import sys

folder = Path(sys.argv[1] if len(sys.argv) > 1 else 'downloads').resolve()
manifests = sorted(folder.glob('*.manifest.json'))
if not manifests:
    raise SystemExit('No artifact manifests found in ' + str(folder))
for path in manifests:
    manifest = json.loads(path.read_text(encoding='utf-8'))
    filename = manifest['filename']
    if Path(filename).name != filename:
        raise SystemExit('Invalid filename in manifest')
    output = folder / filename
    temporary = folder / (filename + '.assembling')
    full = hashlib.sha256()
    total = 0
    try:
        with temporary.open('wb') as dst:
            for part in manifest['parts']:
                if Path(part['name']).name != part['name']:
                    raise ValueError('Invalid part filename')
                digest = hashlib.sha256()
                count = 0
                with (folder / part['name']).open('rb') as src:
                    while chunk := src.read(8 * 1024 * 1024):
                        digest.update(chunk)
                        full.update(chunk)
                        dst.write(chunk)
                        count += len(chunk)
                if count != part['size'] or digest.hexdigest() != part['sha256']:
                    raise ValueError('Checksum mismatch: ' + part['name'])
                total += count
        if total != manifest['size'] or full.hexdigest() != manifest['sha256']:
            raise ValueError('Full-file checksum mismatch: ' + filename)
        temporary.replace(output)
        print('VERIFIED', filename, total, manifest['sha256'])
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
