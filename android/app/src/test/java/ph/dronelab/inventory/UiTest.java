package ph.dronelab.inventory;

import static org.junit.Assert.*;

import android.view.*;
import android.widget.*;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowAlertDialog;

@RunWith(org.robolectric.RobolectricTestRunner.class)
@Config(sdk = 28, qualifiers = "w360dp-h720dp")
public class UiTest {
  MainActivity open() {
    ActivityController<MainActivity> c =
        Robolectric.buildActivity(MainActivity.class).create().start();
    MainActivity a = c.get();
    a.unlocked = true;
    a.model = new Model();
    c.resume().visible();
    return a;
  }

  @Test
  public void phoneHomeAndRegisterDialogRender() {
    MainActivity a = open();
    assertNotNull(a.search);
    assertEquals(0, a.model.items.size());
    a.edit(null, "000001234");
    assertTrue(ShadowAlertDialog.getLatestAlertDialog().isShowing());
    assertEquals(
        "Register item", Shadows.shadowOf(ShadowAlertDialog.getLatestAlertDialog()).getTitle());
    a.onStop();
    assertFalse(ShadowAlertDialog.getLatestAlertDialog().isShowing());
    a.onDestroy();
  }

  @Test
  public void scanSelectsExistingAndNeverIssuesAutomatically() {
    MainActivity a = open();
    Model.Item i = new Model.Item();
    i.id = "T";
    i.code = "0001";
    i.name = "Hammer";
    i.category = "Tool";
    a.model.save(i, true);
    a.scanned("0001");
    assertEquals("Hammer", Shadows.shadowOf(ShadowAlertDialog.getLatestAlertDialog()).getTitle());
    assertTrue(a.model.loans.isEmpty());
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void unknownScanAsksBeforeRegistration() {
    MainActivity a = open();
    a.scanned("0012345");
    assertEquals(
        "New label", Shadows.shadowOf(ShadowAlertDialog.getLatestAlertDialog()).getTitle());
    assertTrue(a.model.items.isEmpty());
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void unreturnedAndArchiveFiltersDoNotChangeInventory() {
    MainActivity a = open();
    Model.Item i = new Model.Item();
    i.id = "T";
    i.code = "0001";
    i.name = "Hammer";
    i.category = "Tool";
    a.model.save(i, true);
    a.model.issue("T", 1, "Student", java.time.LocalDate.now().toString(), "", false);
    a.tab = 1;
    a.home();
    assertEquals(1, a.model.outstanding("T"));
    assertEquals(1, a.list.getChildCount());
    a.query = "nonexistent";
    a.renderList();
    assertEquals(2, a.list.getChildCount());
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void authenticationDoesNotDiscardPendingPickerResult() {
    MainActivity a = open();
    final int[] run = {0};
    a.pending = () -> run[0]++;
    a.unlocked = false;
    a.onActivityResult(MainActivity.AUTH, android.app.Activity.RESULT_OK, null);
    a.onResume();
    assertEquals(1, run[0]);
    assertNull(a.pending);
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void canceledAuthenticationKeepsUnlockActionAndHidesDialogs() {
    MainActivity a = open();
    a.edit(null, "");
    a.onActivityResult(MainActivity.AUTH, android.app.Activity.RESULT_CANCELED, null);
    a.onResume();
    assertFalse(a.unlocked);
    assertFalse(ShadowAlertDialog.getLatestAlertDialog().isShowing());
    assertTrue(a.root.getChildAt(a.root.getChildCount() - 1) instanceof Button);
    a.onStop();
    a.onDestroy();
  }
}
