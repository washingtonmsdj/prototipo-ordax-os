import importlib.util
import json
import stat
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "system" / "diagnostics" / "mvp_surface_smoke.py"
WRAPPER = ROOT / "system" / "surface" / "bin" / "ordax-mvp-smoke"

spec = importlib.util.spec_from_file_location("ordax_mvp_surface_smoke", PROOF)
proof = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proof)


class SmokeHandler(BaseHTTPRequestHandler):
    expected_authority = ""

    def log_message(self, _format, *_args):
        return

    def _send_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("Host") != self.expected_authority:
            self.send_response(403)
            self.end_headers()
            return
        if self.path == "/composition/native/index.html":
            body = b"<!doctype html><title>OrdaX</title>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/__ordax/native/metrics":
            self._send_json({
                "uptimeSeconds": 123,
                "memoryTotalBytes": 1000,
                "memoryAvailableBytes": 400,
                "userStorageTotalBytes": 5000,
                "userStorageFreeBytes": 3000,
            })
            return
        if self.path == "/__ordax/native/network-status":
            self._send_json({
                "interfaces": [
                    {"name": "wlan0", "kind": "wifi", "state": "connected", "signalDbm": -54},
                    {"name": "eth0", "kind": "ethernet", "state": "disconnected", "signalDbm": None},
                ]
            })
            return
        if self.path == "/__ordax/native/power-status":
            self._send_json({
                "battery": {"percent": 71, "state": "discharging"},
                "externalPower": False,
            })
            return
        if self.path == "/__ordax/native/files?path=%2F":
            self._send_json({
                "path": "/",
                "entries": [
                    {"name": "Documento secreto.txt", "kind": "file", "size": 12, "modifiedAt": 1234},
                    {"name": "Projetos", "kind": "directory", "size": 0, "modifiedAt": 1235},
                ],
            })
            return
        if self.path == "/__ordax/native/update":
            self._send_json({
                "sourceSha": "b" * 40,
                "deliveryNumber": 42,
                "runtimeSurfaceSha": "b" * 40,
                "targetSha": "",
                "status": "running",
                "phase": "idle",
                "applyMode": "none",
                "attemptId": "",
                "bootRefreshRequired": False,
                "baseUpdatePhase": "none",
                "baseUpdateSha": "",
                "checkedAt": "2026-09-20T12:00:00Z",
                "lastAppliedSha": "b" * 40,
                "lastAppliedAt": "2026-09-20T11:59:00Z",
                "lastApplyDurationSeconds": 1,
                "lastStageDurationSeconds": 2,
                "rejectedSha": "",
                "lastError": "",
                "healthToken": "SECRET-HEALTH-TOKEN",
            })
            return
        if self.path == "/__ordax/native/update-history":
            self._send_json({
                "releases": [],
                "applications": [
                    {
                        "deliveryNumber": 42,
                        "sourceSha": "a" * 40,
                        "appliedAt": "2026-09-20T12:00:00Z",
                        "applyMode": "reload",
                        "result": "applied",
                        "applyDurationSeconds": 1,
                        "stageDurationSeconds": 2,
                    }
                ],
            })
            return
        self.send_response(404)
        self.end_headers()


