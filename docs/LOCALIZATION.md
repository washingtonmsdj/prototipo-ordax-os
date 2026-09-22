# OrdaX Localization

Status: FIRST-RUN/OOBE MULTILINGUAL FOUNDATION IMPLEMENTED

## Current complete surface

The Native/USB first-run experience is localized in:

- `pt-BR` — Português (Brasil), default;
- `en-US` — English (United States), technical fallback;
- `es-419` — Español (Latinoamérica);
- `fr-FR` — Français (France);
- `de-DE` — Deutsch (Deutschland).

The locale is persisted as a regional preference. Changing the language in the
OOBE rerenders that experience immediately from one shared message catalog; it
does not load a copied/forked UI.

English is the fallback for a missing locale-specific key. An unknown message
key fails rather than displaying `undefined`.

## Product-wide rollout

The four locales above are complete for the first-run/OOBE surface only. The
wider Surface and first-party apps still contain Portuguese strings and must be
migrated incrementally to shared catalogs before claiming full-system coverage.

Japanese and Korean should not be enabled merely by translating labels: they require reviewed fonts, locale behavior and IME/input support on Native hardware. Additional locales must follow the same coverage-and-input rule rather than being advertised from partial string sets.

## Rules

- locale must not fork product logic;
- UI strings belong in shared catalogs, not platform-specific copies;
- formatting of dates/numbers should use the selected locale where supported;
- untranslated keys fall back predictably rather than mixing random strings;
- input-method support is a separate Native capability from translation;
- each surface must declare its actual coverage before being advertised as
  translated.
