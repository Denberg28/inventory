package ph.dronelab.inventory;

import com.google.gson.Gson;
import java.time.*;
import java.util.*;

/** Domain rules are independent of Android. Only persist a fully validated copy. */
public final class Model {
  public static final Gson JSON = new Gson();
  public static final int LIMIT = 999999;

  public static class Item {
    public String id, code, name, category, location = "", notes = "", status = "Available";
    public int total = 1, minimum = 0;
    public boolean archived = false;
  }

  public static class Loan {
    public String id, itemId, borrower, due, issued, note = "";
    public int quantity, returned;
  }

  public static class Event {
    public String id, time, itemId, action, detail;
  }

  public int schema = 1;
  public ArrayList<Item> items = new ArrayList<>();
  public ArrayList<Loan> loans = new ArrayList<>();
  public ArrayList<Event> events = new ArrayList<>();

  public Model copy() {
    return JSON.fromJson(JSON.toJson(this), Model.class);
  }

  public static String text(String v, int max, boolean required) {
    check(v != null, "Missing text field");
    String s = v.replace("\r\n", "\n").replace("\r", "\n").trim();
    check(
        s.length() <= max && (!required || !s.isEmpty()),
        "Required field is empty or too long (maximum " + max + ")");
    for (char c : s.toCharArray())
      check(!Character.isISOControl(c) || c == '\n' || c == '\t', "Unsupported control character");
    return s;
  }

  public static void check(boolean ok, String msg) {
    if (!ok) throw new IllegalArgumentException(msg);
  }

  static boolean category(String c) {
    return Arrays.asList("Tool", "Equipment", "Material").contains(c);
  }

  public static boolean status(String s) {
    return Arrays.asList("Available", "Maintenance", "Damaged", "Lost", "Retired").contains(s);
  }

  public Item item(String id) {
    return items.stream()
        .filter(i -> i.id.equals(id))
        .findFirst()
        .orElseThrow(() -> new IllegalArgumentException("Item no longer exists"));
  }

  public Loan loan(String id) {
    return loans.stream()
        .filter(i -> i.id.equals(id))
        .findFirst()
        .orElseThrow(() -> new IllegalArgumentException("Issue no longer exists"));
  }

  public int outstanding(String id) {
    return loans.stream()
        .filter(l -> l.itemId.equals(id))
        .mapToInt(l -> l.quantity - l.returned)
        .sum();
  }

  public int available(String id) {
    return item(id).total - outstanding(id);
  }

  public static String code(String c) {
    String s = text(c, 128, true);
    for (char ch : s.toCharArray())
      check(!Character.isISOControl(ch), "A scan code or ID must be a single line");
    return s;
  }

  public Item byCode(String c) {
    return items.stream()
        .filter(i -> i.code.equalsIgnoreCase(c) || i.id.equalsIgnoreCase(c))
        .findFirst()
        .orElse(null);
  }

  static String uid() {
    return UUID.randomUUID().toString();
  }

  void audit(String id, String action, String detail) {
    Event e = new Event();
    e.id = uid();
    e.time = Instant.now().toString();
    e.itemId = id;
    e.action = action;
    e.detail = detail;
    events.add(e);
  }

  public void save(Item value, boolean create) {
    Item n = JSON.fromJson(JSON.toJson(value), Item.class);
    n.id = code(n.id);
    n.code = code(n.code);
    n.name = text(n.name, 160, true);
    n.location = text(n.location, 120, false);
    n.notes = text(n.notes, 2000, false);
    check(category(n.category) && status(n.status), "Choose a valid category and status");
    check(
        n.total >= 0 && n.total <= LIMIT && n.minimum >= 0 && n.minimum <= LIMIT,
        "Quantity must be 0–999999");
    check(
        n.category.equals("Material") || (n.total == 1 && n.minimum == 0),
        "Register each physical tool/equipment as quantity 1");
    Item old = create ? null : item(n.id);
    for (Item i : items)
      if (create || !i.id.equals(n.id)) {
        check(
            !i.code.equalsIgnoreCase(n.code)
                && !i.id.equalsIgnoreCase(n.id)
                && !i.id.equalsIgnoreCase(n.code)
                && !i.code.equalsIgnoreCase(n.id),
            "ID or scan code already belongs to another item");
      }
    check(create || old.category.equals(n.category), "Category cannot change after registration");
    check(create || old.archived == n.archived, "Use Archive/Restore to change deletion state");
    check(n.total >= outstanding(n.id), "Quantity cannot be below the amount still issued");
    if (create) {
      check(items.size() < 10000, "Item limit reached");
      items.add(n);
    } else items.set(items.indexOf(old), n);
    audit(n.id, create ? "REGISTER" : "EDIT", JSON.toJson(n));
  }

