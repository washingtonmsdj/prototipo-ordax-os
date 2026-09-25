import assert from "node:assert/strict";
import test from "node:test";

import {
  INTELLIGENCE_PORT_SCHEMA,
  INTELLIGENCE_RESPONSE_SCHEMA,
} from "../system/contracts/intelligence.mjs";
import { MEMORY_PORT_SCHEMA } from "../system/contracts/memory.mjs";
import {
  AUTHORIZED_MEMORY_INTELLIGENCE_SCHEMA,
  createAuthorizedMemoryIntelligence,
} from "../system/services/intelligence/authorized-memory.mjs";

const deviceAuthorization = Object.freeze({
  authority: "composition",
  ownerKind: "device",
  ownerId: null,
  scopes: ["device"],
  spaceId: null,
  projectId: null,
  includeRestricted: false,
});

function memoryItem({ id = "mem-1", content = "Preferência local" } = {}) {
  return {
    id,
    ownerKind: "device",
    ownerId: null,
    scope: "device",
    kind: "fact",
    sensitivity: "private",
    content,
    provenance: "test-memory",
    sourceTimestamp: "2026-09-24T12:00:00Z",
    spaceId: null,
    projectId: null,
  };
}

function memoryPort(items = [memoryItem()]) {
  const searches = [];
  return {
    schema: MEMORY_PORT_SCHEMA,
    searches,
    search(request) {
      searches.push(request);
      return items.slice(0, request.limit);
    },
    remember() { return true; },
    forget() { return false; },
    async flush() { return true; },
  };
}

function intelligencePort() {
  const requests = [];
  return {
    schema: INTELLIGENCE_PORT_SCHEMA,
    requests,
    getSnapshot() {
      return {
        schema: INTELLIGENCE_PORT_SCHEMA,
        state: "ready",
        inferenceAvailable: true,
        engineId: "llama.cpp",
        modelId: "qwen-test",
        authority: "none",
        toolExecution: false,
      };
    },
    subscribe() { return () => {}; },
    async respond(request) {
      requests.push(request);
      return {
        schema: INTELLIGENCE_RESPONSE_SCHEMA,
        text: "ok",
        engineId: "llama.cpp",
        modelId: "qwen-test",
        authority: "none",
      };
    },
  };
}

test("authorized-memory bridge requires explicit composition authorization", async () => {
  const memory = memoryPort();
  const intelligence = intelligencePort();
  const bridge = createAuthorizedMemoryIntelligence({
    intelligencePort: intelligence,
    memoryPort: memory,
  });

  assert.equal(bridge.schema, AUTHORIZED_MEMORY_INTELLIGENCE_SCHEMA);
  await assert.rejects(
    () => bridge.respond({ prompt: "responda" }),
    /bounded authorization set/,
  );
  assert.equal(memory.searches.length, 0);
  assert.equal(intelligence.requests.length, 0);
});

test("authorized-memory bridge injects only explicitly authorized local memory", async () => {
  const memory = memoryPort([memoryItem({ content: "Prefere respostas curtas" })]);
  const intelligence = intelligencePort();
  const bridge = createAuthorizedMemoryIntelligence({
    intelligencePort: intelligence,
    memoryPort: memory,
  });

  await bridge.respond(
    { intent: "ask", prompt: "Como devo responder?" },
    { authorizations: [deviceAuthorization], memoryLimit: 2 },
  );

  assert.equal(memory.searches.length, 1);
  assert.equal(memory.searches[0].ownerKind, "device");
  assert.equal(memory.searches[0].ownerId, null);
  assert.equal(memory.searches[0].query, "Como devo responder?");
  assert.deepEqual(memory.searches[0].scopes, ["device"]);
  assert.equal(intelligence.requests.length, 1);
  assert.equal(intelligence.requests[0].context.length, 1);
  assert.equal(intelligence.requests[0].context[0].text, "Prefere respostas curtas");
  assert.equal(intelligence.requests[0].context[0].provenance, "memory:device:test-memory");
});

test("consumer-selected context has priority over memory item budget", async () => {
  const memory = memoryPort([
    memoryItem({ id: "mem-a", content: "A" }),
    memoryItem({ id: "mem-b", content: "B" }),
  ]);
  const intelligence = intelligencePort();
  const bridge = createAuthorizedMemoryIntelligence({
    intelligencePort: intelligence,
    memoryPort: memory,
  });
  const context = Array.from({ length: 15 }, (_, index) => ({
    id: `doc-${index}`,
    scope: "document",
    text: `documento ${index}`,
    provenance: "explicit-consumer-context",
  }));

  await bridge.respond(
    { prompt: "resuma", context },
    { authorizations: [deviceAuthorization], memoryLimit: 8 },
  );

  assert.equal(memory.searches.length, 1);
  assert.equal(memory.searches[0].limit, 1);
  assert.equal(intelligence.requests[0].context.length, 16);
  assert.deepEqual(
    intelligence.requests[0].context.slice(0, 15).map((entry) => entry.id),
    context.map((entry) => entry.id),
  );
  assert.equal(intelligence.requests[0].context[15].id, "mem-a");
});

test("full consumer context skips memory access instead of evicting explicit context", async () => {
  const memory = memoryPort();
  const intelligence = intelligencePort();
  const bridge = createAuthorizedMemoryIntelligence({
    intelligencePort: intelligence,
    memoryPort: memory,
  });
  const context = Array.from({ length: 16 }, (_, index) => ({
    id: `doc-${index}`,
    scope: "document",
    text: `documento ${index}`,
    provenance: "explicit-consumer-context",
  }));

  await bridge.respond(
    { prompt: "resuma", context },
    { authorizations: [deviceAuthorization] },
  );

  assert.equal(memory.searches.length, 0);
  assert.deepEqual(intelligence.requests[0].context, context);
});

test("memory retrieval query is bounded before reaching the memory port", async () => {
  const memory = memoryPort();
  const intelligence = intelligencePort();
  const bridge = createAuthorizedMemoryIntelligence({
    intelligencePort: intelligence,
    memoryPort: memory,
  });
  const prompt = "p".repeat(2000);

  await bridge.respond(
    { prompt },
    { authorizations: [deviceAuthorization] },
  );
  assert.equal(memory.searches[0].query.length, 1024);

  await assert.rejects(
    () => bridge.respond(
      { prompt: "ok" },
      {
        authorizations: [deviceAuthorization],
        memoryQuery: "q".repeat(1025),
      },
    ),
    /query is outside its allowed bounds/,
  );
  assert.equal(memory.searches.length, 1);
});
