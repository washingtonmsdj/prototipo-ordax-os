import {
  AI_RUNTIME_SCHEMA,
  assertAiProvider,
  validateAiRequest,
  validateAiRuntimeSnapshot,
} from "../../contracts/ai-runtime.mjs";

export function createUnavailableAiRuntime(message = "IA local não instalada.") {
  let snapshot = validateAiRuntimeSnapshot({
    schema: AI_RUNTIME_SCHEMA,
    state: "unavailable",
    providerId: null,
    modelId: null,
    localOnly: true,
    message,
  });
  return Object.freeze({
    schema: AI_RUNTIME_SCHEMA,
    getSnapshot: () => snapshot,
    subscribe(listener) {
      if (typeof listener !== "function") throw new TypeError("AI listener must be a function");
      listener(snapshot);
      return () => {};
    },
    async complete() {
      throw new Error("Local AI runtime is unavailable");
    },
  });
}

export function createAiRuntime(provider) {
  const adapter = assertAiProvider(provider);
  const listeners = new Set();
  let busy = false;
  let snapshot = validateAiRuntimeSnapshot({
    schema: AI_RUNTIME_SCHEMA,
    state: "ready",
    providerId: adapter.id,
    modelId: adapter.modelId,
    localOnly: true,
    message: null,
  });

  const publish = (next) => {
    snapshot = validateAiRuntimeSnapshot(next);
    for (const listener of listeners) listener(snapshot);
  };

  return Object.freeze({
    schema: AI_RUNTIME_SCHEMA,
    getSnapshot: () => snapshot,
    subscribe(listener) {
      if (typeof listener !== "function") throw new TypeError("AI listener must be a function");
      listeners.add(listener);
      listener(snapshot);
      return () => listeners.delete(listener);
    },
    async complete(request) {
      if (busy) throw new Error("Local AI runtime is busy");
      const validated = validateAiRequest(request);
      busy = true;
      publish({
        schema: AI_RUNTIME_SCHEMA,
        state: "loading",
        providerId: adapter.id,
        modelId: adapter.modelId,
        localOnly: true,
        message: "Gerando resposta localmente…",
      });
      try {
        const response = await adapter.complete(validated);
        if (typeof response !== "string" || !response.trim() || response.length > 131072) {
          throw new TypeError("AI provider returned an invalid response");
        }
        publish({
          schema: AI_RUNTIME_SCHEMA,
          state: "ready",
          providerId: adapter.id,
          modelId: adapter.modelId,
          localOnly: true,
          message: null,
        });
        return response;
      } catch (error) {
        publish({
          schema: AI_RUNTIME_SCHEMA,
          state: "error",
          providerId: adapter.id,
          modelId: adapter.modelId,
          localOnly: true,
          message: "A IA local falhou nesta solicitação.",
        });
        throw error;
      } finally {
        busy = false;
      }
    },
  });
}
