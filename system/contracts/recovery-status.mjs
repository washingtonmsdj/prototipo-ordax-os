export const RECOVERY_STATUS_SCHEMA = "ordax.recovery-status/1";

const SHA_RE = /^[0-9a-f]{40}$/;
const BOOT_SLOTS = new Set(["current", "known-good", "candidate", "unknown"]);
const ENTRY_STATES = new Set(["verified", "missing", "invalid", "unavailable"]);

function optionalSha(value, field) {
  if (value === null) return null;
  if (typeof value !== "string" || !SHA_RE.test(value)) {
    throw new TypeError(`Recovery status ${field} must be null or a lowercase full Git SHA`);
  }
  return value;
}

export function validateRecoveryStatusSnapshot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Recovery status snapshot must be an object");
  }
  if (value.layout !== "portable-v2") {
    throw new TypeError("Recovery status layout must be portable-v2");
  }
  if (!BOOT_SLOTS.has(value.bootSlot)) {
    throw new TypeError("Recovery status bootSlot is invalid");
  }
  if (!ENTRY_STATES.has(value.recoveryEntryStatus)) {
    throw new TypeError("Recovery status recoveryEntryStatus is invalid");
  }
  if (typeof value.transactionPresent !== "boolean") {
    throw new TypeError("Recovery status transactionPresent must be boolean");
  }
  if (value.policy !== "local-read-only") {
    throw new TypeError("Recovery status policy must be local-read-only");
  }
  if (value.automaticNetwork !== false || value.automaticMutation !== false) {
    throw new TypeError("Recovery status must not claim automatic network or mutation");
  }

  return Object.freeze({
    schema: RECOVERY_STATUS_SCHEMA,
    layout: "portable-v2",
    bootSlot: value.bootSlot,
    runningSourceSha: optionalSha(value.runningSourceSha, "runningSourceSha"),
    currentSha: optionalSha(value.currentSha, "currentSha"),
    knownGoodSha: optionalSha(value.knownGoodSha, "knownGoodSha"),
    candidateSha: optionalSha(value.candidateSha, "candidateSha"),
    transactionPresent: value.transactionPresent,
    recoveryEntryStatus: value.recoveryEntryStatus,
    policy: "local-read-only",
    automaticNetwork: false,
    automaticMutation: false,
  });
}

export function assertRecoveryStatusPort(port) {
  if (!port || typeof port !== "object" || port.schema !== RECOVERY_STATUS_SCHEMA) {
    throw new TypeError("A compatible recovery-status port is required");
  }
  if (typeof port.read !== "function") {
    throw new TypeError("Recovery-status port must implement read()");
  }
  return port;
}
