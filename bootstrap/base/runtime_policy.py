#!/usr/bin/env python3
"""Shared runtime-pruning policy for Alpine-based OrdaX base profiles."""

from __future__ import annotations

from pathlib import Path
import shutil

BUILD_ONLY_PACKAGES = ("zstd",)
RUNTIME_PRUNE_PATHS = (
    "etc/apk/repositories",
    "lib/apk/db",
    "var/cache/apk",
    "usr/share/doc",
    "usr/share/man",
)


def verify_runtime_acquisition_client(rootfs: Path, error_type) -> None:
    apk = rootfs / "sbin/apk"
    keys = rootfs / "etc/apk/keys"
    if not apk.is_file() or apk.is_symlink():
        raise error_type("runtime acquisition client is missing: /sbin/apk")
    if not keys.is_dir() or not any(path.is_file() for path in keys.glob("*.pub")):
        raise error_type("runtime acquisition trust keys are missing: /etc/apk/keys/*.pub")


def prune_build_only_runtime(
    rootfs: Path,
    *,
    proot_rootfs,
    error_type,
    log_prefix: str,
) -> None:
    command = "apk del --no-cache " + " ".join(BUILD_ONLY_PACKAGES)
    proot_rootfs(rootfs, command)

    for relative in RUNTIME_PRUNE_PATHS:
        path = rootfs / relative
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()

    for executable in ("usr/bin/zstd", "bin/zstd"):
        path = rootfs / executable
        if path.exists() or path.is_symlink():
            raise error_type(f"build-only executable remained in runtime: /{executable}")

    verify_runtime_acquisition_client(rootfs, error_type)
    print(
        f"{log_prefix}_BUILD_ONLY_PRUNED=" + ",".join(BUILD_ONLY_PACKAGES),
        flush=True,
    )
