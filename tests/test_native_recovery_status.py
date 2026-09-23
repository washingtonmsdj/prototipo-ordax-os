import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "system/surface/runtime/native_host_server.py"

spec = importlib.util.spec_from_file_location("ordax_native_recovery_test", HOST)
host = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(host)


class NativeRecoveryStatusTests(unittest.TestCase):
    def test_reads_current_known_good_candidate_and_verified_recovery_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            activation = state / "ordax" / "portable-release"
            activation.mkdir(parents=True)
            current = "a" * 40
            known = "b" * 40
            candidate = "c" * 40
            (activation / "current").write_text(current + "\n", encoding="utf-8")
            (activation / "known-good").write_text(known + "\n", encoding="utf-8")
            (activation / "candidate").write_text(candidate + "\n", encoding="utf-8")
            (activation / "activation-transaction.json").write_text("{}\n", encoding="utf-8")

            esp = root / "esp"
            entry = esp / "loader" / "entries" / "ordax-portable-recovery.conf"
            entry.parent.mkdir(parents=True)
            entry.write_text(
                "title OrdaX Recovery\n"
                "linux /ordax/vmlinuz\n"
                "initrd /ordax/initrd.gz\n"
                "options rdinit=/sbin/ordax-portable-init ordax.mode=recovery\n",
                encoding="utf-8",
            )

            result = host.read_recovery_status(
                str(state),
                str(esp),
                {
                    "ORDAX_STABLE_LAYOUT": "portable-v2",
                    "ORDAX_SOURCE_SHA": current,
                    "ORDAX_BOOT_SLOT": "current",
                },
            )
            self.assertEqual(result["runningSourceSha"], current)
            self.assertEqual(result["currentSha"], current)
            self.assertEqual(result["knownGoodSha"], known)
            self.assertEqual(result["candidateSha"], candidate)
            self.assertTrue(result["transactionPresent"])
            self.assertEqual(result["recoveryEntryStatus"], "verified")
            self.assertFalse(result["automaticNetwork"])
            self.assertFalse(result["automaticMutation"])

    def test_missing_optional_markers_are_observed_not_invented(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            activation = state / "ordax" / "portable-release"
            activation.mkdir(parents=True)
            current = "d" * 40
            (activation / "current").write_text(current + "\n", encoding="utf-8")

            result = host.read_recovery_status(
                str(state),
                str(root / "missing-esp"),
                {
                    "ORDAX_STABLE_LAYOUT": "portable-v2",
                    "ORDAX_SOURCE_SHA": current,
                    "ORDAX_BOOT_SLOT": "unexpected",
                },
            )
            self.assertEqual(result["bootSlot"], "unknown")
            self.assertIsNone(result["knownGoodSha"])
            self.assertIsNone(result["candidateSha"])
            self.assertFalse(result["transactionPresent"])
            self.assertEqual(result["recoveryEntryStatus"], "unavailable")

    def test_non_portable_runtime_is_not_misrepresented(self):
        with self.assertRaises(ValueError):
            host.read_recovery_status(
                "/state",
                "/ordax-esp",
                {
                    "ORDAX_STABLE_LAYOUT": "owner-development",
                    "ORDAX_SOURCE_SHA": "a" * 40,
                },
            )


if __name__ == "__main__":
    unittest.main()
