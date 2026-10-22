#!/usr/bin/env python3
"""Host-only SDK/JDK build. No adb, package installation, root execution or device discovery."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
JAVA_BIN = Path(os.environ['JAVA_HOME'])/'bin' if os.environ.get('JAVA_HOME') else Path(shutil.which('javac') or '/missing/javac').resolve().parent
SDK = Path(os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME') or ROOT/'build-sdk')
BT = SDK / 'build-tools' / os.environ.get('ANDROID_BUILD_TOOLS_VERSION', '35.0.0')
ANDROID = SDK / 'platforms/android-33/android.jar'
OUT = ROOT / 'build'

def run(args):
    env = dict(os.environ, JAVA_HOME=str(JAVA_BIN.parent))
    subprocess.run([str(x) for x in args], check=True, env=env)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    for p in [JAVA_BIN/'javac', BT/'aapt2', BT/'d8', ANDROID]:
        if not p.is_file(): raise SystemExit(f'Missing host build dependency: {p}')
    for p in [OUT/'classes', OUT/'dex', OUT/'generated']:
        if p.exists(): shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
    run([BT/'aapt2', 'compile', '--dir', ROOT/'res', '-o', OUT/'resources.zip'])
    run([BT/'aapt2', 'link', '-o', OUT/'resources.apk', '-I', ANDROID,
         '--manifest', ROOT/'AndroidManifest.xml', '--java', OUT/'generated',
         '--min-sdk-version', '33', '--target-sdk-version', '33', OUT/'resources.zip'])
    java=sorted((ROOT/'src').rglob('*.java'))+sorted((OUT/'generated').rglob('*.java'))
    run([JAVA_BIN/'javac', '--release', '8', '-encoding', 'UTF-8', '-cp', ANDROID,
         '-d', OUT/'classes', *java])
    run([BT/'d8', '--min-api', '33', '--lib', ANDROID, '--output', OUT/'dex',
         *sorted((OUT/'classes').rglob('*.class'))])
    apk=OUT/'e5-switch-ui-review-unsigned.apk'
    with zipfile.ZipFile(OUT/'resources.apk') as source, zipfile.ZipFile(apk,'w') as dest:
        for info in source.infolist(): dest.writestr(info,source.read(info.filename))
        for p in sorted((OUT/'dex').glob('*.dex')):
            dest.write(p,p.name,compress_type=zipfile.ZIP_DEFLATED)
    source_paths=sorted([ROOT/'AndroidManifest.xml', ROOT/'build.py',
        *list((ROOT/'src').rglob('*.java')), *list((ROOT/'res').rglob('*.xml'))])
    profile_source=(ROOT/'src/cn/e5/switchui/VerifiedPowerMenu.java').read_text()
    record={'kind':'HOST_ONLY_UI_REVIEW_BUILD','device_access':False,
        'apk_signed':False, 'backend_adapter_enabled':False, 'public_reference_only':True,
        'backend_device_connection_verified':False,
        'menu_fingerprint_verified':'true, "' in profile_source,
        'menu_observer_logging':'ENABLED=true' in (ROOT/'src/cn/e5/switchui/MenuDiagnostic.java').read_text(),
        'min_sdk':33,'target_sdk':33,'apk':str(apk.relative_to(ROOT)),
        'apk_bytes':apk.stat().st_size,'apk_sha256':sha(apk),
        'sources':{str(p.relative_to(ROOT)):sha(p) for p in source_paths},
        'tool_inputs':{'android_jar_sha256':sha(ANDROID),'aapt2_sha256':sha(BT/'aapt2')},
        'not_proven':['real_menu_event_match','overlay_placement','real_touch_operation',
            'root_authorization','backend_execution','reboot_or_default_change']}
    (OUT/'BUILD.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['kind','apk_bytes','apk_sha256','apk_signed']}))

if __name__ == '__main__': main()
