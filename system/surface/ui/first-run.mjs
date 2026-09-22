import { assertFirstRunStateStore } from "../../contracts/first-run-state-store.mjs";
import {
  assertIdentityActionsPort,
  isIdentityActionSupported,
} from "../../contracts/identity-actions.mjs";
import { assertIdentitySessionPort } from "../../contracts/identity-session.mjs";
import { assertNetworkManagementPort } from "../../contracts/network-management.mjs";
import { assertPreferenceRuntimePort } from "../../contracts/preference-runtime.mjs";
import {
  REGIONAL_LOCALE_OPTIONS,
  REGIONAL_LOCALE_PREFERENCE_ID,
  REGIONAL_TIME_ZONE_OPTIONS,
  REGIONAL_TIME_ZONE_PREFERENCE_ID,
  isSupportedRegionalTimeZone,
} from "../../services/preferences/regional.mjs";
import { completeFirstRunState, validateFirstRunState } from "../../services/state/first-run.mjs";
import {
  networkManagementActionMessage,
  networkManagementFailureMessage,
  runNetworkManagementAction,
} from "../../services/network/management-runtime.mjs";
import { firstRunStepLabels, firstRunText } from "../../i18n/first-run.mjs";

const STEPS = Object.freeze(["welcome", "regional", "network", "account", "privacy", "ready"]);

