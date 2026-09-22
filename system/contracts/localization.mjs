export const LOCALIZATION_SCHEMA = "ordax.localization/1";

export function assertLocalizationPort(port) {
  if (!port || typeof port !== "object" || port.schema !== LOCALIZATION_SCHEMA) {
    throw new TypeError("A compatible localization port is required");
  }
  for (const method of ["getLocale", "translate", "subscribe"]) {
    if (typeof port[method] !== "function") {
      throw new TypeError(`Localization port must implement ${method}()`);
    }
  }
  const locale = port.getLocale();
  if (typeof locale !== "string" || !locale) {
    throw new TypeError("Localization port must expose a non-empty locale");
  }
  return port;
}
