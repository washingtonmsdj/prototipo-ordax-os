import { assertLocalAiPort } from "../../../contracts/local-ai.mjs";
import { assertSurfaceRenderLifecycle } from "../../../contracts/surface-render-lifecycle.mjs";

const WINDOW_SELECTOR = '[data-window-id="assistant"]';
const EXTENSION_SELECTOR = '[data-app-extension="assistant-workspace"]';

function element(documentObject, tag, className, text = "") {
  const node = documentObject.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

export function mountAssistantWorkspaceControls(root, localAi, surfaceLifecycle) {
  const port = assertLocalAiPort(localAi);
  const lifecycle = assertSurfaceRenderLifecycle(surfaceLifecycle);
  let destroyed = false;
  let pending = false;
  const transcript = [];

  const render = () => {
    if (destroyed) return;
    const slot = root.querySelector(`${WINDOW_SELECTOR} ${EXTENSION_SELECTOR}`);
    if (!slot || slot.dataset.ordaxAssistantMounted === "true") return;

    slot.replaceChildren();
    slot.dataset.ordaxAssistantMounted = "true";
    const documentObject = slot.ownerDocument;
    const status = port.getSnapshot();

    const header = element(documentObject, "div", "ordax-assistant-header");
    header.append(
      element(documentObject, "strong", "", "Assistente local"),
      element(documentObject, "span", "ordax-assistant-badge", `${status.backend} · ${status.model}`),
    );
    const messages = element(documentObject, "div", "ordax-assistant-messages");
    messages.dataset.assistantMessages = "";

    const form = element(documentObject, "form", "ordax-assistant-form");
    const input = element(documentObject, "textarea", "ordax-assistant-input");
    input.placeholder = "Pergunte algo…";
    input.rows = 3;
    input.maxLength = 16384;
    const button = element(documentObject, "button", "ordax-assistant-send", "Enviar");
    button.type = "submit";
    form.append(input, button);
    slot.append(header, messages, form);

    const appendMessage = (role, text) => {
      const row = element(documentObject, "article", "ordax-assistant-message");
      row.dataset.role = role;
      row.append(element(documentObject, "span", "ordax-assistant-role", role === "user" ? "Você" : "Assistente"));
      row.append(element(documentObject, "p", "", text));
      messages.append(row);
      messages.scrollTop = messages.scrollHeight;
    };

    for (const entry of transcript) appendMessage(entry.role, entry.content);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const prompt = input.value.trim();
      if (!prompt || pending) return;
      pending = true;
      input.value = "";
      button.disabled = true;
      transcript.push({ role: "user", content: prompt });
      appendMessage("user", prompt);
      const pendingRow = element(documentObject, "p", "ordax-assistant-pending", "Pensando localmente…");
      messages.append(pendingRow);
      try {
        const response = await port.complete(transcript);
        transcript.push({ role: "assistant", content: response.text });
        pendingRow.remove();
        appendMessage("assistant", response.text);
      } catch (error) {
        pendingRow.textContent = "Não foi possível obter uma resposta da IA local.";
        console.warn("OrdaX local AI completion failed", error);
      } finally {
        pending = false;
        button.disabled = false;
        input.focus();
      }
    });
  };

  const unsubscribe = lifecycle.subscribeRender(render);
  render();
  return Object.freeze({
    destroy() {
      if (destroyed) return;
      destroyed = true;
      unsubscribe();
    },
  });
}
