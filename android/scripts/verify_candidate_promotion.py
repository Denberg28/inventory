"""Bind a retained-key promotion to the exact verified artifact and source."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

repo = Path(__file__).resolve().parents[2]
request = json.loads((repo / 'android/release-request.json').read_text())
assert request['kind'] == 'signed-candidate' and request['stage'] == 'publish'
assert request['signing_backup_saved'] is True
assert request['initial_signing_bootstrap'] is False
folder = repo / 'publish'
manifest_file = next(folder.glob('*-BUILD-MANIFEST.json'))
manifest = json.loads(manifest_file.read_text())
assert manifest['version'] == request['version'] and manifest['package'] == request['package']
assert manifest['source_commit'] == request['source_commit']
assert manifest['version_code'] == request['version_code']
assert manifest['tests']['tests'] > 0
assert manifest['signer_certificate_sha256'] == request['certificate_sha256']
assert manifest['tests']['failures'] == manifest['tests']['errors'] == manifest['tests']['skipped'] == 0
assert all(manifest['install_check'][k] == 'PASS' for k in ['install', 'launch', 'same_apk_reinstall', 'coexistence_with_rc2_preview'])
files = {p.name: p for p in folder.iterdir() if p.is_file()}
assert len(files) == 7
apk = files['Inventory-Android-v' + request['version'] + '-Candidate.apk']
assert hashlib.sha256(apk.read_bytes()).hexdigest() == request['apk_sha256']
assert manifest['install_check']['apk_sha256'] == request['apk_sha256']
assert not any(p.suffix.lower() in ['.p12', '.pfx', '.pass', '.pem', '.p7m', '.keystore', '.jks'] for p in files.values())
for line in next(folder.glob('*-SHA256SUMS.txt')).read_text().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(files[name].read_bytes()).hexdigest() == digest, name
def api(path):
    req = urllib.request.Request('https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY'] + '/' + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req) as response:
        return json.load(response)
run = api('actions/runs/' + str(request['build_run_id']))
assert run['conclusion'] == 'success' and run['head_sha'] == request['source_commit']
assert run['event'] == 'push' and run['head_branch'] == 'main'
# Promotion metadata may advance main, but must not change the built app or its tests.
a = api('git/trees/' + request['source_commit'] + '?recursive=1')['tree']
b = api('git/trees/' + os.environ['GITHUB_SHA'] + '?recursive=1')['tree']
for path in ['android/app/src', 'android/app/build.gradle', 'android/build.gradle', 'android/settings.gradle']:
    assert next(x['sha'] for x in a if x['path'] == path) == next(x['sha'] for x in b if x['path'] == path), path
print('Exact signed, installer-tested artifact and private signing backup promotion: PASS')
