export const MEMORY_PORT_SCHEMA = "ordax.memory/1";
export const MAX_MEMORY_SEARCH_RESULTS = 32;
export const MAX_MEMORY_SEARCH_OFFSET = 2048;

const OWNER_KINDS = new Set(["device", "account"]);
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

function optionalText(value, label, max) {
  if (value == null || value === "") return null;
  return boundedText(value, label, max);
}

export function validateMemoryOwner(value, label = "Memory owner") {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
  if (value.ownerId === "") {
    throw new TypeError(`${label} id must not be empty`);
  }
  const ownerId = optionalText(value.ownerId, `${label} id`, 160);
  const ownerKind = value.ownerKind ?? (ownerId === null ? "device" : "account");
  if (!OWNER_KINDS.has(ownerKind)) {
    throw new TypeError(`${label} kind is invalid`);
  }
  if (ownerKind === "account" && ownerId === null) {
    throw new TypeError(`${label} account subject id is required`);
  }
  if (ownerKind === "device" && ownerId !== null) {
    throw new TypeError(`${label} device ownership must not use a synthetic account subject id`);
  }
  return Object.freeze({ ownerKind, ownerId });
}

export function memoryOwnersEqual(left, right) {
  const a = validateMemoryOwner(left, "Memory owner comparison left");
  const b = validateMemoryOwner(right, "Memory owner comparison right");
  return a.ownerKind === b.ownerKind && a.ownerId === b.ownerId;
}

export function memoryIdentityKey(value, label = "Memory identity") {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
  const owner = validateMemoryOwner(value, `${label} owner`);
  const id = boundedText(value.id, `${label} id`, 160);
  // NUL is forbidden from every component, so it is an unambiguous internal
  // separator without expanding the public memory-id contract.
  return `${owner.ownerKind}\0${owner.ownerId ?? ""}\0${id}`;
}

function validSourceTimestamp(value) {
  if (typeof value !== "string" || value.length > 64 || value.includes("\0")) {
    throw new TypeError("Memory source timestamp must be an ISO-8601 string");
  }
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    throw new TypeError("Memory source timestamp is invalid");
  }
  return new Date(parsed).toISOString();
}

function containsSecretMaterial(value) {
  return [
    /-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----/i,
    /\bsk-[A-Za-z0-9_-]{16,}\b/,
    /\bghp_[A-Za-z0-9]{20,}\b/,
    /\bgithub_pat_[A-Za-z0-9_]{20,}\b/,
    /\bxox[baprs]-[A-Za-z0-9-]{16,}\b/,
    /\bsb_secret_[A-Za-z0-9_-]{16,}\b/,
  ].some((pattern) => pattern.test(value));
}

export function validateMemoryItem(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Memory item must be an object");
  }
  if (!SCOPES.has(value.scope) || !KINDS.has(value.kind)) {
    throw new TypeError("Memory scope/kind is invalid");
  }
  const owner = validateMemoryOwner(value);
  if (value.scope === "account" && owner.ownerKind !== "account") {
    throw new TypeError("Account memory requires an account owner");
  }
  const sensitivity = value.sensitivity ?? "private";
  if (!SENSITIVITY.has(sensitivity)) {
    throw new TypeError("Memory sensitivity is invalid");
  }
  const content = boundedText(value.content, "Memory content", MAX_CONTENT_CHARS);
  const provenance = boundedText(value.provenance, "Memory provenance", 1024);
  if (
    value.secret === true
    || containsSecretMaterial(content)
    || containsSecretMaterial(provenance)
  ) {
    throw new TypeError("Secrets are not valid OrdaX memory items");
  }
  const spaceId = optionalText(value.spaceId, "Memory space id", 160);
  const projectId = optionalText(value.projectId, "Memory project id", 240);
  if (value.scope === "space" && !spaceId) {
    throw new TypeError("Space memory requires a space id");
  }
  if (value.scope === "project" && !projectId) {
    throw new TypeError("Project memory requires a project id");
  }
  return Object.freeze({
    schema: MEMORY_PORT_SCHEMA,
    id: boundedText(value.id, "Memory id", 160),
    ownerKind: owner.ownerKind,
    ownerId: owner.ownerId,
    scope: value.scope,
    kind: value.kind,
    sensitivity,
    content,
    provenance,
    sourceTimestamp: validSourceTimestamp(value.sourceTimestamp),
    spaceId,
    projectId,
  });
}

export function validateMemorySearchRequest(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Memory search request must be an object");
  }
  const owner = validateMemoryOwner(value, "Memory search owner");
  const scopes = value.scopes == null
    ? [...SCOPES].filter((scope) => owner.ownerKind === "account" || scope !== "account")
    : value.scopes;
  if (!Array.isArray(scopes) || scopes.length === 0 || scopes.length > SCOPES.size) {
    throw new TypeError("Memory search scopes are invalid");
  }
  const uniqueScopes = [];
  for (const scope of scopes) {
    if (!SCOPES.has(scope) || uniqueScopes.includes(scope)) {
      throw new TypeError("Memory search scopes are invalid");
    }
    uniqueScopes.push(scope);
  }
  if (owner.ownerKind === "device" && uniqueScopes.includes("account")) {
    throw new TypeError("Device-owned memory search cannot request account scope");
  }
  const query = value.query == null ? "" : String(value.query).trim();
  if (query.length > 1024 || query.includes("\0")) {
    throw new TypeError("Memory search query is outside its allowed bounds");
  }
  const spaceId = optionalText(value.spaceId, "Memory search space id", 160);
  const projectId = optionalText(value.projectId, "Memory search project id", 240);
  if (uniqueScopes.length === 1 && uniqueScopes[0] === "space" && !spaceId) {
    throw new TypeError("Space memory search requires a space id");
  }
  if (uniqueScopes.length === 1 && uniqueScopes[0] === "project" && !projectId) {
    throw new TypeError("Project memory search requires a project id");
  }
  const limit = Number.isSafeInteger(value.limit)
    && value.limit > 0
    && value.limit <= MAX_MEMORY_SEARCH_RESULTS
    ? value.limit
    : 8;
  const offset = value.offset === undefined
    ? 0
    : Number.isSafeInteger(value.offset)
      && value.offset >= 0
      && value.offset <= MAX_MEMORY_SEARCH_OFFSET
        ? value.offset
        : null;
  if (offset === null) {
    throw new TypeError("Memory search offset is outside its allowed bounds");
  }
  return Object.freeze({
    ownerKind: owner.ownerKind,
    ownerId: owner.ownerId,
    query,
    scopes: Object.freeze(uniqueScopes),
    spaceId,
    projectId,
    includeRestricted: value.includeRestricted === true,
    limit,
    offset,
  });
}

export function validateMemoryForgetRequest(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Memory forget request must be an object");
  }
  const owner = validateMemoryOwner(value, "Memory forget owner");
  return Object.freeze({
    id: boundedText(value.id, "Memory id", 160),
    ownerKind: owner.ownerKind,
    ownerId: owner.ownerId,
  });
}

export function assertMemoryPort(port) {
  if (!port || typeof port !== "object" || port.schema !== MEMORY_PORT_SCHEMA) {
    throw new TypeError("Compatible OrdaX memory port is required");
  }
  for (const method of ["search", "remember", "forget", "flush"]) {
    if (typeof port[method] !== "function") {
      throw new TypeError(`Memory port must implement ${method}()`);
    }
  }
  return port;
}
