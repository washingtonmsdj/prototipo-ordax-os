import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  validateProfilePack,
  validateProfilePackCatalog,
} from "../system/contracts/profile-pack.mjs";
import { createProfilePackRuntime } from "../system/services/profile-packs/runtime.mjs";
import { createProfilePackSurfaceCatalog } from "../system/services/profile-packs/surface-catalog.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

async function manifest(path) {
  return JSON.parse(await readFile(resolve(ROOT, path), "utf8"));
}

const developer = await manifest("system/profile-packs/developer/manifest.json");
const legalBr = await manifest("system/profile-packs/legal-br/manifest.json");

test("Developer and Legal-BR manifests share the provider-neutral contract", () => {
  const developerPack = validateProfilePack(developer);
  const legalPack = validateProfilePack(legalBr);

  assert.equal(developerPack.slug, "developer");
  assert.equal(developerPack.state, "draft");
  assert.equal(developerPack.intelligence.preferredPurpose, "code");
  assert.equal(developerPack.security.autoGrantPrivileges, false);
  assert.equal(developerPack.security.allowUnsignedApps, false);
  assert.equal(developerPack.security.genericShellImplied, false);

  assert.equal(legalPack.slug, "legal-br");
  assert.equal(legalPack.knowledge.jurisdiction, "BR");
  assert.equal(legalPack.intelligence.preferredPurpose, null);
  assert.equal(legalPack.activation.publiclyAvailable, false);
  assert.equal(legalPack.security.crossSpaceMemory, false);
});

test("catalog rejects duplicate version identity and privilege broadening", () => {
  assert.throws(
    () => validateProfilePackCatalog([developer, developer]),
    /duplicate developer@1/,
  );

  const privileged = structuredClone(developer);
  privileged.security.auto_grant_privileges = true;
  assert.throws(
    () => validateProfilePack(privileged),
    /cannot broaden privilege, signature, shell or memory isolation policy/,
  );
});

test("Developer activates only as an explicit session-only internal proof", () => {
  const runtime = createProfilePackRuntime({ packs: [developer, legalBr] });
  const activation = runtime.activate({
    slug: "developer",
    version: 1,
    mode: "internal-proof",
    space: { id: "space-dev-proof", kind: "professional" },
  });

  assert.equal(activation.schema, "ordax.profile-pack-activation/1");
  assert.equal(activation.authority, "composition-explicit");
  assert.equal(activation.persistence, "session-only");
  assert.equal(activation.entitlementRequired, false);
  assert.equal(activation.billingRequired, false);
  assert.equal(activation.cloudRequired, false);
  assert.equal(activation.pack.slug, "developer");
  assert.equal(runtime.getSnapshot().activations.length, 1);

  assert.equal(runtime.deactivate("space-dev-proof"), true);
  assert.equal(runtime.getSnapshot().activations.length, 0);
});

test("internal proof fails closed for incompatible spaces, Legal-BR and non-draft states", () => {
  const runtime = createProfilePackRuntime({ packs: [developer, legalBr] });

  assert.throws(
    () => runtime.activate({
      slug: "developer",
      version: 1,
      mode: "internal-proof",
      space: { id: "personal", kind: "personal" },
    }),
    /incompatible with the selected Space kind/,
  );

  assert.throws(
    () => runtime.activate({
      slug: "legal-br",
      version: 1,
      mode: "internal-proof",
      space: { id: "legal-space", kind: "professional" },
    }),
    /explicitly blocks activation/,
  );

  const activeDeveloper = structuredClone(developer);
  activeDeveloper.state = "active";
  const activeRuntime = createProfilePackRuntime({ packs: [activeDeveloper] });
  assert.throws(
    () => activeRuntime.activate({
      slug: "developer",
      version: 1,
      mode: "internal-proof",
      space: { id: "space-dev-proof", kind: "professional" },
    }),
    /only draft Profile Packs/,
  );
});

test("Surface catalog is read-only, bounded and honest about availability", () => {
  const runtime = createProfilePackRuntime({ packs: [developer, legalBr] });
  const catalog = createProfilePackSurfaceCatalog(runtime);
  const snapshot = catalog.getSnapshot();

  assert.equal(snapshot.schema, "ordax.profile-pack-surface-catalog/1");
  assert.equal(snapshot.mutationAuthority, "none");
  assert.equal(snapshot.publicActivationEnabled, false);
  assert.equal(snapshot.packs.length, 2);

  const developerView = catalog.get("developer", 1);
  assert.equal(developerView.availability, "internal-proof-only");
  assert.equal(developerView.internalProofEligible, true);
  assert.equal(developerView.userActivationAvailable, false);
  assert.deepEqual(developerView.memoryScopes, ["space", "project"]);

  const legalView = catalog.get("legal-br", 1);
  assert.equal(legalView.availability, "unavailable");
  assert.equal(legalView.internalProofEligible, false);
  assert.equal(legalView.jurisdiction, "BR");
});
