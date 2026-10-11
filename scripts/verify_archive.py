import hashlib
import json
import sys
import zipfile
from pathlib import PurePosixPath

if sys.flags.optimize:
    raise SystemExit("Do not disable verification assertions.")
with zipfile.ZipFile(sys.argv[1]) as z:
    assert z.testzip() is None
    assert len(z.namelist()) == len(set(z.namelist()))
    for name in z.namelist():
        p = PurePosixPath(name)
        assert (
            not p.is_absolute()
            and ".." not in p.parts
            and "\\" not in name
            and ":" not in name
        )
    m = json.loads(z.read("Inventory/DELIVERY.json"))
    assert m["tier"] == "rebuilt private source test candidate" and m["schema"] == 2
    for path, expected in m["files_sha256"].items():
        assert hashlib.sha256(z.read("Inventory/" + path)).hexdigest() == expected, path
    assert set(z.namelist()) == {"Inventory/" + p for p in m["files_sha256"]} | {
        "Inventory/DELIVERY.json"
    }
    print(
        f"PASS: archive integrity, safe paths, {len(m['files_sha256'])} source hashes, commit {m['source_commit']}"
    )
