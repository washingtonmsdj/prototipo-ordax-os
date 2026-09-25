#!/usr/bin/env python3
"""Create a deterministic receipt for manual canonical-v4 operator artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Iterable

SCHEMA = "prototype-ordax.canonical-v4-operator-artifact/1"
EXPECTED_FILES = {
    "system": ("system.erofs",),
    "surface": ("native-surface-runtime.erofs",),
    "local-ai": ("local-ai-runtime.erofs", "source-lock.json"),
}


def _binding(path: Path) -> tuple[str, int]:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"operator artifact must be a regular non-symlink file: {path}")
    if metadata.st_size <= 0:
        raise ValueError(f"operator artifact is empty: {path}")

    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _parse_file_specs(values: Iterable[str]) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError("--file must use logical-name=path")
        logical_name, raw_path = raw.split("=", 1)
        logical_name = logical_name.strip()
        if not logical_name or logical_name in files:
            raise ValueError(f"invalid or duplicate logical file name: {logical_name!r}")
        files[logical_name] = Path(raw_path).resolve()
    return files


def build_receipt(kind: str, source_commit: str, files: dict[str, Path]) -> dict:
    if kind not in EXPECTED_FILES:
        raise ValueError(f"unsupported operator artifact kind: {kind}")
    if len(source_commit) != 40 or source_commit.lower() != source_commit:
        raise ValueError("source commit must be lowercase 40-hex")
    try:
        int(source_commit, 16)
    except ValueError as exc:
        raise ValueError("source commit must be lowercase 40-hex") from exc

    expected = set(EXPECTED_FILES[kind])
    actual = set(files)
    if actual != expected:
        raise ValueError(
            f"{kind} operator artifact files must be exactly {sorted(expected)!r}; "
            f"got {sorted(actual)!r}"
        )

    bindings = []
    for logical_name in EXPECTED_FILES[kind]:
        path = files[logical_name]
        sha256, size = _binding(path)
        bindings.append(
            {
                "name": logical_name,
                "sha256": sha256,
                "size": size,
            }
        )

    return {
        "$schema": SCHEMA,
        "kind": kind,
        "source_commit": source_commit,
        "files": bindings,
        "publication_performed": False,
        "signing_performed": False,
        "release_activated": False,
        "physical_target_selected": False,
        "physical_write_authorized": False,
        "physical_write_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(EXPECTED_FILES), required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--file", action="append", default=[], required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        files = _parse_file_specs(args.file)
        receipt = build_receipt(args.kind, args.source_commit, files)
        output = args.out.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_name(f".{output.name}.tmp-{os.getpid()}")
        temp.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temp, output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
