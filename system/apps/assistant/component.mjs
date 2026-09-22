import { defineComponentManifest } from "../../contracts/component-manifest.mjs";
import { ASSISTANT_VERSION } from "./version.mjs";

export const assistantComponent = defineComponentManifest({
  id: "assistant",
  title: "Assistente",
  kind: "app",
  version: ASSISTANT_VERSION,
  releaseMode: "bundled",
  criticality: "optional",
  failureDomain: "app",
  restartScope: "surface",
  healthMode: "surface",
  owner: "system/apps/assistant",
  dependencies: ["surface-shell"],
});
