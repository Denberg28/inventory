package ph.dronelab.inventory;

import static org.junit.Assert.*;

import java.nio.charset.StandardCharsets;
import java.time.*;
import javax.crypto.spec.SecretKeySpec;
import org.junit.Test;

public class ModelTest {
  Model.Item material(String id, int quantity) {
    Model.Item i = new Model.Item();
    i.id = id;
    i.code = "000" + id;
    i.name = "Cable ties";
    i.category = "Material";
    i.total = quantity;
    return i;
  }

  String due() {
    return LocalDate.now().plusDays(2).toString();
  }

  void rejects(Runnable r) {
    try {
      r.run();
      fail("Expected rejection");
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test
  public void borrowPartialAndFullReturn() {
    Model m = new Model();
    m.save(material("M1", 10), true);
    m.issue("M1", 6, "Student 001", due(), "lab", false);
    assertEquals(4, m.available("M1"));
    String id = m.loans.get(0).id;
    m.receive(id, 2, "Available", "");
    assertEquals(6, m.available("M1"));
    assertEquals(4, m.outstanding("M1"));
    m.receive(id, 4, "Available", "");
    assertEquals(10, m.available("M1"));
    assertEquals(4, m.events.size());
    m.validate();
  }

  @Test
  public void consumedMaterialIsNotUnreturned() {
    Model m = new Model();
    m.save(material("M1", 10), true);
    m.issue("M1", 3, "Student", due(), "", true);
    assertEquals(7, m.available("M1"));
    assertEquals(0, m.outstanding("M1"));
    assertTrue(m.loans.isEmpty());
    m.validate();
  }

  @Test
  public void overIssueAndExcessReturnBlocked() {
    Model m = new Model();
    m.save(material("M1", 2), true);
    rejects(() -> m.issue("M1", 3, "S", due(), "", false));
    m.issue("M1", 2, "S", due(), "", false);
    rejects(() -> m.receive(m.loans.get(0).id, 3, "Available", ""));
    assertEquals(2, m.outstanding("M1"));
  }

  @Test
  public void toolCannotConsumeOrHaveQuantityTwo() {
    Model m = new Model();
    Model.Item i = material("T1", 1);
    i.category = "Tool";
    m.save(i, true);
    rejects(() -> m.issue("T1", 1, "S", due(), "", true));
    i.total = 2;
    rejects(() -> m.save(i, false));
  }

  @Test
  public void duplicateAndAmbiguousScanCodesBlocked() {
    Model m = new Model();
    m.save(material("001", 1), true);
    Model.Item i = material("002", 1);
    i.code = "001";
    rejects(() -> m.save(i, true));
    i.code = "000001";
    rejects(() -> m.save(i, true));
    i.id = "001";
    i.code = "other";
    rejects(() -> m.save(i, true));
    assertEquals("001", m.byCode("000001").id);
  }

  @Test
  public void deleteBlocksCustodyAndKeepsHistory() {
    Model m = new Model();
    m.save(material("M", 3), true);
    m.issue("M", 1, "S", due(), "", false);
    rejects(() -> m.archive("M", true));
    m.receive(m.loans.get(0).id, 1, "Available", "");
    m.archive("M", true);
    assertTrue(m.item("M").archived);
    assertEquals(1, m.loans.size());
    rejects(() -> m.issue("M", 1, "S", due(), "", false));
    m.archive("M", false);
    assertFalse(m.item("M").archived);
    m.validate();
  }

  @Test
  public void damagedReturnPlacesLotOnHold() {
    Model m = new Model();
    m.save(material("M", 3), true);
    m.issue("M", 2, "S", due(), "", false);
    m.receive(m.loans.get(0).id, 1, "Damaged", "broken");
    rejects(() -> m.issue("M", 1, "S", due(), "", false));
    assertEquals("Damaged", m.item("M").status);
    m.validate();
  }

  @Test
  public void editCannotEraseOutstandingStockOrCategory() {
    Model m = new Model();
    m.save(material("M", 10), true);
    m.issue("M", 6, "S", due(), "", false);
    Model.Item i = m.copy().item("M");
    i.total = 5;
    rejects(() -> m.save(i, false));
    i.total = 10;
    i.category = "Tool";
    rejects(() -> m.save(i, false));
    assertEquals(10, m.item("M").total);
  }

  @Test
  public void missingBorrowerPastDueAndZeroIssueBlocked() {
    Model m = new Model();
    m.save(material("M", 3), true);
    rejects(() -> m.issue("M", 0, "S", due(), "", false));
    rejects(() -> m.issue("M", 1, "", due(), "", false));
    rejects(() -> m.issue("M", 1, "S", "2000-01-01", "", false));
  }

  @Test
  public void malformedBackupsFailValidation() {
    Model m = new Model();
    m.save(material("M", 10), true);
    m.issue("M", 2, "S", due(), "", false);
    Model n = m.copy();
    n.loans.get(0).returned = 3;
    rejects(n::validate);
    n = m.copy();
    n.item("M").archived = true;
    rejects(n::validate);
    n = m.copy();
    n.schema = 42;
    rejects(n::validate);
    n = m.copy();
    n.loans.get(0).itemId = "missing";
    rejects(n::validate);
  }

  @Test
  public void copyFailureDoesNotMutateCommittedState() {
    Model committed = new Model();
    committed.save(material("M", 3), true);
    Model working = committed.copy();
    working.issue("M", 1, "S", due(), "", false);
    rejects(() -> working.issue("M", 3, "S", due(), "", false));
    assertEquals(3, committed.available("M"));
    assertEquals(1, committed.events.size());
  }

  @Test
  public void csvRoundTripPreservesCodesQuotesAndNewlines() {
    Model m = new Model();
    Model.Item i = material("0001", 7);
    i.code = "00002345";
    i.name = "Screw, 4\"";
    i.notes = "line one\nline two";
    m.save(i, true);
    Model n = new Model();
    assertEquals(1, Csv.addItems(n, Csv.inventory(m)));
    assertEquals(i.code, n.item(i.id).code);
    assertEquals(i.name, n.item(i.id).name);
    assertEquals(i.notes, n.item(i.id).notes);
  }

  @Test
  public void csvRejectsUnknownColumnsAndMalformedRows() {
    rejects(() -> Csv.addItems(new Model(), "name,quantity\nx,1"));
    rejects(() -> Csv.parse("a,\"unclosed"));
    rejects(() -> Csv.parse("\"quoted\"bad,b"));
    Model m = new Model();
    m.save(material("M", 1), true);
    rejects(() -> Csv.addItems(m, Csv.inventory(m)));
  }

  @Test
  public void csvNeutralizesSpreadsheetFormulas() {
    Model m = new Model();
    Model.Item i = material("M", 1);
    i.name = "=HYPERLINK(\"bad\")";
    m.save(i, true);
    String csv = Csv.inventory(m);
    assertTrue(csv.contains("'=HYPERLINK"));
    Model n = new Model();
    Csv.addItems(n, csv);
    assertEquals(i.name, n.item("M").name);
  }

  @Test
  public void csvRefusesLegacyInUseWithoutCustody() {
    String csv = Csv.HEADER + "T,T,Hammer,Tool,In use,1,0,Lab,Note\n";
    rejects(() -> Csv.addItems(new Model(), csv));
  }

  @Test
  public void fullEncryptedBackupRoundtripAndWrongPassword() throws Exception {
    Model m = new Model();
    m.save(material("M", 3), true);
    m.issue("M", 1, "Student", due(), "", false);
    char[] p = "twelve character passphrase".toCharArray();
    byte[] plain = Model.JSON.toJson(m).getBytes(StandardCharsets.UTF_8),
        b = Crypto.backup(plain, p);
    assertArrayEquals(plain, Crypto.restore(b, p));
    assertFalse(new String(b, StandardCharsets.UTF_8).contains("Student"));
    try {
      Crypto.restore(b, "wrong".toCharArray());
      fail();
    } catch (javax.crypto.AEADBadTagException expected) {
    }
    b[b.length - 1] ^= 1;
    try {
      Crypto.restore(b, p);
      fail();
    } catch (javax.crypto.AEADBadTagException expected) {
    }
  }

  @Test
  public void localCipherUsesFreshNonceAndDetectsTamper() throws Exception {
    SecretKeySpec key = new SecretKeySpec(new byte[32], "AES");
    byte[] data = "inventory".getBytes(StandardCharsets.UTF_8),
        a = Crypto.seal(data, key),
        b = Crypto.seal(data, key);
    assertFalse(java.util.Arrays.equals(a, b));
    assertArrayEquals(data, Crypto.open(a, key));
    a[15] ^= 1;
    try {
      Crypto.open(a, key);
      fail();
    } catch (javax.crypto.AEADBadTagException expected) {
    }
  }

  @Test
  public void shortBackupPassphraseBlocked() throws Exception {
    try {
      Crypto.backup(new byte[1], "short".toCharArray());
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test
  public void csvNormalizesWindowsMultilineNotes() {
    Model m = new Model();
    Csv.addItems(m, Csv.HEADER + "M,M,Ties,Material,Available,10,1,Lab,\"line 1\r\nline 2\"\r\n");
    assertEquals("line 1\nline 2", m.item("M").notes);
  }

  @Test
  public void backupIdentifierMatchingAgreesWithScannerForUnicode() {
    Model m = new Model();
    Model.Item one = material("İ", 1);
    m.save(one, true);
    Model.Item second = material("i", 1);
    second.code = "second-code";
    rejects(() -> m.save(second, true));
    m.items.add(second);
    rejects(m::validate);
  }
}
