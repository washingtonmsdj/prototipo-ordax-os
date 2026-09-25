import {
  PROFILE_PACK_ACTIVATION_SCHEMA,
  PROFILE_PACK_RUNTIME_SCHEMA,
  validateProfilePack,
  validateProfilePackSpace,
} from "../../contracts/profile-pack.mjs";

function packIdentity(pack) {
  return `${pack.slug}@${pack.version}`;
}

function activationSnapshot(pack, space) {
  return Object.freeze({
    schema: PROFILE_PACK_ACTIVATION_SCHEMA,
    mode: "internal-proof",
    authority: "composition-explicit",
    persistence: "session-only",
    entitlementRequired: false,
    billingRequired: false,
    cloudRequired: false,
    space: Object.freeze({ id: space.id, kind: space.kind }),
    pack,
  });
}

export function createProfilePackRuntime({ packs = [] } = {}) {
  if (!Array.isArray(packs) || packs.length > 64) {
    throw new TypeError("Profile Pack runtime requires a bounded pack catalog");
  }

  const catalog = new Map();
  for (const candidate of packs) {
    const pack = validateProfilePack(candidate);
    const key = packIdentity(pack);
    if (catalog.has(key)) throw new Error(`Duplicate Profile Pack ${key}`);
    catalog.set(key, pack);
  }

  const activations = new Map();
  const listeners = new Set();
  let disposed = false;

  const snapshot = () => Object.freeze({
    schema: PROFILE_PACK_RUNTIME_SCHEMA,
    packs: Object.freeze([...catalog.values()]),
    activations: Object.freeze([...activations.values()]),
  });

  const publish = () => {
    if (disposed) return;
    const current = snapshot();
    for (const listener of [...listeners]) listener(current);
  };

  return Object.freeze({
    schema: PROFILE_PACK_RUNTIME_SCHEMA,
    getSnapshot() {
      return snapshot();
    },
    subscribe(listener) {
      if (typeof listener !== "function") throw new TypeError("Profile Pack listener must be a function");
      if (disposed) return () => {};
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    list() {
      if (disposed) throw new Error("Profile Pack runtime is disposed");
      return Object.freeze([...catalog.values()]);
    },
    activate({ slug, version, space, mode } = {}) {
      if (disposed) throw new Error("Profile Pack runtime is disposed");
      if (mode !== "internal-proof") {
        throw new Error("Profile Pack activation is limited to explicit internal proof");
      }
      if (typeof slug !== "string" || !Number.isSafeInteger(version)) {
        throw new TypeError("Profile Pack activation requires exact slug and version");
      }
      const pack = catalog.get(`${slug}@${version}`);
      if (!pack) throw new Error("Requested Profile Pack is not in the local catalog");
      if (pack.state !== "draft" && pack.state !== "internal-proof") {
        throw new Error("Published Profile Packs require the future distribution authority");
      }
      if (pack.intelligence.externalProviderRequired) {
        throw new Error("Internal Profile Pack proof cannot require external model egress");
      }
      const targetSpace = validateProfilePackSpace(space);
      if (targetSpace.kind !== pack.spaceKind) {
        throw new Error("Profile Pack is incompatible with the selected Space kind");
      }
      const activation = activationSnapshot(pack, targetSpace);
      activations.set(targetSpace.id, activation);
      publish();
      return activation;
    },
    deactivate(spaceId) {
      if (disposed) throw new Error("Profile Pack runtime is disposed");
      if (typeof spaceId !== "string" || spaceId.length < 1 || spaceId.length > 160 || spaceId.includes("\0")) {
        throw new TypeError("Profile Pack deactivation requires a bounded Space id");
      }
      const changed = activations.delete(spaceId);
      if (changed) publish();
      return changed;
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      activations.clear();
      listeners.clear();
    },
  });
}
