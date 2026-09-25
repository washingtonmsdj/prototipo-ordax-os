import { assertIdentitySessionPort } from "../../contracts/identity-session.mjs";
import { assertPreferenceRuntimePort } from "../../contracts/preference-runtime.mjs";
import {
  SYNC_RUNTIME_SCHEMA,
  validateSyncRuntimeSnapshot,
} from "../../contracts/sync-runtime.mjs";
import { assertSyncTransportPort } from "../../contracts/sync-transport.mjs";
import {
  assertWorkspaceMetadataSource,
  validateWorkspaceMetadata,
  WORKSPACE_METADATA_SCHEMA,
} from "../../contracts/workspace-metadata-source.mjs";
import {
  assertWorkspaceStore,
  validateWorkspaceRecord,
} from "../../contracts/workspace-store.mjs";
import {
  ACCESSIBILITY_CONTRAST_PREFERENCE_ID,
  ACCESSIBILITY_MOTION_PREFERENCE_ID,
  ACCESSIBILITY_TEXT_SCALE_PREFERENCE_ID,
} from "../preferences/accessibility.mjs";
import { getPreferenceDefinition } from "../preferences/catalog.mjs";
import {
  APPEARANCE_SYNC_OBJECT_ID,
  createAppearanceSyncObject,
  SYNC_MUTATION_SCHEMA,
} from "./runtime.mjs";

export const PORTABLE_PREFERENCES_OBJECT_ID = "preferences/surface";
export const PORTABLE_WORKSPACE_OBJECT_ID = "workspace/portable";

const PORTABLE_PREFERENCE_IDS = Object.freeze([
  ACCESSIBILITY_CONTRAST_PREFERENCE_ID,
  ACCESSIBILITY_MOTION_PREFERENCE_ID,
  ACCESSIBILITY_TEXT_SCALE_PREFERENCE_ID,
]);

function requireIdFactory(value) {
  if (typeof value !== "function") throw new TypeError("Account sync requires createIdempotencyKey()");
  return value;
}

function portablePreferences(snapshot) {
  const payload = {};
  for (const id of PORTABLE_PREFERENCE_IDS) {
    const definition = getPreferenceDefinition(id);
    payload[id] = definition.validate(snapshot[id]);
  }
  return Object.freeze(payload);
}

function validatePortablePreferences(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new TypeError("Portable preferences payload must be an object");
  }
  return portablePreferences(payload);
}

function mutation({ objectId, dataClass, baseServerRevision, payload, idempotencyKey }) {
  return Object.freeze({
    $schema: SYNC_MUTATION_SCHEMA,
    operation: "upsert",
    objectId,
    dataClass,
    objectSchemaVersion: 1,
    resolverVersion: 1,
    baseServerRevision,
    idempotencyKey,
    payload,
  });
}

function workspaceRecordFromMetadata(value) {
  const metadata = validateWorkspaceMetadata(value);
  const areas = metadata.areas.map((area) => {
    const counts = new Map();
    const windows = area.appIds.map((appId, index) => {
      const next = (counts.get(appId) ?? 0) + 1;
      counts.set(appId, next);
      return {
        id: next === 1 ? appId : `${appId}:${next}`,
        appId,
        minimized: false,
        maximized: false,
        placementOrdinal: index + 1,
        positionX: null,
        positionY: null,
        target: null,
      };
    });
    return {
      id: area.id,
      ordinal: area.ordinal,
      windows,
      activeWindowId: area.id === metadata.activeAreaId && windows.length ? windows[0].id : null,
      nextWindowOrdinal: windows.length + 1,
    };
  });
  const highestArea = Math.max(...areas.map((area) => area.ordinal));
  return validateWorkspaceRecord({
    activeAreaId: metadata.activeAreaId,
    nextAreaOrdinal: highestArea + 1,
    areas,
  });
}

function remoteWorkspacePayload(payload) {
  return validateWorkspaceMetadata({
    $schema: WORKSPACE_METADATA_SCHEMA,
    activeAreaId: payload?.activeAreaId,
    areas: payload?.areas,
  });
}

function fingerprint(value) {
  return JSON.stringify(value);
}

