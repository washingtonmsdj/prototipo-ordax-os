import {
  assertPowerStatusPort,
  validatePowerStatusSnapshot,
} from "../../contracts/power-status.mjs";
import { assertLocalizationPort } from "../../contracts/localization.mjs";
import { formatPowerReceivedAt } from "./battery-tray-controls.mjs";

function stateLabel(state, t) {
  const messageId = {
    charging: "battery.state.charging",
    discharging: "battery.state.discharging",
    full: "battery.state.full",
    "not-charging": "battery.state.notCharging",
    unknown: "battery.state.unknown",
  }[state] ?? "battery.state.unknown";
  return t(messageId);
}

function powerLabel(externalPower, t) {
  return externalPower === true
    ? t("battery.power.connected")
    : externalPower === false
      ? t("battery.power.disconnected")
      : t("battery.power.unknown");
}

export function mountBatteryQuickPanel(root, powerStatus, localization) {
  if (!(root instanceof Element)) {
    throw new TypeError("Battery quick panel requires a Surface root Element");
  }
  const port = assertPowerStatusPort(powerStatus);
  const localizationPort = assertLocalizationPort(localization);
  const t = localizationPort.translate;
  const panel = root.querySelector('[data-quick-panel="battery"]');
  const percent = root.querySelector("[data-quick-battery-percent]");
  const state = root.querySelector("[data-quick-battery-state]");
  const power = root.querySelector("[data-quick-battery-power]");
  if (!panel || !percent || !state || !power) {
    throw new Error("Battery quick panel requires shared shell slots");
  }

  let destroyed = false;
  let pending = false;
  let lastSnapshot = null;
  let lastSuccessAt = null;
  let readFailed = false;

  const render = (snapshot, { stale = false } = {}) => {
    const value = validatePowerStatusSnapshot(snapshot);
    panel.dataset.powerObservation = stale ? "stale" : "current";

    if (value.battery === null) {
      percent.textContent = "--%";
      state.textContent = stale
        ? t("battery.quick.noneStale", {
            time: formatPowerReceivedAt(
              lastSuccessAt,
              localizationPort.getLocale(),
              t("common.time.unknown"),
            ),
          })
        : t("battery.quick.none");
      power.textContent = powerLabel(value.externalPower, t);
      return;
    }

    percent.textContent = `${value.battery.percent}%`;
    const localizedState = stateLabel(value.battery.state, t);
    state.textContent = stale
      ? t("battery.quick.stateStale", {
          state: localizedState,
          time: formatPowerReceivedAt(
            lastSuccessAt,
            localizationPort.getLocale(),
            t("common.time.unknown"),
          ),
        })
      : localizedState;
    power.textContent = powerLabel(value.externalPower, t);
  };

  const renderUnavailable = () => {
    panel.dataset.powerObservation = "unavailable";
    percent.textContent = "--%";
    state.textContent = t("battery.quick.unavailable");
    power.textContent = t("battery.quick.powerUnavailable");
  };

  const refresh = async () => {
    if (destroyed || pending) return;
    pending = true;
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
      if (!destroyed) pending = false;
    }
  };

  const onOpen = () => {
    void refresh();
  };

  const unsubscribeLocalization = localizationPort.subscribe(() => {
    if (destroyed) return;
    if (lastSnapshot) {
      render(lastSnapshot, { stale: readFailed });
    } else {
      renderUnavailable();
    }
  });
  panel.addEventListener("ordax:quick-panel-open", onOpen);

  return Object.freeze({
    refresh,
    destroy() {
      destroyed = true;
      unsubscribeLocalization();
      lastSnapshot = null;
      lastSuccessAt = null;
      readFailed = false;
      delete panel.dataset.powerObservation;
      panel.removeEventListener("ordax:quick-panel-open", onOpen);
    },
  });
}
