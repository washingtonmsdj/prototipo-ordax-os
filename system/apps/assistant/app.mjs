import { defineFirstPartyApp } from "../app-contract.mjs";
import { assistantComponent } from "./component.mjs";

export const assistantApp = defineFirstPartyApp({
  id: "assistant",
  title: "Assistente",
  description: "IA local e privada, executada no próprio dispositivo.",
  monogram: "IA",
  singleton: true,
  component: assistantComponent,
  requiredCapabilities: ["ai.local"],
  panels: [
    {
      kind: "extension",
      extensionId: "assistant-workspace",
      label: "Assistente",
      title: "Assistente local",
      body: "A IA local não está disponível nesta composição.",
    },
  ],
});
