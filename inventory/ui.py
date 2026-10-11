"""Minimal Tk desktop flows. Scanner selects; movements always need confirmation."""

import csv
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from . import __version__
from .instance import InstanceLock
from .store import Store, CATEGORIES, STATUSES, FIELDS, default_path

ERRORS = (ValueError, sqlite3.Error, OSError, csv.Error)


class ItemDialog(tk.Toplevel):
    def __init__(self, app, item=None, barcode=""):
        defaults = item or dict(
            item_id=app.store.next_id(),
            barcode=barcode,
            name="",
            category="Equipment",
            status="Available",
            quantity=1,
            min_stock=0,
            location="",
            notes="",
        )
        super().__init__(app.root)
        self.app, self.item, self.saved = app, item, False
        self.title("Edit item" if item else "Add item")
        self.transient(app.root)
        self.resizable(False, False)
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        self.values = {}
        self.widgets = {}
        for n, (f, label) in enumerate(
            zip(
                FIELDS,
                (
                    "Item ID",
                    "Barcode (blank = ID)",
                    "Name",
                    "Category",
                    "Status",
                    "Quantity",
                    "Low stock at",
                    "Location",
                    "Notes",
                ),
            )
        ):
            ttk.Label(frame, text=label).grid(
                row=n, column=0, sticky="w", padx=(0, 12), pady=5
            )
            self.values[f] = tk.StringVar(value=str(defaults[f]))
            if f in ("category", "status"):
                values = (
                    CATEGORIES
                    if f == "category"
                    else tuple(
                        s
                        for s in STATUSES
                        if s != "In use" or (item and item["status"] == "In use")
                    )
                )
                widget = ttk.Combobox(
                    frame,
                    textvariable=self.values[f],
                    values=values,
                    state="readonly",
                    width=36,
                )
            elif f == "notes":
                widget = tk.Text(
                    frame,
                    width=37,
                    height=5,
                    wrap="word",
                    font=("Segoe UI" if os.name == "nt" else "Helvetica", 10),
                )
                widget.insert("1.0", defaults[f])
            else:
                widget = ttk.Entry(frame, textvariable=self.values[f], width=39)
            widget.grid(row=n, column=1, sticky="ew", pady=5)
            self.widgets[f] = widget
        self.error = tk.StringVar()
        ttk.Label(
            frame, textvariable=self.error, foreground="#a62828", wraplength=420
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=8)
        footer = ttk.Frame(frame)
        footer.grid(row=10, column=0, columnspan=2, sticky="e")
        ttk.Button(footer, text="Cancel", command=self.destroy).pack(
            side="left", padx=6
        )
        ttk.Button(footer, text="Save", command=self.save).pack(side="left")
        self.widgets["category"].bind(
            "<<ComboboxSelected>>", lambda e: self.category_changed()
        )
        if item:
            self.widgets["item_id"].configure(state="disabled")
            self.widgets["category"].configure(state="disabled")
        self.category_changed()
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.widgets["name"].focus_set()

    def category_changed(self):
        asset = self.values["category"].get() != "Material"
        self.widgets["quantity"].configure(
            state="disabled" if self.item or asset else "normal"
        )
        self.widgets["min_stock"].configure(state="disabled" if asset else "normal")
        if asset:
            self.values["quantity"].set("1")
            self.values["min_stock"].set("0")

    def save(self):
        if self.saved:
            return
        data = {f: v.get() for f, v in self.values.items()}
        data["notes"] = self.widgets["notes"].get("1.0", "end-1c")
        try:
            if self.item:
                self.app.store.edit(self.item["item_id"], self.item["revision"], data)
            else:
                self.app.store.create(data)
        except ERRORS as exc:
            self.error.set(str(exc))
            return
        self.saved = True
        self.destroy()
        self.app.complete_save(data["item_id"], "Item saved.")


