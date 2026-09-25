export const REPOSITORY_CONNECTIONS_SCHEMA = "ordax.repository-connections/1";
export const REPOSITORY_CONNECTION_SCHEMA = "ordax.repository-connection/1";
export const MAX_REPOSITORY_CONNECTIONS = 128;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const DECIMAL_ID_RE = /^[1-9][0-9]{0,19}$/;
const REPOSITORY_NAME_RE = /^[^\s/]+\/[^\s/]+$/;
const ACCESS_MODES = new Set(["read", "read-write"]);
const SURFACE_STATES = new Set(["active", "error"]);

function objectValue(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
  return value;
}

function boundedText(value, label, max) {
  if (typeof value !== "string" || value.length < 1 || value.length > max || value.includes("\0")) {
    throw new TypeError(`${label} must be bounded text`);
  }
  return value;
}

function uuid(value, label) {
  if (typeof value !== "string" || !UUID_RE.test(value)) {
    throw new TypeError(`${label} must be a UUID`);
  }
  return value.toLowerCase();
}

function decimalId(value, label) {
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || value < 1) throw new TypeError(`${label} is invalid`);
    return String(value);
  }
  if (typeof value !== "string" || !DECIMAL_ID_RE.test(value)) {
    throw new TypeError(`${label} is invalid`);
  }
  return value;
}

function repositoryFullName(value, label) {
  const normalized = boundedText(value, label, 200);
  if (!REPOSITORY_NAME_RE.test(normalized)) {
    throw new TypeError(`${label} must identify one selected owner/repository`);
  }
  return normalized;
}

function projection(fields) {
  return Object.freeze({
    schema: REPOSITORY_CONNECTION_SCHEMA,
    connectionId: fields.connectionId,
    spaceId: fields.spaceId,
    provider: "github",
    repositoryId: fields.repositoryId,
    repositoryFullName: fields.repositoryFullName,
    defaultBranch: fields.defaultBranch,
    accessMode: fields.accessMode,
    state: fields.state,
    selection: "explicit-repository",
    mutationAuthority: "none",
    credentialExposure: "none",
  });
}

export function validateRepositoryConnectionRow(value, label = "Repository connection row") {
  const row = objectValue(value, label);
  if (row.provider !== "github") throw new TypeError(`${label} provider is unsupported`);
  const connectionId = uuid(row.connection_id, `${label} connection_id`);
  const spaceId = uuid(row.space_id, `${label} space_id`);
  const repositoryId = decimalId(row.repository_id, `${label} repository_id`);
  const fullName = repositoryFullName(row.repository_full_name, `${label} repository_full_name`);
  const defaultBranch = row.default_branch == null
    ? null
    : boundedText(row.default_branch, `${label} default_branch`, 255);
  if (!ACCESS_MODES.has(row.access_mode)) throw new TypeError(`${label} access_mode is invalid`);
  if (!SURFACE_STATES.has(row.state)) {
    throw new Error(`${label} must be active or error; revoked connections are not Surface-visible`);
  }
  return projection({
    connectionId,
    spaceId,
    repositoryId,
    repositoryFullName: fullName,
    defaultBranch,
    accessMode: row.access_mode,
    state: row.state,
  });
}

export function validateRepositoryConnection(value, label = "Repository connection") {
  const entry = objectValue(value, label);
  if (entry.schema !== REPOSITORY_CONNECTION_SCHEMA) {
    throw new TypeError(`${label} schema is incompatible`);
  }
  if (entry.provider !== "github") throw new TypeError(`${label} provider is unsupported`);
  if (entry.selection !== "explicit-repository") throw new TypeError(`${label} selection is invalid`);
  if (entry.mutationAuthority !== "none") throw new TypeError(`${label} cannot grant mutation authority`);
  if (entry.credentialExposure !== "none") throw new TypeError(`${label} cannot expose credentials`);
  const connectionId = uuid(entry.connectionId, `${label} connectionId`);
  const spaceId = uuid(entry.spaceId, `${label} spaceId`);
  const repositoryId = decimalId(entry.repositoryId, `${label} repositoryId`);
  const fullName = repositoryFullName(entry.repositoryFullName, `${label} repositoryFullName`);
  const defaultBranch = entry.defaultBranch == null
    ? null
    : boundedText(entry.defaultBranch, `${label} defaultBranch`, 255);
  if (!ACCESS_MODES.has(entry.accessMode)) throw new TypeError(`${label} accessMode is invalid`);
  if (!SURFACE_STATES.has(entry.state)) throw new TypeError(`${label} state is invalid`);
  return projection({
    connectionId,
    spaceId,
    repositoryId,
    repositoryFullName: fullName,
    defaultBranch,
    accessMode: entry.accessMode,
    state: entry.state,
  });
}

export function validateRepositoryConnections(value) {
  if (!Array.isArray(value) || value.length > MAX_REPOSITORY_CONNECTIONS) {
    throw new TypeError(`Repository connections must contain at most ${MAX_REPOSITORY_CONNECTIONS} entries`);
  }
  const entries = Object.freeze(value.map((entry, index) =>
    validateRepositoryConnection(entry, `Repository connection[${index}]`)));
  if (new Set(entries.map((entry) => entry.connectionId)).size !== entries.length) {
    throw new TypeError("Repository connection ids must be unique");
  }
  if (new Set(entries.map((entry) => `${entry.spaceId}:${entry.repositoryId}`)).size !== entries.length) {
    throw new TypeError("A repository may be selected only once per Space");
  }
  return entries;
}

export function assertRepositoryConnectionsPort(port) {
  if (!port || typeof port !== "object" || port.schema !== REPOSITORY_CONNECTIONS_SCHEMA) {
    throw new TypeError("A compatible repository-connections port is required");
  }
  for (const method of ["listForSpace", "get"]) {
    if (typeof port[method] !== "function") {
      throw new TypeError(`Repository connections port must implement ${method}()`);
    }
  }
  if ("connect" in port || "disconnect" in port || "mutate" in port) {
    throw new TypeError("Surface repository-connections port must be read-only");
  }
  return port;
}
