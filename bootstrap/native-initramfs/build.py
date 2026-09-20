#!/usr/bin/env python3
"""Build the dedicated OrdaX Native LUKS2/Btrfs initramfs.

The USB initramfs remains a separate minimal owner. This builder consumes only
an already pinned Ubuntu image/snapshot environment and refuses artifact
construction until the exact runtime closure is locked in the environment
contract.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "bootstrap" / "native-initramfs"
SOURCE_CONTRACT = HERE / "source.json"
ENV_CONTRACT = ROOT / "docs" / "contracts" / "native-initramfs-build-environment.json"
BOOT_CONTRACT = ROOT / "docs" / "contracts" / "native-boot.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
REQUIRED_BUSYBOX_APPLETS = {"sh", "mount", "umount", "cat", "mkdir", "tr"}
PRIMARY_BINARIES = ("/usr/sbin/cryptsetup", "/usr/bin/btrfs")


class BuildError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, schema: str, label: str) -> dict:
    try:
        info = path.lstat()
    except OSError as exc:
        raise BuildError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise BuildError(f"{label} must be a regular non-symlink file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict) or value.get("$schema") != schema:
        raise BuildError(f"unexpected {label} schema")
    return value


def source_contract() -> dict:
    return load_json(
        SOURCE_CONTRACT,
        "prototype-ordax.native-initramfs-source/1",
        "Native initramfs source contract",
    )


def environment_contract() -> dict:
    return load_json(
        ENV_CONTRACT,
        "prototype-ordax.native-initramfs-build-environment/1",
        "Native initramfs environment contract",
    )


def boot_contract() -> dict:
    return load_json(
        BOOT_CONTRACT,
        "prototype-ordax.native-boot/1",
        "Native boot contract",
    )


def source_init_path(source: dict) -> Path:
    relative = source.get("root_init")
    if not isinstance(relative, str):
        raise BuildError("Native root init path is missing")
    path = (ROOT / relative).resolve()
    if ROOT.resolve() not in path.parents or not path.is_file() or path.is_symlink():
        raise BuildError("Native root init path is missing or unsafe")
    return path


def check_contract() -> dict:
    source = source_contract()
    env = environment_contract()
    boot = boot_contract()
    init = source_init_path(source)
    text = init.read_text(encoding="utf-8")

    if source.get("product_mode") != "native-disk":
        raise BuildError("Native initramfs product mode is not native-disk")
    if source.get("boot_contract") != "docs/contracts/native-boot.json":
        raise BuildError("Native initramfs boot contract owner changed")
    if source.get("shared_kernel_contract") != "bootstrap/kernel/source.json":
        raise BuildError("Native initramfs must use the shared canonical kernel")
    if source.get("userspace", {}).get("network_clients_included") is not False:
        raise BuildError("network clients are forbidden in Native initramfs")
    if source.get("userspace", {}).get("git_included") is not False:
        raise BuildError("Git is forbidden in Native initramfs")
    if source.get("userspace", {}).get("package_manager_in_runtime") is not False:
        raise BuildError("package manager is forbidden in Native initramfs")
    if source.get("build", {}).get("physical_artifact_authorized") is not False:
        raise BuildError("Native initramfs source must not authorize physical use")

    required_markers = (
        "ordax.product_mode",
        "ordax.pool_uuid",
        "find_pool_device",
        '/sys/class/block/*',
        'cryptsetup isLuks --type luks2 "$candidate"',
        'cryptsetup isLuks --type luks2 "$POOL_DEVICE"',
        'cryptsetup open --readonly --type luks2',
        'cryptsetup open --type luks2',
        'mount -t btrfs -o ro,subvolid=5',
        'persistent_product_mode',
        'ORDAX_PRODUCT_MODE=native-disk',
        'ORDAX_STATE_DIR=/var/lib/ordax',
        'ORDAX_USER_HOME=/var/home',
        'exec "$BOOTSTRAP_PATH"',
    )
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        raise BuildError(f"Native root init is missing required boundaries: {missing}")
    forbidden = (
        "--key-file",
        "curl ",
        "wget ",
        "git ",
        "ssh ",
        "http://",
        "https://",
        "ordax.pool_key",
        "findfs ",
    )
    leaked = [marker for marker in forbidden if marker in text]
    if leaked:
        raise BuildError(f"forbidden secret/network behavior leaked into Native initramfs: {leaked}")

    if boot.get("shared_kernel") is not True or boot.get("separate_native_kernel") is not False:
        raise BuildError("Native boot must share the canonical kernel")
    if boot.get("secret_policy", {}).get("luks_key_in_esp") is not False:
        raise BuildError("Native boot secret policy allows ESP key material")
    if boot.get("secret_policy", {}).get("luks_passphrase_in_kernel_cmdline") is not False:
        raise BuildError("Native boot secret policy allows cmdline passphrase")

    gate = env.get("gate", {})
    observation_complete = gate.get("environment_observation_complete") is True
    versions_pinned = gate.get("versions_pinned") is True
    artifact_build_allowed = gate.get("artifact_build_allowed") is True
    expected_top = env.get("apt", {}).get("expected_top_level_versions")
    expected_closure = env.get("apt", {}).get("runtime_closure_expected_packages")
    if not isinstance(expected_top, dict) or not isinstance(expected_closure, dict):
        raise BuildError("Native initramfs package locks must be objects")
    if artifact_build_allowed and not (
        observation_complete and versions_pinned and expected_top and expected_closure
    ):
        raise BuildError("Native initramfs artifact gate is inconsistent")

    try:
        subprocess.run(["sh", "-n", str(init)], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError("Native root init shell syntax is invalid") from exc

    return {
        "status": "contract-valid",
        "root_init": str(init.relative_to(ROOT)),
        "root_init_sha256": sha256_file(init),
        "environment_observation_complete": observation_complete,
        "versions_pinned": versions_pinned,
        "artifact_build_allowed": artifact_build_allowed,
        "physical_artifact_authorized": False,
    }


def capture(argv: list[str]) -> str:
    try:
        return subprocess.run(
            argv,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError(f"command failed: {' '.join(argv)}") from exc


def installed_version(package: str) -> str:
    return capture(["dpkg-query", "-W", "-f=${Version}", package])


def runtime_files(binary: str) -> list[str]:
    lines = capture(["lddtree", "-l", binary]).splitlines()
    files = sorted(set(line.strip() for line in lines if line.strip()))
    if binary not in files:
        files.append(binary)
        files.sort()
    return files


def package_path_candidates(path: str) -> list[str]:
    candidates: list[str] = []
    original = Path(path)
    try:
        candidates.append(str(original.resolve(strict=True)))
    except OSError:
        pass
    candidates.append(path)

    aliases: list[str] = []
    for candidate in list(candidates):
        for left, right in (
            ("/usr/bin/", "/bin/"),
            ("/usr/sbin/", "/sbin/"),
            ("/usr/lib/", "/lib/"),
            ("/usr/lib64/", "/lib64/"),
        ):
            if candidate.startswith(left):
                aliases.append(right + candidate[len(left):])
            elif candidate.startswith(right):
                aliases.append(left + candidate[len(right):])
    candidates.extend(aliases)
    return list(dict.fromkeys(candidates))


def package_owner(path: str) -> str:
    output = ""
    selected = ""
    for candidate in package_path_candidates(path):
        try:
            output = capture(["dpkg-query", "-S", candidate])
            selected = candidate
            break
        except BuildError:
            continue
    if not output:
        raise BuildError(f"cannot determine package owner for runtime path: {path}")

    first = output.splitlines()[0]
    owner, separator, _ = first.partition(": ")
    if not separator:
        raise BuildError(f"cannot parse package owner for runtime path: {selected}")
    owner = owner.split(":", 1)[0]
    if not PACKAGE_RE.fullmatch(owner):
        raise BuildError(f"unsafe package owner for runtime path: {selected}")
    return owner


def verify_build_environment(env: dict) -> dict:
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "amd64"}:
        raise BuildError("Native initramfs build requires x86_64 Linux")
    gate = env["gate"]
    if not (
        gate.get("environment_observation_complete") is True
        and gate.get("versions_pinned") is True
        and gate.get("artifact_build_allowed") is True
    ):
        raise BuildError("Native initramfs environment lock is incomplete; artifact build is blocked")

    expected_image = env["base_image"]["repository"] + "@" + env["base_image"]["manifest_digest"]
    actual_image = os.environ.get("ORDAX_BASE_IMAGE", "")
    actual_snapshot = os.environ.get("ORDAX_APT_SNAPSHOT_ID", "")
    if actual_image != expected_image:
        raise BuildError("Native initramfs build image identity does not match contract")
    if actual_snapshot != env["apt"]["snapshot_id"]:
        raise BuildError("Native initramfs APT snapshot does not match contract")

    observed_top = {
        package: installed_version(package)
        for package in sorted(env["apt"]["expected_top_level_versions"])
    }
    if observed_top != env["apt"]["expected_top_level_versions"]:
        raise BuildError("Native initramfs top-level package versions do not match lock")

    closure_files: set[str] = set()
    for binary in PRIMARY_BINARIES:
        if not Path(binary).is_file() or Path(binary).is_symlink():
            raise BuildError(f"required runtime binary is missing or unsafe: {binary}")
        closure_files.update(runtime_files(binary))
    observed_closure = {}
    for path in sorted(closure_files):
        owner = package_owner(path)
        observed_closure[owner] = installed_version(owner)
    if dict(sorted(observed_closure.items())) != env["apt"]["runtime_closure_expected_packages"]:
        raise BuildError("Native initramfs dynamic runtime closure does not match package lock")

    applets = set(capture(["/bin/busybox", "--list"]).splitlines())
    missing = sorted(REQUIRED_BUSYBOX_APPLETS - applets)
    if missing:
        raise BuildError(f"busybox-static lacks required Native applets: {missing}")
    return {
        "top_level_versions": observed_top,
        "runtime_closure_packages": dict(sorted(observed_closure.items())),
        "runtime_files": sorted(closure_files),
        "busybox_applets": sorted(REQUIRED_BUSYBOX_APPLETS),
    }


def copy_regular(source: Path, destination: Path, mode: int | None = None) -> None:
    if not source.is_file() or source.is_symlink():
        raise BuildError(f"runtime source is missing or unsafe: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(mode if mode is not None else stat.S_IMODE(source.stat().st_mode))


def build_rootfs(source: dict, environment: dict, work: Path) -> tuple[Path, dict]:
    observed = verify_build_environment(environment)
    rootfs = work / "rootfs"
    rootfs.mkdir(parents=True)

    for relative in (
        "bin", "sbin", "usr/bin", "usr/sbin", "lib", "lib64",
        "proc", "sys", "dev", "run", "ordax", "var", "home",
    ):
        (rootfs / relative).mkdir(parents=True, exist_ok=True)

    copy_regular(Path("/bin/busybox"), rootfs / "bin/busybox", 0o755)
    applet_locations = {
        "sh": "bin/sh",
        "mount": "bin/mount",
        "umount": "bin/umount",
        "cat": "bin/cat",
        "mkdir": "bin/mkdir",
        "findfs": "bin/findfs",
        "tr": "bin/tr",
    }
    for relative in applet_locations.values():
        target = rootfs / relative
        target.symlink_to("/bin/busybox")

    for binary in PRIMARY_BINARIES:
        copy_regular(Path(binary), rootfs / binary.lstrip("/"), 0o755)

    copied_runtime = {}
    for path_text in observed["runtime_files"]:
        source_path = Path(path_text)
        if path_text in PRIMARY_BINARIES:
            continue
        if not source_path.exists():
            raise BuildError(f"dynamic runtime file disappeared: {path_text}")
        resolved = source_path.resolve()
        if not resolved.is_file():
            raise BuildError(f"dynamic runtime file is not regular: {path_text}")
        destination = rootfs / path_text.lstrip("/")
        copy_regular(resolved, destination)
        copied_runtime[path_text] = sha256_file(destination)

    init = source_init_path(source)
    copy_regular(init, rootfs / "init", 0o755)

    forbidden_names = {"apt", "apt-get", "dpkg", "curl", "wget", "git", "ssh"}
    leaked = [
        path.relative_to(rootfs).as_posix()
        for path in rootfs.rglob("*")
        if path.name in forbidden_names
    ]
    if leaked:
        raise BuildError(f"forbidden package/network tools leaked into initramfs: {leaked}")

    return rootfs, {
        **observed,
        "copied_runtime_sha256": dict(sorted(copied_runtime.items())),
    }


def normalize_tree(rootfs: Path) -> None:
    for path in [rootfs] + sorted(rootfs.rglob("*"), key=lambda item: item.as_posix()):
        try:
            os.utime(path, (0, 0), follow_symlinks=False)
        except (NotImplementedError, OSError) as exc:
            raise BuildError(f"cannot normalize initramfs timestamp: {path}") from exc


def build_archive(rootfs: Path, destination: Path) -> None:
    cpio = shutil.which("cpio")
    if not cpio:
        raise BuildError("GNU cpio is required to build Native initramfs")
    normalize_tree(rootfs)
    names = ["."] + [
        "./" + path.relative_to(rootfs).as_posix()
        for path in sorted(rootfs.rglob("*"), key=lambda item: item.relative_to(rootfs).as_posix())
    ]
    payload = ("\0".join(names) + "\0").encode("utf-8")
    try:
        result = subprocess.run(
            [
                cpio,
                "--null",
                "--create",
                "--format=newc",
                "--owner=0:0",
                "--reproducible",
                "--quiet",
            ],
            cwd=rootfs,
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError("deterministic Native cpio construction failed") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0, compresslevel=9) as gz:
            gz.write(result.stdout)


def git_head() -> str:
    value = os.environ.get("GITHUB_SHA", "")
    if re.fullmatch(r"[0-9a-fA-F]{40}", value):
        return value.lower()
    try:
        return capture(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    except BuildError:
        return "unknown"


def build(out_dir: Path) -> dict:
    source = source_contract()
    env = environment_contract()
    check_contract()

    out_dir = out_dir.resolve()
    if out_dir == ROOT or ROOT in out_dir.parents:
        raise BuildError("Native initramfs output must be outside repository source")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    work = Path(tempfile.mkdtemp(prefix="ordax-native-initramfs-"))
    try:
        rootfs, environment = build_rootfs(source, env, work)
        artifact = out_dir / "native-initramfs.cpio.gz"
        build_archive(rootfs, artifact)
        if artifact.stat().st_size <= 0 or artifact.stat().st_size > 128 * 1024 * 1024:
            raise BuildError("Native initramfs artifact size is invalid")

        provenance = {
            "$schema": "prototype-ordax.native-initramfs-provenance/1",
            "status": "candidate",
            "source_commit": git_head(),
            "product_mode": "native-disk",
            "physical_artifact_authorized": False,
            "source_contract_sha256": sha256_file(SOURCE_CONTRACT),
            "environment_contract_sha256": sha256_file(ENV_CONTRACT),
            "boot_contract_sha256": sha256_file(BOOT_CONTRACT),
            "root_init_sha256": sha256_file(source_init_path(source)),
            "environment": environment,
            "artifact": {
                "name": artifact.name,
                "sha256": sha256_file(artifact),
                "size": artifact.stat().st_size,
            },
        }
        provenance_path = out_dir / "native-initramfs-provenance.json"
        provenance_path.write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (out_dir / "SHA256SUMS").write_text(
            f"{sha256_file(artifact)}  {artifact.name}\n"
            f"{sha256_file(provenance_path)}  {provenance_path.name}\n",
            encoding="utf-8",
        )
        return provenance
    finally:
        shutil.rmtree(work, ignore_errors=True)


def verify(out_dir: Path) -> dict:
    check_contract()
    out_dir = out_dir.resolve()
    artifact = out_dir / "native-initramfs.cpio.gz"
    provenance_path = out_dir / "native-initramfs-provenance.json"
    sums_path = out_dir / "SHA256SUMS"
    for path in (artifact, provenance_path, sums_path):
        if not path.is_file() or path.is_symlink():
            raise BuildError(f"Native initramfs output missing or unsafe: {path.name}")

    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("$schema") != "prototype-ordax.native-initramfs-provenance/1":
        raise BuildError("unexpected Native initramfs provenance schema")
    if provenance.get("physical_artifact_authorized") is not False:
        raise BuildError("Native initramfs provenance crossed physical gate")
    if provenance.get("product_mode") != "native-disk":
        raise BuildError("Native initramfs provenance product mode is invalid")
    recorded = provenance.get("artifact", {})
    if (
        recorded.get("name") != artifact.name
        or recorded.get("sha256") != sha256_file(artifact)
        or recorded.get("size") != artifact.stat().st_size
    ):
        raise BuildError("Native initramfs artifact disagrees with provenance")

    entries = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._+-]*)", line)
        if not match or match.group(2) in entries:
            raise BuildError("Native initramfs checksum manifest is malformed")
        entries[match.group(2)] = match.group(1)
    if set(entries) != {"native-initramfs.cpio.gz", "native-initramfs-provenance.json"}:
        raise BuildError("Native initramfs checksum manifest has unexpected entries")
    for name, digest in entries.items():
        if sha256_file(out_dir / name) != digest:
            raise BuildError(f"Native initramfs checksum mismatch: {name}")

    return {
        "status": "verified",
        "artifact_sha256": recorded["sha256"],
        "artifact_size": recorded["size"],
        "physical_artifact_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    b = sub.add_parser("build")
    b.add_argument("--out-dir", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "check":
            result = check_contract()
        elif args.command == "build":
            result = build(args.out_dir)
        else:
            result = verify(args.out_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (BuildError, OSError, json.JSONDecodeError) as exc:
        print(f"native-initramfs-build: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
