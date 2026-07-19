"""Run the small, dependency-free repository verification suite."""
from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    hooks = sorted((ROOT / "hooks").glob("*.py"))
    for hook in hooks:
        py_compile.compile(str(hook), doraise=True)

    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
