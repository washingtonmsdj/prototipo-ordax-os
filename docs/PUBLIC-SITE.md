# OrdaX Public Site

Status: FOUNDATION / NOT DEPLOYED

The public OrdaX site is a separate delivery surface from the OrdaX Web product mode.

The public portal presents the **Stable/MVP** distribution only. Owner/Development may use Git-first workflows internally, but Git, branches, pull requests and repository mechanics are not part of the normal public product experience. See `MVP.md`.

`OrdaX Web` is the shared OrdaX Surface rendered for a Web-capable host. The public site is the product portal that presents OrdaX, exposes public release downloads, and provides entry points for account creation and sign-in.

## Repository boundary

The public portal stays in this repository while the product is still evolving quickly:

```text
sites/public/
  index.html
  download/index.html
  login/index.html
  cadastro/index.html
  licencas/index.html
  privacidade/index.html
  termos/index.html
  assets/
  config/public-site.json
```

It is built as the independent `public-site` artifact class. A site-only change must not rebuild the kernel, bootstrap, shared Surface or native release.

Keeping the portal in the monorepo does not make it part of the operating-system runtime. It has its own build recipe, candidate artifact and deployment boundary.

## Route ownership

- `/`: public landing page. It must never become the authenticated OrdaX workspace.
- `/download/`: public release discovery and verified download links.
- `/login/`: sign-in entry point.
- `/cadastro/`: account-creation entry point.
- `/conta/`: authenticated user area. Until real identity/session integration is enabled, it remains fail-closed and must not simulate user data.
- `/licencas/`: release-specific license, SBOM and source-compliance entry point.
- `/privacidade/`: privacy-readiness page; not a final policy while account activation is blocked.
- `/termos/`: terms-readiness page; not final terms while account activation is blocked.

The public landing and the authenticated product experience are deliberately separate:

```text
/               -> public product landing
/login/         -> authentication entry
/conta/         -> authenticated account area
OrdaX Web       -> product runtime reached from an appropriate authenticated/product entry point
```

The OrdaX Web Surface must not be mounted over `/`. The account area may expose profile, devices, session, synchronized preferences and product-entry actions only when their backing services are real. OrdaX Web remains a separate product mode from the marketing portal even when the account links to it.

Future routes such as support, docs and additional legal surfaces may be added here only when they have a real owner and service contract.

## Identity boundary

The browser pages do not implement an identity provider and must not store passwords, tokens or session secrets themselves.

The static site exposes a configurable same-origin handoff:

```text
public site
 -> configured identity route/service
 -> OrdaX identity/session owner
```

Until an identity backend is configured, login and registration forms remain absent and the page reports that account access is not yet available. Do not ship a fake form or local-only account database.

The future identity service may use an external infrastructure provider behind an OrdaX-owned service/adapter, but the browser contract must not couple product UI directly to one provider.

The machine-readable entry boundary is `docs/contracts/public-identity.json`. It requires one account model across product modes, forbids browser/service secrets and keeps login/cadastro unavailable until a real same-origin identity route is configured.

The server-side responsibility is prepared under `services/public-identity/`. The dedicated Supabase project `ordax-control-plane` is now the selected pre-MVP backend target and the canonical product-domain schema under `infra/supabase/product/` has been applied there. This prepares account/Spaces/entitlements/Profile Packs/Memory without enabling the public gateway. Login and registration remain fail-closed until same-origin deployment, Auth hardening and legal-readiness gates are complete. The previously considered shared project remains rejected because it already owns unrelated Auth/profile behavior.

## Download boundary

The site never hard-codes a "latest" image or fabricates release availability.

The download page consumes the same-origin catalog at `/releases/catalog.json`. The public-site build generates that file deterministically from `platform/releases/publications.json`; the page does not manufacture release metadata.

The publication source is intentionally empty while `PRODUCTION_RELEASE_PUBLISHED=NO`. A release can enter it only with explicit per-release and per-target public authorization, exact source commit, artifact size and SHA-256. The generator rejects unknown fields, duplicate identities and non-same-origin download paths. See `docs/contracts/public-release-catalog.json`.

Minimum intended flow:

```text
source commit
 -> canonical build
 -> tests + provenance + SHA-256
 -> authorized public release
 -> public release catalog
 -> download page
```

When there is no authorized release, the generated catalog is valid but empty; the page says so and exposes no download button. A missing or malformed catalog still fails closed.

A public release must also pass the release-compliance gate in `docs/RELEASE-COMPLIANCE.md` and `docs/contracts/release-compliance.json`. Each listed release must expose an integrity-bound SBOM, third-party notices and release-specific source-compliance bundle before the Download or Licenças page can render it.

## Security invariants

