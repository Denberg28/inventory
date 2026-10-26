package ph.dronelab.inventory;

import java.util.*;

public final class Csv {
  static final String HEADER =
      "item_id,barcode,name,category,status,quantity,min_stock,location,notes\r\n";

  static String cell(Object o) {
    String s = String.valueOf(o);
    if (s.matches("(?s)^\\s*[=+@-].*")) s = "'" + s;
    return "\"" + s.replace("\"", "\"\"") + "\"";
  }

  static void row(StringBuilder b, Object... cells) {
    for (int i = 0; i < cells.length; i++) {
      if (i > 0) b.append(',');
      b.append(cell(cells[i]));
    }
    b.append("\r\n");
  }

  public static String inventory(Model m) {
    StringBuilder b = new StringBuilder(HEADER);
    for (Model.Item i : m.items)
      if (!i.archived)
        row(b, i.id, i.code, i.name, i.category, i.status, i.total, i.minimum, i.location, i.notes);
    return b.toString();
  }

  public static String issues(Model m) {
    StringBuilder b =
        new StringBuilder(
            "issue_id,item_id,item_name,borrower,issued,due,quantity,returned,outstanding,note\r\n");
    for (Model.Loan l : m.loans)
      row(
          b,
          l.id,
          l.itemId,
          m.item(l.itemId).name,
          l.borrower,
          l.issued,
          l.due,
          l.quantity,
          l.returned,
          l.quantity - l.returned,
          l.note);
    return b.toString();
  }

  public static String history(Model m) {
    StringBuilder b = new StringBuilder("event_id,time,item_id,action,detail\r\n");
    for (Model.Event e : m.events) row(b, e.id, e.time, e.itemId, e.action, e.detail);
    return b.toString();
  }

  public static ArrayList<List<String>> parse(String value) {
    Model.check(value.length() <= 8 * 1024 * 1024, "CSV exceeds 8 MB");
    if (value.startsWith("\uFEFF")) value = value.substring(1);
    ArrayList<List<String>> rows = new ArrayList<>();
    List<String> row = new ArrayList<>();
    StringBuilder s = new StringBuilder();
    boolean quoted = false, closed = false;
    for (int i = 0; i < value.length(); i++) {
      char c = value.charAt(i);
      if (quoted) {
        if (c == '"') {
          if (i + 1 < value.length() && value.charAt(i + 1) == '"') {
            s.append('"');
            i++;
          } else {
            quoted = false;
            closed = true;
          }
        } else s.append(c);
      } else if (c == '"') {
        Model.check(s.length() == 0 && !closed, "Malformed CSV quote");
        quoted = true;
      } else if (c == ',' || c == '\n' || c == '\r') {
        row.add(s.toString());
        s.setLength(0);
        closed = false;
        if (c != ',') {
          rows.add(row);
          row = new ArrayList<>();
          if (c == '\r' && i + 1 < value.length() && value.charAt(i + 1) == '\n') i++;
        }
      } else {
        Model.check(!closed, "Unexpected text after CSV quote");
        s.append(c);
      }
      Model.check(
          s.length() <= 16000 && row.size() <= 32 && rows.size() <= 10001, "CSV limits exceeded");
    }
    Model.check(!quoted, "Unclosed CSV quote");
    if (s.length() > 0 || closed || !row.isEmpty()) {
      row.add(s.toString());
      rows.add(row);
    }
    return rows;
  }

  static String get(List<String> row, int i) {
    String s = row.get(i);
    if (s.matches("(?s)^'\\s*[=+@-].*")) s = s.substring(1);
    return s;
  }

  public static int addItems(Model m, String csv) {
    ArrayList<List<String>> rows = parse(csv);
    Model.check(!rows.isEmpty(), "CSV is empty");
    List<String> h = rows.remove(0), expected = Arrays.asList(HEADER.trim().split(","));
    Model.check(h.equals(expected), "CSV needs columns: " + HEADER.trim());
    int count = 0;
    for (List<String> row : rows) {
      if (row.size() == 1 && row.get(0).trim().isEmpty()) continue;
      Model.check(row.size() == 9, "CSV row must have 9 columns");
      Model.Item i = new Model.Item();
      i.id = get(row, 0);
      i.code = get(row, 1);
      i.name = get(row, 2);
      i.category = get(row, 3);
      i.status = get(row, 4);
      Model.check(
          !i.status.equals("In use"),
          "CSV cannot transfer active loans. Return items first or use an Android encrypted"
              + " backup.");
      try {
        i.total = Integer.parseInt(row.get(5));
        i.minimum = Integer.parseInt(row.get(6));
      } catch (Exception e) {
        throw new IllegalArgumentException("CSV quantity must be a whole number");
      }
      i.location = get(row, 7);
      i.notes = get(row, 8);
      m.save(i, true);
      count++;
    }
    Model.check(count > 0, "CSV has no items");
    m.validate();
    return count;
  }
}
