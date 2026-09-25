import {
  MAX_VISIBLE_SPACES,
  SPACES_PORT_SCHEMA,
  SPACES_SNAPSHOT_SCHEMA,
  validateSpace,
  validateSpacesSnapshot,
} from "../../contracts/spaces.mjs";

const ACCOUNT_SPACES_SCHEMA = "prototype-ordax.account-spaces/1";

function snapshot(state, spaces = []) {
  return validateSpacesSnapshot({
    schema: SPACES_SNAPSHOT_SCHEMA,
    state,
    spaces,
  });
}

function normalizeResponse(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Account Spaces response must be an object");
  }
  if (value.$schema !== ACCOUNT_SPACES_SCHEMA) {
    throw new TypeError("Account Spaces response schema is incompatible");
  }
  if (!Array.isArray(value.spaces) || value.spaces.length > MAX_VISIBLE_SPACES) {
    throw new TypeError("Account Spaces response is outside its bounds");
  }
  return Object.freeze(value.spaces.map(validateSpace));
}

export function createWebSpacesCatalog(windowRef = globalThis.window) {
  if (!windowRef || typeof windowRef.fetch !== "function") {
    throw new TypeError("Web Spaces catalog requires window.fetch");
  }

  let current = snapshot("idle");
  let refreshOrdinal = 0;
  let disposed = false;
  let activeController = null;
  const listeners = new Set();

  const publish = (next) => {
    current = next;
    if (disposed) return;
    for (const listener of [...listeners]) listener(current);
  };

  return Object.freeze({
    schema: SPACES_PORT_SCHEMA,
    getSnapshot() {
      return current;
    },
    subscribe(listener) {
      if (typeof listener !== "function") {
        throw new TypeError("Spaces listener must be a function");
      }
      if (disposed) return () => {};
      listeners.add(listener);
      listener(current);
      return () => listeners.delete(listener);
    },
    reset() {
      if (disposed) return;
      refreshOrdinal += 1;
      activeController?.abort();
      activeController = null;
      publish(snapshot("unavailable"));
    },
    async refresh() {
      if (disposed) throw new Error("Spaces catalog is disposed");
      const ordinal = ++refreshOrdinal;
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;
      publish(snapshot("loading"));
      try {
        const response = await windowRef.fetch("/account/spaces", {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          redirect: "error",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (ordinal !== refreshOrdinal || disposed) return current;
        if (response.status === 401) {
          publish(snapshot("unavailable"));
          return current;
        }
        if (!response.ok) {
          publish(snapshot("error"));
          return current;
        }
        const spaces = normalizeResponse(await response.json());
        if (ordinal !== refreshOrdinal || disposed) return current;
        publish(snapshot("ready", spaces));
        return current;
      } catch (error) {
        if (ordinal !== refreshOrdinal || disposed) return current;
        if (controller.signal.aborted) return current;
        publish(snapshot("error"));
        return current;
      } finally {
        if (activeController === controller) activeController = null;
      }
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      refreshOrdinal += 1;
      activeController?.abort();
      activeController = null;
      listeners.clear();
      current = snapshot("unavailable");
    },
  });
}
