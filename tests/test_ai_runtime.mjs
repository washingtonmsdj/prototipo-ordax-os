import assert from "node:assert/strict";
import test from "node:test";

import {
  AI_RUNTIME_SCHEMA,
  validateAiRuntimeSnapshot,
  validateAiRequest,
} from "../system/contracts/ai-runtime.mjs";
import {
  createAiRuntime,
  createUnavailableAiRuntime,
} from "../system/services/ai/runtime.mjs";
import { createLlamaCppProvider } from "../system/services/ai/providers/llama-cpp.mjs";

test("unavailable local AI remains honest and isolated", async () => {
  const runtime = createUnavailableAiRuntime();
  const snapshot = runtime.getSnapshot();
  assert.equal(snapshot.schema, AI_RUNTIME_SCHEMA);
  assert.equal(snapshot.state, "unavailable");
  assert.equal(snapshot.localOnly, true);
  await assert.rejects(runtime.complete({ prompt: "hello" }));
});

test("AI runtime accepts a replaceable local provider and returns bounded text", async () => {
  const provider = {
    id: "test.local",
    modelId: "tiny-test-model",
    localOnly: true,
    async complete({ prompt }) {
      return `local:${prompt}`;
    },
  };
  const runtime = createAiRuntime(provider);
  assert.equal(runtime.getSnapshot().state, "ready");
  assert.equal(runtime.getSnapshot().providerId, "test.local");
  assert.equal(await runtime.complete({ prompt: "hello" }), "local:hello");
  assert.equal(runtime.getSnapshot().state, "ready");
});

test("llama.cpp provider delegates only through host-owned loopback invocation", async () => {
  let request = null;
  const provider = createLlamaCppProvider({
    modelId: "qwen3.5-0.8b-q4_0",
    async invoke(value) {
      request = value;
      return { choices: [{ message: { content: "offline answer" } }] };
    },
  });
  const result = await provider.complete({ prompt: "Explain this", system: "Stay concise" });
  assert.equal(result, "offline answer");
  assert.equal(request.origin, "http://127.0.0.1");
  assert.equal(request.path, "/v1/chat/completions");
  assert.equal(request.body.model, "qwen3.5-0.8b-q4_0");
  assert.equal(request.body.messages.length, 2);
});

test("AI contracts reject cloud-shaped or unbounded provider state", () => {
  assert.throws(() => validateAiRuntimeSnapshot({
    schema: AI_RUNTIME_SCHEMA,
    state: "ready",
    providerId: "cloud",
    modelId: "x",
    localOnly: false,
    message: null,
  }), TypeError);
  assert.throws(() => validateAiRequest({ prompt: "x".repeat(32769) }), TypeError);
});
