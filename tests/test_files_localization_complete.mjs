import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import {
  FILES_ENGLISH_MESSAGES,
  FILES_SOURCE_MESSAGES,
} from "../system/services/i18n/catalog/files.mjs";
import {
  FILES_OPERATIONAL_ENGLISH_MESSAGES,
  FILES_OPERATIONAL_SOURCE_MESSAGES,
} from "../system/services/i18n/catalog/files-operational.mjs";

const PORTUGUESE_UI =
  /[ãõçáéíóúâêôàü]|\b(?:Meu|espaço|pasta|arquivo|projeto|copiar|cópia|mover|movimento|renomear|lixeira|recentes|histórico|destino|origem|permissão|possível|disponível|inválido|atualize|apagado|visualização|restaurar|importar|exportação|ordenação|crescente|decrescente|Criar nota|Criando nota)\b/i;

function quotedLiterals(source) {
  const values = [];
  const pattern = /(["'`])((?:\\.|(?!\1)[\s\S])*?)\1/g;
  let match;
  while ((match = pattern.exec(source))) {
    const value = match[2].replace(/\s+/g, " ").trim();
    if (!value) continue;
    if (
      value.startsWith("files.")
      || value.startsWith("ordax.")
      || value.startsWith("data-")
      || value.startsWith("[data-")
    ) {
      continue;
    }
    values.push(value);
  }
  return values;
}

test("Files PT-BR and English catalogs stay structurally aligned", () => {
  assert.deepEqual(
    Object.keys(FILES_ENGLISH_MESSAGES).sort(),
    Object.keys(FILES_SOURCE_MESSAGES).sort(),
  );
  assert.deepEqual(
    Object.keys(FILES_OPERATIONAL_ENGLISH_MESSAGES).sort(),
    Object.keys(FILES_OPERATIONAL_SOURCE_MESSAGES).sort(),
  );
});

test("Files UI owners contain no remaining Portuguese user copy", async () => {
  const controls = await readFile(
    new URL("../system/surface/ui/file-space-controls.mjs", import.meta.url),
    "utf8",
  );
  const notesAction = await readFile(
    new URL("../system/surface/ui/file-notes-action.mjs", import.meta.url),
    "utf8",
  );

  const suspicious = [...quotedLiterals(controls), ...quotedLiterals(notesAction)]
    .filter((value) => PORTUGUESE_UI.test(value));

  assert.deepEqual(suspicious, []);
  assert.match(controls, /translate: t/);
  assert.match(controls, /importSelectedFileToNotes\(notesImporterPort, source, t\)/);
  assert.match(notesAction, /files\.notes\.action\.create/);
  assert.match(notesAction, /files\.notes\.createdDevice/);
});

test("English Files catalog covers safety-sensitive operational feedback", () => {
  assert.equal(
    FILES_OPERATIONAL_ENGLISH_MESSAGES["files.trash.failedPreserved"],
    "This item could not be moved to Trash. The original was preserved.",
  );
  assert.match(
    FILES_OPERATIONAL_ENGLISH_MESSAGES["files.restore.collision"],
    /Nothing was replaced/,
  );
  assert.match(
    FILES_OPERATIONAL_ENGLISH_MESSAGES["files.notes.createdDevice"],
    /original file was preserved/i,
  );
  assert.equal(
    FILES_OPERATIONAL_ENGLISH_MESSAGES["files.preview.close"],
    "Close",
  );
});
