"""Install the exact signed APK on an emulator, alongside the old Preview package."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
import time

root = Path(__file__).resolve().parents[1]
meta_path = root / 'app/build/outputs/apk/candidate/output-metadata.json'
meta = json.loads(meta_path.read_text())
apk = meta_path.parent / meta['elements'][0]['outputFile']
package = 'ph.dronelab.inventory.candidate'
assert meta['applicationId'] == package
output = root / 'app/build/evidence'
output.mkdir(parents=True, exist_ok=True)
def command(*args, timeout=120):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()
old = root / 'app/build/previous-preview.apk'
urllib.request.urlretrieve('https://github.com/Denberg28/inventory/releases/download/android-v0.2.0-rc.2/Inventory-Android-v0.2.0-rc.2-Preview.apk', old)
assert hashlib.sha256(old.read_bytes()).hexdigest() == 'a1b2070c75e2f2fe1a6ce6e912f7133338ce827b4261e41a1c3538c836d8b0b2'
old_install = command('adb', 'install', '-r', str(old))
assert 'Success' in old_install
install = command('adb', 'install', '-r', str(apk))
assert 'Success' in install
assert command('adb', 'shell', 'pm', 'path', 'ph.dronelab.inventory.preview').startswith('package:')
assert command('adb', 'shell', 'pm', 'path', package).startswith('package:')
command('adb', 'logcat', '-c')
launch = command('adb', 'shell', 'am', 'start', '-W', '-n', package + '/ph.dronelab.inventory.MainActivity')
assert 'Status: ok' in launch
# This only allows process startup; it is not a phone credential/Keystore test.
time.sleep(2)
assert command('adb', 'shell', 'pidof', package)
reinstall = command('adb', 'install', '-r', str(apk))
assert 'Success' in reinstall
runtime = command('adb', 'logcat', '-d', '-s', 'AndroidRuntime')
assert not ('FATAL EXCEPTION' in runtime and package in runtime)
report = {'package': package, 'version_code': meta['elements'][0]['versionCode'],
    'android_api': command('adb', 'shell', 'getprop', 'ro.build.version.sdk'),
    'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
    'install': 'PASS', 'launch': 'PASS', 'same_apk_reinstall': 'PASS',
    'coexistence_with_rc2_preview': 'PASS', 'physical_phone': 'NOT TESTED',
    'scope': 'Emulator package installation/coexistence and initial screen/process launch only'}
(output / 'candidate-install-smoke.json').write_text(json.dumps(report, indent=2) + '\n')
(output / 'candidate-install-log.txt').write_text(old_install + '\n' + install + '\n' + launch + '\n' + reinstall + '\n')
print(json.dumps(report, indent=2))
