import assert from "node:assert/strict";
import test from "node:test";

import {
  PROJECT_REPOSITORY_CONNECTIONS_SCHEMA,
  assertProjectRepositoryConnectionsPort,
  validateProjectRepositoryConnection,
  validateProjectRepositoryConnectionsSnapshot,
} from "../system/contracts/project-repository-connections.mjs";

const SPACE_ID = "11111111-1111-4111-8111-111111111111";
const PROJECT_ID = "22222222-2222-4222-8222-222222222222";

function connection(overrides = {}) {
  return {
    connectionId: "33333333-3333-4333-8333-333333333333",
    spaceId: SPACE_ID,
    projectId: PROJECT_ID,
    provider: "github",
    repositoryId: "1371063347",
    repositoryFullName: "washingtonmsdj/prototipo-ordax-os",
    defaultBranch: "main",
    accessMode: "read",
    state: "active",
    ...overrides,
  };
}

function snapshot(connections = [connection()]) {
  return {
    schema: PROJECT_REPOSITORY_CONNECTIONS_SCHEMA,
    spaceId: SPACE_ID,
    connections,
  };
}

test("selected GitHub repository projection is bounded and keeps ids precision-safe", () => {
  const normalized = validateProjectRepositoryConnectionsSnapshot(snapshot());
  assert.equal(normalized.spaceId, SPACE_ID);
  assert.equal(normalized.connections[0].repositoryId, "1371063347");
  assert.equal(normalized.connections[0].repositoryFullName, "washingtonmsdj/prototipo-ordax-os");
  assert.equal(Object.isFrozen(normalized.connections), true);
});

test("provider installation identity and tokens cannot cross the Surface projection", () => {
  assert.throws(
    () => validateProjectRepositoryConnection({
      ...connection(),
      installationId: "123",
    }),
    /fields are incompatible/,
  );
  assert.throws(
    () => validateProjectRepositoryConnection({
      ...connection(),
      accessToken: "secret",
    }),
    /fields are incompatible/,
  );
  assert.throws(
    () => validateProjectRepositoryConnection({
      ...connection(),
      externalAccountId: "provider-account",
    }),
    /fields are incompatible/,
  );
});

test("repository ids must be positive decimal strings instead of unsafe JavaScript numbers", () => {
  assert.throws(
    () => validateProjectRepositoryConnection({ ...connection(), repositoryId: 1371063347 }),
    /positive decimal string/,
  );
  assert.throws(
    () => validateProjectRepositoryConnection({ ...connection(), repositoryId: "0" }),
    /positive decimal string/,
  );
});

test("snapshot rejects cross-Space rows and duplicate project repository selections", () => {
  assert.throws(
    () => validateProjectRepositoryConnectionsSnapshot(snapshot([
      connection(),
      connection({
        connectionId: "44444444-4444-4444-8444-444444444444",
        spaceId: "55555555-5555-4555-8555-555555555555",
        repositoryId: "2",
        repositoryFullName: "example/other",
      }),
    ])),
    /belong to the snapshot Space/,
  );

  assert.throws(
    () => validateProjectRepositoryConnectionsSnapshot(snapshot([
      connection(),
      connection({ connectionId: "44444444-4444-4444-8444-444444444444" }),
    ])),
    /cannot be selected twice/,
  );
});

test("repository connection port is structurally read-only", () => {
  const readOnlyPort = Object.freeze({
    schema: PROJECT_REPOSITORY_CONNECTIONS_SCHEMA,
    getSnapshot: () => snapshot(),
    subscribe: () => () => {},
  });
  assert.equal(assertProjectRepositoryConnectionsPort(readOnlyPort), readOnlyPort);

  for (const method of ["connect", "disconnect", "execute", "link", "mutate", "unlink", "update"]) {
    assert.throws(
      () => assertProjectRepositoryConnectionsPort({
        ...readOnlyPort,
        [method]: () => {},
      }),
      new RegExp(`must not expose ${method}`),
    );
  }
});
