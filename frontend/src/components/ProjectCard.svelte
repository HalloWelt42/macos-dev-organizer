<script lang="ts">
  import type { Project } from "../lib/types";
  import { openProject } from "../lib/api";
  import { navigate } from "../lib/router";
  import SvelteMarkdown, { Html } from "@humanspeak/svelte-markdown";
  const renderers = { html: Html };

  let { project, searchQuery = "" }: { project: Project; searchQuery?: string } = $props();

  const typeIcons: Record<string, string> = {
    git: "fa-code-branch",
    node: "fa-node-js",
    extension: "fa-puzzle-piece",
    docker: "fa-docker",
    python: "fa-python",
    readme: "fa-file-lines",
  };

  const typeColors: Record<string, string> = {
    git: "text-orange-500",
    node: "text-green-500",
    extension: "text-purple-500",
    docker: "text-blue-500",
    python: "text-yellow-500",
    readme: "text-slate-500",
  };

  // Repo-URL aus Metadata extrahieren
  let repoUrl = $derived(() => {
    const url = project.metadata?.remote_url as string || "";
    if (!url) return "";
    // SSH -> HTTPS umwandeln
    if (url.startsWith("git@")) {
      return url.replace("git@", "https://").replace(":", "/").replace(/\.git$/, "");
    }
    return url.replace(/\.git$/, "");
  });

  let icon = $derived(typeIcons[project.project_type] || "fa-folder");
  let color = $derived(typeColors[project.project_type] || "text-slate-500");
  let isBrand = $derived(["node", "docker", "python"].includes(project.project_type));

  // Elternverzeichnis als Kontext anzeigen
  let parentDir = $derived(() => {
    // Home-Pfad dynamisch aus dem Projektpfad ableiten (/Users/xxx/ oder /home/xxx/)
    const homeMatch = project.path.match(/^(\/(?:Users|home)\/[^/]+\/)/);
    const home = homeMatch ? homeMatch[1] : "";
    const rel = home && project.path.startsWith(home) ? project.path.slice(home.length) : project.path;
    const relParts = rel.split("/");
    return relParts.length >= 2 ? relParts.slice(0, -1).join("/") : "";
  });

  /**
   * Suchbegriff im Text hervorheben.
   * Gibt HTML zurück mit <mark>-Tags.
   */
  function highlight(text: string, query: string): string {
    if (!query || query.length < 2) return escapeHtml(text);
    const escaped = escapeHtml(text);
    const queryEscaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`(${queryEscaped})`, "gi");
    return escaped.replace(re, '<mark class="rounded bg-amber-200 px-0.5 dark:bg-amber-700 dark:text-amber-100">$1</mark>');
  }

  function escapeHtml(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function relativeTime(iso: string): string {
    if (!iso) return "";
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins} Min.`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours} Std.`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} T.`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} Mon.`;
    return `${Math.floor(months / 12)} J.`;
  }

  let lastActivity = $derived(relativeTime(project.metadata?.last_commit_date as string || project.last_modified));
  let projectAge = $derived(relativeTime(project.metadata?.first_commit_date as string || project.detected_at));

  async function handleOpen(app: string, e: MouseEvent) {
    e.stopPropagation();
    try {
      await openProject(project.path, app);
    } catch (err) {
      console.error("Fehler beim Öffnen:", err);
    }
  }
</script>

<div
  class="group flex h-full cursor-pointer flex-col overflow-hidden rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-all
         hover:border-amber-300 hover:shadow-md
         dark:border-slate-700 dark:bg-slate-800 dark:hover:border-amber-600"
  onclick={() => navigate(`/project/${project.id}`)}
  role="button"
  tabindex="0"
  onkeydown={(e) => e.key === "Enter" && navigate(`/project/${project.id}`)}
>
  <div class="mb-2 flex items-start justify-between gap-2">
    <div class="min-w-0 flex items-center gap-2">
      <i class="{isBrand ? 'fa-brands' : 'fa-solid'} {icon} {color} shrink-0 text-lg"></i>
      <div class="min-w-0">
        <h3 class="truncate font-semibold text-slate-900 dark:text-slate-100">{@html highlight(project.name, searchQuery)}</h3>
        {#if parentDir()}
          <p class="truncate text-xs text-slate-400 dark:text-slate-500">{parentDir()}</p>
        {/if}
      </div>
    </div>
    <div class="shrink-0 text-right text-xs text-slate-400">
      <div title="Letzte Aktivität"><i class="fa-solid fa-pen-to-square mr-1 text-[10px]"></i>{lastActivity}</div>
      <div title="Projektalter"><i class="fa-solid fa-calendar-plus mr-1 text-[10px]"></i>{projectAge}</div>
    </div>
  </div>

  {#if project.description}
    <div class="mb-3 flex-1 overflow-hidden text-sm text-slate-600 line-clamp-2 dark:text-slate-400 prose prose-sm max-w-none dark:prose-invert prose-p:m-0 prose-a:text-amber-600 dark:prose-a:text-amber-400">
      <SvelteMarkdown source={project.description} {renderers} />
    </div>
  {:else}
    <div class="flex-1"></div>
  {/if}

  <div class="mb-3 flex flex-wrap gap-1">
    {#each project.tags as tag}
      <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
        {@html highlight(tag, searchQuery)}
      </span>
    {/each}
  </div>

  <div class="mt-auto flex gap-2">
    {#if repoUrl()}
      <a
        href={repoUrl()}
        target="_blank"
        rel="noopener"
        onclick={(e) => e.stopPropagation()}
        class="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-600 transition-colors
               hover:bg-slate-200 hover:text-slate-800
               dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 dark:hover:text-slate-100"
        title="Repository öffnen"
      >
        <i class="fa-brands fa-github mr-1"></i>Repo
      </a>
    {/if}
    <button
      onclick={(e) => handleOpen("finder", e)}
      class="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-600 transition-colors
             hover:bg-amber-100 hover:text-amber-700
             dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-amber-900 dark:hover:text-amber-300"
      title="Im Finder öffnen"
    >
      <i class="fa-solid fa-folder-open mr-1"></i>Finder
    </button>
    <button
      onclick={(e) => handleOpen("ide", e)}
      class="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-600 transition-colors
             hover:bg-blue-100 hover:text-blue-700
             dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-blue-900 dark:hover:text-blue-300"
      title="In IDE öffnen"
    >
      <i class="fa-solid fa-code mr-1"></i>IDE
    </button>
    <button
      onclick={(e) => handleOpen("terminal", e)}
      class="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-600 transition-colors
             hover:bg-green-100 hover:text-green-700
             dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-green-900 dark:hover:text-green-300"
      title="Terminal öffnen"
    >
      <i class="fa-solid fa-terminal mr-1"></i>Terminal
    </button>
  </div>
</div>
