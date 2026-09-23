import test from "node:test";
import assert from "node:assert/strict";

import {
  UPDATE_STATUS_SCHEMA,
  assertUpdateStatusPort,
  validateUpdateStatusSnapshot,
} from "../system/contracts/update-status.mjs";
import {
  buildReloadUrl,
  createNativeUpdateWatcher,
  shouldReloadForUpdate,
} from "../system/adapters/native/update-runtime.mjs";

function fakeWindow() {
  return {
    async fetch() {
      return {
        ok: true,
        async json() {
          return {
            sourceSha: "0123456789012345678901234567890123456789",
            status: "running",
            applyMode: "initial",
          };
        },
      };
    },
    location: { href: "http://127.0.0.1:8765/composition/native/index.html?source=old", reload() {}, replace() {} },
    setTimeout() { return 1; },
    clearTimeout() {},
  };
}

test("update status contract normalizes optional fields", () => {
  const snapshot = validateUpdateStatusSnapshot({
    sourceSha: "0123456789012345678901234567890123456789",
    status: "running",
    applyMode: "initial",
  });
  assert.equal(snapshot.bootRefreshRequired, false);
  assert.equal(snapshot.baseUpdatePhase, "none");
  assert.equal(snapshot.baseUpdateSha, "");
  assert.equal(snapshot.deliveryNumber, 0);
  assert.equal(snapshot.versionNumber, 0);
  assert.equal(snapshot.lastApplyDurationSeconds, 0);
  assert.equal(snapshot.lastStageDurationSeconds, 0);
  assert.equal(snapshot.runtimeSurfaceSha, snapshot.sourceSha);
  assert.equal(snapshot.targetSha, "");
  assert.equal(snapshot.phase, "idle");
  assert.equal(snapshot.attemptId, "");
  assert.equal(snapshot.checkedAt, "unknown");
  assert.equal(snapshot.lastAppliedSha, "");
  assert.equal(snapshot.rejectedSha, "");
  assert.equal(snapshot.recoveryState, "unavailable");
  assert.equal(snapshot.recoverySource, "none");
  assert.equal(snapshot.currentReleaseSha, "");
  assert.equal(snapshot.knownGoodReleaseSha, "");
  assert.equal(snapshot.candidateReleaseSha, "");
  assert.equal(snapshot.recoveryRejectedSha, "");
  assert.equal(snapshot.rollbackEligible, false);
  assert.equal(snapshot.lastError, "");
  assert.equal(snapshot.healthToken, "");
});

test("update status preserves observed portable recovery state without granting authority", () => {
  const current = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
  const knownGood = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
  const candidate = "cccccccccccccccccccccccccccccccccccccccc";
  const rejected = "dddddddddddddddddddddddddddddddddddddddd";
  const snapshot = validateUpdateStatusSnapshot({
    sourceSha: current,
    status: "running",
    applyMode: "none",
    recoveryState: "available",
    recoverySource: "portable-state",
    currentReleaseSha: current,
    knownGoodReleaseSha: knownGood,
    candidateReleaseSha: candidate,
    recoveryRejectedSha: rejected,
    rollbackEligible: true,
  });
  assert.equal(snapshot.recoveryState, "available");
  assert.equal(snapshot.recoverySource, "portable-state");
  assert.equal(snapshot.currentReleaseSha, current);
  assert.equal(snapshot.knownGoodReleaseSha, knownGood);
  assert.equal(snapshot.candidateReleaseSha, candidate);
  assert.equal(snapshot.recoveryRejectedSha, rejected);
  assert.equal(snapshot.rollbackEligible, true);
  assert.equal("rollback" in snapshot, false);
});

test("update status rejects false recovery claims", () => {
  assert.throws(
    () => validateUpdateStatusSnapshot({
      sourceSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      status: "running",
      applyMode: "none",
      recoveryState: "available",
      recoverySource: "portable-state",
      currentReleaseSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      knownGoodReleaseSha: "",
    }),
    /requires observed portable current and known-good/,
  );
  assert.throws(
    () => validateUpdateStatusSnapshot({
      sourceSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      status: "running",
      applyMode: "none",
      recoveryState: "available",
      recoverySource: "portable-state",
      currentReleaseSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      knownGoodReleaseSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      rollbackEligible: true,
    }),
    /distinct observed known-good/,
  );
});

