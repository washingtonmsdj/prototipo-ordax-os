export const LOCAL_AI_PORT_SCHEMA = "ordax.local-ai/1";

function text(value, label, max = 4096) {
  if (typeof value !== "string" || value.includes("\0")) {
    throw new TypeError(`${label} must be a string`);
  }
  const normalized = value.trim();
  if (!normalized || normalized.length > max) {
    throw new TypeError(`${label} is outside its allowed bounds`);
  }
  return normalized;
}

export function validateLocalAiSnapshot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Local AI snapshot must be an object");
  }
  const state = value.state;
  if (!["unavailable", "stopped", "ready", "busy", "error"].includes(state)) {
    throw new TypeError("Local AI state is invalid");
  }
  const engineId = value.engineId == null ? null : text(value.engineId, "engineId", 80);
  const modelId = value.modelId == null ? null : text(value.modelId, "modelId", 160);
  if (state === "ready" && (!engineId || !modelId)) {
    throw new TypeError("Ready Local AI requires engine and model identity");
  }
  return Object.freeze({
    schema: LOCAL_AI_PORT_SCHEMA,
    state,
    engineId,
    modelId,
    offline: value.offline !== false,
    migratable: value.migratable !== false,
  });
}

export function validateLocalAiRequest(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Local AI request must be an object");
  }
  return Object.freeze({
    prompt: text(value.prompt, "prompt", 32768),
    maxTokens: Number.isSafeInteger(value.maxTokens) && value.maxTokens > 0 && value.maxTokens <= 2048
      ? value.maxTokens
      : 512,
  });
}

export function assertLocalAiPort(port) {
  if (!port || typeof port !== "object" || port.schema !== LOCAL_AI_PORT_SCHEMA) {
    throw new TypeError("Compatible Local AI port is required");
  }
  for (const method of ["getSnapshot", "subscribe", "generate"]) {
    if (typeof port[method] !== "function") {
      throw new TypeError(`Local AI port must implement ${method}()`);
    }
  }
  validateLocalAiSnapshot(port.getSnapshot());
  return port;
}
