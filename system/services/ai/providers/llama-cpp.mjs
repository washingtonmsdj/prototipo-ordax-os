import { validateAiRequest } from "../../../contracts/ai-runtime.mjs";

const LOOPBACK_ORIGIN = "http://127.0.0.1";

export function createLlamaCppProvider({
  modelId = "qwen3.5-0.8b-q4_0",
  invoke,
} = {}) {
  if (typeof invoke !== "function") {
    throw new TypeError("llama.cpp provider requires a host-owned invoke function");
  }

  return Object.freeze({
    id: "llama.cpp",
    modelId,
    localOnly: true,
    async complete(request) {
      const { prompt, system } = validateAiRequest(request);
      const result = await invoke({
        origin: LOOPBACK_ORIGIN,
        method: "POST",
        path: "/v1/chat/completions",
        body: {
          model: modelId,
          stream: false,
          messages: [
            ...(system ? [{ role: "system", content: system }] : []),
            { role: "user", content: prompt },
          ],
        },
      });
      const text = result?.choices?.[0]?.message?.content;
      if (typeof text !== "string" || !text.trim()) {
        throw new TypeError("llama.cpp response does not contain assistant text");
      }
      return text;
    },
  });
}
