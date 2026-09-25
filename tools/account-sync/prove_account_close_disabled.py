#!/usr/bin/env python3
"""Prove that the deployed OrdaX account-close route exists and is disabled.

This proof intentionally uses no account credentials. It is safe to run against
the deployed account gateway only while the canonical account-close contract
requires the route to fail closed before authentication.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_GATEWAY_FILE = os.path.join(ROOT, "system", "services", "account", "gateway-base-url")


def fail(reason: str) -> "NoReturn":
    raise SystemExit(f"ACCOUNT_CLOSE_DISABLED_PROOF=FAIL reason={reason}")


def gateway_url() -> str:
    override = os.environ.get("ORDAX_ACCOUNT_GATEWAY_BASE_URL", "").strip()
    if override:
        return override.rstrip("/")
    try:
        with open(DEFAULT_GATEWAY_FILE, "r", encoding="utf-8") as handle:
            value = handle.read().strip().rstrip("/")
    except OSError:
        fail("gateway-config-missing")
    if not value.startswith("https://") or "?" in value or "#" in value:
        fail("invalid-gateway-url")
    return value


def main() -> int:
    request = Request(
        gateway_url() + "/account/close",
        data=b"confirmation=close-account&password=not-a-real-password",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "OrdaX-Account-Close-Disabled-Proof/1",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            status = int(response.status)
            raw = response.read(1024 * 1024)
    except HTTPError as exc:
        status = int(exc.code)
        raw = exc.read(1024 * 1024)
    except (URLError, OSError, TimeoutError) as exc:
        fail(f"gateway-unreachable:{type(exc).__name__}")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        fail(f"invalid-json:{status}")

    if status != 503:
        fail(f"unexpected-status:{status}")
    if payload.get("error") != "account-close-disabled":
        fail("close-route-not-fail-closed")

    print("ACCOUNT_CLOSE_DISABLED_PROOF=PASS route=/account/close status=503")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
