#!/usr/bin/env python3
"""Verify a deployed OrdaX public-site origin without using account credentials."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


def fail(reason: str) -> "NoReturn":
    raise SystemExit(f"PUBLIC_SITE_DEPLOYMENT_PROOF=FAIL reason={reason}")


def request(base: str, path: str, method: str = "GET"):
    target = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    req = Request(target, method=method, headers={"User-Agent": "OrdaX-Public-Deployment-Proof/1"})
    try:
        return urlopen(req, timeout=15, context=ssl.create_default_context())
    except HTTPError as exc:
        return exc
    except (URLError, OSError, TimeoutError) as exc:
        fail(f"request:{type(exc).__name__}")


def expect_headers(response) -> None:
    for name, fragment in SECURITY_HEADERS.items():
        value = response.headers.get(name, "")
        if fragment not in value:
            fail(f"header:{name}")


def read_json(response):
    try:
        return json.loads(response.read(1024 * 1024).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        fail("invalid-json")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True)
    args = parser.parse_args(argv)

    origin = args.origin.rstrip("/")
    split = urlsplit(origin)
    if split.scheme != "https" or not split.netloc or split.path not in ("", "/") or split.query or split.fragment:
        fail("origin-must-be-clean-https-origin")

    landing = request(origin, "/")
    if landing.status != 200:
        fail(f"landing-status:{landing.status}")
    expect_headers(landing)
    if "no-cache" not in landing.headers.get("Cache-Control", ""):
        fail("landing-cache")

    config = request(origin, "/config/public-site.json")
    if config.status != 200 or "no-store" not in config.headers.get("Cache-Control", ""):
        fail("config-cache")
    config_payload = read_json(config)
    if config_payload.get("$schema") != "prototype-ordax.public-site-runtime/1":
        fail("config-schema")

    session = request(origin, "/auth/session")
    if session.status != 200:
        fail(f"auth-session-status:{session.status}")
    expect_headers(session)
    if "no-store" not in session.headers.get("Cache-Control", ""):
        fail("auth-session-cache")
    session_payload = read_json(session)
    if session_payload.get("$schema") != "prototype-ordax.public-identity-session/1":
        fail("auth-session-schema")
    if session_payload.get("authenticated") is not False:
        fail("unexpected-authenticated-session")

    sync = request(origin, "/sync/snapshot?limit=1")
    if sync.status != 401:
        fail(f"anonymous-sync-status:{sync.status}")
    sync_payload = read_json(sync)
    if sync_payload.get("error") != "authentication-required":
        fail("anonymous-sync-error")

    missing = request(origin, "/__ordax-deployment-proof-missing")
    if missing.status != 404:
        fail(f"unknown-route-status:{missing.status}")

    print("PUBLIC_SITE_DEPLOYMENT_PROOF=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
