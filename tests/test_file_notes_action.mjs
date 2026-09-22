import assert from "node:assert/strict";
import test from "node:test";

import { NOTES_FILE_IMPORTER_SCHEMA } from "../system/contracts/notes-file-importer.mjs";
import {
  FILES_OPERATIONAL_ENGLISH_MESSAGES,
  FILES_OPERATIONAL_SOURCE_MESSAGES,
} from "../system/services/i18n/catalog/files-operational.mjs";
import {
  createFileNotesActionPresentation,
  importSelectedFileToNotes,
  messageForNotesFileImport,
} from "../system/surface/ui/file-notes-action.mjs";

const FILE = Object.freeze({
  kind: "file",
  name: "roteiro.txt",
  path: "/Documentos/roteiro.txt",
});

function translator(messages) {
  return (messageId, values = {}) => {
    let text = messages[messageId];
    if (typeof text !== "string") throw new TypeError(`missing message: ${messageId}`);
    for (const [key, value] of Object.entries(values)) {
      text = text.replaceAll(`{${key}}`, String(value));
    }
    return text;
  };
}

const pt = translator(FILES_OPERATIONAL_SOURCE_MESSAGES);
const en = translator(FILES_OPERATIONAL_ENGLISH_MESSAGES);

function importer(run) {
  return Object.freeze({
    schema: NOTES_FILE_IMPORTER_SCHEMA,
    importTextFile: run,
  });
}

test("action is hidden without an importer or when the selection is not a file", () => {
  assert.deepEqual(
    createFileNotesActionPresentation({ importerAvailable: false, busy: false, selected: FILE, translate: pt }),
    { visible: false, label: "", disabled: true, title: "" },
  );
  assert.deepEqual(
    createFileNotesActionPresentation({
      importerAvailable: true,
      busy: false,
      selected: { kind: "directory", name: "Projeto", path: "/Projeto" },
      translate: pt,
    }),
    { visible: false, label: "", disabled: true, title: "" },
  );
});

test("file action describes copy semantics and exposes a stable busy state", () => {
  const ready = createFileNotesActionPresentation({
    importerAvailable: true,
    busy: false,
    selected: FILE,
    translate: pt,
  });
  assert.equal(ready.visible, true);
  assert.equal(ready.label, "Criar nota");
  assert.equal(ready.disabled, false);
  assert.match(ready.title, /cópia do texto/i);
  assert.match(ready.title, /preserva o arquivo original/i);

  const busy = createFileNotesActionPresentation({
    importerAvailable: true,
    busy: true,
    selected: FILE,
    translate: pt,
  });
  assert.equal(busy.visible, true);
  assert.equal(busy.label, "Criando nota…");
  assert.equal(busy.disabled, true);
});

test("successful import messages distinguish durable, degraded, and session persistence", () => {
  const durable = messageForNotesFileImport({
    status: "created",
    noteId: "note-1",
    projectId: "project-1",
    sourcePath: FILE.path,
    persistence: "device",
    persistenceOk: true,
  }, FILE.name, pt);
  assert.equal(durable.kind, "success");
  assert.equal(durable.openNotes, true);
  assert.match(durable.text, /arquivo original foi preservado/i);

  const degraded = messageForNotesFileImport({
    status: "created",
    noteId: "note-2",
    projectId: "project-1",
    sourcePath: FILE.path,
    persistence: "device",
    persistenceOk: false,
  }, FILE.name, pt);
  assert.equal(degraded.kind, "warning");
  assert.equal(degraded.openNotes, true);
  assert.match(degraded.text, /persistência no dispositivo está degradada/i);

  const session = messageForNotesFileImport({
    status: "created",
    noteId: "note-3",
    projectId: "project-1",
    sourcePath: FILE.path,
    persistence: "session",
    persistenceOk: true,
  }, FILE.name, pt);
  assert.equal(session.kind, "neutral");
  assert.equal(session.openNotes, true);
  assert.match(session.text, /somente nesta sessão/i);
});

test("failed imports remain in Files and never expose host exception detail", async () => {
  const secret = "credential-q7z9 user@example.com /home/private";
  const outcome = await importSelectedFileToNotes(
    importer(async () => {
      throw new Error(secret);
    }),
    FILE,
    pt,
  );

  assert.deepEqual(outcome.result, { status: "failed", code: "notes-create-failed" });
  assert.equal(outcome.presentation.openNotes, false);
  assert.doesNotMatch(JSON.stringify(outcome), /credential-q7z9|user@example\.com|\/home\/private/);
  assert.match(outcome.presentation.text, /arquivo original não foi alterado/i);
});

test("the selected file identity is captured and the importer receives only its exact logical path", async () => {
  const calls = [];
  const outcome = await importSelectedFileToNotes(
    importer(async (path) => {
      calls.push(path);
      return {
        status: "created",
        noteId: "note-4",
        projectId: "project-1",
        sourcePath: path,
        persistence: "session",
        persistenceOk: true,
      };
    }),
    FILE,
    pt,
  );

  assert.deepEqual(calls, [FILE.path]);
  assert.equal(outcome.result.sourcePath, FILE.path);
  assert.equal(outcome.presentation.openNotes, true);
});

test("invalid importer output fails closed instead of reaching presentation as success", async () => {
  const outcome = await importSelectedFileToNotes(
    importer(async () => ({ status: "created", noteId: "missing-fields" })),
    FILE,
    pt,
  );
  assert.deepEqual(outcome.result, { status: "failed", code: "notes-create-failed" });
  assert.equal(outcome.presentation.openNotes, false);
});

test("Files to Notes action and feedback localize in English", async () => {
  const presentation = createFileNotesActionPresentation({
    importerAvailable: true,
    busy: false,
    selected: FILE,
    translate: en,
  });
  assert.equal(presentation.label, "Create note");
  assert.match(presentation.title, /preserves the original file/i);

  const message = messageForNotesFileImport({
    status: "created",
    noteId: "note-en",
    projectId: "project-1",
    sourcePath: FILE.path,
    persistence: "device",
    persistenceOk: true,
  }, FILE.name, en);
  assert.equal(message.kind, "success");
  assert.match(message.text, /original file was preserved/i);
});

