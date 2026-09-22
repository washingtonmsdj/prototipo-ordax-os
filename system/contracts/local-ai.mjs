export const LOCAL_AI_PORT_SCHEMA = "ordax.local-ai-port/1";
export const LOCAL_AI_STATUS_SCHEMA = "ordax.local-ai-status/1";
export const LOCAL_AI_RESPONSE_SCHEMA = "ordax.local-ai-response/1";

const STATES = new Set(["ready", "unavailable"]);
const ROLE_SET = new Set(["system", "user", "assistant"]);

export function validateLocalAiStatus(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Local AI status must be an object");
  }
  if (value.schema !== LOCAL_AI_STATUS_SCHEMA || !STATES.has(value.state)) {
    throw new TypeError("Local AI status is incompatible");
  }
  if (value.state === "unavailable") {
    return Object.freeze({
      schema: LOCAL_AI_STATUS_SCHEMA,
      state: "unavailable",
      backend: null,
      model: null,
    });
  }
  if (
    typeof value.backend !== "string" || !value.backend
    || typeof value.model !== "string" || !value.model
  ) {
    throw new TypeError("Ready Local AI status requires backend and model");
  }
  return Object.freeze({
    schema: LOCAL_AI_STATUS_SCHEMA,
    state: "ready",
    backend: value.backend,
    model: value.model,
  });
}

export function validateLocalAiMessages(messages) {
  if (!Array.isArray(messages) || messages.length < 1 || messages.length > 32) {
    throw new TypeError("Local AI messages must contain between 1 and 32 items");
  }
  let total = 0;
  return Object.freeze(messages.map((entry) => {
    if (!entry || typeof entry !== "object" || !ROLE_SET.has(entry.role)) {
      throw new TypeError("Local AI message role is invalid");
    }
    if (typeof entry.content !== "string" || !entry.content || entry.content.length > 16384) {
      throw new TypeError("Local AI message content is invalid");
    }
    total += entry.content.length;
    if (total > 65536) throw new TypeError("Local AI conversation exceeds the bounded context");
    return Object.freeze({ role: entry.role, content: entry.content });
  }));
}

export function validateLocalAiResponse(value) {
  if (
    !value || typeof value !== "object"
    || value.schema !== LOCAL_AI_RESPONSE_SCHEMA
    || typeof value.text !== "string" || !value.text
    || value.text.length > 131072
    || typeof value.backend !== "string" || !value.backend
    || typeof value.model !== "string" || !value.model
  ) {
    throw new TypeError("Local AI response is invalid");
  }
  return Object.freeze({
    schema: LOCAL_AI_RESPONSE_SCHEMA,
    text: value.text,
    backend: value.backend,
    model: value.model,
  });
}

export function assertLocalAiPort(port) {
  if (!port || typeof port !== "object" || port.schema !== LOCAL_AI_PORT_SCHEMA) {
    throw new TypeError("Local AI port is incompatible");
  }
  if (typeof port.getSnapshot !== "function" || typeof port.complete !== "function") {
    throw new TypeError("Local AI port must implement getSnapshot() and complete()");
  }
  validateLocalAiStatus(port.getSnapshot());
  return port;
}
