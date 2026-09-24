import test from "node:test";
import assert from "node:assert/strict";

import {
  PROJECT_CLOUD_LINK_STORE_SCHEMA,
  createEmptyProjectCloudLinkState,
  validateProjectCloudLinkState,
} from "../system/contracts/project-cloud-link-store.mjs";
import {
  PROJECT_CLOUD_LINKS_SCHEMA,
  validateProjectCloudLink,
} from "../system/contracts/project-cloud-links.mjs";
import { PROJECT_STORE_SCHEMA, createEmptyProjectStoreState, validateProjectStoreState } from "../system/contracts/project-store.mjs";
import { createNativeProjectCloudLinkStore } from "../system/adapters/native/project-cloud-links.mjs";
import { createProjectCatalogRuntime } from "../system/services/files/projects.mjs";
import { createProjectCloudLinksRuntime } from "../system/services/projects/cloud-links.mjs";

const SPACE_A = "11111111-1111-4111-8111-111111111111";
const CLOUD_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const CLOUD_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function projectStore() {
  let state = createEmptyProjectStoreState();
  return {
    schema: PROJECT_STORE_SCHEMA,
    scope: "device",
    load: () => state,
    save(next) {
      state = validateProjectStoreState(next);
      return true;
    },
  };
}

function linkStore({ failSave = false, initial = null } = {}) {
  let state = initial === null
    ? createEmptyProjectCloudLinkState()
    : validateProjectCloudLinkState(initial);
  return {
    schema: PROJECT_CLOUD_LINK_STORE_SCHEMA,
    scope: "device",
    load: () => state,
    save(next) {
      state = validateProjectCloudLinkState(next);
      return !failSave;
    },
  };
}

function localStorageWindow() {
  const values = new Map();
  return {
    localStorage: {
      getItem(key) {
        return values.has(key) ? values.get(key) : null;
      },
      setItem(key, value) {
        values.set(key, String(value));
      },
    },
    values,
  };
}

test("local project remains fully valid without any cloud account or link", () => {
  const projects = createProjectCatalogRuntime({ store: projectStore(), now: () => 10 });
  projects.create({ name: "Offline", path: "/Documentos/Offline" });

  const before = projects.getSnapshot();
  const links = createProjectCloudLinksRuntime({ projects, now: () => 20 });

  assert.equal(links.schema, PROJECT_CLOUD_LINKS_SCHEMA);
  assert.equal(links.getSnapshot().persistence, "session");
  assert.deepEqual(links.getSnapshot().links, []);
  assert.deepEqual(projects.getSnapshot(), before);
  links.destroy();
});

test("cloud linking preserves local project id path and timestamps", () => {
  let clock = 100;
  const projects = createProjectCatalogRuntime({
    store: projectStore(),
    now: () => clock++,
  });
  projects.create({ name: "Projeto", path: "/Documentos/Projeto" });
  const before = projects.getSnapshot().projects[0];

  const links = createProjectCloudLinksRuntime({
    projects,
    store: linkStore(),
    now: () => 500,
  });
  const snapshot = links.link(before.id, { cloudProjectId: CLOUD_A, spaceId: SPACE_A });

  assert.equal(snapshot.persistence, "device");
  assert.equal(snapshot.links[0].localProjectId, before.id);
  assert.equal(snapshot.links[0].cloudProjectId, CLOUD_A);
  assert.equal(snapshot.links[0].spaceId, SPACE_A);
  assert.deepEqual(projects.getSnapshot().projects[0], before);
  assert.equal(Object.hasOwn(snapshot.links[0], "path"), false);
  links.destroy();
});

test("relinking requires explicit unlink and one cloud project cannot bind twice", () => {
  const projects = createProjectCatalogRuntime({ store: projectStore(), now: () => 1 });
  projects.create({ name: "A", path: "/A" });
  projects.create({ name: "B", path: "/B" });

  const links = createProjectCloudLinksRuntime({
    projects,
    store: linkStore(),
    now: () => 2,
  });
  links.link("project-1", { cloudProjectId: CLOUD_A, spaceId: SPACE_A });

  assert.throws(
    () => links.link("project-1", { cloudProjectId: CLOUD_B, spaceId: SPACE_A }),
    /unlink it before relinking/,
  );
  assert.throws(
    () => links.link("project-2", { cloudProjectId: CLOUD_A, spaceId: SPACE_A }),
    /already linked on this device/,
  );

  links.unlink("project-1");
  const relinked = links.link("project-1", {
    cloudProjectId: CLOUD_B,
    spaceId: SPACE_A,
  });
  assert.equal(relinked.links[0].cloudProjectId, CLOUD_B);
  links.destroy();
});

test("linking an unknown local project is rejected before state changes", () => {
  const projects = createProjectCatalogRuntime({ store: projectStore(), now: () => 1 });
  const links = createProjectCloudLinksRuntime({
    projects,
    store: linkStore(),
    now: () => 2,
  });

  assert.throws(
    () => links.link("project-1", { cloudProjectId: CLOUD_A, spaceId: SPACE_A }),
    /not registered/,
  );
  assert.deepEqual(links.getSnapshot().links, []);
  links.destroy();
});

test("removing a local project prunes only its local cloud link", () => {
  const projects = createProjectCatalogRuntime({ store: projectStore(), now: () => 1 });
  projects.create({ name: "A", path: "/A" });
  const links = createProjectCloudLinksRuntime({
    projects,
    store: linkStore(),
    now: () => 2,
  });
  links.link("project-1", { cloudProjectId: CLOUD_A, spaceId: SPACE_A });

  projects.remove("project-1");

  assert.deepEqual(links.getSnapshot().links, []);
  assert.deepEqual(projects.getSnapshot().projects, []);
  links.destroy();
});

test("link persistence failure degrades to session without touching local project", () => {
  const projects = createProjectCatalogRuntime({ store: projectStore(), now: () => 1 });
  projects.create({ name: "Local", path: "/Local" });
  const before = projects.getSnapshot();
  const links = createProjectCloudLinksRuntime({
    projects,
    store: linkStore({ failSave: true }),
    now: () => 2,
  });

  const snapshot = links.link("project-1", {
    cloudProjectId: CLOUD_A,
    spaceId: SPACE_A,
  });
  assert.equal(snapshot.persistence, "session");
  assert.equal(snapshot.links.length, 1);
  assert.deepEqual(projects.getSnapshot(), before);
  links.destroy();
});

test("native cloud link store persists identity only, never a local filesystem path", () => {
  const windowRef = localStorageWindow();
  const store = createNativeProjectCloudLinkStore(windowRef);
  store.save({
    links: [{
      localProjectId: "project-1",
      cloudProjectId: CLOUD_A,
      spaceId: SPACE_A,
      linkedAt: 10,
    }],
  });

  const raw = windowRef.values.get("ordax.native.project-cloud-links.v1");
  assert.match(raw, /project-1/);
  assert.match(raw, /aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/);
  assert.equal(raw.includes("/Documentos"), false);

  const restored = createNativeProjectCloudLinkStore(windowRef);
  assert.equal(restored.load().links[0].cloudProjectId, CLOUD_A);
});

test("cloud identities are bounded UUIDs and reject path-like identifiers", () => {
  assert.throws(() => validateProjectCloudLink({
    localProjectId: "project-1",
    cloudProjectId: "/Documentos/Projeto",
    spaceId: SPACE_A,
    linkedAt: 1,
  }), /UUID/);
});