- no private keys, service-role keys, passwords or bearer tokens in `sites/public/`;
- no direct browser access to privileged release storage;
- identity and download targets are same-origin by default;
- no remote JavaScript, CSS or font runtime dependencies in the baseline;
- client code never treats telemetry as an account/control API;
- release SHA-256/provenance data is displayed from the release owner, not generated by the page;
- account and download availability fail closed.

## Visual direction

### Interactive landing demonstration

The landing includes an explicitly labeled, disposable marketing playground in
`assets/playground.js` and `assets/playground.css`. It is not OrdaX Web and does
not import or fork the product Surface. The default notebook and phone view is
an independent demonstration of the current Surface Home language (Área 01,
clock, application launcher and Seu espaço), while Notes, Files and Settings
remain explorable from that Home.

The playground's labels, app order and Home spaces come from the generated
`assets/playground-fixture.json`. Run
`python tools/public-site/playground_fixture.py --write` after changing the
Surface app catalog or Home shell. `python tools/public-site/build.py check`
validates that the committed JSON and the inline browser fixture are current;
this keeps the public demonstration aligned with the product source without
mounting the product runtime on the public site.

The fixture is used only to render a disposable, anonymous example. Note edits,
a checklist and appearance changes are mirrored locally in either direction;
file browsing reads fixed examples only. This demonstrates intended continuity,
not production cloud sync.

There are no requests, account credentials, user-file access, persistence,
analytics or external dependencies in this demonstration. Reload/reset discards
edits. Device navigation remains independent. On small screens devices stack;
the visitor can also select notebook-only presentation. Login, registration and
download continue through the existing fail-closed routes and owners.

Handoff: this is source implementation only, not deployment evidence. The
dependency-free fixture, public-site check and public-site smoke tests validate
the local artifact; production hosting and configured identity/release owners
remain separate requirements. Do not promote the demonstration into a second
product runtime or treat its fixtures as real user data.

The portal shares OrdaX brand language, not the desktop shell implementation:

- mineral/off-white canvas;
- graphite/black foreground;
- OrdaX orange accent;
- editorial display type with restrained sans-serif controls;
- architectural rules and negative space;
- responsive layout.

It must not copy the Surface desktop markup or make the marketing site look like a fake operating-system screenshot.

Public copy should explain user-facing product behavior: Creator, **USB execution**, apps, official updates, rollback/recovery and account availability. The MVP must not advertise internal-disk installation as available. Native installation may be described only as a future/post-MVP direction. Web, Mobile, synchronization, backup and cross-device continuity may appear only as **Em breve** while unavailable. Do not use the landing page to explain Owner/Development Git operations.

No public page may invent prices, billing, commercial tier names or device-count limits before those policies exist. The provisional two-private-Space architecture default is an internal capacity foundation, not a public commercial offer and must not be advertised as a finalized free-plan quota.

## Build

```bash
python tools/public-site/build.py check
python tools/public-site/build.py build --source-commit <40-hex-sha> --out-dir out/public-site
python tools/public-site/build.py verify --out-dir out/public-site
```

The candidate workflow builds the site twice and compares outputs to protect deterministic packaging.


## Runtime preview and deployment boundary

`tools/public-site/preview_server.py` is a loopback-only development/test adapter for the built artifact. It serves the static portal and mounts the fail-closed public identity gateway under the same `/auth/*` origin so CI can exercise the complete route boundary without deploying a provider.

It refuses non-loopback binds and is **not** the production server.

Production hosting remains provider-neutral. A production-shaped Nginx adapter now exists at `deploy/public-site/nginx.conf`: it serves the deterministic static artifact from loopback and forwards only `/auth/*` and `/sync/*` to the deployed OrdaX account gateway. A public HTTPS terminator must sit in front of that loopback listener, so browser requests remain same-origin and provider-specific CORS is not part of the product contract.

The required route shape, cache policy and security headers are machine-readable in `docs/contracts/public-site-deployment.json`. The adapter preserves account status codes and `Set-Cookie`, applies the declared CSP, anti-framing, MIME-sniffing, referrer and permissions policies, and keeps account/sync responses `no-store`. Source readiness is not deployment evidence: public login remains disabled until this adapter (or an equivalent conforming host adapter) is actually deployed over HTTPS.


## Legal readiness before live accounts

The public account entry points are also gated by `docs/contracts/public-legal-readiness.json`. While that contract is not ready, `sites/public/config/public-site.json` must keep both login and registration targets null. The build fails if someone tries to enable them early.

The readiness pages under `/privacidade/` and `/termos/` intentionally describe only the current prototype state. Final legal documents, versions and effective dates must be reviewed and published before this gate can move to ready.
