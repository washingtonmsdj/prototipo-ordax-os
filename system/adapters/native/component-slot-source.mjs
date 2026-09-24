import { validateComponentId } from "../../contracts/component-manifest.mjs";
import {
  COMPONENT_SLOT_SOURCE_SCHEMA,
  assertComponentSlotSource,
  validateComponentSlotResolution,
  validateComponentSlotState,
} from "../../contracts/component-slot-source.mjs";

const COMPONENT_METADATA_PATH = "/__ordax/native/component-runtime";
const COMPONENT_MODULE_PREFIX = "/__ordax/native/component-module/";

function nativeSurfaceOrigin(windowRef) {
  const href = windowRef?.location?.href;
  if (typeof href !== "string" || !href) {
    throw new TypeError("Native component slot source requires window.location.href");
  }
  const location = new URL(href);
  const port = Number(location.port);
  if (
    location.protocol !== "http:"
    || location.hostname !== "127.0.0.1"
    || location.username
    || location.password
    || !Number.isInteger(port)
    || port < 1
    || port > 65535
  ) {
    throw new TypeError("Native component slots require the canonical loopback Surface origin");
  }
  return location.origin;
}

export function createNativeComponentSlotSource(windowRef = globalThis.window) {
  const origin = nativeSurfaceOrigin(windowRef);
  const source = {
    schema: COMPONENT_SLOT_SOURCE_SCHEMA,
    metadataUrl(componentIdValue, stateValue) {
      const componentId = validateComponentId(componentIdValue);
      const state = validateComponentSlotState(stateValue);
      const url = new URL(COMPONENT_METADATA_PATH, `${origin}/`);
      url.searchParams.set("component", componentId);
      url.searchParams.set("state", state);
      if (url.origin !== origin) {
        throw new TypeError("Native component metadata URL escaped the Surface origin");
      }
      return url.href;
    },
    runtimeUrl(resolutionValue) {
      const resolution = validateComponentSlotResolution(resolutionValue);
      const path =
        `${COMPONENT_MODULE_PREFIX}${resolution.componentId}/`
        + `${resolution.state}/${resolution.version}/${resolution.sourceCommit}/`
        + resolution.entrypoint;
      const url = new URL(path, `${origin}/`);
      if (url.origin !== origin || url.pathname !== path) {
        throw new TypeError("Native component runtime URL escaped the verified namespace");
      }
      return url.href;
    },
  };
  return Object.freeze(assertComponentSlotSource(source));
}
