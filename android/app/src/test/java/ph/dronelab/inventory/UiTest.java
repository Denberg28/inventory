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
    assertEquals("Data", a.getString(R.string.data));
    assertEquals("Inventory Preview", a.getString(R.string.app_name));
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

  Model.Item add(MainActivity a, String id, String category, int total) {
    Model.Item item = new Model.Item();
    item.id = id;
    item.code = "000" + id;
    item.name = "Item " + id;
    item.category = category;
    item.total = total;
    item.minimum = category.equals("Material") ? 5 : 0;
    a.model.save(item, true);
    return item;
  }

  @Test
  public void attentionFiltersPreserveStockAndCustody() {
    MainActivity a = open();
    add(a, "T", "Tool", 1);
    add(a, "M", "Material", 10);
    a.model.issue("M", 6, "Student", java.time.LocalDate.now().toString(), "", false);
    a.filter = 3;
    a.home();
    assertEquals(1, a.list.getChildCount());
    assertEquals(4, a.model.available("M"));
    a.filter = 2;
    a.home();
    assertEquals(1, a.list.getChildCount());
    a.filter = 1;
    a.home();
    assertEquals(2, a.list.getChildCount());
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void dueTodayAndOverdueDoNotOverlapAndCodeSearchWorks() {
    MainActivity a = open();
    add(a, "T", "Tool", 1);
    a.model.issue("T", 1, "Student", java.time.LocalDate.now().toString(), "", false);
    a.tab = 1;
    a.filter = 1;
    a.home();
    assertEquals(2, a.list.getChildCount());
    a.filter = 2;
    a.query = "000T";
    a.home();
    assertEquals(1, a.list.getChildCount());
    a.model.loans.get(0).due = java.time.LocalDate.now().minusDays(1).toString();
    a.filter = 1;
    a.home();
    assertEquals(1, a.list.getChildCount());
    assertEquals(1, a.model.outstanding("T"));
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void unavailableIssueIsDisabledAndDismissRemainsAvailable() {
    MainActivity a = open();
    add(a, "T", "Tool", 1);
    a.model.issue("T", 1, "Student", java.time.LocalDate.now().toString(), "", false);
    a.details("T");
    android.app.AlertDialog d = ShadowAlertDialog.getLatestAlertDialog();
    assertFalse(d.getButton(android.app.AlertDialog.BUTTON_POSITIVE).isEnabled());
    assertEquals("OK", d.getButton(android.app.AlertDialog.BUTTON_NEGATIVE).getText().toString());
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void primaryActionIsOutsideScrollAndDismissCleansRegistry() {
    MainActivity a = open();
    a.edit(null, "0001");
    android.app.AlertDialog d = ShadowAlertDialog.getLatestAlertDialog();
    Button save = d.getButton(android.app.AlertDialog.BUTTON_POSITIVE);
    assertEquals("Save item", save.getText().toString());
    assertEquals(View.VISIBLE, save.getVisibility());
    assertTrue(save.getMinimumHeight() >= a.dp(48));
    // Native themes may wrap the whole dialog; the form's own scroller must not
    // contain the action row.
    ViewParent formScroller = a.formDialogs.keySet().iterator().next().getParent();
    assertTrue(formScroller instanceof ScrollView);
    ViewParent parent = save.getParent();
    while (parent != null) {
      assertNotSame(formScroller, parent);
      parent = parent.getParent();
    }
    d.dismiss();
    org.robolectric.shadows.ShadowLooper.runUiThreadTasksIncludingDelayedTasks();
    assertTrue(a.formDialogs.isEmpty());
    assertTrue(a.dialogs.isEmpty());
    a.onStop();
    a.onDestroy();
  }

  @Test
  public void tabReselectionPreservesSearchButNewViewResetsFilter() {
    MainActivity a = open();
    a.query = "cabinet";
    a.filter = 3;
    a.switchTab(0);
    assertEquals("cabinet", a.query);
    assertEquals(3, a.filter);
    a.switchTab(1);
    assertEquals("", a.query);
    assertEquals(0, a.filter);
    assertEquals("All unreturned", a.filterName());
    a.onStop();
    a.onDestroy();
  }
}