  public void issue(
      String id, int qty, String borrower, String due, String note, boolean consumed) {
    Item i = item(id);
    check(
        !i.archived && i.status.equals("Available"),
        "This item cannot be issued in its current status");
    check(qty > 0 && qty <= available(id), "Not enough available stock");
    borrower = text(borrower, 120, true);
    note = text(note, 500, false);
    check(!consumed || i.category.equals("Material"), "Only materials can be issued as consumed");
    if (consumed) {
      i.total -= qty;
      audit(id, "CONSUME", qty + " to " + borrower + " · " + note);
    } else {
      LocalDate d;
      try {
        d = LocalDate.parse(due);
      } catch (Exception e) {
        throw new IllegalArgumentException("Choose a valid return date");
      }
      check(!d.isBefore(LocalDate.now()), "Return date cannot be in the past");
      Loan l = new Loan();
      l.id = uid();
      l.itemId = id;
      l.borrower = borrower;
      l.due = d.toString();
      l.issued = Instant.now().toString();
      l.note = note;
      l.quantity = qty;
      loans.add(l);
      audit(id, "ISSUE", JSON.toJson(l));
    }
  }

  public void receive(String loanId, int qty, String condition, String note) {
    Loan l = loan(loanId);
    Item i = item(l.itemId);
    check(qty > 0 && qty <= l.quantity - l.returned, "Return exceeds outstanding quantity");
    check(
        Arrays.asList("Available", "Damaged", "Maintenance").contains(condition),
        "Choose a return condition");
    note = text(note, 500, false);
    l.returned += qty;
    // A damaged return holds the whole material lot until the operator edits its status.
    if (!condition.equals("Available")) i.status = condition;
    audit(i.id, "RETURN", qty + " · issue " + l.id + " · " + condition + " · " + note);
  }

  public void archive(String id, boolean value) {
    Item i = item(id);
    check(outstanding(id) == 0, "Return all issued quantities before deleting this item");
    i.archived = value;
    audit(id, value ? "ARCHIVE" : "RESTORE", i.name);
  }

  public void validate() {
    check(
        schema == 1 && items != null && loans != null && events != null,
        "Unsupported or incomplete backup");
    check(
        items.size() <= 10000 && loans.size() <= 50000 && events.size() <= 100000,
        "Backup exceeds record limits");
    Set<String> ids = new TreeSet<>(String.CASE_INSENSITIVE_ORDER),
        codes = new TreeSet<>(String.CASE_INSENSITIVE_ORDER);
    HashSet<String> keys = new HashSet<>();
    for (Item i : items) {
      check(i != null, "Invalid item");
      check(code(i.id).equals(i.id) && code(i.code).equals(i.code), "Invalid item identifiers");
      check(ids.add(i.id) && codes.add(i.code), "Duplicate inventory identifier");
      check(
          text(i.name, 160, true).equals(i.name) && category(i.category) && status(i.status),
          "Invalid item fields");
      text(i.location, 120, false);
      text(i.notes, 2000, false);
      check(
          i.total >= 0 && i.total <= LIMIT && i.minimum >= 0 && i.minimum <= LIMIT,
          "Invalid stock quantity");
      check(
          i.category.equals("Material") || (i.total == 1 && i.minimum == 0),
          "Tools/equipment must be individually registered");
    }
    Map<String, String> owner = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
    for (Item i : items) owner.put(i.id, i.id);
    for (Item i : items) {
      String o = owner.get(i.code);
      check(o == null || o.equals(i.id), "Ambiguous scan code");
    }
    HashMap<String, Item> itemMap = new HashMap<>();
    for (Item i : items) itemMap.put(i.id, i);
    HashMap<String, Long> sums = new HashMap<>();
    for (Loan l : loans) {
      check(l != null && keys.add(code(l.id)), "Invalid/duplicate issue");
      check(itemMap.containsKey(l.itemId), "Unknown issue item");
      text(l.borrower, 120, true);
      text(l.note, 500, false);
      check(
          l.quantity > 0 && l.quantity <= LIMIT && l.returned >= 0 && l.returned <= l.quantity,
          "Invalid returned quantity");
      LocalDate.parse(l.due);
      Instant.parse(l.issued);
      sums.merge(l.itemId, (long) l.quantity - l.returned, Long::sum);
    }
    for (Item i : items) {
      long out = sums.getOrDefault(i.id, 0L);
      check(out <= i.total && (!i.archived || out == 0), "Backup has inconsistent custody/stock");
    }
    keys.clear();
    for (Event e : events) {
      check(e != null && keys.add(code(e.id)), "Invalid/duplicate event");
      check(itemMap.containsKey(e.itemId), "Unknown history item");
      Instant.parse(e.time);
      text(e.action, 30, true);
      text(e.detail, 12000, false);
    }
  }
}
