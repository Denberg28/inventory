from pathlib import Path
from tempfile import TemporaryDirectory
from . import __version__
from .store import Store


def run():
    with TemporaryDirectory() as folder:
        s = Store(Path(folder) / "probe.sqlite3")
        try:
            data = dict(
                item_id="PROBE-001",
                barcode="00001234",
                name="Probe",
                category="Equipment",
                status="Available",
                quantity=1,
                min_stock=0,
                location="Probe",
                notes="Disposable data",
            )
            s.create(data)
            r = s.lookup("00001234")
            s.movement(r["item_id"], r["revision"], "Check out", actor="Probe")
            r = s.get(r["item_id"])
            s.movement(r["item_id"], r["revision"], "Return", actor="Probe")
            s.backup(Path(folder) / "backup.sqlite3")
            s.restore(Path(folder) / "backup.sqlite3")
            if (
                s.get("PROBE-001")["status"] != "Available"
                or len(s.history("PROBE-001")) != 3
            ):
                raise ValueError("Probe failed.")
        finally:
            s.close()
    return f"Inventory {__version__}: self test PASS (disposable database)"
