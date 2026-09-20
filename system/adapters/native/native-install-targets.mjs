import {
  NATIVE_INSTALL_TARGETS_PORT_SCHEMA,
  assertNativeInstallTargetsPort,
  validateNativeInstallTargetsSnapshot,
} from "../../contracts/native-install-targets.mjs";

const SESSION_ENDPOINT = "/__ordax/native/session";
const TARGETS_ENDPOINT = "/__ordax/native/native-install-targets";
const TOKEN_HEADER = "X-OrdaX-Native-Install-Token";

async function readInstallSession(windowRef) {
  const response = await windowRef.fetch(SESSION_ENDPOINT, {
    method: "GET",
    cache: "no-store",
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(`Native install session failed: ${response.status}`);
  }
  const payload = await response.json();
  if (payload.productMode !== "usb") {
    throw new Error("Native install target discovery is available only in OrdaX USB mode");
  }
  if (
    payload.nativeInstallAvailable !== true
    || typeof payload.nativeInstallToken !== "string"
    || payload.nativeInstallToken.length < 16
  ) {
    throw new Error("Native install target discovery is unavailable");
  }
  return payload.nativeInstallToken;
}

export async function createNativeInstallTargets(windowRef = globalThis.window) {
  if (!windowRef || typeof windowRef.fetch !== "function") {
    throw new TypeError("Native install targets adapter requires window.fetch");
  }
  const token = await readInstallSession(windowRef);
  const port = {
    schema: NATIVE_INSTALL_TARGETS_PORT_SCHEMA,
    async list() {
      const response = await windowRef.fetch(TARGETS_ENDPOINT, {
        method: "GET",
        cache: "no-store",
        credentials: "same-origin",
        headers: { [TOKEN_HEADER]: token },
      });
      if (!response.ok) {
        const error = new Error(`Native install target discovery failed: ${response.status}`);
        error.status = response.status;
        throw error;
      }
      return validateNativeInstallTargetsSnapshot(await response.json());
    },
  };
  assertNativeInstallTargetsPort(port);
  await port.list();
  return Object.freeze(port);
}
