import assert from "node:assert/strict";
import test from "node:test";

import { validateIntelligenceRequest } from "../system/contracts/intelligence.mjs";
import { MEMORY_PORT_SCHEMA } from "../system/contracts/memory.mjs";
import { validateMemoryContextAuthorization } from "../system/contracts/memory-context.mjs";
import { createMemoryRuntime } from "../system/services/memory/runtime.mjs";
import {
  retrieveAuthorizedMemoryContext,
  retrieveAuthorizedMemoryContextSet,
} from "../system/services/memory/context.mjs";

function item(overrides = {}) {
  return {
    id: "mem-1",
    ownerId: "user-1",
    scope: "project",
    kind: "fact",
    sensitivity: "private",
    content: "A release v4 inclui a IA local.",
    provenance: "project decision",
    sourceTimestamp: "2026-09-24T12:00:00Z",
    projectId: "ordax",
    spaceId: "space-a",
    ...overrides,
  };
}

const auth = (overrides = {}) => ({
  authority: "composition",
  ownerId: "user-1",
  scopes: ["project"],
  spaceId: "space-a",
  projectId: "ordax",
  ...overrides,
});

function staticMemoryPort(search) {
  return Object.freeze({
    schema: MEMORY_PORT_SCHEMA,
    search,
    remember() {},
    forget() {},
    async flush() { return true; },
  });
}

test("memory context authorization requires composition authority and exact scope identifiers", () => {
  assert.throws(
    () => validateMemoryContextAuthorization({ ...auth(), authority: "client" }),
    /composition/,
  );
  assert.throws(
    () => validateMemoryContextAuthorization({ ...auth(), projectId: null }),
    /project id/,
  );
  assert.throws(
    () => validateMemoryContextAuthorization({
      authority: "composition",
      ownerId: "user-1",
      scopes: ["space"],
    }),
    /space id/,
  );
});

test("device-owned memory context works without account identity and excludes account scope", () => {
  const memory = createMemoryRuntime();
  memory.remember(item({
    id: "device-memory",
    ownerKind: "device",
    ownerId: null,
    scope: "device",
    projectId: null,
    spaceId: null,
    content: "Contexto local do dispositivo.",
  }));

  const deviceAuth = {
    authority: "composition",
    ownerKind: "device",
    ownerId: null,
    scopes: ["device"],
  };
  const context = retrieveAuthorizedMemoryContext(memory, deviceAuth);
  assert.equal(context.length, 1);
  assert.equal(context[0].id, "device-memory");
  assert.equal(context[0].scope, "user");
  assert.equal(context[0].text, "Contexto local do dispositivo.");
  assert.equal(context[0].provenance, "memory:device:project decision");

  assert.throws(
    () => validateMemoryContextAuthorization({
      authority: "composition",
      ownerKind: "device",
      ownerId: null,
      scopes: ["account"],
    }),
    /cannot authorize account scope/,
  );
});

test("authorized memory becomes bounded provenance-bearing Intelligence context", () => {
  const memory = createMemoryRuntime();
  memory.remember(item());
  const context = retrieveAuthorizedMemoryContext(memory, auth(), {
    query: "release",
    limit: 4,
  });
  assert.equal(context.length, 1);
  assert.equal(context[0].id, "mem-1");
  assert.equal(context[0].scope, "workspace");
  assert.equal(context[0].text, "A release v4 inclui a IA local.");
  assert.equal(context[0].provenance, "memory:account:project decision");
});

test("maximum-size canonical memory id remains valid Intelligence context", () => {
  const memory = createMemoryRuntime();
  const maximumId = "m".repeat(160);
  memory.remember(item({ id: maximumId }));
  const [context] = retrieveAuthorizedMemoryContext(memory, auth());
  assert.equal(context.id, maximumId);
  assert.equal(context.id.length, 160);
  const request = validateIntelligenceRequest({
    prompt: "Use o contexto autorizado.",
    context: [context],
  });
  assert.equal(request.context[0].id, maximumId);
});

test("explicit device and account authorizations share one bounded context budget fairly", () => {
  const memory = createMemoryRuntime();
  for (let index = 0; index < 5; index += 1) {
    memory.remember(item({
      id: `device-${index}`,
      ownerKind: "device",
      ownerId: null,
      scope: "device",
      projectId: null,
      spaceId: null,
      content: `device ${index}`,
      sourceTimestamp: `2026-09-24T13:0${index}:00Z`,
    }));
    memory.remember(item({
      id: `account-${index}`,
      scope: "account",
      projectId: null,
      spaceId: null,
      content: `account ${index}`,
      sourceTimestamp: `2026-09-24T14:0${index}:00Z`,
    }));
  }

  const context = retrieveAuthorizedMemoryContextSet(memory, [
    {
      authority: "composition",
      ownerKind: "device",
      ownerId: null,
      scopes: ["device"],
    },
    {
      authority: "composition",
      ownerKind: "account",
      ownerId: "user-1",
      scopes: ["account"],
    },
  ], { limit: 6 });

  assert.equal(context.length, 6);
  assert.deepEqual(context.map((entry) => entry.id), [
    "device-4",
    "account-4",
    "device-3",
    "account-3",
    "device-2",
    "account-2",
  ]);
});

