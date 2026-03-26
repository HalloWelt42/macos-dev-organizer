/**
 * Minimaler History-Router für DevRadar.
 * Echte Pfade statt Hash-Routing.
 */

type Listener = () => void;

let _currentPath = window.location.pathname;
let _listeners: Listener[] = [];

/** Aktuellen Pfad lesen. */
export function currentPath(): string {
  return _currentPath;
}

/** Projekt-ID aus dem Pfad extrahieren (z.B. /project/42 -> 42). */
export function projectIdFromPath(path?: string): number | null {
  const p = path ?? _currentPath;
  const match = p.match(/^\/project\/(\d+)$/);
  return match ? parseInt(match[1], 10) : null;
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
