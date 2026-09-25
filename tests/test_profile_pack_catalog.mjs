import assert from "node:assert/strict";

import {
  assertProfilePackCatalogPort,
  validateProfilePackCatalogProjection,
} from "../system/contracts/profile-pack-catalog.mjs";
import { createProfilePackCatalog } from "../system/services/profile-packs/catalog.mjs";

const active = {
  slug: "developer",
  version: 1,
  state: "active",
  title: "Developer",
  category: "development",
  manifest: {
    space_kind: "professional",
    apps: ["projects", "notes"],
    templates: ["repo-review"],
    intelligence: {
      preferred_purpose: "code",
      external_provider_required: false,
    },
  },
  knowledge_policy: {},
  backend_only_secret: "must-not-leak",
};

{
  const catalog = createProfilePackCatalog({
    rows: [
      { ...active, slug: "creator", title: "Creator", version: 2 },
      active,
    ],
  });
  assert.equal(assertProfilePackCatalogPort(catalog), catalog);
  assert.equal(catalog.schema, "ordax.profile-pack-catalog/1");
  assert.deepEqual(catalog.list().map((entry) => entry.slug), ["creator", "developer"]);
  const developer = catalog.get("developer", 1);
  assert.equal(developer.schema, "ordax.profile-pack-catalog-entry/1");
  assert.equal(developer.spaceKind, "professional");
  assert.deepEqual(developer.apps, ["projects", "notes"]);
  assert.equal(developer.intelligence.preferredPurpose, "code");
  assert.equal(developer.intelligence.externalProviderRequired, false);
  assert.equal("manifest" in developer, false);
  assert.equal("knowledge_policy" in developer, false);
  assert.equal("backend_only_secret" in developer, false);
  assert.equal(catalog.get("developer", 99), null);
  assert.throws(() => developer.apps.push("system"), TypeError);
  assert.deepEqual(validateProfilePackCatalogProjection(developer), developer);
}

for (const state of ["draft", "retired"]) {
  assert.throws(
    () => createProfilePackCatalog({ rows: [{ ...active, state }] }),
    /must be active/,
  );
}

assert.throws(
  () => createProfilePackCatalog({ rows: [active, structuredClone(active)] }),
  /Duplicate Profile Pack catalog entry/,
);

{
  const unsafe = structuredClone(active);
  unsafe.manifest.intelligence.external_provider_required = "yes";
  assert.throws(
    () => createProfilePackCatalog({ rows: [unsafe] }),
    /external provider policy is invalid/,
  );
}

assert.throws(
  () => assertProfilePackCatalogPort({ schema: "ordax.profile-pack-catalog/1", list() { return []; } }),
  /must implement get/,
);
assert.throws(
  () => assertProfilePackCatalogPort({
    schema: "ordax.profile-pack-catalog/1",
    list() {
      return [{
        schema: "ordax.profile-pack-catalog-entry/1",
        slug: "developer",
        version: 1,
        title: "Developer",
        category: "development",
        spaceKind: "professional",
        apps: [],
        templates: [],
        intelligence: { preferredPurpose: "code", externalProviderRequired: "no" },
      }];
    },
    get() { return null; },
  }),
  /external provider policy is invalid/,
);

console.log("PROFILE_PACK_CATALOG=PASS");
