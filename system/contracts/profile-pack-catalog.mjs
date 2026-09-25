export const PROFILE_PACK_CATALOG_SCHEMA = "ordax.profile-pack-catalog/1";
export const PROFILE_PACK_CATALOG_ENTRY_SCHEMA = "ordax.profile-pack-catalog-entry/1";

const SLUG_PATTERN = /^[a-z0-9][a-z0-9-]{1,79}$/;
const SPACE_KINDS = new Set(["personal", "work", "professional"]);

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

function boundedTextArray(value, label, maxItems = 32, maxChars = 160) {
  if (!Array.isArray(value) || value.length > maxItems) {
    throw new TypeError(`${label} must be a bounded array`);
  }
  return Object.freeze(value.map((entry, index) => boundedText(entry, `${label}[${index}]`, maxChars)));
}

export function validateProfilePackCatalogEntry(value, label = "Profile Pack catalog entry") {
  const row = objectValue(value, label);
  const slug = boundedText(row.slug, `${label} slug`, 80);
  if (!SLUG_PATTERN.test(slug)) throw new TypeError(`${label} slug is invalid`);
  if (!Number.isSafeInteger(row.version) || row.version < 1) throw new TypeError(`${label} version is invalid`);
  if (row.state !== "active") throw new Error(`${label} must be active`);
  const title = boundedText(row.title, `${label} title`, 120);
  const category = boundedText(row.category, `${label} category`, 80);
  const manifest = objectValue(row.manifest, `${label} manifest`);
  const spaceKind = manifest.space_kind;
  if (!SPACE_KINDS.has(spaceKind)) throw new TypeError(`${label} space kind is invalid`);
  const apps = boundedTextArray(manifest.apps ?? [], `${label} apps`, 32, 120);
  const templates = boundedTextArray(manifest.templates ?? [], `${label} templates`, 32, 120);
  const intelligence = objectValue(manifest.intelligence ?? {}, `${label} intelligence`);
  const preferredPurpose = intelligence.preferred_purpose == null
    ? null
    : boundedText(intelligence.preferred_purpose, `${label} preferred purpose`, 80);
  if (
    intelligence.external_provider_required !== undefined
    && typeof intelligence.external_provider_required !== "boolean"
  ) {
    throw new TypeError(`${label} external provider policy is invalid`);
  }

  return Object.freeze({
    schema: PROFILE_PACK_CATALOG_ENTRY_SCHEMA,
    slug,
    version: row.version,
    title,
    category,
    spaceKind,
    apps,
    templates,
    intelligence: Object.freeze({
      preferredPurpose,
      externalProviderRequired: intelligence.external_provider_required === true,
    }),
  });
}
