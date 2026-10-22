#!/usr/bin/env python3
"""Host shell fixtures; fake BB only, no actual unshare/mount/device calls."""
from pathlib import Path
import json, os, subprocess, tempfile, unittest
HERE=Path(__file__).resolve().parent
BASE=HERE/'reference'
class NamespaceActionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name).resolve();self.mod=self.root/'module';self.mod.mkdir()
  self.trace=self.root/'trace';self.info=self.root/'mountinfo'
  self.info.write_text('43 42 254:0 / / ro,relatime - erofs /dev/fixture ro\n44 43 0:17 / /dev rw - tmpfs tmpfs rw\n')
  self.bb=self.root/'bb'
  self.bb.write_text('''#!/usr/bin/env python3
import json,os,pathlib,shutil,subprocess,sys
cmd,*args=sys.argv[1:]
if cmd=='readlink':
 if os.environ.get('E5_BAD_NS')=='1': print('unknown');raise SystemExit(0)
 print('mnt:[2]' if os.environ.get('E5_PRIVATE')=='1' and os.environ.get('E5_SAME_NS')!='1' else 'mnt:[1]')
elif cmd=='unshare':
 with open(os.environ['E5_TRACE'],'a') as f:f.write('UNSHARE '+json.dumps(args[:3])+'\\n')
 if args[:3]!=['-m','--propagation','private']:raise SystemExit(61)
 if os.environ.get('E5_UNSHARE_FAIL')=='1':raise SystemExit(23)
 os.execvpe(args[3],args[3:],{**os.environ,'E5_PRIVATE':'1'})
elif cmd=='sh':os.execv('/bin/sh',['/bin/sh']+args)
elif cmd in ('awk','grep'):raise SystemExit(subprocess.call([shutil.which(cmd)]+args))
else:raise SystemExit(62)
''');self.bb.chmod(0o700)
  text=(BASE/'action.sh').read_text().split('# PUBLIC_REFERENCE_GUARD_END\n',1)[1]
  for a,b in [('/data/adb/magisk/busybox',str(self.bb)),('/data/adb/modules/e5_local_system_switch',str(self.mod)),('/proc/self/mountinfo',str(self.info))]:
   self.assertEqual(text.count(a),1);text=text.replace(a,b)
  self.action=self.mod/'action.sh';self.action.write_text(text)
  (self.mod/'switch.sh').write_text('''#!/bin/sh
[ "${E5_PRIVATE:-}" = 1 ] || exit 90
printf 'SWITCH:%s\\n' "$1" >> "$E5_TRACE"
exit "${E5_SWITCH_RC:-0}"
''')
 def run_action(self,args=(),env=None,success=True):
  result=subprocess.run(['/bin/sh',str(self.action),*args],env={**os.environ,'E5_TRACE':str(self.trace),**(env or {})},capture_output=True,timeout=5)
  self.assertEqual(result.returncode==0,success,result.stderr.decode())
  return result
 def lines(self):return self.trace.read_text().splitlines() if self.trace.exists() else []
 def test_default_reboot(self):
  self.run_action();self.assertEqual(self.lines(),['UNSHARE ["-m", "--propagation", "private"]','SWITCH:reboot'])
 def test_check(self):
  self.run_action(['check']);self.assertEqual(self.lines()[-1],'SWITCH:check')
 def test_explicit_reboot(self):
  self.run_action(['reboot']);self.assertEqual(self.lines()[-1],'SWITCH:reboot')
 def test_bad_modes_or_extra_args_never_unshare_or_switch(self):
  for args in [('',),('other',),('check','reboot'),('check; echo x',),('--private',)]:
   with self.subTest(args=args):self.run_action(args,success=False);self.assertEqual(self.lines(),[])
 def test_unshare_failure_never_switches(self):
  r=self.run_action(env={'E5_UNSHARE_FAIL':'1'},success=False);self.assertEqual(r.returncode,23);self.assertEqual(len(self.lines()),1)
 def test_same_namespace_refused(self):
  self.run_action(env={'E5_SAME_NS':'1'},success=False);self.assertEqual(len(self.lines()),1)
 def test_unknown_namespace_refused(self):
  self.run_action(env={'E5_BAD_NS':'1'},success=False);self.assertEqual(self.lines(),[])
 def test_shared_master_propagation_refused(self):
  for flag in ['shared:1','master:2','propagate_from:3']:
   self.info.write_text(f'43 42 254:0 / / ro {flag} - erofs fixture ro\n')
   self.run_action(success=False);self.assertFalse(any(x.startswith('SWITCH:') for x in self.lines()))
 def test_empty_or_malformed_mountinfo_refused(self):
  for data in ['', 'invalid\n']:
   self.info.write_text(data);self.run_action(success=False);self.assertFalse(any(x.startswith('SWITCH:') for x in self.lines()))
 def test_switch_rc_retained(self):
  r=self.run_action(['check'],{'E5_SWITCH_RC':'17'},success=False);self.assertEqual(r.returncode,17)
if __name__=='__main__':unittest.main()
