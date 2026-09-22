import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_LOCALE,
  LOCALE_METADATA,
  SUPPORTED_CATALOG_LOCALES,
  hasTranslation,
  translate,
} from "../system/services/i18n/catalog.mjs";

test("MVP localization catalog has PT-BR plus English and Latin American Spanish previews", () => {
  assert.equal(DEFAULT_LOCALE, "pt-BR");
  assert.deepEqual(SUPPORTED_CATALOG_LOCALES, ["pt-BR", "en-US", "es-419"]);
  assert.equal(LOCALE_METADATA["pt-BR"].status, "complete");
  assert.equal(LOCALE_METADATA["en-US"].status, "preview");
  assert.equal(LOCALE_METADATA["es-419"].status, "preview");
  for (const locale of SUPPORTED_CATALOG_LOCALES) {
    assert.equal(hasTranslation(locale, "assistant.send"), true);
    assert.ok(translate(locale, "assistant.title"));
  }
});

test("unknown locale falls back to PT-BR and unknown key fails closed", () => {
  assert.equal(translate("fr-FR", "assistant.send"), "Enviar");
  assert.throws(() => translate("pt-BR", "missing.key"), TypeError);
});
