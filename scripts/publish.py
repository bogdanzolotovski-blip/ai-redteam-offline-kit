#!/usr/bin/env python3
"""Split artifacts below GitHub's 2 GiB limit; publish hashes and provenance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

streaming = sys.argv[1] == '--stdin'
source = Path(sys.argv[2] if streaming else sys.argv[1])
metadata_index = 3 if streaming else 2
metadata = json.loads(sys.argv[metadata_index]) if len(sys.argv) > metadata_index else {}
limit = 1900 * 1024 * 1024
full = hashlib.sha256()
parts = []
with (sys.stdin.buffer if streaming else source.open('rb')) as src:
    index = 0
    while True:
        first = src.read(8 * 1024 * 1024)
        if not first:
            break
        part = source.with_name(source.name + f'.part{index:03d}')
        digest = hashlib.sha256()
        size = 0
        with part.open('wb') as dst:
            chunk = first
            while chunk:
                dst.write(chunk)
                digest.update(chunk)
                full.update(chunk)
                size += len(chunk)
                if size == limit:
                    break
                chunk = src.read(min(8 * 1024 * 1024, limit - size))
        parts.append({'name': part.name, 'size': size, 'sha256': digest.hexdigest()})
        subprocess.run(['gh', 'release', 'upload', os.environ['RELEASE_TAG'], str(part), '--clobber'], check=True)
        part.unlink()
        index += 1
manifest = {'filename': source.name, 'size': sum(p['size'] for p in parts),
            'sha256': full.hexdigest(), 'parts': parts, 'provenance': metadata}
manifest_path = source.with_name(source.name + '.manifest.json')
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
subprocess.run(['gh', 'release', 'upload', os.environ['RELEASE_TAG'], str(manifest_path), '--clobber'], check=True)
print(json.dumps(manifest, indent=2))
