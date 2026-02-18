<script lang="ts">
  import type { Stats } from "../lib/types";

  let {
    stats,
    activeType = $bindable(""),
    activeSort = $bindable("name"),
    onFilter,
  }: {
    stats: Stats;
    activeType: string;
    activeSort: string;
    onFilter: () => void;
  } = $props();

  const typeLabels: Record<string, { label: string; icon: string; brand?: boolean }> = {
    git: { label: "Git", icon: "fa-code-branch" },
    node: { label: "Node.js", icon: "fa-node-js", brand: true },
    extension: { label: "Extensions", icon: "fa-puzzle-piece" },
    docker: { label: "Docker", icon: "fa-docker", brand: true },
    python: { label: "Python", icon: "fa-python", brand: true },
  };

  function toggleType(type: string) {
    activeType = activeType === type ? "" : type;
    onFilter();
  }

  function setSort(sort: string) {
    activeSort = sort;
    onFilter();
  }
</script>

<aside class="space-y-6">
  <!-- Statistik -->
  <div>
    <h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
      Statistik
    </h2>
    <p class="text-2xl font-bold text-slate-900 dark:text-slate-100">{stats.total}</p>
    <p class="text-sm text-slate-500">Projekte gesamt</p>
  </div>

  <!-- Typ-Filter -->
  <div>
    <h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
      Typ
    </h2>
    <div class="space-y-1">
      <button
        onclick={() => { activeType = ""; onFilter(); }}
        class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors
               {activeType === '' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
      >
        <span><i class="fa-solid fa-layer-group mr-2 w-5 text-center"></i>Alle</span>
        <span class="font-mono text-xs">{stats.total}</span>
      </button>
      {#each Object.entries(stats.by_type) as [type, count]}
        {@const info = typeLabels[type]}
        {#if info}
          <button
            onclick={() => toggleType(type)}
            class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors
                   {activeType === type ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
          >
            <span><i class="{info.brand ? 'fa-brands' : 'fa-solid'} {info.icon} mr-2 w-5 text-center"></i>{info.label}</span>
            <span class="font-mono text-xs">{count}</span>
          </button>
        {/if}
      {/each}
    </div>
  </div>

  <!-- Sortierung -->
  <div>
    <h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
      Sortierung
    </h2>
    <div class="space-y-1">
      {#each [["name", "Name", "fa-arrow-down-a-z"], ["modified", "Zuletzt bearbeitet", "fa-clock"], ["oldest", "Älteste zuerst", "fa-hourglass-start"], ["type", "Typ", "fa-tags"], ["path", "Ordnerstruktur", "fa-folder-tree"]] as [value, label, icon]}
        <button
          onclick={() => setSort(value)}
          class="flex w-full items-center rounded-lg px-3 py-2 text-sm transition-colors
                 {activeSort === value ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
        >
          <i class="fa-solid {icon} mr-2 w-5 text-center"></i>{label}
        </button>
      {/each}
    </div>
  </div>
</aside>
