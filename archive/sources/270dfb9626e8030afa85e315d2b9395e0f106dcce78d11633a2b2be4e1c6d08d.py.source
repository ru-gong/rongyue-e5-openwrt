"""Real Linux isolated proc/O_PATH experiments; no Android or live binary.
Each case enters a new PID+mount namespace. Scanner is HOST_TEST+LINUX_INTEGRATION,
whose device gate stays 0. Synchronization hooks exist only in that test build.
"""
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
TX='0123456789abcdef';OP='d'*32
CASES={
 'many-stream-tables':('p','p',0), 'pipe-churn':('p','p',0), 'socket-churn':('s','s',0), 'bound-socket-fd-churn':('b','b',0),
 'named-fifo-churn':('f','f',70), 'socket-path-inode-churn':('u','u',70),
 'regular-churn':('r','r',70), 'memfd-churn':('m','m',70),
 'epoll-memfd-alternation':('e','m',70),
 'stream-to-protected':('p','P',70), 'stream-regular-alternation':('p','r',70),
 'mixed-regular-to-pipe':('r','p',70),'mixed-pipe-to-regular':('p','r',70),
 'mixed-original-protected':('P','p',70),'mixed-held-protected':('p','P',70),
 'mixed-after-held-protected':('p','P',70),'finite-close-before-pin':('p','d',0),
 'fault-open-enoent':('p',None,70),'fault-open-eacces':('p',None,70),'fault-open-enosys':('p',None,70),
 'stable-named-fifo':('f',None,0),'stable-path-socket':('u',None,0),
}
def inside(case,scanner,workload):
 if os.getpid()!=1 or os.geteuid()!=0:raise RuntimeError('private root PID1 only')
 td=tempfile.TemporaryDirectory(prefix='e5-native-test-object-',dir='/tmp');td._finalizer.detach()
 root=Path(td.name)/'sandbox';(root/'proc').mkdir(parents=True);(root/'sys/block').mkdir(parents=True);(root/'data/e5linux').mkdir(parents=True);(root/'objects').mkdir()
 protected=root/'data/e5linux/boot-os';protected.write_text('openwrt\n')
 subprocess.run(['mount','--bind','/proc',str(root/'proc')],check=True)
 first,mutate,expected=CASES[case]
 w=subprocess.Popen([workload,first,str(protected),str(root/'objects')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 initial=json.loads(w.stdout.readline());objects=[initial];workers={w.pid:w}
 if case=='many-stream-tables':
  for _ in range(11):
   extra=subprocess.Popen([workload,'p',str(protected),str(root/'objects')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);objects.append(json.loads(extra.stdout.readline()));workers[extra.pid]=extra
 boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();deadline=int(time.clock_gettime(time.CLOCK_BOOTTIME)*1000)+5000
 env=dict(os.environ)
 mixed=case.startswith('mixed-') or case=='finite-close-before-pin';env['E5_SCANNER_TEST_SYNC']='fd-tables'
 if mixed:env['E5_SCANNER_TEST_OBJECT_SYNC']=f'{w.pid}:400:'+('held' if case=='mixed-after-held-protected' else 'initial')
 else:env['E5_SCANNER_TEST_FD_SYNC']='*' if case=='many-stream-tables' else str(w.pid)
 if case.startswith('fault-open-'):env['E5_SCANNER_TEST_OPEN_FAULT']=f'{w.pid}:400:'+str({'fault-open-enoent':2,'fault-open-eacces':13,'fault-open-enosys':38}[case])
 p=subprocess.Popen([scanner,'--test-root',str(root),'scan',TX,boot,OP,str(deadline)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
 rows=[];snaps=0;start=time.monotonic()
 for line in p.stdout:
  r=json.loads(line);rows.append(r)
  if r['subphase'] in ('fd-snapshot-test-barrier','fd-object-test-barrier'):
   snaps+=1;command=mutate
   if case=='stream-regular-alternation':command='r' if snaps%2 else 'p'
   if case=='epoll-memfd-alternation':command='m' if snaps%2 else 'e'
   actor=workers.get(r['pid'])
   if command and actor:
    actor.stdin.write(command.encode());actor.stdin.flush();objects.append(json.loads(actor.stdout.readline()))
   p.stdin.write(b'.');p.stdin.flush()
  elif r['event']=='PHASE' and r['phase']=='fd-tables':p.stdin.write(b'.');p.stdin.flush()
 rc=p.wait(timeout=8);elapsed=time.monotonic()-start;r=rows[-1]
 checks={'rc_expected':rc==expected,'complete_expected':r['complete']==(expected==0),'within_5s':elapsed<5,'budget':r['fds']<=131073 and r['read_bytes']<=32*1024*1024+8192,'stdout_cap':sum(len(json.dumps(x)) for x in rows)<256*1024}
 if case in ('stream-to-protected','mixed-original-protected','mixed-held-protected','mixed-after-held-protected'):checks['protected_sticky']=r['errno']==16
 if case in ('mixed-regular-to-pipe','mixed-pipe-to-regular'):checks['mixed_identity_rejected']=r['detail']=='fd-object-identity-drift' and r['errno']==116
 if case=='finite-close-before-pin':
  checks['closed_slot_confirmed_not_discarded']=(r['fd_closed_observed']==1 and r['fd_closed_confirmed']==1 and r['fd_closed_rejected']==0 and r['fd_snapshots_discarded']==0 and r['fd_snapshot_attempts']==2*r['fd_tables'] and r['fd_snapshots_complete']==2*r['fd_tables'])
  checks['all_fd_observations_counted']=r['fds']>=40
 if case=='fault-open-enoent':checks['three_failed_table_attempts']=r['fd_snapshots_discarded']==3 and r['fd_last_acquire_errno']==2
 if case.startswith('fault-open-'):
  checks['persistent_acquire_failure_not_ignored']=rc==70 and not r['complete']
  checks['specific_errno']=r['errno']=={'fault-open-enoent':116,'fault-open-eacces':13,'fault-open-enosys':38}[case]
 if case=='many-stream-tables':
  checks['global_diagnostic_pair_cap']=r['fd_diff_pairs_seen']==12 and r['fd_diff_pairs_recorded']==4
  checks['global_diagnostic_record_cap']=len(r['fd_differences'])==4 and r['fd_diff_records_omitted']==8
  checks['all_real_workers_seen']=r['fd_tables']==14 and r['processes']==14
 if case in ('pipe-churn','socket-churn','bound-socket-fd-churn'):
  k=1 if case=='pipe-churn' else 2
  diffs=[d for d in r['fd_differences'] if d['pid']==w.pid and d['fd']==400]
  checks['held_type_magic_proven']=initial['fs']==(0x50495045 if k==1 else 0x534f434b)
  checks['actual_changed_objects']=len(objects)>=3 and objects[0]['ino']!=objects[1]['ino']
  checks['native_classification']=len(diffs)==1 and diffs[0]['old_kind']==k and diffs[0]['new_kind']==k
  checks['exact_two_full_snapshots']=snaps==2
 if case in ('named-fifo-churn','socket-path-inode-churn','regular-churn','memfd-churn','epoll-memfd-alternation'):
  checks['strict_nonstream_failure']=r['detail']=='fd-table-not-converged' and snaps==3
  checks['strict_native_classification']=all(x['old_kind']==0 and x['new_kind']==0 for x in r['fd_differences'] if x['fd']==400)
 print(json.dumps({'case':case,'rc':rc,'elapsed':elapsed,'checks':checks,'result':r,'object_observations':objects,'kernel':os.uname().release,'stderr':p.stderr.read().decode()}),flush=True)
 return 0 if all(checks.values()) else 1

def run():
 if sys.platform!='linux' or os.geteuid()!=0:raise RuntimeError('isolated Linux VM only')
 build=Path(tempfile.mkdtemp(prefix='e5-native-test-object-build-',dir='/tmp'))
 scanner=build/'scanner';workload=build/'workload'
 subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-O2','-DE5_SCANNER_HOST_TEST','-DE5_SCANNER_LINUX_INTEGRATION',str(HERE/'native_occupancy_scanner.c'),'-o',str(scanner)],check=True)
 subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-O2',str(HERE/'fd_object_workload.c'),'-o',str(workload)],check=True)
 failures=0
 for case in sys.argv[1:] or CASES:
  p=subprocess.run(['unshare','--mount','--pid','--fork','--mount-proc',sys.executable,'-B',str(Path(__file__).resolve()),'--inside',case,str(scanner),str(workload)],capture_output=True,timeout=15)
  print(p.stdout.decode(),end='',flush=True)
  if p.stderr:print(json.dumps({'case':case,'harness_stderr':p.stderr.decode()}),flush=True)
  failures+=p.returncode!=0
 shutil.rmtree(build);return int(bool(failures))
if __name__=='__main__':raise SystemExit(inside(*sys.argv[2:]) if len(sys.argv)>1 and sys.argv[1]=='--inside' else run())
