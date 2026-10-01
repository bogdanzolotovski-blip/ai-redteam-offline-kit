import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
release = json.loads((root / 'release.json').read_text())
assets = {a['name']: a for a in release['assets']}
manifests = [json.loads(p.read_text()) for p in sorted(root.glob('*.manifest.json'))]
expected = {'ubuntu-24.04.5-live-server-amd64.iso', 'docker-open-webui.tar.gz', 'docker-ollama.tar.gz', 'docker-portainer.tar.gz', 'docker-ubuntu.tar.gz', 'ollama-modelstore.tar.gz', 'ubuntu-packages.tar.gz', 'open-webui-v0.11.4-source.tar.gz', 'offline-kit-instructions.tar.gz'}
if {m['filename'] for m in manifests} != expected:
    raise SystemExit('Required artifact set incomplete')
lines = []
for manifest in manifests:
    for part in manifest['parts']:
        asset = assets.get(part['name'])
        if not asset or asset['state'] != 'uploaded' or asset['size'] != part['size']:
            raise SystemExit('Missing/partial uploaded asset: ' + part['name'])
        if asset.get('digest') != 'sha256:' + part['sha256']:
            raise SystemExit('GitHub digest does not match local digest: ' + part['name'])
        lines.append(part['sha256'] + '  ' + part['name'])
(root / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
(root / 'MANIFEST.json').write_text(json.dumps({'release': release['tag_name'], 'artifacts': manifests, 'verification': 'All required uploaded parts matched GitHub SHA256 digests and sizes'}, indent=2) + '\n')
print('Verified', len(manifests), 'artifacts and', len(lines), 'uploaded parts')
