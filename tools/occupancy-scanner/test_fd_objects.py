"""Explicit synthetic object metadata. Real O_PATH evidence is a separate Linux suite."""
import errno, json, os, subprocess, time, unittest
from test_lifecycle import LifecycleTests
from test_native_occupancy_scanner import TX, BOOT, OP

class ObjectTests(LifecycleTests):
    def obj(self,pid=100,fd=0,kind='pipe',ino=1,link=None):
        mode,magic={'pipe':('010600',0x50495045),'socket':('140600',0x534f434b),'fifo':('010600',0xf2f52010),
                    'named-socket':('140600',0xf2f52010),'regular':('100600',0x1021994),
                    'anon':('0600',0x09041934),'bad-mode':('100600',0x50495045),
                    'bad-fs':('010600',0x534f434b)}[kind]
        self.link(f'proc/{pid}/fd/{fd}', link or f'{kind}:[{ino}]')
        self.write(f'proc/{pid}/fd-object-meta/{fd}',f'{mode} 123 {ino} {magic:x}\n')
    def changing(self,kind):
        self.obj(kind=kind)
        return self.synchronized('',lambda n:self.obj(kind=kind,ino=n+1),True)
    def test_pipe_distinct_full_objects_converge_projection(self):
        rc,r,_=self.changing('pipe');self.assertEqual(rc,0);self.assertEqual(r['fds'],2);self.assertEqual(r['fd_stream_observations'],2);self.assertEqual(r['fd_differences'][0]['old_kind'],1)
    def test_socket_distinct_full_objects_converge_projection(self):
        rc,r,_=self.changing('socket');self.assertEqual(rc,0);self.assertEqual(r['fd_differences'][0]['new_kind'],2)
    def test_named_fifo_strict(self):self.assertEqual(self.changing('fifo')[0],70)
    def test_named_socket_inode_strict(self):self.assertEqual(self.changing('named-socket')[0],70)
    def test_memfd_regular_strict(self):self.assertEqual(self.changing('regular')[0],70)
    def test_anon_inode_strict(self):self.assertEqual(self.changing('anon')[0],70)
    def test_pipefs_wrong_mode_strict(self):self.assertEqual(self.changing('bad-mode')[0],70)
    def test_fifo_wrong_fs_strict(self):self.assertEqual(self.changing('bad-fs')[0],70)
    def test_stream_regular_alternation_stops(self):
        self.obj();rc,r,_=self.synchronized('',lambda n:self.obj(kind='regular' if n%2 else 'pipe',ino=n+1),True)
        self.assertEqual((rc,r['errno']),(70,errno.ESTALE))
    def test_stream_protected_path_sticky(self):
        self.obj();rc,r,_=self.synchronized('',lambda n:self.obj(ino=n+1,link='/data/e5linux/boot-os'),True)
        self.assertEqual((rc,r['errno']),(70,errno.EBUSY))
    def test_stream_class_cannot_hide_protected_inode(self):
        self.obj();st=(self.root/'data/e5linux/boot-os').stat()
        self.write('proc/100/fd-object-meta/0',f'010600 {st.st_dev} {st.st_ino} 50495045\n')
        r,_=self.bad();self.assertEqual(r['errno'],errno.EBUSY)
    def test_unresolved_lost_link_not_ignored(self):
        self.obj();(self.root/'proc/100/fd/0').unlink();(self.root/'proc/100/fd/0').mkdir()
        r,_=self.bad();self.assertFalse(r['complete'])
    def test_acquire_identity_drift_stops(self):
        self.obj();r,_=self.bad(fault='fd-object-identity-drift');self.assertEqual(r['errno'],errno.ESTALE)
    def test_acquire_permission_stops(self):
        self.obj();r,_=self.bad(fault='fd-object-open-eacces');self.assertEqual(r['errno'],errno.EACCES)
    def test_all_stream_items_still_counted(self):
        for n in range(20):self.obj(fd=n,ino=n+1)
        r,_=self.good();self.assertEqual(r['fds'],40);self.assertEqual(r['fd_stream_observations'],40)
    def test_global_diagnostics_cap_many_churning_tables(self):
        for pid in range(100,112):
            if pid!=100:self.proc(pid)
            for fd in range(20):self.obj(pid,fd,ino=pid*100+fd)
        env={**os.environ,'E5_SCANNER_TEST_FD_SYNC':'*'}
        deadline=int(time.clock_gettime(time.CLOCK_MONOTONIC)*1000)+5000
        p=subprocess.Popen([str(self.binary),'--test-root',str(self.root),'scan',TX,BOOT,OP,str(deadline)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
        rows=[];output=0
        try:
            for line in p.stdout:
                output+=len(line);r=json.loads(line);rows.append(r)
                if r['subphase']=='fd-snapshot-test-barrier':
                    for fd in range(20):self.obj(r['pid'],fd,ino=100000+len(rows)*100+fd)
                    p.stdin.write(b'.');p.stdin.flush()
            self.assertEqual(p.wait(timeout=8),0,rows[-1]);r=rows[-1]
            self.assertEqual(r['fd_diff_pairs_seen'],12);self.assertEqual(r['fd_diff_pairs_recorded'],4)
            self.assertEqual(len(r['fd_differences']),8);self.assertEqual(r['fd_diff_records_omitted'],232)
            self.assertLess(output,256*1024);self.assertTrue(all('link' not in d for d in r['fd_differences']))
        finally:
            if p.poll() is None:p.kill();p.wait()
            for f in (p.stdin,p.stdout,p.stderr):f.close()

def load_tests(loader,tests,pattern):
    return unittest.TestSuite(ObjectTests(n) for n in ObjectTests.__dict__ if n.startswith('test_'))
if __name__=='__main__':unittest.main(verbosity=2)
