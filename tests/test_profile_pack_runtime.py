import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProfilePackRuntimeTest(unittest.TestCase):
    def test_node_contract_and_surface_catalog(self):
        subprocess.run(
            ["node", "--test", "tests/test_profile_pack_runtime.mjs"],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
