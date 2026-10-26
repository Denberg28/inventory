package ph.dronelab.inventory;

import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;
import javax.crypto.*;
import javax.crypto.spec.*;

public final class Crypto {
  static final byte[] MAGIC = "DLINV1".getBytes(StandardCharsets.US_ASCII);
  static final int ITERATIONS = 210000;

  static byte[] random(int n) {
    byte[] b = new byte[n];
    new SecureRandom().nextBytes(b);
    return b;
  }

  static SecretKey derive(char[] password, byte[] salt) throws Exception {
    PBEKeySpec spec = new PBEKeySpec(password, salt, ITERATIONS, 256);
    try {
      return new SecretKeySpec(
          SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded(),
          "AES");
    } finally {
      spec.clearPassword();
    }
  }

  public static byte[] seal(byte[] plain, SecretKey key) throws Exception {
    Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
    c.init(Cipher.ENCRYPT_MODE, key);
    c.updateAAD(MAGIC);
    byte[] encrypted = c.doFinal(plain),
        iv = c.getIV(),
        out = new byte[iv.length + encrypted.length];
    System.arraycopy(iv, 0, out, 0, iv.length);
    System.arraycopy(encrypted, 0, out, iv.length, encrypted.length);
    return out;
  }

  public static byte[] open(byte[] data, SecretKey key) throws Exception {
    Model.check(
        data.length >= 28 && data.length <= 24 * 1024 * 1024, "Invalid encrypted file size");
    Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
    c.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, Arrays.copyOf(data, 12)));
    c.updateAAD(MAGIC);
    return c.doFinal(data, 12, data.length - 12);
  }

  public static byte[] backup(byte[] plain, char[] password) throws Exception {
    Model.check(password.length >= 12, "Use a backup passphrase of at least 12 characters");
    byte[] salt = random(16),
        enc = seal(plain, derive(password, salt)),
        out = new byte[22 + enc.length];
    System.arraycopy(MAGIC, 0, out, 0, 6);
    System.arraycopy(salt, 0, out, 6, 16);
    System.arraycopy(enc, 0, out, 22, enc.length);
    return out;
  }

  public static byte[] restore(byte[] data, char[] password) throws Exception {
    Model.check(
        data.length >= 50
            && data.length <= 24 * 1024 * 1024
            && Arrays.equals(MAGIC, Arrays.copyOf(data, 6)),
        "Not an Inventory encrypted backup");
    return open(
        Arrays.copyOfRange(data, 22, data.length),
        derive(password, Arrays.copyOfRange(data, 6, 22)));
  }
}
