import assert from "node:assert/strict";
import {
  NATIVE_INSTALL_TARGETS_PORT_SCHEMA,
  validateNativeInstallTargetsSnapshot,
} from "../system/contracts/native-install-targets.mjs";
import { createNativeInstallTargets } from "../system/adapters/native/native-install-targets.mjs";

const target = {
  targetId: "a".repeat(64),
  confirmationToken: "a".repeat(64),
  model: "Example NVMe",
  transport: "nvme",
  physicalBytes: 64 * 1024 * 1024 * 1024,
  removable: false,
  readOnly: false,
  sourceBootMedia: false,
  eligible: true,
};

{
  const snapshot = validateNativeInstallTargetsSnapshot({
    schema: "ordax.native-install-targets/1",
    physicalWriteAllowed: false,
    targets: [target],
  });
  assert.equal(snapshot.physicalWriteAllowed, false);
  assert.equal(snapshot.targets[0].eligible, true);
  assert.throws(
    () => validateNativeInstallTargetsSnapshot({
      schema: "ordax.native-install-targets/1",
      physicalWriteAllowed: true,
      targets: [target],
    }),
    /invalid/,
  );
}

{
  const requests = [];
  const windowRef = {
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (url === "/__ordax/native/session") {
        return {
          ok: true,
          json: async () => ({
            productMode: "usb",
            nativeInstallAvailable: true,
            nativeInstallToken: "session-token-1234567890",
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          schema: "ordax.native-install-targets/1",
          physicalWriteAllowed: false,
          targets: [target],
        }),
      };
    },
  };
  const port = await createNativeInstallTargets(windowRef);
  assert.equal(port.schema, NATIVE_INSTALL_TARGETS_PORT_SCHEMA);
  const snapshot = await port.list();
  assert.equal(snapshot.targets.length, 1);
  assert.equal(requests[1].options.method, "GET");
  assert.equal(
    requests[1].options.headers["X-OrdaX-Native-Install-Token"],
    "session-token-1234567890",
  );
}

{
  const windowRef = {
    fetch: async () => ({
      ok: true,
      json: async () => ({
        productMode: "native-disk",
        nativeInstallAvailable: false,
        nativeInstallToken: "",
      }),
    }),
  };
  await assert.rejects(
    () => createNativeInstallTargets(windowRef),
    /only in OrdaX USB mode/,
  );
}

console.log("NATIVE_INSTALL_TARGETS_ADAPTER=PASS");
