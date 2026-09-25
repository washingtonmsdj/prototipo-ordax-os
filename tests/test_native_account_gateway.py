import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "system" / "surface" / "runtime" / "native_account_gateway.py"

spec = importlib.util.spec_from_file_location("ordax_native_account_gateway_test", MODULE)
gateway = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gateway
spec.loader.exec_module(gateway)


class NativeAccountGatewayTests(unittest.TestCase):
    def test_only_https_ordax_gateway_base_url_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = str(Path(temporary) / "session.json")
            with self.assertRaises(ValueError):
                gateway.NativeAccountGateway("http://accounts.example", path)
            with self.assertRaises(ValueError):
                gateway.NativeAccountGateway("https://user@example.com", path)
            with self.assertRaises(ValueError):
                gateway.NativeAccountGateway("https://accounts.example/path/", path)
            client = gateway.NativeAccountGateway(
                "https://accounts.example/functions/v1/ordax-account-gateway",
                path,
            )
            self.assertEqual(
                client.base_url,
                "https://accounts.example/functions/v1/ordax-account-gateway",
            )

    def test_device_session_is_private_and_contains_only_account_cookies(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "account" / "session.json"
            client = gateway.NativeAccountGateway("https://accounts.example", str(path))
            client._cookies = {
                "ordax_access": "access-value",
                "ordax_refresh": "refresh-value",
            }
            client._persist_session()

            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {"ordax_access", "ordax_refresh"})
            self.assertNotIn("password", path.read_text(encoding="utf-8").lower())

    def test_insecure_existing_session_permissions_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "session.json"
            path.write_text(
                json.dumps({"ordax_access": "a", "ordax_refresh": "b"}),
                encoding="utf-8",
            )
            os.chmod(path, 0o644)
            client = gateway.NativeAccountGateway("https://accounts.example", str(path))
            self.assertEqual(client._cookies, {})

    def test_symlink_session_path_is_never_loaded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.json"
            target.write_text(
                json.dumps({"ordax_access": "a", "ordax_refresh": "b"}),
                encoding="utf-8",
            )
            os.chmod(target, 0o600)
            link = root / "session.json"
            link.symlink_to(target)
            client = gateway.NativeAccountGateway("https://accounts.example", str(link))
            self.assertEqual(client._cookies, {})

    def test_native_adapter_has_no_provider_specific_supabase_dependency(self):
        source = MODULE.read_text(encoding="utf-8").lower()
        self.assertNotIn("supabase", source)
        self.assertIn("/auth/session", source)
        self.assertIn("/sync/objects", source)


if __name__ == "__main__":
    unittest.main()
