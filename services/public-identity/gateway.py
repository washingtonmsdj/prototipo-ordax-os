"""OrdaX same-origin public identity gateway.

The gateway owns browser credentials/session boundaries while Supabase Auth is
only a provider adapter. Access and refresh tokens never enter public-site
JavaScript: they are stored in HttpOnly cookies owned by this same-origin
service. Provider configuration is runtime-only.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Mapping
from urllib.parse import parse_qs, urlsplit

from supabase_password import SupabaseIdentityError, SupabasePasswordProvider

SESSION_SCHEMA = "prototype-ordax.public-identity-session/1"
ERROR_SCHEMA = "prototype-ordax.public-identity-error/1"
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
NO_STORE = "no-store, max-age=0"
MAX_REQUEST_BODY = 16 * 1024
ACCESS_COOKIE = "ordax_access"
REFRESH_COOKIE = "ordax_refresh"


@dataclass(frozen=True)
class GatewayResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes


class ProviderUnavailable(RuntimeError):
    pass


def _provider_from_environment() -> SupabasePasswordProvider | None:
    project_url = os.environ.get("ORDAX_SUPABASE_URL", "").strip()
    publishable_key = os.environ.get("ORDAX_SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not project_url or not publishable_key:
        return None
    try:
        return SupabasePasswordProvider(project_url, publishable_key)
    except (TypeError, ValueError):
        return None


def _secure_cookies() -> bool:
    return os.environ.get("ORDAX_IDENTITY_SECURE_COOKIES", "1") != "0"


def _cookie(name: str, value: str, *, max_age: int) -> str:
    parts = [
        f"{name}={value}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        f"Max-Age={max_age}",
    ]
    if _secure_cookies():
        parts.append("Secure")
    return "; ".join(parts)


def _clear_cookie(name: str) -> str:
    return _cookie(name, "", max_age=0)


def _session_cookies(access_token: str, refresh_token: str, expires_in: int) -> tuple[str, str]:
    return (
        _cookie(ACCESS_COOKIE, access_token, max_age=max(60, int(expires_in))),
        _cookie(REFRESH_COOKIE, refresh_token, max_age=60 * 60 * 24 * 30),
    )


def _read_cookies(cookie_header: str | None) -> dict[str, str]:
    if not cookie_header:
        return {}
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except Exception:
        return {}
    return {key: morsel.value for key, morsel in cookie.items()}


def _json_response(
    status: int,
    payload: Mapping[str, object],
    *,
    set_cookies: tuple[str, ...] = (),
) -> GatewayResponse:
    body = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    headers: list[tuple[str, str]] = [
        ("Content-Type", JSON_CONTENT_TYPE),
        ("Cache-Control", NO_STORE),
        ("Pragma", "no-cache"),
        ("X-Content-Type-Options", "nosniff"),
        ("Content-Length", str(len(body))),
    ]
    for cookie in set_cookies:
        headers.append(("Set-Cookie", cookie))
    return GatewayResponse(status=status, headers=tuple(headers), body=body)


def _redirect(location: str, *, set_cookies: tuple[str, ...] = ()) -> GatewayResponse:
    headers: list[tuple[str, str]] = [
        ("Location", location),
        ("Cache-Control", NO_STORE),
        ("Pragma", "no-cache"),
        ("Content-Length", "0"),
    ]
    for cookie in set_cookies:
        headers.append(("Set-Cookie", cookie))
    return GatewayResponse(status=303, headers=tuple(headers), body=b"")


def _error(status: int, code: str, message: str) -> GatewayResponse:
    return _json_response(
        status,
        {"$schema": ERROR_SCHEMA, "error": code, "message": message},
    )


def _safe_same_origin_path(value: str) -> bool:
    split = urlsplit(value)
    return (
        value.startswith("/")
        and not value.startswith("//")
        and not split.scheme
        and not split.netloc
        and not split.fragment
    )


def _form(body: bytes, content_type: str) -> dict[str, str]:
    if len(body) > MAX_REQUEST_BODY:
        raise ValueError("request-too-large")
    if not content_type.lower().startswith("application/x-www-form-urlencoded"):
        raise ValueError("unsupported-content-type")
    try:
        values = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=False)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("invalid-form") from exc
    return {key: items[-1] for key, items in values.items() if items}


def _same_origin_state_change(headers: Mapping[str, str]) -> bool:
    if headers.get("sec-fetch-site") == "cross-site":
        return False
    origin = headers.get("origin")
    host = headers.get("host")
    if not origin or not host:
        return True
    split = urlsplit(origin)
    return split.netloc == host and split.scheme in ("https", "http")


class PublicIdentityGateway:
    def __init__(self, provider: SupabasePasswordProvider | None = None) -> None:
        self.provider = provider if provider is not None else _provider_from_environment()

    @property
    def provider_configured(self) -> bool:
        return self.provider is not None

    def _provider_unavailable(self) -> GatewayResponse:
        return _error(
            503,
            "identity-provider-unavailable",
            "O serviço de identidade OrdaX ainda não está configurado.",
        )

    def _session(
        self, request_headers: Mapping[str, str]
    ) -> GatewayResponse:
        if not self.provider:
            return _json_response(
                200,
                {
                    "$schema": SESSION_SCHEMA,
                    "authenticated": False,
                    "provider": "unconfigured",
                    "status": "anonymous",
                },
            )

        cookies = _read_cookies(request_headers.get("cookie"))
        access = cookies.get(ACCESS_COOKIE)
        refresh = cookies.get(REFRESH_COOKIE)
        if access:
            try:
                subject, email = self.provider.get_user(access)
                return _json_response(
                    200,
                    {
                        "$schema": SESSION_SCHEMA,
                        "authenticated": True,
                        "provider": "supabase",
                        "status": "authenticated",
                        "subject": subject,
                        "email": email,
                    },
                )
            except SupabaseIdentityError:
                pass

        if refresh:
            try:
                session = self.provider.refresh_session(refresh)
                subject, email = self.provider.get_user(session.access_token)
                return _json_response(
                    200,
                    {
                        "$schema": SESSION_SCHEMA,
                        "authenticated": True,
                        "provider": "supabase",
                        "status": "authenticated",
                        "subject": subject,
                        "email": email,
                    },
                    set_cookies=_session_cookies(
                        session.access_token, session.refresh_token, session.expires_in
                    ),
                )
            except SupabaseIdentityError:
                pass

        return _json_response(
            200,
            {
                "$schema": SESSION_SCHEMA,
                "authenticated": False,
                "provider": "supabase",
                "status": "anonymous",
            },
            set_cookies=(_clear_cookie(ACCESS_COOKIE), _clear_cookie(REFRESH_COOKIE)),
        )

    def _credentials_action(
        self,
        *,
        registration: bool,
        request_headers: Mapping[str, str],
        body: bytes,
    ) -> GatewayResponse:
        if not self.provider:
            return self._provider_unavailable()
        if not _same_origin_state_change(request_headers):
            return _error(403, "cross-site-request-rejected", "A solicitação cross-site foi rejeitada.")
        try:
            form = _form(body, request_headers.get("content-type", ""))
            email = form.get("email", "")
            password = form.get("password", "")
            result = (
                self.provider.sign_up_with_password(email, password)
                if registration
                else self.provider.sign_in_with_password(email, password)
            )
        except ValueError:
            return _error(400, "invalid-credentials-form", "Revise o e-mail e a senha informados.")
        except SupabaseIdentityError:
            return _error(
                401 if not registration else 400,
                "authentication-failed" if not registration else "registration-failed",
                "Não foi possível concluir esta operação de conta.",
            )

        if result.session is None:
            return _redirect("/login/?cadastro=verifique-email")

        return _redirect(
            "/conta/",
            set_cookies=_session_cookies(
                result.session.access_token,
                result.session.refresh_token,
                result.session.expires_in,
            ),
        )

    def handle(
        self,
        method: str,
        target: str,
        headers: Mapping[str, str] | None = None,
        body: bytes = b"",
    ) -> GatewayResponse:
        method = method.upper()
        request_headers = {key.lower(): value for key, value in (headers or {}).items()}
        split = urlsplit(target)
        path = split.path

        if path == "/auth/session":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._session(request_headers)

        if path == "/auth/login":
            if method == "GET":
                return _redirect("/login/")
            if method != "POST":
                return self._method_not_allowed("GET, POST")
            return self._credentials_action(
                registration=False, request_headers=request_headers, body=body
            )

        if path == "/auth/register":
            if method == "GET":
                return _redirect("/cadastro/")
            if method != "POST":
                return self._method_not_allowed("GET, POST")
            return self._credentials_action(
                registration=True, request_headers=request_headers, body=body
            )

        if path == "/auth/logout":
            if method != "POST":
                return self._method_not_allowed("POST")
            if not _same_origin_state_change(request_headers):
                return _error(403, "cross-site-request-rejected", "A solicitação cross-site foi rejeitada.")
            cookies = _read_cookies(request_headers.get("cookie"))
            access = cookies.get(ACCESS_COOKIE)
            if self.provider and access:
                try:
                    self.provider.sign_out(access)
                except SupabaseIdentityError:
                    pass
            return _redirect(
                "/",
                set_cookies=(_clear_cookie(ACCESS_COOKIE), _clear_cookie(REFRESH_COOKIE)),
            )

        if path.startswith("/auth/"):
            return _error(404, "identity-route-not-found", "Rota de identidade inexistente.")
        return _error(404, "not-found", "Recurso inexistente.")

    @staticmethod
    def _method_not_allowed(allowed: str) -> GatewayResponse:
        response = _error(405, "method-not-allowed", "Método não permitido.")
        return GatewayResponse(
            status=response.status,
            headers=response.headers + (("Allow", allowed),),
            body=response.body,
        )


gateway = PublicIdentityGateway()


def application(environ, start_response):
    method = str(environ.get("REQUEST_METHOD", "GET"))
    path = str(environ.get("PATH_INFO", "/"))
    query = str(environ.get("QUERY_STRING", ""))
    target = path + (("?" + query) if query else "")

    headers: dict[str, str] = {}
    for key, value in environ.items():
        if key.startswith("HTTP_") and isinstance(value, str):
            headers[key[5:].replace("_", "-").lower()] = value
    if isinstance(environ.get("CONTENT_TYPE"), str):
        headers["content-type"] = str(environ["CONTENT_TYPE"])
    if isinstance(environ.get("HTTP_HOST"), str):
        headers["host"] = str(environ["HTTP_HOST"])

    body = b""
    if method in ("POST", "PUT", "PATCH"):
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            length = 0
        if length < 0 or length > MAX_REQUEST_BODY:
            response = _error(413, "request-too-large", "A solicitação excede o limite permitido.")
        else:
            stream = environ.get("wsgi.input")
            body = stream.read(length) if stream is not None and length else b""
            response = gateway.handle(method, target, headers, body)
    else:
        response = gateway.handle(method, target, headers, body)

    reason = {
        200: "OK",
        303: "See Other",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        413: "Payload Too Large",
        503: "Service Unavailable",
    }.get(response.status, "Error")
    start_response(f"{response.status} {reason}", list(response.headers))
    return [response.body]
