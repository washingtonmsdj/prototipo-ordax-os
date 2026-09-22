#!/bin/sh

# Shared resolver for read-only physical proof harnesses.
# Stable/MVP uses the initramfs-composed verified runtime in /run.
# Owner/Development uses the dynamically materialized runtime in persistent state.
resolve_ordax_proof_runtime_root() {
    state_root=${ORDAX_STATE_DIR:-/state/ordax}
    stable_root=/run/ordax/runtime/native-surface/rootfs
    runtime_id=alpine-v3.22-cage-webkitgtk-v1
    development_root=$state_root/runtime/native-surface/$runtime_id/rootfs
    profile=${ORDAX_DISTRIBUTION_PROFILE:-}

    case "$profile" in
        stable-mvp)
            candidate=$stable_root
            resolved_profile=stable-mvp
            ;;
        owner-development)
            candidate=$development_root
            resolved_profile=owner-development
            ;;
        "")
            if [ -x "$stable_root/usr/bin/python3" ] && [ -d "$stable_root/srv/ordax-system" ]; then
                candidate=$stable_root
                resolved_profile=stable-mvp
            else
                candidate=$development_root
                resolved_profile=owner-development
            fi
            ;;
        *)
            echo "ordax-proof-runtime: unsupported distribution profile: $profile" >&2
            return 1
            ;;
    esac

    [ -d "$candidate" ] || {
        echo "ordax-proof-runtime: active Surface runtime root unavailable: $candidate" >&2
        return 1
    }

    RUNTIME_ROOT=$candidate
    ORDAX_PROOF_PROFILE=$resolved_profile
    export RUNTIME_ROOT ORDAX_PROOF_PROFILE
}
