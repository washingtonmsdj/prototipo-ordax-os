import {
  assertNetworkManagementPort,
  validateNetworkManagementSnapshot,
} from "../../contracts/network-management.mjs";
import {
  assertNetworkStatusPort,
  validateNetworkStatusSnapshot,
} from "../../contracts/network-status.mjs";
import { runNetworkManagementAction } from "../../services/network/management-runtime.mjs";
import { assertLocalizationPort } from "../../contracts/localization.mjs";
import {
  formatNetworkReceivedAt,
  localizeNetworkSummary,
  summarizeNetworkStatus,
} from "./network-tray-controls.mjs";

const MAX_QUICK_NETWORKS = 8;

function node(documentObject, tag, className, text) {
  const element = documentObject.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function signalLabel(signalDbm, t) {
  if (signalDbm >= -50) return t("network.signal.labelStrong");
  if (signalDbm >= -60) return t("network.signal.labelGood");
  if (signalDbm >= -70) return t("network.signal.labelFair");
  return t("network.signal.labelWeak");
}

function networkActionMessage(action, state, t) {
  return t(`network.action.${action}.${state === 1 ? "done" : "pending"}`);
}

function networkFailureMessage(action, error, t) {
  if (error?.status === 409 && action === "connect") {
    return t("network.action.connect.conflict");
  }
  if (error?.status === 409 && action === "reconnect") {
    return t("network.action.reconnect.conflict");
  }
  if (error instanceof TypeError) {
    return t("network.action.invalid");
  }
  return t("network.action.failed");
}

export function mountNetworkQuickPanel(
  root,
  networkStatus,
  networkManagement = null,
  localization = null,
) {
  if (!(root instanceof Element)) {
    throw new TypeError("Network quick panel requires a Surface root Element");
  }
  const statusPort = networkStatus === null ? null : assertNetworkStatusPort(networkStatus);
  const localizationPort = assertLocalizationPort(localization);
  const t = localizationPort.translate;
  const managementPort =
    networkManagement === null ? null : assertNetworkManagementPort(networkManagement);
  const panel = root.querySelector('[data-quick-panel="network"]');
  const content = root.querySelector("[data-quick-network-content]");
  if (!panel || !content) {
    throw new Error("Network quick panel requires shared shell slots");
  }

  const documentObject = root.ownerDocument;
  let statusSnapshot = null;
  let statusReadFailed = false;
  let statusLastSuccessAt = null;
  let managementSnapshot = null;
  let managementReadFailed = false;
  let managementLastSuccessAt = null;
  let selectedSsid = null;
  let pending = false;
  let message = "";
  let statusOrdinal = 0;
  let managementOrdinal = 0;
  let actionOrdinal = 0;
  let passwordDraft = "";
  let passwordDraftSsid = null;
  let focusPasswordRequested = false;
  let destroyed = false;

  const clearPasswordDraft = () => {
    passwordDraft = "";
    passwordDraftSsid = null;
    focusPasswordRequested = false;
  };

  const focusIdentity = (element) => {
    if (!element || !element.dataset) return null;
    if (element.dataset.quickWifiPasswordFor) {
      return Object.freeze({
        kind: "password",
        value: element.dataset.quickWifiPasswordFor,
      });
    }
    if (element.dataset.quickWifiSsid && !element.dataset.quickNetworkAction) {
      return Object.freeze({ kind: "network", value: element.dataset.quickWifiSsid });
    }
    if (element.dataset.quickNetworkAction) {
      return Object.freeze({
        kind: "action",
        value: element.dataset.quickNetworkAction,
        ssid: element.dataset.quickWifiSsid ?? null,
      });
    }
    if (element.dataset.appTarget === "network") {
      return Object.freeze({ kind: "settings", value: "network" });
    }
    return null;
  };

  const findFocusTarget = (identity) => {
    if (!identity) return null;
    return Array.from(content.querySelectorAll("button, input")).find((element) => {
      const candidate = focusIdentity(element);
      return candidate
        && candidate.kind === identity.kind
        && candidate.value === identity.value
        && (candidate.ssid ?? null) === (identity.ssid ?? null);
    }) ?? null;
  };

  const captureInteraction = () => {
    const activeElement = documentObject.activeElement;
    const activeInside = activeElement && content.contains(activeElement);
    const passwordInput = content.querySelector("[data-quick-wifi-password]");
    const list = content.querySelector(".ordax-quick-network-list");
    return Object.freeze({
      panelScrollTop: panel.scrollTop,
      listScrollTop: list?.scrollTop ?? 0,
      focus: activeInside ? focusIdentity(activeElement) : null,
      passwordSelection:
        passwordInput instanceof HTMLInputElement && activeElement === passwordInput
          ? Object.freeze({
              start: passwordInput.selectionStart,
              end: passwordInput.selectionEnd,
            })
          : null,
    });
  };

  const restoreInteraction = (snapshot) => {
    if (!snapshot) return;
    const list = content.querySelector(".ordax-quick-network-list");
    if (list) list.scrollTop = snapshot.listScrollTop;

    let focusTarget = findFocusTarget(snapshot.focus);
    if (focusPasswordRequested) {
      focusTarget = content.querySelector("[data-quick-wifi-password]") ?? focusTarget;
      focusPasswordRequested = false;
    }
    focusTarget?.focus?.({ preventScroll: true });

    if (
      focusTarget instanceof HTMLInputElement
      && snapshot.passwordSelection
      && focusTarget.dataset.quickWifiPasswordFor === passwordDraftSsid
    ) {
      const length = focusTarget.value.length;
      const start = Math.min(snapshot.passwordSelection.start ?? length, length);
      const end = Math.min(snapshot.passwordSelection.end ?? start, length);
      focusTarget.setSelectionRange(start, end);
    }
    panel.scrollTop = snapshot.panelScrollTop;
  };

  const render = () => {
    const interaction = captureInteraction();
    content.replaceChildren();

    const summary = node(documentObject, "div", "ordax-quick-network-summary");
    if (statusSnapshot) {
      const state = summarizeNetworkStatus(statusSnapshot);
      const stateCopy = localizeNetworkSummary(state, t);
      summary.dataset.observation = statusReadFailed ? "stale" : "current";
      summary.append(
        node(
          documentObject,
          "strong",
          "",
          statusReadFailed
            ? t("network.quick.staleLabel", { label: stateCopy.label })
            : stateCopy.label,
        ),
        node(
          documentObject,
          "span",
          "",
          statusReadFailed
            ? t("network.quick.staleDetail", {
                title: stateCopy.title,
                time: formatNetworkReceivedAt(
                  statusLastSuccessAt,
                  localizationPort.getLocale(),
                  t("common.time.unknown"),
                ),
              })
            : stateCopy.title,
        ),
      );
    } else {
      summary.dataset.observation = statusReadFailed ? "unavailable" : "loading";
      summary.append(
        node(documentObject, "strong", "", t("network.quick.heading")),
        node(
          documentObject,
          "span",
          "",
          statusPort
            ? statusReadFailed
              ? t("network.quick.statusUnavailable")
              : t("network.quick.statusLoading")
            : t("network.quick.localDetailsUnavailable"),
        ),
      );
    }
    content.append(summary);

    if (!managementPort) {
      content.append(
        node(
          documentObject,
          "p",
          "ordax-quick-empty",
          t("network.quick.managementUnavailable"),
        ),
      );
      restoreInteraction(interaction);
      return;
    }

    const actions = node(documentObject, "div", "ordax-quick-actions");
    const addAction = (action, label, primary = false) => {
      const button = node(
        documentObject,
        "button",
        primary ? "ordax-quick-action ordax-quick-action-primary" : "ordax-quick-action",
        label,
      );
      button.type = "button";
      button.dataset.quickNetworkAction = action;
      button.disabled = pending;
      actions.append(button);
    };
    addAction(
      "scan",
      pending ? t("network.quick.wait") : t("network.quick.scan"),
      true,
    );
    if (managementSnapshot?.currentSsid) {
      addAction("disconnect", t("network.quick.disconnect"));
    }
    if (managementSnapshot?.savedSsid && !managementSnapshot.currentSsid) {
      addAction("reconnect", t("network.quick.reconnect"));
    }
    content.append(actions);

    if (message) {
      const status = node(documentObject, "p", "ordax-quick-message", message);
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      content.append(status);
    }

    if (managementReadFailed && managementSnapshot !== null) {
      const stale = node(
        documentObject,
        "p",
        "ordax-quick-message",
        t("network.quick.staleNetworks", {
          time: formatNetworkReceivedAt(
            managementLastSuccessAt,
            localizationPort.getLocale(),
            t("common.time.unknown"),
          ),
        }),
      );
      stale.dataset.observation = "stale";
      content.append(stale);
    }

    if (managementSnapshot === null) {
      content.append(
        node(
          documentObject,
          "p",
          "ordax-quick-empty",
          managementReadFailed
            ? t("network.quick.wifiUnavailable")
            : t("network.quick.wifiLoading"),
        ),
      );
      restoreInteraction(interaction);
      return;
    }

    if (managementSnapshot.currentSsid) {
      const current = node(documentObject, "div", "ordax-quick-current");
      current.append(
        node(documentObject, "span", "ordax-quick-kicker", t("network.quick.connected")),
        node(documentObject, "strong", "", managementSnapshot.currentSsid),
      );
      content.append(current);
    }

    const list = node(documentObject, "div", "ordax-quick-network-list");
    const networks = [...managementSnapshot.networks]
      .sort((left, right) => right.signalDbm - left.signalDbm)
      .slice(0, MAX_QUICK_NETWORKS);
    if (networks.length === 0) {
      list.append(
        node(
          documentObject,
          "p",
          "ordax-quick-empty",
          t("network.quick.empty"),
        ),
      );
    } else {
      for (const entry of networks) {
        const button = node(documentObject, "button", "ordax-quick-network");
        button.type = "button";
        button.dataset.quickWifiSsid = entry.ssid;
        button.dataset.selected = String(selectedSsid === entry.ssid);
        button.dataset.connected = String(entry.connected);
        button.disabled = pending || entry.connected;
        button.setAttribute("aria-pressed", String(selectedSsid === entry.ssid));
        const copy = node(documentObject, "span", "ordax-quick-network-copy");
        copy.append(
          node(documentObject, "strong", "", entry.ssid),
          node(
            documentObject,
            "small",
            "",
            t("network.quick.networkDetail", {
              state: entry.connected
                ? t("network.quick.networkConnected")
                : entry.saved
                  ? t("network.quick.networkSaved")
                  : t("network.quick.networkAvailable"),
              signal: signalLabel(entry.signalDbm, t),
            }),
          ),
        );
        button.append(
          node(documentObject, "span", "ordax-quick-network-dot"),
          copy,
        );
        list.append(button);
      }
    }
    content.append(list);

    const selected = managementSnapshot.networks.find(
      (entry) => entry.ssid === selectedSsid,
    );
    if (selected && !selected.connected) {
      const form = node(documentObject, "div", "ordax-quick-network-form");
      const label = node(documentObject, "label", "ordax-quick-network-password");
      label.append(node(documentObject, "span", "", t("network.quick.password", { ssid: selected.ssid })));
      const input = documentObject.createElement("input");
      input.type = "password";
      input.autocomplete = "off";
      input.dataset.quickWifiPassword = "";
      input.dataset.quickWifiPasswordFor = selected.ssid;
      input.value = passwordDraftSsid === selected.ssid ? passwordDraft : "";
      input.disabled = pending;
      label.append(input);
      const connect = node(documentObject, "button", "ordax-quick-action ordax-quick-action-primary", t("network.quick.connect"));
      connect.type = "button";
      connect.dataset.quickNetworkAction = "connect";
      connect.dataset.quickWifiSsid = selected.ssid;
      connect.disabled = pending;
      form.append(label, connect);
      content.append(form);
    }

    const settings = node(documentObject, "button", "ordax-quick-settings-link", t("network.quick.openSettings"));
    settings.type = "button";
    settings.dataset.launchApp = "settings";
    settings.dataset.appTarget = "network";
    settings.dataset.quickPanelClose = "";
    content.append(settings);
    restoreInteraction(interaction);
  };

  const refreshStatus = async () => {
    if (!statusPort || destroyed) return;
    const ordinal = ++statusOrdinal;
    try {
      const nextSnapshot = validateNetworkStatusSnapshot(await statusPort.read());
      if (destroyed || ordinal !== statusOrdinal) return;
      statusSnapshot = nextSnapshot;
      statusReadFailed = false;
      statusLastSuccessAt = Date.now();
    } catch {
      if (destroyed || ordinal !== statusOrdinal) return;
      statusReadFailed = true;
    }
  };

  const refreshManagement = async () => {
    if (!managementPort || destroyed) return;
    const ordinal = ++managementOrdinal;
    try {
      const nextSnapshot = validateNetworkManagementSnapshot(await managementPort.status());
      if (destroyed || ordinal !== managementOrdinal) return;
      managementSnapshot = nextSnapshot;
      managementReadFailed = false;
      managementLastSuccessAt = Date.now();
      if (message === t("network.quick.temporarilyUnavailable")) {
        message = "";
      }
      if (
        selectedSsid !== null
        && !nextSnapshot.networks.some((entry) => entry.ssid === selectedSsid)
      ) {
        selectedSsid = null;
        clearPasswordDraft();
      }
    } catch {
      if (destroyed || ordinal !== managementOrdinal) return;
      managementReadFailed = true;
      if (managementSnapshot === null) {
        message = t("network.quick.temporarilyUnavailable");
      }
    }
  };

  const refresh = async () => {
    await Promise.all([refreshStatus(), refreshManagement()]);
    if (!destroyed) render();
  };

  const runAction = async (action, credentials = null) => {
    if (!managementPort || pending || destroyed) return;
    const ordinal = ++actionOrdinal;
    managementOrdinal += 1;
    pending = true;
    message = networkActionMessage(action, 0, t);
    render();

    try {
      const nextSnapshot = validateNetworkManagementSnapshot(
        await runNetworkManagementAction(managementPort, action, credentials),
      );
      if (destroyed || ordinal !== actionOrdinal) return;
      managementSnapshot = nextSnapshot;
      managementReadFailed = false;
      managementLastSuccessAt = Date.now();
      selectedSsid = null;
      clearPasswordDraft();
      message = networkActionMessage(action, 1, t);
      await refreshStatus();
    } catch (error) {
      if (destroyed || ordinal !== actionOrdinal) return;
      message = networkFailureMessage(action, error, t);
    } finally {
      if (!destroyed && ordinal === actionOrdinal) {
        pending = false;
        render();
      }
    }
  };

  const onOpen = () => {
    message = "";
    selectedSsid = null;
    clearPasswordDraft();
    panel.scrollTop = 0;
    void refresh();
  };

  const onClose = () => {
    selectedSsid = null;
    clearPasswordDraft();
    message = "";
  };

  const onClick = (event) => {
    const network = event.target.closest("[data-quick-wifi-ssid]");
    if (network && panel.contains(network)) {
      const nextSsid = network.dataset.quickWifiSsid ?? null;
      if (nextSsid !== selectedSsid) clearPasswordDraft();
      selectedSsid = nextSsid;
      passwordDraftSsid = selectedSsid;
      focusPasswordRequested = selectedSsid !== null;
      message = "";
      render();
      return;
    }

    const action = event.target.closest("[data-quick-network-action]");
    if (!action || !panel.contains(action)) return;
    const kind = action.dataset.quickNetworkAction;
    if (kind === "connect") {
      const ssid = action.dataset.quickWifiSsid;
      const input = panel.querySelector("[data-quick-wifi-password]");
      if (!(input instanceof HTMLInputElement) || input.dataset.quickWifiPasswordFor !== ssid) {
        return;
      }
      const password = input.value;
      input.value = "";
      clearPasswordDraft();
      if (!password) {
        message = t("network.quick.passwordRequired");
        render();
        return;
      }
      void runAction("connect", { ssid, password });
      return;
    }
    void runAction(kind);
  };

  const onInput = (event) => {
    const input = event.target.closest("[data-quick-wifi-password]");
    if (!(input instanceof HTMLInputElement) || !panel.contains(input)) return;
    if (input.dataset.quickWifiPasswordFor !== selectedSsid) return;
    passwordDraftSsid = selectedSsid;
    passwordDraft = input.value;
  };

  const onKeyDown = (event) => {
    const input = event.target.closest("[data-quick-wifi-password]");
    if (!input || !panel.contains(input)) return;
    if (event.key === "Enter") {
      event.preventDefault();
      panel.querySelector('[data-quick-network-action="connect"]')?.click();
    }
  };

  const unsubscribeLocalization = localizationPort.subscribe(() => {
    if (destroyed) return;
    message = "";
    render();
  });

  panel.addEventListener("ordax:quick-panel-open", onOpen);
  panel.addEventListener("ordax:quick-panel-close", onClose);
  panel.addEventListener("click", onClick);
  panel.addEventListener("input", onInput);
  panel.addEventListener("keydown", onKeyDown);

  return Object.freeze({
    refresh,
    destroy() {
      destroyed = true;
      statusOrdinal += 1;
      managementOrdinal += 1;
      actionOrdinal += 1;
      clearPasswordDraft();
      unsubscribeLocalization();
      statusSnapshot = null;
      statusLastSuccessAt = null;
      managementSnapshot = null;
      managementLastSuccessAt = null;
      panel.removeEventListener("ordax:quick-panel-open", onOpen);
      panel.removeEventListener("ordax:quick-panel-close", onClose);
      panel.removeEventListener("click", onClick);
      panel.removeEventListener("input", onInput);
      panel.removeEventListener("keydown", onKeyDown);
    },
  });
}
