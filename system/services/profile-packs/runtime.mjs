import {
  PROFILE_PACK_ACTIVATION_SCHEMA,
  PROFILE_PACK_RUNTIME_SCHEMA,
  validateProfilePackCatalog,
  validateProfilePackSpace,
} from "../../contracts/profile-pack.mjs";

function identity(slug, version) {
  return `${slug}@${version}`;
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
  const validated = validateProfilePackCatalog(packs);
  const catalog = new Map(validated.map((pack) => [identity(pack.slug, pack.version), pack]));
  const activations = new Map();
  const listeners = new Set();
  let disposed = false;

  const getPack = (slug, version) => {
    if (typeof slug !== "string" || !Number.isSafeInteger(version)) {
      throw new TypeError("Profile Pack lookup requires exact slug and version");
    }
    return catalog.get(identity(slug, version)) ?? null;
  };

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
      if (typeof listener !== "function") {
        throw new TypeError("Profile Pack listener must be a function");
      }
      if (disposed) return () => {};
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    list() {
      if (disposed) throw new Error("Profile Pack runtime is disposed");
      return Object.freeze([...catalog.values()]);
    },
    get(slug, version) {
      if (disposed) throw new Error("Profile Pack runtime is disposed");
      return getPack(slug, version);
    },
    activate({ slug, version, space, mode } = {}) {
      if (disposed) throw new Error("Profile Pack runtime is disposed");
      if (mode !== "internal-proof") {
        throw new Error("Profile Pack activation is limited to explicit internal proof");
      }
      const pack = getPack(slug, version);
      if (pack === null) throw new Error("Requested Profile Pack is not in the local catalog");
      if (pack.state !== "draft") {
        throw new Error("Internal proof accepts only draft Profile Packs");
      }
      if (pack.activation?.publiclyAvailable === false) {
        throw new Error("Profile Pack explicitly blocks activation in its manifest");
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
      if (
        typeof spaceId !== "string"
        || spaceId.length < 1
        || spaceId.length > 160
        || spaceId.includes("\0")
      ) {
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
