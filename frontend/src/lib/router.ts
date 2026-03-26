/**
 * Minimaler History-Router für DevRadar.
 * Echte Pfade statt Hash-Routing.
 */

type Listener = () => void;

export type Route = {
  page: "dashboard" | "project" | "settings" | "info";
  projectId?: number;
  infoTab?: string;
};

let _currentPath = window.location.pathname;
let _listeners: Listener[] = [];

/** Aktuellen Pfad lesen. */
export function currentPath(): string {
  return _currentPath;
}

/** Route aus dem Pfad parsen. */
export function parseRoute(path?: string): Route {
  const p = path ?? _currentPath;

  const projectMatch = p.match(/^\/project\/(\d+)$/);
  if (projectMatch) return { page: "project", projectId: parseInt(projectMatch[1], 10) };

  if (p === "/settings") return { page: "settings" };

  const infoMatch = p.match(/^\/info(?:\/(.+))?$/);
  if (infoMatch) return { page: "info", infoTab: infoMatch[1] || "info" };

  return { page: "dashboard" };
}

/** Projekt-ID aus dem Pfad extrahieren (Kompatibilität). */
export function projectIdFromPath(path?: string): number | null {
  const route = parseRoute(path);
  return route.projectId ?? null;
}

/** Navigieren (pushState). */
export function navigate(path: string, replace = false): void {
  if (path === _currentPath) return;
  if (replace) {
    history.replaceState(null, "", path);
  } else {
    history.pushState(null, "", path);
  }
  _currentPath = path;
  _notify();
}

/** Listener registrieren, gibt Unsubscribe-Funktion zurück. */
export function onRouteChange(fn: Listener): () => void {
  _listeners.push(fn);
  return () => {
    _listeners = _listeners.filter(l => l !== fn);
  };
}

function _notify(): void {
  for (const fn of _listeners) fn();
}

// Browser Back/Forward abfangen
window.addEventListener("popstate", () => {
  _currentPath = window.location.pathname;
  _notify();
});
