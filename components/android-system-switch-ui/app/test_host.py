#!/usr/bin/env python3
"""Pure host matcher/state tests and manifest/capability assertions; never touches E5."""
from pathlib import Path
import json
import os, shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
JAVA=Path(os.environ['JAVA_HOME'])/'bin' if os.environ.get('JAVA_HOME') else Path(shutil.which('javac') or '/missing/javac').resolve().parent
NS='{http://schemas.android.com/apk/res/android}'

def main():
    manifest=ET.parse(ROOT/'AndroidManifest.xml').getroot()
    assert {x.attrib[NS+'name'] for x in manifest.findall('uses-permission')} == {
        'android.permission.FOREGROUND_SERVICE','android.permission.POST_NOTIFICATIONS'}
    app=manifest.find('application')
    assert app.attrib[NS+'allowBackup']=='false'
    services=app.findall('service')
    assert len(services)==2 and all(s.attrib[NS+'exported']=='false' for s in services)
    assert services[0].attrib[NS+'permission']=='android.permission.BIND_ACCESSIBILITY_SERVICE'
    assert not app.findall('receiver') and not app.findall('provider')
    spec=ET.parse(ROOT/'res/xml/accessibility_service.xml').getroot()
    assert spec.attrib[NS+'packageNames']=='com.android.systemui'
    assert spec.attrib[NS+'accessibilityEventTypes']=='typeWindowStateChanged'
    assert spec.attrib[NS+'canPerformGestures']=='false'
    sources='\n'.join(p.read_text() for p in (ROOT/'src').rglob('*.java'))
    for forbidden in ['Runtime.getRuntime(',
                      '.performAction(', 'dispatchGesture(', 'java.net.', 'java.io.File',
                      'getRootInActiveWindow(', 'TYPE_NOTIFICATION_STATE_CHANGED']:
        assert forbidden not in sources, forbidden
    assert sources.count('performGlobalAction(')==1
    assert sources.count('performGlobalAction(GLOBAL_ACTION_BACK)')==1
    assert sources.count('ProcessBuilder(')==1
    assert 'ProcessBuilder("/debug_ramdisk/su","-c",command(mode))' in sources
    assert 'private static String command(String mode)' in sources
    assert 'BACKEND_SHA256="1afeab4d8aa34c2cd6dd0679663fe52edd8a45b732b314c00a55ea77f9cb2fa2"' in sources
    with tempfile.TemporaryDirectory(prefix='e5-ui-host-') as tmp:
        classes=['MenuMatcher','VerifiedPowerMenu','SwitchBackend','StatusPresentation']
        subprocess.run([str(JAVA/'javac'),'--release','8','-encoding','UTF-8','-d',tmp,
            *[str(ROOT/'src/cn/e5/switchui'/f'{n}.java') for n in classes],
            str(ROOT/'tests/UiSafetyTest.java')],check=True)
        r=subprocess.run([str(JAVA/'java'),'-cp',tmp,'cn.e5.switchui.UiSafetyTest'],check=True,text=True,capture_output=True)
    result={'kind':'HOST_ONLY_UI_SAFETY','device_access':False,'matcher_and_state_cases':27,
        'stdout':r.stdout.strip(),'manifest_and_fixed_backend_boundary_checks':'PASS',
        'limits':['No Android runtime or actual event delivery test','No root process executed; no live backend or reboot acceptance']}
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/HOST_TESTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(r.stdout.strip())

if __name__=='__main__':main()
