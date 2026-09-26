# OrdaX Desktop Identity

The approved OrdaX public landing is the current visual reference for the shared Surface desktop shell. The product runtime must translate that language into an operational interface rather than copy the landing composition or its fictional demonstrations.

This is a product identity contract, not a screenshot contract. Implementations preserve the visual language while remaining functional, responsive, accessible, offline-capable and shared across supported hosts.

## Canonical visual language

- midnight blue-graphite primary canvas, anchored by `#080F19`;
- application canvas `#090F1B` and organized panel surfaces based on `#111E30`;
- pearl primary text `#E2EBF7` and restrained secondary text `#8E9DB4`;
- glacial blue `#A9C9F7` as the primary brand accent, without neon saturation;
- clear primary actions based on `#D1E4FF` with dark blue ink `#172B47`;
- structural borders based on `#243249`, thin rules and restrained depth;
- Inter as the canonical product type family, with light-to-medium headings and compact, legible controls;
- subtle illumination, orbital/geometric composition and titanium-like depth as replaceable visual layers, never as baked screenshots;
- fixed primary-app rail on desktop and a compact responsive equivalent on narrow surfaces;
- bottom area/status strip for workspace identity, running applications, update state and connectivity.

The approved direction is deliberately restrained: glow, blur and transparency may support hierarchy but must never reduce readability or compete with content. Application headings remain sized for working interfaces; the large marketing typography of the landing is not a Surface pattern.

## Shared design-system ownership

`system/surface/ui/tokens.css` is the single source of visual policy for semantic color, typography, spacing, radii, shadows, focus and motion. Surface and first-party application styles consume those semantic tokens instead of defining a separate palette per application.

`system/surface/ui/identity.css` is the shared component/composition layer for this identity. It may map existing components onto the semantic tokens while older component CSS is migrated, but it must not become a second token source.

Legacy palette literals must be removed from active contracts when the identity changes; they must not be retained in comments or assertions merely to satisfy obsolete tests.

The dark graphite identity is the visual reference presentation. Existing appearance preference and default behavior remain unchanged; the light theme remains supported as a cool pearl/blue presentation of the same semantic interface rather than a separate shell. Success, warning and error retain independent semantic colors and must not be reduced to the brand accent.

Motion is restrained to short UI transitions, normally 150–250 ms, and must honor both the OrdaX reduced-motion preference and the host `prefers-reduced-motion` signal. Focus remains visibly distinct in both themes and in high-contrast mode.

## Typography and offline operation

Inter is the canonical UI/display family. The Surface ships a local Latin variable WOFF2 covering normal weights 100–900 at `system/surface/ui/fonts/inter-latin-wght-normal.woff2`. Its pinned source provenance is recorded under `third_party/fonts/` and its SIL OFL license under `third_party/licenses/`.

`tokens.css` loads that font only through a relative local URL. The declared fallback chain remains `system-ui`, `Segoe UI`, sans-serif for hosts or glyphs outside the vendored subset; no host-specific font is source authority. The Surface/Web source graph follows local CSS assets, so the WOFF2 is copied into offline bundles without introducing a runtime network dependency.

## Interaction contract

The desktop shell must remain operational rather than decorative:

- Arquivos, Projetos, Notas, Internet, Ajustes, Conta and Sistema launch their real first-party applications when their capabilities are available;
- `Ctrl+K` opens the shared application launcher;
- area controls are backed by `ordax.workspace-store/2` and independent window state;
- `+` creates a real new area subject to the workspace bound;
- power actions remain host-capability driven and require explicit confirmation;
- update status is surfaced from the update watcher rather than inferred by the UI;
- visual updates must remain compatible with live Surface reload/restart and workspace persistence;
- keyboard navigation, focus restoration, text scaling and reduced motion remain functional after visual changes.

## Landing-page boundary

The public landing is an aesthetic reference only. Its Aurora project workspace, illustrative Intelligence response, notebook/phone simulations and marketing composition are not product contracts and must not be imported into `system/` as working capabilities.

Surface work may reuse the landing's visual principles — graphite, glacial blue, titanium depth, restrained orbit lines, spacing and typography — while continuing to consume only real product state owners and capability contracts.

## Non-goals

The visual reference must not be implemented by embedding the supplied concept image as the desktop background, duplicating the Surface per platform, introducing remote visual dependencies, copying the public demo runtime, or hiding non-functional placeholders behind presentation.

New desktop controls must have a real state owner and contract before being presented as available functionality. A redesign must not change release mode, update semantics, recovery behavior, security boundaries or physical-media policy merely for presentation.
