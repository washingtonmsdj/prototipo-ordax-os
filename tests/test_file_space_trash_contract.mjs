import assert from "node:assert/strict";
import test from "node:test";

import {
  FILE_SPACE_SCHEMA,
  assertFileSpacePort,
  validateFileSpacePath,
  validateTrashEntry,
  validateTrashListing,
} from "../system/contracts/file-space.mjs";

function completePort() {
  const listing = Object.freeze({ path: "/", entries: Object.freeze([]) });
  const trash = Object.freeze({ entries: Object.freeze([]) });
  return Object.freeze({
    schema: FILE_SPACE_SCHEMA,
    async list() { return listing; },
    async createDirectory() { return listing; },
    async readTextFile() { return { path: "/a.txt", size: 0, text: "" }; },
    async renameEntry() { return listing; },
    async copyFile() { return listing; },
    async moveEntry() { return listing; },
    async trashEntry() { return listing; },
    async listTrash() { return trash; },
    async restoreTrashEntry() { return trash; },
    async exportFile() {},
    async importFile() { return listing; },
  });
}

test("file-space v11 reserves the private trash namespace", () => {
  assert.equal(FILE_SPACE_SCHEMA, "ordax.file-space/11");
  assert.throws(() => validateFileSpacePath("/.ordax-trash"), /invalid segment/);
  assert.throws(
    () => validateFileSpacePath("/Documentos/.ordax-trash/item"),
    /invalid segment/,
  );
});

test("trash entries carry bounded recovery metadata", () => {
  const entry = validateTrashEntry({
    id: "0123456789abcdef0123456789abcdef",
    name: "nota.txt",
    kind: "file",
    size: 12,
    modifiedAt: 100,
    originalPath: "/Documentos/nota.txt",
    trashedAt: 200,
  });
  assert.equal(entry.originalPath, "/Documentos/nota.txt");
  assert.equal(entry.trashedAt, 200);
  assert.deepEqual(validateTrashListing({ entries: [entry] }).entries, [entry]);

  assert.throws(
    () => validateTrashEntry({ ...entry, id: "../escape" }),
    /id is invalid/,
  );
  assert.throws(
    () => validateTrashEntry({ ...entry, originalPath: "/Downloads/outro.txt" }),
    /name must match/,
  );
});

test("file-space port requires recoverable trash operations", () => {
  const port = completePort();
  assert.equal(assertFileSpacePort(port), port);
  const incomplete = { ...port };
  delete incomplete.restoreTrashEntry;
  assert.throws(() => assertFileSpacePort(incomplete), /restoreTrashEntry/);
});
