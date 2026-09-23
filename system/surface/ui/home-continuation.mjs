import {
  assertProjectCatalogPort,
  validateProjectCatalogSnapshot,
} from "../../contracts/project-catalog.mjs";
import {
  assertRecentFilesPort,
  validateRecentFilesSnapshot,
} from "../../contracts/recent-files.mjs";
import { validateFileSpacePath } from "../../contracts/file-space.mjs";
import { assertSurfaceRenderLifecycle } from "../../contracts/surface-render-lifecycle.mjs";

const MAX_HOME_CONTINUATION_ITEMS = 4;
const MAX_PROJECT_ITEMS = 2;
const MAX_RECENT_ITEMS = 2;
const HOME_TIME_ZONE = "America/Bahia";

function parentPath(path) {
  const value = validateFileSpacePath(path);
  if (value === "/") return "/";
  const index = value.lastIndexOf("/");
  return index <= 0 ? "/" : value.slice(0, index);
}

export function formatHomeActivity(timestamp, locale = "pt-BR", unknownLabel = "") {
  if (!Number.isSafeInteger(timestamp) || timestamp < 0) return unknownLabel;
  return new Intl.DateTimeFormat(locale, {
    timeZone: HOME_TIME_ZONE,
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(timestamp));
}

export function createHomeContinuationPresentation({
  projects = null,
  recentFiles = null,
} = {}) {
  const projectSnapshot = projects === null
    ? null
    : validateProjectCatalogSnapshot(projects);
  const recentSnapshot = recentFiles === null
    ? null
    : validateRecentFilesSnapshot(recentFiles);

  const projectItems = projectSnapshot
    ? [...projectSnapshot.projects]
      .sort((left, right) => right.lastOpenedAt - left.lastOpenedAt)
      .slice(0, MAX_PROJECT_ITEMS)
      .map((project) => Object.freeze({
        key: `project:${project.id}`,
        kind: "project",
        title: project.name,
        path: project.path,
        activityAt: project.lastOpenedAt,
        persistence: projectSnapshot.persistence,
        detailMessageId: "home.continuation.project.detail",
        actionMessageId: "home.continuation.project.action",
        actionParams: Object.freeze({ name: project.name }),
        appId: "files",
        target: project.path,
      }))
    : [];

  const recentItems = recentSnapshot
    ? [...recentSnapshot.entries]
      .sort((left, right) => right.openedAt - left.openedAt)
      .slice(0, MAX_RECENT_ITEMS)
      .map((entry) => {
        const folder = parentPath(entry.path);
        return Object.freeze({
          key: `recent:${entry.path}`,
          kind: "recent-file",
          title: entry.name,
          folder,
          activityAt: entry.openedAt,
          persistence: recentSnapshot.persistence,
          detailMessageId: "home.continuation.recent.detail",
          actionMessageId: "home.continuation.recent.action",
          actionParams: Object.freeze({ name: entry.name }),
          appId: "files",
          target: folder,
        });
      })
    : [];

  const items = [...projectItems, ...recentItems].slice(0, MAX_HOME_CONTINUATION_ITEMS);
  return Object.freeze({
    visible: items.length > 0,
    items: Object.freeze(items),
  });
}

function node(documentObject, tag, className = "", text = undefined) {
  const element = documentObject.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function assertHomeRoot(root) {
  if (
    !root
    || typeof root !== "object"
    || typeof root.querySelector !== "function"
    || !root.ownerDocument
  ) {
    throw new TypeError("Home continuation requires a Surface root");
  }
  return root;
}

export function mountHomeContinuation(
  rootValue,
  { projects = null, recentFiles = null } = {},
  surfaceLifecycle,
) {
  const root = assertHomeRoot(rootValue);
  const lifecycle = assertSurfaceRenderLifecycle(surfaceLifecycle);
  const localization = lifecycle.localization;
  const t = localization.translate;
  const projectPort = projects === null ? null : assertProjectCatalogPort(projects);
  const recentPort = recentFiles === null ? null : assertRecentFilesPort(recentFiles);
  const documentObject = root.ownerDocument;
  const homePanel = root.querySelector(".ordax-home-panel");
  const space = homePanel?.querySelector(".ordax-space");
  if (!homePanel || !space) {
    throw new Error("Home continuation requires the canonical Home panel");
  }

  let destroyed = false;
  let section = null;
  let projectSnapshot = projectPort?.getSnapshot() ?? null;
  let recentSnapshot = recentPort?.getSnapshot() ?? null;

  const render = () => {
    if (destroyed) return;
    const focusedKey = documentObject.activeElement?.dataset?.homeContinuationKey ?? null;
    const presentation = createHomeContinuationPresentation({
      projects: projectSnapshot,
      recentFiles: recentSnapshot,
    });

    if (!presentation.visible) {
      section?.remove();
      section = null;
      return;
    }

    const next = node(documentObject, "section", "ordax-space");
    next.dataset.homeContinuation = "";
    next.setAttribute("aria-labelledby", "ordax-home-continuation-title");
    const heading = node(
      documentObject,
      "p",
      "ordax-section-kicker",
      t("home.continuation.heading"),
    );
    heading.id = "ordax-home-continuation-title";
    next.append(heading);

    for (const item of presentation.items) {
      const button = node(documentObject, "button", "ordax-space-link");
      button.type = "button";
      button.dataset.homeContinuationKey = item.key;
      button.dataset.launchApp = item.appId;
      button.dataset.appTarget = item.target;
      button.setAttribute("aria-label", t(item.actionMessageId, item.actionParams));

      const marker = node(
        documentObject,
        "span",
        "ordax-space-icon",
        item.kind === "project" ? "P" : "R",
      );
      marker.setAttribute("aria-hidden", "true");
      const activity = formatHomeActivity(
        item.activityAt,
        localization.getLocale(),
        t("home.continuation.activity.unknown"),
      );
      const persistence = item.persistence === "session"
        ? t("home.continuation.persistence.session")
        : "";
      const detailParams = item.kind === "project"
        ? { path: item.path, activity, persistence }
        : { folder: item.folder, activity, persistence };
      const copy = node(documentObject, "span");
      copy.append(
        node(documentObject, "strong", "", item.title),
        node(documentObject, "small", "", t(item.detailMessageId, detailParams)),
      );
      const arrow = node(documentObject, "span", "ordax-space-arrow", "→");
      arrow.setAttribute("aria-hidden", "true");
      button.append(marker, copy, arrow);
      next.append(button);
    }

    if (section) section.replaceWith(next);
    else homePanel.insertBefore(next, space);
    section = next;

    if (focusedKey) {
      const target = Array.from(section.querySelectorAll("[data-home-continuation-key]"))
        .find((element) => element.dataset.homeContinuationKey === focusedKey) ?? null;
      target?.focus({ preventScroll: true });
    }
  };

  const unsubscribeProjects = projectPort?.subscribe((snapshot) => {
    projectSnapshot = validateProjectCatalogSnapshot(snapshot);
    render();
  });
  const unsubscribeRecent = recentPort?.subscribe((snapshot) => {
    recentSnapshot = validateRecentFilesSnapshot(snapshot);
    render();
  });
  const unsubscribeLocalization = localization.subscribe(() => render());

  render();

  return Object.freeze({
    dispose() {
      if (destroyed) return;
      destroyed = true;
      unsubscribeLocalization();
      unsubscribeRecent?.();
      unsubscribeProjects?.();
      section?.remove();
      section = null;
    },
  });
}
