import errno
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "system/surface/runtime/native_host_server.py"
CONTRACT = ROOT / "system/contracts/file-space.mjs"
ADAPTER = ROOT / "system/adapters/native/file-space.mjs"
CONTROLS = ROOT / "system/surface/ui/file-space-controls.mjs"

spec = importlib.util.spec_from_file_location("ordax_native_trash_test", SERVER)
native_host = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(native_host)


class NativeFileTrashTests(unittest.TestCase):
    def test_reserved_trash_namespace_is_not_public_file_space(self):
        self.assertFalse(native_host.valid_file_name(native_host.TRASH_ROOT_NAME))
        self.assertFalse(native_host.valid_logical_file_path("/.ordax-trash"))
        self.assertFalse(native_host.valid_logical_file_path("/.ordax-trash/files"))

        with tempfile.TemporaryDirectory() as temporary:
            user_root = Path(temporary) / "home"
            user_root.mkdir()
            native_host.list_user_trash(str(user_root))
            listing = native_host.list_user_directory(str(user_root), "/")
            self.assertNotIn(
                native_host.TRASH_ROOT_NAME,
                [entry["name"] for entry in listing["entries"]],
            )

    def test_regular_file_moves_to_private_trash_and_restores_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_root = Path(temporary) / "home"
            documents = user_root / "Documentos"
            documents.mkdir(parents=True)
            source = documents / "nota.txt"
            source.write_text("conteúdo preservado", encoding="utf-8")

            listing = native_host.trash_user_entry(
                str(user_root),
                "/Documentos",
                "nota.txt",
            )
            self.assertFalse(source.exists())
            self.assertNotIn("nota.txt", [entry["name"] for entry in listing["entries"]])

            trash = native_host.list_user_trash(str(user_root))
            self.assertEqual(len(trash["entries"]), 1)
            entry = trash["entries"][0]
            self.assertEqual(entry["name"], "nota.txt")
            self.assertEqual(entry["kind"], "file")
            self.assertEqual(entry["originalPath"], "/Documentos/nota.txt")
            self.assertRegex(entry["id"], r"^[0-9a-f]{32}$")

            info_path = (
                user_root
                / native_host.TRASH_ROOT_NAME
                / native_host.TRASH_INFO_NAME
                / f"{entry['id']}.json"
            )
            payload_path = (
                user_root
                / native_host.TRASH_ROOT_NAME
                / native_host.TRASH_FILES_NAME
                / entry["id"]
            )
            self.assertEqual(info_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(payload_path.read_text(encoding="utf-8"), "conteúdo preservado")
            raw_metadata = info_path.read_text(encoding="utf-8")
            self.assertNotIn(str(user_root), raw_metadata)
            metadata = json.loads(raw_metadata)
            self.assertEqual(metadata["originalPath"], "/Documentos/nota.txt")

            restored = native_host.restore_user_trash_entry(str(user_root), entry["id"])
            self.assertEqual(restored["entries"], [])
            self.assertEqual(source.read_text(encoding="utf-8"), "conteúdo preservado")

    def test_directory_round_trip_preserves_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_root = Path(temporary) / "home"
            folder = user_root / "Documentos" / "Projeto"
            folder.mkdir(parents=True)
            (folder / "a.txt").write_text("a", encoding="utf-8")
            (folder / "Sub").mkdir()
            (folder / "Sub" / "b.txt").write_text("b", encoding="utf-8")

            native_host.trash_user_entry(str(user_root), "/Documentos", "Projeto")
            self.assertFalse(folder.exists())
            entry = native_host.list_user_trash(str(user_root))["entries"][0]
            self.assertEqual(entry["kind"], "directory")

            native_host.restore_user_trash_entry(str(user_root), entry["id"])
            self.assertEqual((folder / "a.txt").read_text(encoding="utf-8"), "a")
            self.assertEqual((folder / "Sub" / "b.txt").read_text(encoding="utf-8"), "b")

    def test_restore_collision_fails_without_overwrite_or_trash_loss(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_root = Path(temporary) / "home"
            documents = user_root / "Documentos"
            documents.mkdir(parents=True)
            source = documents / "nota.txt"
            source.write_text("original", encoding="utf-8")
            native_host.trash_user_entry(str(user_root), "/Documentos", "nota.txt")
            entry = native_host.list_user_trash(str(user_root))["entries"][0]

            source.write_text("novo", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                native_host.restore_user_trash_entry(str(user_root), entry["id"])

            self.assertEqual(source.read_text(encoding="utf-8"), "novo")
            trash = native_host.list_user_trash(str(user_root))
            self.assertEqual([item["id"] for item in trash["entries"]], [entry["id"]])

    def test_cross_device_trash_failure_preserves_source_and_hides_stale_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_root = Path(temporary) / "home"
            documents = user_root / "Documentos"
            documents.mkdir(parents=True)
            source = documents / "nota.txt"
            source.write_text("não perder", encoding="utf-8")

            with mock.patch.object(
                native_host,
                "_renameat2_noreplace_between",
                side_effect=OSError(errno.EXDEV, "simulated boundary"),
            ):
                with self.assertRaises(native_host.FileSpaceTrashCrossDeviceError):
                    native_host.trash_user_entry(
                        str(user_root),
                        "/Documentos",
                        "nota.txt",
                    )

            self.assertEqual(source.read_text(encoding="utf-8"), "não perder")
            self.assertEqual(native_host.list_user_trash(str(user_root))["entries"], [])

    def test_symlink_cannot_be_trashed_through_file_space(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            user_root = Path(temporary) / "home"
            documents = user_root / "Documentos"
            documents.mkdir(parents=True)
            outside = Path(temporary) / "outside.txt"
            outside.write_text("fora", encoding="utf-8")
            link = documents / "atalho"
            link.symlink_to(outside)
            with self.assertRaises(ValueError):
                native_host.trash_user_entry(str(user_root), "/Documentos", "atalho")
            self.assertEqual(outside.read_text(encoding="utf-8"), "fora")

    def test_contract_and_http_surface_offer_recovery_not_permanent_delete(self):
        contract = CONTRACT.read_text(encoding="utf-8")
        adapter = ADAPTER.read_text(encoding="utf-8")
        server = SERVER.read_text(encoding="utf-8")
        self.assertIn('ordax.file-space/11', contract)
        self.assertIn("trashEntry()", contract)
        self.assertIn("listTrash()", contract)
        self.assertIn("restoreTrashEntry()", contract)
        self.assertIn('TRASH_ENDPOINT = "/__ordax/native/trash"', adapter)
        self.assertIn('"trash-entry"', adapter)
        self.assertIn('"restore-trash-entry"', adapter)
        self.assertIn('TRASH_ROOT_NAME = ".ordax-trash"', server)
        self.assertIn("RENAME_NOREPLACE", server)
        self.assertNotIn('"delete-entry"', adapter)
        self.assertNotIn('action == "delete-entry"', server)


if __name__ == "__main__":
    unittest.main()
