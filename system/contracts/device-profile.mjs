export const DEVICE_PROFILE_SCHEMA = "ordax.device-profile/1";
export const DEVICE_PROFILE_PORT_SCHEMA = "ordax.device-profile-port/1";

const PUBLIC_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{7,159}$/;

function normalizeDisplayName(value) {
  if (typeof value !== "string") {
    throw new TypeError("Device display name must be a string");
  }
  const normalized = value.trim().replace(/\s+/g, " ");
  if (normalized.length < 1 || normalized.length > 120) {
    throw new TypeError("Device display name must be between 1 and 120 characters");
  }
  return normalized;
}

export function validateDeviceProfile(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Device profile must be an object");
  }
  if (value.schema !== DEVICE_PROFILE_SCHEMA) {
    throw new TypeError(`Unsupported device profile schema: ${String(value.schema)}`);
  }
  if (typeof value.devicePublicId !== "string" || !PUBLIC_ID_RE.test(value.devicePublicId)) {
    throw new TypeError("Device public id is invalid");
  }
  return Object.freeze({
    schema: DEVICE_PROFILE_SCHEMA,
    devicePublicId: value.devicePublicId,
    displayName: normalizeDisplayName(value.displayName),
  });
}

export function validateDeviceDisplayName(value) {
  return normalizeDisplayName(value);
}

export function assertDeviceProfilePort(port) {
  if (!port || typeof port !== "object" || port.schema !== DEVICE_PROFILE_PORT_SCHEMA) {
    throw new TypeError("A compatible device profile port is required");
  }
  if (typeof port.getSnapshot !== "function" || typeof port.rename !== "function") {
    throw new TypeError("Device profile port must implement getSnapshot() and rename()");
  }
  validateDeviceProfile(port.getSnapshot());
  return port;
}
