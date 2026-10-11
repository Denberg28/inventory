import argparse
from pathlib import Path
from inventory.selftest import run
from inventory.store import default_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline drone laboratory inventory")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--self-test-file", type=Path)
    args = parser.parse_args(argv)
    if args.self_test_file and not args.self_test:
        parser.error("--self-test-file requires --self-test")
    if args.self_test_file:
        live = default_path()
        protected = {live.resolve(), live.with_suffix(".lock").resolve()}
        protected.update(
            Path(str(live) + s).resolve() for s in ("-wal", "-shm", "-journal")
        )
        if args.self_test_file.resolve() in protected:
            parser.error("Probe output cannot target the database namespace")
    if args.self_test:
        result = run()
        if args.self_test_file:
            with args.self_test_file.open("x", encoding="utf-8") as f:
                f.write(result)
        else:
            print(result)
        return 0
    from inventory.ui import main as launch

    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
