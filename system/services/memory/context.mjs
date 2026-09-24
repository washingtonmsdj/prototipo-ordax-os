import {
  assertMemoryPort,
  memoryOwnersEqual,
  validateMemoryItem,
} from "../../contracts/memory.mjs";
import {
  MAX_MEMORY_CONTEXT_ITEMS,
  validateMemoryContextAuthorization,
} from "../../contracts/memory-context.mjs";

const MAX_CONTEXT_TEXT_CHARS = 8192;
const MAX_CONTEXT_PROVENANCE_CHARS = 512;
const MAX_CONTEXT_AUTHORIZATIONS = 4;

function excerpt(value, max) {
  if (value.length <= max) return value;
  return `${value.slice(0, Math.max(0, max - 1))}…`;
}

function intelligenceScope(memoryScope) {
  return ["space", "project"].includes(memoryScope) ? "workspace" : "user";
}

function ownerContextKey(authorization) {
  return `${authorization.ownerKind}\0${authorization.ownerId ?? ""}`;
}

export function retrieveAuthorizedMemoryContext(memoryPort, authorizationValue, {
  query = "",
  limit = 4,
} = {}) {
  const memory = assertMemoryPort(memoryPort);
  const authorization = validateMemoryContextAuthorization(authorizationValue);
  const boundedLimit = Number.isSafeInteger(limit) && limit > 0
    ? Math.min(limit, MAX_MEMORY_CONTEXT_ITEMS)
    : 4;

  const items = memory.search({
    ownerKind: authorization.ownerKind,
    ownerId: authorization.ownerId,
    scopes: authorization.scopes,
    spaceId: authorization.spaceId,
    projectId: authorization.projectId,
    includeRestricted: authorization.includeRestricted,
    query,
    limit: boundedLimit,
  });
  if (!Array.isArray(items) || items.length > boundedLimit) {
    throw new TypeError("Memory port returned an invalid context result set");
  }

  return Object.freeze(items.map((raw) => {
    const item = validateMemoryItem(raw);
    if (!memoryOwnersEqual(item, authorization)) {
      throw new Error("Memory port returned an item owned by another principal");
    }
    if (!authorization.scopes.includes(item.scope)) {
      throw new Error("Memory port returned an item outside authorized scopes");
    }
    if (item.scope === "space" && item.spaceId !== authorization.spaceId) {
      throw new Error("Memory port returned an item from another Space");
    }
    if (item.scope === "project") {
      if (item.projectId !== authorization.projectId) {
        throw new Error("Memory port returned an item from another project");
      }
      if (item.spaceId !== null && item.spaceId !== authorization.spaceId) {
        throw new Error("Memory port returned an item from another Space");
      }
    }
    if (item.sensitivity === "restricted" && !authorization.includeRestricted) {
      throw new Error("Memory port returned restricted context without authorization");
    }
    return Object.freeze({
      // Memory ids are already bounded to the Intelligence context-id ceiling.
      // Do not prefix them here: a 160-character canonical memory id must remain valid.
      id: item.id,
      scope: intelligenceScope(item.scope),
      text: excerpt(item.content, MAX_CONTEXT_TEXT_CHARS),
      // Owner kind is safe provenance metadata and disambiguates the same canonical
      // memory id across device/account without exposing an account subject id.
      provenance: excerpt(
        `memory:${item.ownerKind}:${item.provenance}`,
        MAX_CONTEXT_PROVENANCE_CHARS,
      ),
    });
  }));
}

export function retrieveAuthorizedMemoryContextSet(memoryPort, authorizationValues, {
  query = "",
  limit = MAX_MEMORY_CONTEXT_ITEMS,
} = {}) {
  const memory = assertMemoryPort(memoryPort);
  if (
    !Array.isArray(authorizationValues)
    || authorizationValues.length === 0
    || authorizationValues.length > MAX_CONTEXT_AUTHORIZATIONS
  ) {
    throw new TypeError("Memory context authorization set is outside its allowed bounds");
  }
  const boundedLimit = Number.isSafeInteger(limit) && limit > 0
    ? Math.min(limit, MAX_MEMORY_CONTEXT_ITEMS)
    : MAX_MEMORY_CONTEXT_ITEMS;
  const batches = authorizationValues.map((authorizationValue) => {
    const authorization = validateMemoryContextAuthorization(authorizationValue);
    return Object.freeze({
      ownerKey: ownerContextKey(authorization),
      entries: retrieveAuthorizedMemoryContext(memory, authorization, {
        query,
        limit: boundedLimit,
      }),
    });
  });

  const merged = [];
  const seenOwnerItems = new Set();
  for (let ordinal = 0; merged.length < boundedLimit; ordinal += 1) {
    let progressed = false;
    for (const batch of batches) {
      const entry = batch.entries[ordinal];
      if (!entry) continue;
      progressed = true;
      const identity = `${batch.ownerKey}\0${entry.id}`;
      if (seenOwnerItems.has(identity)) continue;
      seenOwnerItems.add(identity);
      merged.push(entry);
      if (merged.length >= boundedLimit) break;
    }
    if (!progressed) break;
  }
  return Object.freeze(merged);
}
