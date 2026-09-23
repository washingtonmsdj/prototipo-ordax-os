import { assertAppActivationPort } from "../../contracts/app-activation.mjs";
import { assertNotificationsPort } from "../../contracts/notifications.mjs";
import {
  assertLocalSessionPort,
  validateLocalSessionSnapshot,
} from "../../contracts/local-session.mjs";
import {
  assertKeyboardLayoutPort,
  validateKeyboardLayoutSnapshot,
} from "../../contracts/keyboard-layout.mjs";
import {
  assertNetworkManagementPort,
  validateNetworkManagementSnapshot,
} from "../../contracts/network-management.mjs";
import { assertPreferenceRuntimePort } from "../../contracts/preference-runtime.mjs";
import {
  assertNetworkStatusPort,
  validateNetworkStatusSnapshot,
} from "../../contracts/network-status.mjs";
import {
  assertSurfaceHost,
  validateSurfaceSnapshot,
} from "../../contracts/surface-host.mjs";
import {
  networkManagementActionMessage,
  networkManagementFailureMessage,
  runNetworkManagementAction,
} from "../../services/network/management-runtime.mjs";
import {
  listNotificationSources,
  notificationSourceDescription,
  notificationSourceLabel,
} from "../../services/notifications/catalog.mjs";
import { KEYBOARD_LAYOUT_OPTIONS } from "../../services/input/keyboard-layout.mjs";
import { listPreferenceDefinitions } from "../../services/preferences/catalog.mjs";
import { assertSurfaceRenderLifecycle } from "../../contracts/surface-render-lifecycle.mjs";

const SETTINGS_WINDOW_SELECTOR = '[data-window-id="settings"]';
const SETTINGS_EXTENSION_SELECTOR = '[data-app-extension="settings-overview"]';

const SETTINGS_SECTIONS = Object.freeze([
  Object.freeze({ id: "appearance", messageId: "settings.section.appearance" }),
  Object.freeze({ id: "accessibility", messageId: "settings.section.accessibility" }),
  Object.freeze({ id: "regional", messageId: "settings.section.regional" }),
  Object.freeze({ id: "network", messageId: "settings.section.network" }),
  Object.freeze({ id: "security", messageId: "settings.section.security" }),
  Object.freeze({ id: "notifications", messageId: "settings.section.notifications" }),
]);

function validSettingsSection(value) {
  return SETTINGS_SECTIONS.some((section) => section.id === value);
}

