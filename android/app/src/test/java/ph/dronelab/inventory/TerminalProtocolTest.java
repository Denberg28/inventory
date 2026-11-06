package ph.dronelab.inventory;

import org.junit.Test;
import java.time.*;
import static org.junit.Assert.*;

public class TerminalProtocolTest {
  private String request(String session, int seq, String action) {
    return "{\"v\":1,\"type\":\"request\",\"session\":\"" + session
        + "\",\"seq\":" + seq + ",\"action\":\"" + action + "\"}";
  }
  @Test public void reconnectRejectsOldSessionAndRepeatedRequests() {
    TerminalProtocol p = new TerminalProtocol("new");
    assertThrows(IllegalArgumentException.class, () -> p.accept(request("old", 1, "issue")));
    assertEquals("issue", p.accept(request("new", 1, "issue")));
    assertThrows(IllegalArgumentException.class, () -> p.accept(request("new", 1, "return")));
    assertEquals("return", p.accept(request("new", 2, "return")));
  }
  @Test public void transportHasNoMutationCommand() {
    TerminalProtocol p = new TerminalProtocol("s");
    for (String action : new String[]{"commit", "delete", "restore", "receive", "save"})
      assertThrows(IllegalArgumentException.class, () -> p.accept(request("s", 1, action)));
    assertEquals("borrower", p.accept(request("s", 1, "borrower")));
    assertThrows(RuntimeException.class, () -> p.accept("not json"));
    assertThrows(RuntimeException.class, () -> p.accept("{}"));
    assertThrows(RuntimeException.class, () -> p.accept(" ".repeat(2049)));
  }
  @Test public void summaryCountsUnitsAndUsesLocalDayBoundary() {
    Model m = new Model();
    Model.Item i = new Model.Item();
    i.id = "MAT"; i.code = "M"; i.name = "Parts"; i.category = "Material"; i.total = 20;
    m.save(i, true);
    m.issue("MAT", 5, "STUDENT-1", LocalDate.now().toString(), "", false);
    m.receive(m.loans.get(0).id, 2, "Available", "");
    m.events.stream().filter(e -> e.action.equals("ISSUE") || e.action.equals("RETURN"))
        .forEach(e -> e.time = "2026-11-05T16:30:00Z");
    TerminalProtocol.Summary s = TerminalProtocol.summary(m, LocalDate.of(2026,11,6), ZoneId.of("Asia/Manila"));
    assertEquals(5, s.issued); assertEquals(2, s.returned); assertEquals(3, s.outstanding);
    s = TerminalProtocol.summary(m, LocalDate.of(2026,11,5), ZoneId.of("Asia/Manila"));
    assertEquals(0, s.issued); assertEquals(0, s.returned);
  }
  @Test public void borrowerCodeRequiresOneLineAndFitsExistingLoanField() {
    assertEquals("2026-A001", MainActivity.borrowerCode(" 2026-A001 "));
    assertThrows(IllegalArgumentException.class, () -> MainActivity.borrowerCode("A\nB"));
    assertThrows(IllegalArgumentException.class, () -> MainActivity.borrowerCode("A".repeat(121)));
  }
}
