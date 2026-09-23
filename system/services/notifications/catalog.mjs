import { validateNotificationSourceId } from "../../contracts/notifications.mjs";

export const SYSTEM_UPDATES_NOTIFICATION_SOURCE_ID = "system-updates";

const SOURCES = Object.freeze([
  Object.freeze({
    id: SYSTEM_UPDATES_NOTIFICATION_SOURCE_ID,
    appId: "system",
    label: "Sistema",
    topic: "Atualizações",
    description: "Avisos de atualização aplicada, falha, rollback e atualização de base pendente.",
  }),
]);

const SOURCE_MESSAGE_IDS = Object.freeze({
  [SYSTEM_UPDATES_NOTIFICATION_SOURCE_ID]: Object.freeze({
    label: "notifications.source.systemUpdates.label",
    topic: "notifications.source.systemUpdates.topic",
  }),
});

const LEGACY_SOURCE_LABELS = Object.freeze({
  files: "Arquivos",
  settings: "Ajustes",
  account: "Conta",
  system: "Sistema",
  internet: "Internet",
});

const LEGACY_SOURCE_MESSAGE_IDS = Object.freeze({
  files: "app.files.title",
  settings: "app.settings.title",
  account: "app.account.title",
  system: "app.system.title",
  internet: "app.internet.title",
});

for (const source of SOURCES) validateNotificationSourceId(source.id);

export function listNotificationSources() {
  return SOURCES;
}

export function notificationSourceLabel(sourceId, translate = null) {
  const source = SOURCES.find((candidate) => candidate.id === sourceId);
  const messageIds = SOURCE_MESSAGE_IDS[sourceId] ?? null;
  if (source && messageIds && typeof translate === "function") {
    return `${translate(messageIds.label)} · ${translate(messageIds.topic)}`;
  }
  if (source) return `${source.label} · ${source.topic}`;
  const legacyMessageId = LEGACY_SOURCE_MESSAGE_IDS[sourceId] ?? null;
  if (legacyMessageId && typeof translate === "function") {
    return translate(legacyMessageId);
  }
  return LEGACY_SOURCE_LABELS[sourceId] ?? sourceId;
}
