export const AI_RUNTIME_SCHEMA = "ordax.ai-runtime/1";

const STATES = new Set(["unavailable", "loading", "ready", "error"]);
const PROVIDER_ID_RE = /^[a-z][a-z0-9.-]{0,63}$/;
const MODEL_ID_RE = /^[a-z0-9][a-z0-9._-]{0,127}$/;

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

export function validateAiRuntimeSnapshot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("AI runtime snapshot must be an object");
  }
  if (value.schema !== AI_RUNTIME_SCHEMA) {
    throw new TypeError("Unsupported AI runtime schema");
  }
  if (!STATES.has(value.state)) {
    throw new TypeError("Unsupported AI runtime state");
  }

  const providerId = value.providerId ?? null;
  const modelId = value.modelId ?? null;
  if (providerId !== null && !PROVIDER_ID_RE.test(providerId)) {
    throw new TypeError("AI provider id is invalid");
  }
  if (modelId !== null && !MODEL_ID_RE.test(modelId)) {
    throw new TypeError("AI model id is invalid");
  }
  if (value.state === "ready" && (!providerId || !modelId)) {
    throw new TypeError("Ready AI runtime requires provider and model identities");
  }
  if (typeof value.localOnly !== "boolean") {
    throw new TypeError("AI runtime localOnly must be boolean");
  }

  return Object.freeze({
    schema: AI_RUNTIME_SCHEMA,
    state: value.state,
    providerId,
    modelId,
    localOnly: value.localOnly,
    message: value.message == null ? null : boundedText(value.message, "AI runtime message", 240),
  });
}

export function assertAiProvider(provider) {
  if (!provider || typeof provider !== "object") {
    throw new TypeError("AI provider is required");
  }
  if (!PROVIDER_ID_RE.test(provider.id ?? "")) {
    throw new TypeError("AI provider id is invalid");
  }
  if (!MODEL_ID_RE.test(provider.modelId ?? "")) {
    throw new TypeError("AI provider model id is invalid");
  }
  if (provider.localOnly !== true) {
    throw new TypeError("MVP local AI provider must be local-only");
  }
  if (typeof provider.complete !== "function") {
    throw new TypeError("AI provider must implement complete(request)");
  }
  return provider;
}

export function validateAiRequest(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("AI request must be an object");
  }
  const prompt = boundedText(value.prompt, "AI prompt", 32768);
  const system = value.system == null ? null : boundedText(value.system, "AI system prompt", 8192);
  return Object.freeze({ prompt, system });
}
