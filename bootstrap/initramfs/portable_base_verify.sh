#!/bin/sh
set -eu

PIN=/etc/ordax/portable-stable-base.sha256
BASE=/ordax-data/.ordax/base/stable-base.erofs

case "${1:-}" in
    verify) ;;
    *)
        echo "usage: ordax-portable-base-verify verify" >&2
        exit 2
        ;;
esac

cat "$PIN" >/dev/null 2>&1 || {
    echo "ordax-portable-base-verify: Stable Base hash pin is missing or unreadable" >&2
    exit 1
}

cat "$BASE" >/dev/null 2>&1 || {
    echo "ordax-portable-base-verify: Stable Base is missing or unreadable" >&2
    exit 1
}

/bin/busybox sha256sum -c "$PIN" >/dev/null 2>&1 || {
    echo "ordax-portable-base-verify: Stable Base SHA-256 does not match initramfs pin" >&2
    exit 1
}

echo "ORDAX_PORTABLE_STABLE_BASE=VERIFIED"
