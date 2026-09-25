import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProjectsDeviceAgentIntegrationTest(unittest.TestCase):
    def test_node_projects_device_agent_integration(self):
        subprocess.run(
            ["node", "--test", "tests/test_projects_device_agent.mjs"],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
