import assert from "node:assert/strict";
import test from "node:test";

import { LOCAL_AI_PORT_SCHEMA } from "../system/contracts/local-ai.mjs";
import {
  INTELLIGENCE_PORT_SCHEMA,
  validateIntelligenceRequest,
} from "../system/contracts/intelligence.mjs";
import { createIntelligenceRuntime } from "../system/services/intelligence/runtime.mjs";

function inferencePort({
  state = "ready",
  engineId = "llama.cpp",
  modelId = "qwen-small",
  answer = "resultado local",
} = {}) {
  let snapshot = Object.freeze({
    schema: LOCAL_AI_PORT_SCHEMA,
    state,
    engineId: state === "unavailable" ? null : engineId,
    modelId: state === "unavailable" ? null : modelId,
    offline: true,
    migratable: true,
  });
  const listeners = new Set();
  return Object.freeze({
    schema: LOCAL_AI_PORT_SCHEMA,
    getSnapshot: () => snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    async generate(request) {
      assert.match(request.prompt, /Ordax Intelligence/);
      assert.match(request.prompt, /provenance: local-note/);
      return Object.freeze({ text: answer, engineId, modelId });
    },
    publish(nextState) {
      snapshot = Object.freeze({ ...snapshot, state: nextState });
      for (const listener of listeners) listener(snapshot);
    },
  });
}

test("Ordax Intelligence is a system contract with zero implicit mutation authority", () => {
  const inference = inferencePort();
  const intelligence = createIntelligenceRuntime({ inferencePort: inference });
  const snapshot = intelligence.getSnapshot();
  assert.equal(intelligence.schema, INTELLIGENCE_PORT_SCHEMA);
  assert.equal(snapshot.state, "ready");
  assert.equal(snapshot.inferenceAvailable, true);
  assert.equal(snapshot.authority, "none");
  assert.equal(snapshot.toolExecution, false);
  intelligence.dispose();
});

test("Ordax Intelligence consumes bounded provenance-bearing context through local inference", async () => {
  const intelligence = createIntelligenceRuntime({ inferencePort: inferencePort() });
  const response = await intelligence.respond({
    intent: "summarize",
    prompt: "Resuma a nota.",
    context: [{
      id: "note-1",
      scope: "document",
      text: "Conteúdo autorizado.",
      provenance: "local-note",
    }],
    maxTokens: 128,
  });
  assert.equal(response.text, "resultado local");
  assert.equal(response.authority, "none");
  intelligence.dispose();
});

test("backend absence degrades Intelligence without becoming an OS boot contract", async () => {
  const intelligence = createIntelligenceRuntime({
    inferencePort: inferencePort({ state: "unavailable" }),
  });
  assert.equal(intelligence.getSnapshot().state, "degraded");
  assert.equal(intelligence.getSnapshot().inferenceAvailable, false);
  await assert.rejects(
    () => intelligence.respond({ prompt: "teste" }),
    /not ready/,
  );
  intelligence.dispose();
});

test("engine and model migration remain behind the Intelligence boundary", async () => {
  const intelligence = createIntelligenceRuntime({
    inferencePort: inferencePort({
      engineId: "future-engine",
      modelId: "future-model",
      answer: "ok",
    }),
  });
  const response = await intelligence.respond({
    intent: "ask",
    prompt: "Teste de migração.",
    context: [{
      id: "system-state",
      scope: "system",
      text: "estado",
      provenance: "local-note",
    }],
  });
  assert.equal(response.engineId, "future-engine");
  assert.equal(response.modelId, "future-model");
  intelligence.dispose();
});

test("Intelligence rejects unbounded or authority-shaped input before inference", () => {
  assert.throws(
    () => validateIntelligenceRequest({
      prompt: "x",
      context: Array.from({ length: 17 }, (_, index) => ({
        id: `item-${index}`,
        scope: "document",
        text: "x",
        provenance: "test",
      })),
    }),
    /bounded array/,
  );
});
