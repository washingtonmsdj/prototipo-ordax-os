import {
  validateComponentManagerSnapshot,
  validateComponentVersion,
} from "../../contracts/component-manager.mjs";

const UPDATE_CHANNELS = Object.freeze({
  "base-ab": Object.freeze({
    id: "system-base",
    label: "Base A/B do OrdaX",
    scope: "system",
  }),
  bundled: Object.freeze({
    id: "system-bundle",
    label: "Atualiza junto com o OrdaX",
    scope: "system",
  }),
  "git-app": Object.freeze({
    id: "development-git",
    label: "App via Git (desenvolvimento)",
    scope: "app",
  }),
  "component-slot": Object.freeze({
    id: "independent-component",
    label: "Atualização independente do app",
    scope: "app",
  }),
});

export function appVersionStage(version) {
  const validated = validateComponentVersion(version);
  const core = validated.split("-", 1)[0];
  const major = Number.parseInt(core.split(".", 1)[0], 10);
  return major === 0 || validated.includes("-") ? "beta" : "stable";
}

function presentComponent(component) {
  const { manifest, state, independentUpdate } = component;
  const channel = UPDATE_CHANNELS[manifest.releaseMode];
  if (!channel) {
    throw new TypeError(`Unsupported component update mode: ${manifest.releaseMode}`);
  }
  const isApp = manifest.kind === "app";
  return Object.freeze({
    id: manifest.id,
    title: manifest.title,
    kind: manifest.kind,
    version: state.currentVersion,
    versionStage: isApp ? appVersionStage(state.currentVersion) : null,
    releaseMode: manifest.releaseMode,
    updateChannel: channel,
    independentUpdate,
    previousVersion: state.previousVersion,
    pendingVersion: state.pendingVersion,
    rejectedVersion: state.rejectedVersion,
    health: state.currentHealth,
  });
}

export function createComponentUpdateScopes(snapshotValue) {
  const snapshot = validateComponentManagerSnapshot(snapshotValue);
  const system = [];
  const applications = [];

  for (const component of snapshot.components) {
    const presented = presentComponent(component);
    if (component.manifest.kind === "app" && component.manifest.id !== "system") {
      applications.push(presented);
    } else {
      system.push(presented);
    }
  }

  return Object.freeze({
    persistence: snapshot.persistence,
    revision: snapshot.revision,
    system: Object.freeze(system),
    applications: Object.freeze(applications),
  });
}
