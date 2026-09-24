import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_MEMORY_SNAPSHOT_BYTES,
  MEMORY_SNAPSHOT_SCHEMA,
} from "../system/contracts/memory-store.mjs";
import {
  MAX_NATIVE_MEMORY_ENVELOPE_BYTES,
  createNativeMemoryStore,
} from "../system/adapters/native/memory.mjs";

function emptySnapshotPayload() {
  return JSON.stringify({
    $schema: MEMORY_SNAPSHOT_SCHEMA,
    items: [],
  });
}

test("Native memory HTTP envelope ceiling matches the host six-times snapshot policy", () => {
  assert.equal(
    MAX_NATIVE_MEMORY_ENVELOPE_BYTES,
    6 * MAX_MEMORY_SNAPSHOT_BYTES + 1024,
  );
});

test("Native memory GET rejects an oversized real Response before JSON parsing", async () => {
  const body = JSON.stringify({
    payload: emptySnapshotPayload(),
    padding: "x".repeat(MAX_NATIVE_MEMORY_ENVELOPE_BYTES),
  });
  await assert.rejects(
    () => createNativeMemoryStore({
      async fetch() {
        return new Response(body, {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      },
    }),
    /response exceeds its byte limit/,
  );
});

test("Native memory GET fails closed when a fetch-like response exposes body without a stream", async () => {
  let jsonCalls = 0;
  await assert.rejects(
    () => createNativeMemoryStore({
      async fetch() {
        return {
          ok: true,
          body: null,
          async json() {
            jsonCalls += 1;
            return { payload: emptySnapshotPayload() };
          },
        };
      },
    }),
    /does not expose a bounded stream/,
  );
  assert.equal(jsonCalls, 0);
});

test("Native memory GET requires the exact response envelope shape", async () => {
  await assert.rejects(
    () => createNativeMemoryStore({
      async fetch() {
        return {
          ok: true,
          async json() {
            return { payload: emptySnapshotPayload(), extra: true };
          },
        };
      },
    }),
    /response shape is invalid/,
  );
});

test("Native memory POST remains within the host envelope ceiling for a valid snapshot", async () => {
  let postedBody = null;
  const store = await createNativeMemoryStore({
    async fetch(url, options = {}) {
      if (options.method === "GET") {
        return {
          ok: true,
          async json() {
            return { payload: null };
          },
        };
      }
      postedBody = options.body;
      return { ok: true };
    },
  });

  store.save({
    $schema: MEMORY_SNAPSHOT_SCHEMA,
    items: [],
  });
  await store.flush();
  assert.equal(typeof postedBody, "string");
  assert.ok(new TextEncoder().encode(postedBody).byteLength <= MAX_NATIVE_MEMORY_ENVELOPE_BYTES);
});
