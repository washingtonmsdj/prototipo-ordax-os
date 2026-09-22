import { COMPONENT_RUNTIME_SCHEMA } from "../../contracts/component-runtime.mjs";
import { ASSISTANT_VERSION } from "./version.mjs";
import { mountAssistantWorkspaceControls } from "./ui/workspace-controls.mjs";

const STYLESHEET_URL = new URL("./assistant.css", import.meta.url).href;
const STYLE_SELECTOR = 'link[data-ordax-component-style="assistant"]';

async function mountStyles(root) {
  const documentObject = root?.ownerDocument;
  if (!documentObject?.head) throw new TypeError("Assistant runtime requires a document head");
  const existing = documentObject.querySelector(STYLE_SELECTOR);
  if (existing) return () => {};
  const link = documentObject.createElement("link");
  link.rel = "stylesheet";
  link.href = STYLESHEET_URL;
  link.dataset.ordaxComponentStyle = "assistant";
  const loaded = new Promise((resolve, reject) => {
    link.addEventListener("load", resolve, { once: true });
    link.addEventListener("error", () => reject(new Error("Assistant stylesheet failed to load")), { once: true });
  });
  documentObject.head.append(link);
  try {
    await loaded;
  } catch (error) {
    link.remove();
    throw error;
  }
  return () => link.remove();
}

export const componentRuntime = Object.freeze({
  schema: COMPONENT_RUNTIME_SCHEMA,
  componentId: "assistant",
  version: ASSISTANT_VERSION,
  async mount({ root, localAi = null, surfaceLifecycle } = {}) {
    const releaseStyles = await mountStyles(root);
    if (localAi === null) {
      return Object.freeze({ destroy() { releaseStyles(); } });
    }
    let controls = null;
    try {
      controls = mountAssistantWorkspaceControls(root, localAi, surfaceLifecycle);
      return Object.freeze({
        destroy() {
          controls?.destroy();
          releaseStyles();
        },
      });
    } catch (error) {
      releaseStyles();
      throw error;
    }
  },
});
