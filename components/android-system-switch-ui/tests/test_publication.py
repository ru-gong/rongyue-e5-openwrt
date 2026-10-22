#!/usr/bin/env python3
"""Publication boundary tests: only early refusal and synthetic native binaries."""
from pathlib import Path
import json, subprocess, tempfile, unittest
ROOT=Path(__file__).resolve().parent.parent
class PublicBoundary(unittest.TestCase):
 def test_all_shell_entrypoints_stop_before_body(self):
  paths=[]
  for directory in ('reference','reference-baseline','backend/reference','backend/reference-baseline'):
   parent=ROOT/directory
   if parent.exists(): paths.extend(p for p in parent.rglob('*') if p.is_file())
  self.assertTrue(paths)
  for p in paths:
   with self.subTest(path=str(p.relative_to(ROOT))):
    lines=p.read_text().splitlines()
    self.assertEqual(lines[1:5],['# PUBLIC_REFERENCE_GUARD_BEGIN','printf "%s\\n" "Reference-only export: device execution is disabled." >&2','exit 64','# PUBLIC_REFERENCE_GUARD_END'])
    subprocess.run(['sh','-n',str(p)],check=True)
    r=subprocess.run(['sh',str(p),'start'],capture_output=True,timeout=3)
    self.assertEqual(r.returncode,64);self.assertEqual(r.stdout,b'')
    self.assertEqual(r.stderr,b'Reference-only export: device execution is disabled.\n')
 def test_sourcing_also_stops(self):
  paths=[p for p in ROOT.rglob('*.sh') if 'reference' in p.parts or 'reference-baseline' in p.parts]
  self.assertTrue(paths)
  for p in paths:
   r=subprocess.run(['sh','-c','. "$1"; printf unsafe','fixture',str(p)],capture_output=True,timeout=3)
   self.assertEqual(r.returncode,64);self.assertEqual(r.stdout,b'')
 def test_default_native_build_is_inert(self):
  paths=list((ROOT/'native').glob('*.c'))+list((ROOT/'backend').glob('*.c'))
  self.assertTrue(paths)
  with tempfile.TemporaryDirectory(prefix='e5-public-default-') as d:
   for p in paths:
    binary=Path(d)/p.stem
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p),'-o',str(binary)],check=True)
    r=subprocess.run([str(binary),'arm','ignored'],capture_output=True,timeout=3)
    self.assertEqual(r.returncode,64);self.assertEqual(r.stdout,b'')
 def test_source_export_hashes(self):
  import hashlib
  entries=json.loads((ROOT/'SOURCE-PROVENANCE.json').read_text())['files']
  for item in entries:
   self.assertEqual(hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest(),item['published_sha256'],item['path'])
if __name__=='__main__':unittest.main(verbosity=2)
