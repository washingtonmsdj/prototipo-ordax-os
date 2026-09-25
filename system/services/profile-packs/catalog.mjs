import {
  PROFILE_PACK_CATALOG_SCHEMA,
  validateProfilePackCatalogEntry,
} from "../../contracts/profile-pack-catalog.mjs";

function identity(entry) {
  return `${entry.slug}@${entry.version}`;
}

export function createProfilePackCatalog({ rows = [] } = {}) {
  if (!Array.isArray(rows) || rows.length > 128) {
    throw new TypeError("Profile Pack catalog requires a bounded row set");
  }

  const entries = [];
  const identities = new Set();
  for (const row of rows) {
    const entry = validateProfilePackCatalogEntry(row);
    const key = identity(entry);
    if (identities.has(key)) throw new Error(`Duplicate Profile Pack catalog entry ${key}`);
    identities.add(key);
    entries.push(entry);
  }
  entries.sort((left, right) => {
    const title = left.title.localeCompare(right.title, "en", { sensitivity: "base" });
    if (title !== 0) return title;
    const slug = left.slug.localeCompare(right.slug);
    if (slug !== 0) return slug;
    return left.version - right.version;
  });
  const frozenEntries = Object.freeze(entries);

  return Object.freeze({
    schema: PROFILE_PACK_CATALOG_SCHEMA,
    list() {
      return frozenEntries;
    },
    get(slug, version) {
      if (typeof slug !== "string" || !Number.isSafeInteger(version)) {
        throw new TypeError("Profile Pack catalog lookup requires exact slug and version");
      }
      return frozenEntries.find((entry) => entry.slug === slug && entry.version === version) ?? null;
    },
  });
}
