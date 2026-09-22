import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import {
  SURFACE_RENDER_LIFECYCLE_SCHEMA,
  assertSurfaceRenderLifecycle,
} from "../system/contracts/surface-render-lifecycle.mjs";
import { LOCALIZATION_SCHEMA } from "../system/contracts/localization.mjs";
import {
  FILES_ENGLISH_MESSAGES,
  FILES_SOURCE_MESSAGES,
} from "../system/services/i18n/catalog/files.mjs";
import {
  SETTINGS_ENGLISH_MESSAGES,
  SETTINGS_SOURCE_MESSAGES,
} from "../system/services/i18n/catalog/settings.mjs";
import {
  SYSTEM_ENGLISH_MESSAGES,
  SYSTEM_SOURCE_MESSAGES,
} from "../system/services/i18n/catalog/system.mjs";

function localization() {
  return Object.freeze({
    schema: LOCALIZATION_SCHEMA,
    getLocale() {
      return "en-US";
    },
    translate(messageId, values = {}) {
      let value = FILES_ENGLISH_MESSAGES[messageId]
        ?? SETTINGS_ENGLISH_MESSAGES[messageId]
        ?? SYSTEM_ENGLISH_MESSAGES[messageId]
        ?? messageId;
      for (const [key, replacement] of Object.entries(values)) {
        value = value.replaceAll(`{${key}}`, String(replacement));
      }
      return value;
    },
    subscribe(listener) {
      listener("en-US");
      return () => {};
    },
  });
}

function lifecycle(overrides = {}) {
  return {
    schema: SURFACE_RENDER_LIFECYCLE_SCHEMA,
    localization: localization(),
    subscribeRender() {
      return () => {};
    },
    getAppTarget() {
      return null;
    },
    setAppTarget() {},
    ...overrides,
  };
}

test("Surface render lifecycle v4 formally requires localization", () => {
  const value = lifecycle();
  assert.equal(SURFACE_RENDER_LIFECYCLE_SCHEMA, "ordax.surface-render-lifecycle/4");
  assert.equal(assertSurfaceRenderLifecycle(value), value);

  const withoutLocalization = { ...value };
  delete withoutLocalization.localization;
  assert.throws(
    () => assertSurfaceRenderLifecycle(withoutLocalization),
    /localization port/i,
  );
});

test("Files source and English catalogs cover the same structural keys", () => {
  assert.deepEqual(
    Object.keys(FILES_ENGLISH_MESSAGES).sort(),
    Object.keys(FILES_SOURCE_MESSAGES).sort(),
  );
  assert.equal(FILES_ENGLISH_MESSAGES["files.location.trash"], "Trash");
  assert.equal(FILES_ENGLISH_MESSAGES["files.trash.restore"], "Restore");
  assert.equal(FILES_ENGLISH_MESSAGES["files.search.folder.placeholder"], "Search this folder");
  assert.equal(FILES_ENGLISH_MESSAGES["files.action.moveToTrash"], "Move to Trash");
});

test("Settings and System navigation catalogs stay key-aligned", () => {
  assert.deepEqual(
    Object.keys(SETTINGS_ENGLISH_MESSAGES).sort(),
    Object.keys(SETTINGS_SOURCE_MESSAGES).sort(),
  );
  assert.deepEqual(
    Object.keys(SYSTEM_ENGLISH_MESSAGES).sort(),
    Object.keys(SYSTEM_SOURCE_MESSAGES).sort(),
  );
  assert.equal(SETTINGS_ENGLISH_MESSAGES["settings.section.regional"], "Language and region");
  assert.equal(SYSTEM_ENGLISH_MESSAGES["system.section.diagnostics"], "Diagnostics");
});

test("first-party app controls consume lifecycle localization instead of locale globals", async () => {
  const files = await readFile(
    new URL("../system/surface/ui/file-space-controls.mjs", import.meta.url),
    "utf8",
  );
  const settings = await readFile(
    new URL("../system/surface/ui/settings-overview-controls.mjs", import.meta.url),
    "utf8",
  );
  const system = await readFile(
    new URL("../system/surface/ui/system-overview-controls.mjs", import.meta.url),
    "utf8",
  );

  assert.match(files, /const localization = lifecycle\.localization/);
  assert.match(files, /t\("files\.location\.trash"\)/);
  assert.match(files, /t\("files\.trash\.restore"\)/);
  assert.match(files, /localeCompare\(right\.name, locale\(\)/);
  assert.doesNotMatch(files, /FILE_SEARCH_LOCALE/);

  assert.match(settings, /const localization = lifecycle\.localization/);
  assert.match(settings, /t\("settings\.navigation\.aria"\)/);
  assert.match(settings, /t\(section\.messageId\)/);
  assert.doesNotMatch(settings, /const SECTION_COPY/);

  assert.match(system, /const localization = lifecycle\.localization/);
  assert.match(system, /t\("system\.navigation\.aria"\)/);
  assert.match(system, /t\(section\.messageId\)/);
  assert.doesNotMatch(system, /const SECTION_COPY/);
});
