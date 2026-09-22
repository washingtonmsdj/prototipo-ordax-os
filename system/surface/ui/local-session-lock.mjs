import {
  assertLocalSessionPort,
  validateLocalSessionSnapshot,
} from "../../contracts/local-session.mjs";

export function mountLocalSessionLock(
  root,
  localSession,
  { documentObject = root?.ownerDocument ?? globalThis.document } = {},
) {
  if (!(root instanceof Element)) {
    throw new TypeError("Local session lock requires the Surface root Element");
  }
  const port = assertLocalSessionPort(localSession);
  let snapshot = validateLocalSessionSnapshot(port.getSnapshot());
  let overlay = null;
  let pending = false;
  let message = "";
  let destroyed = false;
  let previousInert = root.inert;
  let previousAriaHidden = root.getAttribute("aria-hidden");

  const restoreRoot = () => {
    root.inert = previousInert;
    if (previousAriaHidden === null) root.removeAttribute("aria-hidden");
    else root.setAttribute("aria-hidden", previousAriaHidden);
  };

  const removeOverlay = () => {
    overlay?.remove();
    overlay = null;
    restoreRoot();
  };

  const render = () => {
    if (destroyed) return;
    if (snapshot.state !== "locked") {
      removeOverlay();
      return;
    }
    if (!overlay) {
      previousInert = root.inert;
      previousAriaHidden = root.getAttribute("aria-hidden");
      root.inert = true;
      root.setAttribute("aria-hidden", "true");
      overlay = documentObject.createElement("section");
      overlay.className = "ordax-local-session-lock";
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.setAttribute("aria-labelledby", "ordax-local-session-lock-title");
      documentObject.body.append(overlay);
    }

    overlay.replaceChildren();
    const card = documentObject.createElement("main");
    card.className = "ordax-local-session-lock-card";
    const brand = documentObject.createElement("strong");
    brand.className = "ordax-local-session-lock-brand";
    brand.textContent = "OrdaX";
    const title = documentObject.createElement("h1");
    title.id = "ordax-local-session-lock-title";
    title.textContent = "Sessão bloqueada";
    const copy = documentObject.createElement("p");
    copy.textContent =
      "Digite seu PIN ou senha local para continuar. "
      + "Este bloqueio protege a sessão em execução e não criptografa os arquivos do pendrive.";
    const form = documentObject.createElement("form");
    form.className = "ordax-local-session-lock-form";
    form.dataset.localSessionUnlockForm = "";
    const label = documentObject.createElement("label");
    label.textContent = "PIN ou senha local";
    const input = documentObject.createElement("input");
    input.type = "password";
    input.autocomplete = "current-password";
    input.minLength = 6;
    input.maxLength = 128;
    input.required = true;
    input.dataset.localSessionSecret = "";
    input.disabled = pending;
    label.append(input);
    const button = documentObject.createElement("button");
    button.type = "submit";
    button.textContent = pending ? "Verificando…" : "Desbloquear";
    button.disabled = pending;
    form.append(label, button);
    const status = documentObject.createElement("p");
    status.className = "ordax-local-session-lock-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.textContent = message;
    card.append(brand, title, copy, form, status);
    overlay.append(card);
    queueMicrotask(() => input.focus());
  };

  const onSubmit = (event) => {
    const form = event.target.closest?.("[data-local-session-unlock-form]");
    if (!form || !overlay?.contains(form) || pending) return;
    event.preventDefault();
    const input = form.querySelector("[data-local-session-secret]");
    if (!(input instanceof HTMLInputElement)) return;
    let secret = input.value;
    input.value = "";
    if (secret.length < 6) {
      secret = "";
      message = "Digite pelo menos 6 caracteres.";
      render();
      return;
    }
    pending = true;
    message = "";
    render();
    const operationSecret = secret;
    secret = "";
    void port.unlock(operationSecret).catch((error) => {
      if (destroyed) return;
      message = error?.status === 429
        ? "Muitas tentativas. Aguarde alguns segundos e tente novamente."
        : "PIN ou senha local incorreto.";
    }).finally(() => {
      if (destroyed) return;
      pending = false;
      render();
    });
  };

  documentObject.addEventListener("submit", onSubmit);
  const unsubscribe = port.subscribe((next) => {
    snapshot = validateLocalSessionSnapshot(next);
    if (snapshot.state !== "locked") message = "";
    render();
  });
  render();

  return Object.freeze({
    destroy() {
      if (destroyed) return;
      destroyed = true;
      unsubscribe();
      documentObject.removeEventListener("submit", onSubmit);
      removeOverlay();
    },
  });
}
