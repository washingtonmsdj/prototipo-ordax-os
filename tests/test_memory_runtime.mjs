import assert from "node:assert/strict";
import test from "node:test";

import {
  MEMORY_STORE_SCHEMA,
  MEMORY_SNAPSHOT_SCHEMA,
  validateMemorySnapshot,
} from "../system/contracts/memory-store.mjs";
import { createMemoryRuntime } from "../system/services/memory/runtime.mjs";

function memoryItem({
  id,
  ownerKind,
  ownerId = "owner-a",
  scope = "account",
  kind = "fact",
  sensitivity = "private",
  content = "conteúdo",
  provenance = "test-fixture",
  sourceTimestamp = "2026-09-24T15:00:00Z",
  spaceId = null,
  projectId = null,
} = {}) {
  return {
    id,
    ownerKind,
    ownerId,
    scope,
    kind,
    sensitivity,
    content,
    provenance,
    sourceTimestamp,
    spaceId,
    projectId,
  };
}

function memoryStore({
  scope = "device",
  initial = null,
  saveResult = true,
  flushResult = true,
  flushError = null,
} = {}) {
  let snapshot = initial;
  const saves = [];
  return {
    schema: MEMORY_STORE_SCHEMA,
    scope,
    load() {
      return snapshot;
    },
    save(value) {
      const validated = validateMemorySnapshot(value);
      saves.push(validated);
      if (!saveResult) return false;
      snapshot = validated;
      return true;
    },
    async flush() {
      if (flushError) throw flushError;
      return flushResult;
    },
    get snapshot() {
      return snapshot;
    },
    saves,
  };
}

test("memory runtime supports review, edit and delete through the stable port", () => {
  const store = memoryStore();
  const memory = createMemoryRuntime({ store });

  memory.remember(memoryItem({
    id: "mem-1",
    content: "Preferência inicial",
  }));
  memory.remember(memoryItem({
    id: "mem-1",
    content: "Preferência editada",
    sourceTimestamp: "2026-09-24T16:00:00Z",
  }));

  const review = memory.search({ ownerId: "owner-a", scopes: ["account"] });
  assert.equal(review.length, 1);
  assert.equal(review[0].content, "Preferência editada");
  assert.equal(store.snapshot.items.length, 1);
  assert.equal(store.snapshot.items[0].content, "Preferência editada");

  assert.equal(memory.forget({ id: "mem-1", ownerId: "owner-a" }), true);
  assert.equal(memory.forget({ id: "mem-1", ownerId: "owner-a" }), false);
  assert.equal(store.snapshot.items.length, 0);
});

test("memory runtime rolls back RAM state when a synchronous store rejects a snapshot", () => {
  const initial = validateMemorySnapshot({
    $schema: MEMORY_SNAPSHOT_SCHEMA,
    items: [memoryItem({ id: "existing", content: "durável" })],
  });
  const memory = createMemoryRuntime({
    store: memoryStore({ initial, saveResult: false }),
  });

  assert.throws(
    () => memory.remember(memoryItem({ id: "new", content: "não persistiu" })),
    /rejected the snapshot/,
  );
  assert.deepEqual(
    memory.search({ ownerId: "owner-a", scopes: ["account"] }).map((item) => item.id),
    ["existing"],
  );
  assert.throws(
    () => memory.forget({ id: "existing", ownerId: "owner-a" }),
    /rejected the snapshot/,
  );
  assert.equal(
    memory.search({ ownerId: "owner-a", scopes: ["account"] })[0].content,
    "durável",
  );
});

test("memory runtime flush forwards durable confirmation and failure", async () => {
  const good = createMemoryRuntime({ store: memoryStore() });
  good.remember(memoryItem({ id: "good" }));
  assert.equal(await good.flush(), true);

  const bad = createMemoryRuntime({
    store: memoryStore({ flushError: new Error("disk unavailable") }),
  });
  await assert.rejects(() => bad.flush(), /disk unavailable/);
});

