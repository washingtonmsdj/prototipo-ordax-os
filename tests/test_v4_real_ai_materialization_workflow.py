from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/local-ai-runtime-candidate.yml"
AGENT_TEST = ROOT / "bootstrap/release-acquisition/main_test.go"


class V4RealAiMaterializationWorkflowTests(unittest.TestCase):
    def test_real_runtime_is_materialized_through_existing_release_agent_owner(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        test_source = AGENT_TEST.read_text(encoding="utf-8")

        self.assertIn("TestMaterializePortableV4WithRealAIRuntimeFromEnv", test_source)
        self.assertIn('os.Getenv("ORDAX_TEST_REAL_LOCAL_AI_RUNTIME")', test_source)
        self.assertIn("materializePortableV4(", test_source)
        self.assertIn("verifyPortableV4Exact(", test_source)
        self.assertIn("AIRuntimeReused", test_source)
        self.assertIn('filepath.Join(root, "current")', test_source)

        self.assertIn("Materialize signed v4 with real local AI runtime bytes", workflow)
        self.assertIn("build-a/local-ai-runtime.erofs", workflow)
        self.assertIn("ORDAX_TEST_REAL_LOCAL_AI_RUNTIME=", workflow)
        self.assertIn("go test -count=1", workflow)
        self.assertIn("PORTABLE_V4_REAL_AI_SIGNED_MATERIALIZATION=PASS", workflow)
        self.assertIn("PORTABLE_V4_REAL_AI_ACTIVATION_ALLOWED=NO", workflow)
        self.assertIn("PHYSICAL_WRITE_AUTHORIZED=NO", workflow)

    def test_proof_does_not_add_a_second_materializer_or_physical_write_path(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        test_source = AGENT_TEST.read_text(encoding="utf-8")
        proof = workflow.split(
            "- name: Materialize signed v4 with real local AI runtime bytes", 1
        )[1].split("- name: Remove unpromoted runtime bytes", 1)[0]

        self.assertNotIn("materialize-portable-v4 --", proof)
        self.assertNotIn("activate-exact", proof)
        self.assertNotIn("wipefs", proof)
        self.assertNotIn("mkfs.", proof)
        self.assertNotIn("/dev/sd", proof)
        self.assertNotIn("os.Symlink(filepath.Join(\"releases\", testCommit), filepath.Join(root, \"current\"))", test_source.split("func TestMaterializePortableV4WithRealAIRuntimeFromEnv", 1)[1].split("func TestVerifyPortableV4ExactRejectsTamperedAIRuntime", 1)[0])


if __name__ == "__main__":
    unittest.main()
