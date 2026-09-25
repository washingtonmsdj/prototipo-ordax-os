import assert from "node:assert/strict";
import test from "node:test";

import { createLocalAiRuntime } from "../system/services/local-ai/runtime.mjs";

const create = (endpoint) => createLocalAiRuntime({
  endpoint,
  modelId: "x",
  fetchImpl: async () => ({ ok: false }),
});

test("Local AI accepts only literal 127.0.0.1 HTTP endpoints", () => {
  assert.doesNotThrow(() => create("http://127.0.0.1:17865"));
  assert.doesNotThrow(() => create("http://127.0.0.1:17865/base/path?ignored=true#fragment"));

  for (const endpoint of [
    "http://localhost:17865",
    "http://127.0.0.2:17865",
    "https://127.0.0.1:17865",
    "https://example.com",
    "http://2130706433:17865",
    "http://127.1:17865",
    "http://0177.0.0.1:17865",
    "http://0x7f000001:17865",
    "http://user:pass@127.0.0.1:17865",
    "http://127.0.0.1.:17865",
    "HTTP://127.0.0.1:17865",
    "http://127.0.0.1:99999",
    "http://127.0.0.1:@example.com",
  ]) {
    assert.throws(
      () => create(endpoint),
      /literal 127\.0\.0\.1 HTTP/,
      endpoint,
    );
  }
});
