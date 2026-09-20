#!/bin/sh
set -eu

PATH=/sbin:/bin:/usr/sbin:/usr/bin
export PATH

ESP_MOUNT=/ordax-esp
DATA_MOUNT=/ordax-data
STATE_MOUNT=/state
CAPSULE_MOUNT=/bootstrap-capsule
BASE_MOUNT=/base-lower
RELEASE_MOUNT=/release-lower
NEWROOT=/newroot

CAPSULE_IMAGE="$ESP_MOUNT/ordax/bootstrap/bootstrap.erofs"
TRUST_ANCHOR="$ESP_MOUNT/ordax/bootstrap/trust/release-ed25519.json"
STATE_IMAGE="$DATA_MOUNT/.ordax/state/persistent-state.img"
STABLE_BASE_IMAGE="$DATA_MOUNT/.ordax/base/stable-base.erofs"
PORTABLE_ROOT="$DATA_MOUNT/.ordax"

rescue() {
    echo "ordax-portable-init: entering local read-only recovery shell: $*" >&2
    echo "No network or automatic mutation is started from this recovery path." >&2
    exec sh
}

is_sha() {
    value=${1:-}
    [ "${#value}" -eq 40 ] || return 1
    case "$value" in
        ''|*[!0-9a-f]*) return 1 ;;
    esac
}

mkdir -p /proc /sys /dev /run "$ESP_MOUNT" "$DATA_MOUNT"     "$STATE_MOUNT" "$CAPSULE_MOUNT" "$BASE_MOUNT" "$RELEASE_MOUNT" "$NEWROOT"
mount -t proc proc /proc || rescue "cannot mount /proc"
mount -t sysfs sysfs /sys || rescue "cannot mount /sys"
mount -t devtmpfs devtmpfs /dev || rescue "cannot mount /dev"
mount -t tmpfs -o mode=0755 tmpfs /run || rescue "cannot mount /run"

ESP_DEVICE="$(findfs LABEL=ORDAX-ESP 2>/dev/null || true)"
case "$ESP_DEVICE" in
    "") rescue "ORDAX-ESP partition not found" ;;
esac
mount -t vfat -o ro,nodev,nosuid "$ESP_DEVICE" "$ESP_MOUNT" ||
    rescue "cannot mount ORDAX-ESP read-only"

/sbin/ordax-portable-capsule-verify verify ||
    rescue "bootstrap capsule does not match the fixed initramfs pin"
/sbin/ordax-portable-mount mount-capsule "$CAPSULE_IMAGE" "$CAPSULE_MOUNT" ||
    rescue "cannot mount verified bootstrap capsule"

RECOVERY_MODE=0
case " $(cat /proc/cmdline 2>/dev/null || true) " in
    *" ordax.mode=recovery "*) RECOVERY_MODE=1 ;;
esac

DATA_DEVICE="$(findfs LABEL=ORDAX-DATA 2>/dev/null || true)"
case "$DATA_DEVICE" in
    "") rescue "ORDAX-DATA partition not found" ;;
esac

case "$RECOVERY_MODE" in
    1)
        mount -t exfat -o ro,nodev,nosuid "$DATA_DEVICE" "$DATA_MOUNT" ||
            rescue "cannot mount ORDAX-DATA read-only for recovery"
        rescue "portable-v2 recovery mode requested"
        ;;
esac

mount -t exfat -o rw,nodev,nosuid "$DATA_DEVICE" "$DATA_MOUNT" ||
    rescue "cannot mount ORDAX-DATA"

/sbin/ordax-portable-base-verify verify ||
    rescue "Stable Base does not match the fixed initramfs pin"

/sbin/ordax-portable-mount mount-state "$STATE_IMAGE" "$STATE_MOUNT" ||
    rescue "cannot mount persistent ext4 state"

AGENT="$CAPSULE_MOUNT/bootstrap/release-acquisition/ordax-release-agent"
cat "$AGENT" >/dev/null 2>&1 || rescue "release agent is missing from verified capsule"
cat "$TRUST_ANCHOR" >/dev/null 2>&1 || rescue "bootstrap-owned release trust anchor is missing"

