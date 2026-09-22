import assert from "node:assert/strict";
import test from "node:test";

import { createLocalAiRuntime } from "../system/services/local-ai/runtime.mjs";

test("local AI stays unavailable without an installed model", async () => {
  const runtime = createLocalAiRuntime({
    fetchImpl: async () => { throw new Error("must not fetch"); },
    modelId: null,
  });
  assert.equal(runtime.getSnapshot().state, "unavailable");
  assert.equal(runtime.getSnapshot().offline, true);
  assert.equal(runtime.getSnapshot().migratable, true);
});

test("local AI probes loopback and generates through compatible API", async () => {
  const requests = [];
  const runtime = createLocalAiRuntime({
    modelId: "ordax-small",
    fetchImpl: async (url, options = {}) => {
      requests.push([url, options]);
      if (url.endsWith("/health")) return { ok: true };
      return {
        ok: true,
        async json() {
          return { choices: [{ message: { content: "resposta local" } }] };
        },
      };
    },
  });
  await runtime.probe();
  assert.equal(runtime.getSnapshot().state, "ready");
  const result = await runtime.generate({ prompt: "teste", maxTokens: 32 });
  assert.equal(result.text, "resposta local");
  assert.equal(requests.length, 2);
  assert.match(requests[0][0], /^http:\/\/127\.0\.0\.1:/);
  assert.match(requests[1][0], /\/v1\/chat\/completions$/);
});

test("local AI rejects non-loopback endpoints", () => {
  assert.throws(
    () => createLocalAiRuntime({ endpoint: "https://example.com", modelId: "x" }),
    /loopback/,
  );
});
