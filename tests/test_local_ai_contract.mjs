import assert from "node:assert/strict";
import test from "node:test";

import {
  LOCAL_AI_PORT_SCHEMA,
  LOCAL_AI_RESPONSE_SCHEMA,
  LOCAL_AI_STATUS_SCHEMA,
  assertLocalAiPort,
  validateLocalAiMessages,
  validateLocalAiResponse,
} from "../system/contracts/local-ai.mjs";
import { assistantApp } from "../system/apps/assistant/app.mjs";

test("assistant is a capability-gated first-party app", () => {
  assert.equal(assistantApp.id, "assistant");
  assert.deepEqual(assistantApp.requiredCapabilities, ["ai.local"]);
  assert.equal(assistantApp.component.criticality, "optional");
});

test("local AI contract keeps bounded local chat semantics", () => {
  const messages = validateLocalAiMessages([{ role: "user", content: "Olá" }]);
  assert.equal(messages.length, 1);
  assert.throws(() => validateLocalAiMessages([]), TypeError);
  assert.throws(() => validateLocalAiMessages([{ role: "tool", content: "x" }]), TypeError);
  const response = validateLocalAiResponse({
    schema: LOCAL_AI_RESPONSE_SCHEMA,
    text: "Oi",
    backend: "llama.cpp",
    model: "small-model",
  });
  assert.equal(response.text, "Oi");
});

test("local AI port is provider-neutral", () => {
  const port = {
    schema: LOCAL_AI_PORT_SCHEMA,
    getSnapshot() {
      return {
        schema: LOCAL_AI_STATUS_SCHEMA,
        state: "ready",
        backend: "llama.cpp",
        model: "small-model",
      };
    },
    async complete() {
      return {
        schema: LOCAL_AI_RESPONSE_SCHEMA,
        text: "ok",
        backend: "llama.cpp",
        model: "small-model",
      };
    },
  };
  assert.equal(assertLocalAiPort(port), port);
});
