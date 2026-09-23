import { assertAppActivationPort } from "../../contracts/app-activation.mjs";
import { assertSurfaceRenderLifecycle } from "../../contracts/surface-render-lifecycle.mjs";
import {
  updateIsAlerting,
  updateSummaryMessageId,
} from "../../services/update/presentation.mjs";

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

  const button = node(documentObject, "button", "ordax-status-action");
  button.type = "button";
  button.dataset.updateOpenSystem = "";
  slot.append(button);

  let snapshot = updatePort.getSnapshot();

  const render = () => {
    const alerting = updateIsAlerting(snapshot);
    const label = t("system.updateTray.label");
    button.textContent = alerting ? `${label} •` : label;
    button.dataset.alerting = String(alerting);
    button.setAttribute("aria-label", t("system.updateTray.aria"));
    button.title = snapshot?.bootRefreshRequired
      ? t("system.updateTray.summary", {
          summary: t(updateSummaryMessageId(snapshot)),
        })
      : alerting
        ? t("system.updateTray.attention")
        : t("system.updateTray.open");
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
  const unsubscribeLocalization = localization.subscribe(render);
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
