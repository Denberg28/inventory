package ph.dronelab.inventory;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.time.*;
import java.util.Arrays;

/** A terminal requests navigation only. It can never commit an inventory mutation. */
public final class TerminalProtocol {
  public static final int VERSION = 1, MAX_LINE = 2048;
  private final String session;
  private long lastSequence = 0;
  public TerminalProtocol(String session) { this.session = session; }

  public String accept(String line) {
    Model.check(line.length() <= MAX_LINE, "Terminal frame too large");
    JsonObject o = JsonParser.parseString(line).getAsJsonObject();
    Model.check(o.get("v").getAsString().equals("1"), "Terminal protocol mismatch");
    Model.check(session.equals(o.get("session").getAsString()), "Stale terminal session");
    String kind = o.get("type").getAsString();
    if (kind.equals("ready")) return "ready";
    Model.check(kind.equals("request"), "Unknown terminal message");
    Model.check(o.get("seq").getAsString().matches("[1-9][0-9]{0,9}"), "Invalid sequence");
    long seq = o.get("seq").getAsLong();
    Model.check(seq > lastSequence && seq <= Integer.MAX_VALUE, "Repeated terminal request");
    String action = o.get("action").getAsString();
    Model.check(Arrays.asList("borrower", "issue", "return", "summary").contains(action),
        "Unsupported terminal request");
    lastSequence = seq;
    return action;
  }

  public static JsonObject frame(String type, String session) {
    JsonObject o = new JsonObject();
    o.addProperty("v", VERSION); o.addProperty("type", type); o.addProperty("session", session);
    return o;
  }

  public static final class Summary {
    public long issued, returned, outstanding, overdue;
    public int unreadableEvents;
    public final String day;
    Summary(LocalDate day) { this.day = day.toString(); }
    public String text() {
      return day + "\nIssued today: " + issued + " units\nReturned today: " + returned
          + " units\nOutstanding: " + outstanding + " units\nOverdue: " + overdue + " units"
          + (unreadableEvents == 0 ? "" : "\nWarning: " + unreadableEvents + " imported audit entries could not be counted");
    }
  }

  public static Summary summary(Model m, LocalDate day, ZoneId zone) {
    Summary s = new Summary(day);
    for (Model.Loan l : m.loans) {
      int open = l.quantity - l.returned;
      s.outstanding += open;
      if (LocalDate.parse(l.due).isBefore(day)) s.overdue += open;
    }
    for (Model.Event e : m.events) {
      if (!Instant.parse(e.time).atZone(zone).toLocalDate().equals(day)) continue;
      try {
        if (e.action.equals("ISSUE")) {
          int n = Model.JSON.fromJson(e.detail, Model.Loan.class).quantity;
          Model.check(n > 0 && n <= Model.LIMIT, "Invalid audit quantity");
          s.issued += n;
        } else if (e.action.equals("RETURN")) {
          int n = Integer.parseInt(e.detail.split(" ", 2)[0]);
          Model.check(n > 0 && n <= Model.LIMIT, "Invalid audit quantity");
          s.returned += n;
        }
      } catch (RuntimeException ignored) { s.unreadableEvents++; }
    }
    return s;
  }
}
