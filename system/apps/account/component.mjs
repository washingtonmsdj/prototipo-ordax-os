import { defineComponentManifest } from "../../contracts/component-manifest.mjs";
import { ACCOUNT_VERSION } from "./version.mjs";

export const accountComponent = defineComponentManifest({
  id: "account",
  title: "Conta",
  kind: "app",
  version: ACCOUNT_VERSION,
  releaseMode: "bundled",
  criticality: "optional",
  failureDomain: "app",
  restartScope: "surface",
  healthMode: "surface",
  owner: "system/apps/account",
  dependencies: ["surface-shell"],
});
