"""VM-only real-proc tests. Each test has its own PID/mount namespace.

The scanner is compiled HOST_TEST+LINUX_INTEGRATION (gate stays zero), never
production-enabled. /proc is a new procfs mount; /sys/block is empty except the private read-only loop case, which uses real sysfs.
Only the namespace's own children and temporary filesystem are changed.
"""
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
TX = '0123456789abcdef'
OP = 'c' * 32


def inside(case, scanner, workload):
    if sys.platform != 'linux' or os.getpid() != 1 or os.geteuid() != 0:
        raise RuntimeError('isolated root PID1 required')
    tmp = tempfile.TemporaryDirectory(prefix='e5-native-test-real-', dir='/tmp')
    tmp._finalizer.detach()  # Never recurse into a mounted procfs on Python exit.
    root = Path(tmp.name) / 'sandbox'
    (root / 'proc').mkdir(parents=True)
    (root / 'sys/block').mkdir(parents=True)
    (root / 'data/e5linux').mkdir(parents=True)
    protected = root / 'data/e5linux/boot-os'
    protected.write_text('openwrt\n')
    subprocess.run(['mount', '--bind', '/proc', str(root / 'proc')], check=True)
    children = []
    if case.startswith('scale'):
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(8192, hard), hard))

    def child(threads=3, kind='n'):
        p = subprocess.Popen([workload, str(threads), kind, str(protected.parent if kind == 'q' else protected)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not p.stdout.readline().startswith(b'READY '):
            raise RuntimeError('workload failed rc=' + str(p.wait(timeout=1)) + ': ' + p.stderr.read().decode())
        children.append(p)
        return p

    kind = {'leader-exit-protected': 'u', 'unshared-protected': 'u', 'protected-fd': 'p', 'sticky-protected-exit': 'p', 'protected-root': 'q', 'scale': 's', 'representative-exit': 'r', 'representative-exit-protected': 'R'}.get(case, 'f' if case.startswith('fd-') else 'n')
    if case.startswith('scale'):kind='s'
    loop_device = None
    try:
        if case == 'protected-loop':
            backing = root / 'data/e5linux/loop.img'
            backing.write_bytes(bytes(4096))
            loop_device = subprocess.check_output(['losetup', '--read-only', '--find', '--show', str(backing)], text=True).strip()
            if not loop_device.startswith('/dev/loop') or not loop_device[9:].isdigit():
                raise RuntimeError('unexpected private loop identity')
            subprocess.run(['mount', '--bind', '/sys', str(root / 'sys')], check=True)
        first = child(kind=kind)
        if case.startswith('scale'):
            # 441 workload groups / 1532 tasks, in addition to parent and scanner.
            for i in range(440):
                child(4 if i < 209 else 3, 's')
        if case == 'protected-cwd':
            extra = subprocess.Popen(['sleep', '10'], cwd=protected.parent)
            children.append(extra)
        if case.startswith('leader-exit'):
            first.stdin.write(b'l'); first.stdin.flush(); time.sleep(.01)
        if case == 'raise-soft':
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            resource.setrlimit(resource.RLIMIT_NOFILE, (1024, hard))
        if case == 'hard-low':
            resource.setrlimit(resource.RLIMIT_NOFILE, (512, 512))
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        deadline = int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000) + 5000
        inherited = []
        if case == 'self-inherited-protected':
            inherited.append(os.open(protected, os.O_RDONLY))
        sync_phase = 'pin-process-identities' if case == 'exit-before-pin' else 'final-process-identities' if case.startswith('representative-exit') else 'fd-tables'
        sync_env = {'E5_SCANNER_TEST_SYNC': sync_phase}
        if case.startswith('fd-') and case != 'fd-churn':
            sync_env['E5_SCANNER_TEST_FD_SYNC'] = str(first.pid)
        start = time.monotonic()
        p = subprocess.Popen([scanner, '--test-root', str(root), 'scan', TX, boot, OP, str(deadline)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=inherited,
                             env={**os.environ, **sync_env})
        # Child inherited the descriptor; close the parent's copy before the
        # fd-tables handshake so only scanner self can cause this occupancy.
        for fd in inherited:os.close(fd)
        inherited.clear()
        rows = []
        action = False
        fd_snapshots = 0
        for line in p.stdout:
            row = json.loads(line); rows.append(row)
            if not action and row['phase'] == sync_phase and row['event'] == 'PHASE' and row['subphase'] != 'fd-snapshot-test-barrier':
                if case in ('exit-during', 'exit-before-pin', 'scale-exit'):
                    first.stdin.write(b'x'); first.stdin.flush(); first.wait(timeout=1)
                elif case == 'new-protected':
                    child(kind='p')
                elif case in ('new-unrelated', 'scale-new'):
                    child(2)
                elif case.startswith('representative-exit'):
                    first.stdin.write(b'r'); first.stdin.flush()
                    if first.stdout.readline() != b'ACK\n':
                        raise RuntimeError('representative mutation failed')
                action = True
            if row['subphase'] == 'fd-snapshot-test-barrier':
                fd_snapshots += 1
                commands = {'fd-finite-close': b'd', 'fd-finite-reuse': b'z', 'fd-reuse-protected': b'p'}
                command = commands.get(case) if fd_snapshots == 1 else None
                if case == 'fd-continuous-reuse':
                    command = b'z' if fd_snapshots % 2 else b'n'
                if command:
                    first.stdin.write(command); first.stdin.flush()
                    if first.stdout.readline() != b'ACK\n':
                        raise RuntimeError('FD mutation failed')
                p.stdin.write(b'.'); p.stdin.flush()
            elif row['phase'] == sync_phase and row['event'] == 'PHASE':
                p.stdin.write(b'.'); p.stdin.flush()
        rc = p.wait(timeout=8)
        elapsed = time.monotonic() - start
        for fd in inherited:
            os.close(fd)
        result = rows[-1]
        good = case in ('clear', 'scale', 'scale-exit', 'scale-new', 'raise-soft', 'exit-during', 'exit-before-pin', 'new-unrelated', 'representative-exit', 'fd-finite-close', 'fd-finite-reuse', 'leader-exit')
        checks = {'rc_expected': rc == 0 if good else rc == 70,
                  'complete_matches_rc': result['complete'] == (rc == 0),
                  'bounded_5s': elapsed < 5.0,
                  'limits': result['read_bytes'] <= 32 * 1024 * 1024 + 8192 and result['fds'] <= 131073}
        if case in ('protected-fd', 'unshared-protected', 'protected-cwd', 'protected-root', 'protected-loop', 'sticky-protected-exit', 'self-inherited-protected', 'leader-exit-protected', 'new-protected', 'representative-exit-protected', 'fd-reuse-protected'):
            checks['positive_occupancy'] = result['errno'] == 16
        if case == 'sticky-protected-exit':
            first.stdin.write(b'x'); first.stdin.flush(); first.wait(timeout=1)
            checks['busy_not_erased_after_exit'] = rc == 70 and result['errno'] == 16 and not result['complete']
        if case == 'representative-exit':
            checks['survivor_rescanned'] = result['retired_tasks'] == 1 and result['lifecycle_round'] >= 2 and result['fd_tables'] >= 5
        if case == 'leader-exit':
            checks['surviving_threads_covered'] = result['retired_tasks'] == 1 and result['processes'] == 5 and result['fd_tables'] >= 3
        if case.startswith('scale'):
            checks['target_scale'] = result['processes'] >= 1534 and result['fds'] >= 112000 and result['fd_tables'] >= (442 if case == 'scale-exit' else 443)
        if case == 'self-inherited-protected':
            checks['scanner_self_is_occupant'] = result['pid'] == result['self_pid'] and result['errno'] == 16
        if case == 'raise-soft':
            checks['own_soft_raised_only'] = result['nofile_before'] == 1024 and result['nofile_after'] == 8256
        if case == 'hard-low':
            checks['resource_failure'] = result['reason'] == 'process-local-handle-budget-unavailable'
        print(json.dumps({'case': case, 'rc': rc, 'elapsed': elapsed, 'result': result,
                          'checks': checks, 'stderr': p.stderr.read().decode(), 'kernel': os.uname().release}), flush=True)
        # PID namespace teardown kills any remaining test children. The harness
        # never signals a process outside its namespace or touches Android.
        return 0 if all(checks.values()) else 1
    finally:
        if loop_device:
            subprocess.run(['losetup', '--detach', loop_device], check=True)



def run():
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise RuntimeError('Linux VM root only')
    build = Path(tempfile.mkdtemp(prefix='e5-native-test-dynamic-', dir='/tmp'))
    scanner = build / 'scanner-integration'
    workload = build / 'workload'
    subprocess.run(['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                    '-DE5_SCANNER_HOST_TEST', '-DE5_SCANNER_LINUX_INTEGRATION',
                    str(HERE / 'native_occupancy_scanner.c'), '-o', str(scanner)], check=True)
    subprocess.run(['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', '-pthread',
                    str(HERE / 'lifecycle_workload.c'), '-o', str(workload)], check=True)
    cases = sys.argv[1:] or ['clear', 'exit-during', 'new-unrelated', 'new-protected', 'protected-fd',
                             'unshared-protected', 'protected-cwd', 'protected-root', 'protected-loop', 'sticky-protected-exit', 'self-inherited-protected',
                             'leader-exit', 'leader-exit-protected', 'exit-before-pin', 'representative-exit', 'representative-exit-protected', 'fd-finite-close', 'fd-finite-reuse', 'fd-reuse-protected', 'fd-continuous-reuse', 'raise-soft', 'hard-low', 'scale', 'scale-exit', 'scale-new']
    failures = 0
    for case in cases:
        r = subprocess.run(['unshare', '--mount', '--pid', '--fork', '--mount-proc',
                            sys.executable, '-B', str(Path(__file__).resolve()), '--inside', case,
                            str(scanner), str(workload)], capture_output=True, timeout=45)
        print(r.stdout.decode(), end='', flush=True)
        if r.stderr:
            print(json.dumps({'case': case, 'harness_stderr': r.stderr.decode()}), flush=True)
        failures += r.returncode != 0
    shutil.rmtree(build)
    return int(bool(failures))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--inside':
        raise SystemExit(inside(*sys.argv[2:]))
    raise SystemExit(run())
