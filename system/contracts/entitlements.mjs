export const ENTITLEMENTS_PORT_SCHEMA = "ordax.entitlements/1";

const SUBJECT_TYPES = new Set(["account", "space"]);
const KEY_RE = /^[a-z][a-z0-9.-]{2,95}$/;

function boundedText(value, label, max = 160) {
  if (typeof value !== "string" || value.includes("\0")) {
    throw new TypeError(`${label} must be a string`);
  }
  const normalized = value.trim();
  if (!normalized || normalized.length > max) {
    throw new TypeError(`${label} is outside its allowed bounds`);
  }
  return normalized;
}

export function validateEntitlementDecision(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Entitlement decision must be an object");
  }
  if (!SUBJECT_TYPES.has(value.subjectType)) {
    throw new TypeError("Entitlement subject type is invalid");
  }
  const key = boundedText(value.key, "Entitlement key", 96);
  if (!KEY_RE.test(key)) {
    throw new TypeError("Entitlement key is invalid");
  }
  if (!["allowed", "denied", "limited"].includes(value.decision)) {
    throw new TypeError("Entitlement decision is invalid");
  }
  if (value.authority !== "server" && value.authority !== "local-default") {
    throw new TypeError("Entitlement authority is invalid");
  }
  return Object.freeze({
    schema: ENTITLEMENTS_PORT_SCHEMA,
    subjectType: value.subjectType,
    subjectId: boundedText(value.subjectId, "Entitlement subject id", 160),
    key,
    decision: value.decision,
    value: value.value ?? null,
    authority: value.authority,
    expiresAt: value.expiresAt ?? null,
  });
}

export function assertEntitlementsPort(port) {
  if (!port || typeof port !== "object" || port.schema !== ENTITLEMENTS_PORT_SCHEMA) {
    throw new TypeError("Compatible OrdaX entitlements port is required");
  }
  if (typeof port.resolve !== "function") {
    throw new TypeError("Entitlements port must implement resolve()");
  }
  return port;
}
