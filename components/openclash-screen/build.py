"""Build the local plugin, with versioned entry and JS to avoid stale screen caches."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time

root = Path(__file__).resolve().parent
destination = Path(sys.argv[1]).resolve()
manifest = json.loads((root / 'manifest.json').read_bytes())
version = manifest['version'].removesuffix('-local')
assets = {n: (root / n).read_bytes() for n in [
    'manifest.json', 'backend.uc', 'control.py', 'index.html', 'app.js',
    'LICENSE', 'NOTICE.md',
]}
assets[manifest['entry']] = assets['index.html']
stream = io.BytesIO()
with tarfile.open(fileobj=stream, mode='w:gz') as archive:
    for name, data in assets.items():
        entry = tarfile.TarInfo('openclash/' + name)
        entry.size, entry.mode, entry.mtime = len(data), 0o644, int(time.time())
        archive.addfile(entry, io.BytesIO(data))
path = destination / ('openclash-screen-' + version + '.tar.gz')
path.write_bytes(stream.getvalue())
metadata = {'version': manifest['version'], 'entry': manifest['entry'], 'package': str(path),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'files': {n: hashlib.sha256(b).hexdigest() for n, b in assets.items()}}
(destination / 'PACKAGE.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps({'version': manifest['version'], 'package': str(path), 'bytes': len(stream.getvalue())}))
