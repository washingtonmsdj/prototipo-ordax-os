export const MEMORY_PORT_SCHEMA = "ordax.memory/1";

const SCOPES = new Set(["device", "account", "space", "project", "session"]);
const KINDS = new Set(["preference", "fact", "instruction", "summary", "artifact-reference"]);
const SENSITIVITY = new Set(["normal", "private", "restricted"]);
const MAX_CONTENT_CHARS = 32768;

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

export function validateMemoryItem(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Memory item must be an object");
  }
  if (!SCOPES.has(value.scope) || !KINDS.has(value.kind)) {
    throw new TypeError("Memory scope/kind is invalid");
  }
  const sensitivity = value.sensitivity ?? "private";
  if (!SENSITIVITY.has(sensitivity)) {
    throw new TypeError("Memory sensitivity is invalid");
  }
  if (value.secret === true) {
    throw new TypeError("Secrets are not valid OrdaX memory items");
  }
  const spaceId = value.spaceId == null ? null : boundedText(value.spaceId, "Memory space id", 160);
  const projectId = value.projectId == null ? null : boundedText(value.projectId, "Memory project id", 240);
  if (value.scope === "space" && !spaceId) {
    throw new TypeError("Space memory requires a space id");
  }
  if (value.scope === "project" && !projectId) {
    throw new TypeError("Project memory requires a project id");
  }
  return Object.freeze({
    schema: MEMORY_PORT_SCHEMA,
    id: boundedText(value.id, "Memory id", 160),
    ownerId: boundedText(value.ownerId, "Memory owner id", 160),
    scope: value.scope,
    kind: value.kind,
    sensitivity,
    content: boundedText(value.content, "Memory content", MAX_CONTENT_CHARS),
    provenance: boundedText(value.provenance, "Memory provenance", 1024),
    spaceId,
    projectId,
  });
}

export function assertMemoryPort(port) {
  if (!port || typeof port !== "object" || port.schema !== MEMORY_PORT_SCHEMA) {
    throw new TypeError("Compatible OrdaX memory port is required");
  }
  for (const method of ["search", "remember", "forget"]) {
    if (typeof port[method] !== "function") {
      throw new TypeError(`Memory port must implement ${method}()`);
    }
  }
  return port;
}
