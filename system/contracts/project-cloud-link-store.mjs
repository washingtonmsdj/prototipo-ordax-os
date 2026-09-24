import {
  validateProjectCloudLinkEntries,
} from "./project-cloud-links.mjs";

export const PROJECT_CLOUD_LINK_STORE_SCHEMA = "ordax.project-cloud-link-store/1";

const STORE_SCOPES = new Set(["device", "session"]);

export function createEmptyProjectCloudLinkState() {
  return Object.freeze({ links: Object.freeze([]) });
}

export function validateProjectCloudLinkState(value) {
  if (value === undefined || value === null) {
    return createEmptyProjectCloudLinkState();
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Project cloud link store state must be an object");
  }
  return Object.freeze({
    links: validateProjectCloudLinkEntries(value.links),
  });
}

export function assertProjectCloudLinkStore(store) {
  if (
    !store
    || typeof store !== "object"
    || store.schema !== PROJECT_CLOUD_LINK_STORE_SCHEMA
  ) {
    throw new TypeError("A compatible project cloud link store is required");
  }
  if (!STORE_SCOPES.has(store.scope)) {
    throw new TypeError("Project cloud link store scope must be device or session");
  }
  if (typeof store.load !== "function" || typeof store.save !== "function") {
    throw new TypeError("Project cloud link store must implement load() and save(state)");
  }
  validateProjectCloudLinkState(store.load());
  return store;
}
