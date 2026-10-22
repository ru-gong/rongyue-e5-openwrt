#!/usr/bin/env python3
"""Host-only fixtures. No Android, su, device, mount, BCB or filesystem writes."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
OLD = HERE/'reference-baseline'

def fixture_body(text):
    marker='# PUBLIC_REFERENCE_GUARD_END\n'
    if text.count(marker)!=1: raise ValueError('missing public stop guard')
    return text.split(marker,1)[1]

BOOT = '11111111-2222-3333-4444-555555555555'


class ShellFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.mod = self.root/'module'; self.mod.mkdir(mode=0o700)
        self.dev = self.root/'dev'; self.dev.mkdir()
        (self.dev/'null').touch()
        self.proc = self.root/'proc'; (self.proc/'sys/kernel/random').mkdir(parents=True)
        (self.proc/'sys/kernel/random/boot_id').write_text(BOOT+'\n')
        (self.proc/'uptime').write_text('1000.50 0.00\n')
        (self.proc/'self').mkdir()
        (self.proc/'self/mountinfo').write_text(f'1 0 0:1 / {self.dev} rw - tmpfs tmpfs rw\n')
        self.bb = self.root/'bb'
        self.bb.write_text('''#!/usr/bin/env python3
import fcntl,os,pathlib,shutil,subprocess,sys
c,*a=sys.argv[1:]
if c=='id':print(0)
elif c=='stat':
 p=a[-1];s=os.fstat(8) if p.endswith('/self/fd/8') else os.stat(p)
 fmt=a[-2];v={'%a':f'{s.st_mode&0o7777:o}','%u:%g':'0:0','%u:%g:%a':f'0:0:{s.st_mode&0o7777:o}','%u:%g:%a:%h':f'0:0:{s.st_mode&0o7777:o}:{s.st_nlink}','%d':str(s.st_dev),'%s':str(s.st_size),'%d:%i':f'{s.st_dev}:{s.st_ino}'};print(v[fmt])
elif c=='readlink':print(pathlib.Path(a[-1]).resolve())
elif c=='flock':
 try:fcntl.flock(int(a[-1]),fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise SystemExit(1)
elif c=='mkdir':os.mkdir(a[-1],int(a[a.index('-m')+1],8))
elif c=='mv':os.rename(*a)
elif c=='setsid':os.setsid();os.execv(a[0],a)
elif c=='sh':
 p=pathlib.Path(os.environ['FIXTURE_PROC'])/str(os.getpid());p.mkdir(exist_ok=True)
 (p/'stat').write_text(str(os.getpid())+' (fixture) S '+'0 '*18+'1234 0\\n')
 os.execv('/bin/sh',['/bin/sh']+a)
elif c in ('awk','grep'):os.execv(shutil.which(c),[c]+a)
else:raise SystemExit(97)
'''); self.bb.chmod(0o700)
        for name in ('ui-common.sh','ui-backend.sh','ui-worker.sh'):
            source=fixture_body((HERE/'reference'/name).read_text())
            source=source.replace('/data/adb/magisk/busybox',str(self.bb)).replace('/data/adb/modules/e5_local_system_switch',str(self.mod))
            source=source.replace('/dev',str(self.dev)).replace('/proc',str(self.proc))
            source=source.replace('PATH=/system/bin:/system/xbin','PATH='+os.environ['PATH'])
            (self.mod/name).write_text(source); (self.mod/name).chmod(0o600)
        self.trace=self.root/'calls'
        (self.mod/'action.sh').write_text(f"#!/bin/sh\nprintf 'called\\n' >> '{self.trace}'\nprintf '[1/9] fixture\\n[4/9] fixture\\n'\nsleep 0.3\nexit 17\n")
        self.env={**os.environ,'FIXTURE_PROC':str(self.proc)}

    def api(self,*args):
        r=subprocess.run(['/bin/sh',str(self.mod/'ui-backend.sh'),*args],capture_output=True,env=self.env,timeout=4)
        self.assertTrue(r.stdout,r.stderr.decode())
        return r,json.loads(r.stdout)

    def wait_result(self):
        p=self.dev/'e5-switch-ui/result'
        deadline=time.monotonic()+5
        while not p.exists() and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(p.exists(),(self.dev/'e5-switch-ui/worker.log').read_text())

    def test_idle_status_is_read_only(self):
        r,j=self.api('status');self.assertEqual(r.returncode,0);self.assertEqual(j['state'],'IDLE');self.assertFalse((self.dev/'e5-switch-ui').exists())

    def test_bad_arguments_never_start(self):
        for a in [(),('reboot',),('start','other'),('start; touch /x',)]:
            r,j=self.api(*a);self.assertNotEqual(r.returncode,0);self.assertEqual(j['state'],'UNKNOWN');self.assertFalse(self.trace.exists())

    def test_single_submission_detached_and_result_reopen(self):
        _,first=self.api('start');self.assertEqual(first['run_id'],BOOT+'-1')
        _,again=self.api('start');self.assertEqual(again['run_id'],first['run_id'])
        self.wait_result();_,last=self.api('status');self.assertEqual((last['state'],last['exit_code']),('REFUSED',17))
        _,repeat=self.api('start');self.assertEqual(repeat['run_id'],first['run_id']);self.assertEqual(self.trace.read_text(),'called\n')

    def test_symlink_state_directory_rejected(self):
        (self.dev/'e5-switch-ui').symlink_to(self.mod,target_is_directory=True)
        r,j=self.api('start');self.assertNotEqual(r.returncode,0);self.assertEqual(j['state'],'UNKNOWN');self.assertFalse(self.trace.exists())

    def test_unknown_or_incomplete_existing_state_never_restarts(self):
        (self.dev/'e5-switch-ui').mkdir(mode=0o700)
        r,j=self.api('start');self.assertNotEqual(r.returncode,0);self.assertEqual(j['state'],'UNKNOWN');self.assertFalse(self.trace.exists())

    def test_non_tmpfs_dev_refused_before_mkdir(self):
        (self.proc/'self/mountinfo').write_text(f'1 0 0:1 / {self.dev} rw - ext4 fixture rw\n')
        r,j=self.api('start');self.assertNotEqual(r.returncode,0);self.assertEqual(j['state'],'UNKNOWN');self.assertFalse((self.dev/'e5-switch-ui').exists())

    def test_writable_dev_parent_refused_before_mkdir(self):
        self.dev.chmod(0o777)
        r,j=self.api('start');self.assertNotEqual(r.returncode,0);self.assertEqual(j['state'],'UNKNOWN');self.assertFalse((self.dev/'e5-switch-ui').exists())

    def test_original_action_lock_blocks_submission(self):
        p=self.mod/'.operation.lock';p.touch(mode=0o600)
        with p.open('r+') as f:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            r,j=self.api('start');self.assertNotEqual(r.returncode,0);self.assertEqual(j['state'],'UNKNOWN');self.assertFalse(self.trace.exists())

    def test_only_progress_changes_to_existing_switch(self):
        before=fixture_body((OLD/'switch.sh').read_text());after=fixture_body((HERE/'reference/switch.sh').read_text())
        kept='\n'.join(x for x in after.split('\n') if not x.startswith("echo '[") )
        self.assertEqual(before,kept)
        self.assertEqual(sum(x.startswith("echo '[") for x in after.splitlines()),9)


class NativeObserverFixtures(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.dev=self.root/'dev';self.dev.mkdir();self.base=self.dev/'e5-switch-ui';self.base.mkdir(mode=0o700)
        self.proc=self.root/'proc';(self.proc/'sys/kernel/random').mkdir(parents=True);(self.proc/'sys/kernel/random/boot_id').write_text(BOOT+'\n')
        self.start=str(time.monotonic()-10)
        for n,v in [('lock',''),('worker.log',''),('meta',f'{BOOT} 0 0 {self.start}\n')]:
            p=self.base/n;p.write_text(v);p.chmod(0o600)
        self.binary=self.root/'observer'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-DE5_PUBLIC_FIXTURE','-DE5_UI_STREAM_TEST',f'-DBASE="{self.base}"',f'-DDEV="{self.dev}"',f'-DPROC="{self.proc}"',str(HERE/'ui-stream.c'),'-o',str(self.binary)],check=True,capture_output=True)
        self.lock=(self.base/'lock').open('r');fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB);self.addCleanup(self.lock.close)

    def run_stream(self,body,phase='0'):
        (self.base/'worker.log').write_text(body)
        r=subprocess.run([str(self.binary),BOOT,self.start,phase],capture_output=True,timeout=4)
        return r,[json.loads(x) for x in r.stdout.splitlines()]

    def test_phase_replay_never_regresses_and_terminal_preserves_rc(self):
        r,j=self.run_stream('[1/9] old\n[4/9] old\n[7/9] new\nE5_UI_TERMINAL 19\n','4')
        self.assertEqual(r.returncode,0);self.assertEqual([x['phase'] for x in j],['TF_READBACK','FINISHED']);self.assertEqual((j[-1]['state'],j[-1]['exit_code']),('REFUSED',19))

    def test_post_arm_failure_not_misreported_safe(self):
        _,j=self.run_stream('[8/9] arm\nE5_UI_TERMINAL 1\n');self.assertEqual(j[-1]['state'],'FAILED')

    def test_return_zero_never_claims_reboot_success(self):
        _,j=self.run_stream('[9/9] resetting\nE5_UI_TERMINAL 0\n');self.assertEqual(j[-1]['state'],'UNKNOWN')

    def test_log_symlink_refused(self):
        p=self.base/'worker.log';p.unlink();p.symlink_to(self.base/'meta')
        r=subprocess.run([str(self.binary),BOOT,self.start,'0'],capture_output=True,timeout=4)
        self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['state'],'UNKNOWN')

    def test_pid_reuse_or_missing_worker_refused(self):
        (self.base/'meta').write_text(f'{BOOT} 999999 123 {self.start}\n')
        r,j=self.run_stream('');self.assertNotEqual(r.returncode,0);self.assertEqual(j[-1]['state'],'UNKNOWN')

    def test_worker_disappears_without_terminal_unknown(self):
        fcntl.flock(self.lock,fcntl.LOCK_UN)
        r,j=self.run_stream('[4/9] checking\n');self.assertNotEqual(r.returncode,0);self.assertEqual(j[-1]['state'],'UNKNOWN')

    def test_close_ui_pipe_exits_observer_only(self):
        p=subprocess.Popen([str(self.binary),BOOT,self.start,'0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def cleanup():
            if p.poll() is None:p.kill();p.wait()
            if p.stderr:p.stderr.close()
        self.addCleanup(cleanup)
        p.stdout.close();self.assertEqual(p.wait(timeout=4),0);p.stderr.close()
        # The writer lock is still held by the fixture, not cancelled/unlocked.
        other=(self.base/'lock').open('r')
        with other,self.assertRaises(BlockingIOError):fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_oversize_line_fails_closed(self):
        r,j=self.run_stream('x'*4096+'\n');self.assertNotEqual(r.returncode,0);self.assertEqual(j[-1]['state'],'UNKNOWN')

    def test_boot_mismatch_refused(self):
        (self.proc/'sys/kernel/random/boot_id').write_text('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n')
        r,j=self.run_stream('');self.assertNotEqual(r.returncode,0);self.assertEqual(j[-1]['state'],'UNKNOWN')


if __name__=='__main__':unittest.main()
