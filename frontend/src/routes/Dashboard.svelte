<script lang="ts">
  import type { Project, Stats } from "../lib/types";
  import { getProjects, getStats } from "../lib/api";
  import SearchBar from "../components/SearchBar.svelte";
  import ProjectCard from "../components/ProjectCard.svelte";
  import ProjectListItem from "../components/ProjectListItem.svelte";
  import ProjectDetailView from "../components/ProjectDetailView.svelte";
  import StatsBar from "../components/StatsBar.svelte";
  import AskPanel from "../components/AskPanel.svelte";
  import SettingsView from "../components/SettingsView.svelte";
  import SvelteMarkdown, { Html } from "@humanspeak/svelte-markdown";
  const mdRenderers = { html: Html };
  import { navigate } from "../lib/router";

  let { selectedProjectIdFromRoute = null }: { selectedProjectIdFromRoute?: number | null } = $props();
  let selectedProjectId: number | null = $derived(selectedProjectIdFromRoute);

  let projects: Project[] = $state([]);
  let stats: Stats = $state({ total: 0, by_type: {}, last_scan: "" });
  let searchQuery = $state("");
  let activeTypes: Set<string> = $state(new Set());
  let activeSort = $state("name");
  let loading = $state(true);
  let highlightIds: Set<number> = $state(new Set());
  let viewMode: "grid" | "list" = $state("grid");
  let scanRoots: string[] = $state([]);
  let showSettings = $state(false);

  // KI-Antwort im Content-Bereich
  let askAnswer = $state("");
  let askLoading = $state(false);
  let askStats = $state({ tokens: 0, elapsed: 0, tps: 0 });
  let askFallback = $state(false);

  const typeLabels: Record<string, { label: string; icon: string; brand?: boolean }> = {
    git: { label: "Git", icon: "fa-code-branch" },
    node: { label: "Node.js", icon: "fa-node-js", brand: true },
    extension: { label: "Extensions", icon: "fa-puzzle-piece" },
    docker: { label: "Docker", icon: "fa-docker", brand: true },
    python: { label: "Python", icon: "fa-python", brand: true },
    readme: { label: "Readme", icon: "fa-file-lines" },
  };

  async function loadProjects() {
    loading = true;
    try {
      const typeFilter = activeTypes.size === 1 ? [...activeTypes][0] : "";
      projects = await getProjects(searchQuery, typeFilter, activeSort);
      if (activeTypes.size > 1) {
        projects = projects.filter((p) => activeTypes.has(p.project_type));
      }
    } catch (e) {
      console.error("Fehler beim Laden:", e);
    } finally {
      loading = false;
    }
  }

  async function loadStats() {
    try {
      stats = await getStats();
    } catch (e) {
      console.error("Fehler beim Laden der Statistiken:", e);
    }
  }

  /** Zurück zur Projektliste (Einstellungen/Detail schliessen). */
  function showProjectList() {
    showSettings = false;
    selectedProjectId = null;
  }

  function handleSearch(q: string) {
    searchQuery = q;
    showProjectList();
    loadProjects();
  }

  function handleFilter() {
    showProjectList();
    loadProjects();
  }

  function handleRescan() {
    loadProjects();
    loadStats();
  }

  function handleProjectIds(ids: number[]) {
    highlightIds = new Set(ids);
  }

  function toggleType(type: string) {
    const next = new Set(activeTypes);
    if (next.has(type)) next.delete(type); else next.add(type);
    activeTypes = next;
    handleFilter();
  }

  async function loadRoots() {
    try {
      const res = await fetch("/api/config/roots");
      const data = await res.json();
      scanRoots = data.roots || [];
    } catch {}
  }

  function handleSettingsSaved() {
    showSettings = false;
    loadRoots();
    handleRescan();
  }

  $effect(() => {
    loadProjects();
    loadStats();
    loadRoots();
  });

  let displayProjects = $derived(
    highlightIds.size > 0
      ? [
          ...projects.filter((p) => highlightIds.has(p.id)),
          ...projects.filter((p) => !highlightIds.has(p.id)),
        ]
      : projects
  );
</script>

