<script lang="ts">
  import type { Project } from "../lib/types";
  import { openProject } from "../lib/api";
  import { navigate } from "../lib/router";

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

  let repoUrl = $derived(() => {
    const url = project.metadata?.remote_url as string || "";
    if (!url) return "";
    if (url.startsWith("git@")) {
      return url.replace("git@", "https://").replace(":", "/").replace(/\.git$/, "");
    }
    return url.replace(/\.git$/, "");
  });

  let icon = $derived(typeIcons[project.project_type] || "fa-folder");
  let color = $derived(typeColors[project.project_type] || "text-slate-500");
  let isBrand = $derived(["node", "docker", "python"].includes(project.project_type));

  let parentDir = $derived(() => {
    // Home-Pfad dynamisch aus dem Projektpfad ableiten (/Users/xxx/ oder /home/xxx/)
    const homeMatch = project.path.match(/^(\/(?:Users|home)\/[^/]+\/)/);
    const home = homeMatch ? homeMatch[1] : "";
    const rel = home && project.path.startsWith(home) ? project.path.slice(home.length) : project.path;
    const relParts = rel.split("/");
    return relParts.length >= 2 ? relParts.slice(0, -1).join("/") : "";
  });

  function highlight(text: string, query: string): string {
    if (!query || query.length < 2) return escapeHtml(text);
    const escaped = escapeHtml(text);
    const queryEscaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`(${queryEscaped})`, "gi");
    return escaped.replace(re, '<mark class="rounded bg-amber-200 px-0.5 dark:bg-amber-700 dark:text-amber-100">$1</mark>');
  }

  function escapeHtml(text: string): string {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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
  class="group flex cursor-pointer items-center gap-4 border-b border-slate-100 px-3 py-2.5 transition-colors
         hover:bg-amber-50/50 dark:border-slate-800 dark:hover:bg-amber-950/20"
  onclick={() => navigate(`/project/${project.id}`)}
  role="button"
  tabindex="0"
  onkeydown={(e) => e.key === "Enter" && navigate(`/project/${project.id}`)}
>
  <!-- Icon -->
  <i class="{isBrand ? 'fa-brands' : 'fa-solid'} {icon} {color} w-5 text-center"></i>

  <!-- Name + Pfad -->
  <div class="min-w-0 flex-1">
    <div class="flex items-baseline gap-2">
      <span class="truncate font-medium text-slate-900 dark:text-slate-100">{@html highlight(project.name, searchQuery)}</span>
      {#if parentDir()}
        <span class="truncate text-xs text-slate-400">{parentDir()}</span>
      {/if}
    </div>
    {#if project.description}
      <p class="truncate text-xs text-slate-500 dark:text-slate-400">{@html highlight(project.description, searchQuery)}</p>
    {/if}
  </div>

  <!-- Tags -->
  <div class="hidden shrink-0 gap-1 md:flex">
    {#each project.tags.slice(0, 4) as tag}
      <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-700 dark:text-slate-400">
        {tag}
      </span>
    {/each}
    {#if project.tags.length > 4}
      <span class="text-xs text-slate-400">+{project.tags.length - 4}</span>
    {/if}
  </div>

  <!-- Zeit -->
  <div class="shrink-0 text-right text-xs text-slate-400">
    <span title="Letzte Aktivität"><i class="fa-solid fa-pen-to-square mr-0.5 text-[9px]"></i>{lastActivity}</span>
    <span class="mx-1 text-slate-300 dark:text-slate-600">|</span>
    <span title="Projektalter"><i class="fa-solid fa-calendar-plus mr-0.5 text-[9px]"></i>{projectAge}</span>
  </div>

  <!-- Aktionen -->
  <div class="flex shrink-0 gap-1">
    {#if repoUrl()}
      <a
        href={repoUrl()}
        target="_blank"
        rel="noopener"
        onclick={(e) => e.stopPropagation()}
        class="rounded p-1.5 text-xs text-slate-400 hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
        title="Repository"
      >
        <i class="fa-brands fa-github"></i>
      </a>
    {/if}
    <button
      onclick={(e) => handleOpen("finder", e)}
      class="rounded p-1.5 text-xs text-slate-400 hover:bg-amber-100 hover:text-amber-700 dark:hover:bg-amber-900 dark:hover:text-amber-300"
      title="Finder"
    >
      <i class="fa-solid fa-folder-open"></i>
    </button>
    <button
      onclick={(e) => handleOpen("ide", e)}
      class="rounded p-1.5 text-xs text-slate-400 hover:bg-blue-100 hover:text-blue-700 dark:hover:bg-blue-900 dark:hover:text-blue-300"
      title="IDE"
    >
      <i class="fa-solid fa-code"></i>
    </button>
    <button
      onclick={(e) => handleOpen("terminal", e)}
      class="rounded p-1.5 text-xs text-slate-400 hover:bg-green-100 hover:text-green-700 dark:hover:bg-green-900 dark:hover:text-green-300"
      title="Terminal"
    >
      <i class="fa-solid fa-terminal"></i>
    </button>
  </div>
</div>
