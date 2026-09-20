# Apps

`system/apps/` owns the single source of first-party OrdaX applications.

Apps are product modules, not Web/Mobile/Desktop forks. The Surface imports the shared catalog and renders those app contracts inside the same workspace/window model across every compatible host.

## Current baseline

Each first-party app has one explicit owner:

```text
system/apps/files/
system/apps/notes/
system/apps/internet/
system/apps/settings/
system/apps/account/
system/apps/system/
```

Each owner also owns its component identity and semantic version through `component.mjs` and `version.mjs`. Versioning an app is therefore independent from the human OrdaX product version even when that app is still delivered in the same system bundle.

Current first-party app versions are:

```text
Arquivos  0.1.0
Ajustes   0.1.0
Conta     0.1.0
Sistema   0.1.0
Internet  0.3.0
Notas     0.4.0
```

For first-party apps, OrdaX treats the `0.x` line as **Beta**. `1.0.0` is reserved for the first stable app release. The Beta label is an app maturity convention; it does not claim that independent production distribution is already enabled.

`app-contract.mjs` validates the stable first-party app shape. `catalog.mjs` is deliberately thin: it composes the current owners, rejects duplicate IDs and exposes lookup/list operations to the Surface.

The initial owners are:

- Arquivos;
- Notas;
- Internet;
- Ajustes;
- Conta;
- Sistema.

App definitions contain platform-neutral metadata, capability requirements and declarative panels. They do not import browser/native adapters and they do not decide which platform is running.

Application availability is capability-driven. A future app that requires a capability declares that capability in `requiredCapabilities`; the Surface fails closed when the host does not expose it. An app may also declare `optionalCapabilities`: these enrich the same app when a host exposes them without turning that app into a platform fork or making the optional feature a launch requirement.

## Version and update identity

The OrdaX product, the system delivery and each app version are different identities:

```text
OrdaX product version  -> human product milestone
Entrega                -> notebook-facing system delivery sequence
Git SHA                -> exact technical source/build identity
App version             -> semantic version owned by that app
```

Updating OrdaX does not require every app version to change. Updating an app version does not create a new product version automatically.

Current release modes are intentionally mixed while the MVP hardens:

- `bundled`: Arquivos, Ajustes, Conta and Sistema currently update with the OrdaX system delivery;
- `git-app`: Notas and Internet own independent semantic versions, while the Owner/Development profile still delivers their code through the ordinary Git checkout/reconcile path;
- `component-slot`: reserved for an app that has completed the signed independent-package path with verification, pending health, promotion and rollback;
- no `git-app` claim is equivalent to a production app updater or Store.

`system/services/components/update-presentation.mjs` derives the two user-facing update scopes consumed by Sistema: **system** and **applications**. The `system` scope includes Base, Surface/services and the Sistema app itself. Other first-party apps belong to the `applications` scope even when their current channel is still bundled with OrdaX.

**Notas is an app, not a Surface/system subsystem.** Its stable app id is `notes`; Native/USB may enrich it through optional filesystem capabilities without changing its app identity.

**Internet follows the same app boundary.** Its stable app id is `internet`. The shared app owns browser chrome, workspace/tab organization and project context; Native/USB provide the optional browser engine capability through an isolated host, while Web fails closed instead of pretending arbitrary sites can be safely embedded.

## Boundary

Apps may depend on shared contracts and services according to `docs/contracts/module-boundaries.json`. They must not import `system/surface/` or concrete adapter implementations.

Do not create `apps-web`, `apps-mobile`, `apps-desktop`, Android/iOS copies or host-specific UI trees. Genuine host operations belong behind capability contracts and adapters.

The current registry is intentionally first-party and bounded. It is not a plugin marketplace or arbitrary code-loading framework; extension mechanics should only be introduced when there is a concrete product requirement and an explicit trust boundary.
