import { defineComponentManifest } from "../../contracts/component-manifest.mjs";

export const COMPONENT_PROMOTION_DECISION_SCHEMA =
  "ordax.component-promotion-decision/1";

const HEALTH_VALUES = new Set(["unknown", "healthy", "failed"]);
const ACTIONS = new Set(["hold", "reject", "promote"]);

function boolean(value, label) {
  if (typeof value !== "boolean") {
    throw new TypeError(`${label} must be boolean`);
  }
  return value;
}

function decision(manifest, health, action, reason) {
  if (!ACTIONS.has(action)) {
    throw new TypeError("Unsupported component promotion action");
  }
  return Object.freeze({
    schema: COMPONENT_PROMOTION_DECISION_SCHEMA,
    componentId: manifest.id,
    version: manifest.version,
    releaseMode: manifest.releaseMode,
    healthMode: manifest.healthMode,
    health,
    action,
    reason,
  });
}

export function decidePendingComponentAction({
  manifest,
  health,
  canonicalTrustPinned,
  activationAllowed,
} = {}) {
  const component = defineComponentManifest(manifest);
  if (!HEALTH_VALUES.has(health)) {
    throw new TypeError("Pending component health must be unknown, healthy or failed");
  }
  const trustPinned = boolean(
    canonicalTrustPinned,
    "canonicalTrustPinned",
  );
  const canActivate = boolean(
    activationAllowed,
    "activationAllowed",
  );

  if (health === "failed") {
    return decision(component, health, "reject", "pending-health-failed");
  }
  if (health === "unknown") {
    return decision(component, health, "hold", "pending-health-unknown");
  }
  if (component.releaseMode !== "component-slot") {
    return decision(
      component,
      health,
      "hold",
      "release-mode-not-component-slot",
    );
  }
  if (component.healthMode === "none") {
    return decision(
      component,
      health,
      "hold",
      "component-health-mode-none",
    );
  }
  if (!trustPinned) {
    return decision(
      component,
      health,
      "hold",
      "canonical-component-trust-not-pinned",
    );
  }
  if (!canActivate) {
    return decision(
      component,
      health,
      "hold",
      "component-slot-activation-disabled",
    );
  }
  return decision(component, health, "promote", "eligible-for-promotion");
}
