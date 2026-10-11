import csv
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inventory.store import Store, FIELDS

with tempfile.TemporaryDirectory() as folder:
    s = Store(Path(folder) / "test.sqlite3")
    csvpath = Path(folder) / "input.csv"
    try:
        with csvpath.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(
                dict(
                    item_id=f"ID-{i}",
                    barcode=f"BC-{i}",
                    name=f"Material {i}",
                    category="Material",
                    status="Available",
                    quantity=10,
                    min_stock=2,
                    location="Test",
                    notes="",
                )
                for i in range(10000)
            )
        start = time.perf_counter()
        s.import_csv(csvpath)
        import_ms = (time.perf_counter() - start) * 1000
        durations = []
        for n in range(20):
            start = time.perf_counter()
            rows, total = s.search(str(n))
            durations.append((time.perf_counter() - start) * 1000)
            if len(rows) > 250:
                raise SystemExit("FAIL: page budget")
        median = statistics.median(durations)
        if median >= 250:
            raise SystemExit("FAIL: median search exceeds 250 ms")
        print(
            json.dumps(
                dict(
                    status="PASS",
                    records=10000,
                    queries=20,
                    median_search_ms=round(median, 3),
                    max_search_ms=round(max(durations), 3),
                    import_ms=round(import_ms, 3),
                    criterion="Median <250 ms; <=250 visible rows",
                ),
                indent=2,
            )
        )
    finally:
        s.close()
