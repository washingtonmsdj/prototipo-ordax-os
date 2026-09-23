import assert from "node:assert/strict";
import test from "node:test";

import { NOTES_FILE_IMPORTER_SCHEMA } from "../system/contracts/notes-file-importer.mjs";
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

function importer(run) {
  return Object.freeze({
    schema: NOTES_FILE_IMPORTER_SCHEMA,
    importTextFile: run,
  });
}

test("action is hidden without an importer or when the selection is not a file", () => {
  assert.deepEqual(
    createFileNotesActionPresentation({ importerAvailable: false, busy: false, selected: FILE }),
    { visible: false, labelMessageId: null, disabled: true, titleMessageId: null },
  );
  assert.deepEqual(
    createFileNotesActionPresentation({
      importerAvailable: true,
      busy: false,
      selected: { kind: "directory", name: "Projeto", path: "/Projeto" },
    }),
    { visible: false, labelMessageId: null, disabled: true, titleMessageId: null },
  );
});

test("file action describes copy semantics and exposes a stable busy state", () => {
  const ready = createFileNotesActionPresentation({
    importerAvailable: true,
    busy: false,
    selected: FILE,
  });
  assert.equal(ready.visible, true);
  assert.equal(ready.labelMessageId, "files.notes.action.create");
  assert.equal(ready.disabled, false);
  assert.equal(ready.titleMessageId, "files.notes.action.title");

  const busy = createFileNotesActionPresentation({
    importerAvailable: true,
    busy: true,
    selected: FILE,
  });
  assert.equal(busy.visible, true);
  assert.equal(busy.labelMessageId, "files.notes.action.creating");
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
  }, FILE.name);
  assert.equal(durable.kind, "success");
  assert.equal(durable.openNotes, true);
  assert.equal(durable.messageId, "files.notes.createdDevice");
  assert.deepEqual(durable.messageParams, { name: FILE.name });

  const degraded = messageForNotesFileImport({
    status: "created",
    noteId: "note-2",
    projectId: "project-1",
    sourcePath: FILE.path,
    persistence: "device",
    persistenceOk: false,
  }, FILE.name);
  assert.equal(degraded.kind, "warning");
  assert.equal(degraded.openNotes, true);
  assert.equal(degraded.messageId, "files.notes.createdDegraded");

  const session = messageForNotesFileImport({
    status: "created",
    noteId: "note-3",
    projectId: "project-1",
    sourcePath: FILE.path,
    persistence: "session",
    persistenceOk: true,
  }, FILE.name);
  assert.equal(session.kind, "neutral");
  assert.equal(session.openNotes, true);
  assert.equal(session.messageId, "files.notes.createdSession");
});

test("failed imports remain in Files and never expose host exception detail", async () => {
  const secret = "credential-q7z9 user@example.com /home/private";
  const outcome = await importSelectedFileToNotes(
    importer(async () => {
      throw new Error(secret);
    }),
    FILE,
  );

  assert.deepEqual(outcome.result, { status: "failed", code: "notes-create-failed" });
  assert.equal(outcome.presentation.openNotes, false);
  assert.doesNotMatch(JSON.stringify(outcome), /credential-q7z9|user@example\.com|\/home\/private/);
  assert.equal(outcome.presentation.messageId, "files.notes.createFailed");
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
  );

  assert.deepEqual(calls, [FILE.path]);
  assert.equal(outcome.result.sourcePath, FILE.path);
  assert.equal(outcome.presentation.openNotes, true);
});

test("invalid importer output fails closed instead of reaching presentation as success", async () => {
  const outcome = await importSelectedFileToNotes(
    importer(async () => ({ status: "created", noteId: "missing-fields" })),
    FILE,
  );
  assert.deepEqual(outcome.result, { status: "failed", code: "notes-create-failed" });
  assert.equal(outcome.presentation.openNotes, false);
});
