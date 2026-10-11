import csv
import sqlite3
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from inventory.store import Store, FIELDS
from inventory.ui import App, ItemDialog, MovementDialog


def item(id="TEST-001", category="Equipment", **extra):
    d = dict(
        item_id=id,
        barcode="00001234",
        name="Test equipment",
        category=category,
        status="Available",
        quantity=1,
        min_stock=0,
        location="Cabinet",
        notes="",
    )
    d.update(extra)
    return d


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.root = tk.Tk()
        self.s = Store(self.folder / "test.sqlite3")
        self.app = App(self.root, self.s)
        self.root.update()
        self.patch = patch("inventory.ui.messagebox.showerror")
        self.error = self.patch.start()

    def tearDown(self):
        self.patch.stop()
        try:
            self.app.close()
        except tk.TclError:
            pass
        self.temp.cleanup()

    def add(self, **extra):
        self.s.create(item(**extra))
        self.app.reveal(extra.get("id", "TEST-001"))
        self.root.update()

    def dialogs(self, kind):
        return [w for w in self.root.winfo_children() if isinstance(w, kind)]

    def pulse(self, seconds=0.22):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.root.update()
            time.sleep(0.005)

    def test_add_edit_dialog_and_category_controls(self):
        d = ItemDialog(self.app)
        d.values["name"].set("Motor")
        d.values["barcode"].set("00005678")
        self.assertEqual(str(d.widgets["quantity"].cget("state")), "disabled")
        d.save()
        self.assertTrue(d.saved)
        r = self.s.lookup("00005678")
        d = ItemDialog(self.app, r)
        d.values["location"].set("Rack B")
        d.save()
        self.assertEqual(self.s.get(r["item_id"])["location"], "Rack B")
        d = ItemDialog(self.app)
        d.values["category"].set("Material")
        d.category_changed()
        self.assertEqual(str(d.widgets["quantity"].cget("state")), "normal")
        d.destroy()

    def test_keyboard_scan_exact_repeated_and_unknown(self):
        self.add()
        self.app.scan_entry.focus_force()
        self.root.update()
        for _ in range(100):
            self.app.scan_value.set("00001234")
            self.app.scan_entry.event_generate("<Return>")
            self.root.update()
            self.assertEqual(self.app.table.selection(), ("TEST-001",))
        self.assertEqual(len(self.s.history("TEST-001")), 1)
        with patch("inventory.ui.messagebox.askyesno", return_value=False):
            self.app.scan_value.set("UNKNOWN")
            self.app.scan()
        self.assertFalse(self.app.table.selection())
        self.assertIn("disabled", self.app.buttons["Check out"].state())

    def test_invalid_scan_clears_old_actions(self):
        self.add()
        self.app.scan_value.set("bad;sql")
        self.app.safe(self.app.scan)
        self.assertFalse(self.app.table.selection())
        self.error.assert_called_once()

    def test_unknown_barcode_add_and_cancel(self):
        with patch("inventory.ui.messagebox.askyesno", return_value=True):
            self.app.scan_value.set("00009999")
            self.app.scan()
        d = self.dialogs(ItemDialog)[0]
        self.assertEqual(d.values["barcode"].get(), "00009999")
        d.destroy()
        self.assertEqual(self.s.summary()["total"], 0)

    def test_checkout_return_and_status_actions(self):
        self.add()
        self.app.move("Check out")
        d = self.dialogs(MovementDialog)[0]
        d.actor.set("Custodian")
        d.save()
        self.root.update()
        self.assertIn("disabled", self.app.buttons["Check out"].state())
        self.assertNotIn("disabled", self.app.buttons["Return"].state())
        self.app.move("Return")
        d = self.dialogs(MovementDialog)[0]
        d.actor.set("Custodian")
        d.save()
        self.assertEqual(self.s.get("TEST-001")["status"], "Available")

    def test_material_issue_receive_and_validation(self):
        self.add(category="Material", quantity=5, min_stock=2)
        self.app.move("Issue")
        d = self.dialogs(MovementDialog)[0]
        d.actor.set("User")
        d.amount.set("6")
        d.save()
        self.assertFalse(d.saved)
        d.amount.set("4")
        d.save()
        self.assertEqual(self.s.get("TEST-001")["quantity"], 1)
        self.assertEqual(self.s.summary()["low"], 1)
        self.app.move("Receive")
        d = self.dialogs(MovementDialog)[0]
        d.actor.set("User")
        d.amount.set("3")
        d.save()
        self.assertEqual(self.s.get("TEST-001")["quantity"], 4)

    def test_post_commit_refresh_failure_never_repeats_save(self):
        d = ItemDialog(self.app)
        d.values["name"].set("Once")
        with patch.object(
            self.app, "reveal", side_effect=sqlite3.OperationalError("read failed")
        ):
            d.save()
            d.save()
        self.assertEqual(self.s.summary()["total"], 1)
        self.assertTrue(d.saved)
        self.assertIn("saved", self.app.notice.get())
        self.assertFalse(self.app.table.selection())

    def test_post_commit_movement_failure_commits_once(self):
        self.add()
        d = MovementDialog(self.app, self.app.selected(), "Check out")
        d.actor.set("User")
        with patch.object(
            self.app, "reveal", side_effect=sqlite3.OperationalError("read failed")
        ):
            d.save()
            d.save()
        self.assertEqual(len(self.s.history("TEST-001")), 2)

    def test_pagination_cancels_deferred_search(self):
        p = self.folder / "rows.csv"
        with p.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(
                item(id=f"ID-{i:03d}", barcode=f"BC-{i:03d}", name="Shared")
                for i in range(300)
            )
        self.s.import_csv(p)
        self.app.query.set("Shared")
        self.app.reload()
        self.app.change_page(250)
        self.pulse()
        self.assertEqual(self.app.offset, 250)
        self.assertEqual(len(self.app.table.get_children()), 50)

    def test_exact_scan_beyond_substring_page(self):
        for n in range(260):
            self.s.create(item(id=f"ID-{n}", barcode=f"BC-{n}", name="TARGET"))
        self.s.create(item(id="TARGET", barcode="TARGET", name="ZZ"))
        self.app.query.set("TARGET")
        self.app.scan_value.set("TARGET")
        self.app.scan()
        self.pulse()
        self.assertEqual(self.app.table.selection(), ("TARGET",))
        self.assertEqual(self.app.total, 1)

    def test_history_shows_snapshots_and_corruption_no_window(self):
        self.add(notes="Past")
        r = self.s.get("TEST-001")
        self.s.edit(r["item_id"], r["revision"], dict(r, notes="Present"))
        self.app.refresh()
        self.app.history()
        win = self.dialogs(tk.Toplevel)[0]
        text = [
            w
            for w in win.winfo_children()[0].winfo_children()
            if isinstance(w, tk.Text)
        ][0].get("1.0", "end")
        self.assertIn("Past", text)
        self.assertIn("Present", text)
        win.destroy()
        self.s.db.execute("UPDATE events SET snapshot='bad'")
        self.s.db.commit()
        self.app.safe(self.app.history)
        self.assertFalse(self.dialogs(tk.Toplevel))
        self.error.assert_called_once()

    def test_long_notes_minimum_window_preserves_actions(self):
        self.add(notes="word " * 400)
        self.root.geometry("880x560")
        self.root.update()
        for b in self.app.buttons.values():
            self.assertLessEqual(
                b.winfo_rooty() + b.winfo_height(),
                self.root.winfo_rooty() + self.root.winfo_height(),
            )
        self.assertGreater(self.app.table.winfo_height(), 100)
        self.assertLess(len(self.app.detail.get()), 300)

    def test_data_menu_backup_restore_export_import_and_cancel(self):
        self.add()
        backup = self.folder / "backup.sqlite3"
        report = self.folder / "report.csv"
        template = self.folder / "template.csv"
        for action, path in (
            (self.app.backup, backup),
            (self.app.export, report),
            (self.app.template, template),
        ):
            with patch(
                "inventory.ui.filedialog.asksaveasfilename", return_value=str(path)
            ):
                action()
            self.assertTrue(path.exists())
        self.s.create(item(id="OTHER", barcode="OTHER"))
        with patch(
            "inventory.ui.filedialog.askopenfilename", return_value=str(backup)
        ), patch("inventory.ui.messagebox.askyesno", return_value=True):
            self.app.restore()
        self.assertEqual(self.s.summary()["total"], 1)
        with patch(
            "inventory.ui.filedialog.askopenfilename", return_value=str(template)
        ), patch("inventory.ui.messagebox.askyesno", return_value=True):
            self.app.import_csv()
        with patch("inventory.ui.filedialog.askopenfilename", return_value=""), patch(
            "inventory.ui.filedialog.asksaveasfilename", return_value=""
        ):
            self.app.import_csv()
            self.app.restore()
            self.app.backup()
            self.app.export()
            self.app.template()
        self.assertEqual(self.s.summary()["total"], 1)

    def test_retired_material_not_highlighted_or_actionable(self):
        self.add(category="Material", quantity=0, min_stock=2, status="Retired")
        self.assertFalse(self.app.table.item("TEST-001", "tags"))
        self.assertIn("disabled", self.app.buttons["Issue"].state())
        self.assertEqual(self.s.summary()["low"], 0)

    def test_committed_import_read_failure_clears_old_selection(self):
        self.add()
        p = self.folder / "empty.csv"
        self.s.template(p)
        with patch(
            "inventory.ui.filedialog.askopenfilename", return_value=str(p)
        ), patch("inventory.ui.messagebox.askyesno", return_value=True), patch.object(
            self.app, "refresh", side_effect=sqlite3.OperationalError("read failure")
        ):
            self.app.import_csv()
        self.assertIn("imported", self.app.notice.get())
        self.assertIn("Refresh failed", self.app.notice.get())
        self.assertFalse(self.app.table.selection())
        self.assertIn("disabled", self.app.buttons["Check out"].state())

    def test_about_and_modal_f2_guard(self):
        with patch("inventory.ui.messagebox.showinfo") as info:
            self.app.about()
            self.assertIn("0.1.0a3", info.call_args.args[1])
        d = ItemDialog(self.app)
        with patch.object(self.app.scan_entry, "focus_set") as focus:
            self.app.focus_scan()
            focus.assert_not_called()
        d.destroy()


class LifecycleTests(unittest.TestCase):
    def test_twenty_actual_startup_close_cycles(self):
        with tempfile.TemporaryDirectory() as folder:
            for _ in range(20):
                root = tk.Tk()
                s = Store(Path(folder) / "test.sqlite3")
                app = App(root, s)
                root.update()
                app.close()

    def test_failed_main_startup_releases_os_lock(self):
        import inventory.ui as ui
        from inventory.instance import InstanceLock

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "start.sqlite3"
            with patch("inventory.ui.default_path", return_value=path), patch(
                "inventory.ui.App", side_effect=ValueError("startup failed")
            ), patch("inventory.ui.messagebox.showerror"):
                self.assertEqual(ui.main(), 1)
            lock = InstanceLock(path.with_suffix(".lock"))
            lock.close()

    def test_actual_main_startup_exit_reopens(self):
        import inventory.ui as ui

        original = ui.App
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.sqlite3"

            def short_run(root, store):
                app = original(root, store)
                root.after(15, app.close)
                return app

            with patch("inventory.ui.default_path", return_value=path), patch(
                "inventory.ui.App", side_effect=short_run
            ):
                for _ in range(3):
                    self.assertEqual(ui.main(), 0)
