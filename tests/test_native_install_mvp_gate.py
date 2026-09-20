#!/usr/bin/env python3
"""Regress the MVP USB-only Native-install runtime gate."""

from __future__ import annotations

from functools import partial
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "system" / "surface" / "runtime" / "native_host_server.py"
LAUNCHER = ROOT / "system" / "surface" / "bin" / "ordax-surface"

spec = importlib.util.spec_from_file_location("ordax_native_mvp_gate", HOST)
native_host = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(native_host)


class NativeInstallMVPGateTests(unittest.TestCase):
    def make_server(self, root: Path, *, profile: str, capability: str):
        handler = partial(native_host.NativeHostHandler, directory=str(root))
        return native_host.NativeHostServer(
            ("127.0.0.1", 0),
            handler,
            user_root=str(root),
            power_request_path=str(root / "power-request"),
            network_session_dir=str(root),
            product_mode="usb",
            distribution_profile=profile,
            native_install_capability=capability,
        )

    def test_stable_mvp_never_exposes_native_install_token_even_if_broker_exists(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            os.mkfifo(root / "native-install-control", 0o600)
            server = self.make_server(
                root,
                profile="stable-mvp",
                capability="post-mvp-preview",
            )
            try:
                self.assertFalse(server.native_install_available)
                self.assertEqual(server.native_install_token, "")
            finally:
                server.server_close()

    def test_owner_preview_requires_explicit_capability_opt_in(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            os.mkfifo(root / "native-install-control", 0o600)

            disabled = self.make_server(
                root,
                profile="owner-development",
                capability="disabled",
            )
            try:
                self.assertFalse(disabled.native_install_available)
                self.assertEqual(disabled.native_install_token, "")
            finally:
                disabled.server_close()

            preview = self.make_server(
                root,
                profile="owner-development",
                capability="post-mvp-preview",
            )
            try:
                self.assertTrue(preview.native_install_available)
                self.assertGreaterEqual(len(preview.native_install_token), 16)
            finally:
                preview.server_close()

    def test_launcher_forces_stable_profile_off_before_broker_and_host_start(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn(
            'NATIVE_INSTALL_CAPABILITY=${ORDAX_NATIVE_INSTALL_CAPABILITY:-disabled}',
            text,
        )
        self.assertIn(
            '[ "$DISTRIBUTION_PROFILE" = "stable-mvp" ] && NATIVE_INSTALL_CAPABILITY=disabled',
            text,
        )
        self.assertIn(
            '[ "$NATIVE_INSTALL_CAPABILITY" = "post-mvp-preview" ] || return 0',
            text,
        )
        self.assertIn(
            '[ "$DISTRIBUTION_PROFILE" = "owner-development" ] || return 0',
            text,
        )
        self.assertIn('--distribution-profile "$DISTRIBUTION_PROFILE"', text)
        self.assertIn('--native-install-capability "$NATIVE_INSTALL_CAPABILITY"', text)


if __name__ == "__main__":
    unittest.main()
