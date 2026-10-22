#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile,json,os,shutil
R=Path(__file__).resolve().parent
J=Path(os.environ['JAVA_HOME'])/'bin' if os.environ.get('JAVA_HOME') else Path(shutil.which('javac') or '/missing/javac').resolve().parent
SDK=Path(os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME') or R/'build-sdk')
A=SDK/'platforms/android-33/android.jar'
with tempfile.TemporaryDirectory(prefix='e5-backend-host-') as d:
    subprocess.run([str(J/'javac'),'--release','8','-encoding','UTF-8','-cp',str(A),'-d',d,
        str(R/'src/cn/e5/switchui/BackendStatus.java'),str(R/'src/cn/e5/switchui/RootSession.java'),
        str(R/'tests/BackendSafetyTest.java')],check=True)
    r=subprocess.run([str(J/'java'),'-cp',d+':'+str(A),'cn.e5.switchui.BackendSafetyTest'],check=True,text=True,capture_output=True)
(R/'build').mkdir(exist_ok=True)
(R/'build/BACKEND_HOST_TESTS.json').write_text(json.dumps({'device_access':False,'root_process_started':False,'stdout':r.stdout.strip()},indent=2)+'\n')
print(r.stdout.strip())
