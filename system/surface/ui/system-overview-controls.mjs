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
  deliveryLabel,
  formatUpdateTimestamp,
  readableBaseUpdatePhase,
  readableUpdateMode,
  readableUpdatePhase,
  shortSha,
  updateAttentionMessage,
  updateBootLabel,
  updateIsAlerting,
  updateStatusLabel,
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

const CAPABILITY_LABELS = Object.freeze({
  "network.https": "Rede HTTPS",
  "network.status": "Estado local de rede",
  "network.management": "Gerenciamento de Wi-Fi",
  "system.boot-control": "Energia do dispositivo",
  "filesystem.user-space": "Espaço local do usuário",
  "system.metrics": "Métricas do dispositivo",
  "power.status": "Estado da bateria",
  "intelligence.system": "Ordax Intelligence",
});

function node(documentObject, tag, className, text) {
  const element = documentObject.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function formatObservationReceivedAt(value) {
  if (!Number.isFinite(value)) return "horário desconhecido";
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Bahia",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
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
              : (metricsMessage || t("system.resources.waiting"))
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
          t("system.resources.stale", { time: formatObservationReceivedAt(metricsLastSuccessAt) }),
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
    if (metricsMessage) section.append(node(documentObject, "p", "ordax-system-message", metricsMessage));
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
              : (metricsMessage || t("system.resources.waiting"))
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
          t("system.resources.stale", { time: formatObservationReceivedAt(metricsLastSuccessAt) }),
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
    if (metricsMessage) section.append(node(documentObject, "p", "ordax-system-message", metricsMessage));
    view.append(section);
  };

  const renderUpdateDetails = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", "Atualização"),
      node(documentObject, "h4", "ordax-system-section-title", "Entrega e recuperação"),
    );
    heading.append(headingCopy);
    section.append(heading);

    if (!updateSnapshot) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          "Este host não publica o estado do supervisor de atualizações.",
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

    addFact("Entrega", deliveryLabel(updateSnapshot.deliveryNumber));
    addFact("Commit técnico", shortSha(updateSnapshot.sourceSha));
    if (updateSnapshot.runtimeSurfaceSha) {
      addFact("Surface em execução", shortSha(updateSnapshot.runtimeSurfaceSha));
    }
    addFact("Estado", updateStatusLabel(updateSnapshot.status));
    addFact("Fase", readableUpdatePhase(updateSnapshot.phase));
    addFact("Aplicação", readableUpdateMode(updateSnapshot.applyMode));
    if (updateSnapshot.targetSha) {
      addFact("Alvo", shortSha(updateSnapshot.targetSha));
    }
    if (updateSnapshot.attemptId) {
      addFact("Tentativa", formatUpdateTimestamp(updateSnapshot.attemptId));
    }
    if (updateSnapshot.checkedAt && updateSnapshot.checkedAt !== "unknown") {
      addFact("Última verificação", formatUpdateTimestamp(updateSnapshot.checkedAt));
    }
    if (updateSnapshot.lastError) {
      addFact("Diagnóstico", updateSnapshot.lastError);
    }
    if (updateSnapshot.lastAppliedAt !== "unknown") {
      addFact("Última aplicação", formatUpdateTimestamp(updateSnapshot.lastAppliedAt));
      addFact("Duração", `${updateSnapshot.lastApplyDurationSeconds}s · preparação ${updateSnapshot.lastStageDurationSeconds}s`);
    }
    if (updateSnapshot.rejectedSha) {
      addFact("Commit bloqueado", shortSha(updateSnapshot.rejectedSha));
    }
    if (updateSnapshot.bootRefreshRequired) {
      addFact("Progresso da Base", readableBaseUpdatePhase(updateSnapshot.baseUpdatePhase));
      if (updateSnapshot.baseUpdateSha) {
        addFact("Base candidata", shortSha(updateSnapshot.baseUpdateSha));
      }
    }
    addFact("Boot", updateBootLabel(updateSnapshot));
    section.append(facts);

    if (updateIsAlerting(updateSnapshot)) {
      const warning = node(
        documentObject,
        "p",
        "ordax-system-warning",
        updateAttentionMessage(updateSnapshot),
      );
      section.append(warning);
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

  const componentReleaseLabel = (mode) => ({
    "base-ab": "Base A/B",
    "component-slot": "Slot independente",
    "git-app": "App via Git",
    bundled: "Distribuição conjunta",
  }[mode] ?? mode);

  const componentKindLabel = (kind) => ({
    base: "Base",
    shell: "Shell",
    service: "Serviço",
    app: "App",
  }[kind] ?? kind);

  const componentHealthLabel = (health) => ({
    healthy: "Saudável",
    failed: "Falha",
    unknown: "Não observado",
  }[health] ?? health);

  const renderComponentUpdateScopes = (view) => {
    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", "Escopo"),
      node(documentObject, "h4", "ordax-system-section-title", "OrdaX e aplicativos"),
    );
    heading.append(headingCopy);
    section.append(heading);

    if (!componentSnapshot) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          "O catálogo de componentes não está disponível nesta composição.",
        ),
      );
      view.append(section);
      return;
    }

    const scopes = createComponentUpdateScopes(componentSnapshot);
    section.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        "A versão de cada componente e o canal que o entrega são informações separadas. Apps Beta podem ter versão própria mesmo quando ainda atualizam junto com o OrdaX ou, no ambiente de desenvolvimento, diretamente pelo Git.",
      ),
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        "Esta tela descreve os canais realmente habilitados; ela não representa uma Loja nem libera atualização independente de produção quando o componente ainda não usa slot assinado.",
      ),
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
          ? " · Beta"
          : component.versionStage === "stable"
            ? " · Estável"
            : "";
        item.append(
          node(documentObject, "strong", "", component.title),
          node(
            documentObject,
            "span",
            "",
            `v${component.version}${maturity} · ${component.updateChannel.label}`,
          ),
          node(
            documentObject,
            "small",
            "ordax-system-component-health",
            `Saúde: ${componentHealthLabel(component.health)}`,
          ),
        );

        const detail = component.releaseMode === "base-ab"
          ? "A Base usa o ciclo A/B do OrdaX; não é um app independente."
          : component.releaseMode === "component-slot"
            ? "Atualização independente exige pacote assinado, saúde, promoção e rollback."
            : component.releaseMode === "git-app"
              ? "Canal de desenvolvimento via Git; não é o atualizador de produção do app."
              : "Atualiza junto com a entrega do OrdaX; rollback individual não está habilitado.";
        item.append(node(documentObject, "small", "ordax-system-component-slots", detail));

        if (component.independentUpdate) {
          item.append(
            node(
              documentObject,
              "small",
              "ordax-system-component-slots",
              `Anterior: ${component.previousVersion ? `v${component.previousVersion}` : "—"} · Pendente: ${component.pendingVersion ? `v${component.pendingVersion}` : "—"}`,
            ),
          );
        }
        list.append(item);
      }
      group.append(list);
      section.append(group);
    };

    renderScope("OrdaX e sistema", scopes.system, "system");
    renderScope("Aplicativos", scopes.applications, "applications");
    section.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        scopes.persistence === "device"
          ? "Estado de componentes e saúde persistido neste dispositivo."
          : "Catálogo disponível; estado de componentes permanece somente nesta sessão.",
      ),
    );
    view.append(section);
  };

  const renderComponentVersions = (view) => {
    const versionSection = node(documentObject, "section", "ordax-system-section");
    const versionHeading = node(documentObject, "div", "ordax-system-section-heading");
    const versionHeadingCopy = node(documentObject, "div");
    versionHeadingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", "Versão do produto"),
      node(documentObject, "h4", "ordax-system-section-title", productVersionLabel()),
    );
    versionHeading.append(versionHeadingCopy);
    versionSection.append(versionHeading);
    versionSection.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        "A versão do produto identifica o marco geral. Cada componente possui identidade própria. Durante o desenvolvimento, apps podem evoluir diretamente pelo Git; slots assinados ficam reservados para distribuição de produção.",
      ),
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        PRODUCT_VERSION.stableRelease
          ? "Este marco é uma versão estável do produto."
          : "Canal de protótipo: v1.0 permanece reservado para o produto estável.",
      ),
    );
    view.append(versionSection);

    const deliverySection = node(documentObject, "section", "ordax-system-section");
    const deliveryHeading = node(documentObject, "div", "ordax-system-section-heading");
    const deliveryHeadingCopy = node(documentObject, "div");
    deliveryHeadingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", "Identidade da entrega"),
      node(
        documentObject,
        "h4",
        "ordax-system-section-title",
        updateSnapshot?.deliveryNumber ? deliveryLabel(updateSnapshot.deliveryNumber) : "Entrega não informada",
      ),
    );
    deliveryHeading.append(deliveryHeadingCopy);
    deliverySection.append(deliveryHeading);
    deliverySection.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        "Entrega é o número humano do que pode chegar ao notebook; não é número de PR nem versão comercial do OrdaX. O SHA identifica exatamente o build.",
      ),
    );
    if (!updateSnapshot?.deliveryNumber) {
      deliverySection.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          "Este host não informa uma identidade técnica de entrega. As versões dos componentes permanecem disponíveis separadamente.",
        ),
      );
    }
    view.append(deliverySection);

    const section = node(documentObject, "section", "ordax-system-section");
    const heading = node(documentObject, "div", "ordax-system-section-heading");
    const headingCopy = node(documentObject, "div");
    headingCopy.append(
      node(documentObject, "span", "ordax-system-section-kicker", "Componentes"),
      node(documentObject, "h4", "ordax-system-section-title", "Versões e isolamento"),
    );
    heading.append(headingCopy);
    section.append(heading);

    if (!componentSnapshot) {
      section.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          "O Component Manager não está disponível nesta composição.",
        ),
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
          ? "Estado de componentes e saúde persistido neste dispositivo."
          : "Catálogo disponível; estado de componentes permanece somente nesta sessão.",
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
        `Saúde: ${componentHealthLabel(state.currentHealth)} · falha isolada em ${manifest.failureDomain}`,
      );
      item.append(title, identity, health);

      if (independentUpdate) {
        const slots = node(
          documentObject,
          "small",
          "ordax-system-component-slots",
          `Anterior: ${state.previousVersion ? `v${state.previousVersion}` : "—"} · Pendente: ${state.pendingVersion ? `v${state.pendingVersion}` : "—"}`,
        );
        item.append(slots);
      } else {
        item.append(
          node(
            documentObject,
            "small",
            "ordax-system-component-slots",
            manifest.releaseMode === "base-ab"
              ? "Rollback pertence aos slots A/B da Base."
              : manifest.releaseMode === "git-app"
                ? "Desenvolvimento: esta versão do app chega diretamente pelo Git, sem slot de produção."
                : "Ainda acompanha a entrega conjunta; rollback individual permanece bloqueado.",
          ),
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
      node(documentObject, "span", "ordax-system-section-kicker", "Registro"),
      node(documentObject, "h4", "ordax-system-section-title", "Histórico de atualizações"),
    );
    const refresh = node(documentObject, "button", "ordax-system-action", "Atualizar histórico");
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
          historyMessage || "Lendo histórico persistente deste dispositivo…",
        ),
      );
      view.append(section);
      return;
    }

    const applications = node(documentObject, "div", "ordax-system-history");
    applications.append(node(documentObject, "h5", "ordax-system-history-title", "Aplicações neste notebook"));
    if (historySnapshot.applications.length === 0) {
      applications.append(
        node(
          documentObject,
          "p",
          "ordax-system-placeholder",
          "O registro local começa nesta geração do atualizador. Versões anteriores continuam listadas no histórico de entregas.",
        ),
      );
    } else {
      for (const entry of historySnapshot.applications.slice(0, 10)) {
        const item = node(documentObject, "article", "ordax-system-history-item");
        const result = entry.result === "applied" ? "Aplicada" : "Revertida";
        item.append(
          node(documentObject, "strong", "", `${deliveryLabel(entry.deliveryNumber)} · ${result}`),
          node(documentObject, "span", "", formatUpdateTimestamp(entry.appliedAt)),
          node(
            documentObject,
            "small",
            "",
            `SHA ${shortSha(entry.sourceSha)} · ${readableUpdateMode(entry.applyMode)} · ${entry.applyDurationSeconds}s (preparação ${entry.stageDurationSeconds}s)`,
          ),
        );
        applications.append(item);
      }
    }

    const releases = node(documentObject, "div", "ordax-system-history");
    releases.append(node(documentObject, "h5", "ordax-system-history-title", "Entregas do OrdaX"));
    for (const entry of historySnapshot.releases.slice(0, 12)) {
      const item = node(documentObject, "article", "ordax-system-history-item");
      item.append(
        node(documentObject, "strong", "", `${deliveryLabel(entry.deliveryNumber)} · ${entry.title}`),
        node(documentObject, "span", "", formatUpdateTimestamp(entry.releasedAt)),
        node(documentObject, "small", "", `SHA ${shortSha(entry.sourceSha)}`),
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
      node(documentObject, "span", "ordax-system-section-kicker", "Contrato"),
      node(documentObject, "h4", "ordax-system-section-title", "Capacidades desta execução"),
    );
    heading.append(headingCopy);
    section.append(heading);

    const list = node(documentObject, "div", "ordax-system-capabilities");
    if (hostSnapshot.capabilityIds.length === 0) {
      list.append(node(documentObject, "p", "ordax-system-placeholder", "Nenhuma capacidade adicional declarada."));
    } else {
      for (const capabilityId of hostSnapshot.capabilityIds) {
        const item = node(documentObject, "div", "ordax-system-capability");
        item.append(
          node(documentObject, "span", "ordax-system-capability-dot"),
          node(documentObject, "strong", "", CAPABILITY_LABELS[capabilityId] ?? capabilityId),
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
      node(documentObject, "span", "ordax-system-section-kicker", "Intelligence"),
      node(documentObject, "h4", "ordax-system-section-title", "Explicação local do estado"),
    );
    const action = node(
      documentObject,
      "button",
      "ordax-system-action",
      intelligencePending ? "Explicando…" : "Explicar estado",
    );
    action.type = "button";
    action.dataset.systemIntelligenceExplain = "";
    const ready = intelligenceSnapshot?.state === "ready";
    action.disabled = !ready || intelligencePending;
    action.title = ready
      ? "Usar Ordax Intelligence para explicar somente os sinais locais exibidos por Sistema"
      : "Ordax Intelligence não está pronta nesta execução";
    heading.append(headingCopy, action);
    section.append(heading);

    const stateLabel = intelligenceSnapshot === null
      ? "Não exposta neste modo"
      : intelligenceSnapshot.state === "ready"
        ? "Pronta"
        : intelligenceSnapshot.state === "busy"
          ? "Ocupada"
          : intelligenceSnapshot.state === "degraded"
            ? "Degradada"
            : "Com erro";
    const detail = intelligenceSnapshot?.modelId
      ? `${stateLabel} · ${intelligenceSnapshot.modelId}`
      : stateLabel;
    section.append(
      node(
        documentObject,
        "p",
        "ordax-system-section-copy",
        `Estado: ${detail}. Esta consulta é local, somente leitura e não executa ações no dispositivo.`,
      ),
    );

    if (intelligenceMessage) {
      const message = node(
        documentObject,
        "p",
        intelligenceAnswer ? "ordax-system-message" : "ordax-system-warning",
        intelligenceMessage,
      );
      message.setAttribute("role", "status");
      message.setAttribute("aria-live", "polite");
      section.append(message);
    }
    if (intelligenceAnswer) {
      const answer = node(documentObject, "article", "ordax-system-history-item");
      answer.dataset.state = "info";
      answer.append(
        node(documentObject, "strong", "", "Explicação da Ordax Intelligence"),
        node(documentObject, "p", "ordax-system-section-copy", intelligenceAnswer),
        node(documentObject, "small", "", "Fonte: snapshot local de Sistema · autoridade: nenhuma"),
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
        ? "A leitura atual falhou; os valores abaixo são a última leitura válida recebida pela Surface."
        : "Não foi possível obter uma leitura válida dos recursos nesta sessão.";
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
      historyMessage = "Não foi possível atualizar o histórico local.";
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
      intelligenceMessage = "Analisando somente os sinais locais exibidos por Sistema…";
      replaceView();
      void explainSystemStateWithIntelligence(intelligencePort, {
        surface: hostSnapshot,
        metrics: metricsSnapshot,
      }).then((response) => {
        if (destroyed) return;
        intelligenceAnswer = response.text;
        intelligenceMessage = "Explicação local concluída. Nenhuma ação foi executada.";
      }).catch(() => {
        if (destroyed) return;
        intelligenceMessage = "Não foi possível obter uma explicação local nesta execução.";
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
