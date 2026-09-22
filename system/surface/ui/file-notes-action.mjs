import {
  assertNotesFileImporter,
  validateNotesFileImportResult,
} from "../../contracts/notes-file-importer.mjs";
import { validateFileSpacePath } from "../../contracts/file-space.mjs";

const FAILURE_MESSAGE_IDS = Object.freeze({
  "source-reference-too-long": "files.notes.failure.sourceReferenceTooLong",
  "source-read-failed": "files.notes.failure.sourceReadFailed",
  "source-mismatch": "files.notes.failure.sourceMismatch",
  "source-too-large": "files.notes.failure.sourceTooLarge",
  "notes-project-unavailable": "files.notes.failure.projectUnavailable",
  "notes-create-failed": "files.notes.createFailed",
  "import-in-progress": "files.notes.failure.importInProgress",
});

function assertTranslate(translate) {
  if (typeof translate !== "function") {
    throw new TypeError("Files to Notes action requires a localization translate function");
  }
  return translate;
}

function validateFileIdentity(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Files to Notes action requires a file identity");
  }
  const path = validateFileSpacePath(value.path);
  if (path === "/") throw new TypeError("Files to Notes action requires a file path");
  if (
    typeof value.name !== "string"
    || value.name.length === 0
    || value.name.length > 512
    || /[\u0000-\u001f\u007f]/.test(value.name)
  ) {
    throw new TypeError("Files to Notes action file name is invalid");
  }
  return Object.freeze({ path, name: value.name });
}

export function createFileNotesActionPresentation({
  importerAvailable,
  busy,
  selected = null,
  translate,
}) {
  if (typeof importerAvailable !== "boolean" || typeof busy !== "boolean") {
    throw new TypeError("Files to Notes action availability/busy flags must be boolean");
  }
  if (!importerAvailable || selected === null || selected.kind !== "file") {
    return Object.freeze({ visible: false, label: "", disabled: true, title: "" });
  }
  validateFileIdentity(selected);
  const t = assertTranslate(translate);
  return Object.freeze({
    visible: true,
    label: busy ? t("files.notes.action.creating") : t("files.notes.action.create"),
    disabled: busy,
    title: t("files.notes.action.title"),
  });
}

export function messageForNotesFileImport(resultValue, fileName, translate) {
  const result = validateNotesFileImportResult(resultValue);
  const t = assertTranslate(translate);
  const name =
    typeof fileName === "string" && fileName.length > 0
      ? fileName
      : t("files.notes.defaultFileName");
  if (result.status === "failed") {
    return Object.freeze({
      kind: "warning",
      text: t(FAILURE_MESSAGE_IDS[result.code] ?? "files.notes.failure.generic"),
      openNotes: false,
    });
  }

  if (result.persistence === "device" && result.persistenceOk) {
    return Object.freeze({
      kind: "success",
      text: t("files.notes.createdDevice", { name }),
      openNotes: true,
    });
  }
  if (result.persistence === "device") {
    return Object.freeze({
      kind: "warning",
      text: t("files.notes.createdDegraded", { name }),
      openNotes: true,
    });
  }
  return Object.freeze({
    kind: "neutral",
    text: t("files.notes.createdSession", { name }),
    openNotes: true,
  });
}

export async function importSelectedFileToNotes(importerValue, selectedValue, translate) {
  const importer = assertNotesFileImporter(importerValue);
  const selected = validateFileIdentity(selectedValue);
  let result;
  try {
    result = validateNotesFileImportResult(await importer.importTextFile(selected.path));
  } catch {
    result = Object.freeze({ status: "failed", code: "notes-create-failed" });
  }
  return Object.freeze({
    result,
    presentation: messageForNotesFileImport(result, selected.name, translate),
  });
}
