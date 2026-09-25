import {
  SYNC_CHECKPOINT_STORE_SCHEMA,
  assertSyncCheckpointStore,
  validateSyncCheckpoint,
} from "../../contracts/sync-checkpoint-store.mjs";

const STORAGE_KEY = "ordax.account-sync-checkpoint.v1";

function resolveStorage(windowRef) {
  try {
    const storage = windowRef?.localStorage;
    if (storage && typeof storage.getItem === "function" && typeof storage.setItem === "function") {
      return storage;
    }
  } catch {
    // Browser policy may deny storage. Session memory remains safe.
  }
  return null;
}

export function createWebSyncCheckpointStore(windowRef = globalThis.window) {
  const storage = resolveStorage(windowRef);
  let memory = null;

  const store = {
    schema: SYNC_CHECKPOINT_STORE_SCHEMA,
    scope: storage ? "device" : "session",
    load() {
      if (!storage) return memory;
      try {
        const raw = storage.getItem(STORAGE_KEY);
        memory = raw === null ? null : validateSyncCheckpoint(JSON.parse(raw));
      } catch {
        memory = null;
      }
      return memory;
    },
    save(value) {
      const checkpoint = validateSyncCheckpoint(value);
      memory = checkpoint;
      if (!storage) return false;
      try {
        if (checkpoint === null) {
          storage.removeItem?.(STORAGE_KEY);
        } else {
          storage.setItem(STORAGE_KEY, JSON.stringify(checkpoint));
        }
        return true;
      } catch {
        return false;
      }
    },
  };

  assertSyncCheckpointStore(store);
  return Object.freeze(store);
}
