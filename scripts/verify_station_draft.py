"""Download only an explicitly selected draft, check source/signature/checksums before install."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[1]
tag = os.environ['STATION_RELEASE_TAG']
digest = os.environ['STATION_APK_SHA256']
assert re.fullmatch(r'station-v[0-9A-Za-z.\-]+', tag)
assert re.fullmatch('[0-9a-f]{64}', digest)
release = json.loads(subprocess.check_output(['gh', 'release', 'view', tag, '--json', 'isDraft,targetCommitish']))
assert release['isDraft'] is True, 'Never change a published release'
folder = root / 'station-draft'
folder.mkdir(exist_ok=False)
subprocess.run(['gh', 'release', 'download', tag, '--dir', str(folder)], check=True)
manifest = json.loads((folder / 'Inventory-Station-BUILD-MANIFEST.json').read_text())
source = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
assert source == manifest['source_commit']
# Draft releases have no tag ref until publication. Resolve their selected
# target now; publication pins that exact checked source SHA rather than a branch.
target = release['targetCommitish']
if re.fullmatch('[0-9a-f]{40}', target):
    assert target == source
else:
    assert subprocess.check_output(['git','rev-parse','refs/remotes/origin/'+target], text=True).strip() == source
for line in (folder / 'SHA256SUMS.txt').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert Path(name).name == name and re.fullmatch('[0-9a-f]{64}', expected)
    assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected, name
apk = folder / 'Inventory-Android-v0.3.0-rc.1-Candidate.apk'
assert hashlib.sha256(apk.read_bytes()).hexdigest() == digest == manifest['apk_sha256']
apksigner = Path(os.environ['ANDROID_HOME']) / 'build-tools/35.0.0/apksigner'
result = subprocess.check_output([str(apksigner),'verify','--verbose','--print-certs',str(apk)], text=True)
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in result
cert = re.search(r'Signer #1 certificate SHA-256 digest: ([0-9a-f]+)', result).group(1)
assert cert == manifest['certificate_sha256'] == '920d8d691dbedc3c2627363b915c78de516486775acc5c6f8b5234ebfa84f5e0'
# Reuse the existing installation/coexistence gate with the exact uploaded artifact.
out = root / 'android/app/build/outputs/apk/candidate'
out.mkdir(parents=True, exist_ok=True)
import shutil
shutil.copy2(apk, out / 'app-candidate.apk')
(out / 'output-metadata.json').write_text(json.dumps({'applicationId':'ph.dronelab.inventory.candidate',
    'elements':[{'versionCode':6, 'versionName':'0.3.0-rc.1', 'outputFile':'app-candidate.apk'}]}))
print('Draft source, checksums and retained Candidate certificate: PASS')