function node(documentObject, tag, className, text) {
  const element = documentObject.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function formatReceivedAt(value) {
  if (!Number.isFinite(value)) return "horário desconhecido";
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Bahia",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function optionDescription(preferenceId, value) {
  if (preferenceId === "appearance.theme") {
    return value === "dark"
      ? "Contraste escuro para ambientes de pouca luz."
      : "Superfície clara e neutra como padrão do OrdaX.";
  }
  if (preferenceId === "accessibility.contrast") {
    return value === "high"
      ? "Reforça separadores, texto secundário e foco da Surface."
      : "Usa o contraste padrão do tema escolhido.";
  }
  if (preferenceId === "accessibility.motion") {
    return value === "reduced"
      ? "Remove animações e transições não essenciais."
      : "Mantém movimento quando a preferência do ambiente também permite.";
  }
  if (preferenceId === "accessibility.text-scale") {
    if (value === "large") return "Aumenta a tipografia da Surface mantendo o layout responsivo.";
    if (value === "extra-large") return "Amplia ainda mais a tipografia e preserva rolagem nas áreas de conteúdo.";
    return "Mantém a escala tipográfica padrão e respeita o zoom do navegador.";
  }
  if (preferenceId === "regional.locale") {
    return value === "pt-BR"
      ? "Português (Brasil) é o idioma completo desta versão."
      : String(value);
  }
  if (preferenceId === "regional.time-zone") {
    return `Usa ${value} para relógio e datas da Surface.`;
  }
  return String(value);
}

export function mountSettingsOverviewControls(
  root,
  host,
  preferenceRuntime,
  surfaceLifecycle = null,
  networkStatus = null,
  networkManagement = null,
  appActivation = null,
  notifications = null,
  keyboardLayout = null,
  localSession = null,
) {
  if (!(root instanceof Element)) {
    throw new TypeError("Settings overview controls require a Surface root Element");
  }
  const hostPort = assertSurfaceHost(host);
  const preferences = assertPreferenceRuntimePort(preferenceRuntime);
  const lifecycle = assertSurfaceRenderLifecycle(surfaceLifecycle);
  const localization = lifecycle.localization;
  const t = localization.translate;
  const networkPort = networkStatus === null ? null : assertNetworkStatusPort(networkStatus);
  const networkManagementPort =
    networkManagement === null ? null : assertNetworkManagementPort(networkManagement);
  const activationPort = appActivation === null ? null : assertAppActivationPort(appActivation);
  const notificationPort = notifications === null ? null : assertNotificationsPort(notifications);
  const keyboardLayoutPort =
    keyboardLayout === null ? null : assertKeyboardLayoutPort(keyboardLayout);
  const localSessionPort =
    localSession === null ? null : assertLocalSessionPort(localSession);
  const documentObject = root.ownerDocument;

  let hostSnapshot = validateSurfaceSnapshot(hostPort.getSnapshot());
  let preferenceSnapshot = preferences.getSnapshot();
  let networkSnapshot = null;
  let networkReadFailed = false;
  let networkLastSuccessAt = null;
  let networkManagementSnapshot = null;
  let notificationSnapshot = notificationPort?.getSnapshot() ?? null;
  let keyboardLayoutSnapshot = null;
  let keyboardLayoutReadFailed = false;
  let keyboardLayoutPending = false;
  let keyboardLayoutMessage = "";
  let keyboardLayoutOrdinal = 0;
  let localSessionSnapshot = localSessionPort === null
    ? null
    : validateLocalSessionSnapshot(localSessionPort.getSnapshot());
  let localSessionPending = false;
  let localSessionMessage = "";
  let networkManagementReadFailed = false;
  let networkManagementLastSuccessAt = null;
  let networkManagementPending = false;
  let networkManagementMessage = "";
  let networkReadOrdinal = 0;
  let networkManagementReadOrdinal = 0;
  let networkActionOrdinal = 0;
  let selectedNetworkSsid = null;
  let activeSection = validSettingsSection(lifecycle.getAppTarget("settings"))
    ? lifecycle.getAppTarget("settings")
    : "appearance";
  let destroyed = false;
  let mountedSlot = null;

  const findSlot = () =>
    root.querySelector(`${SETTINGS_WINDOW_SELECTOR} ${SETTINGS_EXTENSION_SELECTOR}`);

  const focusIdentity = (element) => {
    if (!element || !element.dataset) return null;
    if (element.dataset.settingsWifiPasswordFor) {
      return Object.freeze({
        kind: "wifi-password",
        value: element.dataset.settingsWifiPasswordFor,
      });
    }
    if (element.dataset.settingsSection) {
      return Object.freeze({ kind: "section", value: element.dataset.settingsSection });
    }
    if (element.dataset.settingsWifiSsid && !element.dataset.settingsNetworkAction) {
      return Object.freeze({ kind: "wifi-network", value: element.dataset.settingsWifiSsid });
    }
    if (element.dataset.settingsNetworkAction) {
      return Object.freeze({
        kind: "network-action",
        value: element.dataset.settingsNetworkAction,
        ssid: element.dataset.settingsWifiSsid ?? null,
      });
    }
    if (element.dataset.settingsKeyboardLayout) {
      return Object.freeze({
        kind: "keyboard-layout",
        value: element.dataset.settingsKeyboardLayout,
      });
    }
    if (element.dataset.settingsNotificationDnd !== undefined) {
      return Object.freeze({ kind: "notification-dnd", value: "dnd" });
    }
    if (element.dataset.settingsNotificationSource) {
      return Object.freeze({
        kind: "notification-source",
        value: element.dataset.settingsNotificationSource,
      });
    }
    if (element.dataset.settingsPreferenceId) {
      return Object.freeze({
        kind: "preference",
        value: element.dataset.settingsPreferenceId,
        option: element.dataset.settingsPreferenceValue ?? "",
      });
    }
    return null;
  };

  const findFocusTarget = (slot, identity) => {
    if (!identity) return null;
    const candidates = Array.from(slot.querySelectorAll("button, input"));
    return candidates.find((element) => {
      const candidate = focusIdentity(element);
      return candidate
        && candidate.kind === identity.kind
        && candidate.value === identity.value
        && (candidate.ssid ?? null) === (identity.ssid ?? null)
        && (candidate.option ?? "") === (identity.option ?? "");
    }) ?? null;
  };

  const captureInteractionState = (slot) => {
    const windowBody = slot.closest(".ordax-window-body");
    const passwordInput = slot.querySelector("[data-settings-wifi-password]");
    const activeElement = documentObject.activeElement;
    const activeInside = activeElement && slot.contains(activeElement);
    return {
      scrollTop: windowBody?.scrollTop ?? 0,
      scrollLeft: windowBody?.scrollLeft ?? 0,
      focus: activeInside ? focusIdentity(activeElement) : null,
      password:
        passwordInput instanceof HTMLInputElement
          ? {
              ssid: passwordInput.dataset.settingsWifiPasswordFor ?? "",
              value: passwordInput.value,
              selectionStart: passwordInput.selectionStart,
              selectionEnd: passwordInput.selectionEnd,
            }
          : null,
    };
  };

  const restoreInteractionState = (slot, snapshot) => {
    if (!snapshot) return;
    const windowBody = slot.closest(".ordax-window-body");
    if (windowBody) {
      windowBody.scrollTop = snapshot.scrollTop;
      windowBody.scrollLeft = snapshot.scrollLeft;
    }

    if (snapshot.password?.ssid) {
      const passwordInput = slot.querySelector("[data-settings-wifi-password]");
      if (
        passwordInput instanceof HTMLInputElement
        && passwordInput.dataset.settingsWifiPasswordFor === snapshot.password.ssid
      ) {
        passwordInput.value = snapshot.password.value;
        if (
          snapshot.password.selectionStart !== null
          && snapshot.password.selectionEnd !== null
        ) {
          passwordInput.setSelectionRange(
            snapshot.password.selectionStart,
            snapshot.password.selectionEnd,
          );
        }
      }
    }

    const focusTarget = findFocusTarget(slot, snapshot.focus);
    if (focusTarget && !focusTarget.disabled) {
      focusTarget.focus({ preventScroll: true });
    }
  };

  const renderHeader = (view) => {
    const header = node(documentObject, "header", "ordax-settings-header");
    header.append(
      node(documentObject, "span", "ordax-settings-eyebrow", t("settings.eyebrow")),
      node(documentObject, "h3", "ordax-settings-title", t(`settings.section.${activeSection}`)),
      node(
        documentObject,
        "p",
        "ordax-settings-subtitle",
        t(`settings.section.${activeSection}.subtitle`),
      ),
    );
    view.append(header);
  };

  const renderSectionNavigation = (view) => {
    const navigation = node(documentObject, "nav", "ordax-settings-navigation");
    navigation.setAttribute("aria-label", t("settings.navigation.aria"));
    for (const section of SETTINGS_SECTIONS) {
      const button = node(
        documentObject,
        "button",
        "ordax-settings-navigation-item",
        t(section.messageId),
      );
      button.type = "button";
      button.dataset.settingsSection = section.id;
      const active = activeSection === section.id;
      button.dataset.active = String(active);
      button.setAttribute("aria-current", active ? "page" : "false");
      navigation.append(button);
    }
    view.append(navigation);
  };

  const renderPreferences = (view, sectionId) => {
    for (const definition of listPreferenceDefinitions()) {
      if (definition.sectionId !== sectionId) continue;
      const section = node(documentObject, "section", "ordax-settings-section");
      section.append(
        node(
          documentObject,
          "span",
          "ordax-settings-section-kicker",
          definition.label ?? t("settings.preference.fallbackLabel"),
        ),
        node(documentObject, "h4", "ordax-settings-section-title", definition.title ?? definition.id),
        node(documentObject, "p", "ordax-settings-section-copy", definition.description ?? definition.id),
      );

      if (Array.isArray(definition.options) && definition.options.length > 0) {
        const options = node(documentObject, "div", "ordax-settings-options");
        for (const option of definition.options) {
          const selected = preferenceSnapshot[definition.id] === option.value;
          const button = node(documentObject, "button", "ordax-settings-option");
          button.type = "button";
          button.dataset.settingsPreferenceId = definition.id;
          button.dataset.settingsPreferenceValue = option.value;
          button.dataset.selected = String(selected);
          button.setAttribute("aria-pressed", String(selected));

          const preview = node(documentObject, "span", "ordax-settings-theme-preview");
          preview.dataset.themePreview = option.value;
          preview.setAttribute("aria-hidden", "true");
          const previewRail = node(documentObject, "span", "ordax-settings-theme-rail");
          const previewBody = node(documentObject, "span", "ordax-settings-theme-body");
          preview.append(previewRail, previewBody);

          const copy = node(documentObject, "span", "ordax-settings-option-copy");
          copy.append(
            node(documentObject, "strong", "", option.label),
            node(documentObject, "small", "", optionDescription(definition.id, option.value)),
          );
          const marker = node(documentObject, "span", "ordax-settings-option-marker", selected ? "Ativo" : "");
          button.append(preview, copy, marker);
          options.append(button);
        }
        section.append(options);
      }
      view.append(section);
    }
  };

  const renderKeyboardLayout = (view) => {
    if (!keyboardLayoutPort) return;

    const section = node(documentObject, "section", "ordax-settings-section");
    section.dataset.settingsKeyboardLayoutSection = "";
    section.append(
      node(documentObject, "span", "ordax-settings-section-kicker", "Teclado físico"),
      node(documentObject, "h4", "ordax-settings-section-title", "Layout do teclado"),
      node(
        documentObject,
        "p",
        "ordax-settings-section-copy",
        "O layout é aplicado pelo Cage antes da Surface iniciar. A escolha fica salva no USB e, quando diferente do layout atual, entra em vigor no próximo início da Surface.",
      ),
    );

    if (keyboardLayoutMessage) {
      const status = node(
        documentObject,
        "p",
        "ordax-settings-keyboard-message",
        keyboardLayoutMessage,
      );
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      section.append(status);
    }

    if (keyboardLayoutReadFailed && keyboardLayoutSnapshot === null) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-settings-empty",
          "O layout do teclado físico está temporariamente indisponível neste host.",
        ),
      );
      view.append(section);
      return;
    }

    if (keyboardLayoutSnapshot === null) {
      section.append(node(documentObject, "p", "ordax-settings-empty", "Lendo layout do teclado…"));
      view.append(section);
      return;
    }

    const stateCopy = keyboardLayoutSnapshot.restartRequired
      ? "Alteração salva · será aplicada no próximo início da Surface."
      : "O layout configurado já está em uso nesta Surface.";
    const state = node(documentObject, "p", "ordax-settings-keyboard-state", stateCopy);
    state.dataset.restartRequired = String(keyboardLayoutSnapshot.restartRequired);
    section.append(state);

    const options = node(documentObject, "div", "ordax-settings-keyboard-options");
    for (const option of KEYBOARD_LAYOUT_OPTIONS) {
      if (!keyboardLayoutSnapshot.supportedLayoutIds.includes(option.id)) continue;
      const selected = keyboardLayoutSnapshot.configuredLayoutId === option.id;
      const applied = keyboardLayoutSnapshot.appliedLayoutId === option.id;
      const button = node(documentObject, "button", "ordax-settings-keyboard-option");
      button.type = "button";
      button.dataset.settingsKeyboardLayout = option.id;
      button.dataset.selected = String(selected);
      button.setAttribute("aria-pressed", String(selected));
      button.disabled = keyboardLayoutPending;

      const copy = node(documentObject, "span", "ordax-settings-keyboard-copy");
      copy.append(
        node(documentObject, "strong", "", option.label),
        node(documentObject, "small", "", option.description),
      );
      const markerLabel = selected
        ? applied ? "Em uso" : "Próximo início"
        : applied ? "Atual" : "";
      button.append(
        copy,
        node(documentObject, "span", "ordax-settings-keyboard-marker", markerLabel),
      );
      options.append(button);
    }
    section.append(options);
    view.append(section);
  };

  const renderSecurity = (view) => {
    const section = node(documentObject, "section", "ordax-settings-section");
    section.dataset.settingsSecurity = "";
    section.append(
      node(documentObject, "span", "ordax-settings-section-kicker", "Sessão local"),
      node(documentObject, "h4", "ordax-settings-section-title", "Bloqueio deste OrdaX"),
      node(
        documentObject,
        "p",
        "ordax-settings-section-copy",
        "A credencial fica somente neste dispositivo e não depende da Conta. "
          + "Este recurso bloqueia a Surface em execução; ele não criptografa os arquivos do pendrive.",
      ),
    );

    if (!localSessionPort || !localSessionSnapshot) {
      section.append(
        node(documentObject, "p", "ordax-settings-empty", "O owner de sessão local não está disponível nesta execução."),
      );
      view.append(section);
      return;
    }

    section.append(
      node(
        documentObject,
        "p",
        "ordax-settings-section-copy",
        localSessionSnapshot.credentialConfigured
          ? "PIN/senha local configurado. O próximo início da Surface começa bloqueado."
          : "Nenhum PIN/senha local configurado. O bloqueio autenticado fica desativado.",
      ),
    );

    const form = node(documentObject, "div", "ordax-settings-security-form");
    if (!localSessionSnapshot.credentialConfigured) {
      const secret = documentObject.createElement("input");
      secret.type = "password";
      secret.autocomplete = "new-password";
      secret.minLength = 6;
      secret.maxLength = 128;
      secret.placeholder = "Novo PIN ou senha local";
      secret.dataset.settingsLocalSessionSecret = "";
      secret.disabled = localSessionPending;
      const confirm = documentObject.createElement("input");
      confirm.type = "password";
      confirm.autocomplete = "new-password";
      confirm.minLength = 6;
      confirm.maxLength = 128;
      confirm.placeholder = "Confirmar PIN ou senha";
      confirm.dataset.settingsLocalSessionConfirm = "";
      confirm.disabled = localSessionPending;
      const configure = node(documentObject, "button", "ordax-settings-notification-action", localSessionPending ? "Salvando…" : "Configurar bloqueio");
      configure.type = "button";
      configure.dataset.settingsLocalSessionAction = "configure";
      configure.disabled = localSessionPending;
      form.append(secret, confirm, configure);
    } else {
      const lock = node(documentObject, "button", "ordax-settings-notification-action", "Bloquear agora");
      lock.type = "button";
      lock.dataset.settingsLocalSessionAction = "lock";
      lock.disabled = localSessionPending;
      const current = documentObject.createElement("input");
      current.type = "password";
      current.autocomplete = "current-password";
      current.minLength = 6;
      current.maxLength = 128;
      current.placeholder = "PIN/senha atual para remover";
      current.dataset.settingsLocalSessionCurrent = "";
      current.disabled = localSessionPending;
      const remove = node(documentObject, "button", "ordax-settings-notification-action", "Remover bloqueio");
      remove.type = "button";
      remove.dataset.settingsLocalSessionAction = "remove";
      remove.disabled = localSessionPending;
      form.append(lock, current, remove);
    }
    section.append(form);

    if (localSessionMessage) {
      const message = node(documentObject, "p", "ordax-settings-section-copy", localSessionMessage);
      message.setAttribute("role", "status");
      message.setAttribute("aria-live", "polite");
      section.append(message);
    }
    view.append(section);
  };

  const renderNotifications = (view) => {
    const policySection = node(documentObject, "section", "ordax-settings-section");
    policySection.dataset.settingsNotifications = "";
    policySection.append(
      node(
        documentObject,
        "span",
        "ordax-settings-section-kicker",
        t("settings.notifications.presentation.kicker"),
      ),
      node(
        documentObject,
        "h4",
        "ordax-settings-section-title",
        t("settings.notifications.dnd.title"),
      ),
      node(
        documentObject,
        "p",
        "ordax-settings-section-copy",
        t("settings.notifications.dnd.description"),
      ),
    );

    if (!notificationPort || !notificationSnapshot) {
      policySection.append(
        node(
          documentObject,
          "p",
          "ordax-settings-empty",
          t("settings.notifications.unavailable"),
        ),
      );
      view.append(policySection);
      return;
    }

    const dndRow = node(documentObject, "div", "ordax-settings-notification-row");
    const dndCopy = node(documentObject, "span", "ordax-settings-notification-copy");
    dndCopy.append(
      node(
        documentObject,
        "strong",
        "",
        notificationSnapshot.doNotDisturb
          ? t("settings.notifications.dnd.active")
          : t("settings.notifications.dnd.inactive"),
      ),
      node(
        documentObject,
        "small",
        "",
        notificationSnapshot.doNotDisturb
          ? t("settings.notifications.dnd.activeDetail")
          : t("settings.notifications.dnd.inactiveDetail"),
      ),
    );
    const dndButton = node(
      documentObject,
      "button",
      "ordax-settings-notification-action",
      notificationSnapshot.doNotDisturb
        ? t("settings.notifications.action.disable")
        : t("settings.notifications.action.enable"),
    );
    dndButton.type = "button";
    dndButton.dataset.settingsNotificationDnd = "";
    dndButton.setAttribute("aria-pressed", String(notificationSnapshot.doNotDisturb));
    dndRow.append(dndCopy, dndButton);
    policySection.append(dndRow);

    const sourceSection = node(documentObject, "section", "ordax-settings-section");
    sourceSection.append(
      node(
        documentObject,
        "span",
        "ordax-settings-section-kicker",
        t("settings.notifications.sources.kicker"),
      ),
      node(
        documentObject,
        "h4",
        "ordax-settings-section-title",
        t("settings.notifications.sources.title"),
      ),
      node(
        documentObject,
        "p",
        "ordax-settings-section-copy",
        t("settings.notifications.sources.description"),
      ),
    );

    for (const source of listNotificationSources()) {
      const enabled = !notificationSnapshot.disabledSources.includes(source.id);
      const row = node(documentObject, "div", "ordax-settings-notification-row");
      row.dataset.enabled = String(enabled);
      const copy = node(documentObject, "span", "ordax-settings-notification-copy");
      copy.append(
        node(documentObject, "strong", "", notificationSourceLabel(source.id, t)),
        node(documentObject, "small", "", notificationSourceDescription(source.id, t)),
      );
      const action = node(
        documentObject,
        "button",
        "ordax-settings-notification-action",
        enabled
          ? t("settings.notifications.action.disable")
          : t("settings.notifications.action.enable"),
      );
      action.type = "button";
      action.dataset.settingsNotificationSource = source.id;
      action.setAttribute("aria-pressed", String(enabled));
      row.append(copy, action);
      sourceSection.append(row);
    }

    sourceSection.append(
      node(
        documentObject,
        "p",
        "ordax-settings-notification-persistence",
        notificationSnapshot.policyPersistence === "device"
          ? t("settings.notifications.persistence.device")
          : t("settings.notifications.persistence.session"),
      ),
    );
    view.append(policySection, sourceSection);
  };

  const renderNetworkManagement = (section) => {
    if (!networkManagementPort) return;

    const panel = node(documentObject, "div", "ordax-settings-wifi");
    panel.dataset.settingsWifi = "";

    const heading = node(documentObject, "div", "ordax-settings-wifi-heading");
    const headingCopy = node(documentObject, "div", "ordax-settings-wifi-heading-copy");
    headingCopy.append(
      node(documentObject, "strong", "", "Wi-Fi"),
      node(
        documentObject,
        "span",
        "",
        networkManagementSnapshot?.currentSsid
          ? `Conectado a ${networkManagementSnapshot.currentSsid}`
          : networkManagementSnapshot?.savedSsid
            ? `Rede salva: ${networkManagementSnapshot.savedSsid}`
            : "Nenhuma rede Wi-Fi conectada",
      ),
    );

    const actions = node(documentObject, "div", "ordax-settings-wifi-actions");
    const addAction = (action, label) => {
      const button = node(documentObject, "button", "ordax-settings-network-action", label);
      button.type = "button";
      button.dataset.settingsNetworkAction = action;
      button.disabled =
        networkManagementPending
        || (networkManagementReadFailed && action !== "scan");
      actions.append(button);
    };
    addAction("scan", networkManagementPending ? "Aguarde…" : "Procurar redes");
    if (networkManagementSnapshot?.currentSsid) addAction("disconnect", "Desconectar");
    if (networkManagementSnapshot?.savedSsid) {
      if (!networkManagementSnapshot.currentSsid) addAction("reconnect", "Reconectar");
      addAction("forget", "Esquecer");
    }
    heading.append(headingCopy, actions);
    panel.append(heading);

    const message = node(
      documentObject,
      "p",
      "ordax-settings-network-message",
      networkManagementMessage,
    );
    message.setAttribute("role", "status");
    message.setAttribute("aria-live", "polite");
    if (networkManagementMessage) panel.append(message);

    if (networkManagementReadFailed && networkManagementSnapshot === null) {
      panel.append(
        node(
          documentObject,
          "p",
          "ordax-settings-empty",
          "O gerenciamento de Wi-Fi está temporariamente indisponível e ainda não há uma leitura válida nesta sessão.",
        ),
      );
      section.append(panel);
      return;
    }

    if (networkManagementReadFailed && networkManagementSnapshot !== null) {
      panel.append(
        node(
          documentObject,
          "p",
          "ordax-settings-network-message",
          `Dados de Wi-Fi antigos · última leitura recebida pela Surface às ${formatReceivedAt(networkManagementLastSuccessAt)}. Uma nova leitura será tentada automaticamente.`,
        ),
      );
    }

    if (networkManagementSnapshot === null) {
      panel.append(node(documentObject, "p", "ordax-settings-empty", "Lendo estado do Wi-Fi…"));
      section.append(panel);
      return;
    }

    const networks = node(documentObject, "div", "ordax-settings-wifi-list");
    if (networkManagementSnapshot.networks.length === 0) {
      networks.append(
        node(
          documentObject,
          "p",
          "ordax-settings-empty",
          "Use “Procurar redes” para listar redes Wi-Fi compatíveis próximas.",
        ),
      );
    } else {
      for (const entry of networkManagementSnapshot.networks) {
        const button = node(documentObject, "button", "ordax-settings-wifi-network");
        button.type = "button";
        button.dataset.settingsWifiSsid = entry.ssid;
        button.dataset.selected = String(selectedNetworkSsid === entry.ssid);
        button.dataset.connected = String(entry.connected);
        button.disabled = networkManagementPending || networkManagementReadFailed;
        button.setAttribute("aria-pressed", String(selectedNetworkSsid === entry.ssid));

        const copy = node(documentObject, "span", "ordax-settings-wifi-network-copy");
        const state = entry.connected
          ? "Conectada"
          : entry.saved
            ? "Salva"
            : "Disponível";
        copy.append(
          node(documentObject, "strong", "", entry.ssid),
          node(documentObject, "small", "", `${state} · sinal ${entry.signalDbm} dBm · WPA/WPA2`),
        );
        button.append(
          node(documentObject, "span", "ordax-settings-network-dot"),
          copy,
        );
        networks.append(button);
      }
    }
    panel.append(networks);

    const selected = networkManagementSnapshot.networks.find(
      (entry) => entry.ssid === selectedNetworkSsid,
    );
    if (selected && !selected.connected && !selected.saved) {
      const form = node(documentObject, "div", "ordax-settings-wifi-connect");
      const label = node(
        documentObject,
        "label",
        "ordax-settings-wifi-password-label",
        `Senha de “${selected.ssid}”`,
      );
      const input = node(documentObject, "input", "ordax-settings-wifi-password");
      input.type = "password";
      input.autocomplete = "off";
      input.spellcheck = false;
      input.disabled = networkManagementPending || networkManagementReadFailed;
      input.dataset.settingsWifiPassword = "";
      input.dataset.settingsWifiPasswordFor = selected.ssid;
      input.setAttribute("aria-label", `Senha da rede ${selected.ssid}`);
      label.append(input);

      const connect = node(
        documentObject,
        "button",
        "ordax-settings-network-action ordax-settings-network-primary",
        networkManagementPending ? "Conectando…" : "Conectar",
      );
      connect.type = "button";
      connect.dataset.settingsNetworkAction = "connect";
      connect.dataset.settingsWifiSsid = selected.ssid;
      connect.disabled = networkManagementPending || networkManagementReadFailed;
      form.append(label, connect);
      panel.append(form);
    }

    section.append(panel);
  };

  const renderNetwork = (view) => {
    const section = node(documentObject, "section", "ordax-settings-section");
    section.dataset.settingsNetwork = "";
    section.append(
      node(documentObject, "span", "ordax-settings-section-kicker", "Rede"),
      node(documentObject, "h4", "ordax-settings-section-title", "Rede e conexões"),
      node(
        documentObject,
        "p",
        "ordax-settings-section-copy",
        networkManagementPort
          ? "Estado real do host e gerenciamento Wi-Fi pelo owner nativo. Senhas são usadas apenas no instante da conexão e não entram em preferências ou sincronização."
          : "Estado real observado no host nativo. O gerenciamento de Wi-Fi não está disponível neste ambiente.",
      ),
    );

    const service = node(documentObject, "div", "ordax-settings-network-service");
    service.dataset.state = hostSnapshot.connectivity;
    const serviceLabels = {
      online: "Conectividade do host disponível",
      offline: "Host sem conectividade",
      unknown: "Conectividade do host desconhecida",
    };
    service.append(
      node(documentObject, "span", "ordax-settings-network-dot"),
      node(documentObject, "strong", "", serviceLabels[hostSnapshot.connectivity] ?? serviceLabels.unknown),
    );
    section.append(service);

    if (networkPort) {
      if (networkReadFailed && networkSnapshot === null) {
        section.append(
          node(
            documentObject,
            "p",
            "ordax-settings-empty",
            "Os detalhes das interfaces estão temporariamente indisponíveis e ainda não há uma leitura válida nesta sessão.",
          ),
        );
      } else {
        if (networkReadFailed && networkSnapshot !== null) {
          section.append(
            node(
              documentObject,
              "p",
              "ordax-settings-network-message",
              `Dados de interface antigos · última leitura recebida pela Surface às ${formatReceivedAt(networkLastSuccessAt)}.`,
            ),
          );
        }
        if (networkSnapshot === null) {
          section.append(node(documentObject, "p", "ordax-settings-empty", "Lendo interfaces de rede…"));
        } else {
        const interfaces = node(documentObject, "div", "ordax-settings-network-list");
        if (networkSnapshot.interfaces.length === 0) {
          interfaces.append(
            node(documentObject, "p", "ordax-settings-empty", "Nenhuma interface de rede utilizável foi observada."),
          );
        } else {
          const kindLabels = { wifi: "Wi-Fi", ethernet: "Cabo", other: "Outra interface" };
          const stateLabels = {
            connected: "Conectado",
            disconnected: "Desconectado",
            unknown: "Estado desconhecido",
          };
          for (const entry of networkSnapshot.interfaces) {
            const item = node(documentObject, "div", "ordax-settings-network-item");
            item.dataset.state = entry.state;
            const copy = node(documentObject, "span", "ordax-settings-network-copy");
            copy.append(
              node(documentObject, "strong", "", kindLabels[entry.kind] ?? kindLabels.other),
              node(
                documentObject,
                "small",
                "",
                `${entry.name} · ${stateLabels[entry.state] ?? stateLabels.unknown}${entry.signalDbm === null ? "" : ` · sinal ${entry.signalDbm} dBm`}`,
              ),
            );
            item.append(node(documentObject, "span", "ordax-settings-network-dot"), copy);
            interfaces.append(item);
          }
        }
        section.append(interfaces);
        }
      }
    }
    renderNetworkManagement(section);
    view.append(section);
  };

  const paint = (slot) => {
    const interaction = captureInteractionState(slot);
    slot.replaceChildren();
    slot.dataset.ordaxSettingsOverviewView = "";
    slot.dataset.settingsActiveSection = activeSection;
    const view = node(documentObject, "div", "ordax-settings-view");
    renderHeader(view);
    renderSectionNavigation(view);
    if (["appearance", "accessibility", "regional"].includes(activeSection)) {
      renderPreferences(view, activeSection);
      if (activeSection === "regional") renderKeyboardLayout(view);
    } else if (activeSection === "network") {
      renderNetwork(view);
    } else if (activeSection === "security") {
      renderSecurity(view);
    } else if (activeSection === "notifications") {
      renderNotifications(view);
    }
    slot.append(view);
    restoreInteractionState(slot, interaction);
  };

  const renderView = (force = false) => {
    if (destroyed) return;
    const slot = findSlot();
    if (!slot) {
      mountedSlot = null;
      return;
    }
    if (!force && slot === mountedSlot) return;
    mountedSlot = slot;
    paint(slot);
  };

  const replaceView = () => renderView(true);

  const refreshKeyboardLayout = async () => {
    if (!keyboardLayoutPort || destroyed || keyboardLayoutPending) return;
    const ordinal = ++keyboardLayoutOrdinal;
    try {
      const nextSnapshot = validateKeyboardLayoutSnapshot(await keyboardLayoutPort.read());
      if (destroyed || ordinal !== keyboardLayoutOrdinal) return;
      const changed =
        keyboardLayoutReadFailed
        || JSON.stringify(nextSnapshot) !== JSON.stringify(keyboardLayoutSnapshot);
      keyboardLayoutSnapshot = nextSnapshot;
      keyboardLayoutReadFailed = false;
      if (changed && activeSection === "regional") replaceView();
    } catch {
      if (destroyed || ordinal !== keyboardLayoutOrdinal) return;
      const changed = !keyboardLayoutReadFailed;
      keyboardLayoutReadFailed = true;
      if (changed && activeSection === "regional") replaceView();
    }
  };

  const configureKeyboardLayout = async (layoutId) => {
    if (!keyboardLayoutPort || keyboardLayoutPending || destroyed) return;
    const ordinal = ++keyboardLayoutOrdinal;
    keyboardLayoutPending = true;
    keyboardLayoutMessage = "Salvando layout do teclado…";
    replaceView();
    try {
      keyboardLayoutSnapshot = validateKeyboardLayoutSnapshot(
        await keyboardLayoutPort.configure(layoutId),
      );
      if (destroyed || ordinal !== keyboardLayoutOrdinal) return;
      keyboardLayoutReadFailed = false;
      keyboardLayoutMessage = keyboardLayoutSnapshot.restartRequired
        ? "Layout salvo. Ele será aplicado no próximo início da Surface."
        : "Layout salvo e já ativo nesta Surface.";
    } catch {
      if (destroyed || ordinal !== keyboardLayoutOrdinal) return;
      keyboardLayoutMessage =
        "Não foi possível salvar o layout do teclado. O layout atualmente aplicado foi preservado.";
    } finally {
      if (!destroyed && ordinal === keyboardLayoutOrdinal) {
        keyboardLayoutPending = false;
        replaceView();
      }
    }
  };

  const refreshNetwork = async () => {
    if (!networkPort || destroyed) return;
    const ordinal = ++networkReadOrdinal;
    let changed = false;
    try {
      const nextSnapshot = validateNetworkStatusSnapshot(await networkPort.read());
      if (destroyed || ordinal !== networkReadOrdinal) return;
      changed =
        networkReadFailed ||
        JSON.stringify(nextSnapshot) !== JSON.stringify(networkSnapshot);
      networkSnapshot = nextSnapshot;
      networkReadFailed = false;
      networkLastSuccessAt = Date.now();
    } catch {
      if (destroyed || ordinal !== networkReadOrdinal) return;
      changed = !networkReadFailed;
      networkReadFailed = true;
    }
    if (changed && !destroyed && ordinal === networkReadOrdinal) replaceView();
  };

  const refreshNetworkManagement = async () => {
    if (!networkManagementPort || destroyed || networkManagementPending) return;
    const ordinal = ++networkManagementReadOrdinal;
    let changed = false;
    try {
      const nextSnapshot = validateNetworkManagementSnapshot(
        await networkManagementPort.status(),
      );
      if (destroyed || ordinal !== networkManagementReadOrdinal) return;
      changed =
        networkManagementReadFailed
        || JSON.stringify(nextSnapshot) !== JSON.stringify(networkManagementSnapshot);
      networkManagementSnapshot = nextSnapshot;
      networkManagementReadFailed = false;
      networkManagementLastSuccessAt = Date.now();
      if (
        selectedNetworkSsid !== null
        && !nextSnapshot.networks.some((entry) => entry.ssid === selectedNetworkSsid)
      ) {
        selectedNetworkSsid = null;
        changed = true;
      }
    } catch {
      if (destroyed || ordinal !== networkManagementReadOrdinal) return;
      changed = !networkManagementReadFailed;
      networkManagementReadFailed = true;
    }
    if (changed && !destroyed && ordinal === networkManagementReadOrdinal) replaceView();
  };

  const runNetworkAction = async (action, { ssid = null, password = null } = {}) => {
    if (!networkManagementPort || networkManagementPending || destroyed) return;
    const ordinal = ++networkActionOrdinal;
    networkManagementReadOrdinal += 1;
    networkManagementPending = true;
    networkManagementMessage = networkManagementActionMessage(action, 0);
    replaceView();

    try {
      const nextSnapshot = validateNetworkManagementSnapshot(
        await runNetworkManagementAction(
          networkManagementPort,
          action,
          action === "connect" ? { ssid, password } : null,
        ),
      );
      if (destroyed || ordinal !== networkActionOrdinal) return;
      networkManagementSnapshot = nextSnapshot;
      networkManagementReadFailed = false;
      networkManagementLastSuccessAt = Date.now();
      networkManagementMessage = networkManagementActionMessage(action, 1);
      if (action === "connect" || action === "forget") selectedNetworkSsid = null;
      void refreshNetwork();
    } catch (error) {
      if (destroyed || ordinal !== networkActionOrdinal) return;
      networkManagementMessage = networkManagementFailureMessage(action, error);
    } finally {
      if (!destroyed && ordinal === networkActionOrdinal) {
        networkManagementPending = false;
        replaceView();
      }
    }
  };

  const onClick = (event) => {
    const sectionButton = event.target.closest("[data-settings-section]");
    if (
      sectionButton
      && root.contains(sectionButton)
      && validSettingsSection(sectionButton.dataset.settingsSection)
    ) {
      const nextSection = sectionButton.dataset.settingsSection;
      selectedNetworkSsid = null;
      networkManagementMessage = "";
      if (activationPort) {
        activationPort.publish({ appId: "settings", target: nextSection });
      } else {
        activeSection = nextSection;
        replaceView();
      }
      return;
    }

    const localSessionButton = event.target.closest("[data-settings-local-session-action]");
    if (
      localSessionButton
      && root.contains(localSessionButton)
      && localSessionPort
      && localSessionSnapshot
      && !localSessionPending
    ) {
      const action = localSessionButton.dataset.settingsLocalSessionAction;
      if (action === "lock") {
        localSessionMessage = "";
        void localSessionPort.lock().catch(() => {
          localSessionMessage = "Não foi possível bloquear a sessão.";
          replaceView();
        });
        return;
      }

      let secret = "";
      if (action === "configure") {
        const input = root.querySelector("[data-settings-local-session-secret]");
        const confirm = root.querySelector("[data-settings-local-session-confirm]");
        if (!(input instanceof HTMLInputElement) || !(confirm instanceof HTMLInputElement)) return;
        secret = input.value;
        const confirmation = confirm.value;
        input.value = "";
        confirm.value = "";
        if (secret.length < 6 || secret !== confirmation) {
          secret = "";
          localSessionMessage = "Use pelo menos 6 caracteres e repita exatamente a mesma credencial.";
          replaceView();
          return;
        }
      } else if (action === "remove") {
        const input = root.querySelector("[data-settings-local-session-current]");
        if (!(input instanceof HTMLInputElement)) return;
        secret = input.value;
        input.value = "";
        if (secret.length < 6) {
          secret = "";
          localSessionMessage = "Digite o PIN ou senha local atual.";
          replaceView();
          return;
        }
      } else {
        return;
      }

      localSessionPending = true;
      localSessionMessage = action === "configure" ? "Criando credencial local…" : "Removendo credencial local…";
      replaceView();
      const operationSecret = secret;
      secret = "";
      const operation = action === "configure"
        ? localSessionPort.configureCredential(operationSecret)
        : localSessionPort.removeCredential(operationSecret);
      void operation.then(() => {
        localSessionMessage = action === "configure"
          ? "Bloqueio local configurado."
          : "Bloqueio autenticado removido.";
      }).catch((error) => {
        localSessionMessage = error?.status === 401
          ? "PIN ou senha local incorreto."
          : "Não foi possível alterar o bloqueio local.";
      }).finally(() => {
        localSessionPending = false;
        replaceView();
      });
      return;
    }

    const dndButton = event.target.closest("[data-settings-notification-dnd]");
    if (dndButton && root.contains(dndButton) && notificationPort && notificationSnapshot) {
      notificationPort.setDoNotDisturb(!notificationSnapshot.doNotDisturb);
      return;
    }

    const notificationSourceButton = event.target.closest("[data-settings-notification-source]");
    if (
      notificationSourceButton
      && root.contains(notificationSourceButton)
      && notificationPort
      && notificationSnapshot
    ) {
      const sourceId = notificationSourceButton.dataset.settingsNotificationSource;
      const enabled = !notificationSnapshot.disabledSources.includes(sourceId);
      notificationPort.setSourceEnabled(sourceId, !enabled);
      return;
    }

    const keyboardLayoutButton = event.target.closest("[data-settings-keyboard-layout]");
    if (keyboardLayoutButton && root.contains(keyboardLayoutButton)) {
      void configureKeyboardLayout(keyboardLayoutButton.dataset.settingsKeyboardLayout);
      return;
    }

    const preferenceButton = event.target.closest("[data-settings-preference-id]");
    if (preferenceButton && root.contains(preferenceButton)) {
      preferences.set(
        preferenceButton.dataset.settingsPreferenceId,
        preferenceButton.dataset.settingsPreferenceValue,
      );
      return;
    }

    const networkButton = event.target.closest("[data-settings-wifi-ssid]");
    if (
      networkButton
      && root.contains(networkButton)
      && !networkButton.matches("[data-settings-network-action]")
    ) {
      selectedNetworkSsid = networkButton.dataset.settingsWifiSsid ?? null;
      networkManagementMessage = "";
      replaceView();
      return;
    }

    const actionButton = event.target.closest("[data-settings-network-action]");
    if (!actionButton || !root.contains(actionButton)) return;
    const action = actionButton.dataset.settingsNetworkAction;

    if (action === "connect") {
      const ssid = actionButton.dataset.settingsWifiSsid;
      const input = root.querySelector("[data-settings-wifi-password]");
      if (
        !(input instanceof HTMLInputElement)
        || input.dataset.settingsWifiPasswordFor !== ssid
      ) return;
      let password = input.value;
      input.value = "";
      if (!password) {
        networkManagementMessage = "Digite a senha da rede Wi-Fi.";
        password = "";
        replaceView();
        return;
      }
      const operationPassword = password;
      password = "";
      void runNetworkAction("connect", { ssid, password: operationPassword });
      return;
    }

    void runNetworkAction(action);
  };

  const onKeyDown = (event) => {
    const input = event.target.closest("[data-settings-wifi-password]");
    if (!input || !root.contains(input)) return;
    if (event.key === "Enter") {
      event.preventDefault();
      const connect = root.querySelector(
        '[data-settings-network-action="connect"]',
      );
      connect?.click();
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      input.value = "";
      selectedNetworkSsid = null;
      networkManagementMessage = "";
      replaceView();
    }
  };

  root.addEventListener("click", onClick);
  root.addEventListener("keydown", onKeyDown);
  const unsubscribeRender = lifecycle.subscribeRender(() => {
    const persistedTarget = lifecycle.getAppTarget("settings");
    const nextSection = validSettingsSection(persistedTarget) ? persistedTarget : "appearance";
    if (nextSection !== activeSection) {
      selectedNetworkSsid = null;
      networkManagementMessage = "";
    }
    activeSection = nextSection;
    renderView(false);
  });
  const unsubscribeActivation = activationPort?.subscribe((activation) => {
    if (
      activation.appId === "settings"
      && activation.target !== null
      && validSettingsSection(activation.target)
    ) {
      activeSection = activation.target;
      selectedNetworkSsid = null;
      networkManagementMessage = "";
      replaceView();
    }
  });
  const unsubscribeHost = hostPort.subscribe((snapshot) => {
    hostSnapshot = validateSurfaceSnapshot(snapshot);
    replaceView();
  });
  const unsubscribePreferences = preferences.subscribe((snapshot) => {
    preferenceSnapshot = snapshot;
    replaceView();
  });
  const unsubscribeLocalSession = localSessionPort?.subscribe((snapshot) => {
    localSessionSnapshot = validateLocalSessionSnapshot(snapshot);
    if (activeSection === "security") replaceView();
  });
  const unsubscribeNotifications = notificationPort?.subscribe((snapshot) => {
    notificationSnapshot = snapshot;
    if (activeSection === "notifications") replaceView();
  });
  const networkPoll = networkPort
    ? setInterval(() => void refreshNetwork(), 5000)
    : null;
  const networkManagementPoll = networkManagementPort
    ? setInterval(() => void refreshNetworkManagement(), 5000)
    : null;
  if (keyboardLayoutPort) void refreshKeyboardLayout();
  if (networkPort) void refreshNetwork();
  if (networkManagementPort) void refreshNetworkManagement();

  return Object.freeze({
    destroy() {
      destroyed = true;
      networkReadOrdinal += 1;
      networkManagementReadOrdinal += 1;
      networkActionOrdinal += 1;
      keyboardLayoutOrdinal += 1;
      if (networkPoll !== null) clearInterval(networkPoll);
      if (networkManagementPoll !== null) clearInterval(networkManagementPoll);
      unsubscribeNotifications?.();
      unsubscribeLocalSession?.();
      unsubscribePreferences?.();
      unsubscribeHost?.();
      unsubscribeActivation?.();
      unsubscribeRender();
      root.removeEventListener("click", onClick);
      root.removeEventListener("keydown", onKeyDown);
      const slot = findSlot();
      if (slot?.dataset.ordaxSettingsOverviewView !== undefined) {
        slot.replaceChildren();
        delete slot.dataset.ordaxSettingsOverviewView;
      }
      mountedSlot = null;
    },
  });
}
