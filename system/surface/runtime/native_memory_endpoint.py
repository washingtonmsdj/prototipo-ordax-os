#!/usr/bin/env python3
"""Isolated request handler for the Native Intelligence memory loopback endpoint."""

from __future__ import annotations

import json

from native_memory_state import (
    DEFAULT_MEMORY_FILE,
    MAX_MEMORY_PAYLOAD_BYTES,
    read_memory_payload,
    valid_memory_payload,
    write_memory_payload,
)

MAX_MEMORY_REQUEST_BODY_BYTES = 6 * MAX_MEMORY_PAYLOAD_BYTES + 1024


class MemoryEndpointRequestError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def parse_memory_write_body(body: object) -> str | None:
    if not isinstance(body, (bytes, bytearray)):
        raise MemoryEndpointRequestError("memory request body must be bytes")
    if len(body) == 0:
        raise MemoryEndpointRequestError("memory request body is empty")
    if len(body) > MAX_MEMORY_REQUEST_BODY_BYTES:
        raise MemoryEndpointRequestError(
            "memory request body exceeds its byte limit",
            status_code=413,
        )
    try:
        request = json.loads(bytes(body).decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MemoryEndpointRequestError("memory request body is invalid JSON") from exc
    if not isinstance(request, dict) or set(request) != {"payload"}:
        raise MemoryEndpointRequestError("memory request body shape is invalid")
    payload = request.get("payload")
    if not valid_memory_payload(payload):
        raise MemoryEndpointRequestError("memory snapshot payload is invalid")
    return payload


def read_memory_endpoint(path: str = DEFAULT_MEMORY_FILE) -> dict:
    return {"payload": read_memory_payload(path)}


def write_memory_endpoint(body: bytes, path: str = DEFAULT_MEMORY_FILE) -> dict:
    payload = parse_memory_write_body(body)
    write_memory_payload(payload, path)
    return {"ok": True}
