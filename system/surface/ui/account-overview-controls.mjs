import { assertAppActivationPort } from "../../contracts/app-activation.mjs";
import {
  assertIdentityActionsPort,
  isIdentityActionSupported,
  validateIdentityActionsSnapshot,
} from "../../contracts/identity-actions.mjs";
import {
  assertIdentitySessionPort,
  validateIdentitySessionSnapshot,
} from "../../contracts/identity-session.mjs";
import { assertIdentityCredentialsPort } from "../../contracts/identity-credentials.mjs";
import {
  assertSyncRuntimePort,
  validateSyncRuntimeSnapshot,
} from "../../contracts/sync-runtime.mjs";
import {
  assertWorkspaceMetadataSource,
  validateWorkspaceMetadata,
} from "../../contracts/workspace-metadata-source.mjs";
import { assertSurfaceRenderLifecycle } from "../../contracts/surface-render-lifecycle.mjs";

const ACCOUNT_WINDOW_SELECTOR = '[data-window-id="account"]';
const ACCOUNT_EXTENSION_SELECTOR = '[data-app-extension="account-overview"]';

const ACCOUNT_SECTIONS = Object.freeze([
  Object.freeze({ id: "overview", messageId: "account.section.overview" }),
  Object.freeze({ id: "sync", messageId: "account.section.sync" }),
]);

function validAccountSection(value) {
  return ACCOUNT_SECTIONS.some((section) => section.id === value);
}

