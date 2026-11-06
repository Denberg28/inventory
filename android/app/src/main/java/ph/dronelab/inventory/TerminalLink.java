package ph.dronelab.inventory;

import android.annotation.SuppressLint;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import android.os.Handler;
import android.os.Looper;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

/** One bonded RFCOMM peer, bounded frames, latest-state-only output, explicit reconnect. */
@SuppressLint("MissingPermission") // Caller checks CONNECT before device selection.
public final class TerminalLink implements AutoCloseable {
  public interface Listener {
    void status(String status);
    void request(String action);
  }
  private final Handler main = new Handler(Looper.getMainLooper());
  private final Listener listener;
  private final ScheduledExecutorService timer = Executors.newScheduledThreadPool(2);
  private final AtomicReference<String> latest = new AtomicReference<>();
  private volatile BluetoothSocket socket;
  private volatile boolean closed = false, ready = false;
  private volatile long received = System.nanoTime();
  private long lastRequest = 0;
  private final String session = UUID.randomUUID().toString();
  private final TerminalProtocol protocol = new TerminalProtocol(session);

  public TerminalLink(Listener listener) { this.listener = listener; }
  public String session() { return session; }
  private void status(String s) { main.post(() -> { if (!closed) listener.status(s); }); }
  public void state(String json) { if (!closed) latest.set(json); }

  public void connect(BluetoothDevice device) {
    status("Connecting…");
    new Thread(() -> {
      try {
        BluetoothSocket candidate = device.createRfcommSocketToServiceRecord(
            UUID.fromString("00001101-0000-1000-8000-00805f9b34fb"));
        synchronized (this) {
          if (closed) { candidate.close(); return; }
          socket = candidate;
        }
        timer.schedule(() -> { if (!ready) fail("Connection timed out; reconnect"); }, 12, TimeUnit.SECONDS);
        timer.scheduleWithFixedDelay(() -> {
          if (System.nanoTime() - received > TimeUnit.SECONDS.toNanos(15)) fail("Terminal timed out; reconnect");
        }, 1, 1, TimeUnit.SECONDS);
        candidate.connect();
        received = System.nanoTime();
        OutputStream out = candidate.getOutputStream();
        timer.scheduleWithFixedDelay(() -> {
          try {
            if (System.nanoTime() - received > TimeUnit.SECONDS.toNanos(15)) {
              fail("Terminal stopped responding; reconnect"); return;
            }
            String line = ready ? latest.getAndSet(null)
                : TerminalProtocol.frame("hello", session).toString();
            if (line == null) line = TerminalProtocol.frame("ping", session).toString();
            byte[] bytes = (line + "\n").getBytes(StandardCharsets.UTF_8);
            if (bytes.length > TerminalProtocol.MAX_LINE + 1) throw new IOException("State frame too large");
            out.write(bytes); out.flush();
          } catch (IOException e) { fail("Bluetooth disconnected; reconnect"); }
        }, 0, 250, TimeUnit.MILLISECONDS);
        ByteArrayOutputStream line = new ByteArrayOutputStream();
        InputStream in = candidate.getInputStream();
        int b;
        while (!closed && (b = in.read()) != -1) {
          if (b == '\n') {
            try {
              String action = protocol.accept(line.toString(StandardCharsets.UTF_8.name()));
              received = System.nanoTime();
              if (action.equals("ready")) {
                if (!ready) { ready = true; status("Bluetooth connected"); }
              } else if (ready && System.nanoTime() - lastRequest > TimeUnit.MILLISECONDS.toNanos(500)) {
                lastRequest = System.nanoTime();
                long acceptedAt = lastRequest;
                main.post(() -> {
                  if (!closed && System.nanoTime() - acceptedAt < TimeUnit.SECONDS.toNanos(2)) listener.request(action);
                });
              }
            } catch (RuntimeException ignored) { /* Malformed/stale input grants no authority. */ }
            line.reset();
          } else if (b != '\r') {
            if (line.size() >= TerminalProtocol.MAX_LINE) throw new IOException("Oversized terminal input");
            line.write(b);
          }
        }
        fail("Bluetooth disconnected; reconnect");
      } catch (IOException | SecurityException | RejectedExecutionException e) { fail("Bluetooth unavailable; pair the terminal and reconnect"); }
    }, "inventory-terminal-reader").start();
  }

  private void fail(String reason) {
    synchronized (this) {
      if (closed) return;
      close();
    }
    main.post(() -> listener.status(reason));
  }

  @Override public synchronized void close() {
    closed = true; ready = false; latest.set(null); timer.shutdownNow();
    if (socket != null) try { socket.close(); } catch (IOException ignored) { }
  }
}
