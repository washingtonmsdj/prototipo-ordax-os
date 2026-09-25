import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProfilePackCatalogTest(unittest.TestCase):
    def test_node_contract(self):
        completed = subprocess.run(
            ["node", "--test", "tests/test_profile_pack_catalog.mjs"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if completed.returncode != 0:
            self.fail(f"Profile Pack catalog contract failed:\n{completed.stdout}\n{completed.stderr}")
        self.assertIn("PROFILE_PACK_CATALOG=PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
