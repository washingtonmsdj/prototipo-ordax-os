import { defineFirstPartyApp } from "../app-contract.mjs";
import { assistantComponent } from "./component.mjs";

export const assistantApp = defineFirstPartyApp({
  id: "assistant",
  title: "Assistente",
  description: "IA local opcional para conversar, resumir conteúdo escolhido e explicar diagnósticos sanitizados.",
  monogram: "IA",
  singleton: true,
  component: assistantComponent,
  requiredCapabilities: [],
  optionalCapabilities: ["ai.local"],
  panels: [
    {
      kind: "static",
      label: "IA local",
      title: "Assistente OrdaX",
      body: "O assistente usa um runtime local substituível. Quando o pacote de IA não estiver instalado, o restante do OrdaX continua funcionando normalmente.",
    },
  ],
});
