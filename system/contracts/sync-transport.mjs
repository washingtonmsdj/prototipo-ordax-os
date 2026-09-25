export const SYNC_TRANSPORT_SCHEMA = "ordax.sync-transport/1";

export function assertSyncTransportPort(port) {
  if (!port || typeof port !== "object" || port.schema !== SYNC_TRANSPORT_SCHEMA) {
    throw new TypeError("A compatible sync transport is required");
  }
  if (
    typeof port.snapshot !== "function"
    || typeof port.pullChanges !== "function"
    || typeof port.applyMutation !== "function"
  ) {
    throw new TypeError("Sync transport must implement snapshot(), pullChanges() and applyMutation()");
  }
  return port;
}
