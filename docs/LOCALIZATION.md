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
