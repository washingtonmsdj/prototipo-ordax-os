#!/usr/bin/env python3
"""Compatibility wrapper for the shared OrdaX firmware-selection policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON_PATH = ROOT / "bootstrap" / "base" / "firmware_policy.py"

spec = importlib.util.spec_from_file_location("ordax_base_firmware_policy", COMMON_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load shared firmware policy: {COMMON_PATH}")
COMMON = importlib.util.module_from_spec(spec)
spec.loader.exec_module(COMMON)

for _name in dir(COMMON):
    if not _name.startswith("_"):
        globals()[_name] = getattr(COMMON, _name)
