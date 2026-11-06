"""Run the existing emulator installation gate; add retained-key rc5 upgrade check."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

root = Path(__file__).resolve().parents[1]
subprocess.run(['python3',str(root/'android/scripts/install_candidate_smoke.py')],check=True)
old = root/'station-draft/previous-candidate.apk'
urllib.request.urlretrieve('https://github.com/Denberg28/inventory/releases/download/android-v0.2.0-rc.5/Inventory-Android-v0.2.0-rc.5-Candidate.apk',old)
assert hashlib.sha256(old.read_bytes()).hexdigest() == '03fb8d9a728574142d2944887bc1e571933d3819b9b32e03a4aa3c6c4ec83c7c'
# Test old->new upgrade on a fresh disposable Candidate package. Preview stays installed.
subprocess.run(['adb','uninstall','ph.dronelab.inventory.candidate'],check=True,capture_output=True)
subprocess.run(['adb','install',str(old)],check=True,capture_output=True)
apk = root/'android/app/build/outputs/apk/candidate/app-candidate.apk'
r = subprocess.check_output(['adb','install','-r',str(apk)],text=True)
assert 'Success' in r
launch = subprocess.check_output(['adb','shell','am','start','-W','-n',
    'ph.dronelab.inventory.candidate/ph.dronelab.inventory.MainActivity'],text=True)
assert 'Status: ok' in launch
report = json.loads((root/'android/app/build/evidence/candidate-install-smoke.json').read_text())
report['retained_key_rc5_upgrade_install'] = 'PASS'
report['scope'] += '; empty rc5 Candidate to current Candidate package upgrade (data migration is not hardware validated)'
(root/'station-draft/Inventory-Station-INSTALL-CHECK.json').write_text(json.dumps(report,indent=2)+'\n')
old.unlink()
print('Exact signed APK installation and retained-key package upgrade: PASS')
