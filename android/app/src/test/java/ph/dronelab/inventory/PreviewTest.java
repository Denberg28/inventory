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
    c.resume().visible();
    capture(a, "items");
    a.tab = 1;
    a.home();
    capture(a, "unreturned");
    a.onStop();
    a.onDestroy();
  }

  void capture(MainActivity a, String name) throws Exception {
    View v = a.root;
    v.measure(
        View.MeasureSpec.makeMeasureSpec(360, View.MeasureSpec.EXACTLY),
        View.MeasureSpec.makeMeasureSpec(720, View.MeasureSpec.EXACTLY));
    v.layout(0, 0, 360, 720);
    Bitmap b = Bitmap.createBitmap(360, 720, Bitmap.Config.ARGB_8888);
    v.draw(new Canvas(b));
    File file = new File("build/evidence/" + name + "-simulated.png");
    file.getParentFile().mkdirs();
    try (FileOutputStream out = new FileOutputStream(file)) {
      b.compress(Bitmap.CompressFormat.PNG, 100, out);
    }
  }
}
