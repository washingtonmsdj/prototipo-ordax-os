import assert from "node:assert/strict";
import test from "node:test";
import {
  generateKeyPairSync,
  sign,
} from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { getFirstPartyApp } from "../system/apps/catalog.mjs";
import {
  EXTERNAL_APP_ENVELOPE_SCHEMA,
  EXTERNAL_APP_SIGNATURE_ALGORITHM,
  EXTERNAL_APP_TEST_TRUST_SCHEMA,
  canonicalExternalAppManifestBytes,
  validateExternalAppManifest,
  verifyExternalAppProof,
} from "../tools/app-package-proof/verify.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const FIXTURE = resolve(ROOT, "tests/fixtures/external-app/external-hello");
const manifest = JSON.parse(await readFile(resolve(FIXTURE, "manifest.json"), "utf8"));
const contentBytes = await readFile(resolve(FIXTURE, "index.mjs"));

function signedProof(manifestValue = manifest) {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const keyId = "external-proof-test";
  const payload = canonicalExternalAppManifestBytes(manifestValue);
  const signature = sign(null, payload, privateKey);
  return {
    trust: {
      $schema: EXTERNAL_APP_TEST_TRUST_SCHEMA,
      algorithm: EXTERNAL_APP_SIGNATURE_ALGORITHM,
      key_id: keyId,
      public_key_pem: publicKey.export({ type: "spki", format: "pem" }),
    },
    envelope: {
      $schema: EXTERNAL_APP_ENVELOPE_SCHEMA,
      algorithm: EXTERNAL_APP_SIGNATURE_ALGORITHM,
      key_id: keyId,
      signature_base64: signature.toString("base64"),
    },
  };
}

test("signed external app proof validates exact non-privileged bytes", () => {
  const { trust, envelope } = signedProof();
  const verified = verifyExternalAppProof({ manifest, envelope, trust, contentBytes });

  assert.equal(verified.app_id, "external-hello");
  assert.equal(verified.version, "0.1.0");
  assert.deepEqual(verified.requested_capabilities, []);
  assert.deepEqual(verified.supported_modes, ["web"]);
  assert.equal(verified.update_policy, "manual-test-only");
});

test("external proof app never becomes first-party catalog content", () => {
  assert.equal(getFirstPartyApp("external-hello"), null);
});

test("payload tampering fails content binding before execution", () => {
  const { trust, envelope } = signedProof();
  const tampered = Buffer.concat([contentBytes, Buffer.from("// tampered\n")]);
  assert.throws(
    () => verifyExternalAppProof({ manifest, envelope, trust, contentBytes: tampered }),
    /content hash mismatch/,
  );
});

test("signature from a different Ed25519 key fails closed", () => {
  const { envelope } = signedProof();
  const { publicKey } = generateKeyPairSync("ed25519");
  const wrongTrust = {
    $schema: EXTERNAL_APP_TEST_TRUST_SCHEMA,
    algorithm: EXTERNAL_APP_SIGNATURE_ALGORITHM,
    key_id: envelope.key_id,
    public_key_pem: publicKey.export({ type: "spki", format: "pem" }),
  };
  assert.throws(
    () => verifyExternalAppProof({ manifest, envelope, trust: wrongTrust, contentBytes }),
    /signature verification failed/,
  );
});

test("proof rejects requested capabilities and path traversal", () => {
  const privileged = structuredClone(manifest);
  privileged.requested_capabilities = ["filesystem.user-space"];
  assert.throws(
    () => validateExternalAppManifest(privileged),
    /must not request capabilities/,
  );

  const traversal = structuredClone(manifest);
  traversal.entrypoint = "../index.mjs";
  assert.throws(
    () => validateExternalAppManifest(traversal),
    /safe relative POSIX path/,
  );
});

test("manifest and envelope reject unknown fields", () => {
  const unknownManifest = { ...manifest, surprise: true };
  assert.throws(
    () => validateExternalAppManifest(unknownManifest),
    /fields are incompatible/,
  );

  const { trust, envelope } = signedProof();
  assert.throws(
    () => verifyExternalAppProof({
      manifest,
      envelope: { ...envelope, surprise: true },
      trust,
      contentBytes,
    }),
    /fields are incompatible/,
  );
});
