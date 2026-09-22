import {
  FIRST_RUN_STATE_STORE_SCHEMA,
  assertFirstRunStateStore,
  createInitialFirstRunState,
  validateFirstRunState,
} from "../../contracts/first-run-state-store.mjs";

const FIRST_RUN_ENDPOINT = "/__ordax/native/first-run";

export async function createNativeFirstRunStateStore(windowRef = globalThis.window) {
  if (!windowRef || typeof windowRef.fetch !== "function") {
    throw new TypeError("Native first-run state store requires window.fetch");
  }

  let memory = createInitialFirstRunState();
  try {
    const response = await windowRef.fetch(FIRST_RUN_ENDPOINT, {
      method: "GET",
      cache: "no-store",
      credentials: "same-origin",
    });
    if (response.ok) {
      memory = validateFirstRunState(await response.json());
    }
  } catch {
    // First boot must remain recoverable if durable state is temporarily
    // unreadable. Completion is not dismissed until a later save succeeds.
  }

  const store = {
    schema: FIRST_RUN_STATE_STORE_SCHEMA,
    load() {
      return memory;
    },
    async save(snapshot) {
      const validated = validateFirstRunState(snapshot);
      const response = await windowRef.fetch(FIRST_RUN_ENDPOINT, {
        method: "POST",
        cache: "no-store",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(validated),
      });
      if (!response.ok) {
        throw new Error(`Native first-run persistence failed: ${response.status}`);
      }
      memory = validated;
      return true;
    },
  };

  assertFirstRunStateStore(store);
  return Object.freeze(store);
}
