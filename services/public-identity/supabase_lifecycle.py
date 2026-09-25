"""Supabase Edge adapter for destructive OrdaX account lifecycle actions.

This client is used by the public identity gateway after the user has been
reauthenticated. It forwards only the fresh user bearer token and an explicit
close-account confirmation to the dedicated lifecycle Edge Function. It never
accepts or uses a service-role key.
"""

from __future__ import annotations

import json
from typing import Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 1024 * 1024
CLOSE_CONFIRMATION = "close-account"


class SupabaseLifecycleError(RuntimeError):
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
            with urlopen(request, timeout=20) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                status = int(response.status)
        except HTTPError as exc:
            payload = exc.read(MAX_RESPONSE_BYTES + 1)
            status = int(exc.code)
        except (URLError, OSError) as exc:
            raise SupabaseLifecycleError("lifecycle-unreachable") from exc
        if len(payload) > MAX_RESPONSE_BYTES:
            raise SupabaseLifecycleError("lifecycle-response-too-large", status=status)
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
        raise ValueError("Supabase lifecycle adapter requires an sb_publishable_ key")
    if len(value) < len("sb_publishable_") + 8 or len(value) > 512:
        raise ValueError("Supabase publishable key length is invalid")
    return value


class SupabaseLifecycleProvider:
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

    def close_account(self, access_token: str, confirmation: str) -> None:
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Access token is invalid")
        if confirmation != CLOSE_CONFIRMATION:
            raise ValueError("Account close confirmation is invalid")
        body = json.dumps(
            {"confirmation": confirmation},
            separators=(",", ":"),
        ).encode("utf-8")
        status, raw = self.transport.request(
            "POST",
            self.project_url + "/functions/v1/ordax-account-lifecycle/close",
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {access_token}",
            },
            body,
        )
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise SupabaseLifecycleError("lifecycle-invalid-response", status=status) from exc
        if status < 200 or status >= 300:
            code = value.get("error") if isinstance(value, dict) else None
            raise SupabaseLifecycleError(
                code if isinstance(code, str) and code else "account-close-failed",
                status=status,
            )
        if not isinstance(value, dict) or value.get("closed") is not True:
            raise SupabaseLifecycleError("lifecycle-invalid-response", status=status)
