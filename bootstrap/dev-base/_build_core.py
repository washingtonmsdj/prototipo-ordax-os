#!/usr/bin/env python3
"""Compatibility wrapper for the shared OrdaX Alpine base core.

New base profiles must import bootstrap/base/alpine_core.py directly. This path
remains so existing development tooling and external references do not break.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON_PATH = ROOT / "bootstrap" / "base" / "alpine_core.py"

spec = importlib.util.spec_from_file_location("ordax_alpine_base_core", COMMON_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load shared Alpine base core: {COMMON_PATH}")
COMMON = importlib.util.module_from_spec(spec)
spec.loader.exec_module(COMMON)

for _name in dir(COMMON):
    if not _name.startswith("_"):
        globals()[_name] = getattr(COMMON, _name)


def main() -> int:
    # Preserve the historical development builder's runtime monkey-patching
    # boundary used by bootstrap/dev-base/build.py.
    COMMON.required_firmware_names = globals()["required_firmware_names"]
    COMMON.prune_firmware = globals()["prune_firmware"]
    return COMMON.main()


if __name__ == "__main__":
    raise SystemExit(main())
