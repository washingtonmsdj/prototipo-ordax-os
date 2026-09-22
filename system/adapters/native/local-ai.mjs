import {
  LOCAL_AI_PORT_SCHEMA,
  LOCAL_AI_RESPONSE_SCHEMA,
  LOCAL_AI_STATUS_SCHEMA,
  validateLocalAiMessages,
  validateLocalAiResponse,
  validateLocalAiStatus,
} from "../../contracts/local-ai.mjs";

const STATUS_PATH = "/__ordax/native/local-ai/status";
const CHAT_PATH = "/__ordax/native/local-ai/chat";

async function readJson(response) {
  if (!response.ok) {
    throw new Error(`Local AI request failed with HTTP ${response.status}`);
  }
  const value = await response.json();
  return value;
}

export async function createNativeLocalAi(windowRef = globalThis.window) {
  if (!windowRef?.fetch) throw new TypeError("Native Local AI requires fetch()");
  const statusResponse = await windowRef.fetch(STATUS_PATH, {
    method: "GET",
    cache: "no-store",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const status = validateLocalAiStatus(await readJson(statusResponse));
  if (status.state !== "ready") {
    throw new Error("Local AI backend is unavailable");
  }

  return Object.freeze({
    schema: LOCAL_AI_PORT_SCHEMA,
    getSnapshot() {
      return status;
    },
    async complete(messages) {
      const validated = validateLocalAiMessages(messages);
      const response = await windowRef.fetch(CHAT_PATH, {
        method: "POST",
        cache: "no-store",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ messages: validated }),
      });
      const value = await readJson(response);
      if (value?.schema !== LOCAL_AI_RESPONSE_SCHEMA) {
        throw new TypeError("Native Local AI returned an incompatible response");
      }
      return validateLocalAiResponse(value);
    },
  });
}

export function unavailableLocalAiStatus() {
  return Object.freeze({
    schema: LOCAL_AI_STATUS_SCHEMA,
    state: "unavailable",
    backend: null,
    model: null,
  });
}