SELECTED_SLOT=
SELECTED_COMMIT=
select_verified_release() {
    for slot in current known-good; do
        commit="$(/sbin/ordax-portable-state resolve "$STATE_MOUNT" "$PORTABLE_ROOT" "$slot" 2>/dev/null || true)"
        is_sha "$commit" || continue
        if "$AGENT" verify-portable-exact             --trust "$TRUST_ANCHOR"             --root "$PORTABLE_ROOT"             --expected-commit "$commit"             >"/run/portable-release-verify.json"; then
            SELECTED_SLOT=$slot
            SELECTED_COMMIT=$commit
            return 0
        fi
    done
    return 1
}

select_verified_release ||
    rescue "neither current nor known-good is an exactly verified signed release"

mkdir -p "$BASE_MOUNT" "$NEWROOT" "$RELEASE_MOUNT"
/sbin/ordax-portable-mount mount-base     "$STABLE_BASE_IMAGE" "$STATE_MOUNT" "$BASE_MOUNT" "$NEWROOT" ||
    rescue "cannot compose verified Stable Base runtime"

mkdir -p "$NEWROOT/system"
/sbin/ordax-portable-mount mount-system     "$PORTABLE_ROOT/releases/$SELECTED_COMMIT/system.erofs"     "$RELEASE_MOUNT"     "$NEWROOT/system" ||
    rescue "cannot mount exactly verified product system release"

mkdir -p     "$NEWROOT/proc"     "$NEWROOT/sys"     "$NEWROOT/dev"     "$NEWROOT/run"     "$NEWROOT/state"     "$NEWROOT/ordax-data"     "$NEWROOT/ordax-esp"     "$NEWROOT/ordax/bootstrap"

mount --move /run "$NEWROOT/run" || rescue "cannot move /run into Stable Base"
mkdir -p     "$NEWROOT/run/ordax/lower/base"     "$NEWROOT/run/ordax/lower/release"     "$NEWROOT/run/ordax/lower/capsule"

mount --move "$BASE_MOUNT" "$NEWROOT/run/ordax/lower/base" ||
    rescue "cannot retain Stable Base lower mount"
mount --move "$RELEASE_MOUNT" "$NEWROOT/run/ordax/lower/release" ||
    rescue "cannot retain product release lower mount"
mount --move "$CAPSULE_MOUNT" "$NEWROOT/run/ordax/lower/capsule" ||
    rescue "cannot retain bootstrap capsule lower mount"

mount "$NEWROOT/run/ordax/lower/capsule/bootstrap" "$NEWROOT/ordax/bootstrap"     -o bind,ro ||
    rescue "cannot expose verified bootstrap support tree"
mount -o remount,bind,ro,nodev,nosuid "$NEWROOT/ordax/bootstrap" ||
    rescue "cannot enforce read-only bootstrap support tree"

mount --move "$STATE_MOUNT" "$NEWROOT/state" ||
    rescue "cannot move persistent state into Stable Base"
mount --move "$DATA_MOUNT" "$NEWROOT/ordax-data" ||
    rescue "cannot move ORDAX-DATA into Stable Base"
mount --move "$ESP_MOUNT" "$NEWROOT/ordax-esp" ||
    rescue "cannot move ORDAX-ESP into Stable Base"
mount --move /proc "$NEWROOT/proc" || rescue "cannot move /proc"
mount --move /sys "$NEWROOT/sys" || rescue "cannot move /sys"
mount --move /dev "$NEWROOT/dev" || rescue "cannot move /dev"

export ORDAX_DISTRIBUTION_PROFILE=stable-mvp
export ORDAX_PRODUCT_MODE=usb
export ORDAX_STABLE_LAYOUT=portable-v2
export ORDAX_SOURCE_SHA="$SELECTED_COMMIT"
export ORDAX_BOOT_SLOT="$SELECTED_SLOT"

echo "ORDAX_PORTABLE_V2_HANDOFF=VERIFIED"
echo "ORDAX_PORTABLE_V2_SLOT=$SELECTED_SLOT"
echo "ORDAX_PORTABLE_V2_SOURCE_SHA=$SELECTED_COMMIT"

exec switch_root "$NEWROOT" /sbin/ordax-stable-init