function el(documentObject, tag, className = "", text = undefined) {
  const node = documentObject.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function action(documentObject, label, id, primary = false) {
  const button = el(
    documentObject,
    "button",
    primary ? "ordax-first-run-action ordax-first-run-action-primary" : "ordax-first-run-action",
    label,
  );
  button.type = "button";
  button.dataset.firstRunAction = id;
  return button;
}

function signalLabel(dbm, locale) {
  if (dbm >= -50) return firstRunText(locale, "strongSignal");
  if (dbm >= -60) return firstRunText(locale, "goodSignal");
  if (dbm >= -70) return firstRunText(locale, "fairSignal");
  return firstRunText(locale, "weakSignal");
}

export function mountFirstRunExperience(
  root,
  {
    stateStore,
    preferences,
    networkManagement = null,
    identitySession,
    identityActions,
  },
) {
  if (!(root instanceof Element)) {
    throw new TypeError("First-run experience requires the Surface root Element");
  }
  const store = assertFirstRunStateStore(stateStore);
  const preferencePort = assertPreferenceRuntimePort(preferences);
  const networkPort = networkManagement === null ? null : assertNetworkManagementPort(networkManagement);
  const sessionPort = assertIdentitySessionPort(identitySession);
  const actionsPort = assertIdentityActionsPort(identityActions);
  const initial = validateFirstRunState(store.load());

  if (initial.completed) {
    return Object.freeze({ shown: false, destroy() {} });
  }

  const documentObject = root.ownerDocument;
  let detectedTimeZone = null;
  try {
    detectedTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    detectedTimeZone = null;
  }

  const draft = {
    locale: initial.locale,
    timeZone: isSupportedRegionalTimeZone(detectedTimeZone) ? detectedTimeZone : initial.timeZone,
    accountMode: null,
  };

  const previousInert = root.inert;
  const previousAriaHidden = root.getAttribute("aria-hidden");
  root.inert = true;
  root.setAttribute("aria-hidden", "true");

  const overlay = el(documentObject, "section", "ordax-first-run");
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-labelledby", "ordax-first-run-title");
  const shell = el(documentObject, "div", "ordax-first-run-shell");
  const progress = el(documentObject, "aside", "ordax-first-run-progress");
  const card = el(documentObject, "main", "ordax-first-run-card");
  shell.append(progress, card);
  overlay.append(shell);
  documentObject.body.append(overlay);

  let stepIndex = 0;
  let destroyed = false;
  let finishing = false;
  let networkSnapshot = null;
  let networkPending = false;
  let networkMessage = "";
  let networkOrdinal = 0;
  let selectedSsid = null;
  let passwordDraft = "";
  let sessionSnapshot = sessionPort.getSnapshot();
  let actionsSnapshot = actionsPort.getSnapshot();
  let identityPending = null;
  let identityMessage = "";
  let completionError = "";
  let unsubscribeSession = null;
  let unsubscribeActions = null;

  const t = (key, variables = {}) => firstRunText(draft.locale, key, variables);

  const restoreRoot = () => {
    root.inert = previousInert;
    if (previousAriaHidden === null) root.removeAttribute("aria-hidden");
    else root.setAttribute("aria-hidden", previousAriaHidden);
  };

  const close = () => {
    if (destroyed) return;
    destroyed = true;
    networkOrdinal += 1;
    passwordDraft = "";
    unsubscribeSession?.();
    unsubscribeActions?.();
    overlay.removeEventListener("click", onClick);
    overlay.removeEventListener("input", onInput);
    overlay.removeEventListener("change", onChange);
    overlay.removeEventListener("keydown", onKeyDown);
    overlay.remove();
    restoreRoot();
  };

  const heading = (eyebrow, title, detail) => {
    const header = el(documentObject, "header", "ordax-first-run-header");
    const titleNode = el(documentObject, "h1", "", title);
    titleNode.id = "ordax-first-run-title";
    header.append(
      el(documentObject, "span", "ordax-first-run-eyebrow", eyebrow),
      titleNode,
      el(documentObject, "p", "", detail),
    );
    return header;
  };

  const renderProgress = () => {
    progress.replaceChildren();
    const brand = el(documentObject, "div", "ordax-first-run-brand");
    brand.append(el(documentObject, "strong", "", "OrdaX"), el(documentObject, "span", "", t("firstUse")));
    const list = el(documentObject, "ol", "ordax-first-run-steps");
    firstRunStepLabels(draft.locale).forEach((label, index) => {
      const item = el(documentObject, "li", "", label);
      item.dataset.state = index < stepIndex ? "done" : index === stepIndex ? "current" : "pending";
      if (index === stepIndex) item.setAttribute("aria-current", "step");
      list.append(item);
    });
    progress.append(brand, list);
  };

  const renderWelcome = (body) => {
    body.append(heading(
      t("welcomeEyebrow"),
      t("welcomeTitle"),
      t("welcomeDetail"),
    ));
    const grid = el(documentObject, "div", "ordax-first-run-grid");
    [
      [t("welcomeUsbTitle"), t("welcomeUsbDetail")],
      [t("welcomeAccountTitle"), t("welcomeAccountDetail")],
      [t("welcomeOfflineTitle"), t("welcomeOfflineDetail")],
    ].forEach(([title, detail]) => {
      const item = el(documentObject, "article", "ordax-first-run-tile");
      item.append(el(documentObject, "strong", "", title), el(documentObject, "p", "", detail));
      grid.append(item);
    });
    body.append(grid);
  };

  const renderRegional = (body) => {
    body.append(heading(
      t("regionalEyebrow"),
      t("regionalTitle"),
      t("regionalDetail"),
    ));
    const form = el(documentObject, "div", "ordax-first-run-form");
    const localeField = el(documentObject, "label", "ordax-first-run-field");
    localeField.append(el(documentObject, "span", "", t("language")));
    const locale = documentObject.createElement("select");
    locale.dataset.firstRunLocale = "";
    REGIONAL_LOCALE_OPTIONS.forEach((entry) => {
      const option = documentObject.createElement("option");
      option.value = entry.value;
      option.textContent = entry.label;
      option.selected = entry.value === draft.locale;
      locale.append(option);
    });
    localeField.append(locale);

    const zoneField = el(documentObject, "label", "ordax-first-run-field");
    zoneField.append(el(documentObject, "span", "", t("timeZone")));
    const zone = documentObject.createElement("select");
    zone.dataset.firstRunTimeZone = "";
    REGIONAL_TIME_ZONE_OPTIONS.forEach((entry) => {
      const option = documentObject.createElement("option");
      option.value = entry.value;
      option.textContent = `${entry.label} · ${entry.value}`;
      option.selected = entry.value === draft.timeZone;
      zone.append(option);
    });
    zoneField.append(zone);
    form.append(localeField, zoneField);
    body.append(form);
  };

  const renderNetwork = (body) => {
    body.append(heading(
      t("networkEyebrow"),
      t("networkTitle"),
      t("networkDetail"),
    ));
    if (!networkPort) {
      body.append(el(
        documentObject,
        "p",
        "ordax-first-run-notice",
        t("wifiUnavailable"),
      ));
      return;
    }

    const toolbar = el(documentObject, "div", "ordax-first-run-network-toolbar");
    const current = el(documentObject, "div", "ordax-first-run-network-current");
    current.append(
      el(documentObject, "span", "", networkSnapshot?.currentSsid ? t("connected") : t("wifi")),
      el(documentObject, "strong", "", networkSnapshot?.currentSsid ?? (networkSnapshot ? t("noNetwork") : t("readingState"))),
    );
    const scan = action(documentObject, networkPending ? t("wait") : t("scanNetworks"), "network-scan");
    scan.disabled = networkPending;
    toolbar.append(current, scan);
    body.append(toolbar);

    if (networkMessage) {
      const status = el(documentObject, "p", "ordax-first-run-status", networkMessage);
      status.setAttribute("role", "status");
      body.append(status);
    }
    if (!networkSnapshot) return;

    const list = el(documentObject, "div", "ordax-first-run-network-list");
    const networks = [...networkSnapshot.networks]
      .sort((left, right) => right.signalDbm - left.signalDbm)
      .slice(0, 10);
    if (networks.length === 0) {
      list.append(el(documentObject, "p", "ordax-first-run-empty", t("noNetworks")));
    }
    networks.forEach((entry) => {
      const button = action(documentObject, entry.ssid, "network-select");
      button.dataset.firstRunSsid = entry.ssid;
      button.dataset.selected = String(selectedSsid === entry.ssid);
      button.disabled = networkPending || entry.connected;
      button.append(el(
        documentObject,
        "small",
        "",
        `${entry.connected ? t("connected") : entry.saved ? t("saved") : t("available")} · ${signalLabel(entry.signalDbm, draft.locale)}`,
      ));
      list.append(button);
    });
    body.append(list);

    const selected = networkSnapshot.networks.find((entry) => entry.ssid === selectedSsid);
    if (selected && !selected.connected) {
      const connectForm = el(documentObject, "div", "ordax-first-run-connect");
      const passwordField = el(documentObject, "label", "ordax-first-run-field");
      passwordField.append(el(documentObject, "span", "", t("passwordFor", { ssid: selected.ssid })));
      const input = documentObject.createElement("input");
      input.type = "password";
      input.autocomplete = "off";
      input.dataset.firstRunWifiPassword = "";
      input.value = passwordDraft;
      input.disabled = networkPending;
      passwordField.append(input);
      const connect = action(documentObject, t("connect"), "network-connect", true);
      connect.dataset.firstRunSsid = selected.ssid;
      connect.disabled = networkPending;
      connectForm.append(passwordField, connect);
      body.append(connectForm);
    }
  };

  const renderAccount = (body) => {
    body.append(heading(
      t("accountEyebrow"),
      t("accountTitle"),
      t("accountDetail"),
    ));
    const state = el(documentObject, "article", "ordax-first-run-account");
    const copy = sessionSnapshot.state === "signed-in"
      ? t("accountSignedIn", { name: sessionSnapshot.displayName })
      : sessionSnapshot.state === "signed-out"
        ? t("accountSignedOut")
        : t("accountUnavailable");
    state.append(
      el(documentObject, "strong", "", sessionSnapshot.state === "signed-in" ? sessionSnapshot.displayName : t("accountEyebrow")),
      el(documentObject, "p", "", copy),
    );
    body.append(state);

    if (identityMessage) {
      const status = el(documentObject, "p", "ordax-first-run-status", identityMessage);
      status.setAttribute("role", "status");
      body.append(status);
    }

    const buttons = el(documentObject, "div", "ordax-first-run-account-actions");
    if (sessionSnapshot.state === "signed-in") {
      buttons.append(action(documentObject, t("useThisAccount"), "account-identity", true));
    } else {
      const signIn = action(documentObject, identityPending === "sign-in" ? t("signingIn") : t("signIn"), "account-sign-in", true);
      signIn.disabled = identityPending !== null || !isIdentityActionSupported(actionsSnapshot, "sign-in");
      const register = action(documentObject, identityPending === "register" ? t("openingRegistration") : t("createAccount"), "account-register");
      register.disabled = identityPending !== null || !isIdentityActionSupported(actionsSnapshot, "register");
      buttons.append(signIn, register);
    }
    const local = action(documentObject, t("continueWithoutAccount"), "account-local");
    local.disabled = identityPending !== null;
    buttons.append(local);
    body.append(buttons);

    if (
      sessionSnapshot.state !== "signed-in"
      && !isIdentityActionSupported(actionsSnapshot, "sign-in")
      && !isIdentityActionSupported(actionsSnapshot, "register")
    ) {
      body.append(el(
        documentObject,
        "p",
        "ordax-first-run-note",
        t("noFakePassword"),
      ));
    }
  };

  const renderPrivacy = (body) => {
    body.append(heading(
      t("privacyEyebrow"),
      t("privacyTitle"),
      t("privacyDetail"),
    ));
    const grid = el(documentObject, "div", "ordax-first-run-grid");
    [
      [t("localDataTitle"), t("localDataDetail")],
      [t("independentAccountTitle"), t("independentAccountDetail")],
      [t("noInternalDiskTitle"), t("noInternalDiskDetail")],
    ].forEach(([title, detail]) => {
      const item = el(documentObject, "article", "ordax-first-run-tile");
      item.append(el(documentObject, "strong", "", title), el(documentObject, "p", "", detail));
      grid.append(item);
    });
    body.append(grid);
  };

  const renderReady = (body) => {
    body.append(heading(
      t("readyEyebrow"),
      t("readyTitle"),
      t("readyDetail"),
    ));
    const summary = el(documentObject, "dl", "ordax-first-run-summary");
    const localeLabel = REGIONAL_LOCALE_OPTIONS.find((entry) => entry.value === draft.locale)?.label ?? draft.locale;
    [
      [t("language"), localeLabel],
      [t("timeZone"), draft.timeZone],
      [t("summaryAccount"), draft.accountMode === "identity" ? t("accountEyebrow") : t("localOnly")],
      [t("summaryExecution"), t("usbDrive")],
    ].forEach(([key, value]) => {
      summary.append(el(documentObject, "dt", "", key), el(documentObject, "dd", "", value));
    });
    body.append(summary);
    if (completionError) {
      const error = el(documentObject, "p", "ordax-first-run-error", completionError);
      error.setAttribute("role", "alert");
      body.append(error);
    }
  };

  const render = () => {
    if (destroyed) return;
    renderProgress();
    card.replaceChildren();
    const body = el(documentObject, "div", "ordax-first-run-body");
    const step = STEPS[stepIndex];
    if (step === "welcome") renderWelcome(body);
    else if (step === "regional") renderRegional(body);
    else if (step === "network") renderNetwork(body);
    else if (step === "account") renderAccount(body);
    else if (step === "privacy") renderPrivacy(body);
    else renderReady(body);

    const footer = el(documentObject, "footer", "ordax-first-run-footer");
    if (stepIndex > 0 && !finishing) footer.append(action(documentObject, t("back"), "back"));
    if (step !== "account") {
      const label = step === "ready"
        ? finishing ? t("saving") : t("enterOrdax")
        : step === "network" ? t("continueConnectedOrOffline") : t("continue");
      const next = action(documentObject, label, step === "ready" ? "finish" : "next", true);
      next.disabled = finishing;
      footer.append(next);
    }
    card.append(body, footer);
  };

  const go = (nextIndex) => {
    if (STEPS[stepIndex] === "network") passwordDraft = "";
    stepIndex = Math.max(0, Math.min(STEPS.length - 1, nextIndex));
    completionError = "";
    render();
    if (STEPS[stepIndex] === "network" && networkPort && networkSnapshot === null) {
      void refreshNetwork(false);
    }
  };

  const refreshNetwork = async (scan) => {
    if (!networkPort || destroyed || networkPending) return;
    const ordinal = ++networkOrdinal;
    networkPending = true;
    networkMessage = scan ? networkManagementActionMessage("scan", 0) : t("readingWifi");
    render();
    try {
      networkSnapshot = await (scan ? networkPort.scan() : networkPort.status());
      if (destroyed || ordinal !== networkOrdinal) return;
      networkMessage = scan ? networkManagementActionMessage("scan", 1) : "";
      if (selectedSsid && !networkSnapshot.networks.some((entry) => entry.ssid === selectedSsid)) {
        selectedSsid = null;
        passwordDraft = "";
      }
    } catch (error) {
      if (destroyed || ordinal !== networkOrdinal) return;
      networkMessage = scan
        ? networkManagementFailureMessage("scan", error)
        : t("wifiReadFailed");
    } finally {
      if (!destroyed && ordinal === networkOrdinal) {
        networkPending = false;
        render();
      }
    }
  };

  const connectNetwork = async (ssid, password) => {
    if (!networkPort || destroyed || networkPending) return;
    const ordinal = ++networkOrdinal;
    networkPending = true;
    networkMessage = networkManagementActionMessage("connect", 0);
    passwordDraft = "";
    render();
    try {
      networkSnapshot = await runNetworkManagementAction(networkPort, "connect", { ssid, password });
      if (destroyed || ordinal !== networkOrdinal) return;
      selectedSsid = null;
      networkMessage = networkManagementActionMessage("connect", 1);
    } catch (error) {
      if (destroyed || ordinal !== networkOrdinal) return;
      networkMessage = networkManagementFailureMessage("connect", error);
    } finally {
      if (!destroyed && ordinal === networkOrdinal) {
        networkPending = false;
        render();
      }
    }
  };

  const runIdentity = async (kind) => {
    if (destroyed || identityPending || !isIdentityActionSupported(actionsSnapshot, kind)) return;
    identityPending = kind;
    identityMessage = "";
    render();
    try {
      await actionsPort.execute(kind);
      if (destroyed) return;
      sessionSnapshot = sessionPort.getSnapshot();
      actionsSnapshot = actionsPort.getSnapshot();
      identityMessage = sessionSnapshot.state === "signed-in"
        ? t("identitySuccess")
        : t("identityStarted");
    } catch {
      if (!destroyed) identityMessage = t("identityFailed");
    } finally {
      if (!destroyed) {
        identityPending = null;
        render();
      }
    }
  };

  const finish = async () => {
    if (destroyed || finishing || draft.accountMode === null) return;
    finishing = true;
    completionError = "";
    render();
    try {
      preferencePort.set(REGIONAL_LOCALE_PREFERENCE_ID, draft.locale);
      preferencePort.set(REGIONAL_TIME_ZONE_PREFERENCE_ID, draft.timeZone);
      await store.save(completeFirstRunState(draft));
      close();
    } catch {
      if (destroyed) return;
      finishing = false;
      completionError = t("persistFailed");
      render();
    }
  };

  const onClick = (event) => {
    const button = event.target.closest("[data-first-run-action]");
    if (!button || !overlay.contains(button) || button.disabled) return;
    const kind = button.dataset.firstRunAction;
    if (kind === "back") go(stepIndex - 1);
    else if (kind === "next") go(stepIndex + 1);
    else if (kind === "finish") void finish();
    else if (kind === "network-scan") void refreshNetwork(true);
    else if (kind === "network-select") {
      const ssid = button.dataset.firstRunSsid ?? null;
      if (ssid !== selectedSsid) passwordDraft = "";
      selectedSsid = ssid;
      networkMessage = "";
      render();
      overlay.querySelector("[data-first-run-wifi-password]")?.focus();
    } else if (kind === "network-connect") {
      const input = overlay.querySelector("[data-first-run-wifi-password]");
      const ssid = button.dataset.firstRunSsid;
      if (!(input instanceof HTMLInputElement) || !ssid) return;
      const password = input.value;
      input.value = "";
      passwordDraft = "";
      if (!password) {
        networkMessage = t("enterWifiPassword");
        render();
      } else {
        void connectNetwork(ssid, password);
      }
    } else if (kind === "account-sign-in") void runIdentity("sign-in");
    else if (kind === "account-register") void runIdentity("register");
    else if (kind === "account-identity" && sessionSnapshot.state === "signed-in") {
      draft.accountMode = "identity";
      go(stepIndex + 1);
    } else if (kind === "account-local") {
      draft.accountMode = "local-only";
      go(stepIndex + 1);
    }
  };

  const onInput = (event) => {
    const input = event.target.closest("[data-first-run-wifi-password]");
    if (input instanceof HTMLInputElement && overlay.contains(input)) passwordDraft = input.value;
  };

  const onChange = (event) => {
    if (event.target.matches("[data-first-run-locale]")) {
      draft.locale = event.target.value;
      render();
      queueMicrotask(() => overlay.querySelector("[data-first-run-locale]")?.focus?.());
    } else if (event.target.matches("[data-first-run-time-zone]")) {
      draft.timeZone = event.target.value;
    }
  };

  const onKeyDown = (event) => {
    if (event.key !== "Enter") return;
    const input = event.target.closest("[data-first-run-wifi-password]");
    if (input && overlay.contains(input)) {
      event.preventDefault();
      overlay.querySelector('[data-first-run-action="network-connect"]')?.click();
    }
  };

  overlay.addEventListener("click", onClick);
  overlay.addEventListener("input", onInput);
  overlay.addEventListener("change", onChange);
  overlay.addEventListener("keydown", onKeyDown);

  unsubscribeSession = sessionPort.subscribe((snapshot) => {
    sessionSnapshot = snapshot;
    if (!destroyed && STEPS[stepIndex] === "account") render();
  });
  unsubscribeActions = actionsPort.subscribe((snapshot) => {
    actionsSnapshot = snapshot;
    if (!destroyed && STEPS[stepIndex] === "account") render();
  });

  render();
  queueMicrotask(() => overlay.querySelector("button, select, input")?.focus?.());

  return Object.freeze({
    shown: true,
    destroy() {
      close();
    },
  });
}
