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
  int tab = 0, visibleLimit = 200, filter = 0;
  final Map<LinearLayout, AlertDialog> formDialogs = new IdentityHashMap<>();
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
      filter = state.getInt("filter", 0);
      showArchived = state.getBoolean("archived", false);
    }
    locked();
  }

  @Override
  public void onSaveInstanceState(Bundle b) {
    super.onSaveInstanceState(b);
    b.putString("query", query);
    b.putInt("tab", tab);
    b.putInt("filter", filter);
    b.putBoolean("archived", showArchived);
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
  public void onConfigurationChanged(android.content.res.Configuration config) {
    super.onConfigurationChanged(config);
    if (model != null && unlocked && resumed) home();
  }

  @Override
  public void onStop() {
    super.onStop();
    for (Dialog d : new ArrayList<>(dialogs)) if (d.isShowing()) d.dismiss();
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
    for (Dialog d : new ArrayList<>(dialogs)) if (d.isShowing()) d.dismiss();
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
      d.setOnDismissListener(x -> dialogs.remove(d));
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
    AlertDialog formDialog = formDialogs.get(box);
    if (primary && formDialog != null) {
      Button actionButton = formDialog.getButton(AlertDialog.BUTTON_POSITIVE);
      actionButton.setText(title);
      actionButton.setAllCaps(false);
      actionButton.setVisibility(View.VISIBLE);
      actionButton.setMinHeight(dp(48));
      actionButton.setOnClickListener(
          v -> {
            if (!busy) action.run();
          });
      return actionButton;
    }
    Button b = new Button(this);
    b.setText(title);
    b.setAllCaps(false);
    b.setTextSize(14);
    b.setTextColor(primary ? Color.WHITE : NAVY);
    b.setBackground(shape(primary ? NAVY : 0xffeaf0f7));
    b.setMinHeight(dp(48));
    b.setMinimumHeight(dp(48));
    b.setPadding(dp(12), dp(8), dp(12), dp(8));
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
    boolean compact =
        getResources().getConfiguration().orientation
            == android.content.res.Configuration.ORIENTATION_LANDSCAPE;
    LinearLayout top = row();
    TextView title =
        label(tab == 1 ? "Unreturned" : showArchived ? "Archived items" : "Inventory", 25, NAVY);
    title.setTypeface(null, Typeface.BOLD);
    if (Build.VERSION.SDK_INT >= 28) title.setAccessibilityHeading(true);
    top.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
    if (compact) {
      Button scanAction = button(top, "Scan label", this::scan, true);
      LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(dp(116), -2);
      sp.setMargins(dp(8), dp(4), dp(8), dp(4));
      scanAction.setLayoutParams(sp);
      if (tab == 0 && !showArchived) {
        Button registerAction = button(top, "+ Register item", () -> edit(null, ""), true);
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(dp(144), -2);
        rp.setMargins(0, dp(4), dp(8), dp(4));
        registerAction.setLayoutParams(rp);
      }
    }
    Button data = button(top, getString(R.string.data), this::dataMenu, false);
    data.setLayoutParams(new LinearLayout.LayoutParams(dp(72), -2));
    root.addView(top);
    int open = 0, overdue = 0, low = 0;
    for (Model.Loan l : model.loans)
      if (l.quantity > l.returned) {
        open++;
        if (LocalDate.parse(l.due).isBefore(LocalDate.now())) overdue++;
      }
    Map<String, Integer> balances = outstandingByItem();
    for (Model.Item i : model.items)
      if (!i.archived
          && i.category.equals("Material")
          && i.total - balances.getOrDefault(i.id, 0) <= i.minimum) low++;
    if (!compact)
      root.addView(
          label(
              tab == 1
                  ? open + " open issues · " + overdue + " overdue"
                  : model.items.stream().filter(i -> i.archived == showArchived).count()
                      + (showArchived ? " archived items" : " items · " + low + " low stock"),
              13,
              MUTED));
    search = new EditText(this);
    search.setSingleLine();
    search.setTextSize(15);
    search.setMinHeight(dp(48));
    search.setPadding(dp(14), dp(8), dp(14), dp(8));
    search.setBackground(shape(Color.WHITE));
    search.setHint(tab == 1 ? "Search item, ID or borrower" : "Search name, ID, code or location");
    search.setText(query);
    search.setContentDescription(tab == 1 ? "Search unreturned items" : "Search inventory");
    LinearLayout searchRow = row();
    if (compact) {
      searchRow.addView(search, new LinearLayout.LayoutParams(0, -2, 1));
      root.addView(searchRow);
    } else root.addView(search);
    search.addTextChangedListener(
        new TextWatcher() {
          public void beforeTextChanged(CharSequence s, int a, int c, int f) {}

          public void onTextChanged(CharSequence s, int a, int b, int c) {
            query = s.toString();
            visibleLimit = 200;
            scrollPosition = 0;
            renderList();
            itemScroll.scrollTo(0, 0);
          }

          public void afterTextChanged(Editable e) {}
        });
    LinearLayout tools = row();
    Button filterButton =
        button(compact ? searchRow : tools, filterName() + " ▾", this::chooseFilter, false);
    LinearLayout.LayoutParams fp =
        compact
            ? new LinearLayout.LayoutParams(dp(176), -2)
            : new LinearLayout.LayoutParams(0, -2, 1);
    fp.setMargins(compact ? dp(8) : 0, dp(8), compact ? 0 : dp(8), dp(8));
    filterButton.setLayoutParams(fp);
    if (!compact) {
      Button scanButton = button(tools, "Scan label", this::scan, true);
      scanButton.setLayoutParams(new LinearLayout.LayoutParams(0, -2, 1));
      root.addView(tools);
    }
    ScrollView scroll = new ScrollView(this);
    itemScroll = scroll;
    scroll.setFillViewport(true);
    list = column();
    scroll.addView(list);
    root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
    if (!compact && tab == 0 && !showArchived)
      button(root, "+ Register item", () -> edit(null, ""), true);
    LinearLayout nav = row();
    for (int n = 0; n < 2; n++) {
      final int destination = n;
      Button navButton =
          button(nav, n == 0 ? "Items" : "Unreturned", () -> switchTab(destination), false);
      navButton.setSelected(tab == n);
      navButton.setTypeface(null, tab == n ? Typeface.BOLD : Typeface.NORMAL);
      navButton.setBackground(shape(tab == n ? 0xffdce7f5 : Color.WHITE));
      navButton.setContentDescription(
          (n == 0 ? "Items" : "Unreturned") + (tab == n ? ", selected" : ""));
      LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(0, -2, 1);
      np.setMargins(dp(2), dp(4), dp(2), dp(4));
      navButton.setLayoutParams(np);
    }
    root.addView(nav);
    renderList();
    scroll.post(() -> scroll.scrollTo(0, scrollPosition));
  }

  void switchTab(int destination) {
    if (tab == destination && !showArchived) return;
    tab = destination;
    showArchived = false;
    query = "";
    filter = 0;
    resetList();
    home();
  }

  void resetList() {
    visibleLimit = 200;
    scrollPosition = 0;
    itemScroll = null;
  }

  String[] filterNames() {
    return tab == 1
        ? new String[] {"All unreturned", "Overdue", "Due today"}
        : new String[] {"All items", "Available", "Issued", "Low stock", "On hold"};
  }

  String filterName() {
    String[] names = filterNames();
    return names[filter >= 0 && filter < names.length ? filter : 0];
  }

  void chooseFilter() {
    new SafeDialog(this)
        .setTitle("Filter " + (tab == 1 ? "unreturned" : "items"))
        .setSingleChoiceItems(
            filterNames(),
            filter,
            (d, choice) -> {
              filter = choice;
              resetList();
              d.dismiss();
              home();
            })
        .setNegativeButton("Cancel", null)
        .show();
  }

  Map<String, Integer> outstandingByItem() {
    Map<String, Integer> balances = new HashMap<>();
    for (Model.Loan loan : model.loans)
      balances.merge(loan.itemId, loan.quantity - loan.returned, Integer::sum);
    return balances;
  }

  void renderList() {
    if (list == null || model == null) return;
    list.removeAllViews();
    String q = query.toLowerCase(Locale.ROOT).trim();
    int count = 0;
    if (tab == 0) {
      Map<String, Integer> balances = outstandingByItem();
      for (Model.Item i : model.items) {
        if (i.archived != showArchived
            || !(i.name + " " + i.id + " " + i.code + " " + i.location)
                .toLowerCase(Locale.ROOT)
                .contains(q)) continue;
        int out = balances.getOrDefault(i.id, 0), avail = i.total - out;
        if ((filter == 1 && (avail <= 0 || !i.status.equals("Available")))
            || (filter == 2 && out == 0)
            || (filter == 3 && (!i.category.equals("Material") || avail > i.minimum))
            || (filter == 4 && i.status.equals("Available"))) continue;
        LinearLayout card = card();
        TextView itemTitle = label(i.name, 18, INK);
        itemTitle.setTypeface(null, Typeface.BOLD);
        card.addView(itemTitle);
        card.addView(label(i.id + " · " + i.category, 13, MUTED));
        String stat =
            !i.status.equals("Available") ? i.status : out > 0 ? out + " issued" : "Available";
        card.addView(
            label(
                stat
                    + "   ·   "
                    + avail
                    + (i.status.equals("Available") && !i.archived ? " available" : " on hand")
                    + (i.category.equals("Material") && avail <= i.minimum
                        ? "   ·   Low stock"
                        : ""),
                14,
                !i.status.equals("Available")
                        || (i.category.equals("Material") && avail <= i.minimum)
                    ? 0xff914323
                    : NAVY));
        if (!i.location.isEmpty()) card.addView(label(i.location, 13, MUTED));
        card.setContentDescription(
            i.name
                + ", "
                + stat
                + ", "
                + avail
                + (i.status.equals("Available") && !i.archived ? " available" : " on hand")
                + (i.category.equals("Material") && avail <= i.minimum ? ", low stock" : "")
                + ", "
                + i.id
                + ", "
                + i.category
                + (i.location.isEmpty() ? "" : ", " + i.location));
        card.setOnClickListener(v -> details(i.id));
        count++;
        if (count >= visibleLimit) break;
      }
    } else {
      Map<String, Model.Item> itemsById = new HashMap<>();
      for (Model.Item item : model.items) itemsById.put(item.id, item);
      ArrayList<Model.Loan> loans = new ArrayList<>(model.loans);
      loans.sort(Comparator.comparing(l -> l.due));
      for (Model.Loan l : loans) {
        if (l.quantity == l.returned) continue;
        LocalDate dueDate = LocalDate.parse(l.due);
        if ((filter == 1 && !dueDate.isBefore(LocalDate.now()))
            || (filter == 2 && !dueDate.equals(LocalDate.now()))) continue;
        Model.Item i = itemsById.get(l.itemId);
        if (!(i.name + " " + i.id + " " + i.code + " " + l.borrower)
            .toLowerCase(Locale.ROOT)
            .contains(q)) continue;
        LinearLayout c = card();
        c.addView(label(i.name, 18, INK));
        c.addView(label(i.id + " · " + i.category, 13, MUTED));
        c.addView(label(l.borrower + " · " + (l.quantity - l.returned) + " to return", 15, NAVY));
        boolean late = LocalDate.parse(l.due).isBefore(LocalDate.now());
        c.addView(label((late ? "Overdue · " : "Due · ") + l.due, 13, late ? 0xffa63e29 : MUTED));
        c.addView(label("Record return →", 14, NAVY));
        c.setContentDescription(
            i.name
                + ", "
                + l.borrower
                + ", "
                + (l.quantity - l.returned)
                + " to return, "
                + (late ? "overdue " : "due ")
                + l.due
                + ". Record return");
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
              !q.isEmpty() || filter != 0
                  ? "No matching records"
                  : showArchived
                      ? "No archived items"
                      : tab == 1 ? "Everything returned" : "Your inventory starts here",
              21,
              INK));
      list.addView(
          label(
              !q.isEmpty() || filter != 0
                  ? "Try another search or choose a different filter."
                  : showArchived
                      ? "Archived items keep their IDs and history."
                      : tab == 1
                          ? "Issued items stay here until fully returned."
                          : "Scan a label or tap Register item. You can also type the ID.",
              15,
              MUTED));
    }
  }

  LinearLayout card() {
    LinearLayout c = column();
    c.setPadding(dp(16), dp(10), dp(16), dp(10));
    c.setBackground(
        new android.graphics.drawable.RippleDrawable(
            android.content.res.ColorStateList.valueOf(0xffdce7f5),
            shape(Color.WHITE),
            shape(Color.WHITE)));
    c.setFocusable(true);
    c.setClickable(true);
    c.setMinimumHeight(dp(64));
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
    TextView captionView = label(caption, 13, MUTED);
    b.addView(captionView);
    EditText e = new EditText(this);
    e.setId(View.generateViewId());
    captionView.setLabelFor(e.getId());
    e.setMinHeight(dp(48));
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
    s.setContentDescription(caption);
    s.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, values));
    for (int n = 0; n < values.length; n++) if (values[n].equals(selected)) s.setSelection(n);
    b.addView(s, new LinearLayout.LayoutParams(-1, dp(48)));
    return s;
  }

  AlertDialog dialog(String title, LinearLayout form) {
    ScrollView s = new ScrollView(this);
    s.addView(form);
    AlertDialog a =
        new SafeDialog(this)
            .setTitle(title)
            .setView(s)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Save", null)
            .create();
    a.show();
    dialogs.add(a);
    formDialogs.put(form, a);
    a.getButton(AlertDialog.BUTTON_POSITIVE).setVisibility(View.GONE);
    a.getButton(AlertDialog.BUTTON_NEGATIVE).setMinHeight(dp(48));
    a.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
    a.setOnDismissListener(
        x -> {
          dialogs.remove(a);
          formDialogs.remove(form);
        });
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
    TextView qtyCaption = (TextView) f.getChildAt(f.indexOfChild(qty) - 1);
    TextView minimumCaption = (TextView) f.getChildAt(f.indexOfChild(minimum) - 1);
    category.setOnItemSelectedListener(
        new AdapterView.OnItemSelectedListener() {
          public void onNothingSelected(AdapterView<?> parent) {}

          public void onItemSelected(AdapterView<?> parent, View view, int position, long rowId) {
            boolean material = category.getSelectedItem().toString().equals("Material");
            qty.setEnabled(material);
            qtyCaption.setText(
                material ? "Total owned quantity" : "One individually labelled asset");
            minimum.setVisibility(material ? View.VISIBLE : View.GONE);
            minimumCaption.setVisibility(material ? View.VISIBLE : View.GONE);
            if (!material) {
              qty.setText("1");
              minimum.setText("0");
            }
          }
        });
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
        label(
            model.available(id)
                + (i.status.equals("Available") && !i.archived ? " available · " : " on hand · ")
                + model.outstanding(id)
                + " issued",
            18,
            NAVY));
    f.addView(label(i.status + (i.location.isEmpty() ? "" : " · " + i.location), 15, INK));
    if (!i.notes.isEmpty()) f.addView(label(i.notes, 15, MUTED));
    AlertDialog d = dialog(i.name, f);
    d.getButton(AlertDialog.BUTTON_NEGATIVE).setText(android.R.string.ok);
    if (!i.archived) {
      boolean canIssue = i.status.equals("Available") && model.available(id) > 0;
      if (!canIssue)
        f.addView(
            label(
                !i.status.equals("Available")
                    ? "Issuing paused: " + i.status + ". Review status in Edit."
                    : "All units are issued. Record a return before issuing again.",
                14,
                MUTED));
      Button issueAction =
          button(
              f,
              "Issue",
              () -> {
                d.dismiss();
                issueForm(id);
              },
              true);
      issueAction.setEnabled(canIssue);
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
        i.archived ? "Restore item" : "Archive item",
        () ->
            new SafeDialog(this)
                .setTitle(i.archived ? "Restore this item?" : "Archive this item?")
                .setMessage(
                    i.archived
                        ? "This item will reappear in active inventory with its existing ID and"
                            + " history."
                        : "This hides the item from active inventory and keeps its ID and history."
                            + " Items still issued must be returned first.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton(
                    i.archived ? "Restore" : "Archive",
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
          picker
              .getDatePicker()
              .setMinDate(
                  LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant().toEpochMilli());
          picker.show();
          dialogs.add(picker);
        });
    TextView consumptionHelp =
        label("Borrowed stock must be returned by the selected date.", 13, MUTED);
    f.addView(consumptionHelp);
    consumed.setMinHeight(dp(48));
    consumed.setOnCheckedChangeListener(
        (v, on) -> {
          due.setVisibility(on ? View.GONE : View.VISIBLE);
          consumptionHelp.setText(
              on
                  ? "Consumed stock reduces total owned quantity. No return is expected."
                  : "Borrowed stock must be returned by the selected date.");
        });
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
    dialog("Item history", f).getButton(AlertDialog.BUTTON_NEGATIVE).setText(android.R.string.ok);
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
      "Export CSV reports",
      "Import new items CSV",
      "Backup & recovery",
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
                case 0 ->
                    new SafeDialog(this)
                        .setTitle("Export CSV report")
                        .setItems(
                            new String[] {"Inventory", "Issues & returns", "Audit history"},
                            (x, choice) -> prepareCsv(choice))
                        .setNegativeButton("Cancel", null)
                        .show();
                case 1 -> openDocument(READ_CSV);
                case 2 -> backupMenu();
                case 3 -> {
                  showArchived = !showArchived;
                  tab = 0;
                  query = "";
                  filter = 0;
                  resetList();
                  home();
                }
                case 4 -> {
                  unlocked = false;
                  locked();
                  authenticate();
                }
                case 5 ->
                    new SafeDialog(this)
                        .setTitle("Inventory " + BuildConfig.VERSION_NAME)
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

  void backupMenu() {
    new SafeDialog(this)
        .setTitle("Backup & recovery")
        .setItems(
            new String[] {
              "Create encrypted backup",
              "Restore encrypted backup",
              "Recover previous save",
              "Recover before last restore"
            },
            (d, n) -> {
              switch (n) {
                case 0 -> password(true, null);
                case 1 -> openDocument(READ_BACKUP);
                case 2 -> recover(false);
                case 3 -> recover(true);
              }
            })
        .setNegativeButton("Cancel", null)
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
                      filter = 0;
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
