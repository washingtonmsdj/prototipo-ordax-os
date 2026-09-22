#!/bin/sh

select_ordax_physical_proof_runtime() {
    proof_name=${1:-ordax-proof}
    STATE_ROOT=${ORDAX_STATE_DIR:-/state/ordax}
    RUNTIME_ID=alpine-v3.22-cage-webkitgtk-v1
    context_file=/run/ordax-surface/runtime-proof-context

    [ -f "$context_file" ] && [ ! -L "$context_file" ] || {
        echo "$proof_name: active Surface runtime proof context is unavailable" >&2
        return 2
    }

    PROOF_DISTRIBUTION_PROFILE=
    PROOF_RUNTIME_MODE=
    PROOF_EVIDENCE_SCOPE=
    proof_runtime_digest=
    seen_profile=0
    seen_mode=0
    seen_scope=0
    seen_digest=0

    while IFS='=' read -r key value; do
        case "$key" in
            distribution_profile)
                [ "$seen_profile" -eq 0 ] || return 2
                PROOF_DISTRIBUTION_PROFILE=$value
                seen_profile=1
                ;;
            runtime_mode)
                [ "$seen_mode" -eq 0 ] || return 2
                PROOF_RUNTIME_MODE=$value
                seen_mode=1
                ;;
            evidence_scope)
                [ "$seen_scope" -eq 0 ] || return 2
                PROOF_EVIDENCE_SCOPE=$value
                seen_scope=1
                ;;
            runtime_sha256)
                [ "$seen_digest" -eq 0 ] || return 2
                proof_runtime_digest=$value
                seen_digest=1
                ;;
            "")
                ;;
            *)
                echo "$proof_name: active Surface runtime proof context contains an unknown field" >&2
                return 2
                ;;
        esac
    done <"$context_file"

    [ "$seen_profile" -eq 1 ] &&
    [ "$seen_mode" -eq 1 ] &&
    [ "$seen_scope" -eq 1 ] &&
    [ "$seen_digest" -eq 1 ] || {
        echo "$proof_name: active Surface runtime proof context is incomplete" >&2
        return 2
    }

    case "$PROOF_DISTRIBUTION_PROFILE:$PROOF_RUNTIME_MODE:$PROOF_EVIDENCE_SCOPE" in
        owner-development:dynamic-native-runtime:development)
            [ -z "$proof_runtime_digest" ] || {
                echo "$proof_name: development runtime context unexpectedly contains a verified digest" >&2
                return 2
            }
            RUNTIME_ROOT=$STATE_ROOT/runtime/native-surface/$RUNTIME_ID/rootfs
            ;;
        stable-mvp:verified-erofs-overlay:canonical-stable-mvp)
            [ "${#proof_runtime_digest}" -eq 64 ] || {
                echo "$proof_name: Stable/MVP verified runtime digest is invalid" >&2
                return 2
            }
            case "$proof_runtime_digest" in
                *[!0-9a-f]*)
                    echo "$proof_name: Stable/MVP verified runtime digest is invalid" >&2
                    return 2
                    ;;
            esac
            RUNTIME_ROOT=/run/ordax/runtime/native-surface/rootfs
            ;;
        *)
            echo "$proof_name: active Surface runtime proof context is invalid" >&2
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
