export const NATIVE_INSTALL_TARGETS_SCHEMA = "ordax.native-install-targets/1";
export const NATIVE_INSTALL_TARGETS_PORT_SCHEMA = "ordax.native-install-targets-port/1";

const TOKEN_RE = /^[0-9a-f]{64}$/;
const MAX_TARGETS = 64;

function boundedText(value, field, maxLength) {
  if (
    typeof value !== "string"
    || value.length > maxLength
    || [...value].some((character) => character.codePointAt(0) < 32)
  ) {
    throw new TypeError(`Native install ${field} is invalid`);
  }
  return value;
}

function validateTarget(value) {
  if (!value || typeof value !== "object") {
    throw new TypeError("Native install target must be an object");
  }
  if (
    typeof value.confirmationToken !== "string"
    || !TOKEN_RE.test(value.confirmationToken)
    || value.targetId !== value.confirmationToken
  ) {
    throw new TypeError("Native install target identity is invalid");
  }
  if (
    !Number.isSafeInteger(value.physicalBytes)
    || value.physicalBytes <= 0
  ) {
    throw new TypeError("Native install target capacity is invalid");
  }
  for (const field of ["removable", "readOnly", "sourceBootMedia", "eligible"]) {
    if (typeof value[field] !== "boolean") {
      throw new TypeError(`Native install target ${field} must be boolean`);
    }
  }
  if (value.eligible !== (!value.readOnly && !value.sourceBootMedia)) {
    throw new TypeError("Native install target eligibility is inconsistent");
  }
  return Object.freeze({
    targetId: value.targetId,
    confirmationToken: value.confirmationToken,
    model: boundedText(value.model, "model", 200),
    transport: boundedText(value.transport, "transport", 32),
    physicalBytes: value.physicalBytes,
    removable: value.removable,
    readOnly: value.readOnly,
    sourceBootMedia: value.sourceBootMedia,
    eligible: value.eligible,
  });
}

export function validateNativeInstallTargetsSnapshot(value) {
  if (
    !value
    || typeof value !== "object"
    || value.schema !== NATIVE_INSTALL_TARGETS_SCHEMA
    || value.physicalWriteAllowed !== false
    || !Array.isArray(value.targets)
    || value.targets.length > MAX_TARGETS
  ) {
    throw new TypeError("Native install target snapshot is invalid");
  }
  const targets = value.targets.map(validateTarget);
  const identities = new Set(targets.map((target) => target.targetId));
  if (identities.size !== targets.length) {
    throw new TypeError("Native install target identities must be unique");
  }
  return Object.freeze({
    schema: NATIVE_INSTALL_TARGETS_SCHEMA,
    physicalWriteAllowed: false,
    targets: Object.freeze(targets),
  });
}

export function assertNativeInstallTargetsPort(port) {
  if (
    !port
    || typeof port !== "object"
    || port.schema !== NATIVE_INSTALL_TARGETS_PORT_SCHEMA
    || typeof port.list !== "function"
  ) {
    throw new TypeError("A compatible Native install targets port is required");
  }
  return port;
}
