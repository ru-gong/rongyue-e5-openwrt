"""Controlled synthetic proc lifecycle; real Linux cases are separate."""
import errno, json, os, shutil, subprocess, time, unittest
from test_native_occupancy_scanner import ScannerTests, TX, BOOT, OP

class LifecycleTests(ScannerTests):
    def synchronized(self, phase, change, fd=False):
        env={**os.environ, ('E5_SCANNER_TEST_FD_SYNC' if fd else 'E5_SCANNER_TEST_SYNC'): ('100' if fd else phase)}
        deadline=int(time.clock_gettime(time.CLOCK_MONOTONIC)*1000)+5000
        p=subprocess.Popen([str(self.binary),'--test-root',str(self.root),'scan',TX,BOOT,OP,str(deadline)], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
        rows=[]; count=0
        try:
            for line in p.stdout:
                row=json.loads(line); rows.append(row)
                match=row['event']=='PHASE' and (row['subphase']=='fd-snapshot-test-barrier' if fd else row['phase']==phase)
                if match:
                    count+=1; change(count); p.stdin.write(b'.');p.stdin.flush()
            rc=p.wait(timeout=8); self.assertEqual(rows[-1]['event'],'RESULT')
            return rc,rows[-1],rows
        finally:
            if p.poll() is None:p.kill();p.wait(timeout=2)
            for stream in (p.stdin,p.stdout,p.stderr):stream.close()

    def state(self, state):
        p=self.root/'proc/100/stat';s=p.read_text();p.write_text(s.replace(') S ',') '+state+' '))

    def test_unpinned_disappearance_covered_by_complete_closing_set(self):
        self.proc(101)
        def change(n):shutil.rmtree(self.root/'proc/100')
        rc,r,_=self.synchronized('pin-process-identities',change)
        self.assertEqual(rc,0);self.assertEqual(r['retired_tasks'],0);self.assertEqual(r['observed_identities'],1)

    def test_unpinned_persistent_missing_stat_stops_three_rounds(self):
        (self.root/'proc/100/stat').unlink()
        r,_=self.bad();self.assertEqual(r['reason'],'lifecycle-not-converged-unknown');self.assertEqual(r['observed_identities'],0)

    def test_new_identity_protected_is_scanned_next_round(self):
        def change(n):
            if n==1:self.proc(101);self.link('proc/101/fd/0','/data/e5linux/boot-os')
        rc,r,_=self.synchronized('final-process-identities',change)
        self.assertEqual((rc,r['errno'],r['lifecycle_round']),(70,errno.EBUSY,2))

    def test_new_identity_each_round_cannot_reset_cap(self):
        rc,r,_=self.synchronized('final-process-identities',lambda n:self.proc(100+n))
        self.assertEqual(rc,70);self.assertEqual(r['reason'],'lifecycle-not-converged-unknown');self.assertEqual(r['observed_identities'],4)
        self.assertGreater(r['fds'],2)

    def test_synthetic_numeric_reuse_old_z_new_protected_is_not_cached(self):
        def change(n):
            if n!=1:return
            self.state('Z');(self.root/'proc/100').rename(self.root/'held-old-proc')
            self.proc(100,start=9999);self.link('proc/100/fd/0','/data/e5linux/boot-os')
        rc,r,_=self.synchronized('final-process-identities',change)
        self.assertEqual((rc,r['errno'],r['retired_tasks'],r['observed_identities']),(70,errno.EBUSY,1,2))

    def test_synthetic_replacement_without_old_exit_is_unknown(self):
        def change(n):
            if n!=1:return
            (self.root/'proc/100').rename(self.root/'held-old-proc');self.proc(100,start=9999)
        rc,r,_=self.synchronized('final-process-identities',change)
        self.assertEqual((rc,r['errno'],r['retired_tasks']),(70,errno.ESTALE,0))

    def test_same_pinned_z_allows_missing_namespace(self):
        def change(n):self.state('Z');(self.root/'proc/100/ns/mnt').unlink()
        rc,r,_=self.synchronized('final-process-identities',change)
        self.assertEqual((rc,r['retired_tasks']),(0,1))

    def test_missing_child_link_does_not_retire_live_task(self):
        def change(n):(self.root/'proc/100/cwd').unlink()
        rc,r,_=self.synchronized('processes',change)
        self.assertEqual(rc,70);self.assertEqual(r['retired_tasks'],0)

    def test_finite_fd_close_requires_two_new_matching_snapshots(self):
        def change(n):
            if n==1:(self.root/'proc/100/fd/0').unlink()
        rc,r,rows=self.synchronized('',change,True)
        self.assertEqual(rc,0);self.assertEqual(sum(x['subphase']=='fd-snapshot-test-barrier' for x in rows),3)

    def test_finite_same_number_replacement_requires_rescan(self):
        def change(n):
            if n==1:self.link('proc/100/fd/0','pipe:[2]')
        rc,r,rows=self.synchronized('',change,True)
        self.assertEqual((rc,r['fds']),(0,3))

    def test_same_number_replacement_to_protected_is_busy(self):
        def change(n):
            if n==1:self.link('proc/100/fd/0','/data/e5linux/boot-os')
        rc,r,_=self.synchronized('',change,True)
        self.assertEqual((rc,r['errno']),(70,errno.EBUSY))

    def test_continuous_fd_replacement_never_ignores_entry(self):
        rc,r,_=self.synchronized('',lambda n:self.link('proc/100/fd/0',f'pipe:[{n+1}]'),True)
        self.assertEqual((rc,r['errno'],r['fds']),(70,errno.ESTALE,3));self.assertEqual(r['detail'],'fd-table-not-converged')

def load_tests(loader,tests,pattern):
    return unittest.TestSuite(LifecycleTests(n) for n in LifecycleTests.__dict__ if n.startswith('test_'))
if __name__=='__main__':unittest.main(verbosity=2)
