"""Offline inventory transactions and validated recovery; standard library only."""

from __future__ import annotations
import csv
import json
import os
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from . import SCHEMA_VERSION

CATEGORIES = ("Equipment", "Tool", "Material")
STATUSES = ("Available", "In use", "Maintenance", "Damaged", "Lost", "Retired")
FIELDS = (
    "item_id",
    "barcode",
    "name",
    "category",
    "status",
    "quantity",
    "min_stock",
    "location",
    "notes",
)
ROW_FIELDS = FIELDS + ("borrower", "revision", "updated_at")
EVENT_FIELDS = (
    "seq",
    "item_id",
    "action",
    "delta",
    "actor",
    "note",
    "occurred_at",
    "snapshot",
)
MAX_ITEMS = 100000
MAX_QUANTITY = 999999999


def default_path():
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local/share")
    # Isolate rebuilt schema. Never silently open or overwrite a previous database.
    return base / "DroneLabInventory" / "inventory-v2.sqlite3"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def token(value):
    if not isinstance(value, str):
        raise ValueError("ID/barcode must be text; leading zeros are preserved.")
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9._/-]{1,64}", value):
        raise ValueError("ID/barcode: 1–64 letters, digits, dot, underscore, / or -.")
    return value


def text(value, limit, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(value) > limit or any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError(f"{field}: maximum {limit} characters; no control characters.")
    return value


def integer(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"{field} must be a whole number.")
    if isinstance(value, str) and not re.fullmatch(r"[0-9]{1,9}", value.strip()):
        raise ValueError(f"{field} must be a whole number.")
    number = int(value)
    if not 0 <= number <= MAX_QUANTITY:
        raise ValueError(f"{field} is outside the supported range.")
    return number


def validate(data):
    d = {f: data.get(f) for f in FIELDS}
    d["item_id"] = token(d["item_id"])
    d["barcode"] = (
        token(d["barcode"] or d["item_id"])
        if isinstance(d["barcode"], str)
        else token(d["barcode"])
    )
    for f, limit in (("name", 120), ("location", 120), ("notes", 2000)):
        d[f] = text(d[f], limit, f)
    if not d["name"] or d["category"] not in CATEGORIES or d["status"] not in STATUSES:
        raise ValueError("Name, valid category and status are required.")
    d["quantity"] = integer(d["quantity"], "Quantity")
    d["min_stock"] = integer(d["min_stock"], "Low stock at")
    if d["category"] != "Material" and (d["quantity"] != 1 or d["min_stock"] != 0):
        raise ValueError("One equipment/tool per record: quantity 1, low stock 0.")
    if d["category"] == "Material" and d["status"] == "In use":
        raise ValueError("Materials use Receive/Issue, not checkout.")
    return d


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=2)
        self.db.row_factory = sqlite3.Row
        try:
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            objects = self.db.execute(
                "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if version == 0 and not objects:
                with self.db:
                    self.db.executescript("""
                    CREATE TABLE items (
                        item_id TEXT PRIMARY KEY NOT NULL, barcode TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL, category TEXT NOT NULL, status TEXT NOT NULL,
                        quantity INTEGER NOT NULL CHECK(quantity BETWEEN 0 AND 999999999),
                        min_stock INTEGER NOT NULL CHECK(min_stock BETWEEN 0 AND 999999999),
                        location TEXT NOT NULL, notes TEXT NOT NULL, borrower TEXT NOT NULL,
                        revision INTEGER NOT NULL CHECK(revision>0), updated_at TEXT NOT NULL);
                    CREATE TABLE events (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_id TEXT NOT NULL REFERENCES items(item_id), action TEXT NOT NULL,
                        delta INTEGER NOT NULL, actor TEXT NOT NULL, note TEXT NOT NULL,
                        occurred_at TEXT NOT NULL, snapshot TEXT NOT NULL);
                    CREATE INDEX events_item_seq ON events(item_id,seq);
                    PRAGMA user_version=2;
                    """)
            self._check_schema(self.db)
            if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError(
                    "Database integrity failure. Retain files and restore a verified backup."
                )
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
        except Exception:
            self.db.close()
            raise

    @staticmethod
    def _check_schema(db):
        if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise ValueError(
                "Unsupported database version. Earlier candidates require separate verified migration."
            )
        objects = db.execute(
            "SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if {(r[0], r[1]) for r in objects} != {
            ("items", "table"),
            ("events", "table"),
            ("events_item_seq", "index"),
        }:
            raise ValueError(
                "Unexpected database objects. Refusing to change this file."
            )
        for table, fields in (("items", ROW_FIELDS), ("events", EVENT_FIELDS)):
            if tuple(r[1] for r in db.execute(f"PRAGMA table_info({table})")) != fields:
                raise ValueError("Unsupported database columns.")
        expected = {"items": {"item_id", "barcode"}, "events": set()}
        for table, columns in expected.items():
            unique = set()
            for index in db.execute(f"PRAGMA index_list({table})"):
                if index[2]:
                    names = tuple(
                        r[2]
                        for r in db.execute(
                            "SELECT * FROM pragma_index_info(?)", (index[1],)
                        )
                    )
                    if len(names) == 1:
                        unique.add(names[0])
            if not columns <= unique:
                raise ValueError("Database lacks unique identities.")
        foreign = list(db.execute("PRAGMA foreign_key_list(events)"))
        if len(foreign) != 1 or (foreign[0][2], foreign[0][3], foreign[0][4]) != (
            "items",
            "item_id",
            "item_id",
        ):
            raise ValueError("Database lacks inventory/history relationship.")

    def close(self):
        self.db.close()

    def get(self, item_id):
        row = self.db.execute(
            "SELECT * FROM items WHERE item_id=?", (token(item_id),)
        ).fetchone()
        if row is None:
            raise ValueError("Item no longer exists. Refresh and select again.")
        return dict(row)

    def lookup(self, code):
        value = token(code)
        row = self.db.execute(
            "SELECT * FROM items WHERE item_id=? OR barcode=?", (value, value)
        ).fetchone()
        return dict(row) if row else None

    def next_id(self):
        for n in range(1, MAX_ITEMS + 1):
            value = f"LAB-{n:06d}"
            if self.lookup(value) is None:
                return value
        raise ValueError("No automatically assigned IDs remain.")

    def _unique(self, d, exclude=""):
        if self.db.execute(
            """SELECT 1 FROM items WHERE item_id<>? AND
            (item_id IN (?,?) OR barcode IN (?,?))""",
            (exclude, d["item_id"], d["barcode"], d["item_id"], d["barcode"]),
        ).fetchone():
            raise ValueError("ID/barcode already identifies another item.")

    def _event(self, item_id, action, delta=0, actor="", note=""):
        row = self.get(item_id)
        self.db.execute(
            "INSERT INTO events(item_id,action,delta,actor,note,occurred_at,snapshot) VALUES(?,?,?,?,?,?,?)",
            (
                item_id,
                action,
                delta,
                actor,
                note,
                row["updated_at"],
                json.dumps(row, ensure_ascii=False),
            ),
        )

    def _create(self, data):
        d = validate(data)
        if d["status"] == "In use":
            raise ValueError("Create the asset first, then check it out.")
        if self.db.execute("SELECT count(*) FROM items").fetchone()[0] >= MAX_ITEMS:
            raise ValueError("Inventory capacity reached.")
        self._unique(d)
        row = dict(d, borrower="", revision=1, updated_at=now())
        self.db.execute(
            "INSERT INTO items VALUES(" + ",".join("?" for _ in ROW_FIELDS) + ")",
            tuple(row[f] for f in ROW_FIELDS),
        )
        self._event(d["item_id"], "Create", d["quantity"])
        return d["item_id"]

    def create(self, data):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            return self._create(data)

    def edit(self, item_id, revision, data):
        d = validate(data)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.get(item_id)
            if (
                d["item_id"] != old["item_id"]
                or d["category"] != old["category"]
                or d["quantity"] != old["quantity"]
            ):
                raise ValueError(
                    "ID/category/stock cannot be edited. Use stock movements or a new record."
                )
            if d["status"] == "In use" and old["status"] != "In use":
                raise ValueError("Use Check out to record the custodian.")
            if old["status"] == "In use" and d["status"] not in (
                "In use",
                "Lost",
                "Retired",
            ):
                raise ValueError("Return the asset before changing this status.")
            self._unique(d, old["item_id"])
            borrower = old["borrower"] if d["status"] == "In use" else ""
            cursor = self.db.execute(
                """UPDATE items SET barcode=?,name=?,status=?,min_stock=?,location=?,notes=?,
                borrower=?,revision=revision+1,updated_at=? WHERE item_id=? AND revision=?""",
                tuple(
                    d[f]
                    for f in (
                        "barcode",
                        "name",
                        "status",
                        "min_stock",
                        "location",
                        "notes",
                    )
                )
                + (borrower, now(), old["item_id"], revision),
            )
            if cursor.rowcount != 1:
                raise ValueError(
                    "Item changed. Close this dialog, refresh, and try again."
                )
            self._event(old["item_id"], "Edit")

    def movement(self, item_id, revision, action, amount="1", actor="", note=""):
        actor, note = text(actor, 120, "Person"), text(note, 500, "Note")
        if not actor:
            raise ValueError("Person / custodian is required.")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.get(item_id)
            qty, status, borrower, delta = (
                old["quantity"],
                old["status"],
                old["borrower"],
                0,
            )
            if old["category"] == "Material":
                if status != "Available" or action not in ("Receive", "Issue"):
                    raise ValueError(
                        "This material is not available for stock movements."
                    )
                n = integer(amount, "Amount")
                if n == 0:
                    raise ValueError("Amount must be greater than zero.")
                delta = n if action == "Receive" else -n
                qty = integer(qty + delta, "Resulting quantity")
            elif action == "Check out" and status == "Available":
                status, borrower = "In use", actor
            elif action == "Return" and status == "In use":
                status, borrower = "Available", ""
            else:
                raise ValueError("Action conflicts with current category/status.")
            cursor = self.db.execute(
                """UPDATE items SET quantity=?,status=?,borrower=?,revision=revision+1,
                updated_at=? WHERE item_id=? AND revision=?""",
                (qty, status, borrower, now(), old["item_id"], revision),
            )
            if cursor.rowcount != 1:
                raise ValueError("Item changed. Refresh and try again.")
            self._event(old["item_id"], action, delta, actor, note)

    def reconcile(self, item_id, revision, counted, actor, reason):
        """Record a physical count using schema-2-compatible adjustment events."""
        counted = integer(counted, "Counted quantity")
        actor, reason = text(actor, 120, "Counted by"), text(reason, 400, "Reason")
        if not actor or not reason:
            raise ValueError("Counted by and a reason are required.")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.get(item_id)
            if old["category"] != "Material" or old["status"] != "Available":
                raise ValueError("Stock count requires an available material.")
            delta = counted - old["quantity"]
            cursor = self.db.execute(
                "UPDATE items SET quantity=?,revision=revision+1,updated_at=? "
                "WHERE item_id=? AND revision=?",
                (counted, now(), old["item_id"], revision),
            )
            if cursor.rowcount != 1:
                raise ValueError("Item changed. Refresh and count again.")
            action = "Receive" if delta > 0 else "Issue" if delta < 0 else "Edit"
            self._event(
                old["item_id"],
                action,
                delta,
                actor,
                f"Stock count: {old['quantity']} -> {counted}. Reason: {reason}",
            )

    def search(
        self,
        query="",
        category="All",
        status="All",
        low=False,
        offset=0,
        *,
        exact_id=None,
    ):
        clauses, args = [], []
        if exact_id is not None:
            clauses.append("item_id=?")
            args.append(token(exact_id))
        elif query:
            q = (
                "%"
                + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                + "%"
            )
            clauses.append(
                "("
                + " OR ".join(
                    f"{f} LIKE ? ESCAPE '\\'"
                    for f in ("item_id", "barcode", "name", "location", "borrower")
                )
                + ")"
            )
            args.extend([q] * 5)
        for field, value, choices in (
            ("category", category, CATEGORIES),
            ("status", status, STATUSES),
        ):
            if value != "All":
                if value not in choices:
                    raise ValueError("Invalid filter.")
                clauses.append(field + "=?")
                args.append(value)
        if low:
            clauses.append(
                "category='Material' AND status<>'Retired' AND quantity<=min_stock"
            )
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        total = self.db.execute("SELECT count(*) FROM items" + where, args).fetchone()[
            0
        ]
        rows = self.db.execute(
            "SELECT * FROM items" + where + " ORDER BY name,item_id LIMIT 250 OFFSET ?",
            args + [max(0, offset)],
        )
        return [dict(r) for r in rows], total

    def summary(self):
        row = self.db.execute(
            """SELECT count(*) total,
            coalesce(sum(status='In use'),0) in_use,
            coalesce(sum(status IN ('Maintenance','Damaged','Lost')),0) attention,
            coalesce(sum(category='Material' AND status<>'Retired' AND quantity<=min_stock),0) low FROM items"""
        ).fetchone()
        return dict(row)

    def history(self, item_id):
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT * FROM events WHERE item_id=? ORDER BY seq DESC LIMIT 500",
                (token(item_id),),
            )
        ]

    def _output(self, path):
        path = Path(path).resolve()
        protected = {self.path.resolve(), self.path.with_suffix(".lock").resolve()}
        protected.update(
            Path(str(self.path) + s).resolve() for s in ("-wal", "-shm", "-journal")
        )
        if path in protected or (
            path.exists() and self.path.exists() and path.samefile(self.path)
        ):
            raise ValueError(
                "Output cannot overwrite the inventory database, journal or lock."
            )
        return path

    def _atomic_file(self, path, write):
        path = self._output(path)
        fd, temp = tempfile.mkstemp(prefix="inventory-", suffix=".tmp", dir=path.parent)
        os.close(fd)
        try:
            write(Path(temp))
            os.replace(temp, path)
        finally:
            Path(temp).unlink(missing_ok=True)

    def template(self, path):
        def write(temp):
            with temp.open("w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(FIELDS)

        self._atomic_file(path, write)

    def export(self, path):
        def write(temp):
            with temp.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(ROW_FIELDS)
                for row in self.db.execute("SELECT * FROM items ORDER BY item_id"):
                    writer.writerow(
                        [
                            (
                                "'" + v
                                if isinstance(v, str)
                                and v.lstrip().startswith(("=", "+", "-", "@"))
                                else v
                            )
                            for v in row
                        ]
                    )

        self._atomic_file(path, write)

    def import_csv(self, path):
        path = Path(path)
        self._output(path)  # Never read/import from the active SQLite namespace.
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("CSV exceeds 20 MB.")
        count = 0
        with path.open(encoding="utf-8-sig", newline="") as f, self.db:
            self.db.execute("BEGIN IMMEDIATE")
            reader = csv.DictReader(f)
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise ValueError("Use the CSV template; exact headers/order required.")
            for n, row in enumerate(reader, 2):
                if (
                    count >= 10000
                    or None in row
                    or any(v is None for v in row.values())
                ):
                    raise ValueError(f"Invalid CSV row {n} or more than 10000 rows.")
                try:
                    self._create(row)
                except ValueError as exc:
                    raise ValueError(f"CSV row {n}: {exc}") from exc
                count += 1
        return count

    @staticmethod
    def _copy(source, destination, timeout=5):
        deadline = time.monotonic() + timeout

        def progress(status, remaining, total):
            if status != sqlite3.SQLITE_DONE and time.monotonic() > deadline:
                raise sqlite3.OperationalError(
                    "Database copy timed out; close other database tools and retry."
                )

        source.backup(destination, pages=256, progress=progress, sleep=0.05)

    def backup(self, path):
        def write(temp):
            dest = sqlite3.connect(temp)
            try:
                self._copy(self.db, dest)
                if dest.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup integrity check failed.")
            finally:
                dest.close()  # Required before Windows rename.

        self._atomic_file(path, write)

    @staticmethod
    def _snapshot(raw):
        if not isinstance(raw, str) or len(raw) > 65536:
            raise ValueError("Invalid history snapshot.")
        try:
            d = json.loads(raw)
            if (
                not isinstance(d, dict)
                or set(d) != set(ROW_FIELDS)
                or validate(d) != {f: d[f] for f in FIELDS}
            ):
                raise ValueError("Noncanonical record.")
            if type(d["revision"]) is not int or d["revision"] < 1:
                raise ValueError("Invalid revision.")
            if text(d["borrower"], 120, "Custodian") != d["borrower"] or (
                d["status"] == "In use"
            ) != bool(d["borrower"]):
                raise ValueError("Invalid custody state.")
            parsed = datetime.fromisoformat(d["updated_at"])
            if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
                raise ValueError("UTC timestamp required.")
            return d
        except (KeyError, TypeError, ValueError, RecursionError) as exc:
            raise ValueError(
                "Invalid history/record data. Retain files and restore a verified backup."
            ) from exc

    @classmethod
    def _check_contents(cls, db):
        identities = set()
        latest = {}
        if (
            db.execute("SELECT count(*) FROM items").fetchone()[0] > MAX_ITEMS
            or db.execute("SELECT count(*) FROM events").fetchone()[0] > 1000000
        ):
            raise ValueError("Backup exceeds recovery limits.")
        for event in db.execute("SELECT * FROM events ORDER BY seq"):
            d = cls._snapshot(event["snapshot"])
            prior = latest.get(d["item_id"])
            action, delta = event["action"], event["delta"]
            if (
                type(event["seq"]) is not int
                or event["seq"] < 1
                or type(delta) is not int
                or not -MAX_QUANTITY <= delta <= MAX_QUANTITY
                or event["item_id"] != d["item_id"]
                or event["occurred_at"] != d["updated_at"]
            ):
                raise ValueError("History identities/time/numbers disagree.")
            if any(
                text(event[f], limit, f) != event[f]
                for f, limit in (("actor", 120), ("note", 500))
            ):
                raise ValueError("Invalid history text.")
            if prior is None:
                valid = (
                    action == "Create"
                    and d["revision"] == 1
                    and delta == d["quantity"]
                    and not d["borrower"]
                )
            else:
                valid = (
                    d["revision"] == prior["revision"] + 1
                    and d["category"] == prior["category"]
                    and d["quantity"] == prior["quantity"] + delta
                )
                if action == "Edit":
                    valid = (
                        valid
                        and delta == 0
                        and not (
                            d["status"] == "In use" and prior["status"] != "In use"
                        )
                        and not (
                            prior["status"] == "In use"
                            and d["status"] not in ("In use", "Lost", "Retired")
                        )
                        and d["borrower"]
                        == (prior["borrower"] if d["status"] == "In use" else "")
                    )
                elif action in ("Receive", "Issue"):
                    valid = (
                        valid
                        and prior["category"] == "Material"
                        and prior["status"] == d["status"] == "Available"
                        and (delta > 0 if action == "Receive" else delta < 0)
                    )
                elif action == "Check out":
                    valid = (
                        valid
                        and d["category"] != "Material"
                        and prior["status"] == "Available"
                        and d["status"] == "In use"
                        and d["borrower"] == event["actor"]
                        and delta == 0
                    )
                elif action == "Return":
                    valid = (
                        valid
                        and d["category"] != "Material"
                        and prior["status"] == "In use"
                        and d["status"] == "Available"
                        and delta == 0
                    )
                else:
                    valid = False
                if action != "Edit" and any(
                    d[f] != prior[f] for f in FIELDS if f not in ("status", "quantity")
                ):
                    valid = False
                if action != "Edit" and not event["actor"]:
                    valid = False
            if not valid:
                raise ValueError("Backup history contains a conflicting transition.")
            latest[d["item_id"]] = d
        for row in db.execute("SELECT * FROM items"):
            d = dict(row)
            cls._snapshot(json.dumps(d))
            keys = {d["item_id"], d["barcode"]}
            if identities & keys or latest.pop(d["item_id"], None) != d:
                raise ValueError(
                    "Inventory and history disagree or identifiers conflict."
                )
            identities |= keys
        if latest:
            raise ValueError("History refers to missing records.")

    def restore(self, path):
        path = self._output(path)
        if path.stat().st_size > 512 * 1024 * 1024:
            raise ValueError("Backup exceeds 512 MB.")
        fd, temp = tempfile.mkstemp(
            prefix="inventory-restore-", suffix=".sqlite3", dir=self.path.parent
        )
        os.close(fd)
        snapshot = sqlite3.connect(temp)
        source = None
        try:
            source = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
            self._copy(source, snapshot)
            source.close()
            source = None
            snapshot.row_factory = sqlite3.Row
            if snapshot.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or list(
                snapshot.execute("PRAGMA foreign_key_check")
            ):
                raise ValueError("Backup integrity failure.")
            self._check_schema(snapshot)
            self._check_contents(snapshot)
            recovery = self.path.with_name(
                "before-restore-"
                + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                + ".sqlite3"
            )
            self.backup(recovery)
            self._copy(snapshot, self.db)
            return recovery
        finally:
            if source is not None:
                source.close()
            snapshot.close()
            Path(temp).unlink(missing_ok=True)
