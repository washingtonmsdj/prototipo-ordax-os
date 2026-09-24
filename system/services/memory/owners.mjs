import {
  IDENTITY_SESSION_SCHEMA,
  validateIdentitySessionSnapshot,
} from "../../contracts/identity-session.mjs";
import { validateMemoryOwner } from "../../contracts/memory.mjs";

export const DEVICE_MEMORY_OWNER = Object.freeze(validateMemoryOwner({
  ownerKind: "device",
  ownerId: null,
}));

export function memoryOwnersForIdentitySession(snapshotValue = null) {
  if (snapshotValue === null || snapshotValue === undefined) {
    return Object.freeze([DEVICE_MEMORY_OWNER]);
  }
  const snapshot = validateIdentitySessionSnapshot(snapshotValue);
  const owners = [DEVICE_MEMORY_OWNER];
  if (snapshot.state === "signed-in") {
    owners.push(validateMemoryOwner({
      ownerKind: "account",
      ownerId: snapshot.subjectId,
    }));
  }
  return Object.freeze(owners);
}

export function memoryOwnersForIdentityPort(port = null) {
  if (port === null || port === undefined) {
    return Object.freeze([DEVICE_MEMORY_OWNER]);
  }
  if (
    !port
    || typeof port !== "object"
    || port.schema !== IDENTITY_SESSION_SCHEMA
    || typeof port.getSnapshot !== "function"
  ) {
    throw new TypeError("Compatible identity-session port is required");
  }
  return memoryOwnersForIdentitySession(port.getSnapshot());
}