class MvpSurfaceSmokeTests(unittest.TestCase):
    def _source_tree(self, root: Path):
        for relative in proof.REQUIRED_SOURCE_FILES:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"// {relative}\n", encoding="utf-8")

    def test_collect_probes_read_only_mvp_runtime_without_leaking_names(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), SmokeHandler)
        SmokeHandler.expected_authority = f"127.0.0.1:{server.server_port}"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source"
                run = root / "run"
                proc = root / "proc"
                self._source_tree(source)
                run.mkdir(parents=True)
                (run / "host.log").write_text("surface healthy\n", encoding="utf-8")
                boot = proc / "sys/kernel/random"
                boot.mkdir(parents=True)
                (boot / "boot_id").write_text("boot-123\n", encoding="ascii")
                report = proof.collect(
                    "unit",
                    host="127.0.0.1",
                    port=server.server_port,
                    timeout=1.0,
                    source_root=source,
                    run_root=run,
                    proc_root=proc,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(report["summary"]["fail"], 0, report["checks"])
        self.assertEqual(report["observed"]["file_space_root"]["entry_count"], 2)
        self.assertEqual(report["observed"]["network_status"]["interface_count"], 2)
        self.assertEqual(report["observed"]["update_status"]["status"], "running")
        self.assertEqual(report["observed"]["update_status"]["phase"], "idle")
        self.assertEqual(report["observed"]["update_status"]["delivery_number"], 42)
        self.assertTrue(report["observed"]["update_status"]["runtime_surface_matches_source"])
        self.assertTrue(report["observed"]["update_status"]["health_token_present"])
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("Documento secreto.txt", serialized)
        self.assertNotIn("wlan0", serialized)
        self.assertNotIn("eth0", serialized)
        self.assertNotIn("SECRET-HEALTH-TOKEN", serialized)
        self.assertNotIn("b" * 40, serialized)

    def test_files_validator_rejects_traversal_and_never_returns_entry_names(self):
        with self.assertRaises(ValueError):
            proof.validate_files({"path": "/../etc", "entries": []})
        summary = proof.validate_files({
            "path": "/",
            "entries": [{"name": "private.txt", "kind": "file", "size": 1, "modifiedAt": 2}],
        })
        self.assertEqual(summary["entry_count"], 1)
        self.assertNotIn("private.txt", json.dumps(summary))

    def test_metrics_validator_rejects_impossible_values(self):
        with self.assertRaises(ValueError):
            proof.validate_metrics({
                "uptimeSeconds": 1,
                "memoryTotalBytes": 10,
                "memoryAvailableBytes": 11,
                "userStorageTotalBytes": 20,
                "userStorageFreeBytes": 10,
            })

    def test_update_status_validator_is_bounded_and_redacts_runtime_secrets(self):
        payload = {
            "sourceSha": "c" * 40,
            "deliveryNumber": 7,
            "runtimeSurfaceSha": "c" * 40,
            "status": "running",
            "phase": "idle",
            "applyMode": "none",
            "bootRefreshRequired": False,
            "baseUpdatePhase": "none",
            "lastAppliedSha": "c" * 40,
            "lastApplyDurationSeconds": 3,
            "lastStageDurationSeconds": 2,
            "lastError": "private diagnostic detail",
            "healthToken": "very-secret-token",
        }
        summary = proof.validate_update_status(payload)
        self.assertEqual(summary["delivery_number"], 7)
        self.assertTrue(summary["runtime_surface_matches_source"])
        self.assertTrue(summary["has_last_error"])
        self.assertTrue(summary["health_token_present"])
        serialized = json.dumps(summary)
        self.assertNotIn("very-secret-token", serialized)
        self.assertNotIn("private diagnostic detail", serialized)
        self.assertNotIn("c" * 40, serialized)

        bad_phase = dict(payload, phase="teleporting")
        with self.assertRaises(ValueError):
            proof.validate_update_status(bad_phase)
        bad_delivery = dict(payload, deliveryNumber=-1)
        with self.assertRaises(ValueError):
            proof.validate_update_status(bad_delivery)
        bad_duration = dict(payload, lastApplyDurationSeconds=3601)
        with self.assertRaises(ValueError):
            proof.validate_update_status(bad_duration)

    def test_source_snapshot_hashes_required_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source_tree(root)
            snapshot, checks = proof.source_snapshot(root)
        self.assertEqual(len(snapshot["files"]), len(proof.REQUIRED_SOURCE_FILES))
        self.assertTrue(all(item["status"] == "pass" for item in checks))
        self.assertTrue(all(len(item["sha256"]) == 64 for item in snapshot["files"].values()))

    def test_wrapper_uses_existing_webkit_runtime_and_no_install(self):
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("alpine-v3.22-cage-webkitgtk-v1", text)
        self.assertIn("/srv/ordax-system/diagnostics/mvp_surface_smoke.py", text)
        self.assertIn('busybox chroot "$RUNTIME_ROOT"', text)
        self.assertNotIn("apk add", text)
        self.assertNotIn("curl ", text)
        self.assertEqual(stat.S_IMODE(WRAPPER.stat().st_mode), 0o755)

    def test_collector_has_no_mutating_http_methods(self):
        text = PROOF.read_text(encoding="utf-8")
        self.assertIn('putrequest("GET"', text)
        self.assertIn('"/__ordax/native/update"', text)
        for method in ('putrequest("POST"', 'putrequest("PUT"', 'putrequest("PATCH"', 'putrequest("DELETE"'):
            self.assertNotIn(method, text)


if __name__ == "__main__":
    unittest.main()
