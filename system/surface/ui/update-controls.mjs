import { assertAppActivationPort } from "../../contracts/app-activation.mjs";
import { assertSurfaceRenderLifecycle } from "../../contracts/surface-render-lifecycle.mjs";
import { updateIsAlerting } from "../../services/update/presentation.mjs";

const BASE_SUMMARY_MESSAGE_IDS = Object.freeze({
  "candidate-requested": "system.overview.update.summary.candidateRequested",
  "candidate-fetching": "system.overview.update.summary.candidateFetching",
  "candidate-ready": "system.overview.update.summary.candidateReady",
  staged: "system.overview.update.summary.staged",
  "activation-ready": "system.overview.update.summary.activationReady",
});

function baseSummaryMessageId(snapshot) {
  return BASE_SUMMARY_MESSAGE_IDS[snapshot?.baseUpdatePhase]
    ?? "system.overview.update.summary.pending";
}

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

  const button = node(
    documentObject,
    "button",
    "ordax-status-action",
    t("system.updates.accelerator.label"),
  );
  button.type = "button";
  button.dataset.updateOpenSystem = "";
  button.setAttribute("aria-label", t("system.updates.accelerator.aria"));
  slot.append(button);

  let snapshot = updatePort.getSnapshot();

  const render = () => {
    const alerting = updateIsAlerting(snapshot);
    button.textContent = alerting
      ? t("system.updates.accelerator.labelAlerting")
      : t("system.updates.accelerator.label");
    button.setAttribute("aria-label", t("system.updates.accelerator.aria"));
    button.dataset.alerting = String(alerting);
    button.title = snapshot?.bootRefreshRequired
      ? t("system.updates.accelerator.titleBoot", {
          summary: t(baseSummaryMessageId(snapshot)),
        })
      : alerting
        ? t("system.updates.accelerator.titleAlerting")
        : t("system.updates.accelerator.title");
  };

  const onClick = (event) => {
    const target = event.target.closest("[data-update-open-system]");
    if (!target || !root.contains(target)) return;
    activationPort.publish({ appId: "system", target: "updates" });
  };

  root.addEventListener("click", onClick);
  const unsubscribeUpdate = updatePort.subscribe((nextSnapshot) => {
    snapshot = nextSnapshot;
    render();
  });
  const unsubscribeLocalization = localization.subscribe(() => render());
  render();

  return Object.freeze({
    destroy() {
      unsubscribeLocalization?.();
      unsubscribeUpdate?.();
      root.removeEventListener("click", onClick);
      button.remove();
    },
  });
}
