package ph.dronelab.inventory;

import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.*;
import android.text.*;
import android.view.*;
import android.widget.*;
import com.google.zxing.integration.android.*;
import java.nio.charset.StandardCharsets;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;

public final class MainActivity extends Activity {
  static final int NAVY = 0xff173c68,
      INK = 0xff192a3e,
      MUTED = 0xff637287,
      BG = 0xfff5f7fa,
      AUTH = 41,
      WRITE = 42,
      READ_CSV = 43,
      READ_BACKUP = 44;
  final ArrayList<Dialog> dialogs = new ArrayList<>();
  final ExecutorService worker = Executors.newSingleThreadExecutor();
  Storage storage;
  Model model;
  LinearLayout root, list;
  EditText search;
  String query = "";
  int tab = 0, visibleLimit = 200;
  ScrollView itemScroll;
  int scrollPosition = 0;
  boolean unlocked = false,
      authPending = false,
      authDismissed = false,
      resumed = false,
      busy = false,
      showArchived = false,
      loadFailed = false;
  long stopped = 0;
  byte[] exportData;
  String exportName;
  Runnable pending;
  AlertDialog progress;

  interface Work {
    void run() throws Exception;
  }

  int dp(float n) {
    return (int) (getResources().getDisplayMetrics().density * n + .5f);
  }

  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
    if (state != null) {
      query = state.getString("query", "");
      tab = state.getInt("tab", 0);
    }
    locked();
  }

  @Override
  public void onSaveInstanceState(Bundle b) {
    super.onSaveInstanceState(b);
    b.putString("query", query);
    b.putInt("tab", tab);
  }

  @Override
  public void onResume() {
    super.onResume();
    resumed = true;
    if (!unlocked || (stopped > 0 && SystemClock.elapsedRealtime() - stopped >= 60000)) {
      unlocked = false;
      locked();
      if (!authDismissed) authenticate();
      else button(root, "Unlock Inventory", this::authenticate, true);
    } else {
      if (model == null) {
        if (loadFailed) {
          startupRecovery();
          runPending();
        } else if (!busy) load();
      } else {
        home();
        runPending();
      }
    }
  }

  @Override
  public void onStop() {
    super.onStop();
    for (Dialog d : dialogs) if (d.isShowing()) d.dismiss();
    dialogs.clear();
    resumed = false;
    stopped = SystemClock.elapsedRealtime();
  }

  @Override
  public void onDestroy() {
    super.onDestroy();
    worker.shutdown();
    if (exportData != null) Arrays.fill(exportData, (byte) 0);
  }

  void authenticate() {
    if (authPending) return;
    authDismissed = false;
    KeyguardManager km = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
    if (!km.isDeviceSecure()) {
      locked();
      TextView t =
          label(
              "Set a screen lock on your phone to protect inventory and borrower records.",
              16,
              MUTED);
      root.addView(t);
      button(
          root,
          "Open screen-lock settings",
          () -> startActivity(new Intent(android.provider.Settings.ACTION_SECURITY_SETTINGS)),
          true);
      button(root, "Try again", this::authenticate, false);
      return;
    }
    Intent i =
        km.createConfirmDeviceCredentialIntent(
            "Unlock Inventory", "Confirm your phone PIN, pattern, or password");
    if (i != null) {
      authPending = true;
      startActivityForResult(i, AUTH);
    }
  }

  void locked() {
    for (Dialog d : dialogs) if (d.isShowing()) d.dismiss();
    dialogs.clear();
    root = column();
    root.setPadding(dp(24), dp(60), dp(24), dp(24));
    root.setBackgroundColor(BG);
    root.addView(label("Inventory", 30, NAVY));
    root.addView(label("Private · Offline · On your phone", 15, MUTED));
    setContentView(root);
    insets(root);
  }

  void runPending() {
    if (unlocked && resumed && pending != null) {
      Runnable r = pending;
      pending = null;
      r.run();
    }
  }

  void load() {
    execute(
        "Opening inventory",
        () -> {
          storage = new Storage(this);
          storage.load();
        },
        () -> {
          loadFailed = false;
          model = storage.snapshot();
          home();
          runPending();
        });
  }

  void execute(String title, Work w, Runnable done) {
    if (busy) {
      toast("Please wait for the current operation");
      return;
    }
    busy = true;
    progress = new SafeDialog(this).setMessage(title + "…").setCancelable(false).create();
    progress.show();
    worker.execute(
        () -> {
          Exception failure = null;
          try {
            w.run();
          } catch (Exception e) {
            failure = e;
          }
          Exception error = failure;
          runOnUiThread(
              () -> {
                busy = false;
                if (progress != null) {
                  progress.dismiss();
                  progress = null;
                }
                if (isDestroyed()) return;
                if (error != null) {
                  if (model == null) loadFailed = true;
                  if (unlocked && resumed) error(error);
                  else pending = () -> error(error);
                } else if (unlocked && resumed) done.run();
                else pending = done;
              });
        });
  }

  void error(Exception e) {
    String msg =
        e instanceof javax.crypto.AEADBadTagException
            ? "Wrong passphrase or damaged encrypted file. No inventory was changed."
            : e.getMessage();
    if (msg == null) msg = "Operation failed. Your existing data was kept.";
    new SafeDialog(this)
        .setTitle("Couldn’t complete")
        .setMessage(msg)
        .setPositiveButton(
            "OK",
            (d, w) -> {
              if (model == null) startupRecovery();
            })
        .show();
  }

  void startupRecovery() {
    locked();
    root.addView(
        label("Inventory could not be opened. Your stored files have been preserved.", 16, MUTED));
    button(root, "Retry opening", this::load, true);
    button(root, "Recover previous save", () -> recover(false), false);
    button(root, "Restore encrypted backup", () -> openDocument(READ_BACKUP), false);
  }

  final class SafeDialog extends AlertDialog.Builder {
    SafeDialog(Context c) {
      super(c);
    }

    @Override
    public AlertDialog show() {
      AlertDialog d = super.show();
      dialogs.add(d);
      return d;
    }
  }

  void toast(String s) {
    Toast.makeText(this, s, Toast.LENGTH_LONG).show();
  }

  LinearLayout column() {
    LinearLayout v = new LinearLayout(this);
    v.setOrientation(LinearLayout.VERTICAL);
    return v;
  }

  LinearLayout row() {
    LinearLayout v = new LinearLayout(this);
    v.setOrientation(LinearLayout.HORIZONTAL);
    v.setGravity(Gravity.CENTER_VERTICAL);
    return v;
  }

  TextView label(String s, int size, int color) {
    TextView v = new TextView(this);
    v.setText(s);
    v.setTextSize(size);
    v.setTextColor(color);
    v.setPadding(0, dp(5), 0, dp(5));
    return v;
  }

  GradientDrawable shape(int color) {
    GradientDrawable g = new GradientDrawable();
    g.setColor(color);
    g.setCornerRadius(dp(14));
    return g;
  }

  Button button(LinearLayout box, String title, Runnable action, boolean primary) {
    Button b = new Button(this);
    b.setText(title);
    b.setAllCaps(false);
    b.setTextSize(14);
    b.setTextColor(primary ? Color.WHITE : NAVY);
    b.setBackground(shape(primary ? NAVY : 0xffeaf0f7));
    b.setMinHeight(dp(48));
    LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
    p.setMargins(0, dp(5), 0, dp(5));
    box.addView(b, p);
    b.setOnClickListener(
        v -> {
          if (!busy) action.run();
        });
    return b;
  }

  void insets(View view) {
    view.setPadding(dp(16), 0, dp(16), 0);
    view.setOnApplyWindowInsetsListener(
        (v, i) -> {
          if (android.os.Build.VERSION.SDK_INT >= 30) {
            android.graphics.Insets in =
                i.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
            v.setPadding(dp(16) + in.left, in.top, dp(16) + in.right, in.bottom);
          } else {
            v.setPadding(
                dp(16), i.getSystemWindowInsetTop(), dp(16), i.getSystemWindowInsetBottom());
          }
          return i;
        });
    view.requestApplyInsets();
  }

  void home() {
    if (model == null || !unlocked || !resumed) return;
    if (itemScroll != null) scrollPosition = itemScroll.getScrollY();
    root = column();
    root.setBackgroundColor(BG);
    setContentView(root);
    insets(root);
    LinearLayout top = row();
    TextView title = label("Inventory", 27, NAVY);
    title.setTypeface(null, Typeface.BOLD);
    top.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
    Button more = new Button(this);
    more.setText(R.string.data);
    more.setBackground(shape(Color.WHITE));
    more.setMinHeight(dp(48));
    more.setAllCaps(false);
    more.setTextColor(NAVY);
    top.addView(more);
    more.setOnClickListener(v -> dataMenu());
    root.addView(top);
    int open = 0, overdue = 0;
    for (Model.Loan l : model.loans)
      if (l.quantity > l.returned) {
        open++;
        if (LocalDate.parse(l.due).isBefore(LocalDate.now())) overdue++;
      }
    root.addView(
        label(
            (model.items.stream().filter(i -> !i.archived).count())
                + " items   ·   "
                + open
                + " unreturned   ·   "
                + overdue
                + " overdue",
            13,
            MUTED));
    search = new EditText(this);
    search.setSingleLine();
    search.setTextSize(15);
    search.setHint(tab == 1 ? "Search item or borrower" : "Search name, ID or scan code");
    search.setText(query);
    search.setContentDescription("Search inventory");
    root.addView(search);
    search.addTextChangedListener(
        new TextWatcher() {
          public void beforeTextChanged(CharSequence s, int a, int c, int f) {}

          public void onTextChanged(CharSequence s, int a, int b, int c) {
            query = s.toString();
            visibleLimit = 200;
            scrollPosition = 0;
            renderList();
          }

          public void afterTextChanged(Editable e) {}
        });
    LinearLayout tools = row();
    Button add = new Button(this);
    add.setText(tab == 1 ? "All unreturned" : showArchived ? "Archived items" : "+ Register item");
    add.setAllCaps(false);
    add.setTextColor(tab == 0 && !showArchived ? Color.WHITE : NAVY);
    add.setBackground(shape(tab == 0 && !showArchived ? NAVY : 0xffeaf0f7));
    tools.addView(add, new LinearLayout.LayoutParams(0, dp(48), 1));
    add.setOnClickListener(
        v -> {
          if (tab == 0 && !showArchived) edit(null, "");
          else {
            query = "";
            search.setText("");
          }
        });
    root.addView(tools);
    ScrollView scroll = new ScrollView(this);
    itemScroll = scroll;
    scroll.setFillViewport(true);
    list = column();
    scroll.addView(list);
    root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
    LinearLayout nav = row();
    for (String name : new String[] {"Items", "Scan", "Unreturned"}) {
      Button b = new Button(this);
      b.setAllCaps(false);
      b.setText(name);
      boolean scanAction = name.equals("Scan");
      boolean selected = name.equals(tab == 0 ? "Items" : "Unreturned");
      b.setTextColor(scanAction ? Color.WHITE : NAVY);
      b.setBackground(shape(scanAction ? NAVY : selected ? 0xffeaf0f7 : Color.WHITE));
      b.setTextSize(14);
      LinearLayout.LayoutParams navParams = new LinearLayout.LayoutParams(0, dp(52), 1);
      navParams.setMargins(dp(2), dp(6), dp(2), dp(6));
      nav.addView(b, navParams);
      b.setOnClickListener(
          v -> {
            if (name.equals("Scan")) scan();
            else {
              tab = name.equals("Items") ? 0 : 1;
              showArchived = false;
              query = "";
              visibleLimit = 200;
              scrollPosition = 0;
              itemScroll = null;
              home();
            }
          });
    }
    root.addView(nav);
    renderList();
    scroll.post(() -> scroll.scrollTo(0, scrollPosition));
  }

  void renderList() {
    if (list == null || model == null) return;
    list.removeAllViews();
    String q = query.toLowerCase(Locale.ROOT).trim();
    int count = 0;
    if (tab == 0) {
      for (Model.Item i : model.items) {
        if (i.archived != showArchived
            || !(i.name + " " + i.id + " " + i.code + " " + i.location)
                .toLowerCase(Locale.ROOT)
                .contains(q)) continue;
        int out = model.outstanding(i.id), avail = model.available(i.id);
        LinearLayout card = card();
        card.addView(label(i.name, 18, INK));
        card.addView(label(i.id + " · " + i.category, 13, MUTED));
        String stat =
            !i.status.equals("Available") ? i.status : out > 0 ? out + " issued" : "Available";
        card.addView(
            label(
                stat
                    + "   ·   "
                    + avail
                    + " available"
                    + (i.category.equals("Material") && avail <= i.minimum
                        ? "   ·   Low stock"
                        : ""),
                14,
                NAVY));
        if (!i.location.isEmpty()) card.addView(label(i.location, 13, MUTED));
        card.setContentDescription(i.name + ", " + stat + ", " + avail + " available");
        card.setOnClickListener(v -> details(i.id));
        count++;
        if (count >= visibleLimit) break;
      }
    } else {
      ArrayList<Model.Loan> loans = new ArrayList<>(model.loans);
      loans.sort(Comparator.comparing(l -> l.due));
      for (Model.Loan l : loans) {
        if (l.quantity == l.returned) continue;
        Model.Item i = model.item(l.itemId);
        if (!(i.name + " " + i.id + " " + l.borrower).toLowerCase(Locale.ROOT).contains(q))
          continue;
        LinearLayout c = card();
        c.addView(label(i.name, 18, INK));
        c.addView(label(l.borrower + " · " + (l.quantity - l.returned) + " to return", 15, NAVY));
        boolean late = LocalDate.parse(l.due).isBefore(LocalDate.now());
        c.addView(label((late ? "Overdue · " : "Due · ") + l.due, 13, late ? 0xffa63e29 : MUTED));
        c.setOnClickListener(v -> returnForm(l.id));
        count++;
        if (count >= visibleLimit) break;
      }
    }
    if (count >= visibleLimit)
      button(
          list,
          "Show 200 more",
          () -> {
            visibleLimit += 200;
            int y = itemScroll.getScrollY();
            renderList();
            itemScroll.post(() -> itemScroll.scrollTo(0, y));
          },
          false);
    if (count == 0) {
      list.addView(
          label(
              q.isEmpty()
                  ? (tab == 1 ? "Everything returned" : "Your inventory starts here")
                  : "No matching records",
              21,
              INK));
      list.addView(
          label(
              tab == 1
                  ? "Issued items stay here until fully returned."
                  : "Scan a label or tap Register item. You can also type the ID.",
              15,
              MUTED));
    }
  }

  LinearLayout card() {
    LinearLayout c = column();
    c.setPadding(dp(16), dp(10), dp(16), dp(10));
    c.setBackground(shape(Color.WHITE));
    LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
    p.setMargins(0, dp(4), 0, dp(6));
    list.addView(c, p);
    return c;
  }

  LinearLayout form() {
    LinearLayout b = column();
    b.setPadding(dp(20), dp(4), dp(20), dp(10));
    return b;
  }

  EditText field(LinearLayout b, String caption, String value, boolean number) {
    b.addView(label(caption, 13, MUTED));
    EditText e = new EditText(this);
    e.setTextSize(16);
    e.setText(value);
    e.setInputType(
        number
            ? android.text.InputType.TYPE_CLASS_NUMBER
            : android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
    e.setSingleLine(!caption.equals("Notes"));
    e.setContentDescription(caption);
    b.addView(e);
    return e;
  }

  Spinner select(LinearLayout b, String caption, String[] values, String selected) {
    b.addView(label(caption, 13, MUTED));
    Spinner s = new Spinner(this);
    s.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, values));
    for (int n = 0; n < values.length; n++) if (values[n].equals(selected)) s.setSelection(n);
    b.addView(s, new LinearLayout.LayoutParams(-1, dp(48)));
    return s;
  }

  AlertDialog dialog(String title, LinearLayout form) {
    ScrollView s = new ScrollView(this);
    s.addView(form);
    AlertDialog a =
        new SafeDialog(this).setTitle(title).setView(s).setNegativeButton("Cancel", null).create();
    a.show();
    dialogs.add(a);
    return a;
  }

  String val(EditText e) {
    return e.getText().toString().trim();
  }

  int number(EditText e) {
    try {
      String s = val(e);
      Model.check(s.matches("[0-9]{1,6}"), "Enter a whole number from 0–999999");
      return Integer.parseInt(s);
    } catch (NumberFormatException ex) {
      throw new IllegalArgumentException("Enter a whole number");
    }
  }

  void mutate(String title, Storage.Change action, AlertDialog d) {
    execute(
        title,
        () -> storage.change(action),
        () -> {
          if (d != null) d.dismiss();
          model = storage.snapshot();
          home();
          toast("Saved");
        });
  }

  void edit(String id, String scanned) {
    Model.Item original = id == null ? new Model.Item() : model.item(id);
    LinearLayout f = form();
    boolean create = id == null;
    String generated =
        "DL-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase(Locale.ROOT);
    EditText itemId = field(f, "Item ID", create ? generated : original.id, false);
    itemId.setEnabled(create);
    EditText code =
        field(
            f,
            "Barcode / QR value",
            create ? (scanned.isEmpty() ? generated : scanned) : original.code,
            false);
    EditText name = field(f, "Item name", create ? "" : original.name, false);
    Spinner category =
        select(
            f,
            "Category",
            new String[] {"Tool", "Equipment", "Material"},
            create ? "Tool" : original.category);
    category.setEnabled(create);
    EditText qty =
        field(f, "Total owned quantity (one per tool/equipment)", "" + original.total, true);
    EditText minimum = field(f, "Low stock at", "" + original.minimum, true);
    Spinner status =
        select(
            f,
            "Status",
            new String[] {"Available", "Maintenance", "Damaged", "Lost", "Retired"},
            original.status);
    EditText location = field(f, "Location", original.location, false),
        notes = field(f, "Notes", original.notes, false);
    AlertDialog d = dialog(create ? "Register item" : "Edit item", f);
    button(
        f,
        "Save item",
        () -> {
          try {
            Model.Item n = new Model.Item();
            n.id = val(itemId);
            n.code = val(code);
            n.name = val(name);
            n.category = category.getSelectedItem().toString();
            n.total = number(qty);
            n.minimum = number(minimum);
            n.status = status.getSelectedItem().toString();
            n.location = val(location);
            n.notes = val(notes);
            n.archived = original.archived;
            mutate("Saving item", m -> m.save(n, create), d);
          } catch (Exception ex) {
            error(ex);
          }
        },
        true);
    if (create && scanned.isEmpty())
      button(
          f,
          "Use camera to read label",
          () -> {
            d.dismiss();
            scan();
          },
          false);
  }

  void details(String id) {
    Model.Item i = model.item(id);
    LinearLayout f = form();
    f.addView(label(i.id + " · " + i.category, 14, MUTED));
    f.addView(label("Scan code: " + i.code, 14, MUTED));
    f.addView(
        label(model.available(id) + " available · " + model.outstanding(id) + " issued", 18, NAVY));
    f.addView(label(i.status + (i.location.isEmpty() ? "" : " · " + i.location), 15, INK));
    if (!i.notes.isEmpty()) f.addView(label(i.notes, 15, MUTED));
    AlertDialog d = dialog(i.name, f);
    if (!i.archived) {
      button(
          f,
          "Issue",
          () -> {
            d.dismiss();
            issueForm(id);
          },
          true);
      button(
          f,
          "Edit",
          () -> {
            d.dismiss();
            edit(id, "");
          },
          false);
    }
    for (Model.Loan l : model.loans)
      if (l.itemId.equals(id) && l.returned < l.quantity)
        button(
            f,
            "Return · " + l.borrower + " (" + (l.quantity - l.returned) + ")",
            () -> {
              d.dismiss();
              returnForm(l.id);
            },
            false);
    button(
        f,
        "History",
        () -> {
          d.dismiss();
          history(id);
        },
        false);
    button(
        f,
        i.archived ? "Restore item" : "Delete item",
        () ->
            new SafeDialog(this)
                .setTitle(i.archived ? "Restore this item?" : "Delete this item?")
                .setMessage(
                    "The record and its issue/return history will be retained in Archived items."
                        + " Items still issued must be returned first.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton(
                    i.archived ? "Restore" : "Delete",
                    (x, w) -> mutate("Updating item", m -> m.archive(id, !i.archived), d))
                .show(),
        false);
  }

  void issueForm(String id) {
    Model.Item i = model.item(id);
    LinearLayout f = form();
    f.addView(label(i.name + " · " + model.available(id) + " available", 18, NAVY));
    EditText borrower = field(f, "Borrower name / ID", "", false),
        qty = field(f, "Quantity", "1", true);
    CheckBox consumed = new CheckBox(this);
    consumed.setText(R.string.consumed);
    if (i.category.equals("Material")) f.addView(consumed);
    Button due = new Button(this);
    final String[] date = {LocalDate.now().plusDays(7).toString()};
    due.setText(getString(R.string.return_by, date[0]));
    due.setAllCaps(false);
    f.addView(due);
    due.setOnClickListener(
        v -> {
          LocalDate now = LocalDate.parse(date[0]);
          DatePickerDialog picker =
              new DatePickerDialog(
                  this,
                  (p, y, m, d) -> {
                    date[0] = LocalDate.of(y, m + 1, d).toString();
                    due.setText(getString(R.string.return_by, date[0]));
                  },
                  now.getYear(),
                  now.getMonthValue() - 1,
                  now.getDayOfMonth());
          picker.show();
          dialogs.add(picker);
        });
    consumed.setOnCheckedChangeListener((v, on) -> due.setEnabled(!on));
    EditText note = field(f, "Notes", "", false);
    AlertDialog d = dialog("Issue item", f);
    button(
        f,
        "Confirm issue",
        () -> {
          try {
            int n = number(qty);
            String b = val(borrower), nt = val(note), dt = date[0];
            boolean c = consumed.isChecked();
            mutate("Recording issue", m -> m.issue(id, n, b, dt, nt, c), d);
          } catch (Exception ex) {
            error(ex);
          }
        },
        true);
  }

  void returnForm(String loanId) {
    Model.Loan l = model.loan(loanId);
    LinearLayout f = form();
    f.addView(label(model.item(l.itemId).name, 19, INK));
    f.addView(label(l.borrower + " · Due " + l.due, 15, MUTED));
    f.addView(label((l.quantity - l.returned) + " outstanding", 18, NAVY));
    EditText qty = field(f, "Quantity returned", "" + (l.quantity - l.returned), true);
    Spinner condition =
        select(
            f,
            "Returned condition",
            new String[] {"Available", "Damaged", "Maintenance"},
            "Available");
    EditText note = field(f, "Notes", "", false);
    f.addView(
        label("A damaged return places this entire item/lot on hold until reviewed.", 13, MUTED));
    AlertDialog d = dialog("Record return", f);
    button(
        f,
        "Confirm return",
        () -> {
          try {
            int n = number(qty);
            String c = condition.getSelectedItem().toString(), nt = val(note);
            mutate("Recording return", m -> m.receive(loanId, n, c, nt), d);
          } catch (Exception ex) {
            error(ex);
          }
        },
        true);
  }

  void history(String id) {
    LinearLayout f = form();
    int n = 0;
    for (int x = model.events.size() - 1; x >= 0; x--) {
      Model.Event e = model.events.get(x);
      if (e.itemId.equals(id)) {
        f.addView(label(e.action + " · " + e.time, 14, NAVY));
        f.addView(label(e.detail, 13, MUTED));
        if (++n >= 100) break;
      }
    }
    f.addView(label("Latest 100 entries. Export history for the complete log.", 13, MUTED));
    dialog("Item history", f);
  }

  void scan() {
    if (busy) return;
    new IntentIntegrator(this)
        .setCaptureActivity(SecureCaptureActivity.class)
        .setDesiredBarcodeFormats(IntentIntegrator.ALL_CODE_TYPES)
        .setPrompt("Scan an item barcode or QR label")
        .setBeepEnabled(false)
        .setOrientationLocked(false)
        .initiateScan();
  }

  void scanned(String code) {
    try {
      String value = Model.code(code);
      Model.Item i = model.byCode(value);
      if (i != null) details(i.id);
      else
        new SafeDialog(this)
            .setTitle("New label")
            .setMessage(value + "\nRegister this label as an inventory item?")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Register", (d, w) -> edit(null, value))
            .show();
    } catch (Exception ex) {
      error(ex);
    }
  }

  void dataMenu() {
    String[] options = {
      "Export inventory CSV",
      "Export issues CSV",
      "Export audit history CSV",
      "Import new items CSV",
      "Create encrypted backup",
      "Restore encrypted backup",
      "Recover previous save",
      "Recover before last restore",
      showArchived ? "Show active items" : "Show archived items",
      "Lock Inventory",
      "About"
    };
    new SafeDialog(this)
        .setTitle("Data & security")
        .setItems(
            options,
            (d, n) -> {
              switch (n) {
                case 0 -> prepareCsv(0);
                case 1 -> prepareCsv(1);
                case 2 -> prepareCsv(2);
                case 3 -> openDocument(READ_CSV);
                case 4 -> password(true, null);
                case 5 -> openDocument(READ_BACKUP);
                case 6 -> recover(false);
                case 7 -> recover(true);
                case 8 -> {
                  showArchived = !showArchived;
                  tab = 0;
                  query = "";
                  home();
                }
                case 9 -> {
                  unlocked = false;
                  locked();
                  authenticate();
                }
                case 10 ->
                    new SafeDialog(this)
                        .setTitle("Inventory 0.2.0-rc.1")
                        .setMessage(
                            "Offline Android test candidate.\n\n"
                                + "Phone-camera barcode and QR scanning. No account or internet"
                                + " required. Device screen lock is required.\n\n"
                                + "Keep encrypted backups outside this phone. Uninstalling removes"
                                + " local data and its encryption key. CSV reports are unencrypted"
                                + " and do not restore issue history.\n\n"
                                + "Single phone only; no shared database or synchronization."
                                + " Powered by ZXing (Apache 2.0) and Gson (Apache 2.0).")
                        .setPositiveButton("OK", null)
                        .show();
              }
            })
        .show();
  }

  void prepareCsv(int type) {
    new SafeDialog(this)
        .setTitle("Export CSV?")
        .setMessage(
            "CSV files are unencrypted. Issues and history may include borrower details. Inventory"
                + " CSV contains total owned quantities, not loan history. Use encrypted backup for"
                + " complete recovery.")
        .setNegativeButton("Cancel", null)
        .setPositiveButton(
            "Continue",
            (d, w) -> {
              execute(
                  "Preparing export",
                  () -> {
                    Model m = storage.snapshot();
                    exportData =
                        (type == 0 ? Csv.inventory(m) : type == 1 ? Csv.issues(m) : Csv.history(m))
                            .getBytes(StandardCharsets.UTF_8);
                  },
                  () ->
                      saveDocument(
                          "Inventory-"
                              + (type == 0 ? "items" : type == 1 ? "issues" : "history")
                              + "-"
                              + LocalDate.now()
                              + ".csv",
                          "text/csv"));
            })
        .show();
  }

  void saveDocument(String name, String mime) {
    exportName = name;
    Intent i =
        new Intent(Intent.ACTION_CREATE_DOCUMENT)
            .addCategory(Intent.CATEGORY_OPENABLE)
            .setType(mime)
            .putExtra(Intent.EXTRA_TITLE, name);
    startActivityForResult(i, WRITE);
  }

  void openDocument(int request) {
    Intent i =
        new Intent(Intent.ACTION_OPEN_DOCUMENT)
            .addCategory(Intent.CATEGORY_OPENABLE)
            .setType("*/*");
    startActivityForResult(i, request);
  }

  void password(boolean create, byte[] data) {
    LinearLayout f = form();
    f.addView(
        label(
            create
                ? "Use at least 12 characters. Keep the passphrase somewhere safe; it cannot be"
                    + " recovered."
                : "Enter the passphrase used when this backup was created.",
            15,
            MUTED));
    EditText pass = field(f, "Backup passphrase", "", false);
    pass.setInputType(129);
    EditText repeat = create ? field(f, "Repeat passphrase", "", false) : null;
    if (repeat != null) repeat.setInputType(129);
    AlertDialog d = dialog(create ? "Encrypted backup" : "Unlock backup", f);
    button(
        f,
        create ? "Create backup" : "Preview restore",
        () -> {
          String s = pass.getText().toString();
          if (create && (!s.equals(repeat.getText().toString()) || s.length() < 12)) {
            toast("Passphrases must match and contain at least 12 characters");
            return;
          }
          char[] secret = s.toCharArray();
          pass.setText("");
          if (repeat != null) repeat.setText("");
          d.dismiss();
          final Model[] incoming = {null};
          execute(
              create ? "Encrypting backup" : "Validating backup",
              () -> {
                try {
                  if (create)
                    exportData =
                        Crypto.backup(
                            Model.JSON.toJson(storage.snapshot()).getBytes(StandardCharsets.UTF_8),
                            secret);
                  else incoming[0] = Storage.decode(Crypto.restore(data, secret));
                } finally {
                  Arrays.fill(secret, '\0');
                  if (data != null) Arrays.fill(data, (byte) 0);
                }
              },
              () -> {
                if (create)
                  saveDocument(
                      "Inventory-backup-" + LocalDate.now() + ".dlinv", "application/octet-stream");
                else previewRestore(incoming[0], false);
              });
        },
        true);
  }

  void previewRestore(Model next, boolean local) {
    long outstanding = next.loans.stream().mapToLong(l -> l.quantity - l.returned).sum();
    new SafeDialog(this)
        .setTitle("Replace this phone’s inventory?")
        .setMessage(
            "Backup: "
                + next.items.size()
                + " items, "
                + outstanding
                + " outstanding units, "
                + next.events.size()
                + " history entries.\n\nThis replaces all current records. "
                + (local
                    ? "Local recovery will be applied."
                    : "A local copy of your current data is kept under Recover before last"
                        + " restore."))
        .setNegativeButton("Cancel", null)
        .setPositiveButton(
            "Replace inventory",
            (d, w) ->
                execute(
                    "Restoring inventory",
                    () -> {
                      if (local) storage.recover(next);
                      else {
                        Model.check(
                            storage != null,
                            "Local encryption could not be initialized. Preserve your backup and"
                                + " reinstall on a device with working Android Keystore.");
                        storage.restore(next);
                      }
                    },
                    () -> {
                      model = storage.snapshot();
                      showArchived = false;
                      query = "";
                      visibleLimit = 200;
                      scrollPosition = 0;
                      itemScroll = null;
                      home();
                      toast("Inventory restored");
                    }))
        .show();
  }

  void recover(boolean before) {
    if (storage == null) {
      toast("Open inventory first, then try recovery");
      return;
    }
    final Model[] next = {null};
    execute(
        "Checking recovery copy",
        () -> next[0] = storage.recovery(before),
        () -> previewRestore(next[0], true));
  }

  @Override
  protected void onActivityResult(int request, int result, Intent data) {
    super.onActivityResult(request, result, data);
    if (request == AUTH) {
      authPending = false;
      if (result == RESULT_OK) {
        unlocked = true;
        stopped = SystemClock.elapsedRealtime();
      } else {
        unlocked = false;
        authDismissed = true;
        locked();
        button(root, "Unlock Inventory", this::authenticate, true);
      }
      return;
    }
    IntentResult scan = IntentIntegrator.parseActivityResult(request, result, data);
    if (scan != null) {
      if (scan.getContents() != null) pending = () -> scanned(scan.getContents());
      return;
    }
    if (result != RESULT_OK || data == null || data.getData() == null) {
      if (request == WRITE && exportData != null) {
        Arrays.fill(exportData, (byte) 0);
        exportData = null;
      }
      return;
    }
    android.net.Uri uri = data.getData();
    pending =
        () -> {
          if (request == WRITE) {
            execute(
                "Saving export",
                () -> {
                  Model.check(exportData != null, "Export expired; create it again");
                  try (java.io.OutputStream out =
                      getContentResolver().openOutputStream(uri, "wt")) {
                    Model.check(out != null, "Could not create file");
                    out.write(exportData);
                    out.flush();
                  } finally {
                    if (exportData != null) Arrays.fill(exportData, (byte) 0);
                    exportData = null;
                  }
                },
                () -> toast("Export saved"));
          } else if (request == READ_CSV) {
            final Model[] preview = {null};
            final int[] count = {0};
            execute(
                "Validating CSV",
                () -> {
                  String csv =
                      new String(
                          Storage.bytes(getContentResolver().openInputStream(uri), 8 * 1024 * 1024),
                          StandardCharsets.UTF_8);
                  preview[0] = storage.snapshot();
                  count[0] = Csv.addItems(preview[0], csv);
                },
                () ->
                    new SafeDialog(this)
                        .setTitle("Import " + count[0] + " new items?")
                        .setMessage(
                            "Existing records and loans will be kept. Duplicate IDs/codes or any"
                                + " invalid row reject the complete import.")
                        .setNegativeButton("Cancel", null)
                        .setPositiveButton(
                            "Import",
                            (d, w) ->
                                execute(
                                    "Importing inventory",
                                    () ->
                                        storage.change(
                                            m -> {
                                              Model.check(
                                                  Model.JSON
                                                      .toJson(m)
                                                      .equals(Model.JSON.toJson(model)),
                                                  "Inventory changed; preview the import again");
                                              m.items = preview[0].items;
                                              m.events = preview[0].events;
                                            }),
                                    () -> {
                                      model = storage.snapshot();
                                      home();
                                      toast("Items imported");
                                    }))
                        .show());
          } else if (request == READ_BACKUP) {
            final byte[][] file = {null};
            execute(
                "Reading backup",
                () ->
                    file[0] =
                        Storage.bytes(getContentResolver().openInputStream(uri), 24 * 1024 * 1024),
                () -> password(false, file[0]));
          }
        };
  }
}
