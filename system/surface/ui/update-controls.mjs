import { assertAppActivationPort } from "../../contracts/app-activation.mjs";
import { assertSurfaceRenderLifecycle } from "../../contracts/surface-render-lifecycle.mjs";
import { updateIsAlerting } from "../../services/update/presentation.mjs";

function node(documentObject, tag, className, text) {
  const element = documentObject.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

export function mountUpdateControls(root, updatePort, appActivation, surfaceLifecycle) {
  if (!(root instanceof Element)) {
    throw new TypeError("Update controls root must be a DOM Element");
  }
  if (!updatePort || typeof updatePort.subscribe !== "function" || typeof updatePort.getSnapshot !== "function") {
    throw new TypeError("Update controls require a native update watcher port");
  }
  const activationPort = assertAppActivationPort(appActivation);
  const lifecycle = assertSurfaceRenderLifecycle(surfaceLifecycle);
  const localization = lifecycle.localization;
  const t = localization.translate;

  const documentObject = root.ownerDocument;
  const slot = root.querySelector("[data-update-slot]");
  if (!slot) {
    throw new Error("Surface update controls require the shared shell update slot");
  }

  const button = node(documentObject, "button", "ordax-status-action", t("system.tray.updates"));
  button.type = "button";
  button.dataset.updateOpenSystem = "";
  button.setAttribute("aria-label", t("system.tray.updates.openAria"));
  slot.append(button);

  let snapshot = updatePort.getSnapshot();

  const summaryMessageId = () => {
    if (snapshot?.bootRefreshRequired) {
      const basePhase = {
        "candidate-requested": "system.overview.update.summary.candidateRequested",
        "candidate-fetching": "system.overview.update.summary.candidateFetching",
        "candidate-ready": "system.overview.update.summary.candidateReady",
        staged: "system.overview.update.summary.staged",
        "activation-ready": "system.overview.update.summary.activationReady",
      }[snapshot?.baseUpdatePhase] ?? "system.overview.update.summary.pending";
      return basePhase;
    }
    return {
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
    }[snapshot?.status] ?? "system.overview.update.status.unavailable";
  };

  const render = () => {
    const alerting = updateIsAlerting(snapshot);
    button.textContent = t(alerting ? "system.tray.updates.alert" : "system.tray.updates");
    button.setAttribute("aria-label", t("system.tray.updates.openAria"));
    button.dataset.alerting = String(alerting);
    button.title = snapshot?.bootRefreshRequired
      ? t("system.tray.updates.summary", { summary: t(summaryMessageId()) })
      : alerting
        ? t("system.tray.updates.attention")
        : t("system.tray.updates.open");
  };

  const onClick = (event) => {
    const target = event.target.closest("[data-update-open-system]");
    if (!target || !root.contains(target)) return;
    activationPort.publish({ appId: "system", target: "updates" });
  };

  root.addEventListener("click", onClick);
  const unsubscribe = updatePort.subscribe((nextSnapshot) => {
    snapshot = nextSnapshot;
    render();
  });
  const unsubscribeLocalization = localization.subscribe(() => render());
  render();

  return Object.freeze({
    destroy() {
      unsubscribeLocalization();
      unsubscribe?.();
      root.removeEventListener("click", onClick);
      button.remove();
    },
  });
}
