export const DEFAULT_LOCALE = "pt-BR";
export const SUPPORTED_CATALOG_LOCALES = Object.freeze(["pt-BR", "en-US", "es-419"]);

export const LOCALE_METADATA = Object.freeze({
  "pt-BR": Object.freeze({ label: "Português (Brasil)", status: "complete" }),
  "en-US": Object.freeze({ label: "English (United States)", status: "preview" }),
  "es-419": Object.freeze({ label: "Español (Latinoamérica)", status: "preview" }),
});

const MESSAGES = Object.freeze({
  "pt-BR": Object.freeze({
    "assistant.title": "Assistente",
    "assistant.description": "IA local e privada, executada no próprio dispositivo.",
    "assistant.heading": "Assistente local",
    "assistant.placeholder": "Pergunte algo…",
    "assistant.send": "Enviar",
    "assistant.unavailable": "A IA local não está instalada neste pendrive.",
    "assistant.thinking": "Pensando localmente…",
    "assistant.error": "Não foi possível obter uma resposta da IA local.",
    "assistant.localBadge": "Executando neste dispositivo",
    "creator.localAi": "Incluir IA local",
    "creator.localAiHint": "Adiciona o motor e um modelo local compatível. Pode aumentar bastante o espaço usado no pendrive.",
    "locale.preview": "prévia",
  }),
  "en-US": Object.freeze({
    "assistant.title": "Assistant",
    "assistant.description": "Private local AI running on this device.",
    "assistant.heading": "Local assistant",
    "assistant.placeholder": "Ask something…",
    "assistant.send": "Send",
    "assistant.unavailable": "Local AI is not installed on this USB drive.",
    "assistant.thinking": "Thinking locally…",
    "assistant.error": "The local AI could not produce a response.",
    "assistant.localBadge": "Running on this device",
    "creator.localAi": "Include local AI",
    "creator.localAiHint": "Adds a local engine and compatible model. This can significantly increase USB storage usage.",
    "locale.preview": "preview",
  }),
  "es-419": Object.freeze({
    "assistant.title": "Asistente",
    "assistant.description": "IA local y privada que se ejecuta en este dispositivo.",
    "assistant.heading": "Asistente local",
    "assistant.placeholder": "Pregunta algo…",
    "assistant.send": "Enviar",
    "assistant.unavailable": "La IA local no está instalada en esta memoria USB.",
    "assistant.thinking": "Pensando localmente…",
    "assistant.error": "La IA local no pudo generar una respuesta.",
    "assistant.localBadge": "Ejecutándose en este dispositivo",
    "creator.localAi": "Incluir IA local",
    "creator.localAiHint": "Agrega un motor local y un modelo compatible. Puede aumentar considerablemente el espacio usado en la memoria USB.",
    "locale.preview": "vista previa",
  }),
});

function normalizedLocale(locale) {
  return SUPPORTED_CATALOG_LOCALES.includes(locale) ? locale : DEFAULT_LOCALE;
}

export function localeMetadata(locale) {
  return LOCALE_METADATA[normalizedLocale(locale)];
}

export function translate(locale, key, variables = Object.freeze({})) {
  const selected = normalizedLocale(locale);
  let value = MESSAGES[selected]?.[key] ?? MESSAGES[DEFAULT_LOCALE]?.[key];
  if (typeof value !== "string") {
    throw new TypeError(`Unknown translation key: ${String(key)}`);
  }
  for (const [name, replacement] of Object.entries(variables)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

export function hasTranslation(locale, key) {
  return typeof MESSAGES[normalizedLocale(locale)]?.[key] === "string";
}
