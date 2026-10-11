import csv
import sqlite3
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from inventory import __version__
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
        self.wait_task()
        for dialog in self.dialogs(tk.Toplevel):
            dialog.destroy()
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

    def wait_task(self):
        end = time.monotonic() + 10
        while self.app.busy and time.monotonic() < end:
            self.root.update()
            time.sleep(0.005)
        self.assertFalse(self.app.busy, "Data worker did not finish within 10 seconds")

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
                self.wait_task()
            self.assertTrue(path.exists())
        self.s.create(item(id="OTHER", barcode="OTHER"))
        with (
            patch("inventory.ui.filedialog.askopenfilename", return_value=str(backup)),
            patch("inventory.ui.messagebox.askyesno", return_value=True),
        ):
            self.app.restore()
            self.wait_task()
        self.assertEqual(self.s.summary()["total"], 1)
        with (
            patch(
                "inventory.ui.filedialog.askopenfilename", return_value=str(template)
            ),
            patch("inventory.ui.messagebox.askyesno", return_value=True),
        ):
            self.app.import_csv()
            self.wait_task()
        with (
            patch("inventory.ui.filedialog.askopenfilename", return_value=""),
            patch("inventory.ui.filedialog.asksaveasfilename", return_value=""),
        ):
            self.app.import_csv()
            self.wait_task()
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
        with (
            patch("inventory.ui.filedialog.askopenfilename", return_value=str(p)),
            patch("inventory.ui.messagebox.askyesno", return_value=True),
            patch.object(
                self.app,
                "refresh",
                side_effect=sqlite3.OperationalError("read failure"),
            ),
        ):
            self.app.import_csv()
            self.wait_task()
        self.assertIn("imported", self.app.notice.get())
        self.assertIn("Refresh failed", self.app.notice.get())
        self.assertFalse(self.app.table.selection())
        self.assertIn("disabled", self.app.buttons["Check out"].state())

    def test_about_and_modal_f2_guard(self):
        with patch("inventory.ui.messagebox.showinfo") as info:
            self.app.about()
            self.assertIn(__version__, info.call_args.args[1])
        d = ItemDialog(self.app)
        with patch.object(self.app.scan_entry, "focus_set") as focus:
            self.app.focus_scan()
            focus.assert_not_called()
        d.destroy()

    def test_stock_count_preview_required_fields_and_history(self):
        self.add(category="Material", quantity=10)
        self.assertEqual(
            self.app.menu.entrycget(self.app.count_menu_index, "state"), "normal"
        )
        self.app.move("Stock count")
        d = self.dialogs(MovementDialog)[0]
        self.assertIn("disabled", d.confirm.state())
        d.actor.set("Counter")
        d.amount.set("7")
        self.assertIn("10 -> 7 (-3)", d.preview.get())
        self.assertIn("disabled", d.confirm.state())
        d.note.set("Shelf count")
        self.assertNotIn("disabled", d.confirm.state())
        # Scanner Enter must never invoke the confirmation.
        d.entries["amount"].focus_force()
        self.root.update()
        d.entries["amount"].event_generate("<Return>")
        self.root.update()
        self.assertEqual(self.s.get("TEST-001")["quantity"], 10)
        d.save()
        d.save()
        self.assertEqual(self.s.get("TEST-001")["quantity"], 7)
        self.assertEqual(len(self.s.history("TEST-001")), 2)
        self.app.history()
        text = self.dialogs(tk.Toplevel)[0].winfo_children()[0].winfo_children()[1]
        self.assertIn("Stock count (Issue)", text.get("1.0", "end"))

    def test_dirty_item_cancel_and_status_confirmation(self):
        self.add()
        d = ItemDialog(self.app, self.app.selected())
        d.values["name"].set("Changed")
        with patch("inventory.ui.messagebox.askyesno", return_value=False):
            d.cancel()
            self.app.close()
        self.assertTrue(d.winfo_exists())
        self.assertEqual(self.s.get("TEST-001")["name"], "Test equipment")
        d.values["status"].set("Retired")
        with patch("inventory.ui.messagebox.askyesno", return_value=False):
            d.save()
        self.assertFalse(d.saved)
        with patch("inventory.ui.messagebox.askyesno", return_value=True):
            d.save()
        self.assertEqual(self.s.get("TEST-001")["status"], "Retired")
        d = ItemDialog(self.app, self.app.selected())
        with patch("inventory.ui.messagebox.askyesno") as prompt:
            d.cancel()
            prompt.assert_not_called()

    def test_fresh_dialog_state_shortcuts_and_failed_refresh_clear_actions(self):
        self.add()
        self.s.movement("TEST-001", 1, "Check out", actor="Other")
        self.app.safe(lambda: self.app.move("Check out"))
        self.assertFalse(self.dialogs(MovementDialog))
        self.error.assert_called_once()
        self.app.refresh(select="TEST-001")
        self.app.edit()
        d = self.dialogs(ItemDialog)[0]
        self.assertEqual(d.item["revision"], 2)
        with patch.object(self.app, "refresh") as refresh:
            self.app.shortcut(self.app.refresh)
            refresh.assert_not_called()
        d.destroy()
        self.app.query.set("Test")
        self.app.reload()
        with patch.object(
            self.s, "search", side_effect=sqlite3.OperationalError("read failed")
        ):
            self.app.shortcut(self.app.refresh)
        self.assertFalse(self.app.table.selection())
        self.assertIn("disabled", self.app.buttons["Return"].state())
        self.assertEqual(self.app.query.get(), "Test")

    def test_data_worker_responsive_blocks_duplicate_close_and_recovers(self):
        self.add()
        target = self.folder / "slow.sqlite3"
        original = Store.backup
        calls = []

        def slow(worker, path):
            calls.append(worker)
            time.sleep(0.2)
            return original(worker, path)

        ticks = []
        with patch.object(Store, "backup", slow):
            self.app.data_task(
                "Backup", "backup", target, lambda _: ticks.append("done")
            )
            self.root.after(10, lambda: ticks.append("heartbeat"))
            self.app.data_task(
                "Backup", "backup", target, lambda _: ticks.append("duplicate")
            )
            self.app.close()
            self.assertTrue(self.root.winfo_exists())
            self.assertIn("disabled", self.app.buttons["Check out"].state())
            self.wait_task()
        self.assertEqual(ticks, ["heartbeat", "done"])
        self.assertEqual(len(calls), 1)
        self.assertIsNot(calls[0], self.s)
        self.assertTrue(target.exists())
        self.assertFalse(self.dialogs(tk.Toplevel))
        with patch.object(Store, "backup", side_effect=OSError("disk full")):
            self.app.data_task(
                "Backup",
                "backup",
                target,
                lambda _: self.fail("Failed worker reported success"),
            )
            self.wait_task()
        self.assertEqual(self.s.summary()["total"], 1)
        self.assertIn("failed", self.app.notice.get())
        self.error.assert_called_once()
        self.app.reveal("TEST-001")
        self.assertNotIn("disabled", self.app.buttons["Check out"].state())

    def test_async_bad_import_preserves_live_data_and_existing_output(self):
        self.add()
        p = self.folder / "bad.csv"
        p.write_text("wrong,headers\nx,y\n")
        self.app.data_task(
            "Import CSV", "import_csv", p, lambda _: self.fail("Bad import accepted")
        )
        self.wait_task()
        self.assertEqual(len(self.s.history("TEST-001")), 1)
        self.assertIn("failed", self.app.notice.get())
        report = self.folder / "report.csv"
        report.write_text("preserve")
        with patch.object(
            Store, "_atomic_file", side_effect=PermissionError("read only")
        ):
            self.app.data_task(
                "Export report", "export", report, lambda _: self.fail("Write accepted")
            )
            self.wait_task()
        self.assertEqual(report.read_text(), "preserve")

    def test_f5_applies_pending_search_and_modal_shortcuts_keep_input(self):
        self.add()
        self.s.create(item(id="SECOND", barcode="SECOND", name="Another item"))
        self.app.query.set("Another")
        self.app.scan_entry.focus_force()
        self.root.update()
        self.app.scan_entry.event_generate("<F5>")
        self.root.update()
        self.assertEqual(tuple(self.app.rows), ("SECOND",))
        self.assertIsNone(self.app.pending)
        self.assertIsNone(self.app.exact_id)
        self.app.scan_entry.event_generate("<Control-f>")
        self.root.update()
        self.assertEqual(self.root.focus_get(), self.app.search_entry)
        self.app.search_entry.event_generate("<Control-n>")
        self.root.update()
        d = self.dialogs(ItemDialog)[0]
        d.values["name"].set("Keyboard saved")
        d.widgets["name"].focus_force()
        self.root.update()
        d.widgets["name"].event_generate("<Control-s>")
        self.root.update()
        self.assertTrue(d.saved)
        self.assertEqual(self.s.summary()["total"], 3)

    def test_worker_start_and_connection_failure_release_busy_modal(self):
        p = self.folder / "backup.sqlite3"
        with patch(
            "inventory.ui.threading.Thread.start", side_effect=RuntimeError("No thread")
        ):
            self.app.data_task(
                "Backup", "backup", p, lambda _: self.fail("Started unexpectedly")
            )
        self.assertFalse(self.app.busy)
        self.assertFalse(self.dialogs(tk.Toplevel))
        with patch(
            "inventory.ui.Store",
            side_effect=sqlite3.OperationalError("Database locked"),
        ):
            self.app.data_task(
                "Backup", "backup", p, lambda _: self.fail("Opened unexpectedly")
            )
            self.wait_task()
        self.assertFalse(self.dialogs(tk.Toplevel))
        self.assertFalse(p.exists())
        self.assertEqual(self.error.call_count, 2)


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
            with (
                patch("inventory.ui.default_path", return_value=path),
                patch("inventory.ui.App", side_effect=ValueError("startup failed")),
                patch("inventory.ui.messagebox.showerror"),
            ):
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

            with (
                patch("inventory.ui.default_path", return_value=path),
                patch("inventory.ui.App", side_effect=short_run),
            ):
                for _ in range(3):
                    self.assertEqual(ui.main(), 0)
