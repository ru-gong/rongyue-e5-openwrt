"""Native HOST_TEST regressions with synthetic proc identities, never Android I/O."""
import errno,json,os,shutil,subprocess,time,unittest
from pathlib import Path
from test_native_occupancy_scanner import ScannerTests,BOOT,TX,OP

class KCMPTests(ScannerTests):
 def member(self,pid,table=100,tgid=100):
  if pid!=100:self.proc(pid)
  self.write(f'proc/{pid}/status',f'Name:\ttest\nTgid:\t{tgid}\n')
  self.write(f'proc/{pid}/files-table',str(table)+'\n')
 def capability(self,fault=None,real=False):
  env=dict(os.environ)
  if fault:env['E5_SCANNER_TEST_FAULT']=fault
  if real:env['E5_SCANNER_TEST_REAL_KCMP']='1'
  d=int(time.clock_gettime(time.CLOCK_MONOTONIC)*1000)+6000
  p=subprocess.run([str(self.binary),'--test-root',str(self.root),'capability',TX,BOOT,OP,str(d)],capture_output=True,timeout=8,env=env)
  return p,json.loads(p.stdout.splitlines()[-1])
 def test_shared_table_scanned_once(self):
  self.member(100);self.member(101)
  r,_=self.good();self.assertEqual((r['fds'],r['fd_tables'],r['shared_tasks'],r['kcmp_calls']),(2,1,1,2))
 def test_same_tgid_distinct_table_scanned(self):
  self.member(100);self.member(101,101)
  r,_=self.good();self.assertEqual((r['fds'],r['fd_tables'],r['shared_tasks']),(4,2,0))
 def test_same_tgid_unshared_protected_fd_rejected(self):
  self.member(100);self.member(101,101);self.link('proc/101/fd/0','/data/e5linux/boot-os')
  r,_=self.bad();self.assertEqual(r['errno'],errno.EBUSY)
 def test_cross_tgid_same_table_not_deduplicated(self):
  self.member(100);self.member(101,100,101)
  r,_=self.good();self.assertEqual((r['fds'],r['fd_tables'],r['shared_tasks'],r['kcmp_calls']),(4,2,0,0))
 def test_distinct_result_two(self):
  self.member(100);self.member(101,101);p,r,_=self.run_scan(fault='kcmp-distinct-2')
  self.assertEqual(p.returncode,0);self.assertEqual(r['fd_tables'],2)
 def test_distinct_result_three(self):
  self.member(100);self.member(101,101);p,r,_=self.run_scan(fault='kcmp-distinct-3')
  self.assertEqual(p.returncode,0);self.assertEqual(r['fd_tables'],2)
 def test_eperm_no_fallback(self):
  self.member(101);r,_=self.bad(fault='kcmp-eperm');self.assertEqual((r['errno'],r['fd_tables']),(errno.EPERM,0))
 def test_enosys_no_fallback(self):
  self.member(101);r,_=self.bad(fault='kcmp-enosys');self.assertEqual(r['errno'],errno.ENOSYS)
 def test_eacces_no_fallback(self):
  self.member(101);r,_=self.bad(fault='kcmp-eacces');self.assertEqual(r['errno'],errno.EACCES)
 def test_einval_no_fallback(self):
  self.member(101);r,_=self.bad(fault='kcmp-einval');self.assertEqual(r['errno'],errno.EINVAL)
 def test_invalid_result_no_fallback(self):
  self.member(101);r,_=self.bad(fault='kcmp-invalid-result');self.assertEqual(r['errno'],errno.EPROTO)
 def test_sigsys_fails_closed(self):
  import signal
  self.member(101);r,_=self.bad(fault='kcmp-sigsys');self.assertEqual(r['cancel_signal'],signal.SIGSYS)
 def test_final_shared_to_unshared_refused(self):
  self.member(101);r,_=self.bad(fault='kcmp-final-split');self.assertEqual(r['reason'],'final-files-relation-changed-unknown')
 def test_final_representative_gone_refused(self):
  self.member(101);r,_=self.bad(fault='kcmp-final-esrch');self.assertEqual(r['errno'],errno.ESRCH)
 def test_final_representative_reused_refused(self):
  self.member(101);raw=(self.root/'proc/100/stat').read_text();self.write('proc/100/stat.final',raw.replace(' 1000 ',' 9999 '));r,_=self.bad(fault='kcmp-final-reused');self.assertEqual(r['errno'],errno.ESTALE)
 def test_final_deadline_refused(self):
  self.member(101);r,_=self.bad(fault='kcmp-final-expired');self.assertEqual(r['errno'],errno.ETIMEDOUT)
 def test_shared_task_cwd_not_skipped(self):
  self.member(101);self.link('proc/101/cwd','/data/e5linux');self.bad()
 def test_shared_task_root_not_skipped(self):
  self.member(101);self.link('proc/101/root','/data/e5linux');self.bad()
 def test_shared_task_namespace_not_skipped(self):
  self.member(101);self.link('proc/101/ns/mnt','mnt:[2000]');self.write('proc/101/mountinfo','1 0 0:1 /e5linux /x rw - rootfs rootfs rw\n');self.bad()
 def test_missing_status_refused(self):
  (self.root/'proc/100/status').unlink();self.bad()
 def test_duplicate_tgid_refused(self):
  self.write('proc/100/status','Tgid:\t100\nTgid:\t100\n');self.bad()
 def test_invalid_tgid_refused(self):
  self.write('proc/100/status','Tgid:\t-1\n');self.bad()
 def test_kernel_empty_fd_independent(self):
  self.proc(101,flags=0x00200000);self.write('proc/101/status','Tgid:\t100\n');(self.root/'proc/101/fd/0').unlink()
  r,_=self.good();self.assertEqual((r['fd_tables'],r['fds'],r['kcmp_calls']),(2,2,0))
 def large(self,cross=False):
  for fd in range(1,128):self.link(f'proc/100/fd/{fd}',f'pipe:[{fd+1}]')
  for pid in range(101,1125):
   self.member(pid,100,pid if cross else 100)
   shutil.rmtree(self.root/f'proc/{pid}/fd');(self.root/f'proc/{pid}/fd').symlink_to(self.root/'proc/100/fd')
 def test_1025_tasks_shared_128_fds_remain_bounded(self):
  self.large();r,_=self.good();self.assertEqual((r['processes'],r['fds'],r['fd_tables'],r['shared_tasks']),(1025,256,1,1024))
 def test_genuine_traversal_cap_still_131072(self):
  self.large(cross=True);r,_=self.bad();self.assertEqual((r['fds'],r['errno'],r['detail']),(131073,errno.E2BIG,'fd-entry-limit'))
 def test_capability_fixture_success(self):
  p,r=self.capability();self.assertEqual(p.returncode,0);self.assertTrue(r['capability_shared'] and r['capability_distinct']);self.assertEqual(r['processes'],0)
 def test_capability_fixture_failure(self):
  p,r=self.capability('capability-eperm');self.assertEqual(p.returncode,70);self.assertFalse(r['complete'])
 def test_capability_fixture_sigsys(self):
  p,r=self.capability('capability-sigsys');self.assertEqual(p.returncode,70);self.assertFalse(r['complete'])
 @unittest.skipUnless(__import__('sys').platform.startswith('linux'),'Linux actual owned-child KCMP only')
 def test_linux_real_owned_children_kcmp(self):
  # Actual Linux syscalls in isolated HOST_TEST, no /data and no device API.
  p,r=self.capability(real=True);self.assertEqual(p.returncode,0,(r,p.stderr));self.assertTrue(r['capability_shared'] and r['capability_distinct']);self.assertTrue(r['capability_children_reaped'])
 @unittest.skipUnless(__import__('sys').platform.startswith('linux'),'Linux owned child cleanup only')
 def test_linux_actual_children_cancelled_reaped(self):
  p,r=self.capability('capability-cancel-after-clone',real=True);self.assertEqual(p.returncode,70);self.assertTrue(r['capability_children_reaped'])
 @unittest.skipUnless(__import__('sys').platform.startswith('linux'),'Linux owned child cleanup only')
 def test_linux_actual_children_expired_reaped(self):
  p,r=self.capability('capability-expire-after-clone',real=True);self.assertEqual(p.returncode,70);self.assertTrue(r['capability_children_reaped'])
 @unittest.skipUnless(__import__('sys').platform.startswith('linux'),'Linux owned child cleanup only')
 def test_linux_actual_children_sigsys_reaped(self):
  p,r=self.capability('capability-sigsys-after-clone',real=True);self.assertEqual(p.returncode,70);self.assertTrue(r['capability_children_reaped'])

def load_tests(loader,tests,pattern):
 names=[name for name in KCMPTests.__dict__ if name.startswith('test_')]
 return unittest.TestSuite(KCMPTests(name) for name in names)
if __name__=='__main__':unittest.main(verbosity=2)
