import { assertLocalizationPort } from "../../contracts/localization.mjs";

const PRESENTATIONS = Object.freeze({
  "system-updates.base-refresh-required": Object.freeze({
    sourceId: "system-updates",
    titleMessageId: "notifications.update.basePending.title",
    messageMessageId: "notifications.update.basePending.message",
  }),
  "system-updates.applied": Object.freeze({
    sourceId: "system-updates",
    titleMessageId: "notifications.update.applied.title",
    messageMessageId: "notifications.update.applied.message",
  }),
  "system-updates.network-error": Object.freeze({
    sourceId: "system-updates",
    titleMessageId: "notifications.update.networkError.title",
    messageMessageId: "notifications.update.networkError.message",
  }),
  "system-updates.remote-error": Object.freeze({
    sourceId: "system-updates",
    titleMessageId: "notifications.update.remoteError.title",
    messageMessageId: "notifications.update.remoteError.message",
  }),
  "system-updates.pull-error": Object.freeze({
    sourceId: "system-updates",
    titleMessageId: "notifications.update.pullError.title",
    messageMessageId: "notifications.update.pullError.message",
  }),
  "system-updates.rejected": Object.freeze({
    sourceId: "system-updates",
    titleMessageId: "notifications.update.rejected.title",
    messageMessageId: "notifications.update.rejected.message",
  }),
  "system-updates.rolled-back": Object.freeze({
    sourceId: "system-updates",
    titleMessageId: "notifications.update.rolledBack.title",
    messageMessageId: "notifications.update.rolledBack.message",
  }),
});

export function notificationPresentationCopy(entry, localization) {
  const localizer = assertLocalizationPort(localization);
  const fallback = Object.freeze({
    title: entry.title,
    message: entry.message,
  });
  if (!entry.presentation) return fallback;
  const descriptor = PRESENTATIONS[entry.presentation.id] ?? null;
  if (!descriptor || descriptor.sourceId !== entry.sourceId) return fallback;
  return Object.freeze({
    title: localizer.translate(
      descriptor.titleMessageId,
      entry.presentation.values,
    ),
    message: localizer.translate(
      descriptor.messageMessageId,
      entry.presentation.values,
    ),
  });
}
