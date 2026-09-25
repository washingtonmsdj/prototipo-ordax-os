import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SpacesCatalogTest(unittest.TestCase):
    def test_node_spaces_catalog(self):
        subprocess.run(
            ["node", "--test", "tests/test_spaces_catalog.mjs"],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
