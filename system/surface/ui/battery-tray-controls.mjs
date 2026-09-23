import {
  assertPowerStatusPort,
  validatePowerStatusSnapshot,
} from "../../contracts/power-status.mjs";
import { assertSurfaceRenderLifecycle } from "../../contracts/surface-render-lifecycle.mjs";

const POLL_INTERVAL_MS = 30000;
const POWER_TIME_ZONE = "America/Bahia";

export function formatPowerReceivedAt(value, locale = "pt-BR") {
  if (!Number.isFinite(value)) return null;
  return new Intl.DateTimeFormat(locale, {
    timeZone: POWER_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function batteryLevel(percent) {
  if (percent <= 10) return 0;
  if (percent <= 25) return 1;
  if (percent <= 50) return 2;
  if (percent <= 75) return 3;
  return 4;
}

function stateKey(state) {
  return state === "not-charging" ? "notCharging" : state;
}

function externalTitleMessageId(externalPower) {
  if (externalPower === true) return "power.tray.external.connected";
  if (externalPower === false) return "power.tray.external.disconnected";
  return null;
}

function batteryTitle(battery, externalPower, translate) {
  const state = translate(`power.stateTitle.${stateKey(battery.state)}`);
  const externalMessageId = externalTitleMessageId(externalPower);
  const external = externalMessageId ? translate(externalMessageId) : "";
  return translate("power.tray.title", {
    percent: battery.percent,
    state,
    external,
  });
}

export function mountBatteryTrayControls(
  root,
  powerStatus,
  surfaceLifecycle,
  { pollIntervalMs = POLL_INTERVAL_MS } = {},
) {
  if (!(root instanceof Element)) {
    throw new TypeError("Battery tray controls require a Surface root Element");
  }
  const port = assertPowerStatusPort(powerStatus);
  const lifecycle = assertSurfaceRenderLifecycle(surfaceLifecycle);
  const localization = lifecycle.localization;
  const t = localization.translate;
  const item = root.querySelector("[data-battery-tray]");
  const icon = root.querySelector("[data-battery-icon]");
  const label = root.querySelector("[data-battery-label]");
  if (!item || !icon || !label) {
    throw new Error("Battery tray controls require the shared system tray");
  }

  let destroyed = false;
  let polling = false;
  let lastSnapshot = null;
  let lastSuccessAt = null;
  let lastObservation = "initial";

  const receivedAt = () =>
    formatPowerReceivedAt(lastSuccessAt, localization.getLocale())
    ?? t("power.time.unknown");

  const render = (snapshot, { stale = false } = {}) => {
    const value = validatePowerStatusSnapshot(snapshot);
    lastObservation = stale ? "stale" : "current";
    item.hidden = false;
    item.dataset.batteryObservation = lastObservation;
    item.dataset.externalPower =
      value.externalPower === null ? "unknown" : String(value.externalPower);

    if (value.battery === null) {
      item.dataset.batteryState = "not-detected";
      icon.dataset.batteryLevel = "unknown";
      icon.dataset.charging = "false";
      label.textContent = stale
        ? t("power.tray.notDetected.staleLabel")
        : "--";
      item.title = stale
        ? t("power.tray.notDetected.staleTitle", { time: receivedAt() })
        : t("power.tray.notDetected.title");
      return;
    }

    item.dataset.batteryState = value.battery.state;
    icon.dataset.batteryLevel = stale
      ? "unknown"
      : String(batteryLevel(value.battery.percent));
    icon.dataset.charging = stale ? "false" : String(value.battery.state === "charging");
    const labelValue = `${value.battery.percent}%`;
    label.textContent = stale
      ? t("power.tray.stale.label", { label: labelValue })
      : labelValue;
    const title = batteryTitle(value.battery, value.externalPower, t);
    item.title = stale
      ? t("power.tray.stale.title", { title, time: receivedAt() })
      : title;
  };

  const renderUnavailable = () => {
    lastObservation = "unavailable";
    item.hidden = false;
    item.dataset.batteryState = "unavailable";
    item.dataset.batteryObservation = lastObservation;
    item.dataset.externalPower = "unknown";
    icon.dataset.batteryLevel = "unknown";
    icon.dataset.charging = "false";
    label.textContent = "--";
    item.title = t("power.tray.unavailable.title");
  };

  const refresh = async () => {
    if (destroyed || polling) return;
    polling = true;
    try {
      const snapshot = validatePowerStatusSnapshot(await port.read());
      if (destroyed) return;
      lastSnapshot = snapshot;
      lastSuccessAt = Date.now();
      render(snapshot);
    } catch {
      if (destroyed) return;
      if (lastSnapshot) {
        render(lastSnapshot, { stale: true });
      } else {
        renderUnavailable();
      }
    } finally {
      if (!destroyed) polling = false;
    }
  };

  const unsubscribeLocalization = localization.subscribe(() => {
    if (destroyed || lastObservation === "initial") return;
    if (lastSnapshot) {
      render(lastSnapshot, { stale: lastObservation === "stale" });
    } else {
      renderUnavailable();
    }
  });

  void refresh();
  const timer = setInterval(() => void refresh(), pollIntervalMs);

  return Object.freeze({
    refresh,
    destroy() {
      destroyed = true;
      clearInterval(timer);
      unsubscribeLocalization();
      lastSnapshot = null;
      lastSuccessAt = null;
      delete item.dataset.batteryObservation;
    },
  });
}
