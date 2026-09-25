import test from "node:test";
import assert from "node:assert/strict";

import {
  IDENTITY_SESSION_SCHEMA,
  assertIdentitySessionPort,
  validateIdentitySessionSnapshot,
} from "../system/contracts/identity-session.mjs";
import { createWebIdentitySession } from "../system/adapters/web/identity.mjs";

test("identity session validates unavailable, signed-out and signed-in states", () => {
  assert.deepEqual(validateIdentitySessionSnapshot({ state: "unavailable" }), {
    state: "unavailable",
    subjectId: null,
    displayName: null,
  });
  assert.deepEqual(validateIdentitySessionSnapshot({ state: "signed-out" }), {
    state: "signed-out",
    subjectId: null,
    displayName: null,
  });
  assert.deepEqual(
    validateIdentitySessionSnapshot({
      state: "signed-in",
      subjectId: "user-1",
      displayName: "Pessoa",
    }),
    { state: "signed-in", subjectId: "user-1", displayName: "Pessoa" },
  );
});

test("signed-in state fails closed without public identity fields", () => {
  assert.throws(
    () => validateIdentitySessionSnapshot({ state: "signed-in", displayName: "Pessoa" }),
    TypeError,
  );
  assert.throws(
    () => validateIdentitySessionSnapshot({ state: "signed-in", subjectId: "user-1" }),
    TypeError,
  );
});

test("web identity adapter reports signed-out when the real gateway is configured", async () => {
  const windowRef = {
    fetch: async () => ({
      ok: true,
      json: async () => ({
        $schema: "prototype-ordax.public-identity-session/1",
        authenticated: false,
        provider: "supabase",
        status: "anonymous",
      }),
    }),
  };
  const port = createWebIdentitySession(windowRef);
  assert.equal(port.schema, IDENTITY_SESSION_SCHEMA);
  assertIdentitySessionPort(port);
  await port.refresh();
  assert.deepEqual(port.getSnapshot(), {
    state: "signed-out",
    subjectId: null,
    displayName: null,
  });
  port.dispose();
});

test("web identity adapter reports a validated signed-in account", async () => {
  const windowRef = {
    fetch: async () => ({
      ok: true,
      json: async () => ({
        $schema: "prototype-ordax.public-identity-session/1",
        authenticated: true,
        provider: "supabase",
        status: "authenticated",
        subject: "user-123",
        email: "pessoa@example.com",
      }),
    }),
  };
  const port = createWebIdentitySession(windowRef);
  await port.refresh();
  assert.deepEqual(port.getSnapshot(), {
    state: "signed-in",
    subjectId: "user-123",
    displayName: "pessoa",
  });
  port.dispose();
});

test("identity gateway failure remains explicitly unavailable", async () => {
  const port = createWebIdentitySession({
    fetch: async () => {
      throw new Error("offline");
    },
  });
  await port.refresh();
  assert.equal(port.getSnapshot().state, "unavailable");
  port.dispose();
});
