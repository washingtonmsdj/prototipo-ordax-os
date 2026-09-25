#!/usr/bin/env python3
"""Bounded private persistence helper for OrdaX Intelligence memory snapshots."""

from __future__ import annotations

from datetime import datetime
import json
import os
import re
import secrets
import stat
import threading

MEMORY_SNAPSHOT_SCHEMA = "ordax.memory-snapshot/1"
MEMORY_ITEM_SCHEMA = "ordax.memory/1"
DEFAULT_MEMORY_FILE = "/var/lib/ordax/intelligence-memory.json"
MAX_MEMORY_ITEMS = 2048
MAX_MEMORY_PAYLOAD_BYTES = 8 * 1024 * 1024
MEMORY_SCOPES = frozenset(("device", "account", "space", "project", "session"))
MEMORY_KINDS = frozenset(("preference", "fact", "instruction", "summary", "artifact-reference"))
MEMORY_SENSITIVITY = frozenset(("normal", "private", "restricted"))
MEMORY_ITEM_KEYS = frozenset((
    "schema",
    "id",
    "ownerKind",
    "ownerId",
    "scope",
    "kind",
    "sensitivity",
    "content",
    "provenance",
    "sourceTimestamp",
    "spaceId",
    "projectId",
))
CANONICAL_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$"
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\bsb_secret_[A-Za-z0-9_-]{16,}\b"),
)


def _canonical_text(value: object, label: str, max_chars: int) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise ValueError(f"{label} must be text")
    if not value or value != value.strip() or len(value) > max_chars:
        raise ValueError(f"{label} is outside its allowed bounds")
    return value


def _optional_text(value: object, label: str, max_chars: int) -> str | None:
    if value is None:
        return None
    return _canonical_text(value, label, max_chars)


def _contains_secret(value: str) -> bool:
    return any(pattern.search(value) is not None for pattern in SECRET_PATTERNS)


def _validate_timestamp(value: object) -> None:
    timestamp = _canonical_text(value, "memory source timestamp", 64)
    if not CANONICAL_TIMESTAMP_RE.fullmatch(timestamp):
        raise ValueError("memory source timestamp is not canonical ISO-8601")
    try:
        datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("memory source timestamp is invalid") from exc


def _validate_item_owner(item: dict) -> tuple[str, str | None]:
    owner_id = item.get("ownerId")
    owner_kind = item.get("ownerKind")
    if owner_kind not in {"device", "account"}:
        raise ValueError("memory payload owner kind is invalid")
    if owner_kind == "account":
        owner_id = _canonical_text(owner_id, "account memory owner id", 160)
    elif owner_id is not None:
        raise ValueError("device memory must not use a synthetic account owner id")
    if item.get("scope") == "account" and owner_kind != "account":
        raise ValueError("account memory requires an account owner")
    return owner_kind, owner_id


def _validate_item(item: object) -> tuple[str, str | None, str]:
    if not isinstance(item, dict) or set(item) != MEMORY_ITEM_KEYS:
        raise ValueError("memory payload item shape is invalid")
    if item.get("schema") != MEMORY_ITEM_SCHEMA:
        raise ValueError("memory payload item schema is invalid")

    item_id = _canonical_text(item.get("id"), "memory item id", 160)
    owner_kind, owner_id = _validate_item_owner(item)

    scope = item.get("scope")
    if scope not in MEMORY_SCOPES:
        raise ValueError("memory payload scope is invalid")
    if scope == "session":
        raise ValueError("session memory must not be persisted to device state")
    if item.get("kind") not in MEMORY_KINDS:
        raise ValueError("memory payload kind is invalid")
    if item.get("sensitivity") not in MEMORY_SENSITIVITY:
        raise ValueError("memory payload sensitivity is invalid")

    content = _canonical_text(item.get("content"), "memory content", 32768)
    provenance = _canonical_text(item.get("provenance"), "memory provenance", 1024)
    if _contains_secret(content) or _contains_secret(provenance):
        raise ValueError("secret material is not valid memory state")
    _validate_timestamp(item.get("sourceTimestamp"))

    space_id = _optional_text(item.get("spaceId"), "memory space id", 160)
    project_id = _optional_text(item.get("projectId"), "memory project id", 240)
    if scope == "space" and space_id is None:
        raise ValueError("space memory requires a space id")
    if scope == "project" and project_id is None:
        raise ValueError("project memory requires a project id")
    return owner_kind, owner_id, item_id


def _parse_payload(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("memory payload must be a string or null")
    raw = value.encode("utf-8")
    if len(raw) > MAX_MEMORY_PAYLOAD_BYTES:
        raise ValueError("memory payload exceeds its byte limit")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("memory payload is not valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"$schema", "items"}:
        raise ValueError("memory payload shape is invalid")
    if payload.get("$schema") != MEMORY_SNAPSHOT_SCHEMA:
        raise ValueError("memory payload schema is invalid")
    items = payload.get("items")
    if not isinstance(items, list) or len(items) > MAX_MEMORY_ITEMS:
        raise ValueError("memory payload items are invalid")

    identities: set[tuple[str, str | None, str]] = set()
    for item in items:
        identity = _validate_item(item)
        if identity in identities:
            raise ValueError("memory payload owner/id identities must be unique")
        identities.add(identity)
    return payload


def valid_memory_payload(value: object) -> bool:
    try:
        _parse_payload(value)
    except (TypeError, ValueError, UnicodeError):
        return False
    return True


def _open_directory(directory: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    return os.open(directory, flags)


def _validate_existing_target(path: str) -> None:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise ValueError("memory state target is not a regular file")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError("memory state target permissions are not private")
    if metadata.st_size > MAX_MEMORY_PAYLOAD_BYTES:
        raise ValueError("memory state target exceeds its byte limit")


def read_memory_payload(path: str = DEFAULT_MEMORY_FILE) -> str | None:
    _validate_existing_target(path)
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return None
    if metadata.st_size > MAX_MEMORY_PAYLOAD_BYTES:
        raise ValueError("memory state exceeds its byte limit")

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_MEMORY_PAYLOAD_BYTES:
            raise ValueError("memory state changed to an unsafe file")
        chunks: list[bytes] = []
        remaining = MAX_MEMORY_PAYLOAD_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_MEMORY_PAYLOAD_BYTES:
            raise ValueError("memory state exceeds its byte limit")
    finally:
        os.close(fd)

    text = raw.decode("utf-8", errors="strict")
    _parse_payload(text)
    return text


def write_memory_payload(payload: str | None, path: str = DEFAULT_MEMORY_FILE) -> None:
    _parse_payload(payload)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, mode=0o700, exist_ok=True)
    _validate_existing_target(path)
    directory_fd = _open_directory(directory)
    try:
        if payload is None:
            try:
                os.unlink(path)
            except FileNotFoundError:
                return
            os.fsync(directory_fd)
            return

        encoded = payload.encode("utf-8")
        basename = os.path.basename(path)
        temporary = os.path.join(
            directory,
            f".{basename}.tmp.{os.getpid()}.{threading.get_ident()}.{secrets.token_hex(4)}",
        )
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        fd = -1
        try:
            fd = os.open(temporary, flags, 0o600)
            offset = 0
            while offset < len(encoded):
                written = os.write(fd, encoded[offset:])
                if written <= 0:
                    raise OSError("memory state write made no progress")
                offset += written
            os.fsync(fd)
            os.close(fd)
            fd = -1
            os.replace(temporary, path)
            os.chmod(path, 0o600, follow_symlinks=False)
            os.fsync(directory_fd)
        except Exception:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
    finally:
        os.close(directory_fd)
