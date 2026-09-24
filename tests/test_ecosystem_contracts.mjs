import test from "node:test";
import assert from "node:assert/strict";

import { validateEntitlementDecision } from "../system/contracts/entitlements.mjs";
import { validateLocalAiSnapshot } from "../system/contracts/local-ai.mjs";
import { validateMemoryItem } from "../system/contracts/memory.mjs";
import { validateModelRoute } from "../system/contracts/model-router.mjs";
import { validateProfilePack, validateSpace } from "../system/contracts/spaces.mjs";

test("entitlements reject client authority", () => {
  assert.throws(() => validateEntitlementDecision({
    subjectType: "account",
    subjectId: "user-1",
    key: "memory.cloud.enabled",
    decision: "allowed",
    authority: "client",
  }));
});

test("spaces keep professional pack separate from account identity", () => {
  const space = validateSpace({
    id: "space-1",
    name: "Advocacia",
    kind: "professional",
    ownerId: "user-1",
    profilePack: "legal-br",
  });
  assert.equal(space.kind, "professional");
  assert.equal(space.profilePack, "legal-br");
});

test("profile packs cannot grant privilege or bypass package trust", () => {
  assert.throws(() => validateProfilePack({
    slug: "legal-br",
    version: 1,
    title: "Advocacia",
    category: "legal",
    autoGrantPrivileges: true,
  }));
});

test("memory is provider-neutral and requires provenance plus source timestamp", () => {
  const memory = validateMemoryItem({
    id: "mem-1",
    ownerId: "user-1",
    scope: "project",
    kind: "fact",
    sensitivity: "private",
    content: "MVP runs from USB.",
    provenance: "project decision",
    sourceTimestamp: "2026-09-24T12:00:00-03:00",
    projectId: "prototipo-ordax-os",
  });
  assert.equal(memory.schema, "ordax.memory/1");
  assert.equal(memory.projectId, "prototipo-ordax-os");
  assert.equal(memory.sourceTimestamp, "2026-09-24T15:00:00.000Z");
});

test("memory rejects secrets in content or provenance", () => {
  assert.throws(() => validateMemoryItem({
    id: "mem-2",
    ownerId: "user-1",
    scope: "account",
    kind: "fact",
    content: "token",
    provenance: "test",
    secret: true,
  }));
  assert.throws(() => validateMemoryItem({
    id: "mem-3",
    ownerId: "user-1",
    scope: "device",
    kind: "fact",
    content: "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----",
    provenance: "test",
    sourceTimestamp: "2026-09-24T15:00:00Z",
  }));
  assert.throws(() => validateMemoryItem({
    id: "mem-4",
    ownerId: "user-1",
    scope: "device",
    kind: "fact",
    content: "normal content",
    provenance: "imported from ghp_abcdefghijklmnopqrstuvwxyz123456",
    sourceTimestamp: "2026-09-24T15:00:00Z",
  }), /Secrets are not valid/);
});

test("available Local AI states require complete engine and model identity", () => {
  for (const state of ["ready", "busy"]) {
    assert.throws(
      () => validateLocalAiSnapshot({
        state,
        engineId: null,
        modelId: "local-model",
        offline: true,
        migratable: true,
      }),
      /engine and model identity/,
    );
    assert.throws(
      () => validateLocalAiSnapshot({
        state,
        engineId: "llama.cpp",
        modelId: null,
        offline: true,
        migratable: true,
      }),
      /engine and model identity/,
    );
  }

  const busy = validateLocalAiSnapshot({
    state: "busy",
    engineId: "llama.cpp",
    modelId: "local-model",
    offline: true,
    migratable: true,
  });
  assert.equal(busy.state, "busy");
  assert.equal(busy.engineId, "llama.cpp");
  assert.equal(busy.modelId, "local-model");
});

test("external model route requires explicit egress approval", () => {
  assert.throws(() => validateModelRoute({
    provider: "openai",
    modelId: "future-model",
    purpose: "general",
    egressApproved: false,
  }));
  const local = validateModelRoute({
    provider: "local",
    engineId: "llama.cpp",
    modelId: "local-model",
    purpose: "general",
  });
  assert.equal(local.engineId, "llama.cpp");
  assert.equal(local.memoryOwner, "ordax");
  assert.equal(local.egressApproved, false);
});
