import { SYNC_TRANSPORT_SCHEMA, assertSyncTransportPort } from "../../contracts/sync-transport.mjs";

const BATCH_SCHEMA = "prototype-ordax.sync-batch/1";
const SNAPSHOT_SCHEMA = "prototype-ordax.sync-snapshot/1";
const CHANGES_SCHEMA = "prototype-ordax.sync-changes/1";
const ACK_SCHEMA = "prototype-ordax.sync-ack/1";

function safeCursor(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new Error(`Invalid sync ${label}`);
  }
  return value;
}

async function readJson(response) {
  const value = await response.json();
  if (!value || typeof value !== "object") throw new Error("Invalid sync gateway response");
  return value;
}

function freezeObjects(items) {
  return Object.freeze(items.map((item) => Object.freeze({ ...item })));
}

export function createWebSyncTransport(windowRef = globalThis.window) {
  if (!windowRef || typeof windowRef.fetch !== "function") {
    throw new TypeError("Web sync transport requires window.fetch");
  }

  const port = {
    schema: SYNC_TRANSPORT_SCHEMA,
    async snapshot({ limit = 200 } = {}) {
      const response = await windowRef.fetch(
        `/sync/snapshot?limit=${encodeURIComponent(limit)}`,
        { method: "GET", credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error(`Sync snapshot failed: ${response.status}`);
      const value = await readJson(response);
      if (value.$schema !== SNAPSHOT_SCHEMA || !Array.isArray(value.objects)) {
        throw new Error("Invalid sync snapshot");
      }
      return Object.freeze({
        cursor: safeCursor(value.cursor, "snapshot cursor"),
        objects: freezeObjects(value.objects),
      });
    },
    async pullChanges({ afterCursor = 0, limit = 200 } = {}) {
      const response = await windowRef.fetch(
        `/sync/changes?afterCursor=${encodeURIComponent(afterCursor)}&limit=${encodeURIComponent(limit)}`,
        { method: "GET", credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error(`Sync pull failed: ${response.status}`);
      const value = await readJson(response);
      if (value.$schema !== CHANGES_SCHEMA || !Array.isArray(value.changes)) {
        throw new Error("Invalid sync changes");
      }
      const checkedAfter = safeCursor(value.afterCursor, "after cursor");
      const nextCursor = safeCursor(value.nextCursor, "next cursor");
      if (checkedAfter !== afterCursor || nextCursor < checkedAfter) {
        throw new Error("Invalid sync cursor progression");
      }
      const changes = freezeObjects(value.changes);
      for (const change of changes) {
        safeCursor(change.cursor, "change cursor");
        if (change.cursor <= checkedAfter || change.cursor > nextCursor) {
          throw new Error("Sync change cursor is outside the returned range");
        }
      }
      return Object.freeze({ afterCursor: checkedAfter, nextCursor, changes });
    },
    async listObjects({ limit = 200 } = {}) {
      const result = await port.snapshot({ limit });
      return result.objects;
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
      if (value.changeCursor !== null && value.changeCursor !== undefined) {
        safeCursor(value.changeCursor, "acknowledgement cursor");
      }
      return Object.freeze({ ...value });
    },
  };
  assertSyncTransportPort(port);
  return Object.freeze(port);
}
