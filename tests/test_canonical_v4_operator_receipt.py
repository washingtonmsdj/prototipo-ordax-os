from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "release-signing" / "operator_receipt.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ordax_operator_receipt", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipt = load_module()


class CanonicalV4OperatorReceiptTests(unittest.TestCase):
    def test_system_receipt_binds_exact_commit_hash_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "system.erofs"
            artifact.write_bytes(b"system-bytes")
            result = receipt.build_receipt(
                "system",
                "0123456789abcdef0123456789abcdef01234567",
                {"system.erofs": artifact},
            )

        self.assertEqual(
            result["$schema"],
            "prototype-ordax.canonical-v4-operator-artifact/1",
        )
        self.assertEqual(result["kind"], "system")
        self.assertEqual(
            result["source_commit"],
            "0123456789abcdef0123456789abcdef01234567",
        )
        self.assertEqual([x["name"] for x in result["files"]], ["system.erofs"])
        self.assertEqual(result["files"][0]["size"], len(b"system-bytes"))
        self.assertEqual(len(result["files"][0]["sha256"]), 64)
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["signing_performed"])
        self.assertFalse(result["physical_write_authorized"])
        self.assertFalse(result["physical_write_performed"])

    def test_local_ai_requires_runtime_and_source_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "local-ai-runtime.erofs"
            runtime.write_bytes(b"ai")
            with self.assertRaises(ValueError):
                receipt.build_receipt(
                    "local-ai",
                    "0123456789abcdef0123456789abcdef01234567",
                    {"local-ai-runtime.erofs": runtime},
                )

    def test_wrong_or_uppercase_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "system.erofs"
            artifact.write_bytes(b"x")
            for source_commit in (
                "ABCDEF0123456789abcdef0123456789abcdef01",
                "not-a-commit",
            ):
                with self.subTest(source_commit=source_commit):
                    with self.assertRaises(ValueError):
                        receipt.build_receipt(
                            "system",
                            source_commit,
                            {"system.erofs": artifact},
                        )

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "real.erofs"
            target.write_bytes(b"x")
            link = root / "system.erofs"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaises(ValueError):
                receipt.build_receipt(
                    "system",
                    "0123456789abcdef0123456789abcdef01234567",
                    {"system.erofs": link},
                )


if __name__ == "__main__":
    unittest.main()
