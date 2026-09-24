import {
  MAX_MEMORY_SNAPSHOT_BYTES,
  MEMORY_STORE_SCHEMA,
  assertMemoryStore,
  parseMemorySnapshotPayload,
  validateMemorySnapshot,
} from "../../contracts/memory-store.mjs";

export const MEMORY_ENDPOINT = "/__ordax/native/intelligence-memory";
export const MAX_NATIVE_MEMORY_ENVELOPE_BYTES = 6 * MAX_MEMORY_SNAPSHOT_BYTES + 1024;

const encoder = new TextEncoder();

function validateDeviceSnapshot(snapshot) {
  const validated = validateMemorySnapshot(snapshot);
  if (validated.items.some((item) => item.scope === "session")) {
    throw new TypeError("Native device memory cannot persist session-scoped memory");
  }
  return validated;
}

function parseDevicePayload(payload) {
  const validated = parseMemorySnapshotPayload(payload);
  if (validated.items.some((item) => item.scope === "session")) {
    throw new TypeError("Native device memory cannot load session-scoped memory");
  }
  return validated;
}

function declaredContentLength(response) {
  const raw = response?.headers?.get?.("content-length");
  if (typeof raw !== "string" || !/^\d+$/.test(raw.trim())) return null;
  const value = Number(raw);
  return Number.isSafeInteger(value) ? value : null;
}

function parseJsonText(text) {
  try {
    return JSON.parse(text);
  } catch {
    throw new Error("Native Intelligence memory response is not valid JSON");
  }
}

async function readBoundedEnvelope(response) {
  const declared = declaredContentLength(response);
  if (declared !== null && declared > MAX_NATIVE_MEMORY_ENVELOPE_BYTES) {
    throw new Error("Native Intelligence memory response exceeds its byte limit");
  }

  if (response?.body && typeof response.body.getReader === "function") {
    const reader = response.body.getReader();
    const chunks = [];
    let total = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!(value instanceof Uint8Array)) {
        try { await reader.cancel(); } catch {}
        throw new Error("Native Intelligence memory response body is invalid");
      }
      total += value.byteLength;
      if (total > MAX_NATIVE_MEMORY_ENVELOPE_BYTES) {
        try { await reader.cancel(); } catch {}
        throw new Error("Native Intelligence memory response exceeds its byte limit");
      }
      chunks.push(value);
    }

    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    let text;
    try {
      text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    } catch {
      throw new Error("Native Intelligence memory response is not valid UTF-8");
    }
    return parseJsonText(text);
  }

  if (response && typeof response === "object" && "body" in response) {
    throw new Error("Native Intelligence memory response does not expose a bounded stream");
  }

  // Compatibility for injected test doubles only. Production fetch Response
  // objects expose body and therefore take the bounded stream path or fail closed.
  if (typeof response?.json === "function") return response.json();
  throw new Error("Native Intelligence memory response body is unreadable");
}

function validateEnvelope(value) {
  if (
    !value
    || typeof value !== "object"
    || Array.isArray(value)
    || Object.keys(value).length !== 1
    || !Object.hasOwn(value, "payload")
  ) {
    throw new TypeError("Native Intelligence memory response shape is invalid");
  }
  if (value.payload !== null && typeof value.payload !== "string") {
    throw new TypeError("Native Intelligence memory response payload is invalid");
  }
  return value;
}

export async function createNativeMemoryStore(windowRef = globalThis.window) {
  if (!windowRef || typeof windowRef.fetch !== "function") {
    throw new TypeError("Native memory store requires window.fetch");
  }

  let memory = null;
  const response = await windowRef.fetch(MEMORY_ENDPOINT, {
    method: "GET",
    cache: "no-store",
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(`Native Intelligence memory persistence unavailable: ${response.status}`);
  }
  const initial = validateEnvelope(await readBoundedEnvelope(response));
  if (initial.payload !== null) {
    memory = parseDevicePayload(initial.payload);
  }

  let desiredRevision = 0;
  let durableRevision = 0;
  let persistQueue = Promise.resolve(true);
  let lastPersistError = null;

  const persist = async (snapshot) => {
    const body = JSON.stringify({ payload: JSON.stringify(snapshot) });
    if (encoder.encode(body).byteLength > MAX_NATIVE_MEMORY_ENVELOPE_BYTES) {
      throw new Error("Native Intelligence memory request exceeds its byte limit");
    }
    const next = await windowRef.fetch(MEMORY_ENDPOINT, {
      method: "POST",
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body,
    });
    if (!next.ok) {
      throw new Error(`Native Intelligence memory persistence failed: ${next.status}`);
    }
    return true;
  };

  const enqueuePersist = (snapshot, revision) => {
    const operation = persistQueue.then(async () => {
      try {
        await persist(snapshot);
        durableRevision = Math.max(durableRevision, revision);
        if (revision === desiredRevision) lastPersistError = null;
        return true;
      } catch (error) {
        if (revision === desiredRevision) {
          lastPersistError = error instanceof Error
            ? error
            : new Error("Native Intelligence memory persistence failed");
        }
        return false;
      }
    });
    persistQueue = operation;
    return operation;
  };

  const store = {
    schema: MEMORY_STORE_SCHEMA,
    scope: "device",
    load() {
      return memory;
    },
    save(snapshot) {
      const validated = validateDeviceSnapshot(snapshot);
      memory = validated;
      desiredRevision += 1;
      enqueuePersist(validated, desiredRevision);
      return true;
    },
    async flush() {
      const targetRevision = desiredRevision;
      if (durableRevision >= targetRevision) return true;

      await persistQueue;
      if (durableRevision >= targetRevision) return true;

      // A queued POST for the target failed. Retry the current desired snapshot
      // once for this flush call. A newer queued save may become durable before
      // this retry runs; durability is therefore decided by revision, not by the
      // retry operation's standalone result.
      const retrySnapshot = memory;
      const retryRevision = desiredRevision;
      await enqueuePersist(retrySnapshot, retryRevision);
      if (durableRevision < targetRevision) {
        throw lastPersistError ?? new Error("Native Intelligence memory persistence failed");
      }
      return true;
    },
  };

  assertMemoryStore(store);
  return Object.freeze(store);
}
