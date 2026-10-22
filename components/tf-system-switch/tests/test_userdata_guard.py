#!/usr/bin/env python3
"""Exercise actual shell guards against synthetic files; never open a block node.

Only the test copy substitutes its /sys and /proc roots and the block-node
predicate. A fake BusyBox implements stat/blockdev against fixture files.
"""
from pathlib import Path
import os, shutil, subprocess, tempfile, unittest

HERE = Path(__file__).resolve().parent.parent

def fixture_body(text):
    marker='# PUBLIC_REFERENCE_GUARD_END\n'
    if text.count(marker)!=1: raise ValueError('missing public stop guard')
    return text.split(marker,1)[1]

class UserdataGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='userdata-fixture-')).resolve()
        self.node = self.tmp/'sys/mmcblk0p70'
        (self.node/'holders').mkdir(parents=True)
        for name, value in {'uevent': 'PARTNAME=userdata\n', 'start': '15241216\n',
                            'size': '45834240\n', 'dev': '179:70\n', 'ro': '0\n'}.items():
            (self.node/name).write_text(value)
        (self.tmp/'dev').mkdir()
        (self.tmp/'dev/mmcblk0p70').write_bytes(b'unchanged fixture media')
        (self.tmp/'stathex').write_text('b3:46\n')
        (self.tmp/'devicebytes').write_text('23467130880\n')
        (self.tmp/'blockro').write_text('0\n')
        self.task(101, 101)
        self.bb = self.tmp/'bb'
        self.bb.write_text('''#!/usr/bin/env python3
from pathlib import Path
import os, sys
r=Path(__file__).resolve().parent
a=sys.argv[1:]
if a[0] in ('stat','blockdev'):
    assert a[-1]==str(r/'dev/mmcblk0p70'), 'fixture escaped'
    if a[0]=='stat': print((r/'stathex').read_text().strip())
    elif a[1]=='--getsize64': print((r/'devicebytes').read_text().strip())
    elif a[1]=='--getro': print((r/'blockro').read_text().strip())
    elif a[1]=='--setro':
        (r/'setro.called').write_text('one ioctl to fixture only')
        if (r/'setro.fail').exists(): sys.exit(1)
        (r/'blockro').write_text('1\\n')
        if not (r/'stale.sysfs').exists(): (r/'sys/mmcblk0p70/ro').write_text('1\\n')
    else: raise ValueError('unexpected blockdev action')
else:
    os.execvp(a[0],a)
''')
        self.bb.chmod(0o700)
        text = fixture_body((HERE/'reference/initramfs/tf-common.sh').read_text())
        self.assertEqual(text.count('[ -b "$TF_USERDATA" ]'), 1)
        text = text.replace('/sys/class/block', str(self.tmp/'sys'))
        text = text.replace('/proc/', str(self.tmp/'proc')+'/')
        text = text.replace('[ -b "$TF_USERDATA" ]', '[ -f "$TF_USERDATA" ]')
        self.script = self.tmp/'common-fixture.sh'
        self.script.write_text(text)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def task(self, pid, tid, mount='1 0 0:1 / / rw - tmpfs tmpfs rw\n'):
        p = self.tmp/f'proc/{pid}/task/{tid}'
        p.mkdir(parents=True)
        (p/'status').write_text('Kthread:\t0\n')
        (p/'mountinfo').write_text(mount)
        return p

    def run_guard(self, name='tf_userdata_protect'):
        env = dict(os.environ, BB=str(self.bb), TF_EMMC='mmcblk0', TF_DEV_PREFIX=str(self.tmp/'dev'))
        return subprocess.run(['sh', '-c', '. "$1"; '+name, 'fixture', str(self.script)],
                              env=env, text=True, capture_output=True)

    def refused_before_ioctl(self):
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.tmp/'setro.called').exists())

    def test_protect_sets_only_kernel_flag_and_reads_both_views(self):
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.tmp/'blockro').read_text(), '1\n')
        self.assertEqual((self.node/'ro').read_text(), '1\n')
        self.assertEqual((self.tmp/'dev/mmcblk0p70').read_bytes(), b'unchanged fixture media')

    def test_wrong_partition_name_refuses_before_ioctl(self):
        (self.node/'uevent').write_text('PARTNAME=other\n')
        self.refused_before_ioctl()

    def test_wrong_geometry_refuses_before_ioctl(self):
        (self.node/'start').write_text('1\n')
        self.refused_before_ioctl()

    def test_wrong_node_rdev_refuses_before_ioctl(self):
        (self.tmp/'stathex').write_text('b3:47\n')
        self.refused_before_ioctl()

    def test_symlink_node_refuses_before_ioctl(self):
        p = self.tmp/'dev/mmcblk0p70'; p.unlink(); p.symlink_to('../blockro')
        self.refused_before_ioctl()

    def test_other_thread_mount_refuses_before_ioctl(self):
        self.task(101, 102, '2 1 179:70 / /hidden ro - f2fs /dev/alias ro\n')
        self.refused_before_ioctl()

    def test_missing_mountinfo_is_unknown_and_refuses(self):
        (self.tmp/'proc/101/task/101/mountinfo').unlink()
        self.refused_before_ioctl()

    def test_holder_refuses_before_ioctl(self):
        (self.node/'holders/dm-test').write_text('fixture')
        self.refused_before_ioctl()

    def test_failed_ioctl_refuses(self):
        (self.tmp/'setro.fail').touch()
        self.assertNotEqual(self.run_guard().returncode, 0)
        self.assertEqual((self.tmp/'blockro').read_text(), '0\n')

    def test_inconsistent_readback_refuses(self):
        (self.tmp/'stale.sysfs').touch()
        self.assertNotEqual(self.run_guard().returncode, 0)

    def test_runtime_check_never_sets_readonly(self):
        self.assertNotEqual(self.run_guard('tf_userdata_check').returncode, 0)
        self.assertFalse((self.tmp/'setro.called').exists())
        (self.tmp/'blockro').write_text('1\n'); (self.node/'ro').write_text('1\n')
        self.assertEqual(self.run_guard('tf_userdata_check').returncode, 0)
        self.assertFalse((self.tmp/'setro.called').exists())

if __name__ == '__main__':
    unittest.main(verbosity=2)
