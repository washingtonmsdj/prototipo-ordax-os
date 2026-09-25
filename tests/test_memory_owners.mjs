import assert from "node:assert/strict";
import test from "node:test";

import { IDENTITY_SESSION_SCHEMA } from "../system/contracts/identity-session.mjs";
import {
  validateMemoryOwner,
  validateMemorySearchRequest,
} from "../system/contracts/memory.mjs";
import {
  DEVICE_MEMORY_OWNER,
  memoryOwnersForIdentityPort,
  memoryOwnersForIdentitySession,
} from "../system/services/memory/owners.mjs";

const session = (overrides = {}) => ({
  state: "signed-out",
  subjectId: null,
  displayName: null,
  ...overrides,
});

test("device memory owner is always available without identity", () => {
  assert.deepEqual(memoryOwnersForIdentitySession(), [
    { ownerKind: "device", ownerId: null },
  ]);
  assert.equal(DEVICE_MEMORY_OWNER.ownerKind, "device");
  assert.equal(DEVICE_MEMORY_OWNER.ownerId, null);
});

test("legacy owner inference never turns an empty account id into device ownership", () => {
  assert.deepEqual(validateMemoryOwner({ ownerId: null }), {
    ownerKind: "device",
    ownerId: null,
  });
  assert.deepEqual(validateMemoryOwner({ ownerId: "account-1" }), {
    ownerKind: "account",
    ownerId: "account-1",
  });
  assert.throws(
    () => validateMemoryOwner({ ownerId: "" }),
    /must not be empty/,
  );
});

test("memory search query is text-only and never coerces arbitrary values", () => {
  const empty = validateMemorySearchRequest({
    ownerId: "account-1",
    scopes: ["account"],
    query: null,
  });
  assert.equal(empty.query, "");

  assert.throws(
    () => validateMemorySearchRequest({
      ownerId: "account-1",
      scopes: ["account"],
      query: 42,
    }),
    /must be text/,
  );

  let coerced = false;
  const dangerous = {
    toString() {
      coerced = true;
      return "must-not-run";
    },
  };
  assert.throws(
    () => validateMemorySearchRequest({
      ownerId: "account-1",
      scopes: ["account"],
      query: dangerous,
    }),
    /must be text/,
  );
  assert.equal(coerced, false);
});

test("signed-out and unavailable identity keep only device-owned memory", () => {
  assert.deepEqual(memoryOwnersForIdentitySession(session()), [
    { ownerKind: "device", ownerId: null },
  ]);
  assert.deepEqual(memoryOwnersForIdentitySession(session({ state: "unavailable" })), [
    { ownerKind: "device", ownerId: null },
  ]);
});

test("signed-in identity adds account owner without replacing device owner", () => {
  const owners = memoryOwnersForIdentitySession(session({
    state: "signed-in",
    subjectId: "account-42",
    displayName: "Pessoa",
  }));
  assert.deepEqual(owners, [
    { ownerKind: "device", ownerId: null },
    { ownerKind: "account", ownerId: "account-42" },
  ]);
});

test("owner resolver can read the stable identity-session port", () => {
  const port = {
    schema: IDENTITY_SESSION_SCHEMA,
    getSnapshot() {
      return session({
        state: "signed-in",
        subjectId: "account-7",
        displayName: "Conta",
      });
    },
  };
  assert.deepEqual(memoryOwnersForIdentityPort(port), [
    { ownerKind: "device", ownerId: null },
    { ownerKind: "account", ownerId: "account-7" },
  ]);
});

test("invalid signed-in identity fails closed instead of fabricating an owner", () => {
  assert.throws(
    () => memoryOwnersForIdentitySession(session({
      state: "signed-in",
      subjectId: "",
      displayName: "Conta",
    })),
    /subjectId/,
  );
  assert.throws(
    () => memoryOwnersForIdentityPort({ schema: "wrong", getSnapshot() {} }),
    /identity-session/,
  );
});
