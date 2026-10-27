"""Publish only the signed, installer-tested Candidate artifact; never include key recovery."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
request = json.loads((root / 'release-request.json').read_text())
assert request['kind'] == 'signed-candidate' and request['stage'] == 'prepare'
meta_path = root / 'app/build/outputs/apk/candidate/output-metadata.json'
meta = json.loads(meta_path.read_text())
element = meta['elements'][0]
assert len(meta['elements']) == 1 and meta['applicationId'] == request['package']
assert element['versionName'] == request['version'] and element['versionCode'] == request['version_code']
apk = meta_path.parent / element['outputFile']
source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root.parent, text=True).strip()
assert source == os.environ['GITHUB_SHA']
verifier = Path(os.environ['ANDROID_HOME']) / 'build-tools/35.0.0/apksigner'
signature = subprocess.check_output([str(verifier), 'verify', '--verbose', '--print-certs', str(apk)], text=True)
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signature
cert = re.search(r'Signer #1 certificate SHA-256 digest: ([0-9a-f]+)', signature).group(1)
if request.get('certificate_sha256'):
    assert cert == request['certificate_sha256'], 'Candidate signing identity changed'
suites = [ET.parse(p).getroot() for p in (root / 'app/build/test-results/testDebugUnitTest').glob('TEST-*.xml')]
tests = {k: sum(int(s.get(k, '0')) for s in suites) for k in ['tests', 'failures', 'errors', 'skipped']}
assert tests['tests'] and not any(tests[k] for k in ['failures', 'errors', 'skipped'])
lint = {}
for variant in ['debug', 'release', 'candidate']:
    issues = list(ET.parse(root / f'app/build/reports/lint-results-{variant}.xml').getroot().iter('issue'))
    lint[variant] = {'errors': sum(i.get('severity') in ['Error', 'Fatal'] for i in issues),
        'warnings': sum(i.get('severity') == 'Warning' for i in issues), 'ids': sorted({i.get('id') for i in issues})}
    assert lint[variant]['errors'] == 0
smoke = json.loads((root / 'app/build/evidence/candidate-install-smoke.json').read_text())
assert all(smoke[k] == 'PASS' for k in ['install', 'launch', 'same_apk_reinstall', 'coexistence_with_rc2_preview'])
assert smoke['apk_sha256'] == hashlib.sha256(apk.read_bytes()).hexdigest()
subprocess.run(['python3', str(root / 'scripts/package_source.py')], check=True)
output = root.parent / 'deliverables/publish'
output.mkdir(parents=True, exist_ok=True)
assert not list(output.iterdir()), 'Do not overwrite existing prepared assets'
base = 'Inventory-Android-v' + request['version']
shutil.copy2(apk, output / (base + '-Candidate.apk'))
shutil.copy2(root.parent / 'deliverables' / (base + '-Source-Build-Kit.zip'), output)
(output / (base + '-SIGNATURE.txt')).write_text(signature)
(output / (base + '-INSTALL-CHECK.json')).write_text(json.dumps(smoke, indent=2) + '\n')
manifest = {'version': request['version'], 'version_code': element['versionCode'], 'source_commit': source,
    'package': meta['applicationId'], 'label': 'Inventory Candidate', 'tier': 'signed test candidate',
    'signer_certificate_sha256': cert, 'tests': tests, 'lint': lint, 'install_check': smoke,
    'schema': 1, 'physical_phone': 'NOT TESTED',
    'build_workflow': f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
    'assets': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(output.iterdir())]}
(output / (base + '-BUILD-MANIFEST.json')).write_text(json.dumps(manifest, indent=2) + '\n')
notes = f"""# Inventory Android {request['version']} — signed Candidate installer

Download `{base}-Candidate.apk`. This APK is signed and its installation and initial
launch passed on Android API {smoke['android_api']} in an emulator. It installs as
**Inventory Candidate** (`{meta['applicationId']}`) beside earlier Inventory/Preview apps.
Do not uninstall or clear the old app. The Candidate has separate local records and
keys; copy records only through a verified encrypted `.dlinv` backup and restore.

This fixes the invalid unsigned installer downloads and includes PR #7 recovery protection:
a missing primary inventory file cannot silently initialize empty data over surviving
recovery copies. Both local recovery choices are available at failed startup. Features:
phone scanning, registration/edit/archive, issue/partial return, audited due-date changes,
live return balances, CSV and encrypted backups. Schema remains version 1.

Source: `{source}`. {tests['tests']} automated Android tests passed; debug/release/candidate
builds and lint passed (zero errors; retained warnings are listed in the manifest).
APK v2 signature verification, emulator installation, initial launch, same-APK reinstall
and coexistence with rc.2 Preview passed. This is a test candidate; physical camera,
credentials, Keystore, providers, power loss and real-phone migration are NOT TESTED.

Certificate SHA-256: `{cert}`. The signing key recovery is private and is deliberately
excluded from every public release/source artifact. Future Candidate updates must use
this key; another debug key is not an upgrade. Earlier releases and installed apps are
preserved for rollback. SHA256SUMS covers every other release asset.
"""
(output / (base + '-RELEASE-NOTES.md')).write_text(notes)
(output / (base + '-SHA256SUMS.txt')).write_text(''.join(
    hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in sorted(output.iterdir())))
print(json.dumps({'source_commit': source, 'certificate_sha256': cert, 'tests': tests, 'package': meta['applicationId'],
    'assets': [p.name for p in output.iterdir()]}, indent=2))
