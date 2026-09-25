import {
  REPOSITORY_CONNECTIONS_SCHEMA,
  validateRepositoryConnectionRow,
  validateRepositoryConnections,
} from "../../contracts/repository-connections.mjs";

function uuid(value, label) {
  if (typeof value !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new TypeError(`${label} must be a UUID`);
  }
  return value.toLowerCase();
}

export function createRepositoryConnectionsCatalog({ rows = [] } = {}) {
  if (!Array.isArray(rows)) throw new TypeError("Repository connection rows must be an array");
  const entries = validateRepositoryConnections(rows.map(validateRepositoryConnectionRow));
  const byId = new Map(entries.map((entry) => [entry.connectionId, entry]));

  return Object.freeze({
    schema: REPOSITORY_CONNECTIONS_SCHEMA,
    listForSpace(spaceIdValue) {
      const spaceId = uuid(spaceIdValue, "Repository connection Space id");
      return Object.freeze(entries.filter((entry) => entry.spaceId === spaceId));
    },
    get(connectionIdValue) {
      const connectionId = uuid(connectionIdValue, "Repository connection id");
      return byId.get(connectionId) ?? null;
    },
  });
}
