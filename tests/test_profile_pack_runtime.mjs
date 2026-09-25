import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { createProfilePackRuntime } from "../system/services/profile-packs/runtime.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const developer = JSON.parse(
  await readFile(resolve(ROOT, "system/profile-packs/developer/manifest.json"), "utf8"),
);

{
  const runtime = createProfilePackRuntime({ packs: [developer] });
  const activation = runtime.activate({
    slug: "developer",
    version: 1,
    mode: "internal-proof",
    space: { id: "space-dev-proof", kind: "professional" },
  });
  assert.equal(activation.schema, "ordax.profile-pack-activation/1");
  assert.equal(activation.mode, "internal-proof");
  assert.equal(activation.authority, "composition-explicit");
  assert.equal(activation.persistence, "session-only");
  assert.equal(activation.entitlementRequired, false);
  assert.equal(activation.billingRequired, false);
  assert.equal(activation.cloudRequired, false);
  assert.equal(activation.pack.slug, "developer");
  assert.deepEqual(activation.pack.intelligence.memoryScopes, ["space", "project"]);
  assert.equal(activation.pack.intelligence.externalProviderRequired, false);
  assert.equal(activation.pack.security.autoGrantPrivileges, false);
  assert.equal(activation.pack.security.allowUnsignedApps, false);
  assert.equal(activation.pack.security.genericShellImplied, false);
  assert.equal(runtime.getSnapshot().activations.length, 1);
  assert.equal(runtime.deactivate("space-dev-proof"), true);
  assert.equal(runtime.getSnapshot().activations.length, 0);
}

{
  const runtime = createProfilePackRuntime({ packs: [developer] });
  assert.throws(
    () => runtime.activate({
      slug: "developer",
      version: 1,
      mode: "internal-proof",
      space: { id: "personal-space", kind: "personal" },
    }),
    /incompatible with the selected Space kind/,
  );
  assert.throws(
    () => runtime.activate({
      slug: "developer",
      version: 1,
      mode: "public",
      space: { id: "space-dev-proof", kind: "professional" },
    }),
    /limited to explicit internal proof/,
  );
}

{
  const privileged = structuredClone(developer);
  privileged.security.auto_grant_privileges = true;
  assert.throws(
    () => createProfilePackRuntime({ packs: [privileged] }),
    /cannot broaden privilege or signature policy/,
  );
}

{
  const cloudRequired = structuredClone(developer);
  cloudRequired.intelligence.external_provider_required = true;
  const runtime = createProfilePackRuntime({ packs: [cloudRequired] });
  assert.throws(
    () => runtime.activate({
      slug: "developer",
      version: 1,
      mode: "internal-proof",
      space: { id: "space-dev-proof", kind: "professional" },
    }),
    /cannot require external model egress/,
  );
}

console.log("PROFILE_PACK_RUNTIME=PASS");
