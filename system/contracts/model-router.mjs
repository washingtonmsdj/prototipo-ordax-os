export const MODEL_ROUTER_PORT_SCHEMA = "ordax.model-router/1";

const PROVIDERS = new Set(["local", "openai", "xai"]);
const PURPOSES = new Set(["general", "summarize", "reason", "code", "embedding"]);

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

export function validateModelRoute(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Model route must be an object");
  }
  if (!PROVIDERS.has(value.provider) || !PURPOSES.has(value.purpose ?? "general")) {
    throw new TypeError("Model route provider/purpose is invalid");
  }
  if (value.provider !== "local" && value.egressApproved !== true) {
    throw new TypeError("External model route requires explicit egress approval");
  }
  const engineId = value.provider === "local"
    ? boundedText(value.engineId, "Engine id", 80)
    : null;
  return Object.freeze({
    schema: MODEL_ROUTER_PORT_SCHEMA,
    provider: value.provider,
    engineId,
    modelId: boundedText(value.modelId, "Model id", 160),
    purpose: value.purpose ?? "general",
    egressApproved: value.provider === "local" ? false : true,
    memoryOwner: "ordax",
  });
}

export function assertModelRouterPort(port) {
  if (!port || typeof port !== "object" || port.schema !== MODEL_ROUTER_PORT_SCHEMA) {
    throw new TypeError("Compatible OrdaX model router port is required");
  }
  if (typeof port.route !== "function") {
    throw new TypeError("Model router port must implement route()");
  }
  return port;
}
