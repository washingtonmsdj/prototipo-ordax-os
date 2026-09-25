import test from "node:test";
import assert from "node:assert/strict";

import { IDENTITY_SESSION_SCHEMA } from "../system/contracts/identity-session.mjs";
import { PREFERENCE_RUNTIME_SCHEMA } from "../system/contracts/preference-runtime.mjs";
import { SYNC_TRANSPORT_SCHEMA } from "../system/contracts/sync-transport.mjs";
import { WORKSPACE_STORE_SCHEMA, createDefaultWorkspaceRecord, validateWorkspaceRecord } from "../system/contracts/workspace-store.mjs";
import { createPreferenceSnapshot, setPreferenceValue } from "../system/services/preferences/catalog.mjs";
import { createPreferenceSyncRuntime } from "../system/services/sync/preference-runtime.mjs";
import { createWorkspaceMetadataBridge } from "../system/services/sync/workspace-metadata.mjs";
import { createAccountSyncRuntime } from "../system/services/sync/account-runtime.mjs";

function signedInIdentity() {
  const snapshot = Object.freeze({
    state: "signed-in",
    subjectId: "user-1",
    displayName: "Pessoa",
  });
  return {
    schema: IDENTITY_SESSION_SCHEMA,
    getSnapshot: () => snapshot,
    subscribe(listener) {
      return () => {};
    },
  };
}

function preferencesRuntime() {
  let snapshot = createPreferenceSnapshot();
  const listeners = new Set();
  return {
    schema: PREFERENCE_RUNTIME_SCHEMA,
    getSnapshot: () => snapshot,
    set(id, value) {
      const next = setPreferenceValue(snapshot, id, value);
      if (next === snapshot) return snapshot;
      snapshot = next;
      for (const listener of [...listeners]) listener(snapshot);
      return snapshot;
    },
    subscribe(listener) {
      listeners.add(listener);
      listener(snapshot);
      return () => listeners.delete(listener);
    },
  };
}

function workspaceStore() {
  let snapshot = createDefaultWorkspaceRecord();
  return {
    schema: WORKSPACE_STORE_SCHEMA,
    load: () => snapshot,
    save(next) {
      snapshot = validateWorkspaceRecord(next);
      return true;
    },
  };
}

function keyFactory(prefix) {
  let ordinal = 0;
  return (kind = "state") => `${prefix}:${kind}:${++ordinal}:abcdefgh`;
}

test("account sync applies remote appearance, portable preferences and workspace without echo", async () => {
  const preferences = preferencesRuntime();
  const preferenceSync = createPreferenceSyncRuntime(preferences, {
    createIdempotencyKey: keyFactory("pref"),
  });
  const bridge = createWorkspaceMetadataBridge(workspaceStore());
  const applied = [];

  const transport = {
    schema: SYNC_TRANSPORT_SCHEMA,
    async listObjects() {
      return [
        {
          objectId: "appearance/theme",
          dataClass: "appearance",
          objectSchemaVersion: 1,
          resolverVersion: 1,
          serverRevision: 3,
          tombstone: false,
          payload: { theme: "dark" },
        },
        {
          objectId: "preferences/surface",
          dataClass: "preferences",
          objectSchemaVersion: 1,
          resolverVersion: 1,
          serverRevision: 5,
          tombstone: false,
          payload: {
            "accessibility.contrast": "high",
            "accessibility.motion": "reduced",
            "accessibility.text-scale": "large",
          },
        },
        {
          objectId: "workspace/portable",
          dataClass: "workspace-metadata",
          objectSchemaVersion: 1,
          resolverVersion: 1,
          serverRevision: 7,
          tombstone: false,
          payload: {
            activeAreaId: "area-2",
            areas: [
              { id: "area-1", ordinal: 1, appIds: ["files"] },
              { id: "area-2", ordinal: 2, appIds: ["settings"] },
            ],
          },
        },
      ];
    },
    async applyMutation(value) {
      applied.push(value);
      return {
        $schema: "prototype-ordax.sync-ack/1",
        objectId: value.objectId,
        dataClass: value.dataClass,
        serverRevision: value.baseServerRevision + 1,
        tombstone: false,
        applied: true,
        conflict: false,
      };
    },
  };

  const sync = createAccountSyncRuntime({
    identitySession: signedInIdentity(),
    transport,
    preferenceSync,
    preferences,
    workspaceMetadataSource: bridge.source,
    workspaceStore: bridge.store,
    createIdempotencyKey: keyFactory("account"),
  });

  await sync.refresh();

  assert.equal(preferences.getSnapshot()["appearance.theme"], "dark");
  assert.equal(preferences.getSnapshot()["accessibility.contrast"], "high");
  assert.equal(preferences.getSnapshot()["accessibility.motion"], "reduced");
  assert.equal(preferences.getSnapshot()["accessibility.text-scale"], "large");
  assert.equal(bridge.source.getSnapshot().activeAreaId, "area-2");
  assert.deepEqual(bridge.source.getSnapshot().areas[1].appIds, ["settings"]);
  assert.equal(preferenceSync.pendingMutations().length, 0);
  assert.equal(applied.length, 0, "remote state must not echo back as a new local mutation");
  assert.deepEqual(sync.getSnapshot().trackedDataClasses, [
    "appearance",
    "preferences",
    "workspace-metadata",
  ]);
  assert.equal(sync.getSnapshot().accountContinuity, "active");

  preferences.set("accessibility.contrast", "standard");
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(applied.some((item) => item.objectId === "preferences/surface"), true);

  sync.destroy();
  preferenceSync.destroy();
});
