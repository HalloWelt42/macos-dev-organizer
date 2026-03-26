import type { Project, Stats, AskResponse } from "./types";

const BASE = "/api";

// CSRF-Token: wird einmal beim Start geladen
let _csrfToken = "";
let _tokenPromise: Promise<string> | null = null;

export async function ensureToken(): Promise<string> {
  if (_csrfToken) return _csrfToken;
  if (!_tokenPromise) {
    _tokenPromise = fetch(`${BASE}/token`)
      .then(res => res.json())
      .then(data => { _csrfToken = data.token; return _csrfToken; })
      .catch(() => { _tokenPromise = null; return ""; });
  }
  return _tokenPromise;
}

/** Header-Objekt mit CSRF-Token für schreibende Requests. */
export async function authHeaders(extra: Record<string, string> = {}): Promise<Record<string, string>> {
  const token = await ensureToken();
  return { "X-DevRadar-Token": token, ...extra };
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  let token = await ensureToken();
  const headers = new Headers(init?.headers);
  headers.set("X-DevRadar-Token", token);
  let res = await fetch(url, { ...init, headers });

  // Token ungültig (Backend neu gestartet) -- einmal refreshen und retry
  if (res.status === 403) {
    _csrfToken = "";
    _tokenPromise = null;
    token = await ensureToken();
    headers.set("X-DevRadar-Token", token);
    res = await fetch(url, { ...init, headers });
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API-Fehler ${res.status}: ${text}`);
  }
  return res.json();
}

export async function getProjects(
  query = "",
  type = "",
  sort = "name"
): Promise<Project[]> {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (type) params.set("type", type);
  if (sort) params.set("sort", sort);
  return fetchJson<Project[]>(`${BASE}/projects?${params}`);
}

export async function getProject(id: number): Promise<Project> {
  return fetchJson<Project>(`${BASE}/projects/${id}`);
}

export async function openProject(path: string, app: string): Promise<void> {
  await fetchJson(`${BASE}/open`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, app }),
  });
}

export async function rescan(): Promise<{ found: number; removed: number }> {
  return fetchJson(`${BASE}/rescan`, { method: "POST" });
}

export async function askQuestion(question: string): Promise<AskResponse> {
  return fetchJson<AskResponse>(`${BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export async function getStats(): Promise<Stats> {
  return fetchJson<Stats>(`${BASE}/stats`);
}

export async function getVersion(): Promise<string> {
  const data = await fetchJson<{ version: string }>(`${BASE}/version`);
  return data.version;
}

export function translateReadme(
  projectId: number,
  onChunk: (data: { type: string; full: string; stats: { tokens: number; elapsed: number; tps: number } }) => void,
  onDone: (data: { full: string }) => void,
  onError: (err: Error) => void
): AbortController {
  const controller = new AbortController();
  ensureToken().then((token) => {
  fetch(`${BASE}/projects/${projectId}/translate`, {
    method: "POST",
    signal: controller.signal,
    headers: { "X-DevRadar-Token": token },
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`API-Fehler ${res.status}`);
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        while (buffer.includes("\n\n")) {
          const idx = buffer.indexOf("\n\n");
          const line = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 2);
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.slice(6));
          if (data.type === "chunk") onChunk(data);
          else if (data.type === "done") onDone(data);
        }
      }
    })
    .catch((err) => { if (err.name !== "AbortError") onError(err); });
  });
  return controller;
}

export async function deleteTranslation(projectId: number): Promise<void> {
  const token = await ensureToken();
  await fetch(`${BASE}/projects/${projectId}/translate`, { method: "DELETE", headers: { "X-DevRadar-Token": token } });
}

export async function saveDescription(
  projectId: number,
  description: string
): Promise<void> {
  await fetchJson(`${BASE}/projects/${projectId}/description`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description }),
  });
}

export function enrichProject(
  projectId: number,
  onChunk: (data: { type: string; full: string; stats: { tokens: number; elapsed: number; tps: number } }) => void,
  onDone: (data: { full: string }) => void,
  onError: (err: Error) => void
): AbortController {
  const controller = new AbortController();

  ensureToken().then((token) => {
  fetch(`${BASE}/projects/${projectId}/enrich`, {
    method: "POST",
    signal: controller.signal,
    headers: { "X-DevRadar-Token": token },
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`API-Fehler ${res.status}`);
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        while (buffer.includes("\n\n")) {
          const idx = buffer.indexOf("\n\n");
          const line = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 2);
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.slice(6));
          if (data.type === "chunk") onChunk(data);
          else if (data.type === "done") onDone(data);
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(err);
    });
  });

  return controller;
}
