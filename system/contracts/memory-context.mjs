import { validateMemoryOwner } from "./memory.mjs";

export const MEMORY_CONTEXT_AUTH_SCHEMA = "ordax.memory-context-auth/1";
export const MAX_MEMORY_CONTEXT_ITEMS = 8;
export const MAX_MEMORY_CONTEXT_AUTHORIZATIONS = 4;

const SCOPES = new Set(["device", "account", "space", "project", "session"]);

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

function optionalText(value, label, max) {
  if (value == null || value === "") return null;
  return boundedText(value, label, max);
}

export function validateMemoryContextAuthorization(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Memory context authorization must be an object");
  }
  if (value.authority !== "composition") {
    throw new TypeError("Memory context authorization must come from composition");
  }
  const owner = validateMemoryOwner(value, "Memory context owner");
  if (!Array.isArray(value.scopes) || value.scopes.length === 0 || value.scopes.length > SCOPES.size) {
    throw new TypeError("Memory context scopes are invalid");
  }
  const scopes = [];
  for (const scope of value.scopes) {
    if (!SCOPES.has(scope) || scopes.includes(scope)) {
      throw new TypeError("Memory context scopes are invalid");
    }
    scopes.push(scope);
  }
  if (owner.ownerKind === "device" && scopes.includes("account")) {
    throw new TypeError("Device-owned memory context cannot authorize account scope");
  }
  const spaceId = optionalText(value.spaceId, "Memory context space id", 160);
  const projectId = optionalText(value.projectId, "Memory context project id", 240);
  if (scopes.includes("space") && !spaceId) {
    throw new TypeError("Space memory context requires a space id");
  }
  if (scopes.includes("project") && !projectId) {
    throw new TypeError("Project memory context requires a project id");
  }
  if (projectId && scopes.includes("project") && value.projectSpaceBound === true && !spaceId) {
    throw new TypeError("Space-bound project memory context requires a space id");
  }
  return Object.freeze({
    schema: MEMORY_CONTEXT_AUTH_SCHEMA,
    authority: "composition",
    ownerKind: owner.ownerKind,
    ownerId: owner.ownerId,
    scopes: Object.freeze(scopes),
    spaceId,
    projectId,
    includeRestricted: value.includeRestricted === true,
  });
}
