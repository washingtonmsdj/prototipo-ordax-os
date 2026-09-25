import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryConnectionsTests(unittest.TestCase):
    def test_selected_repository_projection(self):
        completed = subprocess.run(
            ["node", "--test", "tests/test_repository_connections.mjs"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if completed.returncode != 0:
            self.fail(
                "Repository connection contract failed:\n"
                f"{completed.stdout}\n{completed.stderr}"
            )
        self.assertIn("REPOSITORY_CONNECTIONS=PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
