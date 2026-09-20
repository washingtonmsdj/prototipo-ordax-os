#!/bin/sh
set -eu

PIN=/etc/ordax/portable-bootstrap-capsule.sha256
CAPSULE=/ordax-esp/ordax/bootstrap/bootstrap.erofs

case "${1:-}" in
    verify) ;;
    *)
        echo "usage: ordax-portable-capsule-verify verify" >&2
        exit 2
        ;;
esac

cat "$PIN" >/dev/null 2>&1 || {
    echo "ordax-portable-capsule-verify: capsule hash pin is missing or unreadable" >&2
    exit 1
}

cat "$CAPSULE" >/dev/null 2>&1 || {
    echo "ordax-portable-capsule-verify: bootstrap capsule is missing or unreadable" >&2
    exit 1
}

/bin/busybox sha256sum -c "$PIN" >/dev/null 2>&1 || {
    echo "ordax-portable-capsule-verify: bootstrap capsule SHA-256 does not match initramfs pin" >&2
    exit 1
}

echo "ORDAX_PORTABLE_BOOTSTRAP_CAPSULE=VERIFIED"
