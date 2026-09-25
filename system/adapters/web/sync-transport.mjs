import { SYNC_TRANSPORT_SCHEMA, assertSyncTransportPort } from "../../contracts/sync-transport.mjs";

const BATCH_SCHEMA = "prototype-ordax.sync-batch/1";
const ACK_SCHEMA = "prototype-ordax.sync-ack/1";

async function readJson(response) {
  const value = await response.json();
  if (!value || typeof value !== "object") throw new Error("Invalid sync gateway response");
  return value;
}

export function createWebSyncTransport(windowRef = globalThis.window) {
  if (!windowRef || typeof windowRef.fetch !== "function") {
    throw new TypeError("Web sync transport requires window.fetch");
  }

  const port = {
    schema: SYNC_TRANSPORT_SCHEMA,
    async listObjects({ afterRevision = 0, limit = 200 } = {}) {
      const response = await windowRef.fetch(
        `/sync/objects?afterRevision=${encodeURIComponent(afterRevision)}&limit=${encodeURIComponent(limit)}`,
        { method: "GET", credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error(`Sync read failed: ${response.status}`);
      const value = await readJson(response);
      if (value.$schema !== BATCH_SCHEMA || !Array.isArray(value.objects)) {
        throw new Error("Invalid sync batch");
      }
      return Object.freeze(value.objects.map((item) => Object.freeze({ ...item })));
    },
    async applyMutation(mutation) {
      const response = await windowRef.fetch("/sync/mutate", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(mutation),
      });
      if (!response.ok) throw new Error(`Sync mutation failed: ${response.status}`);
      const value = await readJson(response);
      if (value.$schema !== ACK_SCHEMA) throw new Error("Invalid sync acknowledgement");
      return Object.freeze({ ...value });
    },
  };
  assertSyncTransportPort(port);
  return Object.freeze(port);
}
