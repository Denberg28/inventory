"""OS-backed single workstation lock, released even after process termination."""

import os


class InstanceLock:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open("a+b")
        try:
            self.file.seek(0)
            if os.name == "nt":
                import msvcrt

                if path.stat().st_size == 0:
                    self.file.write(b"0")
                    self.file.flush()
                    self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise ValueError("Inventory is already open for this database.") from exc

    def close(self):
        if not self.file.closed:
            self.file.close()
