import assert from "node:assert/strict";
import test from "node:test";

import {
  RECOVERY_STATUS_SCHEMA,
  assertRecoveryStatusPort,
  validateRecoveryStatusSnapshot,
} from "../system/contracts/recovery-status.mjs";

test("recovery status is factual read-only Portable v2 state", () => {
  const snapshot = validateRecoveryStatusSnapshot({
    layout: "portable-v2",
    bootSlot: "current",
    runningSourceSha: "a".repeat(40),
    currentSha: "a".repeat(40),
    knownGoodSha: "b".repeat(40),
    candidateSha: null,
    transactionPresent: false,
    recoveryEntryStatus: "verified",
    policy: "local-read-only",
    automaticNetwork: false,
    automaticMutation: false,
  });
  assert.equal(snapshot.schema, RECOVERY_STATUS_SCHEMA);
  assert.equal(snapshot.knownGoodSha, "b".repeat(40));
  assert.equal(snapshot.automaticMutation, false);
  assert.equal(snapshot.automaticNetwork, false);
});

test("recovery status rejects mutation/network claims and malformed identities", () => {
  const base = {
    layout: "portable-v2",
    bootSlot: "unknown",
    runningSourceSha: "a".repeat(40),
    currentSha: null,
    knownGoodSha: null,
    candidateSha: null,
    transactionPresent: false,
    recoveryEntryStatus: "unavailable",
    policy: "local-read-only",
    automaticNetwork: false,
    automaticMutation: false,
  };
  assert.throws(
    () => validateRecoveryStatusSnapshot({ ...base, automaticMutation: true }),
    /must not claim automatic network or mutation/,
  );
  assert.throws(
    () => validateRecoveryStatusSnapshot({ ...base, currentSha: "short" }),
    /lowercase full Git SHA/,
  );
});

test("recovery port exposes only read()", () => {
  const port = {
    schema: RECOVERY_STATUS_SCHEMA,
    async read() {
      return validateRecoveryStatusSnapshot({
        layout: "portable-v2",
        bootSlot: "current",
        runningSourceSha: "a".repeat(40),
        currentSha: "a".repeat(40),
        knownGoodSha: "a".repeat(40),
        candidateSha: null,
        transactionPresent: false,
        recoveryEntryStatus: "verified",
        policy: "local-read-only",
        automaticNetwork: false,
        automaticMutation: false,
      });
    },
  };
  assert.equal(assertRecoveryStatusPort(port), port);
  assert.equal("rollback" in port, false);
  assert.equal("reboot" in port, false);
  assert.equal("recover" in port, false);
});
