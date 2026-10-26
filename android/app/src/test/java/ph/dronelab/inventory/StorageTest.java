package ph.dronelab.inventory;

import static org.junit.Assert.*;

import java.io.*;
import java.nio.file.*;
import javax.crypto.spec.SecretKeySpec;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;

@RunWith(org.robolectric.RobolectricTestRunner.class)
@Config(sdk = 28)
public class StorageTest {
  File dir;
  Storage s;
  SecretKeySpec key = new SecretKeySpec(new byte[32], "AES");

  @Before
  public void setup() throws Exception {
    dir = Files.createTempDirectory("inventory-test-").toFile();
    s = new Storage(dir, key);
    s.load();
  }

  Model.Item tool() {
    Model.Item i = new Model.Item();
    i.id = "T1";
    i.code = "0001";
    i.name = "Tool";
    i.category = "Tool";
    return i;
  }

  @Test
  public void rescheduledPartialLoanPersistsAndRecoveryRetainsOriginalDueDate() throws Exception {
    Model initial = new LoanFollowUpTest().openLoan();
    s.restore(initial);
    Model.Loan loan = initial.loans.get(0);
    String next = java.time.LocalDate.now().plusDays(2).toString();
    s.change(m -> m.reschedule(loan.id, loan.due, next, "Authorized extension"));
    Storage reopened = new Storage(dir, key);
    reopened.load();
    assertEquals(next, reopened.snapshot().loan(loan.id).due);
    assertEquals(5, reopened.snapshot().outstanding("M1"));
    assertEquals(loan.due, reopened.recovery(false).loan(loan.id).due);
    byte[] saved = Files.readAllBytes(s.file.getBaseFile().toPath());
    assertThrows(IllegalArgumentException.class,
        () -> s.change(m -> m.reschedule(loan.id, loan.due, next, "Stale request")));
    assertArrayEquals(saved, Files.readAllBytes(s.file.getBaseFile().toPath()));
  }

  @Test
  public void persistenceAndRollbackOnRejectedOperation() throws Exception {
    s.change(m -> m.save(tool(), true));
    byte[] before = Files.readAllBytes(s.file.getBaseFile().toPath());
    try {
      s.change(
          m -> {
            m.item("T1").name = "Mutated";
            throw new IllegalArgumentException("reject");
          });
      fail();
    } catch (IllegalArgumentException expected) {
    }
    assertArrayEquals(before, Files.readAllBytes(s.file.getBaseFile().toPath()));
    assertEquals("Tool", s.snapshot().item("T1").name);
    Storage reopened = new Storage(dir, key);
    reopened.load();
    assertEquals("Tool", reopened.snapshot().item("T1").name);
  }

  @Test
  public void corruptPrimaryDoesNotInitializeEmptyAndCanRecoverPrevious() throws Exception {
    s.change(m -> m.save(tool(), true));
    s.change(
        m -> {
          Model.Item i = m.copy().item("T1");
          i.name = "Edited";
          m.save(i, false);
        });
    byte[] damaged = Files.readAllBytes(s.file.getBaseFile().toPath());
    damaged[20] ^= 1;
    Files.write(s.file.getBaseFile().toPath(), damaged);
    Storage reopened = new Storage(dir, key);
    try {
      reopened.load();
      fail();
    } catch (Exception expected) {
    }
    assertArrayEquals(damaged, Files.readAllBytes(s.file.getBaseFile().toPath()));
    Model recovery = reopened.recovery(false);
    assertEquals("Tool", recovery.item("T1").name);
    reopened.recover(recovery);
    reopened.load();
    assertEquals("Tool", reopened.snapshot().item("T1").name);
  }

  @Test
  public void restoreRetainsPreRestoreRecovery() throws Exception {
    s.change(m -> m.save(tool(), true));
    s.restore(new Model());
    assertTrue(s.snapshot().items.isEmpty());
    Model old = s.recovery(true);
    assertEquals("T1", old.items.get(0).id);
    s.recover(old);
    assertEquals(1, s.snapshot().items.size());
  }

  @Test
  public void invalidCsvIsAtomicThroughRepository() throws Exception {
    s.change(m -> m.save(tool(), true));
    String invalid =
        Csv.HEADER
            + "M,M,Valid,Material,Available,1,0,Lab,Note\n"
            + "X,X,Bad,Material,Available,-1,0,Lab,Note\n";
    try {
      s.change(m -> Csv.addItems(m, invalid));
      fail();
    } catch (IllegalArgumentException expected) {
    }
    assertEquals(1, s.snapshot().items.size());
    s.load();
    assertEquals(1, s.snapshot().items.size());
  }

  @Test
  public void atomicFileRecoversInterruptedSave() throws Exception {
    s.change(m -> m.save(tool(), true));
    FileOutputStream abandoned = s.file.startWrite();
    abandoned.write(new byte[] {1, 2, 3});
    abandoned.close();
    Storage reopened = new Storage(dir, key);
    reopened.load();
    assertEquals("T1", reopened.snapshot().items.get(0).id);
  }

  @Test
  public void writeFailureDoesNotAdvanceMemory() throws Exception {
    s.change(m -> m.save(tool(), true));
    s.previous.getBaseFile().delete();
    assertTrue(s.previous.getBaseFile().mkdir());
    new File(s.previous.getBaseFile(), "block").createNewFile();
    try {
      s.change(m -> m.archive("T1", true));
      fail();
    } catch (Exception expected) {
    }
    assertFalse(s.snapshot().item("T1").archived);
    Storage reopened = new Storage(dir, key);
    reopened.load();
    assertFalse(reopened.snapshot().item("T1").archived);
  }
}