export function createAccountSyncRuntime({
  identitySession,
  transport,
  preferenceSync,
  preferences,
  workspaceMetadataSource,
  workspaceStore,
  createIdempotencyKey,
}) {
  const identity = assertIdentitySessionPort(identitySession);
  const remote = assertSyncTransportPort(transport);
  const preferencePort = assertPreferenceRuntimePort(preferences);
  const workspaceSource = assertWorkspaceMetadataSource(workspaceMetadataSource);
  const workspaceState = assertWorkspaceStore(workspaceStore);
  const nextKey = requireIdFactory(createIdempotencyKey);

  const revisions = new Map([
    [APPEARANCE_SYNC_OBJECT_ID, 0],
    [PORTABLE_PREFERENCES_OBJECT_ID, 0],
    [PORTABLE_WORKSPACE_OBJECT_ID, 0],
  ]);
  const pending = new Map();
  const listeners = new Set();
  let initialized = false;
  let destroyed = false;
  let suppressPreferences = false;
  let suppressWorkspace = false;
  let preferencesDirty = false;
  let workspaceDirty = false;
  let syncing = false;
  let retryRequested = false;
  let lastPreferenceFingerprint = fingerprint(portablePreferences(preferencePort.getSnapshot()));
  let lastWorkspaceFingerprint = fingerprint(workspaceSource.getSnapshot());

  const currentSnapshot = () => {
    const identitySnapshot = identity.getSnapshot();
    const preferenceSnapshot = preferenceSync.getSnapshot();
    const otherPending = pending.size + Number(preferencesDirty) + Number(workspaceDirty);
    return validateSyncRuntimeSnapshot({
      transport: identitySnapshot.state === "unavailable" ? "host-required" : "available",
      accountContinuity:
        identitySnapshot.state === "signed-in" && initialized ? "active" : "not-active",
      pendingMutationCount: preferenceSnapshot.pendingMutationCount + otherPending,
      queuePersistence: otherPending > 0 ? "session" : preferenceSnapshot.queuePersistence,
      trackedDataClasses: ["appearance", "preferences", "workspace-metadata"],
    });
  };

  const emit = () => {
    if (destroyed) return;
    const snapshot = currentSnapshot();
    for (const listener of [...listeners]) listener(snapshot);
  };

  const queuePreferences = () => {
    const payload = portablePreferences(preferencePort.getSnapshot());
    preferencesDirty = false;
    lastPreferenceFingerprint = fingerprint(payload);
    pending.set(
      PORTABLE_PREFERENCES_OBJECT_ID,
      mutation({
        objectId: PORTABLE_PREFERENCES_OBJECT_ID,
        dataClass: "preferences",
        baseServerRevision: revisions.get(PORTABLE_PREFERENCES_OBJECT_ID) ?? 0,
        payload,
        idempotencyKey: nextKey("preferences"),
      }),
    );
    emit();
    void flush();
  };

  const queueWorkspace = () => {
    const metadata = workspaceSource.getSnapshot();
    workspaceDirty = false;
    lastWorkspaceFingerprint = fingerprint(metadata);
    pending.set(
      PORTABLE_WORKSPACE_OBJECT_ID,
      mutation({
        objectId: PORTABLE_WORKSPACE_OBJECT_ID,
        dataClass: "workspace-metadata",
        baseServerRevision: revisions.get(PORTABLE_WORKSPACE_OBJECT_ID) ?? 0,
        payload: {
          activeAreaId: metadata.activeAreaId,
          areas: metadata.areas,
        },
        idempotencyKey: nextKey("workspace"),
      }),
    );
    emit();
    void flush();
  };

  async function flush() {
    if (destroyed || syncing || identity.getSnapshot().state !== "signed-in" || !initialized) {
      return;
    }
    syncing = true;
    retryRequested = false;
    try {
      for (const appearanceMutation of preferenceSync.pendingMutations()) {
        const expected = revisions.get(APPEARANCE_SYNC_OBJECT_ID) ?? 0;
        if (appearanceMutation.baseServerRevision !== expected) continue;
        try {
          const ack = await remote.applyMutation({ ...appearanceMutation, resolverVersion: 1 });
          if (ack.conflict) continue;
          if (ack.applied) {
            revisions.set(APPEARANCE_SYNC_OBJECT_ID, ack.serverRevision);
            preferenceSync.acknowledge(appearanceMutation.idempotencyKey, ack.serverRevision);
          }
        } catch {
          retryRequested = true;
        }
      }

      for (const [objectId, pendingMutation] of [...pending]) {
        try {
          const ack = await remote.applyMutation(pendingMutation);
          if (ack.conflict) continue;
          if (ack.applied) {
            revisions.set(objectId, ack.serverRevision);
            if (pending.get(objectId)?.idempotencyKey === pendingMutation.idempotencyKey) {
              pending.delete(objectId);
            }
          }
        } catch {
          retryRequested = true;
        }
      }
    } finally {
      syncing = false;
      emit();
      if (retryRequested && !destroyed) {
        // A later local change, identity refresh or online event can call flush again.
      }
    }
  }

  const applyRemotePreferences = (object) => {
    const payload = validatePortablePreferences(object.payload);
    suppressPreferences = true;
    try {
      for (const id of PORTABLE_PREFERENCE_IDS) {
        preferencePort.set(id, payload[id]);
      }
      lastPreferenceFingerprint = fingerprint(payload);
    } finally {
      suppressPreferences = false;
    }
  };

  const applyRemoteWorkspace = (object) => {
    const metadata = remoteWorkspacePayload(object.payload);
    suppressWorkspace = true;
    try {
      workspaceState.save(workspaceRecordFromMetadata(metadata));
      lastWorkspaceFingerprint = fingerprint(metadata);
    } finally {
      suppressWorkspace = false;
    }
  };

  async function initialize() {
    if (destroyed || identity.getSnapshot().state !== "signed-in") {
      initialized = false;
      emit();
      return;
    }
    initialized = false;
    emit();
    try {
      const objects = await remote.listObjects({ afterRevision: 0, limit: 200 });
      const byId = new Map(objects.map((object) => [object.objectId, object]));

      const appearance = byId.get(APPEARANCE_SYNC_OBJECT_ID);
      if (appearance && !appearance.tombstone) {
        revisions.set(APPEARANCE_SYNC_OBJECT_ID, appearance.serverRevision);
        const localPending = preferenceSync.pendingMutations();
        if (localPending.length === 0) {
          preferenceSync.applyRemoteAppearance(
            createAppearanceSyncObject({
              theme: appearance.payload?.theme,
              serverRevision: appearance.serverRevision,
            }),
          );
        }
      }

      const prefs = byId.get(PORTABLE_PREFERENCES_OBJECT_ID);
      if (prefs && !prefs.tombstone) {
        revisions.set(PORTABLE_PREFERENCES_OBJECT_ID, prefs.serverRevision);
        if (preferencesDirty) {
          queuePreferences();
        } else {
          applyRemotePreferences(prefs);
        }
      } else {
        queuePreferences();
      }

      const workspace = byId.get(PORTABLE_WORKSPACE_OBJECT_ID);
      if (workspace && !workspace.tombstone) {
        revisions.set(PORTABLE_WORKSPACE_OBJECT_ID, workspace.serverRevision);
        if (workspaceDirty) {
          queueWorkspace();
        } else {
          applyRemoteWorkspace(workspace);
        }
      } else {
        queueWorkspace();
      }

      initialized = true;
      emit();
      await flush();
    } catch {
      initialized = false;
      emit();
    }
  }

  const unsubscribePreferences = preferencePort.subscribe((snapshot) => {
    const next = fingerprint(portablePreferences(snapshot));
    if (suppressPreferences || next === lastPreferenceFingerprint) return;
    lastPreferenceFingerprint = next;
    if (initialized && identity.getSnapshot().state === "signed-in") {
      queuePreferences();
    } else {
      preferencesDirty = true;
      emit();
    }
  });

  const unsubscribeWorkspace = workspaceSource.subscribe((snapshot) => {
    const next = fingerprint(snapshot);
    if (suppressWorkspace || next === lastWorkspaceFingerprint) return;
    lastWorkspaceFingerprint = next;
    if (initialized && identity.getSnapshot().state === "signed-in") {
      queueWorkspace();
    } else {
      workspaceDirty = true;
      emit();
    }
  });

  const unsubscribePreferenceSync = preferenceSync.subscribe(() => {
    emit();
    void flush();
  });

  const unsubscribeIdentity = identity.subscribe((snapshot) => {
    if (snapshot.state === "signed-in") {
      void initialize();
    } else {
      initialized = false;
      emit();
    }
  });

  return Object.freeze({
    schema: SYNC_RUNTIME_SCHEMA,
    getSnapshot() {
      return currentSnapshot();
    },
    subscribe(listener) {
      if (typeof listener !== "function") throw new TypeError("Sync runtime listener must be a function");
      listeners.add(listener);
      listener(currentSnapshot());
      return () => listeners.delete(listener);
    },
    async refresh() {
      await initialize();
      return currentSnapshot();
    },
    async flush() {
      await flush();
      return currentSnapshot();
    },
    destroy() {
      destroyed = true;
      unsubscribeIdentity();
      unsubscribePreferenceSync();
      unsubscribeWorkspace();
      unsubscribePreferences();
      listeners.clear();
    },
  });
}
