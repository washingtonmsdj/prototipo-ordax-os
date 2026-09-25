import assert from "node:assert/strict";
import test from "node:test";

import {
  MEMORY_SNAPSHOT_SCHEMA,
  MEMORY_STORE_SCHEMA,
  validateMemorySnapshot,
} from "../system/contracts/memory-store.mjs";
import { createWebMemoryStore } from "../system/adapters/web/memory.mjs";
import { createMemoryRuntime } from "../system/services/memory/runtime.mjs";

function item(overrides = {}) {
  return {
    id: "mem-1",
    ownerKind: "device",
    ownerId: null,
    scope: "session",
    kind: "fact",
    sensitivity: "private",
    content: "efêmero",
    provenance: "test",
    sourceTimestamp: "2026-09-24T15:00:00Z",
    spaceId: null,
    projectId: null,
    ...overrides,
  };
}

function sessionStore(initial = null) {
  let snapshot = initial;
  return {
    schema: MEMORY_STORE_SCHEMA,
    scope: "session",
    load() { return snapshot; },
    save(value) {
      snapshot = validateMemorySnapshot(value);
      return true;
    },
    async flush() { return true; },
  };
}

test("session-only runtime accepts session memory but rejects durable scopes", () => {
  const memory = createMemoryRuntime({ store: sessionStore() });
  const remembered = memory.remember(item());
  assert.equal(remembered.scope, "session");
  assert.deepEqual(
    memory.search({ ownerKind: "device", scopes: ["session"] }).map((entry) => entry.id),
    ["mem-1"],
  );

  for (const scope of ["device", "space", "project"]) {
    const overrides = {
      id: `durable-${scope}`,
      scope,
      projectId: scope === "project" ? "project-a" : null,
      spaceId: scope === "space" ? "space-a" : null,
    };
    assert.throws(
      () => memory.remember(item(overrides)),
      /cannot accept durable memory scopes/,
    );
  }
});

test("session-only runtime rejects incompatible durable state on load", () => {
  const initial = validateMemorySnapshot({
    $schema: MEMORY_SNAPSHOT_SCHEMA,
    items: [item({ id: "bad-device", scope: "device" })],
  });
  assert.throws(
    () => createMemoryRuntime({ store: sessionStore(initial) }),
    /only session-scoped memory/,
  );
});

test("Web fallback without localStorage refuses durable snapshots instead of pretending persistence", () => {
  const store = createWebMemoryStore({});
  assert.equal(store.scope, "session");
  assert.equal(store.save({
    $schema: MEMORY_SNAPSHOT_SCHEMA,
    items: [item()],
  }), true);
  assert.throws(
    () => store.save({
      $schema: MEMORY_SNAPSHOT_SCHEMA,
      items: [item({ id: "durable", scope: "device" })],
    }),
    /cannot pretend durable scopes/,
  );
});
