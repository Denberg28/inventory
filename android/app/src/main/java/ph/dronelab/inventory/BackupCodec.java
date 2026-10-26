package ph.dronelab.inventory;

import com.google.gson.*;
import com.google.gson.stream.JsonReader;
import java.io.StringReader;
import java.nio.charset.*;
import java.util.*;

/** Reject missing, unknown or mistyped fields before Gson can fill Java defaults. */
public final class BackupCodec {
  static void fields(JsonObject o, String... names) {
    Model.check(
        o.keySet().equals(new HashSet<>(Arrays.asList(names))),
        "Backup fields are missing or unsupported");
  }

  static void string(JsonObject o, String name) {
    JsonElement v = o.get(name);
    Model.check(
        v != null && v.isJsonPrimitive() && v.getAsJsonPrimitive().isString(),
        "Invalid backup text: " + name);
  }

  static void integer(JsonObject o, String name) {
    JsonElement v = o.get(name);
    Model.check(
        v != null
            && v.isJsonPrimitive()
            && v.getAsJsonPrimitive().isNumber()
            && v.toString().matches("0|[1-9][0-9]{0,9}"),
        "Invalid backup number: " + name);
    try {
      v.getAsBigDecimal().intValueExact();
    } catch (Exception e) {
      throw new IllegalArgumentException("Backup integer exceeds supported range");
    }
  }

  static JsonArray array(JsonObject o, String name, int max) {
    JsonElement v = o.get(name);
    Model.check(
        v != null && v.isJsonArray() && v.getAsJsonArray().size() <= max,
        "Invalid backup collection: " + name);
    return v.getAsJsonArray();
  }

  static JsonObject object(JsonElement e) {
    Model.check(e != null && e.isJsonObject(), "Invalid backup record");
    return e.getAsJsonObject();
  }

  public static Model decode(byte[] bytes) {
    Model.check(bytes.length <= 16 * 1024 * 1024, "Backup data exceeds 16 MB");
    String json;
    try {
      json =
          StandardCharsets.UTF_8
              .newDecoder()
              .onMalformedInput(CodingErrorAction.REPORT)
              .decode(java.nio.ByteBuffer.wrap(bytes))
              .toString();
    } catch (CharacterCodingException e) {
      throw new IllegalArgumentException("Backup text is not valid UTF-8");
    }
    JsonReader reader = new JsonReader(new StringReader(json));
    reader.setStrictness(Strictness.STRICT);
    JsonObject root = object(JsonParser.parseReader(reader));
    try {
      Model.check(
          reader.peek() == com.google.gson.stream.JsonToken.END_DOCUMENT,
          "Unexpected data after backup");
    } catch (java.io.IOException e) {
      throw new IllegalArgumentException("Invalid backup JSON");
    }
    fields(root, "schema", "items", "loans", "events");
    integer(root, "schema");
    for (JsonElement e : array(root, "items", 10000)) {
      JsonObject o = object(e);
      fields(
          o,
          "id",
          "code",
          "name",
          "category",
          "location",
          "notes",
          "status",
          "total",
          "minimum",
          "archived");
      for (String n :
          new String[] {"id", "code", "name", "category", "location", "notes", "status"})
        string(o, n);
      integer(o, "total");
      integer(o, "minimum");
      Model.check(
          o.get("archived").isJsonPrimitive() && o.getAsJsonPrimitive("archived").isBoolean(),
          "Invalid archived flag");
    }
    for (JsonElement e : array(root, "loans", 50000)) {
      JsonObject o = object(e);
      fields(o, "id", "itemId", "borrower", "due", "issued", "note", "quantity", "returned");
      for (String n : new String[] {"id", "itemId", "borrower", "due", "issued", "note"})
        string(o, n);
      integer(o, "quantity");
      integer(o, "returned");
    }
    for (JsonElement e : array(root, "events", 100000)) {
      JsonObject o = object(e);
      fields(o, "id", "time", "itemId", "action", "detail");
      for (String n : new String[] {"id", "time", "itemId", "action", "detail"}) string(o, n);
    }
    Model m = Model.JSON.fromJson(root, Model.class);
    m.validate();
    return m;
  }
}
