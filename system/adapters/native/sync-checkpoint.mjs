import {
  SYNC_CHECKPOINT_STORE_SCHEMA,
  assertSyncCheckpointStore,
  validateSyncCheckpoint,
} from "../../contracts/sync-checkpoint-store.mjs";

const ENDPOINT = "/__ordax/native/sync-checkpoint";

export async function createNativeSyncCheckpointStore(windowRef = globalThis.window) {
  if (!windowRef || typeof windowRef.fetch !== "function") {
    throw new TypeError("Native sync checkpoint store requires window.fetch");
  }

  let memory = null;
  let durable = false;
  try {
    const response = await windowRef.fetch(ENDPOINT, {
      method: "GET",
      cache: "no-store",
      credentials: "same-origin",
    });
    if (response.ok) {
      const body = await response.json();
      memory = validateSyncCheckpoint(body?.checkpoint ?? null);
      durable = true;
    }
  } catch {
    // Account continuity is optional for boot; use session memory.
  }

  let persistQueue = Promise.resolve();
  const persist = async (checkpoint) => {
    const response = await windowRef.fetch(ENDPOINT, {
      method: "POST",
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checkpoint }),
    });
    if (!response.ok) {
      throw new Error(`Native sync checkpoint persistence failed: ${response.status}`);
    }
  };

  const store = {
    schema: SYNC_CHECKPOINT_STORE_SCHEMA,
    scope: durable ? "device" : "session",
    load() {
      return memory;
    },
    save(value) {
      const checkpoint = validateSyncCheckpoint(value);
      memory = checkpoint;
      persistQueue = persistQueue.then(() => persist(checkpoint)).catch(() => false);
      return true;
    },
  };

  assertSyncCheckpointStore(store);
  return Object.freeze(store);
}
