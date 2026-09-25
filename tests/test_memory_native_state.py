import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "system" / "surface" / "runtime" / "native_memory_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ordax_native_memory_state", MODULE_PATH)
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


class NativeMemoryStateTests(unittest.TestCase):
    def test_payload_shape_is_bounded_and_rejects_session_state(self):
        memory = load_module()
        self.assertTrue(memory.valid_memory_payload(snapshot()))
        self.assertTrue(memory.valid_memory_payload(snapshot(memory_item())))
        self.assertTrue(memory.valid_memory_payload(snapshot(memory_item(
            id="account-owner",
            ownerKind="account",
            ownerId="user-1",
            scope="account",
        ))))
        self.assertFalse(memory.valid_memory_payload("not-json"))
        self.assertFalse(memory.valid_memory_payload(json.dumps({"$schema": "wrong", "items": []})))
        self.assertFalse(memory.valid_memory_payload(snapshot(memory_item(id="session", scope="session"))))
        self.assertFalse(memory.valid_memory_payload(snapshot(memory_item(
            id="synthetic-device-owner",
            ownerId="fake-user",
        ))))
        self.assertFalse(memory.valid_memory_payload(snapshot(memory_item(
            id="missing-account-owner",
            ownerKind="account",
            ownerId=None,
            scope="account",
        ))))
        self.assertFalse(memory.valid_memory_payload(snapshot(memory_item(
            id="device-account-scope",
            scope="account",
        ))))
        too_many = [memory_item(id=f"item-{index}") for index in range(memory.MAX_MEMORY_ITEMS + 1)]
        self.assertFalse(memory.valid_memory_payload(snapshot(*too_many)))
        self.assertFalse(memory.valid_memory_payload("x" * (memory.MAX_MEMORY_PAYLOAD_BYTES + 1)))

    def test_payload_rejects_noncanonical_or_contract_invalid_items(self):
        memory = load_module()
        invalid = [
            memory_item(schema="wrong"),
            memory_item(id=" spaced "),
            memory_item(scope="unknown"),
            memory_item(kind="unknown"),
            memory_item(sensitivity="unknown"),
            memory_item(content=""),
            memory_item(provenance=""),
            memory_item(sourceTimestamp="2026-09-24T15:00:00Z"),
            memory_item(scope="space", spaceId=None),
            memory_item(scope="project", projectId=None),
            memory_item(content="-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----"),
            memory_item(provenance="ghp_abcdefghijklmnopqrstuvwxyz123456"),
            {**memory_item(), "unexpected": True},
        ]
        for item in invalid:
            with self.subTest(item=item):
                self.assertFalse(memory.valid_memory_payload(snapshot(item)))

        duplicate = memory_item(id="duplicate")
        self.assertFalse(memory.valid_memory_payload(snapshot(duplicate, duplicate)))

    def test_same_item_id_is_allowed_for_distinct_owners_only(self):
        memory = load_module()
        device = memory_item(id="shared")
        account_a = memory_item(
            id="shared",
            ownerKind="account",
            ownerId="user-a",
            scope="account",
        )
        account_b = memory_item(
            id="shared",
            ownerKind="account",
            ownerId="user-b",
            scope="account",
        )
        self.assertTrue(memory.valid_memory_payload(snapshot(device, account_a, account_b)))
        self.assertFalse(memory.valid_memory_payload(snapshot(account_a, {**account_a, "content": "second"})))

    def test_write_read_replace_and_delete_are_private_and_atomic(self):
        memory = load_module()
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory) / "state"
            path = state_dir / "intelligence-memory.json"
            first = snapshot(memory_item(id="a"))
            second = snapshot(memory_item(
                id="b",
                scope="project",
                projectId="project-a",
            ))

            memory.write_memory_payload(first, str(path))
            self.assertEqual(memory.read_memory_payload(str(path)), first)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            self.assertFalse(list(state_dir.glob(".*.tmp.*")))

            memory.write_memory_payload(second, str(path))
            self.assertEqual(memory.read_memory_payload(str(path)), second)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            self.assertFalse(list(state_dir.glob(".*.tmp.*")))

            memory.write_memory_payload(None, str(path))
            self.assertFalse(path.exists())
            self.assertIsNone(memory.read_memory_payload(str(path)))

    def test_unsafe_existing_target_fails_closed(self):
        memory = load_module()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            target = directory / "memory.json"
            target.write_text(snapshot(), encoding="utf-8")
            os.chmod(target, 0o644)
            with self.assertRaises(ValueError):
                memory.read_memory_payload(str(target))
            with self.assertRaises(ValueError):
                memory.write_memory_payload(snapshot(), str(target))

            target.unlink()
            real = directory / "real.json"
            real.write_text(snapshot(), encoding="utf-8")
            os.chmod(real, 0o600)
            target.symlink_to(real)
            with self.assertRaises(ValueError):
                memory.read_memory_payload(str(target))
            with self.assertRaises(ValueError):
                memory.write_memory_payload(snapshot(), str(target))

    def test_source_uses_fsync_replace_and_no_following_symlinks(self):
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("os.fsync(fd)", text)
        self.assertIn("os.fsync(directory_fd)", text)
        self.assertIn("os.replace(temporary, path)", text)
        self.assertIn('getattr(os, "O_NOFOLLOW", 0)', text)
        self.assertIn("session memory must not be persisted", text)
        self.assertIn("device memory must not use a synthetic account owner id", text)
        self.assertIn("account memory requires an account owner", text)
        self.assertIn("secret material is not valid memory state", text)
        self.assertIn("memory payload owner/id identities must be unique", text)


if __name__ == "__main__":
    unittest.main()
