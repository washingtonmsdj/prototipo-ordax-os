import {
  PROFILE_PACK_SURFACE_CATALOG_SCHEMA,
  assertProfilePackRuntime,
} from "../../contracts/profile-pack.mjs";

function availabilityFor(pack) {
  if (pack.state === "retired") return "retired";
  if (pack.activation?.publiclyAvailable === false) return "unavailable";
  if (pack.state === "draft") return "internal-proof-only";
  return "catalog-only";
}

function surfaceDescriptor(pack) {
  const availability = availabilityFor(pack);
  return Object.freeze({
    slug: pack.slug,
    version: pack.version,
    state: pack.state,
    title: pack.title,
    category: pack.category,
    spaceKind: pack.spaceKind,
    apps: pack.apps,
    templates: pack.templates,
    jurisdiction: pack.knowledge.jurisdiction,
    memoryScopes: pack.intelligence.memoryScopes,
    preferredPurpose: pack.intelligence.preferredPurpose,
    availability,
    userActivationAvailable: false,
    internalProofEligible: availability === "internal-proof-only"
      && !pack.intelligence.externalProviderRequired,
  });
}

export function createProfilePackSurfaceCatalog(runtimeValue) {
  const runtime = assertProfilePackRuntime(runtimeValue);

  const list = () => Object.freeze(runtime.list().map(surfaceDescriptor));

  return Object.freeze({
    schema: PROFILE_PACK_SURFACE_CATALOG_SCHEMA,
    getSnapshot() {
      return Object.freeze({
        schema: PROFILE_PACK_SURFACE_CATALOG_SCHEMA,
        packs: list(),
        mutationAuthority: "none",
        publicActivationEnabled: false,
      });
    },
    list,
    get(slug, version) {
      const pack = runtime.get(slug, version);
      return pack === null ? null : surfaceDescriptor(pack);
    },
  });
}