class MovementDialog(tk.Toplevel):
    def __init__(self, app, item, action):
        super().__init__(app.root)
        self.app, self.item, self.action, self.saved = app, item, action, False
        self.title(action)
        self.transient(app.root)
        self.resizable(False, False)
        frame = ttk.Frame(self, padding=20)
        frame.pack()
        ttk.Label(
            frame,
            text=f"{item['item_id']} · {item['name']}",
            wraplength=420,
            style="Heading.TLabel",
        ).pack(anchor="w", pady=(0, 12))
        ttk.Label(
            frame,
            text=f"{item['status']} · Quantity {item['quantity']}"
            + (f" · With {item['borrower']}" if item["borrower"] else ""),
            wraplength=420,
        ).pack(anchor="w")
        self.actor, self.amount, self.note = (
            tk.StringVar(),
            tk.StringVar(value="1"),
            tk.StringVar(),
        )
        for label, var in (
            ("Person / custodian", self.actor),
            ("Amount", self.amount),
            ("Note (optional)", self.note),
        ):
            if label == "Amount" and item["category"] != "Material":
                continue
            ttk.Label(frame, text=label).pack(anchor="w", pady=(12, 4))
            ttk.Entry(frame, textvariable=var, width=44).pack(fill="x")
        self.error = tk.StringVar()
        ttk.Label(
            frame, textvariable=self.error, foreground="#a62828", wraplength=420
        ).pack(anchor="w", pady=12)
        footer = ttk.Frame(frame)
        footer.pack(anchor="e")
        ttk.Button(footer, text="Cancel", command=self.destroy).pack(
            side="left", padx=6
        )
        ttk.Button(footer, text="Confirm " + action.lower(), command=self.save).pack(
            side="left"
        )
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()

    def save(self):
        if self.saved:
            return
        try:
            self.app.store.movement(
                self.item["item_id"],
                self.item["revision"],
                self.action,
                self.amount.get(),
                self.actor.get(),
                self.note.get(),
            )
        except ERRORS as exc:
            self.error.set(str(exc))
            return
        self.saved = True
        self.destroy()
        self.app.complete_save(self.item["item_id"], self.action + " saved.")


