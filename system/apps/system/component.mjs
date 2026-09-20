import { defineComponentManifest } from "../../contracts/component-manifest.mjs";
import { SYSTEM_APP_VERSION } from "./version.mjs";

export const systemComponent = defineComponentManifest({
  id: "system",
  title: "Sistema",
  kind: "app",
  version: SYSTEM_APP_VERSION,
  releaseMode: "bundled",
  criticality: "system",
  failureDomain: "app",
  restartScope: "surface",
  healthMode: "surface",
  owner: "system/apps/system",
  dependencies: ["surface-shell", "update-service"],
});
