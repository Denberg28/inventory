"""Verify reverse restore with the unchanged v0.1.0a3 storage implementation.

Pass an extracted baseline checkout; never download code during this check.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inventory.store import Store

BASELINE_HASH = "07c570b47f01c589bacc9703640b19c9c6349e35391c9f966581b1b513880c74"
CHILD = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from inventory import __version__
from inventory.store import Store
if __version__ != '0.1.0a3':
    raise SystemExit('Wrong baseline version')
s=Store(Path(sys.argv[2])/'restored.sqlite3')
try:
    recovery=s.restore(Path(sys.argv[2])/'a4.sqlite3')
    if not recovery.exists() or s.get('MAT')['quantity'] != 0 or len(s.history('MAT')) != 5:
        raise SystemExit('Reverse stock/history restore failed')
    if s.lookup('00001234')['borrower'] != 'Synthetic borrower':
        raise SystemExit('Reverse identity/custody restore failed')
finally:
    s.close()
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", required=True, type=Path)
    args = parser.parse_args()
    baseline = args.baseline_root.resolve()
    if (
        hashlib.sha256((baseline / "inventory/store.py").read_bytes()).hexdigest()
        != BASELINE_HASH
    ):
        raise SystemExit("Baseline store differs from reviewed v0.1.0a3 source")
    with tempfile.TemporaryDirectory() as folder:
        s = Store(Path(folder) / "current.sqlite3")
        try:
            data = dict(
                item_id="MAT",
                barcode="MAT",
                name="Synthetic material",
                category="Material",
                status="Available",
                quantity=10,
                min_stock=2,
                location="Test",
                notes="",
            )
            s.create(data)
            for counted in (7, 12, 12, 0):
                r = s.get("MAT")
                s.reconcile(
                    "MAT",
                    r["revision"],
                    counted,
                    "Synthetic counter",
                    "Compatibility count",
                )
            s.create(
                dict(
                    data,
                    item_id="ASSET",
                    barcode="00001234",
                    category="Equipment",
                    quantity=1,
                    min_stock=0,
                )
            )
            s.movement("ASSET", 1, "Check out", actor="Synthetic borrower")
            s.backup(Path(folder) / "a4.sqlite3")
        finally:
            s.close()
        subprocess.run(
            [sys.executable, "-I", "-c", CHILD, str(baseline), folder],
            check=True,
            timeout=30,
        )
    print(
        json.dumps(
            dict(
                status="PASS",
                baseline_version="0.1.0a3",
                baseline_commit="c65ef374badbf9309f6d81bcb4548273a9e8afaa",
                baseline_store_sha256=BASELINE_HASH,
                checks=[
                    "v0.1.0a3 restores v0.1.0a4 count increases/decreases/no difference/zero",
                    "leading-zero barcode and asset custody retained",
                    "recovery backup created",
                ],
                limitation="Synthetic schema-2 data; schema-1 migration remains blocked",
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
