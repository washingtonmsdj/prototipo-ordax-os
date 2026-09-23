import {
  SURFACE_SOURCE_LOCALE,
  translateSurfaceMessage,
} from "../../services/i18n/surface.mjs";

const BOOT_SCREEN_ID = "ordax-boot-screen";
const STATUS_SELECTOR = "[data-ordax-boot-status]";

export function createSurfaceBootScreen(documentObject = globalThis.document) {
  if (!documentObject || typeof documentObject.querySelector !== "function") {
    throw new TypeError("Surface boot screen requires a document");
  }
  const element = documentObject.querySelector(`#${BOOT_SCREEN_ID}`);
  if (!(element instanceof Element)) {
    throw new TypeError("Surface boot screen element is missing");
  }
  const status = element.querySelector(STATUS_SELECTOR);
  if (!(status instanceof Element)) {
    throw new TypeError("Surface boot screen status element is missing");
  }

  let finished = false;
  let locale = SURFACE_SOURCE_LOCALE;

  const translated = (messageId) => translateSurfaceMessage(locale, messageId);

  return Object.freeze({
    setLocale(nextLocale) {
      if (finished || typeof nextLocale !== "string" || !nextLocale) return false;
      locale = nextLocale;
      documentObject.documentElement?.setAttribute?.("lang", nextLocale);
      return true;
    },
    setStage(messageId) {
      if (finished) return false;
      status.textContent = translated(messageId);
      element.dataset.state = "loading";
      return true;
    },
    ready() {
      if (finished) return false;
      finished = true;
      element.dataset.state = "ready";
      element.setAttribute("aria-hidden", "true");
      element.hidden = true;
      return true;
    },
    fail(messageId = "boot.failed") {
      if (finished) return false;
      status.textContent = translated(messageId);
      element.dataset.state = "error";
      element.removeAttribute("aria-hidden");
      return true;
    },
    isFinished() {
      return finished;
    },
  });
}
