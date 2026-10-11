"""Actual abrupt child exits and bounded busy-copy failures, disposable databases."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inventory.store import Store

CHILD = """
import os, sqlite3, sys
from inventory.store import Store
s=Store(sys.argv[1])
if sys.argv[2]=='uncommitted':
    s.db.execute("BEGIN IMMEDIATE")
    s.db.execute("UPDATE items SET quantity=999")
else:
    r=s.get('TEST-001'); s.movement(r['item_id'],r['revision'],'Issue',amount=2,actor='Fault test')
os._exit(0)
"""
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "crash.sqlite3"
    s = Store(path)
    s.create(
        dict(
            item_id="TEST-001",
            barcode="00001234",
            name="Test",
            category="Material",
            status="Available",
            quantity=10,
            min_stock=1,
            location="Test",
            notes="",
        )
    )
    s.close()
    for mode, expected, events in (("uncommitted", 10, 1), ("committed", 8, 2)):
        subprocess.run(
            [sys.executable, "-c", CHILD, str(path), mode],
            cwd=ROOT,
            check=True,
            timeout=15,
        )
        s = Store(path)
        try:
            if (
                s.get("TEST-001")["quantity"] != expected
                or len(s.history("TEST-001")) != events
            ):
                raise SystemExit("FAIL: crash recovery")
            if s.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise SystemExit("FAIL: integrity")
        finally:
            s.close()
    busy = Path(folder) / "busy.sqlite3"
    writer = sqlite3.connect(busy)
    writer.execute("CREATE TABLE x(y)")
    writer.commit()
    writer.execute("BEGIN EXCLUSIVE")
    reader = sqlite3.connect(busy, timeout=0.1)
    dest = sqlite3.connect(":memory:")
    start = time.monotonic()
    try:
        try:
            Store._copy(reader, dest, timeout=0.15)
        except sqlite3.OperationalError:
            elapsed = time.monotonic() - start
            if elapsed > 1.5:
                raise SystemExit("FAIL: busy-copy timeout exceeded budget")
        else:
            raise SystemExit("FAIL: expected bounded lock failure")
    finally:
        writer.rollback()
        writer.close()
        reader.close()
        dest.close()
print(
    json.dumps(
        {
            "status": "PASS",
            "checks": [
                "uncommitted abrupt exit rollback",
                "committed abrupt exit retained stock and audit",
                "integrity after both exits",
                "busy SQLite copy bounded failure",
            ],
            "busy_copy_seconds": round(elapsed, 3),
            "limitation": "Process simulation; not physical power loss",
        },
        indent=2,
    )
)
