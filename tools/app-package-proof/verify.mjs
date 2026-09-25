import {
  createHash,
  createPublicKey,
  verify as verifySignature,
} from "node:crypto";

export const EXTERNAL_APP_MANIFEST_SCHEMA = "prototype-ordax.external-app-manifest/1";
export const EXTERNAL_APP_ENVELOPE_SCHEMA = "prototype-ordax.external-app-envelope/1";
export const EXTERNAL_APP_TEST_TRUST_SCHEMA = "prototype-ordax.external-app-test-trust/1";
export const EXTERNAL_APP_SIGNATURE_ALGORITHM = "ed25519";

const APP_ID_PATTERN = /^[a-z][a-z0-9-]{1,79}$/;
const VERSION_PATTERN = /^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$/;
const KEY_ID_PATTERN = /^[a-z0-9][a-z0-9._-]{0,63}$/;
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const CONTRACT_PATTERN = /^[a-z0-9][a-z0-9.-]{0,95}\/[0-9]+$/;
const MAX_CONTENT_BYTES = 4 * 1024 * 1024;
const SUPPORTED_MODES = new Set(["web"]);
const MANIFEST_KEYS = Object.freeze([
  "$schema",
  "app_id",
  "version",
  "publisher",
  "entrypoint",
  "supported_modes",
  "required_contracts",
  "requested_capabilities",
  "content_hash",
  "update_policy",
]);
const ENVELOPE_KEYS = Object.freeze([
  "$schema",
  "algorithm",
  "key_id",
  "signature_base64",
]);
const TRUST_KEYS = Object.freeze([
  "$schema",
  "algorithm",
  "key_id",
  "public_key_pem",
]);

function objectValue(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
  return value;
}

function exactKeys(value, allowed, label) {
  const keys = Object.keys(value).sort();
  const expected = [...allowed].sort();
  if (keys.length !== expected.length || keys.some((key, index) => key !== expected[index])) {
    throw new TypeError(`${label} fields are incompatible`);
  }
}

function boundedText(value, label, max = 160) {
  if (
    typeof value !== "string"
    || value.length < 1
    || value.length > max
    || value.includes("\0")
  ) {
    throw new TypeError(`${label} must be bounded text`);
  }
  return value;
}

function textArray(value, label, maxItems = 16) {
  if (!Array.isArray(value) || value.length > maxItems) {
    throw new TypeError(`${label} must be a bounded array`);
  }
  return Object.freeze(value.map((entry, index) => boundedText(entry, `${label}[${index}]`, 96)));
}

function safeEntrypoint(value) {
  const entrypoint = boundedText(value, "External app entrypoint", 160);
  if (
    entrypoint.startsWith("/")
    || entrypoint.includes("\\")
    || entrypoint.includes(":")
    || entrypoint.split("/").some((segment) => segment === "" || segment === "." || segment === "..")
  ) {
    throw new TypeError("External app entrypoint must be a safe relative POSIX path");
  }
  return entrypoint;
}

function strictBase64(value, label) {
  const text = boundedText(value, label, 256);
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(text) || text.length % 4 !== 0) {
    throw new TypeError(`${label} must be canonical base64`);
  }
  const bytes = Buffer.from(text, "base64");
  if (bytes.toString("base64") !== text) {
    throw new TypeError(`${label} must be canonical base64`);
  }
  return bytes;
}