class App:
    def __init__(self, root, store):
        self.root, self.store = root, store
        self.rows, self.offset, self.total, self.pending, self.exact_id = (
            {},
            0,
            0,
            None,
            None,
        )
        root.title(f"Inventory · Drone Laboratory · {__version__} test candidate")
        root.geometry("1120x700")
        root.minsize(880, 560)
        style = ttk.Style(root)
        style.theme_use("clam")
        family = "Segoe UI" if os.name == "nt" else "Helvetica"
        style.configure(
            ".", font=(family, 10), foreground="#243348", background="#f4f6f9"
        )
        style.configure("Heading.TLabel", font=(family, 18, "bold"))
        style.configure("TButton", padding=(10, 7))
        style.configure(
            "Treeview", rowheight=30, background="white", fieldbackground="white"
        )
        style.configure("Treeview.Heading", font=(family, 10, "bold"), padding=7)
        body = ttk.Frame(root, padding=20)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(4, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Drone laboratory", style="Heading.TLabel").pack(
            side="left"
        )
        button = ttk.Menubutton(header, text="Data")
        button.pack(side="right")
        menu = tk.Menu(button, tearoff=False)
        button.configure(menu=menu)
        for label, command in (
            ("CSV template", self.template),
            ("Import CSV", self.import_csv),
            ("Export report", self.export),
            ("Backup", self.backup),
            ("Restore backup", self.restore),
            ("Data folder", self.data_folder),
            ("About", self.about),
        ):
            menu.add_command(label=label, command=lambda c=command: self.safe(c))
        self.counts = tk.StringVar()
        ttk.Label(body, textvariable=self.counts).grid(
            row=1, column=0, sticky="w", pady=(8, 16)
        )
        scanbar = ttk.Frame(body)
        scanbar.grid(row=2, column=0, sticky="ew")
        ttk.Label(scanbar, text="Scan / item ID").pack(side="left", padx=(0, 10))
        self.scan_value = tk.StringVar()
        self.scan_entry = ttk.Entry(scanbar, textvariable=self.scan_value, width=32)
        self.scan_entry.pack(side="left")
        self.scan_entry.bind("<Return>", lambda e: self.safe(self.scan))
        ttk.Button(scanbar, text="Find", command=lambda: self.safe(self.scan)).pack(
            side="left", padx=8
        )
        ttk.Button(
            scanbar,
            text="Add item",
            command=lambda: self.safe(lambda: ItemDialog(self)),
        ).pack(side="right")
        filters = ttk.Frame(body)
        filters.grid(row=3, column=0, sticky="ew", pady=14)
        self.query, self.category, self.status, self.low = (
            tk.StringVar(),
            tk.StringVar(value="All"),
            tk.StringVar(value="All"),
            tk.BooleanVar(),
        )
        ttk.Label(filters, text="Search").pack(side="left", padx=(0, 8))
        ttk.Entry(filters, textvariable=self.query, width=20).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        for var, values, width in (
            (self.category, ("All",) + CATEGORIES, 14),
            (self.status, ("All",) + STATUSES, 13),
        ):
            combo = ttk.Combobox(
                filters, textvariable=var, values=values, width=width, state="readonly"
            )
            combo.pack(side="left", padx=(0, 8))
            combo.bind("<<ComboboxSelected>>", lambda e: self.reload())
        ttk.Checkbutton(
            filters, text="Low stock", variable=self.low, command=self.reload
        ).pack(side="left", padx=(0, 8))
        ttk.Button(filters, text="Clear", command=self.clear).pack(side="left")
        self.query.trace_add("write", self.schedule)
        tableframe = ttk.Frame(body)
        tableframe.grid(row=4, column=0, sticky="nsew")
        fields = (
            "item_id",
            "name",
            "category",
            "status",
            "quantity",
            "location",
            "borrower",
        )
        self.table = ttk.Treeview(
            tableframe, columns=fields, show="headings", selectmode="browse"
        )
        for f, label, width in zip(
            fields,
            ("Item ID", "Name", "Category", "Status", "Qty", "Location", "With"),
            (125, 240, 110, 115, 55, 140, 130),
        ):
            self.table.heading(f, text=label)
            self.table.column(f, width=width, minwidth=width, stretch=f == "name")
        self.table.grid(row=0, column=0, sticky="nsew")
        tableframe.rowconfigure(0, weight=1)
        tableframe.columnconfigure(0, weight=1)
        y = ttk.Scrollbar(tableframe, orient="vertical", command=self.table.yview)
        y.grid(row=0, column=1, sticky="ns")
        x = ttk.Scrollbar(tableframe, orient="horizontal", command=self.table.xview)
        x.grid(row=1, column=0, sticky="ew")
        self.table.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        self.table.tag_configure("attention", background="#fff1d9")
        self.table.bind("<<TreeviewSelect>>", lambda e: self.update_actions())
        self.table.bind("<Double-1>", lambda e: self.safe(self.edit))
        actions = ttk.Frame(body)
        actions.grid(row=5, column=0, sticky="ew", pady=(12, 10))
        self.buttons = {}
        for label, command in (
            ("Edit", self.edit),
            ("Check out", lambda: self.move("Check out")),
            ("Return", lambda: self.move("Return")),
            ("Receive", lambda: self.move("Receive")),
            ("Issue", lambda: self.move("Issue")),
            ("History", self.history),
        ):
            b = ttk.Button(actions, text=label, command=lambda c=command: self.safe(c))
            b.pack(side="left", padx=(0, 5))
            self.buttons[label] = b
        self.page = tk.StringVar()
        ttk.Button(
            actions,
            text=">",
            width=2,
            command=lambda: self.safe(lambda: self.change_page(250)),
        ).pack(side="right")
        ttk.Label(actions, textvariable=self.page).pack(side="right", padx=8)
        ttk.Button(
            actions,
            text="<",
            width=2,
            command=lambda: self.safe(lambda: self.change_page(-250)),
        ).pack(side="right")
        self.detail, self.notice = tk.StringVar(), tk.StringVar(
            value="Offline · F2 focuses scanner · Stock changes require confirmation."
        )
        self.detail_label = ttk.Label(body, textvariable=self.detail, wraplength=800)
        self.detail_label.grid(row=6, column=0, sticky="w")
        self.notice_label = ttk.Label(body, textvariable=self.notice, wraplength=800)
        self.notice_label.grid(row=7, column=0, sticky="w", pady=(8, 0))
        root.bind("<Configure>", self.resize)
        root.bind("<F2>", lambda e: self.focus_scan())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        self.focus_scan()

    def resize(self, event):
        if event.widget == self.root:
            for label in (self.detail_label, self.notice_label):
                label.configure(wraplength=max(300, event.width - 40))

    def safe(self, command):
        try:
            return command()
        except ERRORS as exc:
            messagebox.showerror("Inventory", str(exc), parent=self.root)

    def focus_scan(self):
        if not self.root.grab_current():
            self.scan_entry.focus_set()
            self.scan_entry.selection_range(0, "end")

    def cancel_search(self):
        if self.pending is not None:
            self.root.after_cancel(self.pending)
            self.pending = None

    def schedule(self, *args):
        self.cancel_search()
        self.pending = self.root.after(180, self.reload)

    def reload(self):
        self.cancel_search()
        self.offset = 0
        self.exact_id = None
        self.safe(self.refresh)

    def reset_filters(self):
        self.query.set("")
        self.category.set("All")
        self.status.set("All")
        self.low.set(False)
        self.cancel_search()
        self.offset = 0
        self.exact_id = None

    def clear(self):
        self.reset_filters()
        self.safe(self.refresh)
        self.focus_scan()

    def refresh(self, select=None):
        chosen = select or (
            self.table.selection()[0] if self.table.selection() else None
        )
        rows, self.total = self.store.search(
            self.query.get(),
            self.category.get(),
            self.status.get(),
            self.low.get(),
            self.offset,
            exact_id=self.exact_id,
        )
        if not rows and self.offset:
            self.offset = max(0, ((self.total - 1) // 250) * 250)
            rows, self.total = self.store.search(
                self.query.get(),
                self.category.get(),
                self.status.get(),
                self.low.get(),
                self.offset,
                exact_id=self.exact_id,
            )
        counts = (
            self.store.summary()
        )  # Complete reads before replacing the visible state.
        self.rows = {r["item_id"]: r for r in rows}
        self.table.delete(*self.table.get_children())
        for r in rows:
            attention = r["status"] in ("Maintenance", "Damaged", "Lost") or (
                r["category"] == "Material"
                and r["status"] != "Retired"
                and r["quantity"] <= r["min_stock"]
            )
            self.table.insert(
                "",
                "end",
                iid=r["item_id"],
                values=tuple(r[f] for f in self.table["columns"]),
                tags=("attention",) if attention else (),
            )
        if chosen in self.rows:
            self.table.selection_set(chosen)
            self.table.see(chosen)
        self.counts.set(
            f"{counts['total']} records     {counts['in_use']} checked out     {counts['attention']} need attention     {counts['low']} low stock"
        )
        self.page.set(
            f"{self.offset+1 if self.total else 0}-{min(self.offset+250,self.total)} / {self.total}"
        )
        self.update_actions()

    def selected(self):
        ids = self.table.selection()
        if not ids or ids[0] not in self.rows:
            raise ValueError("Select or scan an item first.")
        return self.rows[ids[0]]

    def update_actions(self):
        try:
            r = self.selected()
        except ValueError:
            r = None
        for label, b in self.buttons.items():
            enabled = r is not None
            if r and label in ("Check out", "Return"):
                enabled = r["category"] != "Material" and r["status"] == (
                    "Available" if label == "Check out" else "In use"
                )
            if r and label in ("Receive", "Issue"):
                enabled = r["category"] == "Material" and r["status"] == "Available"
            b.configure(state="normal" if enabled else "disabled")
        notes = " ".join(r["notes"].split()) if r else ""
        if len(notes) > 180:
            notes = notes[:180] + "… (Edit shows full notes)"
        self.detail.set(
            f"Barcode {r['barcode']} · Low stock at {r['min_stock']} · {notes}"
            if r
            else "Select an item. F2 focuses the scanner field."
        )

    def scan(self):
        code = self.scan_value.get()
        self.scan_value.set("")
        self.table.selection_remove(*self.table.selection())
        self.update_actions()
        r = self.store.lookup(code)
        if r:
            self.reveal(r["item_id"])
            self.notice.set("Item selected. Choose an action.")
            self.focus_scan()
        elif messagebox.askyesno(
            "Unknown barcode", "No matching item. Add this barcode?", parent=self.root
        ):
            ItemDialog(self, barcode=code.strip().upper())
        else:
            self.notice.set("No item selected.")
            self.focus_scan()

    def reveal(self, item_id):
        self.query.set("")
        self.category.set("All")
        self.status.set("All")
        self.low.set(False)
        self.cancel_search()
        self.exact_id = item_id
        self.offset = 0
        self.refresh(select=item_id)

    def complete_save(self, item_id, message):
        self.notice.set(message)
        try:
            self.reveal(item_id)
        except ERRORS as exc:
            self.table.selection_remove(*self.table.selection())
            self.update_actions()
            self.notice.set(message + " Refresh failed; press Clear to retry.")
            messagebox.showerror("Saved; refresh failed", str(exc), parent=self.root)
        self.focus_scan()

    def complete_data_refresh(self, message):
        self.notice.set(message)
        self.table.selection_remove(*self.table.selection())
        self.update_actions()
        try:
            self.reset_filters()
            self.refresh()
        except ERRORS as exc:
            self.table.selection_remove(*self.table.selection())
            self.update_actions()
            self.notice.set(message + " Refresh failed; press Clear to retry.")
            messagebox.showerror("Saved; refresh failed", str(exc), parent=self.root)

    def change_page(self, delta):
        self.cancel_search()
        if 0 <= self.offset + delta < self.total:
            self.offset += delta
            self.refresh()

    def edit(self):
        ItemDialog(self, self.selected())

    def move(self, action):
        MovementDialog(self, self.selected(), action)

    def history(self):
        r = self.selected()
        lines = []
        for event in self.store.history(r["item_id"]):
            d = self.store._snapshot(event["snapshot"])
            if type(event["delta"]) is not int:
                raise ValueError("History data is damaged.")
            lines.append(
                f"{event['occurred_at']}  {event['action']}  {event['delta']:+d}  {event['actor']}\nStatus {d['status']} · Quantity {d['quantity']} · Location {d['location']}\nBarcode {d['barcode']} · With {d['borrower']}\n{event['note']}\nNotes: {d['notes']}\n\n"
            )
        win = tk.Toplevel(self.root)
        win.title("History · " + r["item_id"])
        win.geometry("850x450")
        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame, text=r["name"] + " · Latest 500 events · UTC", wraplength=790
        ).pack(anchor="w", pady=(0, 12))
        box = tk.Text(frame, wrap="word", background="white")
        box.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, command=box.yview)
        scrollbar.pack(side="right", fill="y")
        box.configure(yscrollcommand=scrollbar.set)
        box.insert("end", "".join(lines))
        box.configure(state="disabled")

    def template(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".csv",
            initialfile="inventory-import-template.csv",
        )
        if path:
            self.store.template(path)
            self.notice.set("Template saved. Add rows, then Import CSV.")

    def import_csv(self):
        path = filedialog.askopenfilename(
            parent=self.root, filetypes=[("CSV", "*.csv")]
        )
        if path and messagebox.askyesno(
            "Import CSV",
            "Add all rows from the template? Existing IDs will cause the entire import to be rejected.",
            parent=self.root,
        ):
            count = self.store.import_csv(path)
            self.complete_data_refresh(f"{count} items imported.")

    def export(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".csv",
            initialfile="inventory-report.csv",
        )
        if path:
            self.store.export(path)
            self.notice.set(
                "Report exported. Use the import template for adding items."
            )

    def backup(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".sqlite3",
            initialfile="inventory-backup.sqlite3",
        )
        if path:
            self.store.backup(path)
            self.notice.set("Backup saved and integrity checked.")

    def restore(self):
        path = filedialog.askopenfilename(
            parent=self.root, filetypes=[("Inventory backup", "*.sqlite3")]
        )
        if path and messagebox.askyesno(
            "Restore backup",
            "Replace current records with this backup? A recovery copy of current data will be saved first.",
            parent=self.root,
        ):
            recovery = self.store.restore(path)
            self.complete_data_refresh(
                "Restored. Previous data saved at " + str(recovery)
            )

    def data_folder(self):
        if os.name == "nt":
            os.startfile(str(self.store.path.parent))
        else:
            messagebox.showinfo(
                "Data folder", str(self.store.path.parent), parent=self.root
            )

    def about(self):
        messagebox.showinfo(
            "Inventory",
            f"Inventory {__version__}\nAuthor: MD\nDrone laboratory equipment, tools and materials.\nOffline · single workstation · whole unit stock\nUSB keyboard scanner with Enter suffix · F2 focus\nRebuilt private test candidate · schema 2\nData: {self.store.path}",
            parent=self.root,
        )

    def close(self):
        self.cancel_search()
        self.store.close()
        self.root.destroy()


def main():
    root = None
    store = None
    lock = None
    try:
        root = tk.Tk()
        path = default_path()
        lock = InstanceLock(path.with_suffix(".lock"))
        store = Store(path)
        App(root, store)
        root.mainloop()
        return 0
    except (tk.TclError,) + ERRORS as exc:
        if root is not None:
            messagebox.showerror("Inventory could not start", str(exc), parent=root)
        return 1
    finally:
        if store is not None:
            store.close()
        if lock is not None:
            lock.close()
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass
