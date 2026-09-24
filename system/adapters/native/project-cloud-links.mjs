import {
  PROJECT_CLOUD_LINK_STORE_SCHEMA,
  assertProjectCloudLinkStore,
  createEmptyProjectCloudLinkState,
  validateProjectCloudLinkState,
} from "../../contracts/project-cloud-link-store.mjs";

const STORAGE_KEY = "ordax.native.project-cloud-links.v1";
const RECORD_SCHEMA = "ordax.native.project-cloud-links-record/1";

function resolveStorage(windowRef) {
  try {
    const storage = windowRef?.localStorage;
    if (
      storage
      && typeof storage.getItem === "function"
      && typeof storage.setItem === "function"
    ) {
      return storage;
    }
  } catch {
    // Offline/local project use must continue even if this optional link store is denied.
  }
  return null;
}

export function createNativeProjectCloudLinkStore(windowRef = globalThis.window) {
  const storage = resolveStorage(windowRef);
  let memory = createEmptyProjectCloudLinkState();

  const store = {
    schema: PROJECT_CLOUD_LINK_STORE_SCHEMA,
    scope: storage ? "device" : "session",
    load() {
      if (!storage) return memory;
      try {
        const raw = storage.getItem(STORAGE_KEY);
        if (raw === null) return memory;
        const record = JSON.parse(raw);
        if (!record || record.schema !== RECORD_SCHEMA) {
          memory = createEmptyProjectCloudLinkState();
          return memory;
        }
        memory = validateProjectCloudLinkState(record.state);
      } catch {
        memory = createEmptyProjectCloudLinkState();
      }
      return memory;
    },
    save(state) {
      memory = validateProjectCloudLinkState(state);
      if (!storage) return false;
      try {
        storage.setItem(
          STORAGE_KEY,
          JSON.stringify({ schema: RECORD_SCHEMA, state: memory }),
        );
        return true;
      } catch {
        return false;
      }
    },
  };

  assertProjectCloudLinkStore(store);
  return Object.freeze(store);
}
