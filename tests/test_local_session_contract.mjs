import assert from "node:assert/strict";
import test from "node:test";

import {
  LOCAL_SESSION_SCHEMA,
  assertLocalSessionPort,
  validateLocalSessionSecret,
  validateLocalSessionSnapshot,
} from "../system/contracts/local-session.mjs";

test("local session snapshot states are explicit and do not claim storage encryption", () => {
  assert.deepEqual(
    validateLocalSessionSnapshot({
      state: "unlocked",
      credentialConfigured: false,
      protectionScope: "surface-session-not-storage-encryption",
    }),
    {
      schema: LOCAL_SESSION_SCHEMA,
      state: "unlocked",
      credentialConfigured: false,
      canLock: false,
      protectionScope: "surface-session-not-storage-encryption",
    },
  );
  assert.throws(
    () => validateLocalSessionSnapshot({
      state: "locked",
      credentialConfigured: false,
      protectionScope: "surface-session-not-storage-encryption",
    }),
    /cannot be locked/,
  );
});

test("local session secret validation is bounded", () => {
  assert.equal(validateLocalSessionSecret("123456"), "123456");
  assert.equal(validateLocalSessionSecret("uma senha local longa"), "uma senha local longa");
  assert.throws(() => validateLocalSessionSecret("12345"), /between 6 and 128/);
  assert.throws(() => validateLocalSessionSecret("      "), /whitespace/);
});

test("local session port is independent and complete", () => {
  const snapshot = Object.freeze({
    state: "unlocked",
    credentialConfigured: true,
    protectionScope: "surface-session-not-storage-encryption",
  });
  const port = {
    schema: LOCAL_SESSION_SCHEMA,
    getSnapshot: () => snapshot,
    subscribe: () => () => {},
    configureCredential: async () => snapshot,
    removeCredential: async () => snapshot,
    lock: async () => snapshot,
    unlock: async () => snapshot,
  };
  assert.equal(assertLocalSessionPort(port), port);
});
