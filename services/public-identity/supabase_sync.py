"""Supabase REST adapter for OrdaX account sync.

Provider rows stay behind this adapter. Callers pass a validated user access
token and receive provider-neutral sync records. No service-role key is used.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class SupabaseSyncError(RuntimeError):
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
            with urlopen(request, timeout=15) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                status = int(response.status)
        except HTTPError as exc:
            payload = exc.read(MAX_RESPONSE_BYTES + 1)
            status = int(exc.code)
        except (URLError, OSError) as exc:
            raise SupabaseSyncError("provider-unreachable") from exc
        if len(payload) > MAX_RESPONSE_BYTES:
            raise SupabaseSyncError("provider-response-too-large", status=status)
        return status, payload


def _json(payload: bytes, status: int):
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SupabaseSyncError("provider-invalid-response", status=status) from exc


@dataclass(frozen=True)
class SyncApplyResult:
    sync_object_id: str | None
    server_revision: int
    tombstone: bool
    applied: bool
    conflict: bool
    change_cursor: int | None


class SupabaseSyncProvider:
    def __init__(
        self,
        project_url: str,
        publishable_key: str,
        *,
        transport: Transport | None = None,
    ) -> None:
        if not project_url.startswith("https://") or "/" in project_url.removeprefix("https://").rstrip("/"):
            raise ValueError("project_url must be an HTTPS origin")
        if not publishable_key.startswith("sb_publishable_"):
            raise ValueError("publishable key is required")
        self.project_url = project_url.rstrip("/")
        self.publishable_key = publishable_key
        self.transport = transport or UrllibTransport()

    def _request(self, path: str, access_token: str, payload: dict) -> object:
        if not access_token:
            raise ValueError("access token is required")
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        status, raw = self.transport.request(
            "POST",
            self.project_url + path,
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {access_token}",
            },
            body,
        )
        value = _json(raw, status)
        if status < 200 or status >= 300:
            raise SupabaseSyncError("provider-sync-failed", status=status)
        return value

    @staticmethod
    def _sync_object(item: dict) -> dict:
        if not isinstance(item, dict):
            raise SupabaseSyncError("provider-invalid-sync-object")
        return {
            "objectId": item.get("stable_object_id"),
            "dataClass": item.get("data_class"),
            "objectSchemaVersion": item.get("object_schema_version"),
            "resolverVersion": item.get("resolver_version"),
            "serverRevision": item.get("server_revision"),
            "tombstone": item.get("tombstone"),
            "payload": item.get("payload"),
            "updatedAt": item.get("updated_at", item.get("changed_at")),
        }

    @staticmethod
    def _limit(value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 500:
            raise ValueError("limit must be between 1 and 500")
        return value

    def snapshot(self, access_token: str, *, limit: int = 200) -> dict:
        value = self._request(
            "/rest/v1/rpc/ordax_sync_snapshot_v1",
            access_token,
            {"p_limit": self._limit(limit)},
        )
        if not isinstance(value, dict):
            raise SupabaseSyncError("provider-invalid-sync-snapshot")
        cursor = value.get("cursor")
        objects = value.get("objects")
        if (
            not isinstance(cursor, int)
            or isinstance(cursor, bool)
            or cursor < 0
            or not isinstance(objects, list)
        ):
            raise SupabaseSyncError("provider-invalid-sync-snapshot")
        return {
            "cursor": cursor,
            "objects": [self._sync_object(item) for item in objects],
        }

    def pull_changes(
        self,
        access_token: str,
        *,
        after_cursor: int = 0,
        limit: int = 200,
    ) -> dict:
        if (
            not isinstance(after_cursor, int)
            or isinstance(after_cursor, bool)
            or after_cursor < 0
        ):
            raise ValueError("after_cursor must be a non-negative integer")
        value = self._request(
            "/rest/v1/rpc/ordax_pull_sync_changes_v1",
            access_token,
            {"p_after_cursor": after_cursor, "p_limit": self._limit(limit)},
        )
        if not isinstance(value, list):
            raise SupabaseSyncError("provider-invalid-sync-changes")
        changes = []
        next_cursor = after_cursor
        for item in value:
            if not isinstance(item, dict):
                raise SupabaseSyncError("provider-invalid-sync-change")
            cursor = item.get("change_cursor")
            if (
                not isinstance(cursor, int)
                or isinstance(cursor, bool)
                or cursor <= next_cursor
            ):
                raise SupabaseSyncError("provider-invalid-sync-cursor")
            change = self._sync_object(item)
            change["cursor"] = cursor
            changes.append(change)
            next_cursor = cursor
        return {
            "afterCursor": after_cursor,
            "nextCursor": next_cursor,
            "changes": changes,
        }

    def list_objects(self, access_token: str, *, after_revision: int = 0, limit: int = 200) -> list[dict]:
        if not isinstance(after_revision, int) or isinstance(after_revision, bool) or after_revision < 0:
            raise ValueError("after_revision must be a non-negative integer")
        limit = self._limit(limit)
        value = self._request(
            "/rest/v1/rpc/ordax_list_sync_objects_v1",
            access_token,
            {"p_after_revision": after_revision, "p_limit": limit},
        )
        if not isinstance(value, list):
            raise SupabaseSyncError("provider-invalid-sync-list")
        result = []
        for item in value:
            if not isinstance(item, dict):
                raise SupabaseSyncError("provider-invalid-sync-object")
            result.append(self._sync_object(item))
        return result

    def apply_mutation(self, access_token: str, mutation: dict) -> SyncApplyResult:
        if not isinstance(mutation, dict):
            raise ValueError("mutation must be an object")
        value = self._request(
            "/rest/v1/rpc/ordax_apply_sync_mutation_v2",
            access_token,
            {
                "p_idempotency_key": mutation.get("idempotencyKey"),
                "p_data_class": mutation.get("dataClass"),
                "p_stable_object_id": mutation.get("objectId"),
                "p_object_schema_version": mutation.get("objectSchemaVersion"),
                "p_resolver_version": mutation.get("resolverVersion", 1),
                "p_base_server_revision": mutation.get("baseServerRevision"),
                "p_tombstone": mutation.get("operation") == "delete",
                "p_payload": mutation.get("payload") or {},
            },
        )
        if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
            raise SupabaseSyncError("provider-invalid-sync-apply")
        item = value[0]
        revision = item.get("server_revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise SupabaseSyncError("provider-invalid-sync-revision")
        cursor = item.get("change_cursor")
        if cursor is not None and (
            not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0
        ):
            raise SupabaseSyncError("provider-invalid-sync-cursor")
        return SyncApplyResult(
            sync_object_id=item.get("sync_object_id"),
            server_revision=revision,
            tombstone=bool(item.get("tombstone")),
            applied=bool(item.get("applied")),
            conflict=bool(item.get("conflict")),
            change_cursor=cursor,
        )
