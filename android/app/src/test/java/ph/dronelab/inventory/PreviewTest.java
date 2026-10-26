package ph.dronelab.inventory;

import android.graphics.*;
import android.view.*;
import java.io.*;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;

@RunWith(org.robolectric.RobolectricTestRunner.class)
@Config(sdk = 28, qualifiers = "w360dp-h720dp-mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class PreviewTest {
  @Test
  public void renderPhoneScreens() throws Exception {
    var c = Robolectric.buildActivity(MainActivity.class).create().start();
    MainActivity a = c.get();
    a.unlocked = true;
    a.model = new Model();
    String[] names = {"Precision screwdriver", "Digital multimeter", "Cable ties"};
    for (int n = 0; n < 3; n++) {
      Model.Item i = new Model.Item();
      i.id = "DL-00" + (n + 1);
      i.code = "0001234" + n;
      i.name = names[n];
      i.category = n == 2 ? "Material" : "Tool";
      i.total = n == 2 ? 100 : 1;
      i.minimum = n == 2 ? 10 : 0;
      if (n == 1) i.status = "Maintenance";
      i.location = "Drone Laboratory · Cabinet " + (n + 1);
      a.model.save(i, true);
    }
    a.model.issue(
        "DL-001",
        1,
        "Student 2026-014",
        java.time.LocalDate.now().plusDays(1).toString(),
        "Practical session",
        false);
    a.model.loans.get(0).due = java.time.LocalDate.now().minusDays(1).toString();
    a.model.issue(
        "DL-003",
        95,
        "Student 2026-021",
        java.time.LocalDate.now().toString(),
        "Practical session",
        false);
    c.resume().visible();
    capture(a, "items");
    a.tab = 1;
    a.home();
    capture(a, "unreturned");
    a.returnForm(a.model.loans.get(0).id);
    android.app.AlertDialog returnDialog =
        org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
    org.robolectric.shadows.ShadowLooper.runUiThreadTasksIncludingDelayedTasks();
    captureView(returnDialog.getWindow().getDecorView(), "return-dialog", 360, 640);
    returnDialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE).performClick();
    android.app.AlertDialog review =
        org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
    org.robolectric.shadows.ShadowLooper.runUiThreadTasksIncludingDelayedTasks();
    captureView(review.getWindow().getDecorView(), "return-review", 360, 500);
    review.dismiss();
    returnDialog.dismiss();
    a.rescheduleForm(a.model.loans.get(0).id);
    android.app.AlertDialog reschedule =
        org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
    org.robolectric.shadows.ShadowLooper.runUiThreadTasksIncludingDelayedTasks();
    captureView(reschedule.getWindow().getDecorView(), "reschedule-dialog", 360, 580);
    reschedule.dismiss();
    a.tab = 0;
    a.home();
    a.edit(null, "000123456789");
    android.app.AlertDialog d = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
    org.robolectric.shadows.ShadowLooper.runUiThreadTasksIncludingDelayedTasks();
    captureView(d.getWindow().getDecorView(), "register-dialog", 360, 640);
    d.dismiss();
    android.content.res.Configuration landscape =
        new android.content.res.Configuration(a.getResources().getConfiguration());
    landscape.orientation = android.content.res.Configuration.ORIENTATION_LANDSCAPE;
    landscape.screenWidthDp = 720;
    landscape.screenHeightDp = 360;
    a.getResources().updateConfiguration(landscape, a.getResources().getDisplayMetrics());
    a.onConfigurationChanged(landscape);
    captureView(a.root, "items-landscape", 720, 360);
    org.junit.Assert.assertTrue(
        "Landscape must leave room for inventory", a.itemScroll.getHeight() >= 120);
    android.content.res.Configuration config =
        new android.content.res.Configuration(a.getResources().getConfiguration());
    config.orientation = android.content.res.Configuration.ORIENTATION_PORTRAIT;
    config.screenWidthDp = 360;
    config.screenHeightDp = 720;
    config.fontScale = 1.3f;
    a.getResources().updateConfiguration(config, a.getResources().getDisplayMetrics());
    a.home();
    captureView(a.root, "items-large-text", 360, 720);
    a.onStop();
    a.onDestroy();
  }

  void capture(MainActivity a, String name) throws Exception {
    captureView(a.root, name, 360, 720);
  }

  void captureView(View v, String name, int width, int height) throws Exception {
    v.measure(
        View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
        View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY));
    v.layout(0, 0, width, height);
    Bitmap b = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
    v.draw(new Canvas(b));
    File file = new File("build/evidence/" + name + "-simulated.png");
    file.getParentFile().mkdirs();
    try (FileOutputStream out = new FileOutputStream(file)) {
      b.compress(Bitmap.CompressFormat.PNG, 100, out);
    }
  }
}
