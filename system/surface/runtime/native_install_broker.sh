#!/bin/sh
set -eu

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

SESSION_DIR=${ORDAX_NATIVE_INSTALL_SESSION_DIR:-/run/ordax-surface}
HELPER=${ORDAX_NATIVE_INSTALL_HELPER:-}
CONTROL=$SESSION_DIR/native-install-control
REQUEST=$SESSION_DIR/native-install-request
RESPONSE=$SESSION_DIR/native-install-response
SNAPSHOT=$SESSION_DIR/native-install-targets.json
MAX_SNAPSHOT_BYTES=262144
HELPER_TIMEOUT_SECONDS=5

umask 077
mkdir -p "$SESSION_DIR"
chmod 700 "$SESSION_DIR"

case "$HELPER" in
    /*) ;;
    *) echo "ordax-native-install-broker: helper path must be absolute" >&2; exit 1 ;;
esac
[ -x "$HELPER" ] && [ ! -L "$HELPER" ] || {
    echo "ordax-native-install-broker: signed Native install helper is unavailable" >&2
    exit 1
}

cleanup() {
    rm -f "$CONTROL" "$REQUEST" "$RESPONSE" "$SNAPSHOT"
}
trap cleanup EXIT HUP INT TERM

rm -f "$CONTROL" "$REQUEST" "$RESPONSE" "$SNAPSHOT"
mkfifo "$CONTROL"
chmod 600 "$CONTROL"

respond() {
    request_id=$1
    outcome=$2
    detail=$3
    temporary=$RESPONSE.tmp.$$
    printf '%s\t%s\t%s\n' "$request_id" "$outcome" "$detail" >"$temporary"
    chmod 600 "$temporary"
    mv -f "$temporary" "$RESPONSE"
}

valid_request_id() {
    value=$1
    [ "${#value}" -eq 24 ] || return 1
    case "$value" in
        *[!0-9a-f]*|'') return 1 ;;
    esac
    return 0
}

handle_request() {
    request_id=""
    action=""
    IFS= read -r request_id <"$REQUEST" 2>/dev/null || {
        respond unknown error invalid-request
        return 0
    }
    action=$(/bin/busybox sed -n '2p' "$REQUEST" 2>/dev/null || true)
    valid_request_id "$request_id" || {
        respond unknown error invalid-request-id
        return 0
    }
    [ "$action" = list ] || {
        respond "$request_id" error unsupported-action
        return 0
    }

    temporary=$SNAPSHOT.tmp.$$
    rm -f "$temporary"
    if ! /bin/busybox timeout -k 2 "$HELPER_TIMEOUT_SECONDS" "$HELPER" >"$temporary" 2>/dev/null; then
        rm -f "$temporary"
        respond "$request_id" error discovery-failed
        return 0
    fi

    bytes=$(/bin/busybox stat -c %s "$temporary" 2>/dev/null || printf '0')
    case "$bytes" in
        ''|*[!0-9]*) bytes=0 ;;
    esac
    if [ "$bytes" -le 0 ] 2>/dev/null || [ "$bytes" -gt "$MAX_SNAPSHOT_BYTES" ] 2>/dev/null; then
        rm -f "$temporary"
        respond "$request_id" error invalid-snapshot-size
        return 0
    fi

    chmod 600 "$temporary"
    mv -f "$temporary" "$SNAPSHOT"
    respond "$request_id" ok listed
}

exec 9<>"$CONTROL"
while :; do
    signal=""
    if IFS= read -r signal <&9; then
        [ "$signal" = request ] && handle_request
    else
        /bin/busybox sleep 1
    fi
done
