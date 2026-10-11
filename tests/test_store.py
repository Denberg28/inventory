import csv
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from inventory.store import Store, FIELDS, token
from inventory.instance import InstanceLock
import run_inventory


def item(id="LAB-001", category="Equipment", **extra):
    d = dict(
        item_id=id,
        barcode=id,
        name="Laboratory item",
        category=category,
        status="Available",
        quantity=1,
        min_stock=0,
        location="Cabinet A",
        notes="",
    )
    d.update(extra)
    return d


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.s = Store(self.folder / "inventory.sqlite3")

    def tearDown(self):
        self.s.close()
        self.temp.cleanup()

    def add(self, **extra):
        self.s.create(item(**extra))
        return self.s.get(extra.get("id", "LAB-001"))

    def move(self, action, actor="Custodian", **extra):
        r = self.s.get("LAB-001")
        self.s.movement(r["item_id"], r["revision"], action, actor=actor, **extra)

    def csv(self, rows):
        p = self.folder / "input.csv"
        with p.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        return p

    def test_scan_leading_zero_and_normalization(self):
        self.add(barcode="00001234")
        self.assertEqual(self.s.lookup(" 00001234 ")["item_id"], "LAB-001")
        self.assertEqual(token("abc-1"), "ABC-1")

    def test_stock_counts_audit_and_restore_for_all_directions(self):
        self.add(category="Material", quantity=10)
        for counted, action, delta in (
            (7, "Issue", -3),
            (12, "Receive", 5),
            (12, "Edit", 0),
            (0, "Issue", -12),
        ):
            r = self.s.get("LAB-001")
            self.s.reconcile(
                r["item_id"], r["revision"], counted, "Counter", "Physical shelf count"
            )
            event = self.s.history("LAB-001")[0]
            self.assertEqual(
                (event["action"], event["delta"], event["actor"]),
                (action, delta, "Counter"),
            )
            self.assertIn("Stock count:", event["note"])
            self.assertEqual(self.s.get("LAB-001")["quantity"], counted)
        p = self.folder / "count-backup.sqlite3"
        self.s.backup(p)
        self.s.restore(p)
        self.assertEqual(len(self.s.history("LAB-001")), 5)

    def test_invalid_counts_stale_revisions_and_audit_failure_roll_back(self):
        r = self.add(category="Material", quantity=10)
        for count, actor, reason in (
            (-1, "Joe", "Count"),
            ("1.5", "Joe", "Count"),
            (True, "Joe", "Count"),
            (1000000000, "Joe", "Count"),
            (2, "", "Count"),
            (2, "Joe", ""),
            (2, "Joe", "X" * 401),
        ):
            with self.assertRaises(ValueError):
                self.s.reconcile("LAB-001", r["revision"], count, actor, reason)
        with patch.object(
            self.s, "_event", side_effect=sqlite3.OperationalError("disk full")
        ):
            with self.assertRaises(sqlite3.Error):
                self.s.reconcile("LAB-001", r["revision"], 4, "Joe", "Count")
        self.assertEqual(self.s.get("LAB-001"), r)
        self.assertEqual(len(self.s.history("LAB-001")), 1)
        self.s.reconcile("LAB-001", r["revision"], 4, "Joe", "Count")
        with self.assertRaises(ValueError):
            self.s.reconcile("LAB-001", r["revision"], 5, "Joe", "Count")
        self.assertEqual(self.s.get("LAB-001")["quantity"], 4)

    def test_count_rejects_asset_and_unavailable_material(self):
        r = self.add()
        with self.assertRaises(ValueError):
            self.s.reconcile(r["item_id"], r["revision"], 1, "Joe", "Count")
        r = self.add(id="MAT", category="Material", status="Maintenance")
        with self.assertRaises(ValueError):
            self.s.reconcile(r["item_id"], r["revision"], 1, "Joe", "Count")

    def test_real_a3_schema_fixture_upgrade_and_recovery(self):
        p = self.folder / "a3.sqlite3"
        db = sqlite3.connect(p)
        db.executescript(
            (Path(__file__).parent / "fixtures/schema2-a3.sql").read_text()
        )
        db.close()
        self.s.restore(p)
        self.assertEqual(self.s.lookup("00001234")["borrower"], "Synthetic borrower")
        self.assertEqual(self.s.get("MAT-1")["quantity"], 8)
        self.assertEqual(self.s.get("MAT-1")["location"], "Rack B")
        r = self.s.get("MAT-1")
        self.s.reconcile("MAT-1", r["revision"], 6, "Counter", "Fixture count")
        r = self.s.get("ASSET-1")
        self.s.movement("ASSET-1", r["revision"], "Return", actor="Receiver")
        q = self.folder / "a4.sqlite3"
        self.s.backup(q)
        self.s.restore(q)
        self.assertEqual(self.s.get("MAT-1")["quantity"], 6)
        self.assertEqual(self.s.get("ASSET-1")["status"], "Available")

    def test_repeated_scan_never_changes_stock_or_history(self):
        self.add()
        for _ in range(100):
            self.s.lookup("LAB-001")
        self.assertEqual(len(self.s.history("LAB-001")), 1)

    def test_cross_namespace_collisions_rejected(self):
        self.add(barcode="OTHER")
        for d in (
            item(id="OTHER"),
            item(id="NEW", barcode="LAB-001"),
            item(id="NEW", barcode="OTHER"),
        ):
            with self.assertRaises(ValueError):
                self.s.create(d)
        self.assertEqual(self.s.summary()["total"], 1)

    def test_next_id_skips_barcode(self):
        self.add(barcode="LAB-000001")
        self.assertEqual(self.s.next_id(), "LAB-000002")

    def test_quantity_rules(self):
        for d in (
            item(quantity=2),
            item(min_stock=1),
            item(category="Material", quantity=-1),
            item(quantity=True),
            item(category="Material", status="In use"),
        ):
            with self.assertRaises(ValueError):
                self.s.create(d)

    def test_missing_invalid_and_long_text_rejected(self):
        for extra in (
            {"name": None},
            {"name": ""},
            {"item_id": "x;drop"},
            {"name": "x" * 121},
            {"notes": "bad\x00"},
            {"barcode": None},
        ):
            with self.assertRaises(ValueError):
                self.s.create(item(**extra))

    def test_checkout_return_and_audit(self):
        self.add()
        self.move("Check out")
        r = self.s.get("LAB-001")
        self.assertEqual((r["status"], r["borrower"]), ("In use", "Custodian"))
        self.move("Return")
        self.assertEqual(self.s.get("LAB-001")["borrower"], "")
        self.assertEqual(len(self.s.history("LAB-001")), 3)

    def test_invalid_asset_transitions(self):
        self.add()
        for action in ("Return", "Issue", "Receive"):
            with self.assertRaises(ValueError):
                self.move(action)
        self.move("Check out")
        with self.assertRaises(ValueError):
            self.move("Check out")

    def test_required_person_and_positive_material_amount(self):
        self.add(category="Material", quantity=10)
        for actor, amount in (
            ("", 1),
            ("Joe", 0),
            ("Joe", "1.5"),
            ("Joe", -1),
            ("Joe", True),
        ):
            with self.assertRaises(ValueError):
                self.move("Issue", actor, amount=amount)

    def test_stock_movement_low_filter_retired(self):
        self.add(category="Material", quantity=10, min_stock=3)
        self.move("Issue", amount=8)
        self.assertEqual(self.s.summary()["low"], 1)
        self.move("Receive", amount=5)
        self.assertEqual(self.s.get("LAB-001")["quantity"], 7)
        r = self.s.get("LAB-001")
        self.s.edit(r["item_id"], r["revision"], dict(r, status="Retired"))
        self.assertEqual(self.s.summary()["low"], 0)
        with self.assertRaises(ValueError):
            self.move("Receive", amount=1)

    def test_underflow_and_overflow_do_not_change_audit(self):
        self.add(category="Material", quantity=10)
        for action, amount in (("Issue", 11), ("Receive", 999999999)):
            with self.assertRaises(ValueError):
                self.move(action, amount=amount)
        self.assertEqual(self.s.get("LAB-001")["quantity"], 10)
        self.assertEqual(len(self.s.history("LAB-001")), 1)

    def test_audit_failure_rolls_back_create(self):
        with patch.object(
            self.s, "_event", side_effect=sqlite3.OperationalError("disk failure")
        ):
            with self.assertRaises(sqlite3.Error):
                self.add()
        self.assertEqual(self.s.summary()["total"], 0)

    def test_audit_failure_rolls_back_movement(self):
        self.add()
        with patch.object(
            self.s, "_event", side_effect=sqlite3.OperationalError("disk failure")
        ):
            with self.assertRaises(sqlite3.Error):
                self.move("Check out")
        self.assertEqual(self.s.get("LAB-001")["status"], "Available")

    def test_stale_revision_rejected(self):
        r = self.add()
        self.move("Check out")
        with self.assertRaises(ValueError):
            self.s.edit(r["item_id"], r["revision"], r)

    def test_edit_preserves_ids_category_quantity_and_custody(self):
        r = self.add()
        for change in (
            {"item_id": "OTHER"},
            {"category": "Tool"},
            {"quantity": 2},
            {"status": "In use"},
        ):
            with self.assertRaises(ValueError):
                self.s.edit(r["item_id"], r["revision"], dict(r, **change))
        self.move("Check out")
        r = self.s.get("LAB-001")
        with self.assertRaises(ValueError):
            self.s.edit(r["item_id"], r["revision"], dict(r, status="Available"))
        self.s.edit(r["item_id"], r["revision"], dict(r, status="Lost"))
        self.assertEqual(self.s.get("LAB-001")["borrower"], "")

    def test_search_literal_sql_and_wildcards(self):
        self.add(name="Part_%")
        self.assertEqual(self.s.search("_%")[1], 1)
        self.assertEqual(self.s.search("' OR 1=1 --")[1], 0)

    def test_exact_scan_beyond_first_page_and_pagination(self):
        rows = [item(id=f"ID-{i:03d}", name="TARGET other") for i in range(301)]
        self.s.import_csv(self.csv(rows))
        self.s.create(item(id="TARGET", name="ZZ target"))
        self.assertEqual(len(self.s.search("TARGET")[0]), 250)
        self.assertEqual(self.s.search(exact_id="TARGET")[0][0]["item_id"], "TARGET")
        self.assertEqual(len(self.s.search(offset=250)[0]), 52)

    def test_csv_valid_unicode_and_crlf_notes(self):
        self.s.import_csv(self.csv([item(name="工具", notes="a\r\nb")]))
        self.assertEqual(self.s.get("LAB-001")["notes"], "a\nb")

    def test_csv_duplicate_rolls_back_all(self):
        with self.assertRaises(ValueError):
            self.s.import_csv(self.csv([item(), item()]))
        self.assertEqual(self.s.summary()["total"], 0)

    def test_csv_invalid_headers_missing_and_extra_columns(self):
        for content in (
            "wrong\nvalue\n",
            ",".join(FIELDS) + "\nID\n",
            ",".join(FIELDS) + "\n" + ",".join(["ID"] * 10) + "\n",
        ):
            p = self.folder / "bad.csv"
            p.write_text(content)
            with self.assertRaises(ValueError):
                self.s.import_csv(p)

    def test_csv_template_and_formula_guard(self):
        self.add(name="=1+1", location="@x")
        p = self.folder / "export.csv"
        self.s.export(p)
        with p.open(encoding="utf-8-sig") as f:
            r = list(csv.DictReader(f))[0]
        self.assertEqual(r["name"], "'=1+1")
        self.assertEqual(r["location"], "'@x")
        p = self.folder / "template.csv"
        self.s.template(p)
        self.assertEqual(self.s.import_csv(p), 0)

    def test_outputs_protect_database_and_alias(self):
        for p in (
            self.s.path,
            Path(str(self.s.path) + "-wal"),
            self.s.path.with_suffix(".lock"),
        ):
            for method in (self.s.backup, self.s.export, self.s.template):
                with self.assertRaises(ValueError):
                    method(p)
        alias = self.folder / "alias"
        os.link(self.s.path, alias)
        with self.assertRaises(ValueError):
            self.s.backup(alias)

    def test_backup_restore_recovery_and_reopen(self):
        self.add()
        self.move("Check out")
        p = self.folder / "backup.sqlite3"
        self.s.backup(p)
        self.move("Return")
        recovery = self.s.restore(p)
        self.assertTrue(recovery.exists())
        self.assertEqual(self.s.get("LAB-001")["status"], "In use")
        other = Store(recovery)
        try:
            self.assertEqual(other.get("LAB-001")["status"], "Available")
        finally:
            other.close()

    def test_backup_connection_closed_before_windows_rename(self):
        self.add()
        p = self.folder / "backup.sqlite3"
        real_replace = os.replace
        real_connect = sqlite3.connect
        opened = []

        class TrackedConnection(sqlite3.Connection):
            closed = False

            def close(self):
                super().close()
                self.closed = True

        def connect(*args, **kwargs):
            db = real_connect(*args, **dict(kwargs, factory=TrackedConnection))
            opened.append(db)
            return db

        def replace(source, dest):
            if any(not c.closed for c in opened):
                raise PermissionError("Simulated Windows open-handle sharing violation")
            real_replace(source, dest)

        with (
            patch("inventory.store.sqlite3.connect", side_effect=connect),
            patch("inventory.store.os.replace", side_effect=replace),
        ):
            self.s.backup(p)
        self.assertTrue(p.exists())
        self.assertTrue(opened)

    def test_failed_backup_preserves_output_and_cleans_temp(self):
        p = self.folder / "backup"
        p.write_bytes(b"keep")
        with patch.object(
            self.s, "_copy", side_effect=sqlite3.OperationalError("busy")
        ):
            with self.assertRaises(sqlite3.Error):
                self.s.backup(p)
        self.assertEqual(p.read_bytes(), b"keep")
        self.assertFalse(list(self.folder.glob("inventory-*.tmp")))

    def test_bad_restore_keeps_live_data(self):
        self.add()
        p = self.folder / "bad"
        p.write_bytes(b"bad db")
        with self.assertRaises(sqlite3.Error):
            self.s.restore(p)
        self.assertEqual(self.s.summary()["total"], 1)

    def test_malformed_history_restore_rejected(self):
        self.add()
        self.move("Check out")
        p = self.folder / "backup.sqlite3"
        self.s.backup(p)
        db = sqlite3.connect(p)
        db.execute("UPDATE events SET delta=4 WHERE action='Check out'")
        db.commit()
        db.close()
        with self.assertRaises(ValueError):
            self.s.restore(p)
        self.assertEqual(self.s.get("LAB-001")["status"], "In use")

    def test_inconsistent_snapshot_restore_rejected(self):
        self.add()
        p = self.folder / "backup.sqlite3"
        self.s.backup(p)
        db = sqlite3.connect(p)
        db.execute("UPDATE items SET name='tampered'")
        db.commit()
        db.close()
        with self.assertRaises(ValueError):
            self.s.restore(p)
        self.assertEqual(self.s.get("LAB-001")["name"], "Laboratory item")

    def test_future_legacy_and_unknown_schema_preserved(self):
        for version in (1, 99):
            p = self.folder / f"v{version}.sqlite3"
            db = sqlite3.connect(p)
            db.execute(f"PRAGMA user_version={version}")
            db.close()
            original = p.read_bytes()
            with self.assertRaises(ValueError):
                Store(p)
            self.assertEqual(p.read_bytes(), original)
        p = self.folder / "unknown"
        db = sqlite3.connect(p)
        db.execute("CREATE TABLE unknown(x)")
        db.close()
        with self.assertRaises(ValueError):
            Store(p)

    def test_probe_uses_disposable_data_and_exclusive_output(self):
        p = self.folder / "result with spaces.txt"
        self.assertEqual(
            run_inventory.main(["--self-test", "--self-test-file", str(p)]), 0
        )
        with self.assertRaises(FileExistsError):
            run_inventory.main(["--self-test", "--self-test-file", str(p)])

    def test_process_lock_releases_and_rejects_second_instance(self):
        p = self.folder / "instance.lock"
        first = InstanceLock(p)
        try:
            with self.assertRaises(ValueError):
                InstanceLock(p)
        finally:
            first.close()
        second = InstanceLock(p)
        second.close()

    def test_completed_copy_is_success_after_deadline(self):
        self.add()
        dest = sqlite3.connect(":memory:")
        try:
            # A one-page in-memory database finishes its transaction in the first chunk.
            source = sqlite3.connect(":memory:")
            source.execute("CREATE TABLE x(y)")
            source.commit()
            try:
                Store._copy(source, dest, timeout=0)
            finally:
                source.close()
            self.assertEqual(dest.execute("SELECT count(*) FROM x").fetchone()[0], 0)
        finally:
            dest.close()
