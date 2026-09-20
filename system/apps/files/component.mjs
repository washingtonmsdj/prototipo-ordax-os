import { defineComponentManifest } from "../../contracts/component-manifest.mjs";
import { FILES_VERSION } from "./version.mjs";

export const filesComponent = defineComponentManifest({
  id: "files",
  title: "Arquivos",
  kind: "app",
  version: FILES_VERSION,
  releaseMode: "bundled",
  criticality: "optional",
  failureDomain: "app",
  restartScope: "surface",
  healthMode: "surface",
  owner: "system/apps/files",
  dependencies: ["surface-shell"],
});