test("device-owned memory works without an account but cannot request account scope", () => {
  const memory = createMemoryRuntime();
  memory.remember(memoryItem({
    id: "offline-device",
    ownerKind: "device",
    ownerId: null,
    scope: "device",
    content: "Preferência local sem conta",
  }));

  const results = memory.search({
    ownerKind: "device",
    scopes: ["device"],
  });
  assert.equal(results.length, 1);
  assert.equal(results[0].ownerKind, "device");
  assert.equal(results[0].ownerId, null);
  assert.equal(results[0].id, "offline-device");

  assert.throws(
    () => memory.search({ ownerKind: "device", scopes: ["account"] }),
    /cannot request account scope/,
  );
  assert.throws(
    () => memory.remember(memoryItem({
      id: "invalid-account",
      ownerKind: "device",
      ownerId: null,
      scope: "account",
    })),
    /Account memory requires an account owner/,
  );
});

test("owner kind and owner id are part of memory identity for update and delete", () => {
  const memory = createMemoryRuntime();
  memory.remember(memoryItem({ id: "shared-id", content: "account value" }));
  memory.remember(memoryItem({
    id: "shared-id",
    ownerKind: "device",
    ownerId: null,
    scope: "device",
    content: "device value",
  }));

  assert.equal(
    memory.search({ ownerId: "owner-a", scopes: ["account"] })[0].content,
    "account value",
  );
  assert.equal(
    memory.search({ ownerKind: "device", scopes: ["device"] })[0].content,
    "device value",
  );

  memory.remember(memoryItem({
    id: "shared-id",
    ownerKind: "device",
    ownerId: null,
    scope: "device",
    content: "device edited",
    sourceTimestamp: "2026-09-24T16:00:00Z",
  }));
  assert.equal(
    memory.search({ ownerKind: "device", scopes: ["device"] })[0].content,
    "device edited",
  );
  assert.equal(
    memory.search({ ownerId: "owner-a", scopes: ["account"] })[0].content,
    "account value",
  );

  assert.equal(
    memory.forget({ id: "shared-id", ownerKind: "device", ownerId: null }),
    true,
  );
  assert.deepEqual(memory.search({ ownerKind: "device", scopes: ["device"] }), []);
  assert.equal(
    memory.search({ ownerId: "owner-a", scopes: ["account"] })[0].content,
    "account value",
  );
});

test("memory search applies owner and structural scope filters before ranking", () => {
  const memory = createMemoryRuntime();
  memory.remember(memoryItem({
    id: "project-a",
    scope: "project",
    spaceId: "space-a",
    projectId: "project-a",
    content: "Arquitetura Alpha do projeto",
  }));
  memory.remember(memoryItem({
    id: "project-b",
    scope: "project",
    spaceId: "space-b",
    projectId: "project-b",
    content: "Arquitetura Alpha de outro espaço",
  }));
  memory.remember(memoryItem({
    id: "other-owner",
    ownerId: "owner-b",
    scope: "project",
    spaceId: "space-a",
    projectId: "project-a",
    content: "Arquitetura Alpha privada de outro owner",
  }));

  const results = memory.search({
    ownerId: "owner-a",
    query: "arquitetura alpha",
    scopes: ["project"],
    spaceId: "space-a",
    projectId: "project-a",
  });
  assert.deepEqual(results.map((item) => item.id), ["project-a"]);

  const missingSpaceGrant = memory.search({
    ownerId: "owner-a",
    query: "alpha",
    scopes: ["project"],
    projectId: "project-a",
  });
  assert.deepEqual(missingSpaceGrant, []);
});

