"""Keep signing secrets outside checkout; retain only an encrypted recovery artifact."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('phase', choices=['create', 'backup'])
args = parser.parse_args()
private = Path(os.environ['RUNNER_TEMP']) / 'inventory-candidate-signing'
if args.phase == 'create':
    request = json.loads((root / 'release-request.json').read_text())
    private.mkdir(mode=0o700, exist_ok=False)
    key, password = private / 'candidate.p12', private / 'candidate.pass'
    existing = os.environ.get('INVENTORY_CANDIDATE_KEYSTORE_BASE64', '')
    if existing:
        key.write_bytes(base64.b64decode(existing, validate=True))
        secret = os.environ['INVENTORY_CANDIDATE_STORE_PASSWORD']
        if not secret:
            raise SystemExit('Existing Candidate keystore password is missing')
        password.write_text(secret + '\n')
    else:
        if (not request.get('initial_signing_bootstrap') or request.get('certificate_sha256')
                or request['version'] != '0.2.0-rc.5'):
            raise SystemExit('Use the retained Candidate signing key; generating another is forbidden')
        password.write_text(secrets.token_urlsafe(40) + '\n')
        subprocess.run(['keytool', '-genkeypair', '-alias', 'inventory-candidate', '-keystore', str(key),
            '-storetype', 'PKCS12', '-storepass:file', str(password), '-keypass:file', str(password),
            '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
            '-dname', 'CN=Inventory Candidate, OU=Application Builds, O=Drone Laboratory'],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    key.chmod(0o600)
    password.chmod(0o600)
    with open(os.environ['GITHUB_ENV'], 'a') as env:
        env.write(f'INVENTORY_CANDIDATE_KEYSTORE={key}\n')
        env.write(f'INVENTORY_CANDIDATE_PASSWORD_FILE={password}\n')
    print('Candidate signing material initialized outside the checkout')
else:
    if not (private / 'candidate.p12').exists():
        raise SystemExit('No signing key available for recovery')
    output = root.parent / 'deliverables/private'
    output.mkdir(parents=True, exist_ok=True)
    archive = private / 'recovery.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(private / 'candidate.p12', 'candidate.p12')
        z.write(private / 'candidate.pass', 'candidate.pass')
        z.writestr('README.txt', 'Private Inventory Candidate signing key. Alias: inventory-candidate.\n'
            'Package: ph.dronelab.inventory.candidate. Keep this recovery file private.\n')
    subprocess.run(['openssl', 'cms', '-encrypt', '-binary', '-aes-256-cbc', '-in', str(archive),
        '-out', str(output / 'Inventory-Candidate-Signing-Recovery.p7m'), '-outform', 'DER',
        str(root.parent / '.github/signing/inventory-candidate-recovery.pem')], check=True)
    shutil.rmtree(private)
    print('Encrypted recovery created; plaintext signing files removed before emulator tools run')
