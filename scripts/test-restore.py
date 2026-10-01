"""Exercise transfer recovery and reject corrupt parts without replacing output."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

restore = Path(__file__).with_name('restore.py')
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    chunks = [b'first part\x00', b'second part\xff']
    payload = b''.join(chunks)
    parts = []
    for index, chunk in enumerate(chunks):
        name = f'archive.tar.part{index:03d}'
        (root / name).write_bytes(chunk)
        parts.append({'name': name, 'size': len(chunk), 'sha256': hashlib.sha256(chunk).hexdigest()})
    manifest = {'filename': 'archive.tar', 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'parts': parts}
    (root / 'archive.tar.manifest.json').write_text(json.dumps(manifest))
    subprocess.run([sys.executable, str(restore), str(root)], check=True)
    assert (root / 'archive.tar').read_bytes() == payload
    (root / parts[0]['name']).write_bytes(b'corrupt')
    result = subprocess.run([sys.executable, str(restore), str(root)], capture_output=True)
    assert result.returncode != 0
    assert (root / 'archive.tar').read_bytes() == payload
    assert not (root / 'archive.tar.assembling').exists()
print('Restore and corruption rejection passed')
