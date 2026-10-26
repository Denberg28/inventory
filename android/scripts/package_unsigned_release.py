"""Package a verified unsigned Preview build without changing signing identity."""
import argparse
import hashlib
import json
import pathlib
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

root = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--source-commit', required=True)
args = parser.parse_args()
if not re.fullmatch(r'[0-9a-f]{40}', args.source_commit):
    raise SystemExit('A complete source commit SHA is required')
repo = root.parent
if (repo / '.git').exists():
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    if actual != args.source_commit:
        raise SystemExit('Source commit does not match checkout')
request = json.loads((root / 'release-request.json').read_text())
version = re.search(r"versionName '([^']+)'", (root / 'app/build.gradle').read_text()).group(1)
if request['version'] != version or request['kind'] != 'unsigned-preview-build':
    raise SystemExit('Release request does not match the configured unsigned build')
meta_path = root / 'app/build/outputs/apk/debug/output-metadata.json'
meta = json.loads(meta_path.read_text())
if meta['applicationId'] != request['package'] or len(meta['elements']) != 1:
    raise SystemExit('Unexpected package identity or split APK output')
element = meta['elements'][0]
if element['versionName'] != version or element['versionCode'] != 3:
    raise SystemExit('APK version does not match this release')
apk = meta_path.parent / element['outputFile']
if apk.parent.resolve() != meta_path.parent.resolve() or apk.suffix != '.apk':
    raise SystemExit('Unexpected APK output path')
data = apk.read_bytes()
with zipfile.ZipFile(apk) as z:
    if z.testzip() is not None or 'AndroidManifest.xml' not in z.namelist() or 'classes.dex' not in z.namelist():
        raise SystemExit('APK is corrupt or incomplete')
    if any(n.upper().startswith('META-INF/') and n.upper().endswith(('.RSA', '.DSA', '.EC', '.SF')) for n in z.namelist()):
        raise SystemExit('Refusing an APK containing a JAR signing certificate')
eocd = data.rfind(b'PK\x05\x06')
if eocd < 0 or len(data) - eocd < 22:
    raise SystemExit('Invalid APK ZIP directory')
central_offset = struct.unpack_from('<I', data, eocd + 16)[0]
if data[max(0, central_offset - 16):central_offset] == b'APK Sig Block 42':
    raise SystemExit('Refusing an APK with an Android signing block')
suites = [ET.parse(p).getroot() for p in (root / 'app/build/test-results/testDebugUnitTest').glob('TEST-*.xml')]
tests = {key: sum(int(s.get(key, '0')) for s in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
if not tests['tests'] or any(tests[k] for k in ['failures', 'errors', 'skipped']):
    raise SystemExit('Required unit tests did not all pass')
lint = {}
for variant in ['debug', 'release']:
    issues = list(ET.parse(root / f'app/build/reports/lint-results-{variant}.xml').getroot().iter('issue'))
    lint[variant] = {
        'errors': sum(i.get('severity') in ['Error', 'Fatal'] for i in issues),
        'warnings': sum(i.get('severity') == 'Warning' for i in issues),
        'ids': sorted({i.get('id') for i in issues}),
    }
    if lint[variant]['errors']:
        raise SystemExit(f'{variant} lint contains errors')
subprocess.run(['python3', str(root / 'scripts/package_source.py')], check=True)
output = repo / 'deliverables/publish'
output.mkdir(parents=True, exist_ok=True)
if list(output.iterdir()):
    raise SystemExit('Publishing directory must be empty; existing artifacts were preserved')
base = f'Inventory-Android-v{version}'
preview = output / f'{base}-Preview-UNSIGNED.apk'
shutil.copy2(apk, preview)
kit = output / f'{base}-Source-Build-Kit.zip'
shutil.copy2(repo / 'deliverables' / kit.name, kit)
assets = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in [preview, kit]]
manifest = {
    'version': version,
    'source_commit': args.source_commit,
    'tier': 'unsigned build prerelease; not installable until signed',
    'package': meta['applicationId'],
    'version_code': element['versionCode'],
    'signing': 'UNSIGNED; no new signing identity generated',
    'required_existing_certificate_sha256': 'df5a504e375d94a473b043c8e903fcee3b3805c9f0cde4c2b5af95c248d67025',
    'schema': 1,
    'tests': tests,
    'lint': lint,
    'physical_device': 'NOT TESTED',
    'toolchain': {'java': 17, 'gradle': '8.9', 'agp': '8.7.3', 'compile_target_sdk': 35, 'min_sdk': 26, 'build_tools': '35.0.0'},
    'assets': assets,
}
(output / f'{base}-BUILD-MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
notes = f"""# Inventory Android v{version} — unsigned Preview build

**This APK is unsigned and cannot be installed yet.** It preserves the existing
`ph.dronelab.inventory.preview` package. An in-place rc.2 Preview update requires the
original signing key with certificate SHA-256:
`{manifest['required_existing_certificate_sha256']}`.
No replacement key or package identity was created. Keep the installed app and its data;
do not uninstall or clear data to work around signing. This release makes the verified
build and matching source available while signed installation remains blocked.

Changes: audited open-loan return-date changes with mandatory reasons, preservation of
custody/original issue details, and live return balances/held-condition warnings.
Routine returns retain one save action. Schema and backup format remain version 1.

Source commit: `{args.source_commit}`.
Validation: {tests['tests']} Android tests passed, zero failures/errors/skipped. Debug
and release lint have zero errors; the manifest records retained warnings. Preview
unsigned and production unsigned variants were built. The build workflow records the
exact tasks and checks. Physical camera, credentials, Keystore, document providers,
power-loss, accessibility and installation/upgrade remain NOT TESTED; no stable claim.

Artifacts: unsigned Preview APK, standalone source/build kit, build manifest, these
notes and SHA256SUMS. SHA256SUMS covers every other asset; the manifest gives APK/source
hashes. The installed rc.2 app and previous GitHub releases are preserved for rollback.
Use verified external encrypted `.dlinv` backups; CSV is not a full custody/history backup.

Build: from the source kit run `./gradlew -PinventoryUnsignedPreview=true
 testDebugUnitTest lintDebug lintRelease assembleDebug assembleRelease` on one line,
using Java 17 and the pinned Android toolchain. Signing/distribution requires the existing
Preview key; the key is deliberately absent from source and release assets.
"""
(output / f'{base}-RELEASE-NOTES.md').write_text(notes)
sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in sorted(output.iterdir()))
(output / f'{base}-SHA256SUMS.txt').write_text(sums)
print(json.dumps({'version': version, 'tests': tests, 'output': str(output), 'assets': sorted(p.name for p in output.iterdir())}, indent=2))
