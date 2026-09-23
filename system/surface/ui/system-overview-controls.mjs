import { assertAppActivationPort } from "../../contracts/app-activation.mjs";
import {
  assertIntelligencePort,
  validateIntelligenceSnapshot,
} from "../../contracts/intelligence.mjs";
import {
  assertComponentManager,
  validateComponentManagerSnapshot,
} from "../../contracts/component-manager.mjs";
import {
  assertSurfaceHost,
  validateSurfaceSnapshot,
} from "../../contracts/surface-host.mjs";
import {
  assertSystemMetricsPort,
  validateSystemMetricsSnapshot,
} from "../../contracts/system-metrics.mjs";
import {
  assertRecoveryStatusPort,
  validateRecoveryStatusSnapshot,
} from "../../contracts/recovery-status.mjs";
import {
  assertUpdateHistoryPort,
  validateUpdateHistorySnapshot,
} from "../../contracts/update-history.mjs";
import {
  assertUpdateStatusPort,
  validateUpdateStatusSnapshot,
} from "../../contracts/update-status.mjs";
import { PRODUCT_VERSION, productVersionLabel } from "../../contracts/product-version.mjs";
import { createComponentUpdateScopes } from "../../services/components/update-presentation.mjs";
import { explainSystemStateWithIntelligence } from "../../services/intelligence/client-actions.mjs";
import {
  shortSha,
  updateIsAlerting,
} from "../../services/update/presentation.mjs";
import { mountSystemDiagnosticsReview } from "./system-diagnostics-review.mjs";
import { assertSurfaceRenderLifecycle } from "../../contracts/surface-render-lifecycle.mjs";

const SYSTEM_WINDOW_SELECTOR = '[data-window-id="system"]';
const SYSTEM_EXTENSION_SELECTOR = '[data-app-extension="system-overview"]';

const SYSTEM_SECTIONS = Object.freeze([
  Object.freeze({ id: "overview", messageId: "system.section.overview" }),
  Object.freeze({ id: "updates", messageId: "system.section.updates" }),
  Object.freeze({ id: "storage", messageId: "system.section.storage" }),
  Object.freeze({ id: "diagnostics", messageId: "system.section.diagnostics" }),
  Object.freeze({ id: "about", messageId: "system.section.about" }),
]);

const OVERVIEW_UPDATE_STATUS_MESSAGE_IDS = Object.freeze({
  running: "system.overview.update.status.running",
  applied: "system.overview.update.status.applied",
  updating: "system.overview.update.status.updating",
  "network-error": "system.overview.update.status.networkError",
  "remote-error": "system.overview.update.status.remoteError",
  "pull-error": "system.overview.update.status.pullError",
  "rolled-back": "system.overview.update.status.rolledBack",
  rejected: "system.overview.update.status.rejected",
  pinned: "system.overview.update.status.pinned",
  disabled: "system.overview.update.status.disabled",
  unavailable: "system.overview.update.status.unavailable",
});

const OVERVIEW_UPDATE_MODE_MESSAGE_IDS = Object.freeze({
  reload: "system.overview.update.mode.reload",
  "surface-restart": "system.overview.update.mode.surfaceRestart",
  "supervisor-restart": "system.overview.update.mode.supervisorRestart",
  initial: "system.overview.update.mode.initial",
});

const OVERVIEW_BASE_SUMMARY_MESSAGE_IDS = Object.freeze({
  "candidate-requested": "system.overview.update.summary.candidateRequested",
  "candidate-fetching": "system.overview.update.summary.candidateFetching",
  "candidate-ready": "system.overview.update.summary.candidateReady",
  staged: "system.overview.update.summary.staged",
  "activation-ready": "system.overview.update.summary.activationReady",
});

const OVERVIEW_BASE_DETAIL_MESSAGE_IDS = Object.freeze({
  "candidate-requested": "system.overview.update.detail.candidateRequested",
  "candidate-fetching": "system.overview.update.detail.candidateFetching",
  "candidate-ready": "system.overview.update.detail.candidateReady",
  staged: "system.overview.update.detail.staged",
  "activation-ready": "system.overview.update.detail.activationReady",
});

function overviewUpdateStatusMessageId(status) {
  return OVERVIEW_UPDATE_STATUS_MESSAGE_IDS[status]
    ?? "system.overview.update.status.unavailable";
}

function overviewUpdateModeMessageId(mode) {
  return OVERVIEW_UPDATE_MODE_MESSAGE_IDS[mode]
    ?? "system.overview.update.mode.none";
}

function overviewUpdateSummaryMessageId(snapshot) {
  if (!snapshot?.bootRefreshRequired) {
    return overviewUpdateStatusMessageId(snapshot?.status);
  }
  return OVERVIEW_BASE_SUMMARY_MESSAGE_IDS[snapshot?.baseUpdatePhase]
    ?? "system.overview.update.summary.pending";
}

function overviewUpdateDetailMessageId(snapshot) {
  if (!snapshot?.bootRefreshRequired) return null;
  return OVERVIEW_BASE_DETAIL_MESSAGE_IDS[snapshot?.baseUpdatePhase]
    ?? "system.overview.update.detail.pending";
}

