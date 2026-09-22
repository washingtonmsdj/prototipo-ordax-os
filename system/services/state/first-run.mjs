import {
  FIRST_RUN_STATE_SCHEMA,
  createInitialFirstRunState,
  validateFirstRunState,
} from "../../contracts/first-run-state-store.mjs";
import { validatePreferenceRecord } from "../../contracts/preference-store.mjs";
import {
  REGIONAL_LOCALE_PREFERENCE_ID,
  REGIONAL_TIME_ZONE_PREFERENCE_ID,
} from "../preferences/regional.mjs";

export {
  FIRST_RUN_STATE_SCHEMA,
  createInitialFirstRunState,
  validateFirstRunState,
};

export function completeFirstRunState({ locale, timeZone, accountMode }) {
  return validateFirstRunState({
    schema: FIRST_RUN_STATE_SCHEMA,
    completed: true,
    locale,
    timeZone,
    accountMode,
  });
}

export function seedMissingRegionalPreferencesFromFirstRun(preferenceRecord, firstRunState) {
  const current = validatePreferenceRecord(preferenceRecord);
  const firstRun = validateFirstRunState(firstRunState);
  if (!firstRun.completed) {
    return Object.freeze({ changed: false, snapshot: current });
  }

  const next = { ...current };
  let changed = false;
  if (!Object.prototype.hasOwnProperty.call(next, REGIONAL_LOCALE_PREFERENCE_ID)) {
    next[REGIONAL_LOCALE_PREFERENCE_ID] = firstRun.locale;
    changed = true;
  }
  if (!Object.prototype.hasOwnProperty.call(next, REGIONAL_TIME_ZONE_PREFERENCE_ID)) {
    next[REGIONAL_TIME_ZONE_PREFERENCE_ID] = firstRun.timeZone;
    changed = true;
  }

  return Object.freeze({
    changed,
    snapshot: changed ? validatePreferenceRecord(next) : current,
  });
}
