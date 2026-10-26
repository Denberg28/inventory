package ph.dronelab.inventory;

import static org.junit.Assert.*;
import android.app.*;
import android.view.*;
import android.widget.*;
import java.time.LocalDate;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowAlertDialog;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28, qualifiers = "w360dp-h720dp")
public class FollowUpUiTest {
  MainActivity open() {
    var controller = Robolectric.buildActivity(MainActivity.class).create().start();
    MainActivity a = controller.get();
    a.unlocked = true;
    a.model = new LoanFollowUpTest().openLoan();
    controller.resume().visible();
    return a;
  }

  @Test
  public void returnSummaryUpdatesAndCancelDoesNotChangeInventory() {
    MainActivity a = open();
    String before = Model.JSON.toJson(a.model);
    a.returnForm(a.model.loans.get(0).id);
    AlertDialog form = ShadowAlertDialog.getLatestAlertDialog();
    LinearLayout fields = a.formDialogs.keySet().iterator().next();
    for (int n = 0; n < fields.getChildCount(); n++) {
      View v = fields.getChildAt(n);
      if (v instanceof EditText && "Quantity returned".contentEquals(v.getContentDescription()))
        ((EditText) v).setText("2");
    }
    assertEquals("Record return", form.getButton(AlertDialog.BUTTON_POSITIVE).getText());
    TextView summary = fields.findViewWithTag("return-summary");
    assertTrue(summary.getText().toString().contains("3 still outstanding"));
    Spinner condition = null;
    for (int n = 0; n < fields.getChildCount(); n++)
      if (fields.getChildAt(n) instanceof Spinner) condition = (Spinner) fields.getChildAt(n);
    assertNotNull(condition);
    condition.setSelection(1);
    org.robolectric.shadows.ShadowLooper.runUiThreadTasksIncludingDelayedTasks();
    assertTrue(summary.getText().toString().contains("entire item/lot will be on hold"));
    form.getButton(AlertDialog.BUTTON_NEGATIVE).performClick();
    assertEquals(before, Model.JSON.toJson(a.model));
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void invalidReturnStaysOnFormWithoutChangingCustody() {
    MainActivity a = open();
    a.returnForm(a.model.loans.get(0).id);
    AlertDialog form = ShadowAlertDialog.getLatestAlertDialog();
    LinearLayout fields = a.formDialogs.keySet().iterator().next();
    for (int n = 0; n < fields.getChildCount(); n++) {
      View v = fields.getChildAt(n);
      if (v instanceof EditText && "Quantity returned".contentEquals(v.getContentDescription()))
        ((EditText) v).setText("6");
    }
    form.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
    assertEquals("Couldn’t complete", Shadows.shadowOf(ShadowAlertDialog.getLatestAlertDialog()).getTitle());
    assertEquals(5, a.model.outstanding("M1"));
    assertTrue(form.isShowing());
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void reschedulingRequiresReasonAndDismissedPickerIsRemoved() {
    MainActivity a = open();
    Model.Loan loan = a.model.loans.get(0);
    a.rescheduleForm(loan.id);
    AlertDialog form = ShadowAlertDialog.getLatestAlertDialog();
    LinearLayout fields = a.formDialogs.keySet().iterator().next();
    Button date = (Button) fields.getChildAt(2);
    date.performClick();
    DatePickerDialog picker = (DatePickerDialog) a.dialogs.get(a.dialogs.size() - 1);
    LocalDate next = LocalDate.now().plusDays(2);
    picker.updateDate(next.getYear(), next.getMonthValue() - 1, next.getDayOfMonth());
    picker.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
    org.robolectric.shadows.ShadowLooper.runUiThreadTasksIncludingDelayedTasks();
    assertFalse(a.dialogs.contains(picker));
    assertTrue(date.getText().toString().contains(next.toString()));
    form.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
    assertEquals("Couldn’t complete", Shadows.shadowOf(ShadowAlertDialog.getLatestAlertDialog()).getTitle());
    assertEquals(LocalDate.now().toString(), loan.due);
    assertEquals("Required field is empty or too long (maximum 500)",
        Shadows.shadowOf(ShadowAlertDialog.getLatestAlertDialog()).getMessage().toString());
    a.onStop();
    a.onDestroy();
  }
}
