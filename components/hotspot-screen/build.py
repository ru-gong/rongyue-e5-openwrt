import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
manifest = json.loads((ROOT/'manifest.json').read_bytes())
assets = {name: (ROOT/name).read_bytes() for name in [
    'control.py', 'backend.uc', 'manifest.json', 'index.html', 'app.js',
    'e5-hotspot', 'LICENSE', 'NOTICE.md',
]}
assets[manifest['entry']] = assets['index.html']
package=out/('hotspot-screen-'+manifest['version'].removesuffix('-local')+'.tar.gz')
with tarfile.open(package, 'w:gz') as tar:
    for name, data in assets.items():
        i=tarfile.TarInfo('hotspot/'+name);i.size=len(data);i.mode=0o644;i.mtime=int(time.time())
        tar.addfile(i,io.BytesIO(data))
meta={'version':manifest['version'],'entry':manifest['entry'],
      'package':package.name,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
      'files':{k:hashlib.sha256(v).hexdigest() for k,v in assets.items()}}
(out/'HOTSPOT_PACKAGE.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'version':manifest['version'],'bytes':package.stat().st_size}))
