import { defineComponentManifest } from "../../contracts/component-manifest.mjs";
import { SETTINGS_VERSION } from "./version.mjs";

export const settingsComponent = defineComponentManifest({
  id: "settings",
  title: "Ajustes",
  kind: "app",
  version: SETTINGS_VERSION,
  releaseMode: "bundled",
  criticality: "system",
  failureDomain: "app",
  restartScope: "surface",
  healthMode: "surface",
  owner: "system/apps/settings",
  dependencies: ["surface-shell", "network-service"],
});
