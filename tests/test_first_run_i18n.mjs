import assert from "node:assert/strict";
import test from "node:test";

import {
  firstRunStepLabels,
  firstRunText,
} from "../system/i18n/first-run.mjs";

const LOCALES = ["pt-BR", "en-US", "es-419", "fr-FR", "de-DE"];

test("first-run catalogs expose complete navigation for MVP locales", () => {
  for (const locale of LOCALES) {
    const labels = firstRunStepLabels(locale);
    assert.equal(labels.length, 6);
    assert.equal(labels.every((value) => typeof value === "string" && value.length > 0), true);
    assert.equal(firstRunText(locale, "continue").length > 0, true);
    assert.equal(firstRunText(locale, "connect").length > 0, true);
    assert.equal(firstRunText(locale, "continueWithoutAccount").length > 0, true);
  }
});

test("first-run interpolation is locale aware and unknown locale falls back to English", () => {
  assert.equal(firstRunText("pt-BR", "passwordFor", { ssid: "Casa" }), "Senha de Casa");
  assert.equal(firstRunText("es-419", "passwordFor", { ssid: "Casa" }), "Contraseña de Casa");
  assert.equal(firstRunText("de-DE", "passwordFor", { ssid: "Casa" }), "Passwort für Casa");
  assert.equal(firstRunText("xx-YY", "continue"), "Continue");
});

test("unknown translation keys fail instead of leaking undefined into UI", () => {
  assert.throws(() => firstRunText("en-US", "missing-key"), TypeError);
});