function formatOverviewTimestamp(value, locale) {
  if (typeof value !== "string" || !value || value === "unknown") return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale, {
    timeZone: "America/Bahia",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function formatOverviewReceivedAt(value, locale) {
  if (!Number.isFinite(value)) return null;
  return new Intl.DateTimeFormat(locale, {
    timeZone: "America/Bahia",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function validSystemSection(value) {
  return SYSTEM_SECTIONS.some((section) => section.id === value);
}

const CAPABILITY_MESSAGE_IDS = Object.freeze({
  "network.https": "system.capabilities.networkHttps",
  "network.status": "system.capabilities.networkStatus",
  "network.management": "system.capabilities.networkManagement",
  "system.boot-control": "system.capabilities.bootControl",
  "filesystem.user-space": "system.capabilities.userSpace",
  "system.metrics": "system.capabilities.systemMetrics",
  "power.status": "system.capabilities.powerStatus",
  "intelligence.system": "system.capabilities.intelligence",
});

function node(documentObject, tag, className, text) {
  const element = documentObject.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function formatBytes(bytes) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const precision = unit >= 3 && value < 10 ? 1 : 0;
  return `${value.toFixed(precision)} ${units[unit]}`;
}

function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h ${minutes}min`;
  if (hours > 0) return `${hours}h ${minutes}min`;
  return `${minutes}min`;
}

function ratio(used, total) {
  if (!Number.isFinite(used) || !Number.isFinite(total) || total <= 0) return 0;
  return Math.min(1, Math.max(0, used / total));
}

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function appendMetricCard(documentObject, container, { label, value, detail = "", progress = null }) {
  const card = node(documentObject, "article", "ordax-system-card");
  card.append(node(documentObject, "span", "ordax-system-card-label", label));
  card.append(node(documentObject, "strong", "ordax-system-card-value", value));
  if (progress !== null) {
    const track = node(documentObject, "span", "ordax-system-meter");
    const fill = node(documentObject, "span", "ordax-system-meter-fill");
    fill.style.setProperty("--ordax-system-meter-value", percent(progress));
    track.append(fill);
    card.append(track);
  }
  if (detail) card.append(node(documentObject, "small", "ordax-system-card-detail", detail));
  container.append(card);
}

export function mountSystemOverviewControls(
  root,
  host,
  updateStatusPort = null,
  systemMetrics = null,
  surfaceLifecycle = null,
  updateHistory = null,
  appActivation = null,
  diagnosticReviewController = null,
  componentManager = null,
  intelligence = null,
  recoveryStatus = null,
) {
  if (!(root instanceof Element)) {
    throw new TypeError("System overview controls require a Surface root Element");
  }

  const hostPort = assertSurfaceHost(host);
  const updatePort = updateStatusPort === null ? null : assertUpdateStatusPort(updateStatusPort);
  const metricsPort = systemMetrics === null ? null : assertSystemMetricsPort(systemMetrics);
  const historyPort = updateHistory === null ? null : assertUpdateHistoryPort(updateHistory);
  const activationPort = appActivation === null ? null : assertAppActivationPort(appActivation);
  const componentPort = componentManager === null ? null : assertComponentManager(componentManager);
  const intelligencePort = intelligence === null ? null : assertIntelligencePort(intelligence);
  const recoveryPort = recoveryStatus === null ? null : assertRecoveryStatusPort(recoveryStatus);
  const lifecycle = assertSurfaceRenderLifecycle(surfaceLifecycle);
  const localization = lifecycle.localization;
  const t = localization.translate;
  const documentObject = root.ownerDocument;

  let hostSnapshot = validateSurfaceSnapshot(hostPort.getSnapshot());
  let updateSnapshot = updatePort?.getSnapshot();
  if (updateSnapshot !== null && updateSnapshot !== undefined) {
    updateSnapshot = validateUpdateStatusSnapshot(updateSnapshot);
  }
  let metricsSnapshot = null;
  let metricsPending = false;
  let metricsReadFailed = false;
  let metricsLastSuccessAt = null;
  let metricsMessage = "";
  let metricsOrdinal = 0;
  let historySnapshot = null;
  let historyMessage = "";
  let componentSnapshot = componentPort?.getSnapshot() ?? null;
  let intelligenceSnapshot = intelligencePort === null
    ? null
    : validateIntelligenceSnapshot(intelligencePort.getSnapshot());
  let intelligencePending = false;
  let intelligenceAnswer = "";
  let intelligenceMessage = "";
  let recoverySnapshot = null;
  let recoveryPending = false;
  let recoveryMessage = "";
  let recoveryOrdinal = 0;
  let historyOrdinal = 0;
  let activeSection = validSystemSection(lifecycle.getAppTarget("system"))
    ? lifecycle.getAppTarget("system")
    : "overview";
  let destroyed = false;
  let mountedSlot = null;
  let diagnosticsReviewMount = null;

  const findSlot = () =>
    root.querySelector(`${SYSTEM_WINDOW_SELECTOR} ${SYSTEM_EXTENSION_SELECTOR}`);

  const disposeDiagnosticsReview = () => {
    diagnosticsReviewMount?.dispose();
    diagnosticsReviewMount = null;
  };

  const focusIdentity = (element) => {
    if (!element || !element.dataset) return null;
    if (element.dataset.systemSection) {
      return Object.freeze({ kind: "section", value: element.dataset.systemSection });
    }
    if (element.dataset.systemOverviewRefresh !== undefined) {
      return Object.freeze({ kind: "metrics-refresh", value: "" });
    }
    if (element.dataset.systemHistoryRefresh !== undefined) {
      return Object.freeze({ kind: "history-refresh", value: "" });
    }
    if (element.dataset.systemRecoveryRefresh !== undefined) {
      return Object.freeze({ kind: "recovery-refresh", value: "" });
    }
    if (element.dataset.systemDiagnosticsPrepare !== undefined) {
      return Object.freeze({ kind: "diagnostics-prepare", value: "" });
    }
    if (element.dataset.systemDiagnosticsCopy !== undefined) {
      return Object.freeze({ kind: "diagnostics-copy", value: "" });
    }
    if (element.dataset.systemDiagnosticsExport !== undefined) {
      return Object.freeze({ kind: "diagnostics-export", value: "" });
    }
    if (element.dataset.systemIntelligenceExplain !== undefined) {
      return Object.freeze({ kind: "intelligence-explain", value: "" });
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
      section: slot.dataset.systemActiveSection ?? "",
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
    const header = node(documentObject, "header", "ordax-system-header");
    const copy = node(documentObject, "div", "ordax-system-header-copy");
    copy.append(
      node(documentObject, "span", "ordax-system-eyebrow", t("system.eyebrow")),
      node(documentObject, "h3", "ordax-system-title", t(`system.section.${activeSection}`)),
      node(
        documentObject,
        "p",
        "ordax-system-subtitle",
        t(`system.section.${activeSection}.subtitle`),
      ),
    );

    const health = node(documentObject, "span", "ordax-system-health");
    const alerting = updateIsAlerting(updateSnapshot);
    health.dataset.state =
      alerting || hostSnapshot.connectivity === "offline"
        ? "attention"
        : "observed";
    health.textContent = updateSnapshot?.bootRefreshRequired
      ? t(overviewUpdateSummaryMessageId(updateSnapshot))
      : alerting
        ? t("system.overview.health.updateAttention")
        : hostSnapshot.connectivity === "offline"
          ? t("system.overview.health.offline")
          : updateSnapshot
            ? t(overviewUpdateStatusMessageId(updateSnapshot.status))
            : t("system.overview.health.active");
    header.append(copy, health);
    view.append(header);
  };

  const renderSectionNavigation = (view) => {
    const navigation = node(documentObject, "nav", "ordax-system-navigation");
    navigation.setAttribute("aria-label", t("system.navigation.aria"));
    for (const section of SYSTEM_SECTIONS) {
      const button = node(
        documentObject,
        "button",
        "ordax-system-navigation-item",
        t(section.messageId),
      );
      button.type = "button";
      button.dataset.systemSection = section.id;
      const active = activeSection === section.id;
      button.dataset.active = String(active);
      button.setAttribute("aria-current", active ? "page" : "false");
      navigation.append(button);
    }
    view.append(navigation);
  };

  const renderSummary = (view) => {
    const grid = node(documentObject, "section", "ordax-system-summary");
    grid.setAttribute("aria-label", t("system.overview.aria"));

    appendMetricCard(documentObject, grid, {
      label: t("system.overview.card.productVersion"),
      value: productVersionLabel(),
      detail: t("system.overview.card.productVersionDetail"),
    });

    const deliveryNumber = updateSnapshot?.deliveryNumber ?? null;
    const deliveryValue = Number.isSafeInteger(deliveryNumber) && deliveryNumber > 0
      ? t("system.overview.delivery.number", { value: deliveryNumber })
      : t("system.overview.delivery.unnumbered");
    appendMetricCard(documentObject, grid, {
      label: t("system.overview.card.delivery"),
      value: updateSnapshot ? deliveryValue : "—",
      detail: updateSnapshot
        ? t("system.overview.card.deliveryDetail", {
            sha: shortSha(updateSnapshot.sourceSha),
            mode: t(overviewUpdateModeMessageId(updateSnapshot.applyMode)),
          })
        : t("system.overview.card.deliveryUnavailable"),
    });

    const updateDetailMessageId = overviewUpdateDetailMessageId(updateSnapshot);
    const checkedAt = updateSnapshot?.checkedAt && updateSnapshot.checkedAt !== "unknown"
      ? formatOverviewTimestamp(updateSnapshot.checkedAt, localization.getLocale())
      : null;
    appendMetricCard(documentObject, grid, {
      label: t("system.overview.card.update"),
      value: updateSnapshot
        ? t(overviewUpdateSummaryMessageId(updateSnapshot))
        : t("system.overview.card.unavailable"),
      detail: updateDetailMessageId
        ? t(updateDetailMessageId)
        : checkedAt
          ? t("system.overview.card.updateChecked", { value: checkedAt })
          : t("system.overview.card.updateUnpublished"),
    });

    const connectivityMessageId = hostSnapshot.connectivity === "online"
      ? "system.overview.connectivity.online"
      : hostSnapshot.connectivity === "offline"
        ? "system.overview.connectivity.offline"
        : "system.overview.connectivity.unknown";
    appendMetricCard(documentObject, grid, {
      label: t("system.overview.card.connectivity"),
      value: t(connectivityMessageId),
      detail: t("system.overview.card.capabilities", {
        count: hostSnapshot.capabilityIds.length,
      }),
    });

    const receivedAt = formatOverviewReceivedAt(
      metricsLastSuccessAt,
      localization.getLocale(),
    ) ?? t("system.overview.time.unknown");
    appendMetricCard(documentObject, grid, {
      label: t("system.overview.card.uptime"),
      value: metricsSnapshot ? formatUptime(metricsSnapshot.uptimeSeconds) : "—",
      detail: !metricsPort
        ? t("system.overview.card.metricsUnavailable")
        : metricsReadFailed && metricsSnapshot
          ? t("system.overview.card.metricsPrevious", { time: receivedAt })
          : metricsSnapshot
            ? t("system.overview.card.metricsCurrent", { time: receivedAt })
            : t("system.overview.card.metricsWaiting"),
    });

    view.append(grid);
  };

  const renderMemory = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.resources.memory.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.resources.memory.title")),
    );
    const refresh = node(
      documentObject,
      "button",
      "ordax-system-action",
      metricsPending ? t("system.resources.action.refreshing") : t("system.resources.action.refresh"),
    );
    refresh.type = "button";
    refresh.dataset.systemOverviewRefresh = "";
    refresh.disabled = metricsPending || !metricsPort;
    heading.append(headingCopy, refresh);
    section.append(heading);

    if (!metricsPort || !metricsSnapshot) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          metricsPort
            ? metricsPending
              ? t("system.resources.memory.reading")
              : (metricsMessage ? t(metricsMessage) : t("system.resources.waiting"))
            : t("system.resources.memory.unavailable"),
        ),
      );
      view.append(section);
      return;
    }

    if (metricsReadFailed) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-warning",
          t("system.resources.stale", { time: formatOverviewReceivedAt(metricsLastSuccessAt, localization.getLocale()) ?? t("system.overview.time.unknown") }),
        ),
      );
    }

    const memoryUsed = metricsSnapshot.memoryTotalBytes - metricsSnapshot.memoryAvailableBytes;
    const resourceGrid = node(documentObject, "div", "ordax-system-resource-grid");
    appendMetricCard(documentObject, resourceGrid, {
      label: t("system.resources.memory.used"),
      value: formatBytes(memoryUsed),
      detail: t("system.resources.memory.availableOf", { available: formatBytes(metricsSnapshot.memoryAvailableBytes), total: formatBytes(metricsSnapshot.memoryTotalBytes) }),
      progress: ratio(memoryUsed, metricsSnapshot.memoryTotalBytes),
    });
    section.append(resourceGrid);
    if (metricsMessage) section.append(node(documentObject, "p", "ordax-system-message", t(metricsMessage)));
    view.append(section);
  };

  const renderStorage = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.resources.storage.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.resources.storage.title")),
    );
    const refresh = node(
      documentObject,
      "button",
      "ordax-system-action",
      metricsPending ? t("system.resources.action.refreshing") : t("system.resources.action.refresh"),
    );
    refresh.type = "button";
    refresh.dataset.systemOverviewRefresh = "";
    refresh.disabled = metricsPending || !metricsPort;
    heading.append(headingCopy, refresh);
    section.append(heading);

    if (!metricsPort || !metricsSnapshot) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          metricsPort
            ? metricsPending
              ? t("system.resources.storage.reading")
              : (metricsMessage ? t(metricsMessage) : t("system.resources.waiting"))
            : t("system.resources.storage.unavailable"),
        ),
      );
      view.append(section);
      return;
    }

    if (metricsReadFailed) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-warning",
          t("system.resources.stale", { time: formatOverviewReceivedAt(metricsLastSuccessAt, localization.getLocale()) ?? t("system.overview.time.unknown") }),
        ),
      );
    }

    const storageUsed = metricsSnapshot.userStorageTotalBytes - metricsSnapshot.userStorageFreeBytes;
    const resourceGrid = node(documentObject, "div", "ordax-system-resource-grid");
    appendMetricCard(documentObject, resourceGrid, {
      label: t("system.resources.storage.used"),
      value: formatBytes(storageUsed),
      detail: t("system.resources.storage.freeOf", { free: formatBytes(metricsSnapshot.userStorageFreeBytes), total: formatBytes(metricsSnapshot.userStorageTotalBytes) }),
      progress: ratio(storageUsed, metricsSnapshot.userStorageTotalBytes),
    });
    section.append(resourceGrid);
    section.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        t("system.resources.storage.scope"),
      ),
    );
    if (metricsMessage) section.append(node(documentObject, "p", "ordax-system-message", t(metricsMessage)));
    view.append(section);
  };

  const updatePhaseMessageId = (phase) => ({
    checking: "system.updates.phase.checking",
    fetching: "system.updates.phase.fetching",
    validating: "system.updates.phase.validating",
    activating: "system.updates.phase.activating",
    "health-wait": "system.updates.phase.healthWait",
    rollback: "system.updates.phase.rollback",
    blocked: "system.updates.phase.blocked",
    error: "system.updates.phase.error",
  }[phase] ?? "system.updates.phase.idle");

  const baseUpdatePhaseMessageId = (phase) => ({
    "waiting-candidate": "system.updates.basePhase.waitingCandidate",
    "candidate-requested": "system.updates.basePhase.candidateRequested",
    "candidate-fetching": "system.updates.basePhase.candidateFetching",
    "candidate-ready": "system.updates.basePhase.candidateReady",
    staged: "system.updates.basePhase.staged",
    "activation-ready": "system.updates.basePhase.activationReady",
  }[phase] ?? "system.updates.basePhase.none");

  const bootMessageId = (snapshot) => {
    if (!snapshot?.bootRefreshRequired) return "system.updates.boot.none";
    return ({
      "candidate-requested": "system.updates.boot.candidateRequested",
      "candidate-fetching": "system.updates.boot.candidateFetching",
      "candidate-ready": "system.updates.boot.candidateReady",
      staged: "system.updates.boot.staged",
      "activation-ready": "system.updates.boot.activationReady",
    }[snapshot.baseUpdatePhase] ?? "system.updates.boot.pending");
  };

  const localizedDelivery = (value) => Number.isSafeInteger(value) && value > 0
    ? t("system.overview.delivery.number", { value })
    : t("system.overview.delivery.unnumbered");

  const localizedTimestamp = (value) =>
    formatOverviewTimestamp(value, localization.getLocale()) ?? "—";

  const localizedUpdateAttention = (snapshot) => snapshot?.bootRefreshRequired
    ? t(overviewUpdateDetailMessageId(snapshot) ?? "system.overview.update.detail.pending")
    : t("system.updates.attention.generic");

  const renderUpdateDetails = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.updates.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.updates.title")),
    );
    heading.append(headingCopy);
    section.append(heading);

    if (!updateSnapshot) {
      section.append(
        node(documentObject, "p", "ordax-system-placeholder", t("system.updates.unavailable")),
      );
      view.append(section);
      return;
    }

    const facts = node(documentObject, "dl", "ordax-system-facts");
    const addFact = (label, value) => {
      const item = node(documentObject, "div", "ordax-system-fact");
      item.append(
        node(documentObject, "dt", "", label),
        node(documentObject, "dd", "", value),
      );
      facts.append(item);
    };

    addFact(t("system.updates.fact.delivery"), localizedDelivery(updateSnapshot.deliveryNumber));
    addFact(t("system.updates.fact.sourceCommit"), shortSha(updateSnapshot.sourceSha));
    if (updateSnapshot.runtimeSurfaceSha) {
      addFact(t("system.updates.fact.runtimeSurface"), shortSha(updateSnapshot.runtimeSurfaceSha));
    }
    addFact(t("system.updates.fact.status"), t(overviewUpdateStatusMessageId(updateSnapshot.status)));
    addFact(t("system.updates.fact.phase"), t(updatePhaseMessageId(updateSnapshot.phase)));
    addFact(t("system.updates.fact.applyMode"), t(overviewUpdateModeMessageId(updateSnapshot.applyMode)));
    if (updateSnapshot.targetSha) {
      addFact(t("system.updates.fact.target"), shortSha(updateSnapshot.targetSha));
    }
    if (updateSnapshot.attemptId) {
      addFact(t("system.updates.fact.attempt"), localizedTimestamp(updateSnapshot.attemptId));
    }
    if (updateSnapshot.checkedAt && updateSnapshot.checkedAt !== "unknown") {
      addFact(t("system.updates.fact.checkedAt"), localizedTimestamp(updateSnapshot.checkedAt));
    }
    if (updateSnapshot.lastError) {
      addFact(t("system.updates.fact.diagnostic"), updateSnapshot.lastError);
    }
    if (updateSnapshot.lastAppliedAt !== "unknown") {
      addFact(t("system.updates.fact.lastAppliedAt"), localizedTimestamp(updateSnapshot.lastAppliedAt));
      addFact(
        t("system.updates.fact.duration"),
        t("system.updates.duration", {
          apply: updateSnapshot.lastApplyDurationSeconds,
          stage: updateSnapshot.lastStageDurationSeconds,
        }),
      );
    }
    if (updateSnapshot.rejectedSha) {
      addFact(t("system.updates.fact.rejectedCommit"), shortSha(updateSnapshot.rejectedSha));
    }
    if (updateSnapshot.bootRefreshRequired) {
      addFact(t("system.updates.fact.baseProgress"), t(baseUpdatePhaseMessageId(updateSnapshot.baseUpdatePhase)));
      if (updateSnapshot.baseUpdateSha) {
        addFact(t("system.updates.fact.baseCandidate"), shortSha(updateSnapshot.baseUpdateSha));
      }
    }
    addFact(t("system.updates.fact.boot"), t(bootMessageId(updateSnapshot)));
    section.append(facts);

    if (updateIsAlerting(updateSnapshot)) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-warning",
          localizedUpdateAttention(updateSnapshot),
        ),
      );
    }

    view.append(section);
  };

  const renderRecovery = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    section.dataset.systemRecovery = "";
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.recovery.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.recovery.title")),
    );
    const refresh = node(
      documentObject,
      "button",
      "ordax-system-action",
      recoveryPending ? t("system.recovery.refreshing") : t("system.recovery.refresh"),
    );
    refresh.type = "button";
    refresh.dataset.systemRecoveryRefresh = "";
    refresh.disabled = recoveryPending || recoveryPort === null;
    heading.append(headingCopy, refresh);
    section.append(heading);

    section.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        t("system.recovery.policy"),
      ),
    );

    if (!recoveryPort) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          t("system.recovery.unavailableMode"),
        ),
      );
      view.append(section);
      return;
    }

    if (!recoverySnapshot) {
      section.append(
        node(
          documentObject,
          "p",
          recoveryMessage ? "ordax-system-warning" : "ordax-system-placeholder",
          recoveryMessage || t("system.recovery.reading"),
        ),
      );
      view.append(section);
      return;
    }

    const facts = node(documentObject, "dl", "ordax-system-facts");
    const addFact = (label, value) => {
      const item = node(documentObject, "div", "ordax-system-fact");
      item.append(
        node(documentObject, "dt", "", label),
        node(documentObject, "dd", "", value),
      );
      facts.append(item);
    };
    const shaValue = (value) => value ? shortSha(value) : t("system.recovery.notObserved");
    const slotLabel = {
      current: t("system.recovery.slot.current"),
      "known-good": t("system.recovery.slot.knownGood"),
      candidate: t("system.recovery.slot.candidate"),
      unknown: t("system.recovery.slot.unknown"),
    }[recoverySnapshot.bootSlot] ?? recoverySnapshot.bootSlot;
    const entryLabel = {
      verified: t("system.recovery.entry.verified"),
      missing: t("system.recovery.entry.missing"),
      invalid: t("system.recovery.entry.invalid"),
      unavailable: t("system.recovery.entry.unavailable"),
    }[recoverySnapshot.recoveryEntryStatus] ?? recoverySnapshot.recoveryEntryStatus;

    addFact(t("system.recovery.fact.runningSlot"), slotLabel);
    addFact(t("system.recovery.fact.runningSource"), shaValue(recoverySnapshot.runningSourceSha));
    addFact(t("system.recovery.fact.current"), shaValue(recoverySnapshot.currentSha));
    addFact(t("system.recovery.fact.knownGood"), shaValue(recoverySnapshot.knownGoodSha));
    addFact(t("system.recovery.fact.candidate"), shaValue(recoverySnapshot.candidateSha));
    addFact(
      t("system.recovery.fact.transaction"),
      recoverySnapshot.transactionPresent
        ? t("system.recovery.transaction.present")
        : t("system.recovery.transaction.absent"),
    );
    addFact(t("system.recovery.fact.entry"), entryLabel);
    section.append(facts);

    if (recoverySnapshot.recoveryEntryStatus !== "verified") {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-warning",
          t("system.recovery.entryWarning"),
        ),
      );
    }
    if (recoveryMessage) {
      section.append(node(documentObject, "p", "ordax-system-message", recoveryMessage));
    }
    view.append(section);
  };

  const componentReleaseLabel = (mode) => t(({
    "base-ab": "system.updates.component.release.baseAb",
    "component-slot": "system.updates.component.release.componentSlot",
    "git-app": "system.updates.component.release.gitApp",
    bundled: "system.updates.component.release.bundled",
  }[mode] ?? "system.updates.component.release.bundled"));

  const componentKindLabel = (kind) => t(({
    base: "system.updates.component.kind.base",
    shell: "system.updates.component.kind.shell",
    service: "system.updates.component.kind.service",
    app: "system.updates.component.kind.app",
  }[kind] ?? "system.updates.component.kind.app"));

  const componentHealthLabel = (health) => t(({
    healthy: "system.updates.component.health.healthy",
    failed: "system.updates.component.health.failed",
    unknown: "system.updates.component.health.unknown",
  }[health] ?? "system.updates.component.health.unknown"));

  const componentChannelLabel = (channelId) => t(({
    "system-base": "system.updates.component.channel.systemBase",
    "system-bundle": "system.updates.component.channel.systemBundle",
    "development-git": "system.updates.component.channel.developmentGit",
    "independent-component": "system.updates.component.channel.independentComponent",
  }[channelId] ?? "system.updates.component.channel.systemBundle"));

  const componentDetail = (releaseMode) => t(({
    "base-ab": "system.updates.component.detail.baseAb",
    "component-slot": "system.updates.component.detail.componentSlot",
    "git-app": "system.updates.component.detail.gitApp",
    bundled: "system.updates.component.detail.bundled",
  }[releaseMode] ?? "system.updates.component.detail.bundled"));

  const renderComponentUpdateScopes = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.updates.scope.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.updates.scope.title")),
    );
    heading.append(headingCopy);
    section.append(heading);

    if (!componentSnapshot) {
      section.append(
        node(documentObject, "p", "ordax-system-placeholder", t("system.updates.scope.unavailable")),
      );
      view.append(section);
      return;
    }

    const scopes = createComponentUpdateScopes(componentSnapshot);
    section.append(
      node(documentObject, "p", "ordax-system-section-copy", t("system.updates.scope.policy")),
      node(documentObject, "p", "ordax-system-section-copy", t("system.updates.scope.channelPolicy")),
    );

    const renderScope = (title, components, scopeId) => {
      const group = node(documentObject, "div", "ordax-system-history");
      group.dataset.updateScope = scopeId;
      group.append(node(documentObject, "h5", "ordax-system-history-title", title));
      const list = node(documentObject, "div", "ordax-system-version-grid");

      for (const component of components) {
        const item = node(documentObject, "div", "ordax-system-version-item");
        item.dataset.componentId = component.id;
        item.dataset.releaseMode = component.releaseMode;
        item.dataset.updateChannel = component.updateChannel.id;
        const maturity = component.versionStage === "beta"
          ? t("system.updates.scope.stage.beta")
          : component.versionStage === "stable"
            ? t("system.updates.scope.stage.stable")
            : "";
        item.append(
          node(documentObject, "strong", "", component.title),
          node(
            documentObject,
            "span",
            "",
            `v${component.version}${maturity} · ${componentChannelLabel(component.updateChannel.id)}`,
          ),
          node(
            documentObject,
            "small",
            "ordax-system-component-health",
            t("system.updates.scope.health", { health: componentHealthLabel(component.health) }),
          ),
        );

        item.append(
          node(
            documentObject,
            "small",
            "ordax-system-component-slots",
            componentDetail(component.releaseMode),
          ),
        );

        if (component.independentUpdate) {
          item.append(
            node(
              documentObject,
              "small",
              "ordax-system-component-slots",
              t("system.updates.scope.previousPending", {
                previous: component.previousVersion ? `v${component.previousVersion}` : "—",
                pending: component.pendingVersion ? `v${component.pendingVersion}` : "—",
              }),
            ),
          );
        }
        list.append(item);
      }
      group.append(list);
      section.append(group);
    };

    renderScope(t("system.updates.scope.system"), scopes.system, "system");
    renderScope(t("system.updates.scope.applications"), scopes.applications, "applications");
    section.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        scopes.persistence === "device"
          ? t("system.updates.scope.persistence.device")
          : t("system.updates.scope.persistence.session"),
      ),
    );
    view.append(section);
  };

  const renderComponentVersions = (view) => {
    const versionSection = node(documentObject, "section", "ordax-system-section");
    const versionHeading = node(documentObject, "div", "ordax-system-section-heading");
    const versionHeadingCopy = node(documentObject, "div");
    versionHeadingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.about.version.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", productVersionLabel()),
    );
    versionHeading.append(versionHeadingCopy);
    versionSection.append(versionHeading);
    versionSection.append(
      node(documentObject, "p", "ordax-system-section-copy", t("system.about.version.policy")),
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        PRODUCT_VERSION.stableRelease
          ? t("system.about.version.stable")
          : t("system.about.version.prototype"),
      ),
    );
    view.append(versionSection);

    const deliverySection = node(documentObject, "section", "ordax-system-section");
    const deliveryHeading = node(documentObject, "div", "ordax-system-section-heading");
    const deliveryHeadingCopy = node(documentObject, "div");
    deliveryHeadingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.about.delivery.kicker")),
      node(
        documentObject,
        "h4",
        "ordax-system-section-title",
        updateSnapshot?.deliveryNumber
          ? localizedDelivery(updateSnapshot.deliveryNumber)
          : t("system.about.delivery.unavailable"),
      ),
    );
    deliveryHeading.append(deliveryHeadingCopy);
    deliverySection.append(deliveryHeading);
    deliverySection.append(
      node(documentObject, "p", "ordax-system-section-copy", t("system.about.delivery.policy")),
    );
    if (!updateSnapshot?.deliveryNumber) {
      deliverySection.append(
        node(documentObject, "p", "ordax-system-placeholder", t("system.about.delivery.hostUnavailable")),
      );
    }
    view.append(deliverySection);

    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.about.components.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.about.components.title")),
    );
    heading.append(headingCopy);
    section.append(heading);

    if (!componentSnapshot) {
      section.append(
        node(documentObject, "p", "ordax-system-placeholder", t("system.about.components.unavailable")),
      );
      view.append(section);
      return;
    }

    section.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        componentSnapshot.persistence === "device"
          ? t("system.about.components.persistence.device")
          : t("system.about.components.persistence.session"),
      ),
    );

    const list = node(documentObject, "div", "ordax-system-version-grid");
    for (const component of componentSnapshot.components) {
      const { manifest, state, independentUpdate } = component;
      const item = node(documentObject, "div", "ordax-system-version-item");
      item.dataset.componentId = manifest.id;
      item.dataset.releaseMode = manifest.releaseMode;
      const title = node(documentObject, "strong", "", manifest.title);
      const identity = node(
        documentObject,
        "span",
        "",
        `${componentKindLabel(manifest.kind)} · v${state.currentVersion} · ${componentReleaseLabel(manifest.releaseMode)}`,
      );
      const health = node(
        documentObject,
        "small",
        "ordax-system-component-health",
        t("system.about.components.health", {
          health: componentHealthLabel(state.currentHealth),
          domain: manifest.failureDomain,
        }),
      );
      item.append(title, identity, health);

      if (independentUpdate) {
        item.append(
          node(
            documentObject,
            "small",
            "ordax-system-component-slots",
            t("system.about.components.previousPending", {
              previous: state.previousVersion ? `v${state.previousVersion}` : "—",
              pending: state.pendingVersion ? `v${state.pendingVersion}` : "—",
            }),
          ),
        );
      } else {
        const detailId = manifest.releaseMode === "base-ab"
          ? "system.about.components.detail.baseAb"
          : manifest.releaseMode === "git-app"
            ? "system.about.components.detail.gitApp"
            : "system.about.components.detail.bundled";
        item.append(
          node(documentObject, "small", "ordax-system-component-slots", t(detailId)),
        );
      }
      list.append(item);
    }
    section.append(list);
    view.append(section);
  };
  const renderHistory = (view) => {
    if (!historyPort) return;
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.updates.history.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.updates.history.title")),
    );
    const refresh = node(
      documentObject,
      "button",
      "ordax-system-action",
      t("system.updates.history.refresh"),
    );
    refresh.type = "button";
    refresh.dataset.systemHistoryRefresh = "";
    heading.append(headingCopy, refresh);
    section.append(heading);

    if (!historySnapshot) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          historyMessage || t("system.updates.history.reading"),
        ),
      );
      view.append(section);
      return;
    }

    const applications = node(documentObject, "div", "ordax-system-history");
    applications.append(
      node(documentObject, "h5", "ordax-system-history-title", t("system.updates.history.applications")),
    );
    if (historySnapshot.applications.length === 0) {
      applications.append(
        node(documentObject, "p", "ordax-system-placeholder", t("system.updates.history.empty")),
      );
    } else {
      for (const entry of historySnapshot.applications.slice(0, 10)) {
        const item = node(documentObject, "article", "ordax-system-history-item");
        const result = entry.result === "applied"
          ? t("system.updates.history.result.applied")
          : t("system.updates.history.result.rolledBack");
        item.append(
          node(documentObject, "strong", "", `${localizedDelivery(entry.deliveryNumber)} · ${result}`),
          node(documentObject, "span", "", localizedTimestamp(entry.appliedAt)),
          node(
            documentObject,
            "small",
            "",
            t("system.updates.history.applicationDetail", {
              sha: shortSha(entry.sourceSha),
              mode: t(overviewUpdateModeMessageId(entry.applyMode)),
              apply: entry.applyDurationSeconds,
              stage: entry.stageDurationSeconds,
            }),
          ),
        );
        applications.append(item);
      }
    }

    const releases = node(documentObject, "div", "ordax-system-history");
    releases.append(
      node(documentObject, "h5", "ordax-system-history-title", t("system.updates.history.releases")),
    );
    for (const entry of historySnapshot.releases.slice(0, 12)) {
      const item = node(documentObject, "article", "ordax-system-history-item");
      item.append(
        node(documentObject, "strong", "", `${localizedDelivery(entry.deliveryNumber)} · ${entry.title}`),
        node(documentObject, "span", "", localizedTimestamp(entry.releasedAt)),
        node(
          documentObject,
          "small",
          "",
          t("system.updates.history.releaseDetail", { sha: shortSha(entry.sourceSha) }),
        ),
      );
      releases.append(item);
    }

    section.append(applications, releases);
    if (historyMessage) section.append(node(documentObject, "p", "ordax-system-message", historyMessage));
    view.append(section);
  };

  const renderCapabilities = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.capabilities.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.capabilities.title")),
    );
    heading.append(headingCopy);
    section.append(heading);

    const list = node(documentObject, "div", "ordax-system-capabilities");
    if (hostSnapshot.capabilityIds.length === 0) {
      list.append(
        node(documentObject, "p", "ordax-system-placeholder", t("system.capabilities.empty")),
      );
    } else {
      for (const capabilityId of hostSnapshot.capabilityIds) {
        const item = node(documentObject, "div", "ordax-system-capability");
        const messageId = CAPABILITY_MESSAGE_IDS[capabilityId] ?? null;
        item.append(
          node(documentObject, "span", "ordax-system-capability-dot"),
          node(documentObject, "strong", "", messageId ? t(messageId) : capabilityId),
          node(documentObject, "small", "", capabilityId),
        );
        list.append(item);
      }
    }
    section.append(list);
    view.append(section);
  };

  const renderIntelligence = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", t("system.intelligence.kicker")),
      node(documentObject, "h4", "ordax-system-section-title", t("system.intelligence.title")),
    );
    const action = node(
      documentObject,
      "button",
      "ordax-system-action",
      intelligencePending
        ? t("system.intelligence.action.explaining")
        : t("system.intelligence.action.explain"),
    );
    action.type = "button";
    action.dataset.systemIntelligenceExplain = "";
    const ready = intelligenceSnapshot?.state === "ready";
    action.disabled = !ready || intelligencePending;
    action.title = ready
      ? t("system.intelligence.action.readyTitle")
      : t("system.intelligence.action.unavailableTitle");
    heading.append(headingCopy, action);
    section.append(heading);

    const stateMessageId = intelligenceSnapshot === null
      ? "system.intelligence.state.unavailable"
      : intelligenceSnapshot.state === "ready"
        ? "system.intelligence.state.ready"
        : intelligenceSnapshot.state === "busy"
          ? "system.intelligence.state.busy"
          : intelligenceSnapshot.state === "degraded"
            ? "system.intelligence.state.degraded"
            : "system.intelligence.state.error";
    const stateLabel = t(stateMessageId);
    const detail = intelligenceSnapshot?.modelId
      ? `${stateLabel} · ${intelligenceSnapshot.modelId}`
      : stateLabel;
    section.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        t("system.intelligence.status", { detail }),
      ),
    );

    if (intelligenceMessage) {
      const message = node(
        documentObject,
        "p",
        intelligenceAnswer ? "ordax-system-message" : "ordax-system-warning",
        t(intelligenceMessage),
      );
      message.setAttribute("role", "status");
      message.setAttribute("aria-live", "polite");
      section.append(message);
    }
    if (intelligenceAnswer) {
      const answer = node(documentObject, "article", "ordax-system-history-item");
      answer.dataset.state = "info";
      answer.append(
        node(documentObject, "strong", "", t("system.intelligence.answerTitle")),
        node(documentObject, "p", "ordax-system-section-copy", intelligenceAnswer),
        node(documentObject, "small", "", t("system.intelligence.source")),
      );
      section.append(answer);
    }
    view.append(section);
  };

  const renderDiagnosticReviewMount = (view) => {
    if (diagnosticReviewController === null) return null;
    const mount = node(documentObject, "div", "");
    mount.dataset.systemDiagnosticsReviewMount = "";
    view.append(mount);
    return mount;
  };

  const paint = (slot, interaction = null) => {
    disposeDiagnosticsReview();
    slot.replaceChildren();
    slot.dataset.ordaxSystemOverviewView = "";
    slot.dataset.systemActiveSection = activeSection;

    const view = node(documentObject, "div", "ordax-system-view");
    renderHeader(view);
    renderSectionNavigation(view);
    let diagnosticMount = null;

    if (activeSection === "overview") {
      renderSummary(view);
      renderMemory(view);
    } else if (activeSection === "updates") {
      renderUpdateDetails(view);
      renderRecovery(view);
      renderComponentUpdateScopes(view);
      renderHistory(view);
    } else if (activeSection === "storage") {
      renderStorage(view);
    } else if (activeSection === "diagnostics") {
      diagnosticMount = renderDiagnosticReviewMount(view);
      renderIntelligence(view);
      renderCapabilities(view);
    } else if (activeSection === "about") {
      renderComponentVersions(view);
    }
    slot.append(view);

    if (diagnosticMount) {
      diagnosticsReviewMount = mountSystemDiagnosticsReview(
        diagnosticMount,
        diagnosticReviewController,
        lifecycle,
      );
    }
    restoreInteractionState(slot, interaction);
  };

  const renderView = (force = false) => {
    if (destroyed) return;
    const slot = findSlot();
    if (!slot) {
      disposeDiagnosticsReview();
      mountedSlot = null;
      return;
    }
    if (!force && mountedSlot === slot) return;
    const interaction =
      force && slot === mountedSlot ? captureInteractionState(slot) : null;
    mountedSlot = slot;
    paint(slot, interaction);
  };

  const replaceView = () => renderView(true);

  const refreshMetrics = async () => {
    if (!metricsPort || metricsPending) return;
    const ordinal = ++metricsOrdinal;
    metricsPending = true;
    metricsMessage = "";
    replaceView();
    try {
      const next = validateSystemMetricsSnapshot(await metricsPort.read());
      if (destroyed || ordinal !== metricsOrdinal) return;
      metricsSnapshot = next;
      metricsReadFailed = false;
      metricsLastSuccessAt = Date.now();
    } catch {
      if (destroyed || ordinal !== metricsOrdinal) return;
      metricsReadFailed = true;
      metricsMessage = metricsSnapshot
        ? "system.resources.readFailedPrevious"
        : "system.resources.readFailedNoData";
    } finally {
      if (!destroyed && ordinal === metricsOrdinal) {
        metricsPending = false;
        replaceView();
      }
    }
  };

  const refreshRecovery = async () => {
    if (!recoveryPort || recoveryPending) return;
    const ordinal = ++recoveryOrdinal;
    recoveryPending = true;
    recoveryMessage = "";
    replaceView();
    try {
      const next = validateRecoveryStatusSnapshot(await recoveryPort.read());
      if (destroyed || ordinal !== recoveryOrdinal) return;
      recoverySnapshot = next;
    } catch {
      if (destroyed || ordinal !== recoveryOrdinal) return;
      recoverySnapshot = null;
      recoveryMessage = t("system.recovery.readFailed");
    } finally {
      if (!destroyed && ordinal === recoveryOrdinal) {
        recoveryPending = false;
        replaceView();
      }
    }
  };

  const refreshHistory = async () => {
    if (!historyPort) return;
    const ordinal = ++historyOrdinal;
    historyMessage = "";
    try {
      const next = validateUpdateHistorySnapshot(await historyPort.list());
      if (destroyed || ordinal !== historyOrdinal) return;
      historySnapshot = next;
    } catch {
      if (destroyed || ordinal !== historyOrdinal) return;
      historyMessage = t("system.updates.history.readFailed");
    } finally {
      if (!destroyed && ordinal === historyOrdinal) replaceView();
    }
  };

  const onClick = (event) => {
    const section = event.target.closest("[data-system-section]");
    if (section && root.contains(section) && validSystemSection(section.dataset.systemSection)) {
      const nextSection = section.dataset.systemSection;
      if (activationPort) {
        activationPort.publish({ appId: "system", target: nextSection });
      } else {
        activeSection = nextSection;
        replaceView();
      }
      return;
    }

    const refresh = event.target.closest("[data-system-overview-refresh]");
    if (refresh && root.contains(refresh)) {
      void refreshMetrics();
      return;
    }
    const historyRefresh = event.target.closest("[data-system-history-refresh]");
    if (historyRefresh && root.contains(historyRefresh)) {
      void refreshHistory();
      return;
    }
    const recoveryRefresh = event.target.closest("[data-system-recovery-refresh]");
    if (recoveryRefresh && root.contains(recoveryRefresh)) {
      void refreshRecovery();
      return;
    }

    const intelligenceExplain = event.target.closest("[data-system-intelligence-explain]");
    if (
      intelligenceExplain
      && root.contains(intelligenceExplain)
      && intelligencePort
      && intelligenceSnapshot?.state === "ready"
      && !intelligencePending
    ) {
      intelligencePending = true;
      intelligenceAnswer = "";
      intelligenceMessage = "system.intelligence.progress";
      replaceView();
      void explainSystemStateWithIntelligence(intelligencePort, {
        surface: hostSnapshot,
        metrics: metricsSnapshot,
      }).then((response) => {
        if (destroyed) return;
        intelligenceAnswer = response.text;
        intelligenceMessage = "system.intelligence.success";
      }).catch(() => {
        if (destroyed) return;
        intelligenceMessage = "system.intelligence.failed";
      }).finally(() => {
        if (destroyed) return;
        intelligencePending = false;
        replaceView();
      });
    }
  };

  root.addEventListener("click", onClick);
  const unsubscribeRender = lifecycle.subscribeRender(() => {
    const persistedTarget = lifecycle.getAppTarget("system");
    const nextSection = validSystemSection(persistedTarget) ? persistedTarget : "overview";
    activeSection = nextSection;
    renderView(false);
  });
  const unsubscribeHost = hostPort.subscribe((snapshot) => {
    hostSnapshot = validateSurfaceSnapshot(snapshot);
    replaceView();
  });
  const unsubscribeActivation = activationPort?.subscribe((activation) => {
    if (
      activation.appId === "system"
      && activation.target !== null
      && validSystemSection(activation.target)
    ) {
      activeSection = activation.target;
      replaceView();
    }
  });
  const unsubscribeComponents = componentPort?.subscribe((snapshot) => {
    componentSnapshot = validateComponentManagerSnapshot(snapshot);
    replaceView();
  });
  const unsubscribeIntelligence = intelligencePort?.subscribe((snapshot) => {
    intelligenceSnapshot = validateIntelligenceSnapshot(snapshot);
    replaceView();
  });
  const unsubscribeUpdate = updatePort?.subscribe((snapshot) => {
    const previousAppliedSha = updateSnapshot?.lastAppliedSha ?? "";
    updateSnapshot = validateUpdateStatusSnapshot(snapshot);
    replaceView();
    if (historyPort && updateSnapshot.lastAppliedSha !== previousAppliedSha) {
      void refreshHistory();
    }
  });

  if (metricsPort) void refreshMetrics();
  if (historyPort) void refreshHistory();
  if (recoveryPort) void refreshRecovery();

  return Object.freeze({
    destroy() {
      destroyed = true;
      metricsOrdinal += 1;
      historyOrdinal += 1;
      recoveryOrdinal += 1;
      disposeDiagnosticsReview();
      unsubscribeUpdate?.();
      unsubscribeIntelligence?.();
      unsubscribeComponents?.();
      unsubscribeActivation?.();
      unsubscribeHost?.();
      unsubscribeRender();
      root.removeEventListener("click", onClick);
      const slot = findSlot();
      if (slot?.dataset.ordaxSystemOverviewView !== undefined) {
        slot.replaceChildren();
        delete slot.dataset.ordaxSystemOverviewView;
      }
      mountedSlot = null;
    },
  });
}
