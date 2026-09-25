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

function pendingUntilAbort(options = {}) {
  return new Promise((resolve, reject) => {
    const abort = () => reject(new Error("aborted"));
    if (options.signal?.aborted) {
      abort();
      return;
    }
    options.signal?.addEventListener("abort", abort, { once: true });
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

test("Native memory GET timeout covers a stalled response body", async () => {
  await assert.rejects(
    () => createNativeMemoryStore({
      async fetch() {
        return {
          ok: true,
          headers: { get() { return null; } },
          body: {
            getReader() {
              return {
                read() { return new Promise(() => {}); },
                async cancel() {},
              };
            },
          },
        };
      },
    }, { requestTimeoutMs: 100 }),
    /memory load timed out after 100ms/,
  );
});

test("Native memory POST timeout is surfaced by flush after one bounded retry", async () => {
  let postCalls = 0;
  const store = await createNativeMemoryStore({
    async fetch(url, options = {}) {
      if (options.method === "GET") {
        return {
          ok: true,
          async json() { return { payload: null }; },
        };
      }
      postCalls += 1;
      return pendingUntilAbort(options);
    },
  }, { requestTimeoutMs: 100 });

  store.save({ $schema: MEMORY_SNAPSHOT_SCHEMA, items: [] });
  await assert.rejects(
    () => store.flush(),
    /memory persistence timed out after 100ms/,
  );
  assert.equal(postCalls, 2);
});

test("Native memory rejects an invalid request timeout before touching the endpoint", async () => {
  let fetchCalls = 0;
  await assert.rejects(
    () => createNativeMemoryStore({
      async fetch() {
        fetchCalls += 1;
        return { ok: true, async json() { return { payload: null }; } };
      },
    }, { requestTimeoutMs: 99 }),
    /request timeout/,
  );
  assert.equal(fetchCalls, 0);
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
