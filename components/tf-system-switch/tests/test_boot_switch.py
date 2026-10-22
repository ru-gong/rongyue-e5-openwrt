#!/usr/bin/env python3
"""No device access. All stateful fixtures live under this directory."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import struct
import subprocess
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parent.parent

def fixture_body(text):
    marker='# PUBLIC_REFERENCE_GUARD_END\n'
    if text.count(marker)!=1: raise ValueError('missing public stop guard')
    return text.split(marker,1)[1]


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_bins = tempfile.TemporaryDirectory(prefix='e5-tf-native-')
        cls.addClassCleanup(cls._temp_bins.cleanup)
        cls.bins = Path(cls._temp_bins.name)
        for src, define, out in [('bootctl.c','E5_BOOTCTL_TEST','bootctl-test'),('tf-idle.c','E5_IDLE_TEST','idle-test')]:
            subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-DE5_PUBLIC_FIXTURE',f'-D{define}',str(HERE/'native'/src),'-o',str(cls.bins/out)],check=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='test-', dir=self.bins))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def runbin(self, binary, *args):
        return subprocess.run([str(self.bins/binary),*map(str,args)],capture_output=True,text=True)


class BootControl(Fixture):
    def fixture(self, a=0x9f, b=0x1e):
        data = bytearray((i*17+13)&255 for i in range(1048576))
        bc = bytearray(32)
        bc[:4] = b'_a\0\0'; bc[4:8] = b'BCAB'; bc[8] = 1; bc[9] = 2
        bc[12] = a; bc[14] = b
        bc[28:32] = struct.pack('<I',zlib.crc32(bc[:28]))
        data[2048:2080] = bc
        p = self.tmp/'misc'; p.write_bytes(data)
        return p, bytes(data)

    def assertOutside(self, a, b):
        self.assertEqual(a[:2048],b[:2048]); self.assertEqual(a[2080:],b[2080:])

    def test_arm_changes_only_32_and_saves_fresh_state(self):
        p, old = self.fixture(); backup=self.tmp/'backup'
        r=self.runbin('bootctl-test','arm',backup,p)
        self.assertEqual(r.returncode,0,r.stderr)
        new=p.read_bytes(); self.assertOutside(old,new)
        self.assertEqual(backup.read_bytes(),old[2048:2080])
        self.assertEqual(new[2060],0x9e); self.assertEqual(new[2062],0x2f)
        self.assertEqual(struct.unpack('<I',new[2076:2080])[0],zlib.crc32(new[2048:2076]))
        self.assertEqual(self.runbin('bootctl-test','next',p).stdout.strip(),'linux')

    def test_android_priority_preserves_other_slot_bits(self):
        p,old=self.fixture(0x9e,0x2f)
        self.assertEqual(self.runbin('bootctl-test','android',self.tmp/'b',p).returncode,0)
        new=p.read_bytes();self.assertOutside(old,new)
        self.assertEqual(new[2060],0x9f);self.assertEqual(new[2062],0x2e)
        self.assertEqual(self.runbin('bootctl-test','next',p).stdout.strip(),'android')

    def test_lk_one_remaining_try_is_android(self):
        p,_=self.fixture(0x9e,0x1f)
        self.assertEqual(self.runbin('bootctl-test','next',p).stdout.strip(),'android')

    def test_crc_corruption_refuses_without_writing(self):
        p,old=self.fixture();bad=bytearray(old);bad[2050]^=1;p.write_bytes(bad)
        self.assertNotEqual(self.runbin('bootctl-test','arm',self.tmp/'b',p).returncode,0)
        self.assertEqual(p.read_bytes(),bad);self.assertFalse((self.tmp/'b').exists())

    def test_unconfirmed_android_refuses(self):
        p,old=self.fixture(0x1f,0x2f)
        self.assertNotEqual(self.runbin('bootctl-test','arm',self.tmp/'b',p).returncode,0)
        self.assertEqual(p.read_bytes(),old)

    def test_backup_collision_refuses_without_writing(self):
        p,old=self.fixture();b=self.tmp/'b';b.write_text('keep')
        self.assertNotEqual(self.runbin('bootctl-test','arm',b,p).returncode,0)
        self.assertEqual(p.read_bytes(),old);self.assertEqual(b.read_text(),'keep')

    def test_backup_symlink_refuses(self):
        p,old=self.fixture();b=self.tmp/'b';b.symlink_to(self.tmp/'missing')
        self.assertNotEqual(self.runbin('bootctl-test','arm',b,p).returncode,0)
        self.assertEqual(p.read_bytes(),old);self.assertFalse((self.tmp/'missing').exists())

    def test_expected_control_mismatch_refuses(self):
        p,old=self.fixture();expected=self.tmp/'expected';expected.write_bytes(bytes(32))
        self.assertNotEqual(self.runbin('bootctl-test','arm',self.tmp/'b',expected,p).returncode,0)
        self.assertEqual(p.read_bytes(),old);self.assertFalse((self.tmp/'b').exists())

    def test_expected_control_match(self):
        p,old=self.fixture();expected=self.tmp/'expected';expected.write_bytes(old[2048:2080])
        self.assertEqual(self.runbin('bootctl-test','arm',self.tmp/'b',expected,p).returncode,0)

    def test_short_control_refuses(self):
        p=self.tmp/'misc';p.write_bytes(bytes(2060))
        self.assertNotEqual(self.runbin('bootctl-test','arm',self.tmp/'b',p).returncode,0)
        self.assertEqual(p.stat().st_size,2060)


class IdleGuard(Fixture):
    def task(self, pid=123, tid=123, maps=''):
        d=self.tmp/str(pid)/'task'/str(tid);d.mkdir(parents=True)
        (d/'fd').mkdir();(d/'maps').write_text(maps)
        (d/'cwd').symlink_to('/');(d/'root').symlink_to('/')
        return d

    def scan(self, target='179:9', disk='179:8'):
        return self.runbin('idle-test',target,disk,self.tmp).returncode

    def test_clean_observable_tasks(self):
        self.task();self.assertEqual(self.scan(),0)

    def test_mapping_on_partition_refused(self):
        self.task(maps='1000-2000 r--p 0 b3:09 1 /card/file\n')
        self.assertEqual(self.scan(),1)

    def test_mapping_on_whole_disk_refused(self):
        self.task(maps='1000-2000 r--p 0 b3:08 1 /card/file\n')
        self.assertEqual(self.scan(),1)

    def test_unshared_thread_is_scanned(self):
        self.task();self.task(tid=124,maps='1000-2000 r--p 0 b3:09 1 /card/file\n')
        self.assertEqual(self.scan(),1)

    def test_missing_maps_on_live_task_is_unknown(self):
        d=self.task();(d/'maps').unlink();self.assertEqual(self.scan(),2)

    def test_missing_fd_dir_on_live_task_is_unknown(self):
        d=self.task();(d/'fd').rmdir();self.assertEqual(self.scan(),2)

    def test_malformed_mapping_is_unknown(self):
        self.task(maps='not a maps line\n');self.assertEqual(self.scan(),2)

    def test_no_tasks_is_unknown(self):
        self.assertEqual(self.scan(),2)

    def test_cwd_on_target_filesystem_refused(self):
        self.task();d=os.stat('/').st_dev
        target=f'{os.major(d)}:{os.minor(d)}'
        self.assertEqual(self.scan(target=target),1)


class RootSwitchTransaction(Fixture):
    """Run the actual shell transaction with isolated paths and health mocks.

    This validates state/rollback semantics, not live storage identity probes.
    """
    fixture = BootControl.fixture
    assertOutside = BootControl.assertOutside

    def setup_runtime(self, default='android', request=None, native_fail=False):
        p,original=self.fixture(0x9e,0x1f)
        root=self.tmp/'root'
        for n in ('etc/e5/local-switch','etc/e5linux','opt/e5','run'):
            (root/n).mkdir(parents=True,exist_ok=True)
        conf=root/'etc/e5linux/default-boot';conf.write_text(default+'\n')
        req=root/'etc/e5/local-switch/return-to-linux'
        if request is not None:req.write_text(request)
        (root/'opt/e5/tf-common.sh').write_text('''tf_load() { TF_INSTALL_ID=fixture-install; TF_KERNEL_RELEASE=fixture-kernel; }
tf_internal() { return 0; }
tf_running_root() { return 0; }
tf_fail() { echo "REFUSED: $*" >&2; return 1; }
''')
        ctl=root/'opt/e5/e5-tf-bootctl'
        if native_fail:
            ctl.write_text('#!/bin/sh\n[ "$1" = check ] && exit 0\nexit 1\n')
        else:
            ctl.write_text('#!/bin/sh\nexec '+shlex.quote(str(self.bins/'bootctl-test'))+' "$@" '+shlex.quote(str(p))+'\n')
        ctl.chmod(0o755)
        text=fixture_body((HERE/'reference/openwrt/opt/e5/e5-next-boot').read_text())
        text=text.replace('BB=/usr/local/bin/busybox','BB=/usr/bin/env')
        for prefix in ('/etc/e5','/opt/e5','/run/'):
            text=text.replace(prefix,str(root)+prefix)
        script=root/'next';script.write_text(text)
        return root,script,conf,req,p,original

    def runscript(self,script,mode):
        return subprocess.run(['sh',str(script),mode],capture_output=True,text=True)

    def test_first_trial_does_not_rearm(self):
        root,s,c,r,p,old=self.setup_runtime()
        x=self.runscript(s,'--confirm-return');self.assertEqual(x.returncode,0,x.stderr)
        self.assertEqual(c.read_text(),'android\n');self.assertFalse(r.exists());self.assertEqual(p.read_bytes(),old)
        self.assertFalse((root/'run/e5-tf-switch.lock').exists())

    def test_magisk_request_consumes_once_and_sets_linux(self):
        root,s,c,r,p,old=self.setup_runtime(request='e5-tf-return-v1\nfixture-install\nfixture-kernel\n')
        x=self.runscript(s,'--confirm-return');self.assertEqual(x.returncode,0,x.stderr)
        self.assertEqual(c.read_text(),'linux\n');self.assertFalse(r.exists())
        self.assertEqual(p.read_bytes()[2062],0x2f);self.assertOutside(old,p.read_bytes())
        self.assertFalse((root/'run/e5-tf-switch.lock').exists())

    def test_explicit_android_stays_android_clears_request(self):
        root,s,c,r,p,old=self.setup_runtime(default='linux',request='e5-tf-return-v1\nfixture-install\nfixture-kernel\n')
        x=self.runscript(s,'android');self.assertEqual(x.returncode,0,x.stderr)
        self.assertEqual(c.read_text(),'android\n');self.assertFalse(r.exists())
        self.assertEqual(self.runbin('bootctl-test','next',p).stdout.strip(),'android')
        self.assertOutside(old,p.read_bytes())

    def test_wrong_install_request_refuses(self):
        root,s,c,r,p,old=self.setup_runtime(request='e5-tf-return-v1\nwrong-install\nfixture-kernel\n')
        x=self.runscript(s,'--confirm-return');self.assertNotEqual(x.returncode,0)
        self.assertEqual(c.read_text(),'android\n');self.assertTrue(r.exists());self.assertEqual(p.read_bytes(),old)
        self.assertFalse((root/'run/e5-tf-switch.lock').exists())

    def test_native_failure_restores_default_and_request(self):
        request='e5-tf-return-v1\nfixture-install\nfixture-kernel\n'
        root,s,c,r,p,old=self.setup_runtime(default='linux',request=request,native_fail=True)
        x=self.runscript(s,'android');self.assertNotEqual(x.returncode,0)
        self.assertEqual(c.read_text(),'linux\n');self.assertEqual(r.read_text(),request);self.assertEqual(p.read_bytes(),old)
        self.assertFalse((root/'run/e5-tf-switch.lock').exists())

    def test_existing_lock_is_never_deleted(self):
        root,s,c,r,p,old=self.setup_runtime()
        lock=root/'run/e5-tf-switch.lock';lock.mkdir()
        x=self.runscript(s,'linux');self.assertNotEqual(x.returncode,0)
        self.assertTrue(lock.is_dir());self.assertEqual(c.read_text(),'android\n');self.assertEqual(p.read_bytes(),old)


if __name__ == '__main__': unittest.main(verbosity=2)
