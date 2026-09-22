#!/bin/sh

select_ordax_physical_proof_runtime() {
    proof_name=${1:-ordax-proof}
    STATE_ROOT=${ORDAX_STATE_DIR:-/state/ordax}
    RUNTIME_ID=alpine-v3.22-cage-webkitgtk-v1
    PROOF_DISTRIBUTION_PROFILE=${ORDAX_DISTRIBUTION_PROFILE:-owner-development}
    PROOF_RUNTIME_MODE=dynamic-native-runtime
    PROOF_EVIDENCE_SCOPE=development
    RUNTIME_ROOT=$STATE_ROOT/runtime/native-surface/$RUNTIME_ID/rootfs

    case "$PROOF_DISTRIBUTION_PROFILE" in
        owner-development)
            ;;
        stable-mvp)
            [ "${ORDAX_SURFACE_RUNTIME_MODE:-}" = "verified-erofs-overlay" ] || {
                echo "$proof_name: Stable/MVP proof requires the verified EROFS Surface runtime" >&2
                return 2
            }
            [ "${ORDAX_SURFACE_RUNTIME_ROOT:-}" = "/run/ordax/runtime/native-surface/rootfs" ] || {
                echo "$proof_name: Stable/MVP verified runtime root is invalid" >&2
                return 2
            }
            runtime_digest=${ORDAX_SURFACE_RUNTIME_SHA256:-}
            [ "${#runtime_digest}" -eq 64 ] || {
                echo "$proof_name: Stable/MVP verified runtime digest is invalid" >&2
                return 2
            }
            case "$runtime_digest" in
                *[!0-9a-f]*)
                    echo "$proof_name: Stable/MVP verified runtime digest is invalid" >&2
                    return 2
                    ;;
            esac
            RUNTIME_ROOT=$ORDAX_SURFACE_RUNTIME_ROOT
            PROOF_RUNTIME_MODE=verified-erofs-overlay
            PROOF_EVIDENCE_SCOPE=canonical-stable-mvp
            ;;
        *)
            echo "$proof_name: unsupported distribution profile: $PROOF_DISTRIBUTION_PROFILE" >&2
            return 2
            ;;
    esac

    export RUNTIME_ROOT PROOF_DISTRIBUTION_PROFILE PROOF_RUNTIME_MODE PROOF_EVIDENCE_SCOPE
}

exec_ordax_physical_proof() {
    proof_name=$1
    collector=$2
    shift 2

    [ -x /bin/busybox ] || {
        echo "$proof_name: /bin/busybox unavailable" >&2
        return 2
    }
    [ -x "$RUNTIME_ROOT/usr/bin/python3" ] || {
        echo "$proof_name: active WebKit runtime Python unavailable: $RUNTIME_ROOT/usr/bin/python3" >&2
        return 2
    }
    [ -r "$RUNTIME_ROOT$collector" ] || {
        echo "$proof_name: proof collector is not mounted in the active Surface runtime" >&2
        return 2
    }
    [ -d "$RUNTIME_ROOT/proc" ] && [ -d "$RUNTIME_ROOT/run" ] && [ -d "$RUNTIME_ROOT/srv/ordax-system" ] || {
        echo "$proof_name: active Surface runtime bindings are unavailable" >&2
        return 2
    }

    ORDAX_PROOF_DISTRIBUTION_PROFILE="$PROOF_DISTRIBUTION_PROFILE" \
    ORDAX_PROOF_RUNTIME_MODE="$PROOF_RUNTIME_MODE" \
    ORDAX_PROOF_EVIDENCE_SCOPE="$PROOF_EVIDENCE_SCOPE" \
        exec /bin/busybox chroot "$RUNTIME_ROOT" /usr/bin/python3 "$collector" "$@"
}
