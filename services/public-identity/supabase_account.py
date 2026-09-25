"""Supabase REST adapter for OrdaX account lifecycle reads.

This adapter owns only provider-specific account export transport. It receives
an already validated user access token, calls an RLS-scoped SECURITY INVOKER
RPC, and returns provider-neutral account export data. No service-role key is
accepted or used here.
"""

from __future__ import annotations

import json
from typing import Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 16 * 1024 * 1024
EXPORT_SCHEMA = "prototype-ordax.account-export/1"


class SupabaseAccountError(RuntimeError):
    def __init__(self, code: str, *, status: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
    ) -> tuple[int, bytes]: ...


class UrllibTransport:
    def request(self, method, url, headers, body):
        request = Request(url, data=body, headers=dict(headers), method=method)
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                status = int(response.status)
        except HTTPError as exc:
            payload = exc.read(MAX_RESPONSE_BYTES + 1)
            status = int(exc.code)
        except (URLError, OSError) as exc:
            raise SupabaseAccountError("provider-unreachable") from exc
        if len(payload) > MAX_RESPONSE_BYTES:
            raise SupabaseAccountError("provider-response-too-large", status=status)
        return status, payload


def _validated_base_url(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Supabase URL must be a string")
    split = urlsplit(value)
    if (
        split.scheme != "https"
        or not split.netloc
        or split.username is not None
        or split.password is not None
        or split.query
        or split.fragment
        or split.path not in ("", "/")
    ):
        raise ValueError("Supabase URL must be an HTTPS origin")
    return f"https://{split.netloc}"


def _validated_publishable_key(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Supabase publishable key must be a string")
    if not value.startswith("sb_publishable_") or any(ch.isspace() for ch in value):
        raise ValueError("Supabase account adapter requires an sb_publishable_ key")
    if len(value) < len("sb_publishable_") + 8 or len(value) > 512:
        raise ValueError("Supabase publishable key length is invalid")
    return value


class SupabaseAccountProvider:
    def __init__(
        self,
        project_url: str,
        publishable_key: str,
        *,
        transport: Transport | None = None,
    ) -> None:
        self.project_url = _validated_base_url(project_url)
        self.publishable_key = _validated_publishable_key(publishable_key)
        self.transport = transport or UrllibTransport()

    def export_account(self, access_token: str) -> dict:
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Access token is invalid")
        status, raw = self.transport.request(
            "POST",
            self.project_url + "/rest/v1/rpc/ordax_account_export_v1",
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {access_token}",
            },
            b"{}",
        )
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise SupabaseAccountError("provider-invalid-response", status=status) from exc
        if status < 200 or status >= 300:
            raise SupabaseAccountError("provider-account-export-failed", status=status)
        if not isinstance(value, dict) or value.get("$schema") != EXPORT_SCHEMA:
            raise SupabaseAccountError("provider-invalid-account-export", status=status)
        subject = value.get("subject")
        if not isinstance(subject, str) or not subject:
            raise SupabaseAccountError("provider-invalid-account-export", status=status)
        for section in (
            "spaces",
            "memberships",
            "space_profile_packs",
            "entitlements",
            "projects",
            "devices",
            "project_connections",
            "memory_items",
            "sync_objects",
        ):
            if not isinstance(value.get(section), list):
                raise SupabaseAccountError("provider-invalid-account-export", status=status)
        if not isinstance(value.get("account"), dict):
            raise SupabaseAccountError("provider-invalid-account-export", status=status)
        return value