test("same memory id from different owners survives real runtime merge with owner-aware provenance", () => {
  const memory = createMemoryRuntime();
  memory.remember(item({
    id: "same",
    ownerKind: "device",
    ownerId: null,
    scope: "device",
    projectId: null,
    spaceId: null,
    content: "device value",
    provenance: "local-device",
  }));
  memory.remember(item({
    id: "same",
    ownerKind: "account",
    ownerId: "user-1",
    scope: "account",
    projectId: null,
    spaceId: null,
    content: "account value",
    provenance: "account-memory",
  }));

  const context = retrieveAuthorizedMemoryContextSet(memory, [
    {
      authority: "composition",
      ownerKind: "device",
      ownerId: null,
      scopes: ["device"],
    },
    {
      authority: "composition",
      ownerKind: "account",
      ownerId: "user-1",
      scopes: ["account"],
    },
  ], { limit: 4 });

  assert.deepEqual(context.map((entry) => entry.id), ["same", "same"]);
  assert.deepEqual(context.map((entry) => entry.text), ["device value", "account value"]);
  assert.deepEqual(context.map((entry) => entry.provenance), [
    "memory:device:local-device",
    "memory:account:account-memory",
  ]);
  assert.equal(context.some((entry) => entry.provenance.includes("user-1")), false);
  const request = validateIntelligenceRequest({
    prompt: "Use ambos os owners autorizados.",
    context,
  });
  assert.equal(request.context.length, 2);
});

test("multi-authorization context set is itself bounded and deduplicates repeated grants", () => {
  const memory = createMemoryRuntime();
  memory.remember(item({ id: "same" }));
  const repeated = auth();
  const context = retrieveAuthorizedMemoryContextSet(memory, [repeated, repeated], { limit: 8 });
  assert.deepEqual(context.map((entry) => entry.id), ["same"]);
  assert.throws(
    () => retrieveAuthorizedMemoryContextSet(memory, []),
    /authorization set/,
  );
  assert.throws(
    () => retrieveAuthorizedMemoryContextSet(memory, [auth(), auth(), auth(), auth(), auth()]),
    /authorization set/,
  );
});

test("restricted memory requires explicit retrieval authorization", () => {
  const memory = createMemoryRuntime();
  memory.remember(item({ id: "private", sensitivity: "restricted" }));
  assert.deepEqual(retrieveAuthorizedMemoryContext(memory, auth()), []);
  const allowed = retrieveAuthorizedMemoryContext(memory, auth({ includeRestricted: true }));
  assert.equal(allowed.length, 1);
  assert.equal(allowed[0].id, "private");
});

test("context builder independently rejects cross-principal and cross-Space results", () => {
  const badPort = staticMemoryPort(() => [item({ ownerId: "user-2", id: "leak" })]);
  assert.throws(
    () => retrieveAuthorizedMemoryContext(badPort, auth()),
    /another principal/,
  );

  const wrongOwnerKind = staticMemoryPort(() => [item({
    id: "leak-kind",
    ownerKind: "device",
    ownerId: null,
    scope: "device",
    projectId: null,
    spaceId: null,
  })]);
  assert.throws(
    () => retrieveAuthorizedMemoryContext(wrongOwnerKind, auth({ scopes: ["device"], spaceId: null, projectId: null })),
    /another principal/,
  );

  const crossSpace = staticMemoryPort(() => [item({ id: "leak-space", spaceId: "space-b" })]);
  assert.throws(
    () => retrieveAuthorizedMemoryContext(crossSpace, auth()),
    /another Space/,
  );
});

test("memory context is capped and long content is excerpted before Intelligence", () => {
  const memory = createMemoryRuntime();
  for (let index = 0; index < 12; index += 1) {
    memory.remember(item({
      id: `mem-${index}`,
      content: index === 11 ? "x".repeat(12000) : `context ${index}`,
      sourceTimestamp: `2026-09-24T12:${String(index).padStart(2, "0")}:00Z`,
    }));
  }
  const context = retrieveAuthorizedMemoryContext(memory, auth(), { limit: 99 });
  assert.equal(context.length, 8);
  assert.ok(context.every((entry) => entry.text.length <= 8192));
  const excerpted = context.find((entry) => entry.id === "mem-11");
  assert.ok(excerpted);
  assert.equal(excerpted.text.length, 8192);
  assert.ok(excerpted.text.endsWith("…"));
});
