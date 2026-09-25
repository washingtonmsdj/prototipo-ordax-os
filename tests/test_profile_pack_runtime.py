from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProfilePackRuntimeTests(unittest.TestCase):
    def test_developer_internal_activation_contract(self) -> None:
        result = subprocess.run(
            ["node", "tests/test_profile_pack_runtime.mjs"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("PROFILE_PACK_RUNTIME=PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