function node(documentObject, tag, className, text) {
  const element = documentObject.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function sessionLabel(snapshot, t) {
  if (snapshot.state === "signed-in") return t("account.identity.signedIn");
  if (snapshot.state === "signed-out") return t("account.identity.signedOut");
  return t("account.identity.unavailable");
}

function sessionDescription(snapshot, t) {
  if (snapshot.state === "signed-in") {
    return t("account.identity.description.signedIn");
  }
  if (snapshot.state === "signed-out") {
    return t("account.identity.description.signedOut");
  }
  return t("account.identity.description.unavailable");
}

function desiredAction(session, actions) {
  if (session.state === "signed-out" && isIdentityActionSupported(actions, "sign-in")) {
    return "sign-in";
  }
  if (session.state === "signed-in" && isIdentityActionSupported(actions, "sign-out")) {
    return "sign-out";
  }
  return null;
}

function appendStateCard(documentObject, container, label, value, detail, state = "neutral") {
  const card = node(documentObject, "article", "ordax-account-card");
  card.dataset.state = state;
  card.append(
    node(documentObject, "span", "ordax-account-card-label", label),
    node(documentObject, "strong", "ordax-account-card-value", value),
    node(documentObject, "small", "ordax-account-card-detail", detail),
  );
  container.append(card);
}

export function mountAccountOverviewControls(
  root,
  identitySession,
  identityActions,
  surfaceLifecycle = null,
  syncRuntime = null,
  workspaceMetadataSource = null,
  appActivation = null,
  identityCredentials = null,
) {
  if (!(root instanceof Element)) {
    throw new TypeError("Account overview controls require a Surface root Element");
  }

  const sessionPort = assertIdentitySessionPort(identitySession);
  const actionsPort = assertIdentityActionsPort(identityActions);
  const credentialsPort = identityCredentials === null
    ? null
    : assertIdentityCredentialsPort(identityCredentials);
  const syncPort = syncRuntime === null ? null : assertSyncRuntimePort(syncRuntime);
  const workspaceMetadataPort = workspaceMetadataSource === null
    ? null
    : assertWorkspaceMetadataSource(workspaceMetadataSource);
  const activationPort = appActivation === null ? null : assertAppActivationPort(appActivation);
  const lifecycle = assertSurfaceRenderLifecycle(surfaceLifecycle);
  const localization = lifecycle.localization;
  const t = localization.translate;
  const documentObject = root.ownerDocument;

  let sessionSnapshot = validateIdentitySessionSnapshot(sessionPort.getSnapshot());
  let actionsSnapshot = validateIdentityActionsSnapshot(actionsPort.getSnapshot());
  let syncSnapshot = syncPort ? validateSyncRuntimeSnapshot(syncPort.getSnapshot()) : null;
  let workspaceMetadataSnapshot = workspaceMetadataPort
    ? validateWorkspaceMetadata(workspaceMetadataPort.getSnapshot())
    : null;
  let pendingAction = null;
  let actionMessage = "";
  let credentialEmailDraft = "";
  let credentialPasswordDraft = "";
  let actionOrdinal = 0;
  let activeSection = validAccountSection(lifecycle.getAppTarget("account"))
    ? lifecycle.getAppTarget("account")
    : "overview";
  let destroyed = false;
  let mountedSlot = null;

  const findSlot = () =>
    root.querySelector(`${ACCOUNT_WINDOW_SELECTOR} ${ACCOUNT_EXTENSION_SELECTOR}`);

  const focusIdentity = (element) => {
    if (!element || !element.dataset) return null;
    if (element.dataset.accountSection) {
      return Object.freeze({ kind: "section", value: element.dataset.accountSection });
    }
    if (element.dataset.accountIdentityAction) {
      return Object.freeze({ kind: "identity-action", value: element.dataset.accountIdentityAction });
    }
    return null;
  };

  const findFocusTarget = (slot, identity) => {
    if (!identity) return null;
    for (const element of slot.querySelectorAll("button")) {
      const candidate = focusIdentity(element);
      if (
        candidate
        && candidate.kind === identity.kind
        && candidate.value === identity.value
      ) {
        return element;
      }
    }
    return null;
  };

  const captureInteractionState = (slot) => {
    const windowBody = slot.closest(".ordax-window-body");
    const activeElement = documentObject.activeElement;
    const activeInside = activeElement && slot.contains(activeElement);
    return Object.freeze({
      section: slot.dataset.accountActiveSection ?? "",
      windowScrollTop: windowBody?.scrollTop ?? 0,
      windowScrollLeft: windowBody?.scrollLeft ?? 0,
      focus: activeInside ? focusIdentity(activeElement) : null,
    });
  };

  const restoreInteractionState = (slot, snapshot) => {
    const sameSection = Boolean(snapshot) && snapshot.section === activeSection;
    if (!sameSection) return;

    const windowBody = slot.closest(".ordax-window-body");
    if (windowBody) {
      windowBody.scrollTop = snapshot.windowScrollTop;
      windowBody.scrollLeft = snapshot.windowScrollLeft;
    }

    const target = findFocusTarget(slot, snapshot.focus);
    if (!target || target.disabled) return;
    target.focus({ preventScroll: true });
  };

  const renderHeader = (view) => {
    const header = node(documentObject, "header", "ordax-account-header");
    header.append(
      node(documentObject, "span", "ordax-account-eyebrow", t("account.eyebrow")),
      node(
        documentObject,
        "h3",
        "ordax-account-title",
        t(`account.section.${activeSection}.title`),
      ),
      node(
        documentObject,
        "p",
        "ordax-account-subtitle",
        t(`account.section.${activeSection}.subtitle`),
      ),
    );
    view.append(header);
  };

  const renderSectionNavigation = (view) => {
    const navigation = node(documentObject, "nav", "ordax-account-navigation");
    navigation.setAttribute("aria-label", t("account.navigation.aria"));
    for (const section of ACCOUNT_SECTIONS) {
      const button = node(
        documentObject,
        "button",
        "ordax-account-navigation-item",
        t(section.messageId),
      );
      button.type = "button";
      button.dataset.accountSection = section.id;
      const active = activeSection === section.id;
      button.dataset.active = String(active);
      button.setAttribute("aria-current", active ? "page" : "false");
      navigation.append(button);
    }
    view.append(navigation);
  };

  const renderIdentity = (view) => {
    const section = node(documentObject, "section", "ordax-account-section");
    const heading = node(documentObject, "div", "ordax-account-section-heading");
    const copy = node(documentObject, "div");
    copy.append(
      node(documentObject, "span", "ordax-account-eyebrow", t("account.identity.eyebrow")),
      node(documentObject, "h4", "ordax-account-section-title", t("account.identity.title")),
      node(
        documentObject,
        "p",
        "ordax-account-subtitle",
        sessionDescription(sessionSnapshot, t),
      ),
    );

    const status = node(
      documentObject,
      "span",
      "ordax-account-status",
      sessionLabel(sessionSnapshot, t),
    );
    status.dataset.state = sessionSnapshot.state;
    heading.append(copy, status);
    section.append(heading);

    if (sessionSnapshot.state === "signed-in") {
      const identity = node(documentObject, "div", "ordax-account-identity");
      const avatar = node(
        documentObject,
        "span",
        "ordax-account-avatar",
        sessionSnapshot.displayName.trim().slice(0, 1).toLocaleUpperCase(),
      );
      const identityCopy = node(documentObject, "div", "ordax-account-identity-copy");
      identityCopy.append(
        node(documentObject, "strong", "", sessionSnapshot.displayName),
        node(
          documentObject,
          "small",
          "",
          t("account.identity.subject", { subjectId: sessionSnapshot.subjectId }),
        ),
      );
      identity.append(avatar, identityCopy);
      section.append(identity);
    }

    const action = desiredAction(sessionSnapshot, actionsSnapshot);
    const actions = node(documentObject, "div", "ordax-account-actions");

    if (sessionSnapshot.state === "signed-out" && credentialsPort) {
      const form = node(documentObject, "div", "ordax-account-credential-form");

      const emailLabel = node(documentObject, "label", "ordax-account-field");
      emailLabel.append(node(documentObject, "span", "", t("account.credentials.email")));
      const emailInput = documentObject.createElement("input");
      emailInput.type = "email";
      emailInput.autocomplete = "email";
      emailInput.maxLength = 320;
      emailInput.value = credentialEmailDraft;
      emailInput.dataset.accountCredentialEmail = "";
      emailInput.disabled = pendingAction !== null;
      emailLabel.append(emailInput);

      const passwordLabel = node(documentObject, "label", "ordax-account-field");
      passwordLabel.append(node(documentObject, "span", "", t("account.credentials.password")));
      const passwordInput = documentObject.createElement("input");
      passwordInput.type = "password";
      passwordInput.autocomplete = "current-password";
      passwordInput.maxLength = 1024;
      passwordInput.value = credentialPasswordDraft;
      passwordInput.dataset.accountCredentialPassword = "";
      passwordInput.disabled = pendingAction !== null;
      passwordLabel.append(passwordInput);

      form.append(emailLabel, passwordLabel);
      section.append(form);

      const signIn = node(
        documentObject,
        "button",
        "ordax-account-action ordax-account-action-primary",
        pendingAction === "sign-in" ? t("account.action.signingIn") : t("account.action.signIn"),
      );
      signIn.type = "button";
      signIn.dataset.accountIdentityAction = "sign-in";
      signIn.disabled = pendingAction !== null || !isIdentityActionSupported(actionsSnapshot, "sign-in");
      actions.append(signIn);

      const register = node(
        documentObject,
        "button",
        "ordax-account-action",
        pendingAction === "register" ? t("account.action.registering") : t("account.action.register"),
      );
      register.type = "button";
      register.dataset.accountIdentityAction = "register";
      register.disabled = pendingAction !== null || !isIdentityActionSupported(actionsSnapshot, "register");
      actions.append(register);
    } else if (action) {
      const label = pendingAction === action
        ? action === "sign-in"
          ? t("account.action.signingIn")
          : t("account.action.signingOut")
        : action === "sign-in"
          ? t("account.action.signIn")
          : t("account.action.signOut");
      const button = node(documentObject, "button", "ordax-account-action ordax-account-action-primary", label);
      button.type = "button";
      button.dataset.accountIdentityAction = action;
      button.disabled = pendingAction !== null;
      actions.append(button);
    } else {
      actions.append(
        node(
          documentObject,
          "span",
          "ordax-account-action-note",
          sessionSnapshot.state === "unavailable"
            ? t("account.action.unavailable")
            : t("account.action.none"),
        ),
      );
    }
    section.append(actions);

    if (actionMessage) {
      section.append(node(documentObject, "p", "ordax-account-message", actionMessage));
    }
    view.append(section);
  };

  const renderContinuity = (view) => {
    const section = node(documentObject, "section", "ordax-account-section");
    section.append(
      node(documentObject, "span", "ordax-account-eyebrow", t("account.continuity.eyebrow")),
      node(documentObject, "h4", "ordax-account-section-title", t("account.continuity.title")),
      node(
        documentObject,
        "p",
        "ordax-account-subtitle",
        t("account.continuity.subtitle"),
      ),
    );

    const grid = node(documentObject, "div", "ordax-account-grid");
    const pendingMutationCount = syncSnapshot?.pendingMutationCount ?? 0;
    const appearanceTracked = syncSnapshot?.trackedDataClasses.includes("appearance") ?? false;
    const queueIsDurable = syncSnapshot?.queuePersistence === "device";
    const workspaceAreaCount = workspaceMetadataSnapshot?.areas.length ?? 0;
    const workspaceAppCount = workspaceMetadataSnapshot
      ? workspaceMetadataSnapshot.areas.reduce((total, area) => total + area.appIds.length, 0)
      : 0;

    appendStateCard(
      documentObject,
      grid,
      t("account.card.localChanges"),
      syncSnapshot
        ? pendingMutationCount > 0
          ? t(
              pendingMutationCount === 1
                ? "account.card.pending.one"
                : "account.card.pending.many",
              { count: pendingMutationCount },
            )
          : t("account.card.noPending")
        : t("account.card.stateUnavailable"),
      syncSnapshot
        ? pendingMutationCount > 0
          ? t("account.card.pending.detail")
          : t("account.card.noPending.detail")
        : t("account.card.syncUnavailable.detail"),
      syncSnapshot ? (pendingMutationCount > 0 ? "neutral" : "available") : "unavailable",
    );

    appendStateCard(
      documentObject,
      grid,
      t("account.card.appearance"),
      appearanceTracked
        ? t("account.card.appearanceTracked")
        : t("account.card.appearanceUntracked"),
      appearanceTracked
        ? t("account.card.appearanceTracked.detail")
        : t("account.card.appearanceUntracked.detail"),
      appearanceTracked ? "available" : "neutral",
    );

    appendStateCard(
      documentObject,
      grid,
      t("account.card.workspace"),
      workspaceMetadataSnapshot
        ? t("account.card.workspaceCounts", {
            areas: t(
              workspaceAreaCount === 1
                ? "account.card.area.one"
                : "account.card.area.many",
              { count: workspaceAreaCount },
            ),
            apps: t(
              workspaceAppCount === 1
                ? "account.card.app.one"
                : "account.card.app.many",
              { count: workspaceAppCount },
            ),
          })
        : t("account.card.metadataUnavailable"),
      workspaceMetadataSnapshot
        ? t("account.card.workspace.detail")
        : t("account.card.workspaceUnavailable.detail"),
      workspaceMetadataSnapshot ? "available" : "neutral",
    );

    appendStateCard(
      documentObject,
      grid,
      t("account.card.offlineQueue"),
      syncSnapshot
        ? queueIsDurable
          ? t("account.card.queueDurable")
          : t("account.card.queueSession")
        : t("account.card.unavailable"),
      syncSnapshot
        ? queueIsDurable
          ? t("account.card.queueDurable.detail")
          : t("account.card.queueSession.detail")
        : t("account.card.queueUnavailable.detail"),
      syncSnapshot ? (queueIsDurable ? "available" : "neutral") : "unavailable",
    );

    section.append(grid);
    view.append(section);
  };

  const paint = (slot, interaction = null) => {
    slot.replaceChildren();
    slot.dataset.ordaxAccountOverviewView = "";
    slot.dataset.accountActiveSection = activeSection;
    const view = node(documentObject, "div", "ordax-account-view");
    renderHeader(view);
    renderSectionNavigation(view);
    if (activeSection === "overview") {
      renderIdentity(view);
    } else if (activeSection === "sync") {
      renderContinuity(view);
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
    const interaction =
      force && slot === mountedSlot ? captureInteractionState(slot) : null;
    mountedSlot = slot;
    paint(slot, interaction);
  };

  const replaceView = () => renderView(true);

  const invoke = async (action) => {
    if (
      pendingAction !== null ||
      !isIdentityActionSupported(actionsSnapshot, action)
    ) {
      return;
    }
    const credentialInput = (
      credentialsPort
      && sessionSnapshot.state === "signed-out"
      && (action === "sign-in" || action === "register")
    )
      ? { email: credentialEmailDraft, password: credentialPasswordDraft }
      : null;
    credentialPasswordDraft = "";
    const ordinal = ++actionOrdinal;
    pendingAction = action;
    actionMessage = "";
    replaceView();
    try {
      let credentialResult = null;
      if (credentialInput) {
        credentialResult = action === "sign-in"
          ? await credentialsPort.signIn(credentialInput)
          : await credentialsPort.register(credentialInput);
        if (typeof sessionPort.refresh === "function") {
          await sessionPort.refresh();
        }
        if (credentialResult?.confirmationRequired) {
          actionMessage = t("account.credentials.confirmationRequired");
        }
      } else {
        await actionsPort.execute(action);
      }
      if (destroyed || ordinal !== actionOrdinal) return;
    } catch {
      if (destroyed || ordinal !== actionOrdinal) return;
      actionMessage = t("account.action.failed");
    } finally {
      if (!destroyed && ordinal === actionOrdinal) {
        pendingAction = null;
        replaceView();
      }
    }
  };

  const onInput = (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || !root.contains(input)) return;
    if (input.matches("[data-account-credential-email]")) {
      credentialEmailDraft = input.value;
    } else if (input.matches("[data-account-credential-password]")) {
      credentialPasswordDraft = input.value;
    }
  };

  const onClick = (event) => {
    const sectionButton = event.target.closest("[data-account-section]");
    if (
      sectionButton
      && root.contains(sectionButton)
      && validAccountSection(sectionButton.dataset.accountSection)
    ) {
      const nextSection = sectionButton.dataset.accountSection;
      actionMessage = "";
      if (activationPort) {
        activationPort.publish({ appId: "account", target: nextSection });
      } else {
        activeSection = nextSection;
        replaceView();
      }
      return;
    }

    const button = event.target.closest("[data-account-identity-action]");
    if (button && root.contains(button)) {
      void invoke(button.dataset.accountIdentityAction);
    }
  };

  root.addEventListener("click", onClick);
  root.addEventListener("input", onInput);
  const unsubscribeRender = lifecycle.subscribeRender(() => {
    const persistedTarget = lifecycle.getAppTarget("account");
    const nextSection = validAccountSection(persistedTarget) ? persistedTarget : "overview";
    if (nextSection !== activeSection) actionMessage = "";
    activeSection = nextSection;
    renderView(false);
  });
  const unsubscribeActivation = activationPort?.subscribe((activation) => {
    if (
      activation.appId === "account"
      && activation.target !== null
      && validAccountSection(activation.target)
    ) {
      activeSection = activation.target;
      actionMessage = "";
      replaceView();
    }
  });
  const unsubscribeSession = sessionPort.subscribe((snapshot) => {
    sessionSnapshot = validateIdentitySessionSnapshot(snapshot);
    actionMessage = "";
    replaceView();
  });
  const unsubscribeActions = actionsPort.subscribe((snapshot) => {
    actionsSnapshot = validateIdentityActionsSnapshot(snapshot);
    actionMessage = "";
    replaceView();
  });
  const unsubscribeSync = syncPort?.subscribe((snapshot) => {
    syncSnapshot = validateSyncRuntimeSnapshot(snapshot);
    replaceView();
  });
  const unsubscribeWorkspaceMetadata = workspaceMetadataPort?.subscribe((snapshot) => {
    workspaceMetadataSnapshot = validateWorkspaceMetadata(snapshot);
    replaceView();
  });

  return Object.freeze({
    destroy() {
      destroyed = true;
      actionOrdinal += 1;
      unsubscribeWorkspaceMetadata?.();
      unsubscribeSync?.();
      unsubscribeActions?.();
      unsubscribeSession?.();
      unsubscribeActivation?.();
      unsubscribeRender();
      credentialPasswordDraft = "";
      root.removeEventListener("input", onInput);
      root.removeEventListener("click", onClick);
      const slot = findSlot();
      if (slot?.dataset.ordaxAccountOverviewView !== undefined) {
        slot.replaceChildren();
        delete slot.dataset.ordaxAccountOverviewView;
      }
      mountedSlot = null;
    },
  });
}