import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "system" / "surface" / "runtime"
MODULE_PATH = RUNTIME_DIR / "native_memory_endpoint.py"


def load_module():
    runtime = str(RUNTIME_DIR)
    if runtime not in sys.path:
        sys.path.insert(0, runtime)
    spec = importlib.util.spec_from_file_location("ordax_native_memory_endpoint", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def memory_item(**overrides):
    value = {
        "schema": "ordax.memory/1",
        "id": "mem-1",
        "ownerKind": "device",
        "ownerId": None,
        "scope": "device",
        "kind": "fact",
        "sensitivity": "private",
        "content": "Memória local",
        "provenance": "test-fixture",
        "sourceTimestamp": "2026-09-24T15:00:00.000Z",
        "spaceId": None,
        "projectId": None,
    }
    value.update(overrides)
    return value


def snapshot(*items):
    return json.dumps({
        "$schema": "ordax.memory-snapshot/1",
        "items": list(items),
    }, separators=(",", ":"), sort_keys=True)


def request_body(payload):
    return json.dumps({"payload": payload}, separators=(",", ":")).encode("utf-8")


class NativeMemoryEndpointTests(unittest.TestCase):
    def test_endpoint_round_trips_device_owned_snapshot_and_delete(self):
        endpoint = load_module()
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "memory.json")
            self.assertEqual(endpoint.read_memory_endpoint(path), {"payload": None})

            payload = snapshot(memory_item(id="local"))
            self.assertEqual(
                endpoint.write_memory_endpoint(request_body(payload), path),
                {"ok": True},
            )
            self.assertEqual(endpoint.read_memory_endpoint(path), {"payload": payload})

            self.assertEqual(
                endpoint.write_memory_endpoint(request_body(None), path),
                {"ok": True},
            )
            self.assertEqual(endpoint.read_memory_endpoint(path), {"payload": None})

    def test_endpoint_rejects_invalid_shape_and_invalid_memory_payloads(self):
        endpoint = load_module()
        invalid_bodies = [
            b"",
            b"not-json",
            json.dumps({"payload": snapshot(), "extra": True}).encode("utf-8"),
            request_body(snapshot(memory_item(id="session", scope="session"))),
            request_body(snapshot(memory_item(
                id="fake-account",
                ownerId="synthetic-user",
            ))),
            request_body(snapshot(memory_item(
                id="invalid-account-scope",
                scope="account",
            ))),
            request_body(snapshot(memory_item(
                id="invalid-secret-provenance",
                provenance="ghp_abcdefghijklmnopqrstuvwxyz123456",
            ))),
            request_body(snapshot(memory_item(
                id="invalid-timestamp",
                sourceTimestamp="2026-09-24T15:00:00Z",
            ))),
        ]
        for body in invalid_bodies:
            with self.subTest(body=body[:80]):
                with self.assertRaises(endpoint.MemoryEndpointRequestError):
                    endpoint.parse_memory_write_body(body)

    def test_endpoint_body_limit_is_explicit_and_uses_413(self):
        endpoint = load_module()
        body = b"x" * (endpoint.MAX_MEMORY_REQUEST_BODY_BYTES + 1)
        with self.assertRaises(endpoint.MemoryEndpointRequestError) as raised:
            endpoint.parse_memory_write_body(body)
        self.assertEqual(raised.exception.status_code, 413)

    def test_handler_uses_state_owner_instead_of_reimplementing_file_io(self):
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("read_memory_payload", text)
        self.assertIn("write_memory_payload", text)
        self.assertIn("valid_memory_payload", text)
        self.assertNotIn("os.replace", text)
        self.assertNotIn("open(", text)


if __name__ == "__main__":
    unittest.main()
