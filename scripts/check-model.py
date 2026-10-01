import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1])
blobs = list((root / 'models' / 'blobs').glob('sha256-*'))
if not blobs:
    raise SystemExit('Model download contains no blobs')
for path in blobs:
    digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
    if path.name != 'sha256-' + digest:
        raise SystemExit('Corrupt model blob: ' + path.name)
    print('VERIFIED', path.name, path.stat().st_size)
for manifest in (root / 'models' / 'manifests').rglob('*'):
    if manifest.is_file():
        import json
        data = json.loads(manifest.read_text())
        for entry in [data['config'], *data['layers']]:
            blob = root / 'models' / 'blobs' / entry['digest'].replace(':', '-')
            if not blob.is_file() or blob.stat().st_size != entry['size']:
                raise SystemExit('Missing or invalid manifest blob: ' + str(blob))
