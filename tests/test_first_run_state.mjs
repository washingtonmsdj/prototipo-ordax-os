import test from "node:test";
import assert from "node:assert/strict";

import {
  FIRST_RUN_STATE_SCHEMA,
  completeFirstRunState,
  createInitialFirstRunState,
  seedMissingRegionalPreferencesFromFirstRun,
  validateFirstRunState,
} from "../system/services/state/first-run.mjs";
import {
  REGIONAL_LOCALE_PREFERENCE_ID,
  REGIONAL_TIME_ZONE_PREFERENCE_ID,
  regionalLocalePreference,
  regionalTimeZonePreference,
} from "../system/services/preferences/regional.mjs";

test("first-run begins incomplete and local/account choice is not preselected", () => {
  assert.deepEqual(createInitialFirstRunState(), {
    schema: FIRST_RUN_STATE_SCHEMA,
    completed: false,
    locale: "pt-BR",
    timeZone: "America/Bahia",
    accountMode: null,
  });
});

test("first-run completion supports local-only and identity modes", () => {
  for (const accountMode of ["local-only", "identity"]) {
    const state = completeFirstRunState({
      locale: "pt-BR",
      timeZone: "America/Bahia",
      accountMode,
    });
    assert.equal(state.completed, true);
    assert.equal(state.accountMode, accountMode);
  }
});

test("first-run rejects unsupported locale, timezone and incomplete account persistence", () => {
  assert.throws(
    () => completeFirstRunState({ locale: "en-US", timeZone: "America/Bahia", accountMode: "local-only" }),
    TypeError,
  );
  assert.throws(
    () => completeFirstRunState({ locale: "pt-BR", timeZone: "Europe/London", accountMode: "local-only" }),
    TypeError,
  );
  assert.throws(
    () => validateFirstRunState({
      schema: FIRST_RUN_STATE_SCHEMA,
      completed: false,
      locale: "pt-BR",
      timeZone: "America/Bahia",
      accountMode: "local-only",
    }),
    TypeError,
  );
});

test("regional preferences are canonical preference definitions", () => {
  assert.equal(regionalLocalePreference.id, REGIONAL_LOCALE_PREFERENCE_ID);
  assert.equal(regionalLocalePreference.validate("pt-BR"), "pt-BR");
  assert.equal(regionalTimeZonePreference.id, REGIONAL_TIME_ZONE_PREFERENCE_ID);
  assert.equal(regionalTimeZonePreference.validate("America/Bahia"), "America/Bahia");
  assert.throws(() => regionalLocalePreference.validate("en-US"), TypeError);
});

test("completed first-run repairs only missing regional preference keys", () => {
  const completed = completeFirstRunState({
    locale: "pt-BR",
    timeZone: "America/Manaus",
    accountMode: "local-only",
  });

  const seeded = seedMissingRegionalPreferencesFromFirstRun(
    { "appearance.theme": "dark" },
    completed,
  );
  assert.equal(seeded.changed, true);
  assert.deepEqual(seeded.snapshot, {
    "appearance.theme": "dark",
    "regional.locale": "pt-BR",
    "regional.time-zone": "America/Manaus",
  });

  const preserved = seedMissingRegionalPreferencesFromFirstRun(
    {
      "regional.locale": "pt-BR",
      "regional.time-zone": "America/Sao_Paulo",
    },
    completed,
  );
  assert.equal(preserved.changed, false);
  assert.equal(preserved.snapshot["regional.time-zone"], "America/Sao_Paulo");

  const incomplete = seedMissingRegionalPreferencesFromFirstRun(
    {},
    createInitialFirstRunState(),
  );
  assert.equal(incomplete.changed, false);
  assert.deepEqual(incomplete.snapshot, {});
});
