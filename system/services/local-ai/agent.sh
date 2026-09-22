#!/bin/sh
set -eu

PACK_ROOT=${ORDAX_LOCAL_AI_PACK_ROOT:-/ordax/ai/current}
ENGINE="$PACK_ROOT/bin/llama-server"
MODEL="$PACK_ROOT/models/default.gguf"
CONFIG="$PACK_ROOT/local-ai.json"
STATE_CONFIG=${ORDAX_LOCAL_AI_STATE_CONFIG:-/var/lib/ordax/local-ai.json}
LOG=${ORDAX_LOCAL_AI_LOG:-/run/ordax-surface/local-ai.log}
PORT=${ORDAX_LOCAL_AI_PORT:-11435}

disabled() {
    rm -f "$STATE_CONFIG" >/dev/null 2>&1 || true
    exit 0
}

[ -f "$CONFIG" ] || disabled
[ -x "$ENGINE" ] || disabled
[ -f "$MODEL" ] || disabled

case "$PORT" in
    ''|*[!0-9]*) disabled ;;
esac
[ "$PORT" -ge 1024 ] 2>/dev/null && [ "$PORT" -le 65535 ] 2>/dev/null || disabled

mkdir -p "$(dirname "$STATE_CONFIG")" "$(dirname "$LOG")"
chmod 700 "$(dirname "$STATE_CONFIG")" 2>/dev/null || true

tmp="$STATE_CONFIG.tmp.$$"
cat >"$tmp" <<EOF
{"schema":"ordax.local-ai-config/1","enabled":true,"endpoint":"http://127.0.0.1:$PORT","engine":"llama.cpp","model":"default.gguf"}
EOF
chmod 600 "$tmp"
mv "$tmp" "$STATE_CONFIG"

# llama.cpp exposes an OpenAI-compatible /v1 API. Bind strictly to loopback.
# The optional pack owns engine/model bytes; OrdaX owns policy and UI.
exec "$ENGINE"     --host 127.0.0.1     --port "$PORT"     --model "$MODEL"     --ctx-size 4096     --no-webui     >>"$LOG" 2>&1
