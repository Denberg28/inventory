"""Small explicit source gates; not a general vulnerability audit."""

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inventory import __version__, SCHEMA_VERSION
from inventory.selftest import run


def main():
    if sys.flags.optimize:
        raise SystemExit("Do not disable verification assertions with -O.")
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    if (
        metadata["project"]["version"] != __version__
        or SCHEMA_VERSION != 2
        or metadata["project"]["dependencies"]
    ):
        raise SystemExit("Version/schema/runtime dependencies disagree.")
    forbidden = {
        "requests",
        "httpx",
        "urllib",
        "socket",
        "subprocess",
        "pickle",
        "eval",
        "exec",
    }
    runtime = list((ROOT / "inventory").glob("*.py")) + [ROOT / "run_inventory.py"]
    for p in runtime:
        source = p.read_text()
        tree = ast.parse(source, filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = (
                    [x.name for x in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                if any(x.split(".")[0] in forbidden for x in modules):
                    raise SystemExit("Unexpected runtime import: " + str(p))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("eval", "exec")
            ):
                raise SystemExit("Unexpected dynamic execution: " + str(p))
        if re.search(
            r"gh[pousr]_[A-Za-z0-9]{25,}|-----BEGIN .*PRIVATE KEY-----|sk-[A-Za-z0-9]{30,}",
            source,
        ):
            raise SystemExit("Potential embedded secret: " + str(p))
    for name in (
        "README.md",
        "AGENTS.md",
        "CHANGELOG.md",
        "docs/SPEC.md",
        "docs/TESTING.md",
        "docs/VERIFICATION.md",
        "docs/RECOVERY.md",
    ):
        if not (ROOT / name).is_file():
            raise SystemExit("Missing " + name)
    print(
        "PASS: syntax, version/schema, runtime network/dynamic execution and limited secret-pattern checks"
    )
    print(run())


if __name__ == "__main__":
    main()
