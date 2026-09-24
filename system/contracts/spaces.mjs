export const SPACES_PORT_SCHEMA = "ordax.spaces/1";
export const PROFILE_PACKS_PORT_SCHEMA = "ordax.profile-packs/1";

const SPACE_KINDS = new Set(["personal", "work", "professional"]);
const MEMBER_ROLES = new Set(["owner", "admin", "member", "viewer"]);
const SPACE_STATES = new Set(["active", "archived"]);

function boundedText(value, label, max = 160) {
  if (typeof value !== "string" || value.includes("\0")) {
    throw new TypeError(`${label} must be a string`);
  }
  const normalized = value.trim();
  if (!normalized || normalized.length > max) {
    throw new TypeError(`${label} is outside its allowed bounds`);
  }
  return normalized;
}

export function validateSpace(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Space must be an object");
  }
  if (!SPACE_KINDS.has(value.kind) || !SPACE_STATES.has(value.state ?? "active")) {
    throw new TypeError("Space kind/state is invalid");
  }
  return Object.freeze({
    schema: SPACES_PORT_SCHEMA,
    id: boundedText(value.id, "Space id", 160),
    name: boundedText(value.name, "Space name", 120),
    kind: value.kind,
    state: value.state ?? "active",
    ownerId: boundedText(value.ownerId, "Space owner id", 160),
    profilePack: value.profilePack == null
      ? null
      : boundedText(value.profilePack, "Profile pack", 160),
  });
}

export function validateSpaceMembership(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Space membership must be an object");
  }
  if (!MEMBER_ROLES.has(value.role)) {
    throw new TypeError("Space membership role is invalid");
  }
  return Object.freeze({
    spaceId: boundedText(value.spaceId, "Membership space id", 160),
    userId: boundedText(value.userId, "Membership user id", 160),
    role: value.role,
  });
}

export function validateProfilePack(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Profile pack must be an object");
  }
  if (!Number.isSafeInteger(value.version) || value.version < 1) {
    throw new TypeError("Profile pack version is invalid");
  }
  if (value.autoGrantPrivileges === true || value.allowUnsignedApps === true) {
    throw new TypeError("Profile pack cannot bypass authorization or package trust");
  }
  return Object.freeze({
    schema: PROFILE_PACKS_PORT_SCHEMA,
    slug: boundedText(value.slug, "Profile pack slug", 96),
    version: value.version,
    title: boundedText(value.title, "Profile pack title", 120),
    category: boundedText(value.category, "Profile pack category", 80),
    autoGrantPrivileges: false,
    allowUnsignedApps: false,
  });
}
