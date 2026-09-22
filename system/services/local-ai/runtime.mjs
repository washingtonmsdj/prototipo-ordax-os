import {
  LOCAL_AI_PORT_SCHEMA,
  validateLocalAiRequest,
  validateLocalAiSnapshot,
} from "../../contracts/local-ai.mjs";

const DEFAULT_ENDPOINT = "http://127.0.0.1:17865";

function normalizeEndpoint(value) {
  const url = new URL(value);
  if (url.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(url.hostname)) {
    throw new TypeError("Local AI endpoint must be loopback HTTP");
  }
  url.pathname = "";
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/$/, "");
}

export function createLocalAiRuntime({
  fetchImpl = globalThis.fetch,
  endpoint = DEFAULT_ENDPOINT,
  engineId = "llama.cpp",
  modelId = null,
} = {}) {
  if (typeof fetchImpl !== "function") {
    throw new TypeError("Local AI runtime requires fetch");
  }
  const base = normalizeEndpoint(endpoint);
  let activeModelId = modelId;
  let snapshot = validateLocalAiSnapshot({
    schema: LOCAL_AI_PORT_SCHEMA,
    state: activeModelId ? "stopped" : "unavailable",
    engineId: activeModelId ? engineId : null,
    modelId: activeModelId,
    offline: true,
    migratable: true,
  });
  const listeners = new Set();

  const publish = (next) => {
    snapshot = validateLocalAiSnapshot(next);
    for (const listener of listeners) listener(snapshot);
  };

  return Object.freeze({
    schema: LOCAL_AI_PORT_SCHEMA,
    getSnapshot() {
      return snapshot;
    },
    subscribe(listener) {
      if (typeof listener !== "function") throw new TypeError("Local AI listener must be a function");
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    async probe() {
      try {
        if (!activeModelId) {
          const modelsResponse = await fetchImpl(base + "/v1/models", {
            method: "GET",
            cache: "no-store",
            credentials: "omit",
          });
          if (!modelsResponse.ok) {
            publish({
              schema: LOCAL_AI_PORT_SCHEMA,
              state: "unavailable",
              engineId: null,
              modelId: null,
              offline: true,
              migratable: true,
            });
            return snapshot;
          }
          const payload = await modelsResponse.json();
          const discovered = payload?.data?.[0]?.id;
          if (typeof discovered !== "string" || !discovered.trim() || discovered.length > 160) {
            publish({
              schema: LOCAL_AI_PORT_SCHEMA,
              state: "unavailable",
              engineId: null,
              modelId: null,
              offline: true,
              migratable: true,
            });
            return snapshot;
          }
          activeModelId = discovered.trim();
        }

        const response = await fetchImpl(base + "/health", {
          method: "GET",
          cache: "no-store",
          credentials: "omit",
        });
        publish({
          schema: LOCAL_AI_PORT_SCHEMA,
          state: response.ok ? "ready" : "error",
          engineId,
          modelId: activeModelId,
          offline: true,
          migratable: true,
        });
      } catch {
        publish({
          schema: LOCAL_AI_PORT_SCHEMA,
          state: activeModelId ? "stopped" : "unavailable",
          engineId: activeModelId ? engineId : null,
          modelId: activeModelId,
          offline: true,
          migratable: true,
        });
      }
      return snapshot;
    },
    async generate(request) {
      const input = validateLocalAiRequest(request);
      if (snapshot.state !== "ready") {
        throw new Error("Local AI is not ready");
      }
      publish({ ...snapshot, state: "busy" });
      try {
        const response = await fetchImpl(base + "/v1/chat/completions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          cache: "no-store",
          credentials: "omit",
          body: JSON.stringify({
            model: activeModelId,
            messages: [{ role: "user", content: input.prompt }],
            max_tokens: input.maxTokens,
            stream: false,
          }),
        });
        if (!response.ok) throw new Error(`Local AI inference failed: HTTP ${response.status}`);
        const payload = await response.json();
        const text = payload?.choices?.[0]?.message?.content;
        if (typeof text !== "string" || !text.trim()) {
          throw new Error("Local AI returned an invalid completion");
        }
        publish({ ...snapshot, state: "ready" });
        return Object.freeze({ text: text.trim(), engineId, modelId: activeModelId });
      } catch (error) {
        publish({ ...snapshot, state: "error" });
        throw error;
      }
    },
    dispose() {
      listeners.clear();
    },
  });
}
