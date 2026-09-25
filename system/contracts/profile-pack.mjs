export const PROFILE_PACK_SCHEMA = "ordax.profile-pack/1";
export const PROFILE_PACK_RUNTIME_SCHEMA = "ordax.profile-pack-runtime/1";
export const PROFILE_PACK_ACTIVATION_SCHEMA = "ordax.profile-pack-activation/1";

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SPACE_KINDS = new Set(["personal", "work", "professional"]);
const PACK_STATES = new Set(["draft", "active", "retired"]);
const MEMORY_SCOPES = new Set(["device", "account", "space", "project", "session"]);

function objectValue(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
  return value;
}

function text(value, label, max = 160) {
  if (typeof value !== "string" || value.length < 1 || value.length > max || value.includes("\0")) {
    throw new TypeError(`${label} must be bounded text`);
  }
  return value;
}

function textArray(value, label, maxItems = 32) {
  if (!Array.isArray(value) || value.length > maxItems) {
    throw new TypeError(`${label} must be a bounded array`);
  }
  return Object.freeze(value.map((entry, index) => text(entry, `${label}[${index}]`)));
}

export function validateProfilePack(value, label = "Profile Pack") {
  const pack = objectValue(value, label);
  if (pack.$schema !== PROFILE_PACK_SCHEMA) throw new TypeError(`${label} schema is incompatible`);
  const slug = text(pack.slug, `${label} slug`, 80);
  if (!SLUG_PATTERN.test(slug)) throw new TypeError(`${label} slug is invalid`);
  if (!Number.isSafeInteger(pack.version) || pack.version < 1) throw new TypeError(`${label} version is invalid`);
  if (!PACK_STATES.has(pack.state)) throw new TypeError(`${label} state is invalid`);
  if (!SPACE_KINDS.has(pack.space_kind)) throw new TypeError(`${label} space kind is invalid`);

  const security = objectValue(pack.security, `${label} security`);
  for (const key of ["auto_grant_privileges", "allow_unsigned_apps", "generic_shell_implied"]) {
    if (typeof security[key] !== "boolean") throw new TypeError(`${label} security.${key} must be boolean`);
  }
  if (security.auto_grant_privileges || security.allow_unsigned_apps || security.generic_shell_implied) {
    throw new TypeError(`${label} cannot broaden privilege or signature policy`);
  }

  const intelligence = objectValue(pack.intelligence, `${label} intelligence`);
  const memoryScopes = textArray(intelligence.memory_scopes, `${label} memory scopes`, 8);
  if (memoryScopes.some((scope) => !MEMORY_SCOPES.has(scope))) {
    throw new TypeError(`${label} memory scope is invalid`);
  }
  if (typeof intelligence.external_provider_required !== "boolean") {
    throw new TypeError(`${label} external provider policy is invalid`);
  }

  const knowledge = objectValue(pack.knowledge, `${label} knowledge`);
  const sourceClasses = textArray(knowledge.source_classes, `${label} source classes`);
  const apps = textArray(pack.apps, `${label} apps`);
  const templates = textArray(pack.templates, `${label} templates`);

  return Object.freeze({
    schema: PROFILE_PACK_SCHEMA,
    slug,
    version: pack.version,
    state: pack.state,
    title: text(pack.title, `${label} title`, 120),
    category: text(pack.category, `${label} category`, 80),
    spaceKind: pack.space_kind,
    apps,
    templates,
    knowledge: Object.freeze({
      jurisdiction: pack.knowledge.jurisdiction === null ? null : text(pack.knowledge.jurisdiction, `${label} jurisdiction`, 80),
      sourceClasses,
      refreshPolicy: text(pack.knowledge.refresh_policy, `${label} refresh policy`, 80),
    }),
    intelligence: Object.freeze({
      memoryScopes,
      preferredPurpose: text(pack.intelligence.preferred_purpose, `${label} preferred purpose`, 80),
      externalProviderRequired: pack.intelligence.external_provider_required,
    }),
    security: Object.freeze({
      autoGrantPrivileges: false,
      allowUnsignedApps: false,
      genericShellImplied: false,
    }),
  });
}

export function validateProfilePackSpace(value, label = "Profile Pack Space") {
  const space = objectValue(value, label);
  const id = text(space.id, `${label} id`, 160);
  if (!SPACE_KINDS.has(space.kind)) throw new TypeError(`${label} kind is invalid`);
  return Object.freeze({ id, kind: space.kind });
}
