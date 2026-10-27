package ph.dronelab.inventory;

import android.content.Context;
import android.security.keystore.*;
import android.util.AtomicFile;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.*;

/** Single worker owns storage; fsync/atomic rename precede a visible successful result. */
public final class Storage {
  final AtomicFile file, previous, preRestore;
  final javax.crypto.SecretKey key;
  Model state;

  public interface Change {
    void apply(Model m) throws Exception;
  }

  public Storage(Context c) throws Exception {
    file = new AtomicFile(new File(c.getFilesDir(), "inventory.enc"));
    previous = new AtomicFile(new File(c.getFilesDir(), "previous.enc"));
    preRestore = new AtomicFile(new File(c.getFilesDir(), "before-restore.enc"));
    KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
    ks.load(null);
    if (!ks.containsAlias("inventory-v1")) {
      Model.check(
          !hasStoredData(), "Encryption key is missing. Restore your external backup.");
      KeyGenerator gen = KeyGenerator.getInstance("AES", "AndroidKeyStore");
      gen.init(
          new KeyGenParameterSpec.Builder(
                  "inventory-v1", KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
              .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
              .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
              .setKeySize(256)
              .build());
      gen.generateKey();
    }
    key = (javax.crypto.SecretKey) ks.getKey("inventory-v1", null);
  }

  Storage(File directory, javax.crypto.SecretKey testKey) {
    file = new AtomicFile(new File(directory, "inventory.enc"));
    previous = new AtomicFile(new File(directory, "previous.enc"));
    preRestore = new AtomicFile(new File(directory, "before-restore.enc"));
    key = testKey;
  }

  static byte[] bytes(InputStream in, int max) throws Exception {
    try (InputStream stream = in;
        ByteArrayOutputStream out = new ByteArrayOutputStream()) {
      Model.check(stream != null, "Unable to open file");
      byte[] buf = new byte[8192];
      int n;
      while ((n = stream.read(buf)) != -1) {
        Model.check(out.size() + n <= max, "File is too large");
        out.write(buf, 0, n);
      }
      return out.toByteArray();
    }
  }

  public static Model decode(byte[] bytes) {
    return BackupCodec.decode(bytes);
  }

  Model read(AtomicFile f) throws Exception {
    return decode(Crypto.open(bytes(f.openRead(), 24 * 1024 * 1024), key));
  }

  public void load() throws Exception {
    if (committedFileExists(file)) {
      state = read(file);
    } else {
      // A missing primary is not a new installation when a recovery copy survives.
      // Opening an empty model would overwrite that copy on the next mutation.
      Model.check(!hasStoredData(),
          "Inventory file is missing. Recover previous save or restore an encrypted backup.");
      state = new Model();
    }
  }

  static boolean committedFileExists(AtomicFile f) {
    return f.getBaseFile().exists() || new File(f.getBaseFile() + ".bak").exists();
  }

  boolean hasStoredData() {
    return committedFileExists(file)
        || committedFileExists(previous)
        || committedFileExists(preRestore);
  }

  static void write(AtomicFile f, byte[] data) throws Exception {
    FileOutputStream out = null;
    try {
      out = f.startWrite();
      out.write(data);
      out.getFD().sync();
      f.finishWrite(out);
      Model.check(
          java.util.Arrays.equals(data, bytes(f.openRead(), 24 * 1024 * 1024)),
          "Saved file could not be verified. Retry after checking device storage.");
    } catch (Exception e) {
      if (out != null) f.failWrite(out);
      throw e;
    }
  }

  byte[] encode(Model m) throws Exception {
    byte[] plain = Model.JSON.toJson(m).getBytes(StandardCharsets.UTF_8);
    Model.check(
        plain.length <= 16 * 1024 * 1024,
        "Data limit reached; export and start a new inventory on another installation");
    return Crypto.seal(plain, key);
  }

  public Model snapshot() {
    return state.copy();
  }

  public void change(Change change) throws Exception {
    Model next = state.copy();
    change.apply(next);
    next.validate();
    byte[] enc = encode(next);
    write(previous, encode(state));
    write(file, enc);
    state = next;
  }

  public void restore(Model replacement) throws Exception {
    replacement.validate();
    byte[] enc = encode(replacement);
    if (state != null) write(preRestore, encode(state));
    write(file, enc);
    state = replacement.copy();
  }

  public Model recovery(boolean beforeRestore) throws Exception {
    return read(beforeRestore ? preRestore : previous);
  }

  public void recover(Model m) throws Exception {
    m.validate();
    write(file, encode(m));
    state = m.copy();
  }
}
