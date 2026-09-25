"""Privacy-preserving compromised-password screening for OrdaX.

Only the first five hexadecimal characters of a locally computed SHA-1 hash
are sent to the HIBP Pwned Passwords range API. The plaintext password and the
complete hash never leave the OrdaX identity gateway.
"""

from __future__ import annotations

import hashlib
from typing import Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RANGE_ORIGIN = "https://api.pwnedpasswords.com"
MAX_RESPONSE_BYTES = 256 * 1024
USER_AGENT = "OrdaX-Account-Gateway/1"


class PwnedPasswordsError(RuntimeError):
    pass


class Transport(Protocol):
    def request(
        self,
        url: str,
        headers: Mapping[str, str],
    ) -> tuple[int, bytes]: ...


class UrllibTransport:
    def request(self, url: str, headers: Mapping[str, str]) -> tuple[int, bytes]:
        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=8) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                status = int(response.status)
        except HTTPError as exc:
            payload = exc.read(MAX_RESPONSE_BYTES + 1)
            status = int(exc.code)
        except (URLError, OSError, TimeoutError) as exc:
            raise PwnedPasswordsError("pwned-passwords-unreachable") from exc
        if len(payload) > MAX_RESPONSE_BYTES:
            raise PwnedPasswordsError("pwned-passwords-response-too-large")
        return status, payload


class PwnedPasswordChecker:
    def __init__(self, *, transport: Transport | None = None) -> None:
        self.transport = transport or UrllibTransport()

    def compromised_count(self, password: str) -> int:
        if not isinstance(password, str) or not password or "\x00" in password:
            raise ValueError("Password is invalid")
        digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
        prefix, suffix = digest[:5], digest[5:]
        status, raw = self.transport.request(
            f"{RANGE_ORIGIN}/range/{prefix}",
            {
                "Accept": "text/plain",
                "Add-Padding": "true",
                "User-Agent": USER_AGENT,
            },
        )
        if status != 200:
            raise PwnedPasswordsError(f"pwned-passwords-status-{status}")
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise PwnedPasswordsError("pwned-passwords-invalid-response") from exc

        for line in text.splitlines():
            candidate, separator, count_text = line.partition(":")
            if not separator:
                continue
            if candidate.strip().upper() != suffix:
                continue
            try:
                count = int(count_text.strip())
            except ValueError as exc:
                raise PwnedPasswordsError("pwned-passwords-invalid-response") from exc
            return max(0, count)
        return 0

    def is_compromised(self, password: str) -> bool:
        return self.compromised_count(password) > 0
