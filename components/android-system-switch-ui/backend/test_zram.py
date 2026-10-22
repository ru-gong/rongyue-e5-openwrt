#!/usr/bin/env python3
"""Host fixtures execute the exact module shell guard; never access a device.

The fixture replaces fixed proc/sys paths and only the block-node predicate
with a regular-file predicate. A fake BB implements readlink/stat/zcat, while
AWK/grep/printf/cat use host commands. Production has no test/env bypass.
"""
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMMON = HERE / 'reference/tf-common.sh'
HEADER = 'Filename\tType\tSize\tUsed\tPriority\n'
ROW = '/dev/block/zram0 partition 3145724 100 -2\n'
CONFIG = ('CONFIG_IKCONFIG=y\nCONFIG_IKCONFIG_PROC=y\nCONFIG_ZRAM=m\n'
          '# CONFIG_ZRAM_WRITEBACK is not set\n')

class ZramTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.proc = self.root / 'proc'; self.proc.mkdir()
        self.sys = self.root / 'virtual/block/zram0'; self.sys.mkdir(parents=True)
        self.cls = self.root / 'class/block/zram0'; self.cls.parent.mkdir(parents=True)
        self.cls.symlink_to(self.sys)
        self.node = self.root / 'dev/block/zram0'; self.node.parent.mkdir(parents=True)
        self.node.write_bytes(b'fixture, not a real block device')
        Path(str(self.node) + '.rdev').write_text('fd:0')
        (self.proc / 'swaps').write_text(HEADER + ROW)
        (self.proc / 'config.gz').write_bytes(gzip.compress(CONFIG.encode()))
        for name, value in [('dev', '253:0'), ('initstate', '1'), ('disksize', '3221225472'), ('size', '6291456')]:
            (self.sys / name).write_text(value + '\n')
        (self.sys / 'holders').mkdir(); (self.sys / 'slaves').mkdir()
        self.bb = self.root / 'bb'
        self.bb.write_text('''#!/usr/bin/env python3
import gzip, os, pathlib, shutil, subprocess, sys
command, *args = sys.argv[1:]
try:
    if command == 'readlink' and args[0] == '-f':
        print(pathlib.Path(args[1]).resolve(strict=True))
    elif command == 'stat':
        assert args[:2] == ['-c', '%t:%T']
        count = pathlib.Path(__file__).with_suffix('.count')
        n = int(count.read_text()) + 1 if count.exists() else 1
        count.write_text(str(n))
        value = pathlib.Path(args[2] + '.rdev').read_text()
        print('fd:1' if n == 2 and os.environ.get('E5_FIXTURE_CHANGED_RDEV') == '1' else value)
    elif command == 'zcat':
        sys.stdout.buffer.write(gzip.decompress(pathlib.Path(args[0]).read_bytes()))
    elif command in ('cat', 'awk', 'grep', 'printf'):
        raise SystemExit(subprocess.call([shutil.which(command)] + args))
    else:
        raise ValueError('unexpected fixture command')
except Exception:
    raise SystemExit(1)
''')
        self.bb.chmod(0o700)
        source = COMMON.read_text().split('# PUBLIC_REFERENCE_GUARD_END\n',1)[1]
        self.assertEqual(source.count('[ -b "$node" ]'), 1)
        source = source.replace('[ -b "$node" ]', '[ -f "$node" ]')
        for old, new in [('node=/dev/block/zram0', 'node=' + str(self.node)),
                         ('sys=/sys/class/block/zram0', 'sys=' + str(self.cls)),
                         ('= /sys/devices/virtual/block/zram0', '= ' + str(self.sys)),
                         ('/proc/swaps', str(self.proc / 'swaps')),
                         ('/proc/config.gz', str(self.proc / 'config.gz'))]:
            self.assertEqual(source.count(old), 1)
            source = source.replace(old, new)
        self.script = self.root / 'guard.sh'
        self.script.write_text(source + '\nBB=' + str(self.bb) + '\ntf_android_swap_safe\n')

    def run_guard(self, ok=False, extra_env=None):
        result = subprocess.run(['/bin/sh', self.script], capture_output=True,
                                env={**os.environ, **(extra_env or {})}, timeout=15)
        self.assertEqual(result.returncode == 0, ok, result.stderr.decode())
        return result

    def config(self, text):
        (self.proc / 'config.gz').write_bytes(gzip.compress(text.encode()))

    def test_verified_memory_zram(self): self.run_guard(True)
    def test_no_swap_needs_no_config_or_zram(self):
        (self.proc / 'swaps').write_text(HEADER)
        (self.proc / 'config.gz').unlink(); self.node.unlink()
        self.run_guard(True)
    def test_real_block_alias_swapfile_and_additional_entry(self):
        for row in [ROW.replace('/dev/block/zram0', '/dev/block/mmcblk1p1'),
                    ROW.replace('/dev/block/zram0', '/dev/zram0'),
                    ROW.replace('/dev/block/zram0', '/dev/block/by-name/zram'),
                    '/data/swapfile file 3145724 100 -2\n', ROW + ROW]:
            with self.subTest(row=row.split()[0]):
                (self.proc / 'swaps').write_text(HEADER + row); self.run_guard()
    def test_missing_conflicting_duplicate_writeback_config(self):
        for config in [CONFIG.replace('# CONFIG_ZRAM_WRITEBACK is not set\n', ''),
                       CONFIG.replace('# CONFIG_ZRAM_WRITEBACK is not set', 'CONFIG_ZRAM_WRITEBACK=y'),
                       CONFIG + '# CONFIG_ZRAM_WRITEBACK is not set\n',
                       CONFIG + 'CONFIG_ZRAM_WRITEBACK=y\n',
                       CONFIG.replace('# CONFIG_ZRAM_WRITEBACK is not set', '# CONFIG_ZRAM_WRITEBACK not set')]:
            with self.subTest(config_sha=hashlib.sha256(config.encode()).hexdigest()):
                self.config(config); self.run_guard()
    def test_missing_disabled_or_duplicate_required_config(self):
        for line in ['CONFIG_IKCONFIG=y\n', 'CONFIG_IKCONFIG_PROC=y\n', 'CONFIG_ZRAM=m\n']:
            for config in [CONFIG.replace(line, ''), CONFIG + line, CONFIG.replace(line, line.replace('=y', '=n').replace('=m', '=n'))]:
                with self.subTest(line=line): self.config(config); self.run_guard()
    def test_unreadable_or_truncated_config(self):
        raw = (self.proc / 'config.gz').read_bytes()
        (self.proc / 'config.gz').write_bytes(raw[:-4]); self.run_guard()
        (self.proc / 'config.gz').unlink(); self.run_guard()
    def test_backing_attribute_even_none_or_dangling_rejected(self):
        for name in ['backing_dev', 'bd_stat']:
            path = self.sys / name
            path.write_text('none\n'); self.run_guard(); path.unlink()
            path.symlink_to(self.root / 'missing'); self.run_guard(); path.unlink()
    def test_holders_slaves_even_dangling_rejected(self):
        for name in ['holders', 'slaves']:
            path = self.sys / name / 'entry'
            path.symlink_to(self.root / 'missing'); self.run_guard(); path.unlink()
            path.write_text('holder'); self.run_guard(); path.unlink()
    def test_missing_links_directory(self):
        (self.sys / 'holders').rmdir(); self.run_guard()
    def test_nonvirtual_sysfs_rejected(self):
        self.cls.unlink(); self.cls.mkdir(); self.run_guard()
    def test_node_alias_or_nonblock_rejected(self):
        self.node.unlink(); self.node.symlink_to(self.root / 'missing'); self.run_guard()
        self.node.unlink(); self.node.mkdir(); self.run_guard()
    def test_wrong_device_number_and_state(self):
        for name, value in [('dev', 'bad'), ('dev', '253:1'), ('initstate', '0')]:
            path = self.sys / name; old = path.read_text(); path.write_text(value)
            self.run_guard(); path.write_text(old)
    def test_wrong_geometry(self):
        for name, value in [('disksize', '0'), ('disksize', 'garbage'), ('size', '1')]:
            path = self.sys / name; old = path.read_text(); path.write_text(value)
            self.run_guard(); path.write_text(old)
    def test_malformed_swaps(self):
        for data in ['', 'bad\n', HEADER + '\n' + ROW, HEADER + ROW.replace('100', '9999999'),
                     HEADER + ROW.replace('3145724', '9999999'), HEADER + ROW.replace('3145724', '-1'),
                     HEADER + ROW.replace('partition', 'file')]:
            with self.subTest(data=data):
                (self.proc / 'swaps').write_text(data); self.run_guard()
    def test_second_snapshot_identity_change_rejected(self):
        self.run_guard(extra_env={'E5_FIXTURE_CHANGED_RDEV': '1'})

if __name__ == '__main__': unittest.main()
