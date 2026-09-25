export const PROJECT_REPOSITORY_CONNECTIONS_SCHEMA = "ordax.project-repository-connections/1";
export const MAX_PROJECT_REPOSITORY_CONNECTIONS = 128;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const REPOSITORY_ID_RE = /^[1-9][0-9]{0,19}$/;
const ACCESS_MODES = new Set(["read", "read-write"]);
const STATES = new Set(["active", "revoked", "error"]);
const FORBIDDEN_PORT_METHODS = [
  "connect",
  "disconnect",
  "execute",
  "link",
  "mutate",
  "unlink",
  "update",
];

function exactKeys(value, expected, label) {
  const actual = Object.keys(value).sort();
  const normalizedExpected = [...expected].sort();
  if (
    actual.length !== normalizedExpected.length
    || actual.some((key, index) => key !== normalizedExpected[index])
  ) {
    throw new TypeError(`${label} fields are incompatible`);
  }
}

function validateUuid(value, label) {
  if (typeof value !== "string" || !UUID_RE.test(value)) {
    throw new TypeError(`${label} must be a UUID`);
  }
  return value.toLowerCase();
}

function boundedText(value, label, max) {
  if (typeof value !== "string" || value.includes("\0")) {
    throw new TypeError(`${label} must be a string`);
  }
  const normalized = value.trim();
  if (!normalized || normalized.length > max || /[\r\n]/.test(normalized)) {
    throw new TypeError(`${label} is outside its allowed bounds`);
  }
  return normalized;
}

function validateRepositoryId(value) {
  if (typeof value !== "string" || !REPOSITORY_ID_RE.test(value)) {
    throw new TypeError("Repository id must be a positive decimal string");
  }
  return value;
}

function validateRepositoryFullName(value) {
  const normalized = boundedText(value, "Repository full name", 200);
  const parts = normalized.split("/");
  if (
    parts.length !== 2
    || parts.some((part) => !part || part === "." || part === "..")
    || parts.some((part) => /[\s\\]/.test(part))
  ) {
    throw new TypeError("Repository full name must be an owner/name pair");
  }
  return normalized;
}

export function validateProjectRepositoryConnection(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Project repository connection must be an object");
  }
  exactKeys(
    value,
    [
      "connectionId",
      "spaceId",
      "projectId",
      "provider",
      "repositoryId",
      "repositoryFullName",
      "defaultBranch",
      "accessMode",
      "state",
    ],
    "Project repository connection",
  );
  if (value.provider !== "github") {
    throw new TypeError("Project repository connection provider is unsupported");
  }
  if (!ACCESS_MODES.has(value.accessMode)) {
    throw new TypeError("Project repository connection access mode is invalid");
  }
  if (!STATES.has(value.state)) {
    throw new TypeError("Project repository connection state is invalid");
  }

  return Object.freeze({
    connectionId: validateUuid(value.connectionId, "Connection id"),
    spaceId: validateUuid(value.spaceId, "Space id"),
    projectId: validateUuid(value.projectId, "Project id"),
    provider: "github",
    repositoryId: validateRepositoryId(value.repositoryId),
    repositoryFullName: validateRepositoryFullName(value.repositoryFullName),
    defaultBranch: boundedText(value.defaultBranch, "Default branch", 255),
    accessMode: value.accessMode,
    state: value.state,
  });
}

export function validateProjectRepositoryConnectionsSnapshot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Project repository connections snapshot must be an object");
  }
  exactKeys(value, ["schema", "spaceId", "connections"], "Project repository connections snapshot");
  if (value.schema !== PROJECT_REPOSITORY_CONNECTIONS_SCHEMA) {
    throw new TypeError("Project repository connections snapshot schema is incompatible");
  }
  const spaceId = validateUuid(value.spaceId, "Snapshot space id");
  if (!Array.isArray(value.connections) || value.connections.length > MAX_PROJECT_REPOSITORY_CONNECTIONS) {
    throw new TypeError("Project repository connections must be a bounded array");
  }

  const connections = value.connections.map(validateProjectRepositoryConnection);
  if (connections.some((connection) => connection.spaceId !== spaceId)) {
    throw new TypeError("Every repository connection must belong to the snapshot Space");
  }
  if (new Set(connections.map((connection) => connection.connectionId)).size !== connections.length) {
    throw new TypeError("Project repository connection ids must be unique");
  }
  const selectionKeys = connections.map(
    (connection) => `${connection.projectId}\0${connection.provider}\0${connection.repositoryId}`,
  );
  if (new Set(selectionKeys).size !== selectionKeys.length) {
    throw new TypeError("The same repository cannot be selected twice for one project");
  }

  return Object.freeze({
    schema: PROJECT_REPOSITORY_CONNECTIONS_SCHEMA,
    spaceId,
    connections: Object.freeze(connections),
  });
}

export function assertProjectRepositoryConnectionsPort(port) {
  if (
    !port
    || typeof port !== "object"
    || port.schema !== PROJECT_REPOSITORY_CONNECTIONS_SCHEMA
  ) {
    throw new TypeError("A compatible project-repository-connections port is required");
  }
  if (typeof port.getSnapshot !== "function" || typeof port.subscribe !== "function") {
    throw new TypeError("Project repository connections port must implement getSnapshot() and subscribe()");
  }
  for (const method of FORBIDDEN_PORT_METHODS) {
    if (method in port) {
      throw new TypeError(`Project repository connections port must not expose ${method}()`);
    }
  }
  validateProjectRepositoryConnectionsSnapshot(port.getSnapshot());
  return port;
}
