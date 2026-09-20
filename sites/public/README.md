# Public site source

This directory owns the public OrdaX product portal. It is not the OrdaX Web product mode and it must not import the shared Surface runtime.

Routes:

- `/` — landing page;
- `/download/` — public release catalog;
- `/login/` — sign-in entry point;
- `/cadastro/` — account creation entry point;
- `/conta/` — reserved authenticated user area; fail-closed until real identity/session integration is ready.

The baseline is dependency-free HTML/CSS/JavaScript. Runtime integration is configured by `config/public-site.json` and fails closed when identity or public release services are not configured.

Do not place secrets, privileged storage URLs, private release objects or provider service-role credentials in this tree. See `docs/PUBLIC-SITE.md`.


## Product distribution

This portal represents the **Stable/MVP** product distribution described in `MVP.md`.

Owner/Development remains an internal engineering profile. Public pages must not teach or depend on Git operations, branch names, pull requests or repository access. Public updates are presented as official OrdaX releases/channels, and the Creator is the normal public media-preparation path.

The portal may describe a capability only when its real owner/service exists or clearly mark it as not yet available.

The route `/` is always the public landing page. The authenticated OrdaX/account experience must never replace the public root. OrdaX Web remains a separate product mode and is reached from an appropriate authenticated/product entry point rather than being rendered as the marketing homepage.

## MVP scope: USB-only

The public MVP prepares and boots OrdaX from removable USB media. It does not advertise or expose installation to internal SSD/NVMe/HDD. Native installation remains a post-MVP foundation.

Web, Mobile, synchronization, backup and cross-device continuity may be presented only as **Em breve** while unavailable. No billing, pricing, commercial tier names or device-count limits are defined at this stage.
