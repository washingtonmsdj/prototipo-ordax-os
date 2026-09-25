import test from "node:test";
import assert from "node:assert/strict";

import {
  IDENTITY_CREDENTIALS_SCHEMA,
  assertIdentityCredentialsPort,
  validateIdentityCredentialInput,
} from "../system/contracts/identity-credentials.mjs";
import { createSameOriginIdentityCredentials } from "../system/adapters/web/identity-credentials.mjs";

test("identity credentials validate transient email/password input", () => {
  assert.deepEqual(
    validateIdentityCredentialInput({
      email: " pessoa@example.com ",
      password: "segredo-local",
    }),
    { email: "pessoa@example.com", password: "segredo-local" },
  );
  assert.throws(
    () => validateIdentityCredentialInput({ email: "invalid", password: "x" }),
    TypeError,
  );
});

test("same-origin credential adapter posts only to OrdaX auth routes", async () => {
  const calls = [];
  const windowRef = {
    fetch: async (path, options) => {
      calls.push({ path, options });
      return { ok: true, status: 303 };
    },
  };
  const port = createSameOriginIdentityCredentials(windowRef);
  assert.equal(port.schema, IDENTITY_CREDENTIALS_SCHEMA);
  assertIdentityCredentialsPort(port);

  await port.signIn({ email: "pessoa@example.com", password: "secret-1" });
  await port.register({ email: "nova@example.com", password: "secret-2" });

  assert.deepEqual(calls.map((call) => call.path), ["/auth/login", "/auth/register"]);
  assert.equal(calls.every((call) => call.options.credentials === "same-origin"), true);
  assert.equal(calls.every((call) => call.options.redirect === "manual"), true);
  assert.equal(calls[0].options.body.includes("pessoa%40example.com"), true);
  assert.equal(calls[0].options.body.includes("secret-1"), true);
});

test("registration confirmation is explicit and does not claim a session", async () => {
  const port = createSameOriginIdentityCredentials({
    fetch: async () => ({ ok: true, status: 202 }),
  });
  assert.deepEqual(
    await port.register({ email: "nova@example.com", password: "secret" }),
    { authenticated: false, confirmationRequired: true },
  );
});