test("restricted memory requires explicit inclusion and lexical search is accent-insensitive", () => {
  const memory = createMemoryRuntime();
  memory.remember(memoryItem({
    id: "normal",
    content: "Preferência de atualização local",
  }));
  memory.remember(memoryItem({
    id: "restricted",
    sensitivity: "restricted",
    content: "Preferência restrita de atualização local",
    sourceTimestamp: "2026-09-24T16:00:00Z",
  }));

  const defaultResults = memory.search({
    ownerId: "owner-a",
    query: "preferencia atualizacao",
    scopes: ["account"],
  });
  assert.deepEqual(defaultResults.map((item) => item.id), ["normal"]);

  const privilegedResults = memory.search({
    ownerId: "owner-a",
    query: "preferencia atualizacao",
    scopes: ["account"],
    includeRestricted: true,
  });
  assert.deepEqual(privilegedResults.map((item) => item.id), ["restricted", "normal"]);
});

test("memory search pagination remains bounded and deterministic", () => {
  const memory = createMemoryRuntime();
  for (let index = 0; index < 40; index += 1) {
    memory.remember(memoryItem({
      id: `page-${String(index).padStart(2, "0")}`,
      content: `item ${index}`,
      sourceTimestamp: `2026-09-24T15:${String(index).padStart(2, "0")}:00Z`,
    }));
  }

  const first = memory.search({
    ownerId: "owner-a",
    scopes: ["account"],
    limit: 32,
    offset: 0,
  });
  const second = memory.search({
    ownerId: "owner-a",
    scopes: ["account"],
    limit: 32,
    offset: 32,
  });
  assert.equal(first.length, 32);
  assert.equal(second.length, 8);
  assert.equal(first[0].id, "page-39");
  assert.equal(second[0].id, "page-07");
  assert.throws(
    () => memory.search({ ownerId: "owner-a", scopes: ["account"], offset: 2049 }),
    /offset/,
  );
});

test("device persistence never carries session-scoped memory across runtime recreation", () => {
  const store = memoryStore();
  const memory = createMemoryRuntime({ store });
  memory.remember(memoryItem({
    id: "session-1",
    scope: "session",
    content: "contexto efêmero",
  }));
  memory.remember(memoryItem({
    id: "device-1",
    scope: "device",
    content: "preferência durável",
  }));

  assert.deepEqual(store.snapshot.items.map((item) => item.id), ["device-1"]);
  assert.deepEqual(
    memory.search({ ownerId: "owner-a", scopes: ["session"] }).map((item) => item.id),
    ["session-1"],
  );

  const recreated = createMemoryRuntime({ store });
  assert.deepEqual(recreated.search({ ownerId: "owner-a", scopes: ["session"] }), []);
  assert.deepEqual(
    recreated.search({ ownerId: "owner-a", scopes: ["device"] }).map((item) => item.id),
    ["device-1"],
  );
});

test("device store fails closed if session memory was persisted by an incompatible implementation", () => {
  const initial = validateMemorySnapshot({
    $schema: MEMORY_SNAPSHOT_SCHEMA,
    items: [memoryItem({ id: "bad-session", scope: "session" })],
  });
  assert.throws(
    () => createMemoryRuntime({ store: memoryStore({ initial }) }),
    /must not persist session-scoped memory/,
  );
});

test("memory snapshot allows the same id for distinct owners but rejects duplicate owner/id identity", () => {
  const distinctOwners = validateMemorySnapshot({
    $schema: MEMORY_SNAPSHOT_SCHEMA,
    items: [
      memoryItem({ id: "duplicate" }),
      memoryItem({ id: "duplicate", ownerId: "owner-b" }),
      memoryItem({
        id: "duplicate",
        ownerKind: "device",
        ownerId: null,
        scope: "device",
      }),
    ],
  });
  assert.equal(distinctOwners.items.length, 3);

  assert.throws(
    () => validateMemorySnapshot({
      $schema: MEMORY_SNAPSHOT_SCHEMA,
      items: [
        memoryItem({ id: "duplicate", ownerId: "owner-a" }),
        memoryItem({ id: "duplicate", ownerId: "owner-a", content: "second" }),
      ],
    }),
    /owner\/id identities must be unique/,
  );
});
