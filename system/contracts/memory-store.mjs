import {
  memoryIdentityKey,
  validateMemoryItem,
} from "./memory.mjs";

export const MEMORY_STORE_SCHEMA = "ordax.memory-store/1";
export const MEMORY_SNAPSHOT_SCHEMA = "ordax.memory-snapshot/1";
export const MAX_MEMORY_ITEMS = 2048;
export const MAX_MEMORY_SNAPSHOT_BYTES = 8 * 1024 * 1024;

const encoder = new TextEncoder();

function serializedBytes(value) {
  return encoder.encode(JSON.stringify(value)).byteLength;
}

export function parseMemorySnapshotPayload(payload) {
  if (typeof payload !== "string" || payload.includes("\0")) {
    throw new TypeError("Serialized memory snapshot must be a string");
  }
  if (encoder.encode(payload).byteLength > MAX_MEMORY_SNAPSHOT_BYTES) {
    throw new TypeError("Serialized memory snapshot exceeds its byte limit");
  }
  let parsed;
  try {
    parsed = JSON.parse(payload);
  } catch {
    throw new TypeError("Serialized memory snapshot is not valid JSON");
  }
  return validateMemorySnapshot(parsed);
}

export function validateMemorySnapshot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Memory snapshot must be an object");
  }
  if (value.$schema !== MEMORY_SNAPSHOT_SCHEMA || !Array.isArray(value.items)) {
    throw new TypeError("Memory snapshot schema/items are invalid");
  }
  if (value.items.length > MAX_MEMORY_ITEMS) {
    throw new TypeError("Memory snapshot has too many items");
  }
  const items = value.items.map(validateMemoryItem);
  const identities = new Set(items.map((item) => memoryIdentityKey(item)));
  if (identities.size !== items.length) {
    throw new TypeError("Memory item owner/id identities must be unique");
  }
  const snapshot = Object.freeze({
    $schema: MEMORY_SNAPSHOT_SCHEMA,
    items: Object.freeze(items),
  });
  if (serializedBytes(snapshot) > MAX_MEMORY_SNAPSHOT_BYTES) {
    throw new TypeError("Memory snapshot exceeds its byte limit");
  }
  return snapshot;
}

export function assertMemoryStore(store) {
  if (!store || typeof store !== "object" || store.schema !== MEMORY_STORE_SCHEMA) {
    throw new TypeError("A compatible memory store is required");
  }
  if (!["device", "session"].includes(store.scope)) {
    throw new TypeError("Memory store scope must be device or session");
  }
  for (const method of ["load", "save", "flush"]) {
    if (typeof store[method] !== "function") {
      throw new TypeError(`Memory store must implement ${method}()`);
    }
  }
  return store;
}
