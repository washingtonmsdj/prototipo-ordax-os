import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "local-ai-hardware-probe" / "probe.py"
SPEC = importlib.util.spec_from_file_location("ordax_local_ai_hardware_probe", MODULE_PATH)
PROBE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PROBE)


class LocalAiHardwareProbeTests(unittest.TestCase):
    def write_fixture(self, root, name, content):
        path = Path(root) / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_x86_64_probe_reports_only_features_common_to_all_processors(self):
        with tempfile.TemporaryDirectory() as root:
            cpuinfo = self.write_fixture(
                root,
                "cpuinfo",
                "processor : 0\nflags : sse4_1 sse4_2 avx avx2 fma bmi1 bmi2 popcnt\n"
                "processor : 1\nflags : sse4_1 sse4_2 avx avx2 fma popcnt\n",
            )
            meminfo = self.write_fixture(
                root,
                "meminfo",
                "MemTotal:       8388608 kB\nMemAvailable:   4194304 kB\n",
            )
            result = PROBE.probe_system(
                machine="AMD64",
                logical_cpus=2,
                cpuinfo_path=cpuinfo,
                meminfo_path=meminfo,
            )

        self.assertEqual(result["$schema"], PROBE.SCHEMA)
        self.assertEqual(result["architecture"], "x86_64")
        self.assertEqual(result["logical_cpus"], 2)
        self.assertTrue(result["runtime_compatible"])
        self.assertEqual(result["start_blockers"], [])
        self.assertEqual(
            result["cpu_features"],
            ["avx", "avx2", "fma", "popcnt", "sse4_1", "sse4_2"],
        )
        self.assertEqual(result["memory"]["total_bytes"], 8388608 * 1024)
        self.assertEqual(result["memory"]["available_bytes"], 4194304 * 1024)
        self.assertTrue(result["benchmark_required_before_tuning"])
        self.assertIsNone(result["tuning_recommendation"])

    def test_non_x86_host_is_objectively_blocked_by_pinned_engine_artifact(self):
        with tempfile.TemporaryDirectory() as root:
            cpuinfo = self.write_fixture(root, "cpuinfo", "processor : 0\nFeatures : asimd\n")
            meminfo = self.write_fixture(root, "meminfo", "MemTotal: 1024 kB\n")
            result = PROBE.probe_system(
                machine="aarch64",
                logical_cpus=1,
                cpuinfo_path=cpuinfo,
                meminfo_path=meminfo,
            )

        self.assertFalse(result["runtime_compatible"])
        self.assertEqual(result["start_blockers"], ["runtime-artifact-architecture-mismatch"])
        self.assertEqual(result["runtime_artifact_platform"], "linux-x86_64")

    def test_probe_does_not_invent_memory_or_cpu_thresholds(self):
        with tempfile.TemporaryDirectory() as root:
            cpuinfo = self.write_fixture(root, "cpuinfo", "processor : 0\nflags : sse4_2\n")
            meminfo = self.write_fixture(root, "meminfo", "MemTotal: 512 kB\n")
            result = PROBE.probe_system(
                machine="x86_64",
                logical_cpus=1,
                cpuinfo_path=cpuinfo,
                meminfo_path=meminfo,
            )

        self.assertTrue(result["runtime_compatible"])
        self.assertEqual(result["start_blockers"], [])
        self.assertIsNone(result["tuning_recommendation"])

    def test_sources_are_bounded(self):
        with tempfile.TemporaryDirectory() as root:
            oversized = Path(root) / "cpuinfo"
            oversized.write_bytes(b"x" * (PROBE.MAX_CPUINFO_BYTES + 1))
            meminfo = self.write_fixture(root, "meminfo", "MemTotal: 1 kB\n")
            with self.assertRaisesRegex(PROBE.HardwareProbeError, "exceeds byte limit"):
                PROBE.probe_system(
                    machine="x86_64",
                    logical_cpus=1,
                    cpuinfo_path=oversized,
                    meminfo_path=meminfo,
                )


if __name__ == "__main__":
    unittest.main()
