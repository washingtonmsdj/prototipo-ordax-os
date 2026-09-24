import { defineComponentManifest } from "../../contracts/component-manifest.mjs";
import { PROJECTS_VERSION } from "./version.mjs";

export const projectsComponent = defineComponentManifest({
  id: "projects",
  title: "Projetos",
  kind: "app",
  version: PROJECTS_VERSION,
  releaseMode: "git-app",
  criticality: "optional",
  failureDomain: "app",
  restartScope: "component",
  healthMode: "runtime",
  owner: "system/apps/projects",
  dependencies: ["surface-shell"],
});
