import {
  assertPowerStatusPort,
  validatePowerStatusSnapshot,
} from "../../contracts/power-status.mjs";
import { assertLocalizationPort } from "../../contracts/localization.mjs";

const POLL_INTERVAL_MS = 30000;
const POWER_TIME_ZONE = "America/Bahia";

export function formatPowerReceivedAt(value, locale = "pt-BR", fallback = "horário desconhecido") {
  if (!Number.isFinite(value)) return fallback;
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

function batteryStateLabel(state, t) {
  const messageId = {
    charging: "battery.state.charging",
    discharging: "battery.state.discharging",
    full: "battery.state.full",
    "not-charging": "battery.state.notCharging",
    unknown: "battery.state.unknown",
  }[state] ?? "battery.state.unknown";
  return t(messageId);
}

function batteryTitle(battery, externalPower, localization) {
  const t = localization.translate;
  const stateCopy = batteryStateLabel(battery.state, t)
    .toLocaleLowerCase(localization.getLocale());
  const powerCopy =
    externalPower === true
      ? ` ${t("battery.tray.external")}`
      : externalPower === false
        ? ` ${t("battery.tray.discharging")}`
        : "";
  return t("battery.tray.title", {
    percent: battery.percent,
    state: stateCopy,
    power: powerCopy,
  });
}

export function mountBatteryTrayControls(
  root,
  powerStatus,
  localization,
  { pollIntervalMs = POLL_INTERVAL_MS } = {},
) {
  if (!(root instanceof Element)) {
    throw new TypeError("Battery tray controls require a Surface root Element");
  }
  const port = assertPowerStatusPort(powerStatus);
  const localizationPort = assertLocalizationPort(localization);
  const t = localizationPort.translate;
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
  let readFailed = false;

  const render = (snapshot, { stale = false } = {}) => {
    const value = validatePowerStatusSnapshot(snapshot);
    item.hidden = false;
    item.dataset.batteryObservation = stale ? "stale" : "current";
    item.dataset.externalPower =
      value.externalPower === null ? "unknown" : String(value.externalPower);

    if (value.battery === null) {
      item.dataset.batteryState = "not-detected";
      icon.dataset.batteryLevel = "unknown";
      icon.dataset.charging = "false";
      label.textContent = stale ? t("battery.tray.noneStaleLabel") : "--";
      item.title = stale
        ? t("battery.tray.noneStaleTitle", {
            time: formatPowerReceivedAt(
              lastSuccessAt,
              localizationPort.getLocale(),
              t("common.time.unknown"),
            ),
          })
        : t("battery.tray.none");
      return;
    }

    item.dataset.batteryState = value.battery.state;
    icon.dataset.batteryLevel = stale
      ? "unknown"
      : String(batteryLevel(value.battery.percent));
    icon.dataset.charging = stale ? "false" : String(value.battery.state === "charging");
    label.textContent = stale
      ? t("battery.tray.staleLabel", { percent: value.battery.percent })
      : `${value.battery.percent}%`;
    const title = batteryTitle(value.battery, value.externalPower, localizationPort);
    item.title = stale
      ? t("battery.tray.staleTitle", {
          title,
          time: formatPowerReceivedAt(
            lastSuccessAt,
            localizationPort.getLocale(),
            t("common.time.unknown"),
          ),
        })
      : title;
  };

  const renderUnavailable = () => {
    item.hidden = false;
    item.dataset.batteryState = "unavailable";
    item.dataset.batteryObservation = "unavailable";
    item.dataset.externalPower = "unknown";
    icon.dataset.batteryLevel = "unknown";
    icon.dataset.charging = "false";
    label.textContent = "--";
    item.title = t("battery.tray.unavailable");
  };

  const refresh = async () => {
    if (destroyed || polling) return;
    polling = true;
    try {
      const snapshot = validatePowerStatusSnapshot(await port.read());
      if (destroyed) return;
      lastSnapshot = snapshot;
      lastSuccessAt = Date.now();
      readFailed = false;
      render(snapshot);
    } catch {
      if (destroyed) return;
      readFailed = true;
      if (lastSnapshot) {
        render(lastSnapshot, { stale: true });
      } else {
        renderUnavailable();
      }
    } finally {
      if (!destroyed) polling = false;
    }
  };

  const unsubscribeLocalization = localizationPort.subscribe(() => {
    if (destroyed) return;
    if (lastSnapshot) {
      render(lastSnapshot, { stale: readFailed });
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
      readFailed = false;
      delete item.dataset.batteryObservation;
    },
  });
}
