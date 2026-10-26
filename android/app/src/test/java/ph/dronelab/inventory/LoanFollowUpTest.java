package ph.dronelab.inventory;

import static org.junit.Assert.*;
import java.time.LocalDate;
import org.junit.Test;

public class LoanFollowUpTest {
  Model openLoan() {
    Model m = new Model();
    Model.Item item = new Model.Item();
    item.id = "M1";
    item.code = "000123";
    item.name = "Cable ties";
    item.category = "Material";
    item.total = 20;
    m.save(item, true);
    m.issue(item.id, 8, "Student 014", LocalDate.now().toString(), "Lab session", false);
    m.receive(m.loans.get(0).id, 3, "Available", "Partial return");
    return m;
  }

  @Test
  public void dateChangePreservesPartialCustodyAndRecordsOldDateAndReason() {
    Model m = openLoan();
    Model.Loan loan = m.loans.get(0);
    String originalIssued = loan.issued, oldDue = loan.due;
    int history = m.events.size();
    String next = LocalDate.now().plusDays(2).toString();
    m.reschedule(loan.id, oldDue, next, "  Extended practical session  ");
    m.validate();
    assertEquals(15, m.available("M1"));
    assertEquals(20, m.item("M1").total);
    assertEquals(8, loan.quantity);
    assertEquals(3, loan.returned);
    assertEquals("Student 014", loan.borrower);
    assertEquals("Lab session", loan.note);
    assertEquals(originalIssued, loan.issued);
    assertEquals(next, loan.due);
    assertEquals(history + 1, m.events.size());
    Model.Event event = m.events.get(history);
    assertEquals("RESCHEDULE", event.action);
    var detail = com.google.gson.JsonParser.parseString(event.detail).getAsJsonObject();
    assertEquals(oldDue, detail.get("previous_due").getAsString());
    assertEquals(next, detail.get("new_due").getAsString());
    assertEquals(loan.id, detail.get("issue_id").getAsString());
    assertEquals("Extended practical session", detail.get("reason").getAsString());
    assertEquals(next, BackupCodec.decode(Model.JSON.toJson(m).getBytes(
        java.nio.charset.StandardCharsets.UTF_8)).loans.get(0).due);
    assertTrue(Csv.issues(m).contains(next));
  }

  @Test
  public void invalidAndStaleDateChangesLeaveAllRecordsUnchanged() {
    Model m = openLoan();
    Model.Loan loan = m.loans.get(0);
    String next = LocalDate.now().plusDays(1).toString();
    String[][] invalid = {
      {loan.due, loan.due, "No change"},
      {loan.due, LocalDate.now().minusDays(1).toString(), "Past date"},
      {loan.due, "not-a-date", "Bad date"},
      {loan.due, next, " "},
      {loan.due, next, "x".repeat(501)},
      {"2000-01-01", next, "Stale form"}
    };
    String before = Model.JSON.toJson(m);
    for (String[] values : invalid) {
      assertThrows(IllegalArgumentException.class,
          () -> m.reschedule(loan.id, values[0], values[1], values[2]));
      assertEquals(before, Model.JSON.toJson(m));
    }
  }

  @Test
  public void overdueIssueCanBeRescheduledAndReturnedButCompletedIssueCannotChange() {
    Model m = openLoan();
    Model.Loan loan = m.loans.get(0);
    loan.due = LocalDate.now().minusDays(3).toString();
    m.reschedule(loan.id, loan.due, LocalDate.now().toString(), "Authorized extension");
    m.receive(loan.id, 5, "Available", "Completed");
    assertEquals(20, m.available("M1"));
    String before = Model.JSON.toJson(m);
    assertThrows(IllegalArgumentException.class, () -> m.reschedule(loan.id,
        loan.due, LocalDate.now().plusDays(1).toString(), "Too late"));
    assertEquals(before, Model.JSON.toJson(m));
  }
}
