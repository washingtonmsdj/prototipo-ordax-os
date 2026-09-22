export const ORDAX_INTELLIGENCE_PORT_SCHEMA = "ordax.intelligence/1";

const MAX_CONTEXT_SOURCES = 16;
const MAX_SOURCE_TEXT = 16384;
const MAX_CONTEXT_TEXT = 65536;

function boundedText(value, label, max) {
  if (typeof value !== "string" || value.includes("\0")) {
    throw new TypeError(`${label} must be a string`);
  }
  const normalized = value.trim();
  if (!normalized || normalized.length > max) {
    throw new TypeError(`${label} is outside its allowed bounds`);
  }
  return normalized;
}

function validateSource(value, index) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`Intelligence context source ${index} must be an object`);
  }
  return Object.freeze({
    id: boundedText(value.id, `context[${index}].id`, 160),
    title: boundedText(value.title, `context[${index}].title`, 240),
    text: boundedText(value.text, `context[${index}].text`, MAX_SOURCE_TEXT),
  });
}

export function validateIntelligenceRequest(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Intelligence request must be an object");
  }
  const prompt = boundedText(value.prompt, "prompt", 32768);
  const rawContext = value.context ?? [];
  if (!Array.isArray(rawContext) || rawContext.length > MAX_CONTEXT_SOURCES) {
    throw new TypeError("Intelligence context must be a bounded array");
  }
  const context = rawContext.map(validateSource);
  const contextBytes = context.reduce((total, source) => total + source.text.length, 0);
  if (contextBytes > MAX_CONTEXT_TEXT) {
    throw new TypeError("Intelligence context exceeds its aggregate bound");
  }
  return Object.freeze({
    prompt,
    context: Object.freeze(context),
    maxTokens:
      Number.isSafeInteger(value.maxTokens) && value.maxTokens > 0 && value.maxTokens <= 2048
        ? value.maxTokens
        : 512,
  });
}

export function validateIntelligenceSnapshot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Intelligence snapshot must be an object");
  }
  if (!["unavailable", "stopped", "ready", "busy", "error"].includes(value.state)) {
    throw new TypeError("Intelligence state is invalid");
  }
  return Object.freeze({
    schema: ORDAX_INTELLIGENCE_PORT_SCHEMA,
    state: value.state,
    route: value.route === "local" ? "local" : "unavailable",
    offlineCapable: value.offlineCapable !== false,
    systemCapability: true,
    toolsEnabled: value.toolsEnabled === true,
    engineId: value.engineId == null ? null : boundedText(value.engineId, "engineId", 80),
    modelId: value.modelId == null ? null : boundedText(value.modelId, "modelId", 160),
  });
}

export function assertIntelligencePort(port) {
  if (!port || typeof port !== "object" || port.schema !== ORDAX_INTELLIGENCE_PORT_SCHEMA) {
    throw new TypeError("Compatible Ordax Intelligence port is required");
  }
  for (const method of ["getSnapshot", "subscribe", "ask"]) {
    if (typeof port[method] !== "function") {
      throw new TypeError(`Ordax Intelligence port must implement ${method}()`);
    }
  }
  validateIntelligenceSnapshot(port.getSnapshot());
  return port;
}