<div class="flex h-screen flex-col">
  <!-- Header: kompakt -->
  <header class="shrink-0 border-b border-slate-200 bg-slate-50 px-4 py-2 dark:border-slate-700 dark:bg-slate-900">
    <StatsBar {stats} onRescan={handleRescan} />
    <!-- Suche + KI nebeneinander, gleich aufgeteilt -->
    <div class="mt-2 grid grid-cols-2 gap-3">
      <SearchBar bind:value={searchQuery} onSearch={handleSearch} />
      <AskPanel
        onStart={() => { askAnswer = ""; askLoading = true; askStats = { tokens: 0, elapsed: 0, tps: 0 }; askFallback = false; }}
        onChunk={(data) => { askAnswer = data.full; askStats = data.stats; }}
        onDone={(data) => {
          askAnswer = data.full;
          askLoading = false;
          askFallback = data.fallback;
          askStats = data.stats;
          if (data.project_ids?.length > 0) handleProjectIds(data.project_ids);
        }}
      />
    </div>
  </header>

  <!-- Body: Sidebar + Content -->
  <div class="flex min-h-0 flex-1">
    <!-- Sidebar: Filter + Sortierung -->
    <aside class="w-48 shrink-0 overflow-y-auto border-r border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900">
      <!-- Typ-Filter (Mehrfachauswahl) -->
      <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Typ</h2>
      <div class="space-y-0.5">
        <button
          onclick={() => { activeTypes = new Set(); handleFilter(); }}
          class="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-xs transition-colors
                 {activeTypes.size === 0 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
        >
          <span><i class="fa-solid fa-layer-group mr-2 w-4 text-center"></i>Alle</span>
          <span class="font-mono text-[10px]">{stats.total}</span>
        </button>
        {#each Object.entries(stats.by_type) as [type, count]}
          {@const info = typeLabels[type]}
          <button
            onclick={() => toggleType(type)}
            class="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-xs transition-colors
                   {activeTypes.has(type) ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
          >
            <span>
              {#if info}
                <i class="{info.brand ? 'fa-brands' : 'fa-solid'} {info.icon} mr-2 w-4 text-center"></i>{info.label}
              {:else}
                <i class="fa-solid fa-folder mr-2 w-4 text-center"></i>{type}
              {/if}
            </span>
            <span class="font-mono text-[10px]">{count}</span>
          </button>
        {/each}
      </div>

      <!-- Sortierung -->
      <h2 class="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Sortierung</h2>
      <div class="space-y-0.5">
        {#each [["name", "Name", "fa-arrow-down-a-z"], ["modified", "Bearbeitet", "fa-clock"], ["oldest", "Älteste", "fa-hourglass-start"], ["type", "Typ", "fa-tags"], ["path", "Ordner", "fa-folder-tree"]] as [value, label, icon]}
          <button
            onclick={() => { activeSort = value; handleFilter(); }}
            class="flex w-full items-center rounded-md px-2 py-1.5 text-xs transition-colors
                   {activeSort === value ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
          >
            <i class="fa-solid {icon} mr-2 w-4 text-center"></i>{label}
          </button>
        {/each}
      </div>

      <!-- Ansicht -->
      <h2 class="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Ansicht</h2>
      <div class="flex gap-1">
        <button
          onclick={() => { viewMode = "grid"; showProjectList(); }}
          class="flex-1 rounded-md px-2 py-1.5 text-xs transition-colors
                 {viewMode === 'grid' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
        >
          <i class="fa-solid fa-table-cells mr-1"></i>Karten
        </button>
        <button
          onclick={() => { viewMode = "list"; showProjectList(); }}
          class="flex-1 rounded-md px-2 py-1.5 text-xs transition-colors
                 {viewMode === 'list' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
        >
          <i class="fa-solid fa-list mr-1"></i>Liste
        </button>
      </div>

      <!-- Einstellungen -->
      <div class="mt-4 border-t border-slate-200 pt-3 dark:border-slate-700">
        <button
          onclick={() => { showSettings = !showSettings; }}
          class="flex w-full items-center rounded-md px-2 py-1.5 text-xs transition-colors
                 {showSettings ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
        >
          <i class="fa-solid fa-gear mr-2 w-4 text-center"></i>Einstellungen
        </button>
      </div>
    </aside>

    <!-- Content: bei Detail kein eigenes Scroll, Detail managed das selbst -->
    <main class="flex-1 {selectedProjectId && !showSettings ? 'overflow-hidden p-3' : 'overflow-y-auto p-4'}">
      {#if showSettings}
        <SettingsView onSave={handleSettingsSaved} />
      {:else if selectedProjectId}
        <ProjectDetailView projectId={selectedProjectId} allProjectIds={projects.map(p => p.id)} />
      {:else if askAnswer || askLoading}
        <!-- KI-Antwort im Content-Bereich -->
        <div class="flex gap-4 lg:flex-row flex-col">
          <!-- Antwort (62%) -->
          <div class="lg:w-[62%] min-w-0">
            <div class="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
              <div class="flex items-center justify-between border-b border-slate-200 px-4 py-2 dark:border-slate-700">
                <div class="flex items-center gap-2">
                  <i class="fa-solid fa-robot text-amber-500"></i>
                  <span class="text-sm font-medium text-slate-500">KI-Antwort</span>
                  {#if askFallback}
                    <span class="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] text-slate-500 dark:bg-slate-700">FTS5-Fallback</span>
                  {/if}
                </div>
                <div class="flex items-center gap-3 text-xs text-slate-400">
                  {#if askStats.tps > 0}
                    <span class="font-mono">{askStats.tokens} Tokens -- {askStats.tps} t/s -- {askStats.elapsed}s</span>
                  {/if}
                  {#if askLoading}
                    <span class="animate-pulse text-amber-400"><i class="fa-solid fa-circle text-[6px]"></i></span>
                  {/if}
                  <button onclick={() => { askAnswer = ""; highlightIds = new Set(); }} class="text-slate-400 hover:text-slate-600" title="Schliessen">
                    <i class="fa-solid fa-xmark"></i>
                  </button>
                </div>
              </div>
              <div class="max-h-[calc(100vh-14rem)] overflow-y-auto p-4">
                <div class="prose prose-sm max-w-prose dark:prose-invert
                            prose-headings:text-slate-800 dark:prose-headings:text-slate-200
                            prose-a:text-amber-600 dark:prose-a:text-amber-400
                            prose-code:rounded prose-code:bg-slate-200 prose-code:px-1 dark:prose-code:bg-slate-800">
                  <SvelteMarkdown source={askAnswer} renderers={mdRenderers} />
                </div>
              </div>
            </div>
          </div>

          <!-- Referenzierte Projekte (38%) -->
          {#if highlightIds.size > 0}
            <div class="lg:w-[38%] space-y-2">
              <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500">Referenzierte Projekte</h3>
              {#each projects.filter(p => highlightIds.has(p.id)) as project (project.id)}
                <button
                  onclick={() => navigate(`/project/${project.id}`)}
                  class="flex w-full items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 text-left transition-colors
                         hover:border-amber-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-amber-600"
                >
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-medium text-slate-900 dark:text-slate-100">{project.name}</p>
                    {#if project.description}
                      <p class="mt-0.5 truncate text-xs text-slate-500">{project.description}</p>
                    {/if}
                    <div class="mt-1 flex flex-wrap gap-1">
                      {#each project.tags.slice(0, 3) as tag}
                        <span class="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500 dark:bg-slate-700">{tag}</span>
                      {/each}
                    </div>
                  </div>
                  <i class="fa-solid fa-chevron-right mt-1 text-xs text-slate-400"></i>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {:else if loading}
        <div class="flex items-center justify-center py-20">
          <i class="fa-solid fa-spinner animate-spin text-2xl text-amber-500"></i>
        </div>
      {:else if projects.length === 0 && scanRoots.length === 0}
        <!-- Willkommens-Dialog bei Erststart -->
        <div class="flex items-center justify-center py-20">
          <div class="max-w-md rounded-lg border border-amber-200 bg-amber-50 p-8 text-center dark:border-amber-800 dark:bg-amber-950/30">
            <i class="fa-solid fa-radar mb-4 text-5xl text-amber-500"></i>
            <h2 class="mb-2 text-xl font-bold text-slate-900 dark:text-slate-100">Willkommen bei DevRadar</h2>
            <p class="mb-4 text-sm text-slate-600 dark:text-slate-400">
              Um loszulegen, konfiguriere mindestens ein Verzeichnis, das nach Projekten durchsucht werden soll.
            </p>
            <button
              onclick={() => { showSettings = true; }}
              class="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-600"
            >
              <i class="fa-solid fa-gear mr-2"></i>Einstellungen öffnen
            </button>
          </div>
        </div>
      {:else if projects.length === 0}
        <div class="py-20 text-center text-slate-500">
          <i class="fa-solid fa-folder-open mb-4 text-4xl"></i>
          <p>Keine Projekte gefunden.</p>
        </div>
      {:else}
        <p class="mb-3 text-sm text-slate-400">{projects.length} Projekte</p>

        {#if viewMode === "grid"}
          <div class="grid gap-3" style="grid-template-columns: repeat(auto-fill, minmax(300px, 1fr))">
            {#each displayProjects as project (project.id)}
              <div class={highlightIds.has(project.id) ? "ring-2 ring-amber-400 rounded-lg" : ""}>
                <ProjectCard {project} searchQuery={searchQuery} />
              </div>
            {/each}
          </div>
        {:else}
          <div class="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
            {#each displayProjects as project, idx (project.id)}
              <div class="{highlightIds.has(project.id) ? 'bg-amber-50 dark:bg-amber-950/30' : idx % 2 === 1 ? 'bg-slate-50/50 dark:bg-slate-800/30' : ''}">
                <ProjectListItem {project} searchQuery={searchQuery} />
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </main>
  </div>
</div>
