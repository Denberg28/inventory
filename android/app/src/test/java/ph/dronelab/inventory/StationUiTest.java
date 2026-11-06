package ph.dronelab.inventory;
import static org.junit.Assert.*;
import android.app.AlertDialog;
import android.widget.*;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowAlertDialog;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28, qualifiers = "w360dp-h720dp")
public class StationUiTest {
  MainActivity open() {
    var controller = Robolectric.buildActivity(MainActivity.class).create().start();
    MainActivity a = controller.get();
    a.unlocked = true; a.model = new LoanFollowUpTest().openLoan();
    controller.resume().visible(); return a;
  }
  @Test public void borrowerThenItemOnlyPreparesIssueUntilPhoneConfirms() {
    MainActivity a = open();
    String before = Model.JSON.toJson(a.model);
    a.stationScanned("borrower", "ID-002");
    a.stationDialog.dismiss();
    a.stationScanned("station", "M1");
    // Dismissal callbacks may still be queued in Robolectric. Inspect the issue
    // dialog created by this scan, rather than an arbitrary older station form.
    LinearLayout fields = a.formDialogs.entrySet().stream()
        .filter(e -> e.getValue() == a.stationTransactionForm)
        .map(java.util.Map.Entry::getKey).findFirst().orElseThrow();
    boolean borrower = false;
    for (int n = 0; n < fields.getChildCount(); n++)
      if (fields.getChildAt(n) instanceof EditText e && "Borrower name / ID".contentEquals(e.getContentDescription()))
        borrower = e.getText().toString().equals("ID-002");
    assertTrue(borrower);
    assertEquals(before, Model.JSON.toJson(a.model));
    a.onStop(); a.onDestroy();
  }
  @Test public void returnCannotSelectAnotherBorrowersLoan() {
    MainActivity a = open();
    a.stationBorrower = "OTHER"; a.stationMode = "return";
    String before = Model.JSON.toJson(a.model);
    a.stationScanned("station", "M1");
    assertEquals("Couldn’t complete", Shadows.shadowOf(ShadowAlertDialog.getLatestAlertDialog()).getTitle());
    assertEquals(before, Model.JSON.toJson(a.model));
    a.onStop(); a.onDestroy();
  }
  @Test public void terminalCannotInterruptConfirmationAndLockClearsBorrower() {
    MainActivity a = open();
    a.returnForm(a.model.loans.get(0).id);
    AlertDialog existing = ShadowAlertDialog.getLatestAlertDialog();
    a.terminalRequest("summary");
    assertSame(existing, ShadowAlertDialog.getLatestAlertDialog());
    a.stationBorrower = "PRIVATE"; a.unlocked = false; a.locked();
    assertEquals("", a.stationBorrower);
    a.terminalRequest("summary");
    assertSame(existing, ShadowAlertDialog.getLatestAlertDialog());
    a.onStop(); a.onDestroy();
  }
}
