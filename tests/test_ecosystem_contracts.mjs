import test from "node:test";
import assert from "node:assert/strict";

import { validateEntitlementDecision } from "../system/contracts/entitlements.mjs";
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

test("memory is provider-neutral and requires provenance", () => {
  const memory = validateMemoryItem({
    id: "mem-1",
    ownerId: "user-1",
    scope: "project",
    kind: "fact",
    sensitivity: "private",
    content: "MVP runs from USB.",
    provenance: "project decision",
    projectId: "prototipo-ordax-os",
  });
  assert.equal(memory.schema, "ordax.memory/1");
  assert.equal(memory.projectId, "prototipo-ordax-os");
});

test("memory rejects secrets", () => {
  assert.throws(() => validateMemoryItem({
    id: "mem-2",
    ownerId: "user-1",
    scope: "account",
    kind: "fact",
    content: "token",
    provenance: "test",
    secret: true,
  }));
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
    modelId: "local-model",
    purpose: "general",
  });
  assert.equal(local.memoryOwner, "ordax");
  assert.equal(local.egressApproved, false);
});
