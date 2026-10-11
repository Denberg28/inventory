"""Package a clean committed source candidate with hashes and source identity."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inventory import __version__, SCHEMA_VERSION

if subprocess.check_output(
    ["git", "status", "--porcelain"], cwd=ROOT, text=True
).strip():
    raise SystemExit("Commit source/configuration/evidence before packaging.")
commit = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
).strip()
paths = (
    subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
)
files = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths if p}
dest = ROOT / "dist"
dest.mkdir(exist_ok=True)
output = dest / f"Inventory-{__version__}-source-test-candidate.zip"
if output.exists():
    raise SystemExit(
        "This version already exists. Use a new version; do not replace it."
    )
manifest = dict(
    version=__version__,
    schema=SCHEMA_VERSION,
    source_commit=commit,
    tier="rebuilt private source test candidate",
    windows_exe="NOT BUILT",
    scanner_hil="BLOCKED",
    legacy_migration="BLOCKED",
    files_sha256=files,
)
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):
        z.write(ROOT / p, "Inventory/" + p)
    z.writestr("Inventory/DELIVERY.json", json.dumps(manifest, indent=2) + "\n")
checksum = hashlib.sha256(output.read_bytes()).hexdigest()
(output.with_suffix(".sha256")).write_text(checksum + "  " + output.name + "\n")
print(
    json.dumps(dict(file=str(output), sha256=checksum, source_commit=commit), indent=2)
)
