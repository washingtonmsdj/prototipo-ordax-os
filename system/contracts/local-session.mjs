export const LOCAL_SESSION_SCHEMA = "ordax.local-session/1";

const STATES = new Set(["unlocked", "locked"]);
const MIN_SECRET_CHARS = 6;
const MAX_SECRET_CHARS = 128;

function secretText(value, label = "Local session secret") {
  if (typeof value !== "string" || value.includes("\0")) {
    throw new TypeError(`${label} must be text`);
  }
  if (value.length < MIN_SECRET_CHARS || value.length > MAX_SECRET_CHARS) {
    throw new TypeError(
      `${label} must contain between ${MIN_SECRET_CHARS} and ${MAX_SECRET_CHARS} characters`,
    );
  }
  if (!value.trim()) {
    throw new TypeError(`${label} may not contain only whitespace`);
  }
  return value;
}

export function validateLocalSessionSnapshot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Local session snapshot must be an object");
  }
  if (!STATES.has(value.state)) {
    throw new TypeError(`Unsupported local session state: ${String(value.state)}`);
  }
  if (typeof value.credentialConfigured !== "boolean") {
    throw new TypeError("Local session credentialConfigured must be boolean");
  }
  if (value.state === "locked" && !value.credentialConfigured) {
    throw new TypeError("Local session cannot be locked without a configured credential");
  }
  if (value.protectionScope !== "surface-session-not-storage-encryption") {
    throw new TypeError("Local session protection scope must remain explicit");
  }
  return Object.freeze({
    schema: LOCAL_SESSION_SCHEMA,
    state: value.state,
    credentialConfigured: value.credentialConfigured,
    canLock: value.credentialConfigured,
    protectionScope: "surface-session-not-storage-encryption",
  });
}

export function validateLocalSessionSecret(value) {
  return secretText(value);
}

export function assertLocalSessionPort(port) {
  if (!port || typeof port !== "object" || port.schema !== LOCAL_SESSION_SCHEMA) {
    throw new TypeError("A compatible local-session port is required");
  }
  for (const method of [
    "getSnapshot",
    "subscribe",
    "configureCredential",
    "removeCredential",
    "lock",
    "unlock",
  ]) {
    if (typeof port[method] !== "function") {
      throw new TypeError(`Local-session port must implement ${method}()`);
    }
  }
  validateLocalSessionSnapshot(port.getSnapshot());
  return port;
}
