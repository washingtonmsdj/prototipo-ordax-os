import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "services" / "public-identity" / "supabase_sync.py"

spec = importlib.util.spec_from_file_location("ordax_supabase_sync_test", MODULE)
sync_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = sync_module
spec.loader.exec_module(sync_module)


class FakeTransport:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def request(self, method, url, headers, body):
        self.requests.append((method, url, headers, json.loads(body.decode("utf-8"))))
        status, payload = self.replies.pop(0)
        return status, json.dumps(payload).encode("utf-8")


class SupabaseSyncProviderV2Tests(unittest.TestCase):
    def provider(self, replies):
        transport = FakeTransport(replies)
        provider = sync_module.SupabaseSyncProvider(
            "https://example.supabase.co",
            "sb_publishable_test",
            transport=transport,
        )
        return provider, transport

    def test_atomic_snapshot_maps_provider_rows_to_ordax_objects(self):
        provider, transport = self.provider([
            (200, {
                "cursor": 17,
                "objects": [{
                    "stable_object_id": "preferences/surface",
                    "data_class": "preferences",
                    "object_schema_version": 1,
                    "resolver_version": 1,
                    "server_revision": 4,
                    "tombstone": False,
                    "payload": {"accessibility.contrast": "high"},
                    "updated_at": "2026-09-25T00:00:00Z",
                }],
            }),
        ])
        result = provider.snapshot("access-token", limit=200)
        self.assertEqual(result["cursor"], 17)
        self.assertEqual(result["objects"][0]["objectId"], "preferences/surface")
        self.assertTrue(transport.requests[0][1].endswith("/rest/v1/rpc/ordax_sync_snapshot_v1"))
        self.assertEqual(transport.requests[0][3], {"p_limit": 200})

    def test_incremental_pull_requires_monotonic_change_cursor(self):
        provider, transport = self.provider([
            (200, [{
                "change_cursor": 18,
                "stable_object_id": "workspace/portable",
                "data_class": "workspace-metadata",
                "object_schema_version": 1,
                "resolver_version": 1,
                "server_revision": 3,
                "tombstone": False,
                "payload": {"activeAreaId": "area-1", "areas": []},
                "changed_at": "2026-09-25T00:00:01Z",
            }]),
        ])
        result = provider.pull_changes("access-token", after_cursor=17, limit=50)
        self.assertEqual(result["afterCursor"], 17)
        self.assertEqual(result["nextCursor"], 18)
        self.assertEqual(result["changes"][0]["cursor"], 18)
        self.assertTrue(transport.requests[0][1].endswith("/rest/v1/rpc/ordax_pull_sync_changes_v1"))

    def test_mutation_uses_v2_and_returns_change_cursor(self):
        provider, transport = self.provider([
            (200, [{
                "sync_object_id": "00000000-0000-0000-0000-000000000001",
                "server_revision": 2,
                "tombstone": False,
                "applied": True,
                "conflict": False,
                "change_cursor": 19,
            }]),
        ])
        result = provider.apply_mutation("access-token", {
            "idempotencyKey": "mutation:abcdefgh",
            "dataClass": "preferences",
            "objectId": "preferences/surface",
            "objectSchemaVersion": 1,
            "resolverVersion": 1,
            "baseServerRevision": 1,
            "operation": "upsert",
            "payload": {"accessibility.contrast": "standard"},
        })
        self.assertEqual(result.server_revision, 2)
        self.assertEqual(result.change_cursor, 19)
        self.assertTrue(transport.requests[0][1].endswith("/rest/v1/rpc/ordax_apply_sync_mutation_v2"))


if __name__ == "__main__":
    unittest.main()
