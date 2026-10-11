"""Check a remotely published Git tree against the local reviewed source."""

import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
entries = json.loads(Path(sys.argv[1]).read_text())
actual = {e["path"]: e["sha"] for e in entries if e["type"] == "blob"}
for p, expected in actual.items():
    data = (root / p).read_bytes()
    sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if sha != expected:
        raise SystemExit("Mismatch: " + p)
print(f"PASS: {len(actual)} remote blob hashes match reviewed files")
