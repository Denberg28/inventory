"""Minimal Tk desktop flows. Scanner selects; movements always need confirmation."""

import csv
import os
import queue
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from . import __version__
from .instance import InstanceLock
from .store import Store, CATEGORIES, STATUSES, FIELDS, default_path, integer, validate

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
        ttk.Button(footer, text="Cancel", command=self.cancel).pack(side="left", padx=6)
        ttk.Button(footer, text="Save", command=self.save).pack(side="left")
        self.widgets["category"].bind(
            "<<ComboboxSelected>>", lambda e: self.category_changed()
        )
        if item:
            self.widgets["item_id"].configure(state="disabled")
            self.widgets["category"].configure(state="disabled")
        self.category_changed()
        self.initial = self.data()
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<Control-s>", lambda e: self.save())
        self.protocol("WM_DELETE_WINDOW", self.cancel)
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

    def data(self):
        data = {f: v.get() for f, v in self.values.items()}
        data["notes"] = self.widgets["notes"].get("1.0", "end-1c")
        return data

    def cancel(self):
        if self.data() != self.initial and not messagebox.askyesno(
            "Unsaved changes", "Discard changes to this item?", parent=self
        ):
            return
        self.destroy()

    def save(self):
        if self.saved:
            return
        data = self.data()
        try:
            validate(data)
            if (
                data["status"] in ("Lost", "Retired")
                and (not self.item or data["status"] != self.item["status"])
                and not messagebox.askyesno(
                    "Confirm status",
                    f"Mark this item {data['status'].lower()}? Its history will be retained.",
                    parent=self,
                )
            ):
                return
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
            tk.StringVar(
                value=str(item["quantity"]) if action == "Stock count" else "1"
            ),
            tk.StringVar(),
        )
        self.entries = {}
        for key, label, var in (
            (
                "actor",
                {
                    "Check out": "Borrower",
                    "Return": "Received by",
                    "Receive": "Received by",
                    "Issue": "Issued to / person",
                    "Stock count": "Counted by",
                }[action],
                self.actor,
            ),
            (
                "amount",
                "Counted quantity" if action == "Stock count" else "Amount",
                self.amount,
            ),
            (
                "note",
                "Reason (required)" if action == "Stock count" else "Note (optional)",
                self.note,
            ),
        ):
            if key == "amount" and item["category"] != "Material":
                continue
            ttk.Label(frame, text=label).pack(anchor="w", pady=(12, 4))
            self.entries[key] = ttk.Entry(frame, textvariable=var, width=44)
            self.entries[key].pack(fill="x")
        self.preview = tk.StringVar()
        ttk.Label(frame, textvariable=self.preview, wraplength=420).pack(
            anchor="w", pady=(12, 0)
        )
        self.error = tk.StringVar()
        ttk.Label(
            frame, textvariable=self.error, foreground="#a62828", wraplength=420
        ).pack(anchor="w", pady=12)
        footer = ttk.Frame(frame)
        footer.pack(anchor="e")
        ttk.Button(footer, text="Cancel", command=self.destroy).pack(
            side="left", padx=6
        )
        self.confirm = ttk.Button(
            footer, text="Confirm " + action.lower(), command=self.save
        )
        self.confirm.pack(side="left")
        for var in (self.actor, self.amount, self.note):
            var.trace_add("write", self.update_preview)
        self.update_preview()
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.entries["actor"].focus_set()

    def update_preview(self, *args):
        valid = bool(self.actor.get().strip())
        if self.item["category"] == "Material":
            try:
                n = integer(self.amount.get(), "Amount")
                if self.action != "Stock count" and n == 0:
                    raise ValueError("Amount must be greater than zero.")
                qty = self.item["quantity"]
                result = integer(
                    (
                        n
                        if self.action == "Stock count"
                        else qty + (n if self.action == "Receive" else -n)
                    ),
                    "Resulting quantity",
                )
                self.preview.set(f"Quantity: {qty} -> {result} ({result-qty:+d})")
            except ValueError as exc:
                self.preview.set(str(exc))
                valid = False
        else:
            self.preview.set(
                "Status: "
                + self.item["status"]
                + " -> "
                + ("In use" if self.action == "Check out" else "Available")
            )
        if self.action == "Stock count":
            valid = valid and bool(self.note.get().strip())
        self.confirm.configure(state="normal" if valid else "disabled")

    def save(self):
        if self.saved:
            return
        try:
            if self.action == "Stock count":
                self.app.store.reconcile(
                    self.item["item_id"],
                    self.item["revision"],
                    self.amount.get(),
                    self.actor.get(),
                    self.note.get(),
                )
            else:
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
        self.busy = False
        self.task_poll = None
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
        menu = self.menu = tk.Menu(button, tearoff=False)
        button.configure(menu=menu)
        for label, command in (
            ("Refresh (F5)", self.refresh_view),
            ("Stock count…", lambda: self.move("Stock count")),
            ("CSV template", self.template),
            ("Import CSV", self.import_csv),
            ("Export report", self.export),
            ("Backup", self.backup),
            ("Restore backup", self.restore),
            ("Data folder", self.data_folder),
            ("About", self.about),
        ):
            menu.add_command(label=label, command=lambda c=command: self.safe(c))
        self.count_menu_index = 1
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
            tk.StringVar(value="All categories"),
            tk.StringVar(value="All statuses"),
            tk.BooleanVar(),
        )
        ttk.Label(filters, text="Search").pack(side="left", padx=(0, 8))
        self.search_entry = ttk.Entry(filters, textvariable=self.query, width=20)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        for var, values, width in (
            (self.category, ("All categories",) + CATEGORIES, 14),
            (self.status, ("All statuses",) + STATUSES, 13),
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
        root.bind("<F5>", lambda e: self.shortcut(self.refresh_view))
        root.bind("<Control-f>", lambda e: self.shortcut(self.search_entry.focus_set))
        root.bind("<Control-n>", lambda e: self.shortcut(lambda: ItemDialog(self)))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        self.focus_scan()

    def resize(self, event):
        if event.widget == self.root:
            for label in (self.detail_label, self.notice_label):
                label.configure(wraplength=max(300, event.width - 40))

    def safe(self, command):
        if self.busy:
            self.notice.set("Working. Wait for the data operation to finish.")
            return
        try:
            return command()
        except ERRORS as exc:
            self.table.selection_remove(*self.table.selection())
            self.update_actions()
            messagebox.showerror("Inventory", str(exc), parent=self.root)

    def shortcut(self, command):
        if not self.root.grab_current():
            self.safe(command)
        return "break"

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
        if not self.busy:
            self.pending = self.root.after(180, self.reload)

    def reload(self):
        self.cancel_search()
        self.offset = 0
        self.exact_id = None
        self.safe(self.refresh)

    def reset_filters(self):
        self.query.set("")
        self.category.set("All categories")
        self.status.set("All statuses")
        self.low.set(False)
        self.cancel_search()
        self.offset = 0
        self.exact_id = None

    def clear(self):
        self.reset_filters()
        self.safe(self.refresh)
        self.focus_scan()

    def refresh_view(self):
        if self.pending is not None or self.exact_id is not None:
            self.offset = 0
        self.cancel_search()
        self.exact_id = None
        self.refresh()

    def refresh(self, select=None):
        chosen = select or (
            self.table.selection()[0] if self.table.selection() else None
        )
        rows, self.total = self.store.search(
            self.query.get(),
            "All" if self.category.get() == "All categories" else self.category.get(),
            "All" if self.status.get() == "All statuses" else self.status.get(),
            self.low.get(),
            self.offset,
            exact_id=self.exact_id,
        )
        if not rows and self.offset:
            self.offset = max(0, ((self.total - 1) // 250) * 250)
            rows, self.total = self.store.search(
                self.query.get(),
                (
                    "All"
                    if self.category.get() == "All categories"
                    else self.category.get()
                ),
                "All" if self.status.get() == "All statuses" else self.status.get(),
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
            enabled = r is not None and not self.busy
            if r and label in ("Check out", "Return"):
                enabled = (
                    not self.busy
                    and r["category"] != "Material"
                    and r["status"]
                    == ("Available" if label == "Check out" else "In use")
                )
            if r and label in ("Receive", "Issue"):
                enabled = (
                    not self.busy
                    and r["category"] == "Material"
                    and r["status"] == "Available"
                )
            b.configure(state="normal" if enabled else "disabled")
        self.menu.entryconfigure(
            self.count_menu_index,
            state=(
                "normal"
                if r
                and not self.busy
                and r["category"] == "Material"
                and r["status"] == "Available"
                else "disabled"
            ),
        )
        notes = " ".join(r["notes"].split()) if r else ""
        if len(notes) > 180:
            notes = notes[:180] + "… (Edit shows full notes)"
        self.detail.set(
            f"Barcode {r['barcode']} · Low stock at {r['min_stock']} · {notes}"
            if r
            else (
                "No matching items. Clear filters or add an item."
                if not self.rows
                else "Select an item. F2 focuses the scanner field."
            )
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
        self.category.set("All categories")
        self.status.set("All statuses")
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
        ItemDialog(self, self.store.get(self.selected()["item_id"]))

    def move(self, action):
        r = self.store.get(self.selected()["item_id"])
        allowed = (
            r["category"] == "Material"
            and r["status"] == "Available"
            and action in ("Receive", "Issue", "Stock count")
        ) or (
            r["category"] != "Material"
            and (
                (action == "Check out" and r["status"] == "Available")
                or (action == "Return" and r["status"] == "In use")
            )
        )
        if not allowed:
            raise ValueError(
                "Action conflicts with current category/status. Refresh and select again."
            )
        MovementDialog(self, r, action)

    def history(self):
        r = self.selected()
        lines = []
        for event in self.store.history(r["item_id"]):
            d = self.store._snapshot(event["snapshot"])
            if type(event["delta"]) is not int:
                raise ValueError("History data is damaged.")
            action = (
                "Stock count (" + event["action"] + ")"
                if event["note"].startswith("Stock count:")
                else event["action"]
            )
            lines.append(
                f"{event['occurred_at']}  {action}  {event['delta']:+d}  {event['actor']}\nStatus {d['status']} · Quantity {d['quantity']} · Location {d['location']}\nBarcode {d['barcode']} · With {d['borrower']}\n{event['note']}\nNotes: {d['notes']}\n\n"
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

    def data_task(self, label, method, path, completed):
        """One worker owns its SQLite connection; only Tk's thread touches UI."""
        if self.busy:
            return
        self.cancel_search()
        results = queue.Queue(maxsize=1)
        database = self.store.path
        self.busy = True
        self.table.selection_remove(*self.table.selection())
        self.update_actions()
        win = tk.Toplevel(self.root)
        win.title(label)
        win.transient(self.root)
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=20)
        frame.pack()
        ttk.Label(frame, text=label + "…", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            frame, text="Please wait. Keep Inventory open until this finishes."
        ).pack(pady=12)
        progress = ttk.Progressbar(frame, mode="indeterminate", length=360)
        progress.pack(fill="x")
        progress.start(30)
        win.protocol(
            "WM_DELETE_WINDOW",
            lambda: self.notice.set(
                "Wait for the data operation to finish before closing."
            ),
        )
        win.grab_set()
        self.notice.set(label + " in progress…")

        def work():
            try:
                worker = Store(database)
                try:
                    value = getattr(worker, method)(path)
                finally:
                    worker.close()
                result = (True, value)
            except Exception as exc:
                result = (False, f"{type(exc).__name__}: {exc}")
            results.put(result)

        def poll():
            self.task_poll = None
            try:
                ok, value = results.get_nowait()
            except queue.Empty:
                self.task_poll = self.root.after(30, poll)
                return
            progress.stop()
            win.destroy()
            self.busy = False
            if ok:
                completed(value)
            else:
                self.notice.set(label + " failed. Review the error and retry.")
                messagebox.showerror(label + " failed", value, parent=self.root)
            self.update_actions()
            self.focus_scan()

        try:
            # Non-daemon: never abandon a transaction at normal interpreter exit.
            threading.Thread(target=work, name="inventory-data", daemon=False).start()
        except RuntimeError as exc:
            progress.stop()
            win.destroy()
            self.busy = False
            self.update_actions()
            self.notice.set(label + " could not start. Retry the operation.")
            messagebox.showerror(label + " could not start", str(exc), parent=self.root)
            self.focus_scan()
            return
        self.task_poll = self.root.after(30, poll)

    def import_csv(self):
        path = filedialog.askopenfilename(
            parent=self.root, filetypes=[("CSV", "*.csv")]
        )
        if path and messagebox.askyesno(
            "Import CSV",
            "Add all rows from the template? Existing IDs will cause the entire import to be rejected.",
            parent=self.root,
        ):
            self.data_task(
                "Import CSV",
                "import_csv",
                path,
                lambda count: self.complete_data_refresh(f"{count} items imported."),
            )

    def export(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".csv",
            initialfile="inventory-report.csv",
        )
        if path:
            self.data_task(
                "Export report",
                "export",
                path,
                lambda _: self.notice.set(
                    "Report exported. Use the import template for adding items."
                ),
            )

    def backup(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".sqlite3",
            initialfile="inventory-backup.sqlite3",
        )
        if path:
            self.data_task(
                "Backup",
                "backup",
                path,
                lambda _: self.notice.set("Backup saved and integrity checked."),
            )

    def restore(self):
        path = filedialog.askopenfilename(
            parent=self.root, filetypes=[("Inventory backup", "*.sqlite3")]
        )
        if path and messagebox.askyesno(
            "Restore backup",
            "Replace current records with this backup? A recovery copy of current data will be saved first.",
            parent=self.root,
        ):
            self.data_task(
                "Restore backup",
                "restore",
                path,
                lambda recovery: self.complete_data_refresh(
                    "Restored. Previous data saved at " + str(recovery)
                ),
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
            f"Inventory {__version__}\nAuthor: MD\nDrone laboratory equipment, tools and materials.\nOffline · single workstation · whole unit stock\nUSB keyboard scanner with Enter suffix · F2 focus\nF5 refresh · Ctrl+F search · Ctrl+N add · Ctrl+S save item\nStock count: select a material, then Data -> Stock count\nPrivate test candidate · schema 2\nData: {self.store.path}",
            parent=self.root,
        )

    def close(self):
        if self.busy:
            self.notice.set("Wait for the data operation to finish before closing.")
            return
        dialog = self.root.grab_current()
        if isinstance(dialog, ItemDialog):
            dialog.cancel()
            if dialog.winfo_exists():
                return
        elif dialog:
            # A modal movement still owns input; close it explicitly first.
            return
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
