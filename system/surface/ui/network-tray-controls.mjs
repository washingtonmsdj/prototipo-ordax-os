import {
  assertNetworkStatusPort,
  validateNetworkStatusSnapshot,
} from "../../contracts/network-status.mjs";
import { assertLocalizationPort } from "../../contracts/localization.mjs";

const POLL_INTERVAL_MS = 5000;
const NETWORK_TIME_ZONE = "America/Bahia";

export function formatNetworkReceivedAt(value, locale = "pt-BR", fallback = "horário desconhecido") {
  if (!Number.isFinite(value)) return fallback;
  return new Intl.DateTimeFormat(locale, {
    timeZone: NETWORK_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function signalLevel(signalDbm) {
  if (!Number.isInteger(signalDbm)) return 0;
  if (signalDbm >= -50) return 4;
  if (signalDbm >= -60) return 3;
  if (signalDbm >= -70) return 2;
  return 1;
}

function choosePrimaryInterface(snapshot) {
  const connected = snapshot.interfaces.filter((entry) => entry.state === "connected");
  const wifi = connected
    .filter((entry) => entry.kind === "wifi")
    .sort((left, right) => (right.signalDbm ?? -999) - (left.signalDbm ?? -999))[0];
  if (wifi) return wifi;
  const ethernet = connected.find((entry) => entry.kind === "ethernet");
  if (ethernet) return ethernet;
  if (connected[0]) return connected[0];
  return (
    snapshot.interfaces.find((entry) => entry.kind === "wifi")
    ?? snapshot.interfaces.find((entry) => entry.kind === "ethernet")
    ?? snapshot.interfaces[0]
    ?? null
  );
}

function stateCopy(entry) {
  if (!entry) {
    return {
      kind: "unknown",
      state: "unknown",
      signalLevel: 0,
      quality: null,
    };
  }
  if (entry.state !== "connected") {
    return {
      kind: entry.kind,
      state: entry.state,
      signalLevel: 0,
      quality: null,
    };
  }
  if (entry.kind === "wifi") {
    const level = signalLevel(entry.signalDbm);
    const quality = [null, "weak", "fair", "good", "strong"][level] ?? null;
    return {
      kind: "wifi",
      state: "connected",
      signalLevel: level,
      quality,
    };
  }
  return {
    kind: entry.kind === "ethernet" ? "ethernet" : "other",
    state: "connected",
    signalLevel: 0,
    quality: null,
  };
}

function networkKindLabel(summary, t) {
  if (summary.kind === "wifi") return t("network.kind.wifi");
  if (summary.kind === "ethernet") return t("network.kind.ethernet");
  return t("network.kind.generic");
}

function networkSummaryCopy(summary, t) {
  if (summary.kind === "unknown") {
    return Object.freeze({
      label: t("network.status.unavailable"),
      title: t("network.status.noInterface"),
    });
  }
  const kind = networkKindLabel(summary, t);
  if (summary.state !== "connected") {
    const state = summary.state === "unknown"
      ? t("network.state.unknown")
      : t("network.state.disconnected");
    return Object.freeze({
      label: summary.state === "unknown"
        ? kind
        : t("network.status.disconnectedLabel", { kind }),
      title: t("network.status.detail", { kind, state }),
    });
  }
  if (summary.kind === "wifi") {
    const quality = summary.quality
      ? t(`network.signal.${summary.quality}`)
      : "";
    return Object.freeze({
      label: kind,
      title: quality
        ? t("network.status.wifiConnectedSignal", { quality })
        : t("network.status.wifiConnected"),
    });
  }
  if (summary.kind === "ethernet") {
    return Object.freeze({
      label: kind,
      title: t("network.status.ethernetConnected"),
    });
  }
  return Object.freeze({
    label: kind,
    title: t("network.status.connected"),
  });
}

export function summarizeNetworkStatus(value) {
  const snapshot = validateNetworkStatusSnapshot(value);
  return Object.freeze(stateCopy(choosePrimaryInterface(snapshot)));
}

export function mountNetworkTrayControls(
  root,
  networkStatus,
  localization,
  { pollIntervalMs = POLL_INTERVAL_MS } = {},
) {
  if (!(root instanceof Element)) {
    throw new TypeError("Network tray controls require a Surface root Element");
  }
  const port = assertNetworkStatusPort(networkStatus);
  const localizationPort = assertLocalizationPort(localization);
  const t = localizationPort.translate;
  const tray = root.querySelector("[data-connectivity-tray]");
  const label = root.querySelector("[data-connectivity-label]");
  const icon = root.querySelector("[data-connectivity-icon]");
  if (!tray || !label || !icon) {
    throw new Error("Network tray controls require the shared system tray");
  }

  let destroyed = false;
  let polling = false;
  let lastSnapshot = null;
  let lastSuccessAt = null;
  let readFailed = false;

  const render = (snapshot, { stale = false } = {}) => {
    const next = summarizeNetworkStatus(snapshot);
    const copy = networkSummaryCopy(next, t);
    tray.dataset.networkKind = next.kind;
    tray.dataset.networkState = next.state;
    tray.dataset.networkObservation = stale ? "stale" : "current";
    const receivedAt = formatNetworkReceivedAt(
      lastSuccessAt,
      localizationPort.getLocale(),
      t("common.time.unknown"),
    );
    tray.title = stale
      ? t("network.tray.staleTitle", { title: copy.title, time: receivedAt })
      : copy.title;
    label.textContent = stale
      ? t("network.tray.staleLabel", { label: copy.label })
      : copy.label;
    icon.dataset.state = stale
      ? "unknown"
      : next.state === "connected" ? "online" : "offline";
    icon.dataset.networkKind = next.kind;
    icon.dataset.signalLevel = String(next.signalLevel);
    tray.dataset.networkDetailOwner = "true";
  };

  const renderUnavailable = () => {
    tray.dataset.networkKind = "unknown";
    tray.dataset.networkState = "unknown";
    tray.dataset.networkObservation = "unavailable";
    tray.title = t("network.tray.detailUnavailable");
    label.textContent = t("network.kind.generic");
    icon.dataset.state = "unknown";
    icon.dataset.networkKind = "unknown";
    icon.dataset.signalLevel = "0";
    tray.dataset.networkDetailOwner = "true";
  };

  const refresh = async () => {
    if (destroyed || polling) return;
    polling = true;
    try {
      const snapshot = validateNetworkStatusSnapshot(await port.read());
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
      delete tray.dataset.networkObservation;
      delete tray.dataset.networkDetailOwner;
    },
  });
}
