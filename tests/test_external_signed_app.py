import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExternalSignedAppProofTest(unittest.TestCase):
    def test_node_signed_app_proof(self):
        subprocess.run(
            ["node", "--test", "tests/test_external_signed_app.mjs"],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