export function validateExternalAppManifest(value) {
  const manifest = objectValue(value, "External app manifest");
  exactKeys(manifest, MANIFEST_KEYS, "External app manifest");
  if (manifest.$schema !== EXTERNAL_APP_MANIFEST_SCHEMA) {
    throw new TypeError("External app manifest schema is incompatible");
  }

  const appId = boundedText(manifest.app_id, "External app id", 80);
  if (!APP_ID_PATTERN.test(appId)) throw new TypeError("External app id is invalid");
  const version = boundedText(manifest.version, "External app version", 80);
  if (!VERSION_PATTERN.test(version)) throw new TypeError("External app version is invalid");
  const publisher = boundedText(manifest.publisher, "External app publisher", 120);
  const entrypoint = safeEntrypoint(manifest.entrypoint);

  const supportedModes = textArray(manifest.supported_modes, "External app supported modes", 4);
  if (supportedModes.length < 1 || supportedModes.some((mode) => !SUPPORTED_MODES.has(mode))) {
    throw new TypeError("External app proof supports only the web mode");
  }

  const requiredContracts = textArray(
    manifest.required_contracts,
    "External app required contracts",
    16,
  );
  if (requiredContracts.some((contract) => !CONTRACT_PATTERN.test(contract))) {
    throw new TypeError("External app required contract is invalid");
  }

  const requestedCapabilities = textArray(
    manifest.requested_capabilities,
    "External app requested capabilities",
    8,
  );
  if (requestedCapabilities.length !== 0) {
    throw new TypeError("External app proof must not request capabilities");
  }

  const contentHash = boundedText(manifest.content_hash, "External app content hash", 64);
  if (!SHA256_PATTERN.test(contentHash)) {
    throw new TypeError("External app content hash must be lowercase SHA-256");
  }
  if (manifest.update_policy !== "manual-test-only") {
    throw new TypeError("External app proof update policy must remain manual-test-only");
  }

  return Object.freeze({
    $schema: EXTERNAL_APP_MANIFEST_SCHEMA,
    app_id: appId,
    version,
    publisher,
    entrypoint,
    supported_modes: supportedModes,
    required_contracts: requiredContracts,
    requested_capabilities: Object.freeze([]),
    content_hash: contentHash,
    update_policy: "manual-test-only",
  });
}

export function canonicalExternalAppManifestBytes(value) {
  return Buffer.from(JSON.stringify(validateExternalAppManifest(value)), "utf8");
}

function validateEnvelope(value) {
  const envelope = objectValue(value, "External app envelope");
  exactKeys(envelope, ENVELOPE_KEYS, "External app envelope");
  if (envelope.$schema !== EXTERNAL_APP_ENVELOPE_SCHEMA) {
    throw new TypeError("External app envelope schema is incompatible");
  }
  if (envelope.algorithm !== EXTERNAL_APP_SIGNATURE_ALGORITHM) {
    throw new TypeError("External app envelope algorithm is unsupported");
  }
  const keyId = boundedText(envelope.key_id, "External app envelope key id", 64);
  if (!KEY_ID_PATTERN.test(keyId)) throw new TypeError("External app envelope key id is invalid");
  const signature = strictBase64(envelope.signature_base64, "External app signature");
  if (signature.length !== 64) throw new TypeError("External app Ed25519 signature must be 64 bytes");
  return Object.freeze({ keyId, signature });
}

function validateTrust(value) {
  const trust = objectValue(value, "External app test trust");
  exactKeys(trust, TRUST_KEYS, "External app test trust");
  if (trust.$schema !== EXTERNAL_APP_TEST_TRUST_SCHEMA) {
    throw new TypeError("External app test trust schema is incompatible");
  }
  if (trust.algorithm !== EXTERNAL_APP_SIGNATURE_ALGORITHM) {
    throw new TypeError("External app test trust algorithm is unsupported");
  }
  const keyId = boundedText(trust.key_id, "External app test trust key id", 64);
  if (!KEY_ID_PATTERN.test(keyId)) throw new TypeError("External app test trust key id is invalid");
  const publicKeyPem = boundedText(trust.public_key_pem, "External app test public key", 2048);
  const publicKey = createPublicKey(publicKeyPem);
  if (publicKey.asymmetricKeyType !== "ed25519") {
    throw new TypeError("External app test trust must contain an Ed25519 public key");
  }
  return Object.freeze({ keyId, publicKey });
}

export function verifyExternalAppProof({ manifest, envelope, trust, contentBytes } = {}) {
  const normalizedManifest = validateExternalAppManifest(manifest);
  const normalizedEnvelope = validateEnvelope(envelope);
  const normalizedTrust = validateTrust(trust);
  if (normalizedEnvelope.keyId !== normalizedTrust.keyId) {
    throw new Error("External app signature key does not match test trust");
  }

  if (!(contentBytes instanceof Uint8Array) || contentBytes.byteLength < 1 || contentBytes.byteLength > MAX_CONTENT_BYTES) {
    throw new TypeError("External app proof content must be bounded bytes");
  }
  const actualHash = createHash("sha256").update(contentBytes).digest("hex");
  if (actualHash !== normalizedManifest.content_hash) {
    throw new Error("External app content hash mismatch");
  }

  const payload = canonicalExternalAppManifestBytes(normalizedManifest);
  if (!verifySignature(null, payload, normalizedTrust.publicKey, normalizedEnvelope.signature)) {
    throw new Error("External app manifest signature verification failed");
  }

  return normalizedManifest;
}
