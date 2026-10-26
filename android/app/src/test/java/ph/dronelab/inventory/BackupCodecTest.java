package ph.dronelab.inventory;

import static org.junit.Assert.*;

import java.nio.charset.StandardCharsets;
import org.junit.Test;

public class BackupCodecTest {
  void reject(String s) {
    try {
      BackupCodec.decode(s.getBytes(StandardCharsets.UTF_8));
      fail("Expected invalid backup rejection");
    } catch (Exception expected) {
    }
  }

  @Test
  public void onlyCompleteTypedBackupIsAccepted() {
    Model m = new Model();
    assertEquals(
        0, BackupCodec.decode(Model.JSON.toJson(m).getBytes(StandardCharsets.UTF_8)).items.size());
    reject("{}");
    reject("{\"schema\":1,\"items\":[],\"loans\":[]}");
    reject("{\"schema\":1.5,\"items\":[],\"loans\":[],\"events\":[]}");
    reject("{\"schema\":\"1\",\"items\":[],\"loans\":[],\"events\":[]}");
    reject("{\"schema\":1,\"items\":[],\"loans\":[],\"events\":[],\"extra\":0}");
  }

  @Test
  public void missingItemQuantityAndNullFieldsRejected() {
    Model m = new Model();
    Model.Item i = new Model.Item();
    i.id = "I";
    i.code = "001";
    i.name = "Hammer";
    i.category = "Tool";
    m.save(i, true);
    String json = Model.JSON.toJson(m);
    reject(json.replace("\"total\":1,", ""));
    reject(json.replace("\"total\":1", "\"total\":1.9"));
    reject(
        json.replace("\"returned\":0", "\"returned\":null")
            .replace("\"name\":\"Hammer\"", "\"name\":null"));
    assertEquals(
        "001", BackupCodec.decode(json.getBytes(StandardCharsets.UTF_8)).items.get(0).code);
  }

  @Test
  public void invalidUtf8AndTrailingJsonRejected() {
    reject(Model.JSON.toJson(new Model()) + " true");
    try {
      BackupCodec.decode(new byte[] {(byte) 0xc3, 0x28});
      fail();
    } catch (Exception expected) {
    }
  }
}
