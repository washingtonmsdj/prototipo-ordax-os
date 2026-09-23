# OrdaX localization

Status: **ACTIVE MVP POLICY**

OrdaX must separate three things that are often incorrectly called “language
support”:

1. locale accepted and persisted by the system;
2. first-use/OOBE translation;
3. complete Surface/application translation.

## MVP language set

The Native/USB first-use flow supports:

- `pt-BR` — Portuguese (Brazil), source/default language;
- `en-US` — English;
- `es-ES` — Spanish;
- `de-DE` — German;
- `fr-FR` — French.

The selector must never label a language as completely translated merely
because the OOBE is translated. Current English/Spanish/German/French coverage
starts at the first-use flow and expands through shared Surface catalogs.

## Expansion order

1. complete English across the shared Surface and first-party apps;
2. complete Spanish;
3. complete German;
4. complete French;
5. add further languages only when the shared i18n owner can keep them tested.

This order is about engineering sequence, not the importance of a language or
its speakers. PT-BR remains fully supported as the source language throughout.

## Current implementation status

The shared Surface now owns a provider-neutral localization runtime
(`ordax.localization/1`) driven directly by the persisted `regional.locale`
preference. PT-BR remains the source catalog. The shared desktop shell, launcher,
window chrome, workspace labels, connectivity copy, first-party app titles and
fallback panel metadata have explicit English catalog entries.

This does **not** make `en-US` a complete Surface locale yet. Files now localizes
navigation, search, locale-aware sorting, listing, selection, common create/copy/
rename/project forms, export/preview controls, Recents and recoverable Trash through
the same owner. Settings and System localize their shared section navigation/header
copy. Account consumes the shared catalog end to end. Notes now localizes its primary
navigation/editor shell, projects/list state, core persistence status and consultative
Intelligence controls; Internet localizes its primary browser shell, tab navigation,
address/search locale handling, project panel and key history/favorite states.
Operational/error messages in Files, deeper Settings/System content, deeper Notes/
Internet flows and remaining Surface copy still contain PT-BR text and remain in
migration. Network and battery trays/quick panels plus the Notification Center now
consume the shared localization owner. First-party update notifications persist bounded
semantic presentation identity so stored history can rerender when the locale changes;
generic producer text remains untouched by design. Spanish, German and French
continue to use explicit source-language fallback outside the already translated
OOBE until their shared catalogs are implemented.

```text
SURFACE_LOCALIZATION_OWNER=PASS_SOURCE
SURFACE_SOURCE_LOCALE=pt-BR
SURFACE_SHARED_SHELL_EN_US=PASS_SOURCE
FILES_PRIMARY_JOURNEY_EN_US=PASS_SOURCE
FILES_FORMS_SORT_EXPORT_PREVIEW_EN_US=PASS_SOURCE
SETTINGS_SYSTEM_NAV_EN_US=PASS_SOURCE
ACCOUNT_EN_US=PASS_SOURCE
NOTES_PRIMARY_JOURNEY_EN_US=PASS_SOURCE
INTERNET_PRIMARY_JOURNEY_EN_US=PASS_SOURCE
NETWORK_TRAY_QUICK_PANEL_EN_US=PASS_SOURCE
BATTERY_TRAY_QUICK_PANEL_EN_US=PASS_SOURCE
NOTIFICATION_CENTER_EN_US=PASS_SOURCE
FIRST_PARTY_UPDATE_NOTIFICATION_HISTORY_EN_US=PASS_SOURCE
SURFACE_COMPLETE_LOCALES=pt-BR
SURFACE_EN_US_APP_CONTROLS=MIGRATING
SURFACE_ES_ES=MIGRATING
SURFACE_DE_DE=MIGRATING
SURFACE_FR_FR=MIGRATING
```

## Architecture

Translations belong to shared product owners, never platform forks:

```text
shared message identity/catalog
 -> locale selection
 -> Surface/apps/services
 -> Web/Mobile/Desktop/USB/Native adapters only where platform formatting differs
```

Do not copy screens per language. Dynamic state such as Wi-Fi status must be
translated as structured pieces rather than concatenated Portuguese strings.

Locale and keyboard layout stay separate. Choosing English does not silently
change a Brazilian physical keyboard, and choosing German/French does not
invent an unproven XKB layout. Physical keyboard support remains governed by
`docs/contracts/keyboard-layout.json`.
