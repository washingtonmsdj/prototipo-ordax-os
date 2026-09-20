#!/usr/bin/env python3
"""Read-only MVP Surface smoke collector for the OrdaX Native runtime."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

SCHEMA = "ordax.mvp-surface-smoke/1"
SOURCE_ROOT = Path("/srv/ordax-system")
RUN_ROOT = Path("/run/ordax-surface")
EVIDENCE_ROOT = Path("/var/lib/ordax/mvp-smoke")
PROC_ROOT = Path("/proc")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_BODY = 2 * 1024 * 1024

REQUIRED_SOURCE_FILES = (
    "apps/files/app.mjs",
    "apps/notes/app.mjs",
    "apps/internet/app.mjs",
    "apps/settings/app.mjs",
    "apps/system/app.mjs",
    "composition/native/main.mjs",
    "surface/ui/surface.mjs",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"id": name, "status": "pass" if ok else "fail", "detail": detail}


def _warn(name: str, detail: str) -> dict:
    return {"id": name, "status": "warn", "detail": detail}


def _summary(checks: list[dict]) -> dict:
    return {status: sum(item["status"] == status for item in checks) for status in ("pass", "warn", "fail")}


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _boot_id(proc_root: Path = PROC_ROOT) -> str | None:
    try:
        return (proc_root / "sys/kernel/random/boot_id").read_text(encoding="ascii").strip() or None
    except OSError:
        return None


def _bounded_json(body: bytes) -> object:
    if len(body) > MAX_BODY:
        raise ValueError(f"response exceeds {MAX_BODY} bytes")
    return json.loads(body.decode("utf-8"))


def _http_get(host: str, port: int, target: str, timeout: float) -> tuple[int, dict[str, str], bytes]:
    authority = f"{host}:{port}"
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    connection.putrequest("GET", target, skip_host=True, skip_accept_encoding=True)
    connection.putheader("Host", authority)
    connection.putheader("Accept", "application/json, text/html;q=0.9, */*;q=0.1")
    connection.endheaders()
    response = connection.getresponse()
    body = response.read(MAX_BODY + 1)
    headers = {name.lower(): value for name, value in response.getheaders()}
    status = response.status
    connection.close()
    if len(body) > MAX_BODY:
        raise ValueError(f"response exceeds {MAX_BODY} bytes")
    return status, headers, body


def source_snapshot(source_root: Path = SOURCE_ROOT) -> tuple[dict, list[dict]]:
    files = {}
    checks = []
    for relative in REQUIRED_SOURCE_FILES:
        path = source_root / relative
        try:
            data = path.read_bytes()
        except OSError as exc:
            checks.append(_check(f"source:{relative}", False, f"arquivo indisponível: {exc}"))
            continue
        files[relative] = {"size": len(data), "sha256": _sha(data)}
        checks.append(_check(f"source:{relative}", bool(data), f"{len(data)} bytes"))
    return {"files": files}, checks


def validate_metrics(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("metrics payload must be an object")
    fields = (
        "uptimeSeconds",
        "memoryTotalBytes",
        "memoryAvailableBytes",
        "userStorageTotalBytes",
        "userStorageFreeBytes",
    )
    for field in fields:
        item = value.get(field)
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise ValueError(f"invalid metrics field: {field}")
    if value["memoryAvailableBytes"] > value["memoryTotalBytes"]:
        raise ValueError("available memory exceeds total")
    if value["userStorageFreeBytes"] > value["userStorageTotalBytes"]:
        raise ValueError("free user storage exceeds total")
    return {
        "uptime_seconds": value["uptimeSeconds"],
        "memory_total_bytes": value["memoryTotalBytes"],
        "memory_available_bytes": value["memoryAvailableBytes"],
        "user_storage_total_bytes": value["userStorageTotalBytes"],
        "user_storage_free_bytes": value["userStorageFreeBytes"],
    }


def validate_network(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get("interfaces"), list):
        raise ValueError("network payload must contain interfaces")
    interfaces = value["interfaces"]
    if len(interfaces) > 64:
        raise ValueError("too many interfaces")
    kinds = {"wifi": 0, "ethernet": 0, "other": 0}
    states = {"connected": 0, "disconnected": 0, "unknown": 0}
    names = set()
    for item in interfaces:
        if not isinstance(item, dict):
            raise ValueError("invalid network interface")
        name = item.get("name")
        kind = item.get("kind")
        state = item.get("state")
        signal = item.get("signalDbm")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("invalid or duplicate interface name")
        if kind not in kinds or state not in states:
            raise ValueError("invalid interface kind/state")
        if signal is not None and (kind != "wifi" or not isinstance(signal, int) or isinstance(signal, bool) or signal < -200 or signal > 0):
            raise ValueError("invalid signal")
        names.add(name)
        kinds[kind] += 1
        states[state] += 1
    return {"interface_count": len(interfaces), "kinds": kinds, "states": states}


def validate_power(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("power payload must be an object")
    battery = value.get("battery")
    external = value.get("externalPower")
    if external is not None and not isinstance(external, bool):
        raise ValueError("invalid externalPower")
    if battery is None:
        return {"battery_present": False, "battery_percent": None, "battery_state": None, "external_power": external}
    if not isinstance(battery, dict):
        raise ValueError("invalid battery")
    percent = battery.get("percent")
    state = battery.get("state")
    if not isinstance(percent, int) or isinstance(percent, bool) or not 0 <= percent <= 100:
        raise ValueError("invalid battery percent")
    if state not in {"charging", "discharging", "full", "not-charging", "unknown"}:
        raise ValueError("invalid battery state")
    return {"battery_present": True, "battery_percent": percent, "battery_state": state, "external_power": external}


def _valid_logical_path(path: object) -> bool:
    if not isinstance(path, str) or not path.startswith("/"):
        return False
    if path != "/" and path.endswith("/"):
        return False
    if path == "/":
        return True
    return all(part and part not in {".", ".."} and "\0" not in part for part in path.split("/")[1:])


def validate_files(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get("entries"), list):
        raise ValueError("file listing must contain entries")
    if not _valid_logical_path(value.get("path")):
        raise ValueError("invalid file listing path")
    file_count = 0
    directory_count = 0
    for entry in value["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("invalid file entry")
        name = entry.get("name")
        kind = entry.get("kind")
        size = entry.get("size")
        modified = entry.get("modifiedAt")
        if not isinstance(name, str) or not name or "/" in name or "\0" in name or name in {".", ".."}:
            raise ValueError("invalid file entry name")
        if kind not in {"file", "directory"}:
            raise ValueError("invalid file entry kind")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("invalid file entry size")
        if not isinstance(modified, int) or isinstance(modified, bool) or modified < 0:
            raise ValueError("invalid file modifiedAt")
        if kind == "file":
            file_count += 1
        else:
            directory_count += 1
    return {
        "path": value["path"],
        "entry_count": len(value["entries"]),
        "file_count": file_count,
        "directory_count": directory_count,
    }


def validate_update_history(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("update history payload must be an object")
    releases = value.get("releases")
    applications = value.get("applications")
    if not isinstance(releases, list) or len(releases) > 80:
        raise ValueError("invalid releases")
    if not isinstance(applications, list) or len(applications) > 200:
        raise ValueError("invalid applications")
    results = {"applied": 0, "rolled-back": 0}
    for item in applications:
        if not isinstance(item, dict) or item.get("result") not in results:
            raise ValueError("invalid update application")
        results[item["result"]] += 1
    return {
        "release_count": len(releases),
        "application_count": len(applications),
        "results": results,
    }


def live_surface_checks(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 1.5) -> tuple[dict, list[dict]]:
    checks = []
    observed = {}

    try:
        status, headers, body = _http_get(host, port, "/composition/native/index.html", timeout)
        ok = status == 200 and bool(body)
        checks.append(_check("surface_document", ok, f"HTTP {status}; {len(body)} bytes"))
        observed["surface_document"] = {
            "status": status,
            "size": len(body),
            "sha256": _sha(body) if body else None,
            "content_type": headers.get("content-type"),
        }
    except (OSError, ValueError) as exc:
        checks.append(_check("surface_document", False, f"probe falhou: {exc}"))

    probes = (
        ("system_metrics", "/__ordax/native/metrics", validate_metrics),
        ("network_status", "/__ordax/native/network-status", validate_network),
        ("power_status", "/__ordax/native/power-status", validate_power),
        ("file_space_root", f"/__ordax/native/files?path={quote('/', safe='')}", validate_files),
        ("update_history", "/__ordax/native/update-history", validate_update_history),
    )
    for name, target, validator in probes:
        try:
            status, _headers, body = _http_get(host, port, target, timeout)
            if status != 200:
                checks.append(_check(name, False, f"HTTP {status}; esperado 200"))
                continue
            summary = validator(_bounded_json(body))
            observed[name] = summary
            checks.append(_check(name, True, "HTTP 200; payload válido"))
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            checks.append(_check(name, False, f"probe falhou: {exc}"))
    return observed, checks


def host_log_snapshot(run_root: Path = RUN_ROOT) -> tuple[dict, list[dict]]:
    path = run_root / "host.log"
    try:
        data = path.read_bytes()[-64 * 1024 :]
    except OSError as exc:
        return {"present": False, "tail_sha256": None, "error_markers": None}, [
            _check("surface_host_log", False, f"host.log indisponível: {exc}")
        ]
    lower = data.lower()
    markers = sum(lower.count(marker) for marker in (b"traceback", b"segmentation fault", b"fatal"))
    return {
        "present": True,
        "tail_sha256": _sha(data),
        "error_markers": markers,
    }, [
        _check("surface_host_log", markers == 0, f"{markers} marcador(es) fatal/traceback no tail")
    ]


def collect(
    label: str,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = 1.5,
    source_root: Path = SOURCE_ROOT,
    run_root: Path = RUN_ROOT,
    proc_root: Path = PROC_ROOT,
) -> dict:
    source, source_checks = source_snapshot(source_root)
    observed, live_checks = live_surface_checks(host, port, timeout)
    host_log, log_checks = host_log_snapshot(run_root)
    checks = [*source_checks, *live_checks, *log_checks]
    report = {
        "schema": SCHEMA,
        "captured_at": _timestamp(),
        "label": label,
        "boot_id": _boot_id(proc_root),
        "loopback": {"host": host, "port": port},
        "source": source,
        "observed": observed,
        "host_log": host_log,
        "checks": checks,
    }
    report["summary"] = _summary(checks)
    return report


def write_report(report: dict, output: Path | None) -> Path:
    path = output or (EVIDENCE_ROOT / f"mvp-smoke-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(serialized, encoding="utf-8")
    return path


def _print_summary(report: dict, path: Path) -> None:
    summary = report["summary"]
    print(f"REPORT={path}")
    print(f"PASS={summary['pass']} WARN={summary['warn']} FAIL={summary['fail']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collect", nargs="?", default="collect", choices=["collect"])
    parser.add_argument("--label", default="mvp-surface-smoke")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=1.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = collect(args.label, host=args.host, port=args.port, timeout=args.timeout)
    path = write_report(report, args.output)
    _print_summary(report, path)
    return 1 if report["summary"]["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