test("update status preserves runtime-effective Surface identity separately from Git HEAD", () => {
  const snapshot = validateUpdateStatusSnapshot({
    sourceSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    runtimeSurfaceSha: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    status: "running",
    applyMode: "none",
  });
  assert.equal(snapshot.sourceSha, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
  assert.equal(snapshot.runtimeSurfaceSha, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
});

test("update status preserves human version and bounded durations", () => {
  const snapshot = validateUpdateStatusSnapshot({
    sourceSha: "0123456789012345678901234567890123456789",
    deliveryNumber: 124,
    status: "running",
    applyMode: "reload",
    lastApplyDurationSeconds: 5,
    lastStageDurationSeconds: 0,
  });
  assert.equal(snapshot.deliveryNumber, 124);
  assert.equal(snapshot.versionNumber, 124);
  assert.equal(snapshot.lastApplyDurationSeconds, 5);
  assert.equal(snapshot.lastStageDurationSeconds, 0);
});

test("update status preserves transaction context", () => {
  const snapshot = validateUpdateStatusSnapshot({
    sourceSha: "0123456789012345678901234567890123456789",
    targetSha: "abcdef0123456789abcdef0123456789abcdef01",
    status: "applied",
    phase: "health-wait",
    applyMode: "reload",
    attemptId: "2026-09-18T09:10:00Z",
    lastError: "health-check-pending",
  });
  assert.equal(snapshot.targetSha, "abcdef0123456789abcdef0123456789abcdef01");
  assert.equal(snapshot.phase, "health-wait");
  assert.equal(snapshot.attemptId, "2026-09-18T09:10:00Z");
  assert.equal(snapshot.lastError, "health-check-pending");
});

test("update status preserves explicit Base pipeline progress", () => {
  const snapshot = validateUpdateStatusSnapshot({
    sourceSha: "0123456789012345678901234567890123456789",
    status: "running",
    applyMode: "none",
    bootRefreshRequired: true,
    baseUpdatePhase: "activation-ready",
    baseUpdateSha: "abcdef0123456789abcdef0123456789abcdef01",
  });
  assert.equal(snapshot.baseUpdatePhase, "activation-ready");
  assert.equal(snapshot.baseUpdateSha, "abcdef0123456789abcdef0123456789abcdef01");
});

test("boot refresh without a new Base phase remains backward compatible", () => {
  const snapshot = validateUpdateStatusSnapshot({
    sourceSha: "0123456789012345678901234567890123456789",
    status: "running",
    applyMode: "none",
    bootRefreshRequired: true,
  });
  assert.equal(snapshot.baseUpdatePhase, "waiting-candidate");
});

test("update status rejects unknown Base pipeline phase", () => {
  assert.throws(
    () => validateUpdateStatusSnapshot({
      sourceSha: "0123456789012345678901234567890123456789",
      status: "running",
      applyMode: "none",
      bootRefreshRequired: true,
      baseUpdatePhase: "mystery-base-phase",
    }),
    TypeError,
  );
});

test("update status rejects unknown transaction phase", () => {
  assert.throws(
    () => validateUpdateStatusSnapshot({
      sourceSha: "0123456789012345678901234567890123456789",
      status: "running",
      phase: "mystery",
      applyMode: "none",
    }),
    TypeError,
  );
});

test("update status rejects missing runtime identity", () => {
  assert.throws(
    () => validateUpdateStatusSnapshot({ status: "running", applyMode: "initial" }),
    TypeError,
  );
});

test("native update watcher implements neutral update status port", () => {
  const watcher = createNativeUpdateWatcher(fakeWindow(), { intervalMs: 1 });
  assert.equal(watcher.schema, UPDATE_STATUS_SCHEMA);
  assert.equal(assertUpdateStatusPort(watcher), watcher);
  watcher.dispose();
});

test("native reload URL carries target SHA and bounded retry marker", () => {
  const url = buildReloadUrl(
    "http://127.0.0.1:8765/composition/native/index.html?source=old#surface",
    "abcdef0123456789abcdef0123456789abcdef01",
    3,
  );
  assert.equal(
    url,
    "http://127.0.0.1:8765/composition/native/index.html?source=abcdef0123456789abcdef0123456789abcdef01&ordax_reload=3#surface",
  );
});

test("native reload URL replaces prior retry marker instead of growing forever", () => {
  const url = buildReloadUrl(
    "http://127.0.0.1:8765/composition/native/index.html?source=old&ordax_reload=2",
    "0123456789012345678901234567890123456789",
    4,
  );
  assert.match(url, /source=0123456789012345678901234567890123456789/);
  assert.match(url, /ordax_reload=4/);
  assert.equal((url.match(/ordax_reload=/g) ?? []).length, 1);
});

test("runtime-neutral checkout advancement does not suppress the next live reload", () => {
  const docsSha = "3333333333333333333333333333333333333333";
  const targetSha = "4444444444444444444444444444444444444444";
  assert.equal(
    shouldReloadForUpdate(docsSha, {
      sourceSha: targetSha,
      status: "applied",
      applyMode: "reload",
    }),
    true,
  );
});

test("native update watcher never acknowledges a SHA different from the rendered page", async () => {
  const calls = [];
  const renderedSha = "1111111111111111111111111111111111111111";
  const checkoutSha = "2222222222222222222222222222222222222222";
  const windowRef = {
    async fetch(path, options = {}) {
      calls.push({ path, options });
      if (path === "/__ordax/native/update") {
        return {
          ok: true,
          async json() {
            return {
              sourceSha: checkoutSha,
              status: "running",
              applyMode: "none",
              healthToken: "token",
            };
          },
        };
      }
      return { ok: true };
    },
    location: {
      href: `http://127.0.0.1:8765/composition/native/index.html?source=${renderedSha}`,
      reload() {},
      replace() {},
    },
    setTimeout() { return 1; },
    clearTimeout() {},
  };
  const watcher = createNativeUpdateWatcher(windowRef, { intervalMs: 1 });
  await watcher.markHealthy();
  await Promise.resolve();
  assert.equal(
    calls.filter((call) => call.path === "/__ordax/native/health").length,
    0,
  );
  watcher.dispose();
});
