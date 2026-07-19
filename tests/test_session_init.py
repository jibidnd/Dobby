from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SessionInitTests(unittest.TestCase):
    def test_runs_with_an_empty_private_state_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "DOBBY_HOME": temp}
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks" / "session_init.py")],
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dobby  ·  session starting", result.stdout)


if __name__ == "__main__":
    unittest.main()
