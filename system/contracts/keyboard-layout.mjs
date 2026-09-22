export const KEYBOARD_LAYOUT_SCHEMA = "ordax.keyboard-layout/1";

export const KEYBOARD_LAYOUT_IDS = Object.freeze(["br-abnt2", "us"]);
const LAYOUT_IDS = new Set(KEYBOARD_LAYOUT_IDS);

function validateLayoutId(value, label) {
  if (typeof value !== "string" || !LAYOUT_IDS.has(value)) {
    throw new TypeError(`${label} is not a supported keyboard layout`);
  }
  return value;
}

export function validateKeyboardLayoutSnapshot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Keyboard layout snapshot must be an object");
  }

  const configuredLayoutId = validateLayoutId(
    value.configuredLayoutId,
    "Configured keyboard layout",
  );
  const appliedLayoutId = validateLayoutId(
    value.appliedLayoutId,
    "Applied keyboard layout",
  );
  if (!Array.isArray(value.supportedLayoutIds) || value.supportedLayoutIds.length === 0) {
    throw new TypeError("Keyboard layout snapshot must expose supportedLayoutIds");
  }
  const supportedLayoutIds = value.supportedLayoutIds.map((layoutId) =>
    validateLayoutId(layoutId, "Supported keyboard layout"));
  if (new Set(supportedLayoutIds).size !== supportedLayoutIds.length) {
    throw new TypeError("Keyboard layout supportedLayoutIds must be unique");
  }
  for (const required of KEYBOARD_LAYOUT_IDS) {
    if (!supportedLayoutIds.includes(required)) {
      throw new TypeError(`Keyboard layout snapshot is missing supported layout: ${required}`);
    }
  }

  const restartRequired = configuredLayoutId !== appliedLayoutId;
  if (value.restartRequired !== restartRequired) {
    throw new TypeError("Keyboard layout restartRequired does not match configured/applied state");
  }

  return Object.freeze({
    configuredLayoutId,
    appliedLayoutId,
    supportedLayoutIds: Object.freeze([...supportedLayoutIds]),
    restartRequired,
  });
}

export function assertKeyboardLayoutPort(port) {
  if (!port || typeof port !== "object" || port.schema !== KEYBOARD_LAYOUT_SCHEMA) {
    throw new TypeError("A compatible keyboard-layout port is required");
  }
  if (typeof port.read !== "function" || typeof port.configure !== "function") {
    throw new TypeError("Keyboard-layout port must implement read() and configure(layoutId)");
  }
  return port;
}
